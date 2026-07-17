from twobrain_rec_server.api.schemas import TrackDescriptor
from twobrain_rec_server.domain.statuses import MediaRevisionSourceKind, TrackRole

# These role sets are intentionally limited to immutable pre-v5 records. New
# first-party capture declares INITIAL_MIXED_RECORDING and must take the v5
# canonical-media branch below.
HISTORICAL_DUAL_FINALIZE_ROLES = {TrackRole.MANIFEST, TrackRole.MICROPHONE, TrackRole.SYSTEM}
HISTORICAL_DUAL_WITH_PLAYBACK_FINALIZE_ROLES = HISTORICAL_DUAL_FINALIZE_ROLES | {TrackRole.PLAYBACK}
SINGLE_TRACK_FINALIZE_ROLES = {TrackRole.MANIFEST, TrackRole.MEDIA}
MIXED_RECORDING_V5_FINALIZE_ROLES = SINGLE_TRACK_FINALIZE_ROLES | {TrackRole.PLAYBACK}
VALID_FINALIZE_ROLE_SETS = (
    HISTORICAL_DUAL_FINALIZE_ROLES,
    HISTORICAL_DUAL_WITH_PLAYBACK_FINALIZE_ROLES,
    SINGLE_TRACK_FINALIZE_ROLES,
)

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
    if source_kind_value == MediaRevisionSourceKind.INITIAL_RECORDING.value:
        return HISTORICAL_DUAL_FINALIZE_ROLES
    if source_kind_value == MediaRevisionSourceKind.INITIAL_MIXED_RECORDING.value:
        return MIXED_RECORDING_V5_FINALIZE_ROLES
    if source_kind_value == MediaRevisionSourceKind.MANUAL_UPLOAD.value:
        return SINGLE_TRACK_FINALIZE_ROLES
    raise ManifestValidationError("unsupported media revision source kind")


def validate_required_track_roles(
    roles: set[TrackRole],
    *,
    source_kind: MediaRevisionSourceKind | str | None = None,
) -> None:
    source_kind_value = _source_kind_value(source_kind)
    if source_kind_value is not None:
        expected = _expected_roles_for_source_kind(source_kind_value)
        if source_kind_value == MediaRevisionSourceKind.INITIAL_RECORDING.value:
            accepted_role_sets = (
                HISTORICAL_DUAL_FINALIZE_ROLES,
                HISTORICAL_DUAL_WITH_PLAYBACK_FINALIZE_ROLES,
            )
            if roles in accepted_role_sets:
                return
        elif roles == expected:
            return
        missing = expected - roles
        if missing:
            missing_names = ", ".join(sorted(role.value for role in missing))
            raise ManifestValidationError(f"missing required track roles: {missing_names}")
        role_names = ", ".join(sorted(role.value for role in roles))
        raise ManifestValidationError(f"invalid finalize track role combination: {role_names}")
    # Source-kind-less clients predate v5. Keep their accepted shapes readable,
    # but no v5 desktop path may rely on this fallback.
    if roles in VALID_FINALIZE_ROLE_SETS:
        return
    expected = SINGLE_TRACK_FINALIZE_ROLES if TrackRole.MEDIA in roles else HISTORICAL_DUAL_FINALIZE_ROLES
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
