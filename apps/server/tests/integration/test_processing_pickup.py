import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.admin import (
    DEFAULT_MEMBER_DEVICE_ID,
    DEFAULT_MEMBER_USER_ID,
    seed_default_workspace_admin_roles,
)
from tests.fixtures.admin import (
    auth_headers_for as admin_auth_headers_for,
)
from tests.fixtures.processing import create_finalized_meeting, enable_processing_autostart
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.sessions import issue_auth_session
from twobrain_rec_server.billing.catalog import FREE_PROCESSING_SECONDS
from twobrain_rec_server.billing.usage import (
    QuotaExceeded,
    moscow_window_for,
    release_free_usage,
    reserve_free_usage,
)
from twobrain_rec_server.db.models import (
    AuthSessionDeviceBinding,
    FreeUsageWindow,
    MediaScribeJob,
    ProcessingAuditEvent,
    ProcessingWorkflow,
    UsageReservation,
    WorkspaceSubscription,
)
from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.processing import pickup as pickup_module
from twobrain_rec_server.processing import store


def test_processing_pickup_starts_workflow_and_reuses_duplicate(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "pickup-start")
    meeting_id = finalized["meeting"]["meeting_id"]
    media_revision_id = finalized["meeting"]["media_revision"]["media_revision_id"]

    first = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": meeting_id},
    )
    assert first.status_code == 202
    assert first.json()["started_count"] == 1
    assert first.json()["reused_count"] == 0

    second = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": meeting_id},
    )
    assert second.status_code == 202
    assert second.json()["started_count"] == 0
    assert second.json()["reused_count"] == 1

    async def workflow_count() -> tuple[int, str]:
        async with client.app_state["sessionmaker"]() as db:
            rows = (await db.scalars(select(ProcessingWorkflow))).all()
            return len(rows), rows[0].workflow_id

    count, workflow_id = asyncio.run(workflow_count())
    assert count == 1
    assert workflow_id == f"processing/{media_revision_id}"


def test_processing_pickup_without_temporal_blocks_safely(client) -> None:
    finalized = create_finalized_meeting(client, "pickup-no-temporal")
    meeting_id = finalized["meeting"]["meeting_id"]
    response = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": meeting_id},
    )
    assert response.status_code == 202
    assert response.json()["blocked_count"] == 1

    async def reason_code() -> str | None:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == UUID(meeting_id))
            )
            assert workflow is not None
            return workflow.last_reason_code

    assert asyncio.run(reason_code()) == "blocked_temporal_unavailable"


def test_processing_pickup_reserves_free_seconds_before_temporal(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "pickup-free-reservation", duration_seconds=60)
    meeting_id = finalized["meeting"]["meeting_id"]
    media_revision_id = finalized["meeting"]["media_revision"]["media_revision_id"]

    response = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": meeting_id},
    )
    assert response.status_code == 202
    assert response.json()["started_count"] == 1

    async def reservation_state() -> tuple[str, int, int]:
        async with client.app_state["sessionmaker"]() as db:
            row = await db.scalar(
                select(UsageReservation).where(
                    UsageReservation.workspace_id == WORKSPACE_ID,
                    UsageReservation.idempotency_key == f"processing:{media_revision_id}",
                )
            )
            assert row is not None
            return row.state, row.declared_seconds, row.committed_seconds

    assert asyncio.run(reservation_state()) == ("active", 60, 0)


