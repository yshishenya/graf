from twobrain_rec_server.api.schemas import TrackDescriptor
from twobrain_rec_server.domain.statuses import TrackRole

DUAL_TRACK_FINALIZE_ROLES = {TrackRole.MANIFEST, TrackRole.MICROPHONE, TrackRole.SYSTEM}
SINGLE_TRACK_FINALIZE_ROLES = {TrackRole.MANIFEST, TrackRole.MEDIA}


class ManifestValidationError(ValueError):
    pass


def validate_required_tracks(tracks: list[TrackDescriptor]) -> None:
    roles = {track.track_role for track in tracks}
    if roles in (DUAL_TRACK_FINALIZE_ROLES, SINGLE_TRACK_FINALIZE_ROLES):
        return
    expected = SINGLE_TRACK_FINALIZE_ROLES if TrackRole.MEDIA in roles else DUAL_TRACK_FINALIZE_ROLES
    missing = expected - roles
    if missing:
        missing_names = ", ".join(sorted(role.value for role in missing))
        raise ManifestValidationError(f"missing required track roles: {missing_names}")
    role_names = ", ".join(sorted(role.value for role in roles))
    raise ManifestValidationError(f"invalid finalize track role combination: {role_names}")
