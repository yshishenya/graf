from twobrain_rec_server.api.schemas import TrackDescriptor
from twobrain_rec_server.domain.statuses import TrackRole

REQUIRED_FINALIZE_ROLES = {TrackRole.MANIFEST, TrackRole.MICROPHONE, TrackRole.SYSTEM}


class ManifestValidationError(ValueError):
    pass


def validate_required_tracks(tracks: list[TrackDescriptor]) -> None:
    roles = {track.track_role for track in tracks}
    missing = REQUIRED_FINALIZE_ROLES - roles
    if missing:
        missing_names = ", ".join(sorted(role.value for role in missing))
        raise ManifestValidationError(f"missing required track roles: {missing_names}")
