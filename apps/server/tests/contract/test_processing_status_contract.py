import asyncio
from pathlib import Path
from uuid import UUID

import yaml
from sqlalchemy import select

import twobrain_rec_server.api.processing as processing_api
from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import create_finalized_meeting, enable_processing_autostart
from twobrain_rec_server.db.models import MediaScribeJob, ProcessingAuditEvent, ProcessingResult
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


def test_processing_status_projects_imported_no_speech_as_terminal_even_with_stale_workflow(client) -> None:
    finalized = create_finalized_meeting(client, "processing-status-no-speech")
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
                    failure_reason="no_recognizable_speech",
                )
            )
            await db.commit()

    asyncio.run(seed_no_speech_result())

    status = client.get(f"/api/v1/meetings/{meeting_id}/processing", headers=auth_headers())
    assert status.status_code == 200
    payload = status.json()
    assert payload["state"] == ProcessingStatus.FAILED_TERMINAL.value
    assert payload["retry_class"] == "terminal"
    assert payload["reason_code"] == "no_recognizable_speech"
    assert payload["manual_action"] == "new_attempt"


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
    assert body["state"] == ProcessingStatus.STARTING.value
    assert body["manual_action"] == "none"
    assert client.app.state.temporal_client is temporal
    assert len(temporal.starts) == 1

    status = client.get(
        f"/api/v1/meetings/{meeting_id}/processing",
        headers=auth_headers(),
    )
    assert status.status_code == 200
    payload = status.json()
    assert payload["attempt_ordinal"] == 2
    assert payload["state"] == ProcessingStatus.STARTING.value
    assert payload["attempt_in_flight"] is True


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
