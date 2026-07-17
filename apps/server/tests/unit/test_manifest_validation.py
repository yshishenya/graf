import pytest

from twobrain_rec_server.api.schemas import TrackDescriptor
from twobrain_rec_server.domain.statuses import MediaRevisionSourceKind, TrackRole
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


def test_v5_mixed_recording_requires_exact_media_and_playback_roles() -> None:
    validate_required_tracks(
        [
            TrackDescriptor(
                track_role=TrackRole.MANIFEST,
                codec="json",
                sample_rate_hz=1,
                channel_count=1,
                duration_seconds=1,
                byte_length=120,
                sha256="a" * 64,
            ),
            TrackDescriptor(
                track_role=TrackRole.MEDIA,
                codec="wav-pcm-s16le",
                sample_rate_hz=16_000,
                channel_count=1,
                duration_seconds=60,
                byte_length=1_024,
                sha256="b" * 64,
            ),
            TrackDescriptor(
                track_role=TrackRole.PLAYBACK,
                codec="m4a-aac-lc",
                sample_rate_hz=48_000,
                channel_count=1,
                duration_seconds=60,
                byte_length=2_048,
                sha256="c" * 64,
            ),
        ],
        source_kind=MediaRevisionSourceKind.INITIAL_MIXED_RECORDING,
    )


@pytest.mark.parametrize(
    "track_role,codec,sample_rate_hz,channel_count",
    [
        (TrackRole.MEDIA, "pcm_s16le", 16_000, 1),
        (TrackRole.MEDIA, "wav-pcm-s16le", 48_000, 1),
        (TrackRole.PLAYBACK, "m4a-aac-lc", 48_000, 2),
    ],
)
def test_v5_mixed_recording_rejects_wrong_artifact_descriptor(
    track_role: TrackRole,
    codec: str,
    sample_rate_hz: int,
    channel_count: int,
) -> None:
    tracks = [
        TrackDescriptor(
            track_role=TrackRole.MANIFEST,
            codec="json",
            sample_rate_hz=1,
            channel_count=1,
            duration_seconds=1,
            byte_length=120,
            sha256="a" * 64,
        ),
        TrackDescriptor(
            track_role=TrackRole.MEDIA,
            codec="wav-pcm-s16le",
            sample_rate_hz=16_000,
            channel_count=1,
            duration_seconds=60,
            byte_length=1_024,
            sha256="b" * 64,
        ),
        TrackDescriptor(
            track_role=TrackRole.PLAYBACK,
            codec="m4a-aac-lc",
            sample_rate_hz=48_000,
            channel_count=1,
            duration_seconds=60,
            byte_length=2_048,
            sha256="c" * 64,
        ),
    ]
    index = next(index for index, track in enumerate(tracks) if track.track_role == track_role)
    tracks[index] = TrackDescriptor(
        track_role=track_role,
        codec=codec,
        sample_rate_hz=sample_rate_hz,
        channel_count=channel_count,
        duration_seconds=tracks[index].duration_seconds,
        byte_length=tracks[index].byte_length,
        sha256=tracks[index].sha256,
    )

    with pytest.raises(ManifestValidationError):
        validate_required_tracks(tracks, source_kind=MediaRevisionSourceKind.INITIAL_MIXED_RECORDING)