def test_processing_pickup_blocks_free_job_when_window_is_exhausted(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "pickup-free-exhausted", duration_seconds=60)
    meeting_id = finalized["meeting"]["meeting_id"]
    now = datetime.now(UTC)
    window_start, window_end = moscow_window_for(now)

    async def seed_exhausted_window() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                FreeUsageWindow(
                    workspace_id=WORKSPACE_ID,
                    window_start=window_start,
                    window_end=window_end,
                    included_seconds=FREE_PROCESSING_SECONDS,
                    committed_seconds=FREE_PROCESSING_SECONDS,
                )
            )
            await db.commit()

    asyncio.run(seed_exhausted_window())
    response = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": meeting_id},
    )
    assert response.status_code == 202
    assert response.json()["blocked_count"] == 1

    async def blocked_state() -> tuple[str, str]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == UUID(meeting_id))
            )
            assert workflow is not None
            return workflow.status, workflow.last_reason_code

    assert asyncio.run(blocked_state()) == (
        ProcessingStatus.BLOCKED.value,
        "blocked_free_processing_exhausted",
    )
    status = client.get(
        f"/api/v1/meetings/{meeting_id}/processing",
        headers=auth_headers(),
    )
    assert status.status_code == 200
    assert status.json()["manual_action"] == "new_attempt"

    async def restore_limit() -> None:
        async with client.app_state["sessionmaker"]() as db:
            window = await db.scalar(
                select(FreeUsageWindow).where(FreeUsageWindow.workspace_id == WORKSPACE_ID)
            )
            assert window is not None
            window.committed_seconds = 0
            await db.commit()

    asyncio.run(restore_limit())
    attempt = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/attempt",
        headers=auth_headers(),
    )
    assert attempt.status_code == 202
    assert attempt.json()["attempt_result"] == "created"


def test_usage_reservation_rebinds_to_new_moscow_month(client) -> None:
    before_boundary = datetime(2026, 1, 31, 20, 59, tzinfo=UTC)
    after_boundary = datetime(2026, 1, 31, 21, 1, tzinfo=UTC)
    reservation_key = "processing:moscow-month-rebind"

    async def rebind() -> tuple[object, object, object, object, int, int]:
        async with client.app_state["sessionmaker"]() as db:
            original = await reserve_free_usage(
                db,
                workspace_id=WORKSPACE_ID,
                reservation_key=reservation_key,
                declared_seconds=60,
                now=before_boundary,
            )
            original_window_id = original.window_id
            await db.commit()

            rebound = await reserve_free_usage(
                db,
                workspace_id=WORKSPACE_ID,
                reservation_key=reservation_key,
                declared_seconds=60,
                now=after_boundary,
            )
            await db.commit()
            old_window = await db.get(FreeUsageWindow, original_window_id)
            new_window = await db.get(FreeUsageWindow, rebound.window_id)
            assert old_window is not None and new_window is not None
            return (
                original.id,
                rebound.id,
                original_window_id,
                rebound.window_id,
                old_window.reserved_seconds,
                new_window.reserved_seconds,
            )

    original_id, reservation_id, old_window_id, new_window_id, old_reserved, new_reserved = (
        asyncio.run(rebind())
    )
    assert reservation_id == original_id
    assert old_window_id != new_window_id
    assert old_reserved == 0
    assert new_reserved == 60


def test_usage_reservation_month_rebind_rechecks_current_window_quota(client) -> None:
    before_boundary = datetime(2026, 1, 31, 20, 59, tzinfo=UTC)
    after_boundary = datetime(2026, 1, 31, 21, 1, tzinfo=UTC)
    reservation_key = "processing:moscow-month-over-quota"

    async def reject_rebind() -> tuple[object, object, object, str]:
        async with client.app_state["sessionmaker"]() as db:
            original = await reserve_free_usage(
                db,
                workspace_id=WORKSPACE_ID,
                reservation_key=reservation_key,
                declared_seconds=60,
                now=before_boundary,
            )
            original_window_id = original.window_id
            current_start, current_end = moscow_window_for(after_boundary)
            db.add(
                FreeUsageWindow(
                    workspace_id=WORKSPACE_ID,
                    window_start=current_start,
                    window_end=current_end,
                    included_seconds=FREE_PROCESSING_SECONDS,
                    committed_seconds=FREE_PROCESSING_SECONDS,
                )
            )
            await db.commit()

            with pytest.raises(QuotaExceeded, match="quota is exhausted"):
                await reserve_free_usage(
                    db,
                    workspace_id=WORKSPACE_ID,
                    reservation_key=reservation_key,
                    declared_seconds=60,
                    now=after_boundary,
                )
            persisted = await db.scalar(
                select(UsageReservation).where(
                    UsageReservation.workspace_id == WORKSPACE_ID,
                    UsageReservation.idempotency_key == reservation_key,
                )
            )
            assert persisted is not None
            return persisted.id, original_window_id, persisted.window_id, persisted.state

    reservation_id, original_window_id, window_id, state = asyncio.run(reject_rebind())
    assert reservation_id is not None
    assert window_id == original_window_id
    assert state == "active"


