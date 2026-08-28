import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
import yaml
from sqlalchemy import select

import twobrain_rec_server.api.processing as processing_api
from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import create_finalized_meeting, enable_processing_autostart
from twobrain_rec_server.billing.catalog import FREE_PROCESSING_SECONDS
from twobrain_rec_server.billing.usage import moscow_window_for
from twobrain_rec_server.db.models import (
    FreeUsageWindow,
    MediaScribeJob,
    ProcessingAuditEvent,
    ProcessingResult,
    ProcessingWorkflow,
)
from twobrain_rec_server.domain.statuses import (
    MediaScribeJobStatus,
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
    ProcessingStatus,
    SummaryStatus,
)
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.audit import safe_audit_metadata

ROOT = Path(__file__).parents[4]


def test_attribution_diagnostics_allow_only_bounded_metadata() -> None:
    metadata = safe_audit_metadata(
        {
            "provider_job_id": "job_safe_42",
            "raw_turn_count": 3,
            "accepted_turn_count": 0,
            "multi_label_conflict_count": 1,
            "unknown_tiny_count": 1,
            "duplicate_text_count": 3,
            "text_conservation_status": "mismatched",
            "source_result_hash": "a" * 64,
            "transcript_text": "must not persist",
            "provider_payload": {"private": True},
            "signed_url": "https://example.test/private",
        }
    )

    assert metadata == {
        "provider_job_id": "job_safe_42",
        "raw_turn_count": 3,
        "accepted_turn_count": 0,
        "multi_label_conflict_count": 1,
        "unknown_tiny_count": 1,
        "duplicate_text_count": 3,
        "text_conservation_status": "mismatched",
        "source_result_hash": "a" * 64,
    }


def test_attribution_reason_codes_require_the_fixed_allowlist() -> None:
    allowed = safe_audit_metadata(
        {"reason_codes": ["invalid_provider_timing", "text_conservation_mismatch"]}
    )
    rejected = safe_audit_metadata(
        {"reason_codes": ["invalid_provider_timing", "private meeting content"]}
    )

    assert allowed == {
        "reason_codes": ["invalid_provider_timing", "text_conservation_mismatch"]
    }
    assert rejected == {}


def test_processing_status_openapi_contract_has_content_safe_fields() -> None:
    contract = yaml.safe_load(
        (ROOT / "specs/015-mediascribe-processing-pipeline/contracts/processing-status.openapi.yaml").read_text(
            encoding="utf-8"
        )
    )
    properties = contract["components"]["schemas"]["ProcessingStatusResponse"]["properties"]
    assert "transcript_available" in properties
    assert "diarization_available" in properties
    assert "workflow_id" in properties
    assert "transcript_text" not in properties
    assert "audio_download_url" not in properties
    assert "mediascribe_api_key" not in properties


def test_processing_status_endpoint_returns_no_content_or_secret_fields(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "processing-status-contract")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    pickup = client.post(
        "/api/v1/internal/processing/pickup",
        headers=auth_headers(),
        json={"meeting_id": str(meeting_id)},
    )
    assert pickup.status_code == 202
    status = client.get(f"/api/v1/meetings/{meeting_id}/processing", headers=auth_headers())
    assert status.status_code == 200
    assert status.headers["cache-control"] == "private, no-store"
    assert status.headers["pragma"] == "no-cache"
    payload = status.json()
    assert payload["meeting_id"] == str(meeting_id)
    assert payload["workflow_id"] == f"processing/{media_revision_id}"
    assert payload["mediascribe_job_id_present"] is False
    forbidden = {"transcript_text", "audio_download_url", "mediascribe_job_id", "api_key", "signed_url"}
    assert forbidden.isdisjoint(payload)


def test_processing_status_endpoint_requires_rows_for_content_availability(client) -> None:
    finalized = create_finalized_meeting(client, "processing-status-empty-available")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def seed_empty_available_result() -> None:
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
                external_job_id="job_empty_available",
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
                    result_version=1,
                    status=ProcessingResultStatus.IMPORTED.value,
                    processing_workflow_id=workflow.id,
                    transcript_status=ProcessingAvailabilityStatus.AVAILABLE.value,
                    diarization_status=ProcessingAvailabilityStatus.AVAILABLE.value,
                    summary_status=SummaryStatus.NOT_REQUESTED.value,
                    segment_count=0,
                    diarization_segment_count=0,
                )
            )
            await db.commit()

    asyncio.run(seed_empty_available_result())

    status = client.get(f"/api/v1/meetings/{meeting_id}/processing", headers=auth_headers())
    assert status.status_code == 200
    payload = status.json()
    assert payload["transcript_available"] is False
    assert payload["diarization_available"] is False
    assert payload["content_available"] is False


