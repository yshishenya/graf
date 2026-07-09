from uuid import uuid4

from twobrain_rec_server.cabinet.access import AccessDecision
from twobrain_rec_server.cabinet.egress import _transcript_state, safe_audit_metadata
from twobrain_rec_server.db.models import ProcessingResult
from twobrain_rec_server.domain.statuses import ProcessingAvailabilityStatus, ProcessingResultStatus


def test_safe_audit_metadata_keeps_only_allowed_redacted_scalars() -> None:
    metadata = safe_audit_metadata(
        {
            "artifact_class": "transcript",
            "byte_length": 123,
            "storage_object_key": "private/object/key",
            "share_token_hash": "private-token-hash",
            "nested": {"secret": "value"},
        }
    )

    assert metadata == {"artifact_class": "transcript", "byte_length": 123}


def test_safe_audit_metadata_for_playback_keeps_source_mode_without_private_audio_fields() -> None:
    metadata = safe_audit_metadata(
        {
            "artifact_class": "audio",
            "request_class": "playback",
            "source_mode": "combined_review_stream",
            "byte_length": 456,
            "storage_object_key": "private/object/key",
            "sha256": "private-hash",
            "raw_audio": "private samples",
            "transcript_text": "private transcript",
        }
    )

    assert metadata == {
        "artifact_class": "audio",
        "request_class": "playback",
        "source_mode": "combined_review_stream",
        "byte_length": 456,
    }


def test_safe_audit_metadata_for_playback_range_denial_drops_private_headers() -> None:
    metadata = safe_audit_metadata(
        {
            "artifact_class": "audio",
            "request_class": "playback",
            "outcome": "denied",
            "policy_reason": "playback_range_not_satisfiable",
            "range_header": "bytes=999999-1000000",
            "authorization": "Bearer private-token",
            "storage_object_key": "private/object/key",
            "raw_audio": "private samples",
        }
    )

    assert metadata == {
        "artifact_class": "audio",
        "request_class": "playback",
        "outcome": "denied",
        "policy_reason": "playback_range_not_satisfiable",
    }


def test_transcript_download_state_requires_available_status_and_segments() -> None:
    access = AccessDecision(
        state="owner",
        label="Owner",
        reason=None,
        can_view=True,
        can_share=True,
        can_manage_team_visibility=True,
        can_download=True,
        can_export=True,
    )
    result = ProcessingResult(
        id=uuid4(),
        meeting_id=uuid4(),
        workspace_id=uuid4(),
        mediascribe_job_id=uuid4(),
        status=ProcessingResultStatus.IMPORTED.value,
        transcript_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
        segment_count=0,
    )

    state = _transcript_state("allowed", access, result)

    assert state.artifact_class == "transcript"
    assert state.state == "missing"
    assert state.action == "disabled"
