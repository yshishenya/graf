from hashlib import sha256
from uuid import UUID

from sqlalchemy import select

import twobrain_rec_server.ingest.store as store_module
from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.artifacts import deterministic_wav_bytes, track_descriptor
from twobrain_rec_server.db.models import ProcessingPlaceholder
from twobrain_rec_server.ingest.processing_placeholder import (
    get_processing_placeholder,
    load_processing_placeholder,
)
from twobrain_rec_server.ingest.store import InMemoryIngestStore


def test_processing_placeholder_has_no_workflow_or_mediascribe_ids(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "placeholder", "duration_seconds": 60},
    ).json()
    placeholder = get_processing_placeholder(__import__("uuid").UUID(meeting["meeting_id"]))
    assert placeholder is not None
    assert placeholder.workflow_id is None
    assert placeholder.mediascribe_job_id is None


def test_processing_placeholder_loads_from_database_after_process_store_reset(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "placeholder-cold-load", "duration_seconds": 60},
    ).json()
    meeting_id = UUID(meeting["meeting_id"])
    store_module.store = InMemoryIngestStore()

    async def load():
        async with client.app_state["sessionmaker"]() as db:
            return await load_processing_placeholder(db, meeting_id)

    import asyncio

    placeholder = asyncio.run(load())
    assert placeholder is not None
    assert placeholder.meeting_id == meeting_id
    assert placeholder.processing_status == "not_submitted"
    assert placeholder.meeting_status == "draft"
    assert placeholder.workflow_id is None
    assert placeholder.mediascribe_job_id is None


def test_processing_placeholder_snapshot_tracks_finalized_degraded_and_aborted_states(client) -> None:
    finalized_meeting = _create_meeting_and_session(client, "placeholder-finalized")
    finalized_tracks = _upload_required_tracks(client, finalized_meeting["session"], [8, 9, 10])
    finalized = client.post(
        f"/api/v1/upload-sessions/{finalized_meeting['session']['session_id']}/finalize",
        headers=auth_headers(),
        json={
            "manifest_sha256": finalized_tracks[0]["sha256"],
            "tracks": finalized_tracks,
        },
    )
    assert finalized.status_code == 200

    degraded_meeting = _create_meeting_and_session(client, "placeholder-degraded")
    degraded_tracks = _upload_required_tracks(client, degraded_meeting["session"], [8, 9, 10])
    degraded = client.post(
        f"/api/v1/upload-sessions/{degraded_meeting['session']['session_id']}/finalize",
        headers=auth_headers(),
        json={
            "manifest_sha256": sha256(b"wrong").hexdigest(),
            "tracks": degraded_tracks,
        },
    )
    assert degraded.status_code == 400

    aborted_meeting = _create_meeting_and_session(client, "placeholder-aborted")
    aborted = client.post(
        f"/api/v1/upload-sessions/{aborted_meeting['session']['session_id']}/abort",
        headers=auth_headers(),
        json={"reason": "user requested stop"},
    )
    assert aborted.status_code == 200

    async def placeholder_statuses() -> dict[str, str]:
        async with client.app_state["sessionmaker"]() as db:
            rows = (
                await db.scalars(
                    select(ProcessingPlaceholder).where(
                        ProcessingPlaceholder.meeting_id.in_(
                            [
                                UUID(finalized_meeting["meeting"]["meeting_id"]),
                                UUID(degraded_meeting["meeting"]["meeting_id"]),
                                UUID(aborted_meeting["meeting"]["meeting_id"]),
                            ]
                        )
                    )
                )
            ).all()
            return {str(row.meeting_id): row.meeting_status for row in rows}

    import asyncio

    statuses = asyncio.run(placeholder_statuses())
    assert statuses[finalized_meeting["meeting"]["meeting_id"]] == "ingested_pending_processing"
    assert statuses[degraded_meeting["meeting"]["meeting_id"]] == "degraded"
    assert statuses[aborted_meeting["meeting"]["meeting_id"]] == "aborted"


def _create_meeting_and_session(client, local_recording_id: str) -> dict[str, object]:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": local_recording_id, "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"manifest": 8, "microphone": 9, "system": 10}},
    ).json()
    return {"meeting": meeting, "session": session, "tracks": []}


def _upload_required_tracks(client, session: dict[str, str], sizes: list[int]) -> list[dict[str, object]]:
    tracks = []
    for size, role in zip(sizes, ["manifest", "microphone", "system"], strict=True):
        data = deterministic_wav_bytes(size)
        digest = sha256(data).hexdigest()
        response = client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/{role}/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
            content=data,
        )
        assert response.status_code == 200
        tracks.append(track_descriptor(role, size) | {"sha256": digest, "byte_length": size})
    return tracks
