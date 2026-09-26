from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import TrackDescriptor
from twobrain_rec_server.domain.statuses import MediaRevisionSourceKind, TrackRole

SINGLE_TRACK_FINALIZE_ROLES = {TrackRole.MANIFEST, TrackRole.MEDIA}
MIXED_RECORDING_V5_FINALIZE_ROLES = SINGLE_TRACK_FINALIZE_ROLES | {TrackRole.PLAYBACK}

MIXED_RECORDING_V5_DESCRIPTOR_CONTRACT = {
    TrackRole.MANIFEST: ("json", 1, 1),
    TrackRole.MEDIA: ("wav-pcm-s16le", 16_000, 1),
    TrackRole.PLAYBACK: ("m4a-aac-lc", 48_000, 1),
}


class ManifestValidationError(ValueError):
    pass


def _source_kind_value(source_kind: MediaRevisionSourceKind | str | None) -> str | None:
    if source_kind is None:
        return None
    return str(getattr(source_kind, "value", source_kind))


def _expected_roles_for_source_kind(source_kind: MediaRevisionSourceKind | str) -> set[TrackRole]:
    source_kind_value = _source_kind_value(source_kind)
    if source_kind_value == MediaRevisionSourceKind.INITIAL_MIXED_RECORDING.value:
        return MIXED_RECORDING_V5_FINALIZE_ROLES
    if source_kind_value == MediaRevisionSourceKind.MANUAL_UPLOAD.value:
        return SINGLE_TRACK_FINALIZE_ROLES
    if source_kind_value in {
        MediaRevisionSourceKind.LOCAL_TRIM.value,
        MediaRevisionSourceKind.REPLACE.value,
        MediaRevisionSourceKind.RESTORE.value,
        MediaRevisionSourceKind.REPROCESS.value,
        MediaRevisionSourceKind.VIDEO_CAPTURE.value,
    }:
        return SINGLE_TRACK_FINALIZE_ROLES
    raise ManifestValidationError("unsupported media revision source kind")


def ensure_supported_upload_source(
    source_kind: MediaRevisionSourceKind | str,
    roles: list[TrackRole] | None = None,
) -> None:
    """Admission only: historical values remain usable by readers and deletion."""
    if _source_kind_value(source_kind) == MediaRevisionSourceKind.INITIAL_RECORDING.value or (
        roles is not None and any(role in {TrackRole.MICROPHONE, TrackRole.SYSTEM} for role in roles)
    ):
        raise ProblemDetail(
            status=400, code="unsupported_recording_source_kind",
            title="Historical recording sources are read and delete only",
        )


def validate_required_track_roles(
    roles: set[TrackRole],
    *,
    source_kind: MediaRevisionSourceKind | str | None = None,
) -> None:
    source_kind_value = _source_kind_value(source_kind)
    if source_kind_value is not None:
        expected = _expected_roles_for_source_kind(source_kind_value)
        if roles == expected:
            return
        missing = expected - roles
        if missing:
            missing_names = ", ".join(sorted(role.value for role in missing))
            raise ManifestValidationError(f"missing required track roles: {missing_names}")
        role_names = ", ".join(sorted(role.value for role in roles))
        raise ManifestValidationError(f"invalid finalize track role combination: {role_names}")
    # Source-kind-less validation is retained for the manual single-file path.
    if roles == SINGLE_TRACK_FINALIZE_ROLES:
        return
    expected = SINGLE_TRACK_FINALIZE_ROLES
    missing = expected - roles
    if missing:
        missing_names = ", ".join(sorted(role.value for role in missing))
        raise ManifestValidationError(f"missing required track roles: {missing_names}")
    role_names = ", ".join(sorted(role.value for role in roles))
    raise ManifestValidationError(f"invalid finalize track role combination: {role_names}")


def validate_required_tracks(
    tracks: list[TrackDescriptor],
    *,
    source_kind: MediaRevisionSourceKind | str | None = None,
) -> None:
    validate_required_track_roles(
        {track.track_role for track in tracks},
        source_kind=source_kind,
    )
    if _source_kind_value(source_kind) != MediaRevisionSourceKind.INITIAL_MIXED_RECORDING.value:
        return
    for track in tracks:
        expected = MIXED_RECORDING_V5_DESCRIPTOR_CONTRACT[track.track_role]
        actual = (track.codec, track.sample_rate_hz, track.channel_count)
        if actual != expected:
            raise ManifestValidationError(
                "invalid v5 artifact descriptor for "
                f"{track.track_role.value}: expected {expected}, got {actual}"
            )
