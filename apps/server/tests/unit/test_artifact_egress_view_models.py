from datetime import UTC, datetime
from uuid import uuid4

from twobrain_rec_server.api.schemas import ArtifactEgressState
from twobrain_rec_server.cabinet.egress import _is_stored_review_m4a
from twobrain_rec_server.cabinet.view_models import governance_summary
from twobrain_rec_server.db.models import PlaybackNormalizationJob, TrackArtifact
from twobrain_rec_server.normalization.statuses import (
    CANONICAL_PROFILE_VERSION,
    VALIDATION_VERSION,
)


def test_review_audio_gate_requires_matching_ready_job_and_validation_bundle() -> None:
    workspace_id = uuid4()
    meeting_id = uuid4()
    revision_id = uuid4()
    artifact = TrackArtifact(
        id=uuid4(),
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=revision_id,
        track_role="playback",
        codec="m4a-aac-lc",
        sample_rate_hz=48_000,
        channel_count=1,
        duration_seconds=60,
        byte_length=512_000,
        sha256="a" * 64,
        storage_object_key="private/canonical.m4a",
        status="stored",
        normalization_profile_version=CANONICAL_PROFILE_VERSION,
        validated_at=datetime.now(UTC),
        derivation_kind="dual_source_mix_transcode",
        source_fingerprint_sha256="b" * 64,
        validation_version=VALIDATION_VERSION,
    )
    job = PlaybackNormalizationJob(
        id=uuid4(),
        organization_id=uuid4(),
        workspace_id=workspace_id,
        requested_by_user_id=uuid4(),
        source_device_id=uuid4(),
        meeting_id=meeting_id,
        media_revision_id=revision_id,
        profile_version=CANONICAL_PROFILE_VERSION,
        validation_version=VALIDATION_VERSION,
        trigger_kind="finalize",
        priority_class="new_ingest",
        source_kind="initial_recording",
        source_fingerprint_sha256="b" * 64,
        planned_action="normalize_source",
        state="ready",
        workflow_id=f"playback-normalization/{revision_id}/v1",
        canonical_track_artifact_id=artifact.id,
        ready_at=datetime.now(UTC),
    )

    assert _is_stored_review_m4a(artifact, job=job) is True

    artifact.status = "candidate"
    assert _is_stored_review_m4a(artifact, job=job) is False


def test_governance_enables_download_and_export_from_available_artifact_states() -> None:
    governance = governance_summary(
        artifacts=[
            ArtifactEgressState(
                artifact_class="transcript",
                state="available",
                label="Download transcript",
                reason="allowed",
                action="download",
            ),
            ArtifactEgressState(
                artifact_class="package",
                state="available",
                label="Export package",
                reason="allowed",
                action="export",
            ),
        ]
    )

    assert governance.share.state == "available"
    assert governance.download.state == "available"
    assert governance.export.state == "available"


def test_governance_keeps_download_and_export_disabled_without_available_artifacts() -> None:
    governance = governance_summary(
        artifacts=[
            ArtifactEgressState(
                artifact_class="audio",
                state="policy_blocked",
                label="Disabled by policy",
                reason="blocked",
                action="disabled",
            )
        ]
    )

    assert governance.download.state == "disabled"
    assert governance.export.state == "disabled"
