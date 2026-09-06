from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.cabinet_access import (
    add_workspace_user,
    auth_headers_for,
    set_retained_audio_source_status,
)
from tests.fixtures.processing import create_finalized_meeting
from tests.integration.test_cabinet_csrf import (
    OWNER_REVIEW_TEST_TOKEN,
    _seed_owner_review_session,
)
from twobrain_rec_server.api import processing as processing_api
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.db.models import (
    MediaScribeJob,
    ProcessingResult,
    ProcessingWorkflow,
    UsageReservation,
)
from twobrain_rec_server.domain.statuses import (
    MediaScribeJobStatus,
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
    ProcessingStatus,
    SummaryStatus,
    TrackRole,
)
from twobrain_rec_server.processing import store


async def _seed_complete_result(
    client,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID,
) -> str:
    async with client.app_state["sessionmaker"]() as db:
        workflow = await store.upsert_processing_workflow(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
            workflow_id=f"processing/{media_revision_id}",
            status=ProcessingStatus.PROCESSED,
        )
        job = MediaScribeJob(
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
            processing_workflow_id=workflow.id,
            external_job_id="job_reprocess_ready",
            status=MediaScribeJobStatus.READY.value,
        )
        db.add(job)
        await db.flush()
        db.add(
            ProcessingResult(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                mediascribe_job_id=job.id,
                processing_workflow_id=workflow.id,
                result_version=1,
                status=ProcessingResultStatus.IMPORTED.value,
                transcript_status=ProcessingAvailabilityStatus.AVAILABLE.value,
                diarization_status=ProcessingAvailabilityStatus.AVAILABLE.value,
                summary_status=SummaryStatus.NOT_REQUESTED.value,
                segment_count=1,
                diarization_segment_count=1,
            )
        )
        await db.commit()
        return workflow.workflow_id


def test_owner_reprocess_creates_one_successor_and_replays_lost_response(client) -> None:
    temporal = FakeTemporalClient()
    client.app.state.temporal_client = temporal
    finalized = create_finalized_meeting(client, "owner-reprocess-cas")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    predecessor_id = asyncio.run(
        _seed_complete_result(
            client,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
        )
    )
    payload = {
        "expected_workflow_id": predecessor_id,
        "expected_media_revision_id": str(media_revision_id),
    }

    created = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/reprocess",
        headers=auth_headers(),
        json=payload,
    )
    async def seed_successor_provider_job() -> str:
        async with client.app_state["sessionmaker"]() as db:
            successor = await db.scalar(
                select(ProcessingWorkflow).where(
                    ProcessingWorkflow.workspace_id == workspace_id,
                    ProcessingWorkflow.meeting_id == meeting_id,
                    ProcessingWorkflow.attempt_ordinal == 2,
                )
            )
            assert successor is not None
            db.add(
                MediaScribeJob(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=media_revision_id,
                    processing_workflow_id=successor.id,
                    idempotency_key=f"processing:{successor.id}",
                    external_job_id="job_reprocess_successor",
                    status=MediaScribeJobStatus.SUBMITTED.value,
                )
            )
            await db.commit()
            return successor.workflow_id

    assert created.status_code == 202
    successor_id = asyncio.run(seed_successor_provider_job())
    replayed = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/reprocess",
        headers=auth_headers(),
        json=payload,
    )
    coalesced = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/reprocess",
        headers=auth_headers(),
        json={
            "expected_workflow_id": successor_id,
            "expected_media_revision_id": str(media_revision_id),
        },
    )

    assert created.json()["request_result"] == "created"
    assert created.json()["attempt_ordinal"] == 2
    assert replayed.status_code == 202
    assert replayed.json()["request_result"] == "replayed"
    assert replayed.json()["workflow_id"] == created.json()["workflow_id"]
    assert coalesced.status_code == 202
    assert coalesced.json()["request_result"] == "already_in_flight"
    assert coalesced.json()["workflow_id"] == created.json()["workflow_id"]
    assert len(temporal.starts) == 1

    async def counts() -> tuple[int, int, int]:
        async with client.app_state["sessionmaker"]() as db:
            workflow_count = await db.scalar(
                select(func.count(ProcessingWorkflow.id)).where(
                    ProcessingWorkflow.workspace_id == workspace_id,
                    ProcessingWorkflow.meeting_id == meeting_id,
                )
            )
            reservation_count = await db.scalar(
                select(func.count(UsageReservation.id)).where(
                    UsageReservation.workspace_id == workspace_id,
                    UsageReservation.idempotency_key == f"processing:{media_revision_id}",
                )
            )
            provider_job_count = await db.scalar(
                select(func.count(MediaScribeJob.id)).where(
                    MediaScribeJob.workspace_id == workspace_id,
                    MediaScribeJob.meeting_id == meeting_id,
                )
            )
            return (
                int(workflow_count or 0),
                int(reservation_count or 0),
                int(provider_job_count or 0),
            )

    assert asyncio.run(counts()) == (2, 1, 2)


def test_reprocess_temporal_failure_does_not_promise_automatic_resume(
    client, monkeypatch
) -> None:
    async def unavailable_temporal(_settings):
        raise RuntimeError("synthetic temporal outage")

    monkeypatch.setattr(processing_api, "connect_temporal_client", unavailable_temporal)
    client.app.state.temporal_client = None
    finalized = create_finalized_meeting(client, "owner-reprocess-temporal-unavailable")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    predecessor_id = asyncio.run(
        _seed_complete_result(
            client,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
        )
    )

    response = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/reprocess",
        headers=auth_headers(),
        json={
            "expected_workflow_id": predecessor_id,
            "expected_media_revision_id": str(media_revision_id),
        },
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "автоматически" not in detail
    assert "повторите действие позже" in detail


