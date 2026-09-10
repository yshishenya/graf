import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest

from tests.contract.test_ingest_openapi_contract import auth_headers
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY


def cancel(client, origin):
    return client.post(
        f"/api/v1/desktop/recordings/{origin}/deletion-requests",
        headers=auth_headers(),
        json={"operation_id": str(uuid4()), "confirmation_boundary": BOUNDED_DELETE_COPY},
    )


def create(client, origin):
    return client.post("/api/v1/meetings", headers=auth_headers(), json={
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


def test_cancel_existing_origin_uses_meeting_deletion_receipt(client):
    origin = str(uuid4())
    created = create(client, origin)
    assert created.status_code == 200
    deleted = cancel(client, origin)
    assert deleted.status_code == 202
    assert deleted.json()["receipt_type"] == "meeting_deletion"
    assert deleted.json()["meeting_id"] == created.json()["meeting_id"]
    assert cancel(client, origin).json() == deleted.json()


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
            for scope in [replace(tenant_scope(), user_id=uuid4()), replace(tenant_scope(), workspace_id=uuid4())]:
                async with async_sessionmaker(engine)() as db:
                    await apply_tenant_scope(db, scope)
                    assert await db.scalar(select(RecordingOriginCancellation)) is None
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