@pytest.mark.parametrize("stale_retry_class", ["none", "retryable"])
def test_processed_result_without_diarization_is_terminal_and_does_not_poll(
    client,
    stale_retry_class: str,
) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(
        client,
        f"processing-status-missing-diarization-{stale_retry_class}",
    )
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def seed_incomplete_result() -> None:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.PROCESSED,
            )
            workflow.retry_class = stale_retry_class
            job = MediaScribeJob(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                processing_workflow_id=workflow.id,
                external_job_id="job_missing_diarization",
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
                    result_version=1,
                    status=ProcessingResultStatus.IMPORTED.value,
                    processing_workflow_id=workflow.id,
                    transcript_status=ProcessingAvailabilityStatus.AVAILABLE.value,
                    diarization_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
                    summary_status=SummaryStatus.NOT_REQUESTED.value,
                    segment_count=1,
                    diarization_segment_count=0,
                    failure_reason="mediascribe_malformed_response",
                )
            )
            await db.commit()

    asyncio.run(seed_incomplete_result())

    response = client.get(f"/api/v1/meetings/{meeting_id}/processing", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == ProcessingStatus.FAILED_TERMINAL.value
    assert payload["retry_class"] == "terminal"
    assert payload["manual_action"] == "new_attempt"
    assert payload["attempt_in_flight"] is False
    assert payload["transcript_available"] is False
    assert payload["artifacts"]["transcript"] == {"state": "unavailable", "visible": False}
    assert payload["artifacts"]["diarization"] == {"state": "unavailable", "visible": False}

    detail = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}",
        headers=auth_headers(),
    )
    assert detail.status_code == 200
    assert detail.json()["processing"]["state"] == "failed"
    listed = client.get(
        "/api/v1/cabinet/meetings",
        params={"q": f"processing-status-missing-diarization-{stale_retry_class}"},
        headers=auth_headers(),
    )
    assert listed.status_code == 200
    assert listed.json()["items"][0]["status"] == "failed"

    attempt = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/attempt",
        headers=auth_headers(),
    )
    assert attempt.status_code == 202
    assert attempt.json()["attempt_result"] == "created"


def test_exhausted_processing_limit_offers_a_later_new_attempt(client) -> None:
    client.app.state.temporal_client = FakeTemporalClient()
    finalized = create_finalized_meeting(client, "processing-status-quota-exhausted")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def seed_terminal_workflow() -> None:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.FAILED_TERMINAL,
            )
            workflow.last_reason_code = "blocked_free_processing_exhausted"
            workflow.retry_class = "terminal"
            workflow.ended_at = datetime.now(UTC)
            db.add(
                MediaScribeJob(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=media_revision_id,
                    processing_workflow_id=workflow.id,
                    external_job_id="job_quota_ready_result",
                    status=MediaScribeJobStatus.READY.value,
                )
            )
            window_start, window_end = moscow_window_for(datetime.now(UTC))
            db.add(
                FreeUsageWindow(
                    workspace_id=workspace_id,
                    window_start=window_start,
                    window_end=window_end,
                    included_seconds=FREE_PROCESSING_SECONDS,
                    committed_seconds=FREE_PROCESSING_SECONDS,
                )
            )
            await db.commit()

    asyncio.run(seed_terminal_workflow())
    response = client.get(f"/api/v1/meetings/{meeting_id}/processing", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == ProcessingStatus.FAILED_TERMINAL.value
    assert payload["reason_code"] == "blocked_free_processing_exhausted"
    assert payload["manual_action"] == "new_attempt"

    exhausted = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/attempt",
        headers=auth_headers(),
    )
    assert exhausted.status_code == 409
    assert exhausted.json()["code"] == "processing_quota_exceeded"

    async def restore_limit() -> None:
        async with client.app_state["sessionmaker"]() as db:
            window = await db.scalar(
                select(FreeUsageWindow).where(FreeUsageWindow.workspace_id == workspace_id)
            )
            assert window is not None
            window.committed_seconds = 0
            await db.commit()

    asyncio.run(restore_limit())
    created = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/attempt",
        headers=auth_headers(),
    )
    assert created.status_code == 202
    assert created.json()["attempt_result"] == "created"
    assert created.json()["attempt_ordinal"] == 2

    async def same_provider_job_is_reused() -> tuple[int, str, bool]:
        async with client.app_state["sessionmaker"]() as db:
            jobs = list(
                await db.scalars(
                    select(MediaScribeJob).where(MediaScribeJob.meeting_id == meeting_id)
                )
            )
            latest_workflow = await db.scalar(
                select(ProcessingWorkflow)
                .where(ProcessingWorkflow.meeting_id == meeting_id)
                .order_by(ProcessingWorkflow.attempt_ordinal.desc())
            )
            assert latest_workflow is not None
            return (
                len(jobs),
                jobs[0].external_job_id or "",
                jobs[0].processing_workflow_id == latest_workflow.id,
            )

    assert asyncio.run(same_provider_job_is_reused()) == (
        1,
        "job_quota_ready_result",
        True,
    )