def test_reprocess_rejects_non_owner_and_stale_revision(client) -> None:
    finalized = create_finalized_meeting(client, "owner-reprocess-trust-boundary")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    predecessor_id = asyncio.run(
        _seed_complete_result(
            client,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
        )
    )
    add_workspace_user(client)

    non_owner = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/reprocess",
        headers=auth_headers_for(),
        json={
            "expected_workflow_id": predecessor_id,
            "expected_media_revision_id": str(media_revision_id),
        },
    )
    stale_revision = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/reprocess",
        headers=auth_headers(),
        json={
            "expected_workflow_id": predecessor_id,
            "expected_media_revision_id": str(uuid4()),
        },
    )

    assert non_owner.status_code == 404
    assert non_owner.json()["code"] == "meeting_not_found"
    assert stale_revision.status_code == 409
    assert stale_revision.json()["code"] == "stale_meeting_view"


def test_predecessor_older_than_one_successor_is_stale(client) -> None:
    temporal = FakeTemporalClient()
    client.app.state.temporal_client = temporal
    finalized = create_finalized_meeting(client, "owner-reprocess-stale-predecessor")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    predecessor_id = asyncio.run(
        _seed_complete_result(
            client,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
        )
    )
    payload = {
        "expected_workflow_id": predecessor_id,
        "expected_media_revision_id": str(media_revision_id),
    }
    assert (
        client.post(
            f"/api/v1/meetings/{meeting_id}/processing/reprocess",
            headers=auth_headers(),
            json=payload,
        ).status_code
        == 202
    )

    async def seed_later_attempt() -> None:
        async with client.app_state["sessionmaker"]() as db:
            successor = await db.scalar(
                select(ProcessingWorkflow).where(
                    ProcessingWorkflow.workspace_id == workspace_id,
                    ProcessingWorkflow.meeting_id == meeting_id,
                    ProcessingWorkflow.attempt_ordinal == 2,
                )
            )
            assert successor is not None
            successor.status = ProcessingStatus.CANCELED.value
            db.add(
                ProcessingWorkflow(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=media_revision_id,
                    workflow_id=f"processing/{media_revision_id}/3",
                    purpose="transcription",
                    source_fingerprint=successor.source_fingerprint,
                    deletion_epoch_at_start=successor.deletion_epoch_at_start,
                    status=ProcessingStatus.FAILED_TERMINAL.value,
                    attempt_ordinal=3,
                    archive_audio=successor.archive_audio,
                )
            )
            await db.commit()

    asyncio.run(seed_later_attempt())
    stale = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/reprocess",
        headers=auth_headers(),
        json=payload,
    )

    assert stale.status_code == 409
    assert stale.json()["code"] == "stale_meeting_view"
    assert len(temporal.starts) == 1


def test_terminal_replacement_allows_one_fresh_successor(client) -> None:
    temporal = FakeTemporalClient()
    client.app.state.temporal_client = temporal
    finalized = create_finalized_meeting(client, "owner-reprocess-terminal-successor")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    predecessor_id = asyncio.run(
        _seed_complete_result(
            client,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
        )
    )
    first = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/reprocess",
        headers=auth_headers(),
        json={
            "expected_workflow_id": predecessor_id,
            "expected_media_revision_id": str(media_revision_id),
        },
    )
    assert first.status_code == 202

    async def fail_replacement() -> None:
        async with client.app_state["sessionmaker"]() as db:
            replacement = await db.scalar(
                select(ProcessingWorkflow).where(
                    ProcessingWorkflow.workspace_id == workspace_id,
                    ProcessingWorkflow.meeting_id == meeting_id,
                    ProcessingWorkflow.attempt_ordinal == 2,
                )
            )
            assert replacement is not None
            replacement.status = ProcessingStatus.FAILED_TERMINAL.value
            replacement.retry_class = "terminal"
            replacement.ended_at = datetime.now(UTC)
            await db.commit()

    asyncio.run(fail_replacement())
    second = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/reprocess",
        headers=auth_headers(),
        json={
            "expected_workflow_id": first.json()["workflow_id"],
            "expected_media_revision_id": str(media_revision_id),
        },
    )

    assert second.status_code == 202
    assert second.json()["request_result"] == "created"
    assert second.json()["attempt_ordinal"] == 3
    assert second.json()["workflow_id"] != first.json()["workflow_id"]
    assert len(temporal.starts) == 2


def test_reprocess_rejects_missing_retained_source(client) -> None:
    finalized = create_finalized_meeting(client, "owner-reprocess-missing-source")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    predecessor_id = asyncio.run(
        _seed_complete_result(
            client,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
        )
    )
    set_retained_audio_source_status(client, meeting_id, TrackRole.MICROPHONE, "purged")
    set_retained_audio_source_status(client, meeting_id, TrackRole.SYSTEM, "purged")

    response = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/reprocess",
        headers=auth_headers(),
        json={
            "expected_workflow_id": predecessor_id,
            "expected_media_revision_id": str(media_revision_id),
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "processing_source_unavailable"


def test_cookie_authenticated_reprocess_requires_csrf_token(client) -> None:
    finalized = create_finalized_meeting(client, "owner-reprocess-csrf")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])
    predecessor_id = asyncio.run(
        _seed_complete_result(
            client,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
        )
    )
    client.portal.call(_seed_owner_review_session, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)

    response = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/reprocess",
        json={
            "expected_workflow_id": predecessor_id,
            "expected_media_revision_id": str(media_revision_id),
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "csrf_token_missing"
