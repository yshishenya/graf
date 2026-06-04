from datetime import UTC, datetime
from uuid import uuid4

from twobrain_rec_server.domain.statuses import TrackRole, UploadSessionStatus
from twobrain_rec_server.ingest.ranges import accepted_bytes_by_track, missing_ranges_for_expected_sizes
from twobrain_rec_server.ingest.store import UploadPartRecord, UploadSessionRecord


def session() -> UploadSessionRecord:
    return UploadSessionRecord(
        id=uuid4(),
        meeting_id=uuid4(),
        workspace_id=uuid4(),
        organization_id=uuid4(),
        device_id=uuid4(),
        created_by_user_id=uuid4(),
        status=UploadSessionStatus.UPLOADING,
        expires_at=datetime.now(UTC),
    )


def test_accepted_bytes_by_track_sums_parts() -> None:
    upload_session = session()
    upload_session.parts[(TrackRole.MICROPHONE, 0)] = UploadPartRecord(
        track_role=TrackRole.MICROPHONE,
        part_number=0,
        byte_offset=0,
        byte_length=10,
        sha256="a" * 64,
        object_key="x",
        data=b"a" * 10,
    )
    upload_session.parts[(TrackRole.MICROPHONE, 1)] = UploadPartRecord(
        track_role=TrackRole.MICROPHONE,
        part_number=1,
        byte_offset=10,
        byte_length=5,
        sha256="b" * 64,
        object_key="x",
        data=b"b" * 5,
    )
    assert accepted_bytes_by_track(upload_session)[TrackRole.MICROPHONE] == 15


def test_missing_ranges_returns_remaining_tail() -> None:
    upload_session = session()
    upload_session.parts[(TrackRole.SYSTEM, 0)] = UploadPartRecord(
        track_role=TrackRole.SYSTEM,
        part_number=0,
        byte_offset=0,
        byte_length=4,
        sha256="a" * 64,
        object_key="x",
        data=b"a" * 4,
    )
    assert missing_ranges_for_expected_sizes(upload_session, {TrackRole.SYSTEM: 10}) == {
        TrackRole.SYSTEM: [(4, 10)]
    }