def test_expired_manual_check_claim_reopens_same_job_action(client) -> None:
    finalized = create_finalized_meeting(client, "processing-status-expired-manual-claim")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def seed_expired_claim() -> None:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.POLLING,
            )
            workflow.retry_class = "retryable"
            workflow.last_reason_code = "manual_processing_check"
            workflow.manual_claimed_at = datetime.now(UTC) - timedelta(minutes=3)
            workflow.manual_claimed_by = "user"
            db.add(
                MediaScribeJob(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=media_revision_id,
                    processing_workflow_id=workflow.id,
                    external_job_id="job_expired_manual_claim",
                    status=MediaScribeJobStatus.TRANSCRIBING.value,
                )
            )
            await db.commit()

    asyncio.run(seed_expired_claim())

    response = client.get(f"/api/v1/meetings/{meeting_id}/processing", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["attempt_in_flight"] is False
    assert payload["manual_action"] == "check_now"
    assert payload["next_attempt_at"] is None


def test_processing_status_ignores_historical_retry_class_after_processed_result(client) -> None:
    finalized = create_finalized_meeting(client, "processing-status-clears-stale-retry")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def seed_processed_result() -> None:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.PROCESSED,
            )
            workflow.retry_class = "retryable"
            job = MediaScribeJob(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                processing_workflow_id=workflow.id,
                external_job_id="job_processed_after_retry",
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

    asyncio.run(seed_processed_result())

    status = client.get(f"/api/v1/meetings/{meeting_id}/processing", headers=auth_headers())
    assert status.status_code == 200
    payload = status.json()
    assert payload["state"] == ProcessingStatus.PROCESSED.value
    assert payload["retry_class"] == "none"
    assert payload["manual_action"] == "none"
    assert payload["transcript_available"] is True
    assert payload["diarization_available"] is True


@pytest.mark.parametrize(
    ("failure_reason", "failure_source"),
    [
        ("no_recognizable_speech", None),
        ("invalid_audio_payload", "input_audio"),
    ],
)
def test_processing_status_projects_imported_terminal_input_even_with_stale_workflow(
    client,
    failure_reason: str,
    failure_source: str | None,
) -> None:
    finalized = create_finalized_meeting(client, f"processing-status-{failure_reason}")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def seed_no_speech_result() -> None:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.POLLING,
            )
            job = MediaScribeJob(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                processing_workflow_id=workflow.id,
                external_job_id="job_no_speech",
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
                    transcript_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
                    diarization_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
                    summary_status=SummaryStatus.NOT_REQUESTED.value,
                    segment_count=0,
                    diarization_segment_count=0,
                    failure_reason=failure_reason,
                    failure_source=failure_source,
                )
            )
            await db.commit()

    asyncio.run(seed_no_speech_result())

    status = client.get(f"/api/v1/meetings/{meeting_id}/processing", headers=auth_headers())
    assert status.status_code == 200
    payload = status.json()
    assert payload["state"] == ProcessingStatus.FAILED_TERMINAL.value
    assert payload["retry_class"] == "terminal"
    assert payload["reason_code"] == failure_reason
    assert payload["manual_action"] == (
        "upload_another" if failure_reason == "invalid_audio_payload" else "new_attempt"
    )


