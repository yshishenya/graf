import pytest

from twobrain_rec_server.api.schemas import TrackDescriptor
from twobrain_rec_server.domain.statuses import TrackRole
from twobrain_rec_server.ingest.manifest import ManifestValidationError, validate_required_tracks


def descriptor(role: TrackRole) -> TrackDescriptor:
    return TrackDescriptor(
        track_role=role,
        codec="pcm_s16le",
        sample_rate_hz=48_000,
        channel_count=1,
        duration_seconds=60,
        byte_length=120,
        sha256="a" * 64,
    )


def test_required_tracks_accepts_manifest_microphone_and_system() -> None:
    validate_required_tracks(
        [
            descriptor(TrackRole.MANIFEST),
            descriptor(TrackRole.MICROPHONE),
            descriptor(TrackRole.SYSTEM),
        ]
    )


def test_required_tracks_accepts_optional_playback_candidate() -> None:
    validate_required_tracks(
        [
            descriptor(TrackRole.MANIFEST),
            descriptor(TrackRole.MICROPHONE),
            descriptor(TrackRole.SYSTEM),
            descriptor(TrackRole.PLAYBACK),
        ]
    )


def test_required_tracks_rejects_missing_system_track() -> None:
    with pytest.raises(ManifestValidationError):
        validate_required_tracks([descriptor(TrackRole.MANIFEST), descriptor(TrackRole.MICROPHONE)])


def test_required_tracks_accepts_manifest_and_media() -> None:
    validate_required_tracks(
        [
            descriptor(TrackRole.MANIFEST),
            descriptor(TrackRole.MEDIA),
        ]
    )


def test_required_tracks_rejects_mixed_single_and_dual_roles() -> None:
    with pytest.raises(ManifestValidationError):
        validate_required_tracks(
            [
                descriptor(TrackRole.MANIFEST),
                descriptor(TrackRole.MEDIA),
                descriptor(TrackRole.SYSTEM),
            ]
        )


def test_required_tracks_rejects_playback_on_manual_media_upload() -> None:
    with pytest.raises(ManifestValidationError):
        validate_required_tracks(
            [
                descriptor(TrackRole.MANIFEST),
                descriptor(TrackRole.MEDIA),
                descriptor(TrackRole.PLAYBACK),
            ]
        )
