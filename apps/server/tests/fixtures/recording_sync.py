from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID, uuid5

from tests.fixtures.artifacts import deterministic_wav_bytes, track_descriptor

FIXTURE_NAMESPACE = UUID("d0ef04b8-37c3-4e6a-87db-3c13e91f0042")


@dataclass(frozen=True, slots=True)
class RevisionAwareRecordingFixture:
    local_recording_id: str
    local_media_revision_id: str
    meeting_id: UUID
    media_revision_id: UUID
    manifest_sha256: str
    track_sha256_by_role: dict[str, str]
    expected_tracks: list[dict[str, object]]


def stable_uuid(*parts: str) -> UUID:
    return uuid5(FIXTURE_NAMESPACE, ":".join(parts))


def initial_local_media_revision_id(local_recording_id: str) -> str:
    return f"{local_recording_id}--initial"


def revision_aware_recording_fixture(local_recording_id: str = "offline-fixture-001") -> RevisionAwareRecordingFixture:
    tracks = [
        track_descriptor("manifest", size=128),
        track_descriptor("microphone", size=1_024),
        track_descriptor("system", size=2_048),
    ]
    by_role = {str(track["track_role"]): str(track["sha256"]) for track in tracks}
    local_media_revision_id = initial_local_media_revision_id(local_recording_id)
    return RevisionAwareRecordingFixture(
        local_recording_id=local_recording_id,
        local_media_revision_id=local_media_revision_id,
        meeting_id=stable_uuid("meeting", local_recording_id),
        media_revision_id=stable_uuid("media-revision", local_media_revision_id),
        manifest_sha256=by_role["manifest"],
        track_sha256_by_role=by_role,
        expected_tracks=tracks,
    )


def upload_part_bytes(track_role: str, part_index: int = 0, size: int = 256) -> bytes:
    seed = f"{track_role}:{part_index}:".encode()
    body = seed + deterministic_wav_bytes(max(size - len(seed), 0))
    return body[:size]


def upload_part_sha256(track_role: str, part_index: int = 0, size: int = 256) -> str:
    return sha256(upload_part_bytes(track_role, part_index, size)).hexdigest()


def desktop_sync_state_payload(
    fixture: RevisionAwareRecordingFixture | None = None,
    *,
    state: str = "uploading",
    conflict_state: str = "none",
) -> dict[str, object]:
    fixture = fixture or revision_aware_recording_fixture()
    return {
        "local_recording_id": fixture.local_recording_id,
        "local_media_revision_id": fixture.local_media_revision_id,
        "meeting": {
            "meeting_id": str(fixture.meeting_id),
            "status": state,
            "processing_status": "not_submitted",
            "deletion_state": "none",
            "access_state": "owner",
        },
        "media_revision": {
            "media_revision_id": str(fixture.media_revision_id),
            "revision_number": 1,
            "status": state,
            "manifest_sha256": fixture.manifest_sha256,
            "track_sha256_by_role": fixture.track_sha256_by_role,
        },
        "upload_session": {
            "session_id": str(stable_uuid("upload-session", fixture.local_recording_id)),
            "status": state,
            "accepted_bytes_by_track": {"manifest": 0, "microphone": 0, "system": 0},
            "desktop_truth_rule": "server_ranges_authoritative",
        },
        "processing": {"status": "not_submitted", "workflow_id": None, "reason_code": None},
        "review": {
            "available": False,
            "web_url": f"/meetings/{fixture.meeting_id}",
            "desktop_url": f"/desktop/meetings/{fixture.meeting_id}",
        },
        "conflict": {
            "state": conflict_state,
            "reason": None if conflict_state == "none" else conflict_state,
            "next_action": "continue_upload" if conflict_state == "none" else "manual_review",
        },
    }
