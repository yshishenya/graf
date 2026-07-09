from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
from twobrain_rec_server.db.models import (
    Meeting,
    MeetingDeletionRequest,
    MeetingLifecycleAuditEvent,
    RetentionPolicySnapshot,
    WorkspaceMembership,
)
from twobrain_rec_server.domain.statuses import (
    DeletionState,
    ProcessingStatus,
    RetentionPolicyState,
)


def test_retention_scan_rejects_member_role(client) -> None:
    asyncio.run(_set_owner_role(client, "member"))
    seeded = asyncio.run(_seed_retention_matrix(client))

    response = client.post(
        "/api/v1/internal/retention/run",
        headers=auth_headers(),
        json={"limit": 20, "dry_run": False},
    )

    assert response.status_code == 403
    persisted = asyncio.run(_load_retention_results(client, seeded))
    assert persisted["requests_by_meeting"] == {}


def test_retention_scan_defaults_to_dry_run(client) -> None:
    seeded = asyncio.run(_seed_retention_matrix(client))

    response = client.post(
        "/api/v1/internal/retention/run",
        headers=auth_headers(),
        json={"limit": 20},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["evaluated"] == 7
    assert body["created_requests"] == 0
    assert body["skipped"] >= 5
    assert body["blocked"] >= 2
    assert body["policy_snapshot_id"] is not None

    persisted = asyncio.run(_load_retention_results(client, seeded))
    assert persisted["requests_by_meeting"] == {}


def test_retention_scan_owner_write_run_creates_requests_only_for_eligible_meetings(client) -> None:
    seeded = asyncio.run(_seed_retention_matrix(client))

    response = client.post(
        "/api/v1/internal/retention/run",
        headers=auth_headers(),
        json={"limit": 20, "dry_run": False},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["evaluated"] == 7
    assert body["created_requests"] == 1
    assert body["skipped"] >= 4
    assert body["blocked"] >= 2
    assert body["policy_snapshot_id"] is not None

    persisted = asyncio.run(_load_retention_results(client, seeded))
    eligible_request = persisted["requests_by_meeting"][seeded["eligible"]]
    assert eligible_request.request_source == "retention_job"
    assert eligible_request.reason_code == "retention_expired"
    assert str(eligible_request.policy_snapshot_id) == body["policy_snapshot_id"]
    assert persisted["meetings"][seeded["eligible"]].deletion_state == "deleting"
    assert persisted["meetings"][seeded["eligible"]].retention_policy_state == "expired"

    report = client.get(
        f"/api/v1/cabinet/meetings/{seeded['eligible']}/deletion-report",
        headers=auth_headers(),
    )
    assert report.status_code == 200
    artifact_classes = {row["artifact_class"] for row in report.json()["artifact_states"]}
    assert "retention_policy" in artifact_classes

    for key in ["future", "processing", "already_deleting", "already_deleted", "blocked", "unsafe"]:
        assert seeded[key] not in persisted["requests_by_meeting"]

    events = persisted["events_by_meeting"]
    assert events[seeded["future"]].safe_reason == "retention_window_pending"
    assert events[seeded["processing"]].safe_reason == "processing_active"
    assert events[seeded["already_deleting"]].safe_reason == "already_deleting_or_deleted"
    assert events[seeded["already_deleted"]].safe_reason == "already_deleting_or_deleted"
    assert events[seeded["blocked"]].outcome == "blocked"
    assert events[seeded["blocked"]].safe_reason == "policy_blocked"
    assert events[seeded["unsafe"]].outcome == "blocked"
    assert events[seeded["unsafe"]].safe_reason == "policy_unsafe"

    for event in events.values():
        assert set(event.metadata_json) <= {
            "state",
            "policy_source",
            "outcome",
            "safe_reason",
            "reason_code",
            "request_source",
        }
        assert "transcript" not in str(event.metadata_json).lower()
        assert "object" not in str(event.metadata_json).lower()
        assert "path" not in str(event.metadata_json).lower()


def test_retention_scan_fails_closed_when_policy_is_unsafe(client) -> None:
    client.app.state.settings.retention_meeting_delete_after_days = None
    seeded = asyncio.run(_seed_retention_matrix(client))

    response = client.post(
        "/api/v1/internal/retention/run",
        headers=auth_headers(),
        json={"limit": 20},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["evaluated"] == 0
    assert body["created_requests"] == 0
    assert body["blocked"] == 1
    assert body["policy_snapshot_id"] is not None

    persisted = asyncio.run(_load_retention_results(client, seeded))
    assert persisted["requests_by_meeting"] == {}
    assert persisted["snapshot"].unsafe_reason == "retention_policy_missing_or_unsafe"
    assert persisted["operator_event"].meeting_id is None
    assert persisted["operator_event"].outcome == "blocked"
    assert persisted["operator_event"].safe_reason == "retention_policy_missing_or_unsafe"


async def _set_owner_role(client, role: str) -> None:
    async with client.app_state["sessionmaker"]() as db:
        membership = await db.get(WorkspaceMembership, (WORKSPACE_ID, USER_ID))
        assert membership is not None
        membership.role = role
        await db.commit()


async def _seed_retention_matrix(client) -> dict[str, UUID]:
    now = datetime.now(UTC)
    cases = {
        "eligible": (now - timedelta(days=1), RetentionPolicyState.ACTIVE, ProcessingStatus.PROCESSED, DeletionState.NONE),
        "future": (now + timedelta(days=1), RetentionPolicyState.ACTIVE, ProcessingStatus.PROCESSED, DeletionState.NONE),
        "processing": (now - timedelta(days=1), RetentionPolicyState.ACTIVE, ProcessingStatus.PENDING_PROCESSING, DeletionState.NONE),
        "already_deleting": (now - timedelta(days=1), RetentionPolicyState.ACTIVE, ProcessingStatus.PROCESSED, DeletionState.DELETING),
        "already_deleted": (now - timedelta(days=1), RetentionPolicyState.ACTIVE, ProcessingStatus.PROCESSED, DeletionState.COMPLETE),
        "blocked": (now - timedelta(days=1), RetentionPolicyState.BLOCKED, ProcessingStatus.PROCESSED, DeletionState.NONE),
        "unsafe": (now - timedelta(days=1), RetentionPolicyState.UNSAFE, ProcessingStatus.PROCESSED, DeletionState.NONE),
    }
    ids = {
        name: UUID(f"51000000-0000-0000-0000-{index:012d}")
        for index, name in enumerate(cases, start=1)
    }
    async with client.app_state["sessionmaker"]() as db:
        for name, (delete_after, retention_state, processing_status, deletion_state) in cases.items():
            db.add(
                Meeting(
                    id=ids[name],
                    workspace_id=WORKSPACE_ID,
                    created_by_user_id=USER_ID,
                    device_id=DEVICE_ID,
                    local_recording_id=f"retention-{name}",
                    title=None,
                    started_at=now - timedelta(days=40),
                    duration_seconds=1800,
                    status="ingested_pending_processing",
                    processing_status=processing_status.value,
                    deletion_state=deletion_state.value,
                    retention_delete_after=delete_after,
                    retention_policy_state=retention_state.value,
                )
            )
        await db.commit()
    return ids


async def _load_retention_results(client, meeting_ids: dict[str, UUID]) -> dict[str, object]:
    async with client.app_state["sessionmaker"]() as db:
        meetings = {
            meeting_id: await db.get(Meeting, meeting_id)
            for meeting_id in meeting_ids.values()
        }
        requests = (
            await db.scalars(
                select(MeetingDeletionRequest).where(MeetingDeletionRequest.workspace_id == WORKSPACE_ID)
            )
        ).all()
        events = (
            await db.scalars(
                select(MeetingLifecycleAuditEvent)
                .where(MeetingLifecycleAuditEvent.workspace_id == WORKSPACE_ID)
                .order_by(MeetingLifecycleAuditEvent.created_at.asc())
            )
        ).all()
        snapshot = await db.scalar(
            select(RetentionPolicySnapshot)
            .where(RetentionPolicySnapshot.workspace_id == WORKSPACE_ID)
            .order_by(RetentionPolicySnapshot.created_at.desc())
        )
        return {
            "meetings": meetings,
            "requests_by_meeting": {
                request.meeting_id: request
                for request in requests
                if request.request_source == "retention_job"
            },
            "events_by_meeting": {
                event.meeting_id: event
                for event in events
                if event.event_type == "retention_evaluated" and event.meeting_id is not None
            },
            "operator_event": next(
                (
                    event
                    for event in events
                    if event.event_type == "retention_policy_blocked"
                    and event.meeting_id is None
                ),
                None,
            ),
            "snapshot": snapshot,
        }
