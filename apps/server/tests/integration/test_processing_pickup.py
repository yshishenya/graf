import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

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
from twobrain_rec_server.billing.usage import moscow_window_for
from twobrain_rec_server.db.models import (
    AuthSessionDeviceBinding,
    FreeUsageWindow,
    ProcessingAuditEvent,
    ProcessingWorkflow,
    UsageReservation,
    WorkspaceSubscription,
)


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

    async def blocked_reason() -> str:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.scalar(
                select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == UUID(meeting_id))
            )
            assert workflow is not None
            return workflow.last_reason_code

    assert asyncio.run(blocked_reason()) == "blocked_free_processing_exhausted"


def test_processing_pickup_keeps_paid_processing_unlimited_without_reservation(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "pickup-paid-unlimited", duration_seconds=60)
    meeting_id = finalized["meeting"]["meeting_id"]
    media_revision_id = finalized["meeting"]["media_revision"]["media_revision_id"]

    async def seed_paid_subscription() -> None:
        async with client.app_state["sessionmaker"]() as db:
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

    async def reservation_count() -> int:
        async with client.app_state["sessionmaker"]() as db:
            return len(
                (
                    await db.scalars(
                        select(UsageReservation).where(
                            UsageReservation.idempotency_key == f"processing:{media_revision_id}"
                        )
                    )
                ).all()
            )

    assert asyncio.run(reservation_count()) == 0


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
    assert all(token not in serialized for token in {"transcript", "audio_download_url", "api_key", "signed_url"})


def test_processing_pickup_rejects_workspace_member(client) -> None:
    _seed_default_workspace_roles(client)
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "pickup-member-denied")
    meeting_id = finalized["meeting"]["meeting_id"]

    response = client.post(
        "/api/v1/internal/processing/pickup",
        headers=admin_auth_headers_for(user_id=DEFAULT_MEMBER_USER_ID, device_id=DEFAULT_MEMBER_DEVICE_ID),
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
        rows = await db.scalars(select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id))
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
