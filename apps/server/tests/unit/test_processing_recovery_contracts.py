from datetime import UTC, datetime, timedelta

import pytest

from twobrain_rec_server.config import Settings
from twobrain_rec_server.mediascribe.downloads import (
    normalize_download_reference,
    safe_download_references,
)
from twobrain_rec_server.mediascribe.schemas import (
    MediaScribeDeletionResponse,
    MediaScribeProvenance,
    MediaScribeResult,
)
from twobrain_rec_server.processing.audit import validate_processing_aggregate_event
from twobrain_rec_server.processing.deletion import reconcile_deletion_response
from twobrain_rec_server.processing.recovery import schedule_retry_with_settings
from twobrain_rec_server.processing.store import _safe_provenance_projection


def test_processing_recovery_settings_are_bounded_and_ordered() -> None:
    settings = Settings()
    assert settings.processing_recovery_min_delay_seconds == 5
    assert settings.processing_recovery_default_delay_seconds == 30
    assert settings.processing_recovery_max_delay_seconds == 900
    schedule = schedule_retry_with_settings(
        settings,
        now=datetime(2026, 8, 24, tzinfo=UTC),
        retry_count=0,
        generation=0,
        retry_after=timedelta(seconds=40),
    )
    assert schedule.next_attempt_at is not None
    assert schedule.next_attempt_at > datetime(2026, 8, 24, tzinfo=UTC)


def test_enabled_processing_requires_diarization() -> None:
    with pytest.raises(ValueError, match="requires MediaScribe diarization"):
        Settings(processing_enabled=True, mediascribe_diarize=False)


@pytest.mark.parametrize(
    "overrides",
    [
        {"processing_recovery_min_delay_seconds": 31},
        {"processing_recovery_default_delay_seconds": 901},
        {"processing_recovery_jitter_ratio": 0.3},
    ],
)
def test_processing_recovery_settings_reject_unsafe_values(overrides: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        Settings(**overrides)


def test_provider_download_references_drop_signed_urls_and_unknown_artifacts() -> None:
    safe_path = "/v1/audio/transcriptions/job_fixture/downloads/transcript"
    assert normalize_download_reference(safe_path) == safe_path
    assert normalize_download_reference("https://provider.test/signed?token=secret") is None
    assert normalize_download_reference(f"{safe_path}?signature=secret") is None
    assert safe_download_references(
        {
            "transcript": safe_path,
            "summary": "/v1/audio/transcriptions/job_fixture/downloads/summary",
            "secret": "https://provider.test/signed?token=secret",
        }
    ) == {"transcript": safe_path, "summary": "/v1/audio/transcriptions/job_fixture/downloads/summary"}


def test_deletion_202_is_pending_until_provider_receipt() -> None:
    pending = MediaScribeDeletionResponse(
        id="receipt-1",
        state="cancelling",
        deleted=False,
        requested_at="2026-08-24T00:00:00Z",
        status_url="/v1/audio/transcriptions/job/deletion",
        retry_after_seconds=20,
    )
    completed = pending.model_copy(update={"state": "completed", "deleted": True})
    assert reconcile_deletion_response(pending).confirmed is False
    assert reconcile_deletion_response(pending).next_retry_seconds == 20
    assert reconcile_deletion_response(completed).confirmed is True


def test_processing_analytics_envelope_is_allowlisted_and_content_free() -> None:
    event = validate_processing_aggregate_event(
        event_name="processing_retry_scheduled",
        window="hour",
        window_started_at="2026-08-24T00:00:00Z",
        window_ended_at="2026-08-24T01:00:00Z",
        surface="server",
        count=2,
        dimensions={
            "retry_reason": "transport",
            "schedule_source": "server_fallback",
            "delay_bucket": "30s_2m",
            "retry_count_bucket": "first",
        },
    )
    assert event["schema_version"] == 1
    assert "meeting_id" not in event
    with pytest.raises(ValueError):
        validate_processing_aggregate_event(
            event_name="processing_retry_scheduled",
            window="hour",
            window_started_at="2026-08-24T00:00:00Z",
            window_ended_at="2026-08-24T01:00:00Z",
            surface="server",
            count=1,
            dimensions={"retry_reason": "raw provider detail"},
        )


def test_durable_provenance_ignores_provider_extras_and_content() -> None:
    result = MediaScribeResult(
        external_job_id="job-fixture",
        provenance=MediaScribeProvenance(
            service_version="service-1",
            quality_reasons=["low_confidence", "private transcript text"],
            future_provider_payload={"transcript": "private transcript text"},
            effective_diarization_parameters={
                "num_speakers": 2,
                "raw": {"transcript": "private transcript text"},
            },
        ),
    )
    projection = _safe_provenance_projection(result)
    assert projection == {
        "service_version": "service-1",
        "quality_reasons": ["low_confidence"],
        "effective_diarization_parameters": {"num_speakers": 2},
    }
    assert "future_provider_payload" not in projection
