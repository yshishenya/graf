import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
from twobrain_rec_server.auth.sessions import issue_auth_session
from twobrain_rec_server.db.models import (
    AuthSessionDeviceBinding,
    MeetingLifecycleAuditEvent,
    RecordingOriginCancellation,
    RegisteredDevice,
)
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY


def cancel(client, origin, headers=None):
    return client.post(
        f"/api/v1/desktop/recordings/{origin}/deletion-requests",
        headers=auth_headers() if headers is None else headers,
        json={"operation_id": str(uuid4()), "confirmation_boundary": BOUNDED_DELETE_COPY},
    )


def create(client, origin, headers=None):
    return client.post("/api/v1/meetings", headers=auth_headers() if headers is None else headers, json={
        "local_recording_id": origin, "duration_seconds": 10, "title": "Synthetic recording",
    })


def test_cancel_before_create_is_durable_and_repeatable(client):
    origin = str(uuid4())
    first = cancel(client, origin)
    assert first.status_code == 202
    assert first.json()["receipt_type"] == "origin_cancellation"
    assert "meeting_id" not in first.json()
    assert cancel(client, origin).json() == first.json()
    late = create(client, origin)
    assert late.status_code == 409
    assert late.json()["code"] == "recording_deletion_active"


def test_repeat_from_another_registered_device_preserves_first_audit(client):
    origin, second_device = str(uuid4()), uuid4()

    async def sessions():
        async with client.app_state["sessionmaker"]() as db:
            db.add(RegisteredDevice(
                id=second_device, workspace_id=WORKSPACE_ID, user_id=USER_ID,
                device_public_id=str(second_device), status="active",
            ))
            await db.flush()
            headers = []
            for device_id in (DEVICE_ID, second_device):
                session = await issue_auth_session(
                    db, user_id=USER_ID, workspace_id=WORKSPACE_ID,
                    device_id=device_id, provider="synthetic-f262",
                )
                db.add(AuthSessionDeviceBinding(
                    auth_session_id=session.id, registered_device_id=device_id,
                    device_state="trusted",
                ))
                headers.append({
                    "X-Auth-Session": session.token,
                    "X-Graf-Expected-Actor": str(USER_ID),
                    "X-Graf-Expected-Workspace": str(WORKSPACE_ID),
                })
            await db.commit()
            return headers

    async def audit_snapshot():
        async with client.app_state["sessionmaker"]() as db:
            return (await db.execute(select(
                MeetingLifecycleAuditEvent.id, MeetingLifecycleAuditEvent.workspace_id,
                MeetingLifecycleAuditEvent.actor_user_id, MeetingLifecycleAuditEvent.device_id,
                MeetingLifecycleAuditEvent.created_at, MeetingLifecycleAuditEvent.metadata_json,
            ))).all()

    first_headers, second_headers = asyncio.run(sessions())
    first = cancel(client, origin, first_headers)
    assert first.status_code == 202
    snapshot = asyncio.run(audit_snapshot())
    assert len(snapshot) == 1
    assert snapshot[0][1:4] == (WORKSPACE_ID, USER_ID, DEVICE_ID)
    assert snapshot[0].metadata_json == {"cancellation_id": first.json()["request_id"]}
    for headers in (second_headers, first_headers):
        repeated = cancel(client, origin, headers)
        assert repeated.status_code == 202
        assert repeated.json() == first.json()
        assert create(client, origin, headers).status_code == 409
        assert asyncio.run(audit_snapshot()) == snapshot


