from twobrain_rec_server.domain.statuses import TrackRole
from twobrain_rec_server.ingest.store import UploadSessionRecord


def accepted_bytes_by_track(session: UploadSessionRecord) -> dict[TrackRole, int]:
    accepted: dict[TrackRole, int] = {}
    for (role, _part_number), part in session.parts.items():
        accepted[role] = accepted.get(role, 0) + part.byte_length
    return accepted


def missing_ranges_for_expected_sizes(
    session: UploadSessionRecord,
    expected_sizes: dict[TrackRole, int],
) -> dict[TrackRole, list[tuple[int, int]]]:
    accepted = accepted_bytes_by_track(session)
    missing: dict[TrackRole, list[tuple[int, int]]] = {}
    for role, total in expected_sizes.items():
        current = accepted.get(role, 0)
        missing[role] = [] if current >= total else [(current, total)]
    return missing
