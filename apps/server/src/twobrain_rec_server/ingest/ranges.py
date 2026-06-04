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
    missing: dict[TrackRole, list[tuple[int, int]]] = {}
    for role, total in expected_sizes.items():
        intervals = sorted(
            (part.byte_offset, min(part.byte_offset + part.byte_length, total))
            for (part_role, _part_number), part in session.parts.items()
            if part_role == role and part.byte_offset < total
        )
        role_missing: list[tuple[int, int]] = []
        cursor = 0
        for start, end in intervals:
            if start > cursor:
                role_missing.append((cursor, start))
            cursor = max(cursor, end)
        if cursor < total:
            role_missing.append((cursor, total))
        missing[role] = role_missing
    return missing