def test_stale_start_intent_rebinds_reservation_to_current_window(client) -> None:
    temporal = FakeTemporalClient()
    client.app.state.temporal_client = temporal
    finalized = create_finalized_meeting(client, "pickup-stale-free-exhausted", duration_seconds=60)
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    now = datetime.now(UTC)
    window_start, window_end = moscow_window_for(now - timedelta(days=31))

    async def seed_stale_intent_and_exhausted_window() -> None:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.STARTING,
            )
            workflow.updated_at = now - timedelta(minutes=2)
            window = FreeUsageWindow(
                workspace_id=WORKSPACE_ID,
                window_start=window_start,
                window_end=window_end,
                included_seconds=FREE_PROCESSING_SECONDS,
                committed_seconds=FREE_PROCESSING_SECONDS,
            )
            db.add(window)
            await db.flush()
            db.add(
                UsageReservation(
                    workspace_id=WORKSPACE_ID,
                    window_id=window.id,
                    idempotency_key=f"processing:{media_revision_id}",
                    declared_seconds=60,
                    state="released",
                )
            )
            await db.commit()

    asyncio.run(seed_stale_intent_and_exhausted_window())
    response = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": str(meeting_id)},
    )

    assert response.status_code == 202
    assert response.json()["started_count"] == 1
    assert response.json()["blocked_count"] == 0
    assert len(temporal.starts) == 1


def test_stale_start_reconciliation_records_scalar_audit_after_rollback(
    client,
    monkeypatch,
) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "pickup-stale-start-rollback-scalars")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])

    async def seed_stale_start() -> tuple[UUID, str]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.STARTING,
            )
            workflow.updated_at = datetime.now(UTC) - timedelta(minutes=2)
            await db.commit()
            return workflow.id, workflow.workflow_id

    workflow_id, temporal_workflow_id = asyncio.run(seed_stale_start())

    async def fail_start(**_kwargs):
        raise RuntimeError("temporal start unavailable")

    monkeypatch.setattr(pickup_module, "start_processing_workflow", fail_start)
    response = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": str(meeting_id)},
    )

    assert response.status_code == 202
    assert response.json()["reused_count"] == 1

    async def audit_metadata() -> tuple[UUID | None, dict[str, object]]:
        async with client.app_state["sessionmaker"]() as db:
            event = await db.scalar(
                select(ProcessingAuditEvent).where(
                    ProcessingAuditEvent.processing_workflow_id == workflow_id,
                    ProcessingAuditEvent.event_type == "workflow_start_reconciliation_deferred",
                )
            )
            assert event is not None
            return event.meeting_id, event.metadata_json

    audit_meeting_id, metadata = asyncio.run(audit_metadata())
    assert audit_meeting_id == meeting_id
    assert metadata == {
        "workflow_id": temporal_workflow_id,
        "reason_code": "temporal_start_reconciliation_unavailable",
    }