def test_no_speech_new_attempt_lazily_connects_temporal_and_projects_as_active(client, monkeypatch) -> None:
    temporal = FakeTemporalClient()

    async def connect_temporal(_settings):
        return temporal

    monkeypatch.setattr(processing_api, "connect_temporal_client", connect_temporal)
    finalized = create_finalized_meeting(client, "processing-status-no-speech-retry")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def seed_no_speech_result() -> None:
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
                external_job_id="job_no_speech_retry",
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
                    transcript_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
                    diarization_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
                    summary_status=SummaryStatus.NOT_REQUESTED.value,
                    segment_count=0,
                    diarization_segment_count=0,
                    failure_reason="no_recognizable_speech",
                )
            )
            await db.commit()

    asyncio.run(seed_no_speech_result())

    attempt = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/attempt",
        headers=auth_headers(),
    )
    assert attempt.status_code == 202
    body = attempt.json()
    assert body["attempt_result"] == "created"
    assert body["attempt_ordinal"] == 2
    assert body["attempt_in_flight"] is True
    assert body["state"] == ProcessingStatus.WORKFLOW_STARTED.value
    assert body["manual_action"] == "none"
    assert body["artifacts"]["transcript"]["state"] == "processing"
    assert body["artifacts"]["diarization"]["state"] == "processing"
    assert client.app.state.temporal_client is temporal
    assert len(temporal.starts) == 1

    status = client.get(
        f"/api/v1/meetings/{meeting_id}/processing",
        headers=auth_headers(),
    )
    assert status.status_code == 200
    payload = status.json()
    assert payload["attempt_ordinal"] == 2
    assert payload["state"] == ProcessingStatus.WORKFLOW_STARTED.value
    assert payload["attempt_in_flight"] is True
    assert payload["artifacts"]["transcript"]["state"] == "processing"
    assert payload["artifacts"]["diarization"]["state"] == "processing"


def test_expired_transient_source_requires_a_new_upload(client) -> None:
    finalized = create_finalized_meeting(
        client,
        "processing-status-expired-source",
        archive_audio=False,
    )
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def seed_expired_terminal_result() -> None:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.FAILED_TERMINAL,
                archive_audio=False,
            )
            workflow.transient_hard_deadline = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()

    asyncio.run(seed_expired_terminal_result())

    response = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/attempt",
        headers=auth_headers(),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "processing_source_expired"
    assert response.json()["detail"] == "Срок временного хранения записи истёк. Загрузите файл заново."


def test_manual_check_releases_claim_when_temporal_connect_is_cancelled(client, monkeypatch) -> None:
    finalized = create_finalized_meeting(client, "processing-status-cancelled-check")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])
    media_revision_id = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace_id = UUID(finalized["meeting"]["workspace_id"])

    async def seed_polling_job() -> None:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await store.upsert_processing_workflow(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
                workflow_id=f"processing/{media_revision_id}",
                status=ProcessingStatus.WAITING_RETRY,
            )
            db.add(
                MediaScribeJob(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=media_revision_id,
                    processing_workflow_id=workflow.id,
                    external_job_id="job_cancelled_check",
                    status=MediaScribeJobStatus.SUBMITTED.value,
                )
            )
            await db.commit()

    asyncio.run(seed_polling_job())

    async def cancelled_temporal(_request):
        raise asyncio.CancelledError

    monkeypatch.setattr(processing_api, "_get_temporal_client", cancelled_temporal)
    with pytest.raises(RuntimeError, match="No response returned"):
        client.post(
            f"/api/v1/meetings/{meeting_id}/processing/check",
            headers=auth_headers(),
            json={},
        )

    async def load_workflow() -> tuple[str, object | None, object | None]:
        async with client.app_state["sessionmaker"]() as db:
            workflow = await db.scalar(
                select(ProcessingWorkflow).where(
                    ProcessingWorkflow.meeting_id == meeting_id,
                    ProcessingWorkflow.workspace_id == workspace_id,
                )
            )
            assert workflow is not None
            return workflow.status, workflow.manual_claimed_at, workflow.manual_claimed_by

    assert asyncio.run(load_workflow()) == (
        ProcessingStatus.WAITING_RETRY.value,
        None,
        None,
    )


def test_finalize_autostart_audit_metadata_is_content_safe(client) -> None:
    enable_processing_autostart(client, FakeTemporalClient())
    finalized = create_finalized_meeting(client, "processing-autostart-audit")
    meeting_id = UUID(finalized["meeting"]["meeting_id"])

    async def audit_metadata() -> dict[str, object]:
        async with client.app_state["sessionmaker"]() as db:
            event = await db.scalar(
                select(ProcessingAuditEvent)
                .where(
                    ProcessingAuditEvent.meeting_id == meeting_id,
                    ProcessingAuditEvent.event_type == "workflow_started",
                )
                .order_by(ProcessingAuditEvent.created_at.desc())
            )
            assert event is not None
            return event.metadata_json

    metadata = asyncio.run(audit_metadata())
    assert set(metadata) <= {"workflow_id", "started_count"}
    serialized = str(metadata).lower()
    forbidden = {"transcript", "audio_download_url", "api_key", "signed_url", "/users/"}
    assert all(token not in serialized for token in forbidden)