def test_audit_insert_failure_rolls_back_origin_cancellation(client):
    origin = str(uuid4())

    def fail_audit_insert(mapper, connection, target):
        if target.event_type == "recording_origin_canceled":
            raise RuntimeError("synthetic audit write failure")

    event.listen(MeetingLifecycleAuditEvent, "before_insert", fail_audit_insert)
    try:
        with pytest.raises(RuntimeError, match="synthetic audit write failure"):
            cancel(client, origin)
    finally:
        event.remove(MeetingLifecycleAuditEvent, "before_insert", fail_audit_insert)

    async def inspect():
        async with client.app_state["sessionmaker"]() as db:
            assert await db.scalar(select(RecordingOriginCancellation)) is None
            assert await db.scalar(select(MeetingLifecycleAuditEvent)) is None

    asyncio.run(inspect())
    assert create(client, origin).status_code == 200
    # A fresh cancellation can still commit normally after the failed audit.
    assert cancel(client, str(uuid4())).status_code == 202


def test_old_marker_repeat_does_not_fabricate_historical_device_audit(client):
    origin = str(uuid4())

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            marker = RecordingOriginCancellation(
                workspace_id=WORKSPACE_ID, created_by_user_id=USER_ID,
                local_recording_id=origin,
            )
            db.add(marker)
            await db.commit()
            return marker.id, marker.accepted_at

    marker_id, accepted_at = asyncio.run(seed())
    response = cancel(client, origin)
    assert response.status_code == 202
    assert response.json()["request_id"] == str(marker_id)
    assert cancel(client, origin).json() == response.json()
    assert create(client, origin).status_code == 409

    async def inspect():
        async with client.app_state["sessionmaker"]() as db:
            marker = await db.get(RecordingOriginCancellation, marker_id)
            assert marker.accepted_at == accepted_at
            assert marker.local_recording_id == origin
            assert await db.scalar(select(MeetingLifecycleAuditEvent)) is None

    asyncio.run(inspect())


@pytest.mark.parametrize("device_state", ["revoked", "pending", "other_workspace"])
def test_unavailable_session_device_cannot_create_cancellation_or_audit(client, device_state):
    from tests.fakes.auth_contexts import PERSONAL_WORKSPACE_ID

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            session = await issue_auth_session(
                db, user_id=USER_ID, workspace_id=WORKSPACE_ID,
                device_id=DEVICE_ID, provider="synthetic-f262",
            )
            db.add(AuthSessionDeviceBinding(
                auth_session_id=session.id, registered_device_id=DEVICE_ID,
                device_state="trusted",
            ))
            device = await db.get(RegisteredDevice, DEVICE_ID)
            if device_state == "other_workspace":
                device.workspace_id = PERSONAL_WORKSPACE_ID
            else:
                device.registration_state = device_state
            await db.commit()
            return session.token

    response = cancel(client, str(uuid4()), {
        "X-Auth-Session": asyncio.run(seed()),
        "X-Graf-Expected-Actor": str(USER_ID),
        "X-Graf-Expected-Workspace": str(WORKSPACE_ID),
    })
    assert response.status_code == 403
    assert "receipt_type" not in response.json()

    async def inspect():
        async with client.app_state["sessionmaker"]() as db:
            assert await db.scalar(select(RecordingOriginCancellation)) is None
            assert await db.scalar(select(MeetingLifecycleAuditEvent)) is None

    asyncio.run(inspect())


def test_concurrent_cancellations_commit_one_marker_and_audit(client):
    origin = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: cancel(client, origin), range(2)))
    assert [response.status_code for response in responses] == [202, 202]
    assert responses[0].json() == responses[1].json()

    async def inspect():
        async with client.app_state["sessionmaker"]() as db:
            markers = (await db.scalars(select(RecordingOriginCancellation))).all()
            audits = (await db.scalars(select(MeetingLifecycleAuditEvent))).all()
            assert len(markers) == len(audits) == 1
            assert audits[0].metadata_json == {"cancellation_id": str(markers[0].id)}
            assert audits[0].device_id == DEVICE_ID
            assert audits[0].created_at == markers[0].accepted_at

    asyncio.run(inspect())


def test_cancel_existing_origin_uses_meeting_deletion_receipt(client):
    origin = str(uuid4())
    created = create(client, origin)
    assert created.status_code == 200
    deleted = cancel(client, origin)
    assert deleted.status_code == 202
    assert deleted.json()["receipt_type"] == "meeting_deletion"
    assert deleted.json()["meeting_id"] == created.json()["meeting_id"]
    assert cancel(client, origin).json() == deleted.json()