def test_processing_pickup_keeps_paid_processing_unlimited_without_reservation(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "pickup-paid-unlimited", duration_seconds=60)
    meeting_id = finalized["meeting"]["meeting_id"]
    media_revision_id = finalized["meeting"]["media_revision"]["media_revision_id"]

    async def seed_paid_subscription() -> None:
        async with client.app_state["sessionmaker"]() as db:
            now = datetime.now(UTC)
            reservation = await reserve_free_usage(
                db,
                workspace_id=WORKSPACE_ID,
                reservation_key=f"processing:{media_revision_id}",
                declared_seconds=60,
                now=now,
                expires_at=now + timedelta(hours=24),
            )
            await release_free_usage(db, reservation_id=reservation.id)
            db.add(
                WorkspaceSubscription(
                    workspace_id=WORKSPACE_ID,
                    state="personal",
                    plan_code="personal",
                    paid_through=datetime.now(UTC) + timedelta(days=30),
                    capacity_bytes=2_000_000_000,
                )
            )
            await db.commit()

    asyncio.run(seed_paid_subscription())
    response = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": meeting_id},
    )
    assert response.status_code == 202
    assert response.json()["started_count"] == 1

    async def commit_usage_with_released_reservation() -> tuple[int, str]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == UUID(meeting_id))
            )
            assert workflow is not None
            job = MediaScribeJob(
                workspace_id=WORKSPACE_ID,
                meeting_id=UUID(meeting_id),
                media_revision_id=UUID(media_revision_id),
                processing_workflow_id=workflow.id,
                idempotency_key=f"paid-released-reservation:{media_revision_id}",
                source_fingerprint=workflow.source_fingerprint,
            )
            db.add(job)
            await db.flush()
            committed = await store._commit_processing_usage(
                db,
                job=job,
                transcript=[SimpleNamespace(start_seconds=0, end_seconds=1)],
            )
            reservation = await db.scalar(
                select(UsageReservation).where(
                    UsageReservation.idempotency_key == f"processing:{media_revision_id}"
                )
            )
            assert reservation is not None
            return committed, reservation.state

    assert asyncio.run(commit_usage_with_released_reservation()) == (0, "released")


def test_processing_pickup_reopens_blocked_workflow_after_temporal_recovers(client) -> None:
    finalized = create_finalized_meeting(client, "pickup-temporal-recovery")
    meeting_id = finalized["meeting"]["meeting_id"]
    first = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": meeting_id},
    )
    assert first.status_code == 202
    client.app.state.temporal_client = FakeTemporalClient()

    second = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": meeting_id},
    )
    assert second.status_code == 202
    assert second.json()["started_count"] == 1

    async def workflow_status() -> str:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == UUID(meeting_id))
            )
            assert workflow is not None
            return workflow.status

    assert asyncio.run(workflow_status()) == "workflow_started"


def test_processing_pickup_reuses_workflow_started_by_finalize_autostart(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    enable_processing_autostart(client, client.app.state.temporal_client)
    finalized = create_finalized_meeting(client, "pickup-after-finalize-autostart")
    meeting_id = finalized["meeting"]["meeting_id"]

    response = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": meeting_id},
    )

    assert response.status_code == 202
    assert response.json()["started_count"] == 0
    assert response.json()["reused_count"] == 1

    async def reuse_audit_metadata() -> dict[str, object]:
        async with client.app_state["sessionmaker"]() as db:
            event = await db.scalar(
                select(ProcessingAuditEvent)
                .where(
                    ProcessingAuditEvent.meeting_id == UUID(meeting_id),
                    ProcessingAuditEvent.event_type == "workflow_duplicate_reused",
                )
                .order_by(ProcessingAuditEvent.created_at.desc())
            )
            assert event is not None
            return event.metadata_json

    metadata = asyncio.run(reuse_audit_metadata())
    assert set(metadata) <= {"workflow_id", "reason_code"}
    assert metadata["reason_code"] == "duplicate_workflow_reused"
    serialized = str(metadata).lower()
    assert all(
        token not in serialized
        for token in {"transcript", "audio_download_url", "api_key", "signed_url"}
    )


@pytest.mark.parametrize(
    "waiting_status",
    [ProcessingStatus.WAITING_RETRY, ProcessingStatus.BLOCKED_UNKNOWN],
)
def test_processing_pickup_reuses_existing_durable_wait(client, waiting_status) -> None:
    temporal = FakeTemporalClient()
    client.app.state.temporal_client = temporal
    finalized = create_finalized_meeting(client, f"pickup-{waiting_status.value}")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])

    async def seed_wait() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await store.upsert_processing_workflow(
                db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=waiting_status,
            )

    asyncio.run(seed_wait())
    response = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": str(meeting_id)},
    )

    assert response.status_code == 202
    assert response.json()["started_count"] == 0
    assert response.json()["reused_count"] == 1
    assert temporal.starts == {}

    async def workflow_states() -> list[str]:
        async with client.app_state["sessionmaker"]() as db:
            workflows = list(
                await db.scalars(
                    select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id)
                )
            )
            return [workflow.status for workflow in workflows]

    assert asyncio.run(workflow_states()) == [waiting_status.value]


def test_processing_pickup_rejects_workspace_member(client) -> None:
    _seed_default_workspace_roles(client)
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "pickup-member-denied")
    meeting_id = finalized["meeting"]["meeting_id"]

    response = client.post(
        "/api/v1/internal/processing/pickup",
        headers=admin_auth_headers_for(
            user_id=DEFAULT_MEMBER_USER_ID, device_id=DEFAULT_MEMBER_DEVICE_ID
        ),
        json={"meeting_id": meeting_id},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "admin_forbidden"
    assert asyncio.run(_workflow_count(client, UUID(meeting_id))) == 0


def test_processing_pickup_rejects_browser_cookie_without_csrf(client) -> None:
    finalized = create_finalized_meeting(client, "pickup-cookie-csrf")
    meeting_id = finalized["meeting"]["meeting_id"]

    session_cookie = client.portal.call(_issue_owner_session_token, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, session_cookie)

    response = client.post(
        "/api/v1/internal/processing/pickup",
        json={"meeting_id": meeting_id},
    )

    client.cookies.clear()
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_token_missing"
    assert asyncio.run(_workflow_count(client, UUID(meeting_id))) == 0


def test_processing_pickup_rejects_cookie_with_blank_session_header_without_csrf(client) -> None:
    finalized = create_finalized_meeting(client, "pickup-cookie-blank-session-header-csrf")
    meeting_id = finalized["meeting"]["meeting_id"]

    session_cookie = client.portal.call(_issue_owner_session_token, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, session_cookie)

    response = client.post(
        "/api/v1/internal/processing/pickup",
        headers={"X-Auth-Session": "   "},
        json={"meeting_id": meeting_id},
    )

    client.cookies.clear()
    assert response.status_code == 403
    assert response.json()["code"] == "csrf_token_missing"
    assert asyncio.run(_workflow_count(client, UUID(meeting_id))) == 0


def test_processing_pickup_accepts_bearer_session_without_csrf(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "pickup-bearer-session")
    meeting_id = finalized["meeting"]["meeting_id"]

    session_token = client.portal.call(_issue_owner_session_token, client)

    response = client.post(
        "/api/v1/internal/processing/pickup",
        headers={"Authorization": f"Bearer {session_token}"},
        json={"meeting_id": meeting_id},
    )

    assert response.status_code == 202
    assert response.json()["started_count"] == 1
    assert asyncio.run(_workflow_count(client, UUID(meeting_id))) == 1


async def _workflow_count(client, meeting_id: UUID) -> int:
    async with client.app_state["sessionmaker"]() as db:
        rows = await db.scalars(
            select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id)
        )
        return len(rows.all())


async def _issue_owner_session_token(client) -> str:
    async with client.app_state["sessionmaker"]() as db:
        issued = await issue_auth_session(
            db,
            user_id=USER_ID,
            workspace_id=WORKSPACE_ID,
            device_id=DEVICE_ID,
            provider="email",
            now=datetime.now(UTC),
        )
        db.add(
            AuthSessionDeviceBinding(
                auth_session_id=issued.id,
                registered_device_id=DEVICE_ID,
                device_state="trusted",
                last_heartbeat_at=datetime.now(UTC),
            )
        )
        await db.commit()
        return issued.token


def _seed_default_workspace_roles(client) -> None:
    async def seed() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await seed_default_workspace_admin_roles(db)

    asyncio.run(seed())