@pytest.mark.parametrize("other_namespace", ["user", "workspace"])
def test_equal_origins_keep_create_and_cancel_in_their_owner_namespace(client, other_namespace):
    from sqlalchemy import select

    from tests.fakes.auth_contexts import ORG_ID, PERSONAL_WORKSPACE_ID, USER_ID, WORKSPACE_ID
    from twobrain_rec_server.db.models import (
        Meeting,
        RecordingOriginCancellation,
        RegisteredDevice,
        UserIdentity,
        WorkspaceMembership,
    )

    other_user = uuid4() if other_namespace == "user" else USER_ID
    other_workspace = PERSONAL_WORKSPACE_ID if other_namespace == "workspace" else WORKSPACE_ID
    other_device = uuid4()
    other_headers = auth_headers() | {
        "X-User-Id": str(other_user),
        "X-Workspace-Id": str(other_workspace),
        "X-Device-Id": str(other_device),
    }

    async def seed_owner():
        async with client.app_state["sessionmaker"]() as db:
            assert db.bind.dialect.name == "postgresql"
            if other_namespace == "user":
                db.add(UserIdentity(
                    id=other_user, organization_id=ORG_ID,
                    external_subject=str(other_user), display_name="Synthetic owner",
                ))
                await db.flush()
                db.add(WorkspaceMembership(
                    workspace_id=other_workspace, user_id=other_user, role="member", status="active",
                ))
            db.add(RegisteredDevice(
                id=other_device, workspace_id=other_workspace, user_id=other_user,
                device_public_id=str(other_device), status="active",
            ))
            await db.commit()

    async def snapshot(origin):
        async with client.app_state["sessionmaker"]() as db:
            meetings = (await db.execute(select(
                Meeting.id, Meeting.workspace_id, Meeting.created_by_user_id,
                Meeting.deletion_state, Meeting.deletion_epoch,
            ).where(Meeting.local_recording_id == origin))).all()
            markers = (await db.execute(select(
                RecordingOriginCancellation.id, RecordingOriginCancellation.workspace_id,
                RecordingOriginCancellation.created_by_user_id,
            ).where(RecordingOriginCancellation.local_recording_id == origin))).all()
            return meetings, markers

    asyncio.run(seed_owner())
    origin = str(uuid4())
    created = create(client, origin, other_headers)
    assert created.status_code == 200
    meeting_id = UUID(created.json()["meeting_id"])
    initial_meetings, initial_markers = asyncio.run(snapshot(origin))
    assert initial_meetings == [(meeting_id, other_workspace, other_user, "none", 0)]
    assert initial_markers == []

    canceled = cancel(client, origin)
    assert canceled.status_code == 202
    receipt = canceled.json()
    assert receipt["receipt_type"] == "origin_cancellation"
    assert "meeting_id" not in receipt
    meetings, markers = asyncio.run(snapshot(origin))
    assert meetings == initial_meetings
    assert markers == [(UUID(receipt["request_id"]), WORKSPACE_ID, USER_ID)]

    late = create(client, origin)
    assert late.status_code == 409
    assert late.json()["code"] == "recording_deletion_active"
    repeated = create(client, origin, other_headers)
    assert repeated.status_code == 200
    assert repeated.json()["meeting_id"] == str(meeting_id)
    assert cancel(client, origin).json() == receipt
    assert asyncio.run(snapshot(origin)) == (initial_meetings, markers)

    other_canceled = cancel(client, origin, other_headers)
    assert other_canceled.status_code == 202
    other_receipt = other_canceled.json()
    assert other_receipt["receipt_type"] == "meeting_deletion"
    assert other_receipt["meeting_id"] == str(meeting_id)
    assert other_receipt["request_id"] != receipt["request_id"]
    assert cancel(client, origin).json() == receipt
    meetings, retained_markers = asyncio.run(snapshot(origin))
    assert len(meetings) == 1
    assert meetings[0][:3] == initial_meetings[0][:3]
    assert meetings[0].deletion_state != "none"
    assert meetings[0].deletion_epoch > 0
    assert retained_markers == markers

    absent_origin = str(uuid4())
    absent_receipts = []
    for headers in [auth_headers(), other_headers]:
        response = cancel(client, absent_origin, headers)
        assert response.status_code == 202
        absent_receipt = response.json()
        assert absent_receipt["receipt_type"] == "origin_cancellation"
        assert "meeting_id" not in absent_receipt
        absent_receipts.append(absent_receipt)
        late = create(client, absent_origin, headers)
        assert late.status_code == 409
        assert late.json()["code"] == "recording_deletion_active"
        assert cancel(client, absent_origin, headers).json() == absent_receipt
    assert absent_receipts[0]["request_id"] != absent_receipts[1]["request_id"]
    meetings, markers = asyncio.run(snapshot(absent_origin))
    assert meetings == []
    assert set(markers) == {
        (UUID(absent_receipts[0]["request_id"]), WORKSPACE_ID, USER_ID),
        (UUID(absent_receipts[1]["request_id"]), other_workspace, other_user),
    }


def test_concurrent_cancel_and_create_never_leave_live_recording(client):
    for _ in range(3):
        origin = str(uuid4())
        with ThreadPoolExecutor(max_workers=2) as pool:
            deleting = pool.submit(cancel, client, origin)
            creating = pool.submit(create, client, origin)
            receipt = deleting.result()
            creation = creating.result()
        assert receipt.status_code == 202
        assert creation.status_code in {200, 409}
        assert create(client, origin).status_code == 409
        assert cancel(client, origin).json() == receipt.json()


def test_cancellation_rls_is_owner_scoped_and_markers_cannot_be_removed(client):
    import asyncio
    from dataclasses import replace

    from sqlalchemy import delete, select, update
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from tests.fakes.auth_contexts import tenant_scope
    from tests.integration.test_rls_postgres_policies import _create_probe_role, _drop_probe_role
    from twobrain_rec_server.db.models import RecordingOriginCancellation
    from twobrain_rec_server.db.tenant_context import apply_tenant_scope
    from twobrain_rec_server.deletion.origin_cancellation import cancel_recording_origin

    origin = str(uuid4())
    assert cancel(client, origin).status_code == 202

    async def check():
        database_url = client.app.state.settings.database_url
        role, password = await _create_probe_role(database_url, role_name="graf_cancel_" + uuid4().hex[:12])
        engine = create_async_engine(make_url(database_url).set(username=role, password=password))
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                await apply_tenant_scope(db, tenant_scope())
                marker = await db.scalar(select(RecordingOriginCancellation))
                assert marker.local_recording_id == origin
                assert (await db.execute(delete(RecordingOriginCancellation))).rowcount == 0
                assert (await db.execute(update(RecordingOriginCancellation).values(local_recording_id="changed"))).rowcount == 0
                await db.commit()
                assert (await db.scalar(select(RecordingOriginCancellation))).local_recording_id == origin
                receipt = await cancel_recording_origin(
                    db, scope=tenant_scope(), local_recording_id=str(uuid4()),
                    confirmation_boundary=BOUNDED_DELETE_COPY,
                    storage=client.app_state["storage"], local_buffer_expiry_days=7,
                )
                await db.commit()
                audits = (await db.scalars(select(MeetingLifecycleAuditEvent))).all()
                assert len(audits) == 2
                audit = next(row for row in audits if row.metadata_json == {
                    "cancellation_id": str(receipt.request_id),
                })
                assert audit.actor_user_id == tenant_scope().user_id
                assert audit.device_id == tenant_scope().device_id
                assert audit.workspace_id == tenant_scope().workspace_id
                assert audit.meeting_id is None and audit.deletion_request_id is None
            for scope in [replace(tenant_scope(), user_id=uuid4()), replace(tenant_scope(), workspace_id=uuid4())]:
                async with async_sessionmaker(engine)() as db:
                    await apply_tenant_scope(db, scope)
                    assert await db.scalar(select(RecordingOriginCancellation)) is None
                    if scope.workspace_id != tenant_scope().workspace_id:
                        assert await db.scalar(select(MeetingLifecycleAuditEvent)) is None
        finally:
            await engine.dispose()
            await _drop_probe_role(database_url, role)

    asyncio.run(check())


def test_lifecycle_batch_returns_metadata_receipts_and_bounds_selection(client):
    origin = str(uuid4())
    canceled = cancel(client, origin).json()
    live_origin = str(uuid4())
    live = create(client, live_origin).json()
    missing = str(uuid4())
    response = client.post("/api/v1/desktop/recordings/lifecycle", headers=auth_headers(), json={
        "origins": [origin], "meeting_ids": [live["meeting_id"], missing],
    })
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    entries = response.json()
    assert entries[0]["state"] == "canceled_before_creation"
    assert entries[0]["receipt"] == canceled
    assert entries[1]["state"] == "allowed"
    assert entries[2]["state"] == "unavailable"
    assert entries[2]["meeting_id"] is None
    assert "Synthetic recording" not in response.text
    assert client.post("/api/v1/desktop/recordings/lifecycle", headers=auth_headers(), json={
        "origins": [str(uuid4()) for _ in range(101)],
    }).status_code == 422


def test_execution_scope_change_rejects_cancellation_before_any_mutation(client):
    origin = str(uuid4())
    blocked = client.post(
        f"/api/v1/desktop/recordings/{origin}/deletion-requests",
        headers=auth_headers() | {"X-Graf-Expected-Actor": str(uuid4()), "X-Graf-Expected-Workspace": str(uuid4())},
        json={"operation_id": str(uuid4()), "confirmation_boundary": BOUNDED_DELETE_COPY},
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "recording_scope_changed"
    assert create(client, origin).status_code == 200


def test_cancellation_rate_limit_retains_retry_after_and_does_not_cancel_origin(client, monkeypatch):
    from twobrain_rec_server.cabinet.access import SHARE_RATE_LIMITS
    monkeypatch.setitem(SHARE_RATE_LIMITS, "recording_deletion", (1, 60))
    assert cancel(client, str(uuid4())).status_code == 202
    origin = str(uuid4())
    blocked = cancel(client, origin)
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
    assert create(client, origin).status_code == 200


@pytest.mark.parametrize("first_action", ["create", "cancel"])
def test_origin_lock_orders_both_interleavings(client, monkeypatch, first_action):
    import importlib
    origins = importlib.import_module("twobrain_rec_server.deletion.origin_cancellation")
    meetings = importlib.import_module("twobrain_rec_server.ingest.meetings")
    original = origins.lock_recording_origin
    acquired, release, second_entered = Event(), Event(), Event()
    origin = str(uuid4())

    async def first_lock(db, scope, value):
        await original(db, scope, value)
        if value == origin:
            acquired.set()
            assert await asyncio.to_thread(release.wait, 10)

    async def second_lock(db, scope, value):
        if value == origin:
            second_entered.set()
        await original(db, scope, value)

    monkeypatch.setattr(meetings, "lock_recording_origin", first_lock if first_action == "create" else second_lock)
    monkeypatch.setattr(origins, "lock_recording_origin", first_lock if first_action == "cancel" else second_lock)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(create if first_action == "create" else cancel, client, origin)
        try:
            assert acquired.wait(10)
            second = pool.submit(cancel if first_action == "create" else create, client, origin)
            assert second_entered.wait(10)
            assert not second.done()
        finally:
            release.set()
        first_response, second_response = first.result(), second.result()
    deletion = first_response if first_action == "cancel" else second_response
    creation = first_response if first_action == "create" else second_response
    assert deletion.status_code == 202
    assert creation.status_code == (200 if first_action == "create" else 409)
    assert create(client, origin).status_code == 409
