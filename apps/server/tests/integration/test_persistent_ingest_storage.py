from hashlib import sha256
from uuid import UUID

from sqlalchemy import func, select

import twobrain_rec_server.ingest.store as store_module
from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.artifacts import deterministic_wav_bytes, track_descriptor
from twobrain_rec_server.db.models import (
    IngestAuditEvent,
    ManifestSnapshot,
    Meeting,
    ProcessingPlaceholder,
    TrackArtifact,
    UploadPart,
    UploadSession,
)
from twobrain_rec_server.ingest.store import InMemoryIngestStore


def test_ingest_metadata_is_persisted_to_database(client) -> None:
    meeting_response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "persistent-001", "duration_seconds": 60},
    )
    assert meeting_response.status_code == 200
    meeting_id = meeting_response.json()["meeting_id"]

    session_response = client.post(
        f"/api/v1/meetings/{meeting_id}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"manifest": 8, "microphone": 8, "system": 8}},
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["session_id"]

    data = deterministic_wav_bytes(8)
    digest = sha256(data).hexdigest()
    part_response = client.put(
        f"/api/v1/upload-sessions/{session_id}/tracks/system/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
        content=data,
    )
    assert part_response.status_code == 200

    async def counts() -> tuple[int, int, int, int]:
        async with client.app_state["sessionmaker"]() as db:
            return (
                await db.scalar(select(func.count()).select_from(Meeting)),
                await db.scalar(select(func.count()).select_from(UploadSession)),
                await db.scalar(select(func.count()).select_from(UploadPart)),
                await db.scalar(select(func.count()).select_from(IngestAuditEvent)),
            )

    assert client.portal.call(counts) == (1, 1, 1, 3)


def test_meeting_start_and_end_times_are_persisted(client) -> None:
    meeting_response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "persistent-times",
            "duration_seconds": 60,
            "started_at": "2026-06-04T10:00:00Z",
            "ended_at": "2026-06-04T10:01:00Z",
        },
    )
    assert meeting_response.status_code == 200
    assert meeting_response.json()["started_at"].startswith("2026-06-04T10:00:00")
    assert meeting_response.json()["ended_at"].startswith("2026-06-04T10:01:00")
    meeting_id = UUID(meeting_response.json()["meeting_id"])

    async def persisted_times():
        async with client.app_state["sessionmaker"]() as db:
            model = await db.get(Meeting, meeting_id)
            assert model is not None
            return model.started_at, model.ended_at

    started_at, ended_at = client.portal.call(persisted_times)
    assert started_at is not None
    assert ended_at is not None
    assert started_at.isoformat().startswith("2026-06-04T10:00:00")
    assert ended_at.isoformat().startswith("2026-06-04T10:01:00")


def test_meeting_response_reports_title_source_for_user_and_generic_titles(client) -> None:
    titled = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "persistent-user-title", "duration_seconds": 60, "title": "Manual title"},
    )
    generic = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "persistent-generic-title", "duration_seconds": 60},
    )

    assert titled.status_code == 200
    assert titled.json()["title"] == "Manual title"
    assert titled.json()["title_source"] == "legacy_unknown"
    assert generic.status_code == 200
    assert generic.json()["title"] is None
    assert generic.json()["title_source"] == "generic"

    async def persisted_fingerprints() -> tuple[str | None, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            titled_model = await db.get(Meeting, UUID(titled.json()["meeting_id"]))
            generic_model = await db.get(Meeting, UUID(generic.json()["meeting_id"]))
            assert titled_model is not None
            assert generic_model is not None
            return (
                titled_model.create_request_fingerprint_sha256,
                generic_model.create_request_fingerprint_sha256,
            )

    titled_fingerprint, generic_fingerprint = client.portal.call(
        persisted_fingerprints
    )
    assert titled_fingerprint is not None and len(titled_fingerprint) == 64
    assert generic_fingerprint is not None and len(generic_fingerprint) == 64
    assert titled_fingerprint != generic_fingerprint


def test_upload_session_persists_expected_roles_separately_from_expected_sizes(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "persistent-track-expectations", "duration_seconds": 60},
    ).json()

    response = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={
            "expected_tracks": ["manifest", "microphone", "system"],
            "expected_track_sizes": {"manifest": 8},
        },
    )

    assert response.status_code == 200

    async def persisted_expectations() -> tuple[list[str], dict[str, int]]:
        async with client.app_state["sessionmaker"]() as db:
            session = await db.get(UploadSession, UUID(response.json()["session_id"]))
            assert session is not None
            return session.expected_track_roles, session.expected_track_sizes

    roles, sizes = client.portal.call(persisted_expectations)
    assert roles == ["manifest", "microphone", "system"]
    assert sizes == {"manifest": 8}


def test_upload_session_rejects_size_for_unexpected_track_role(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "unexpected-track-size-role", "duration_seconds": 60},
    ).json()

    response = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={
            "expected_tracks": ["manifest", "media"],
            "expected_track_sizes": {"microphone": 8},
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "unexpected_expected_track_size_role"


def test_finalize_creates_track_artifact_metadata(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "persistent-finalize", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"manifest": 8, "microphone": 9, "system": 10}},
    ).json()

    tracks = []
    for size, role in [(8, "manifest"), (9, "microphone"), (10, "system")]:
        data = deterministic_wav_bytes(size)
        digest = sha256(data).hexdigest()
        response = client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/{role}/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
            content=data,
        )
        assert response.status_code == 200
        tracks.append(track_descriptor(role, size) | {"sha256": digest, "byte_length": size})

    finalized = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/finalize",
        headers=auth_headers(),
        json={"manifest_sha256": tracks[0]["sha256"], "tracks": tracks},
    )
    assert finalized.status_code == 200
    assert finalized.json()["object_count"] == 3

    async def finalized_metadata() -> tuple[list[TrackArtifact], ManifestSnapshot | None]:
        meeting_id = UUID(meeting["meeting_id"])
        async with client.app_state["sessionmaker"]() as db:
            artifacts = list(
                (
                    await db.scalars(
                        select(TrackArtifact)
                        .where(TrackArtifact.meeting_id == meeting_id)
                        .order_by(TrackArtifact.track_role)
                    )
                ).all()
            )
            snapshot = await db.scalar(select(ManifestSnapshot).where(ManifestSnapshot.meeting_id == meeting_id))
            return artifacts, snapshot

    artifacts, snapshot = client.portal.call(finalized_metadata)
    artifacts_by_role = {artifact.track_role: artifact for artifact in artifacts}
    assert set(artifacts_by_role) == {"manifest", "microphone", "system"}
    for track in tracks:
        artifact = artifacts_by_role[str(track["track_role"])]
        assert artifact.codec == track["codec"]
        assert artifact.sample_rate_hz == track["sample_rate_hz"]
        assert artifact.channel_count == track["channel_count"]
        assert artifact.duration_seconds == track["duration_seconds"]
        assert artifact.byte_length == track["byte_length"]
        assert artifact.sha256 == track["sha256"]
        assert f"/tracks/{track['track_role']}/" in artifact.storage_object_key
    assert snapshot is not None
    assert snapshot.manifest_sha256 == tracks[0]["sha256"]
    assert snapshot.manifest_json["manifest_sha256"] == tracks[0]["sha256"]
    assert snapshot.manifest_json["tracks"] == tracks
    assert {track["track_role"] for track in snapshot.manifest_json["tracks"]} == {
        "manifest",
        "microphone",
        "system",
    }
    assert all("sha256" in track and "byte_length" in track for track in snapshot.manifest_json["tracks"])


def test_finalize_persists_processing_and_lifecycle_fields(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "persistent-processing-fields",
            "duration_seconds": 60,
            "started_at": "2026-06-04T10:00:00Z",
            "ended_at": "2026-06-04T10:01:00Z",
        },
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"manifest": 8, "microphone": 9, "system": 10}},
    ).json()

    tracks = []
    for size, role in [(8, "manifest"), (9, "microphone"), (10, "system")]:
        data = deterministic_wav_bytes(size)
        digest = sha256(data).hexdigest()
        response = client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/{role}/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
            content=data,
        )
        assert response.status_code == 200
        tracks.append(track_descriptor(role, size) | {"sha256": digest, "byte_length": size})

    finalized = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/finalize",
        headers=auth_headers(),
        json={"manifest_sha256": tracks[0]["sha256"], "tracks": tracks},
    )
    assert finalized.status_code == 200

    async def persisted_fields():
        async with client.app_state["sessionmaker"]() as db:
            meeting_model = await db.get(Meeting, UUID(meeting["meeting_id"]))
            session_model = await db.get(UploadSession, UUID(session["session_id"]))
            placeholder = await db.scalar(
                select(ProcessingPlaceholder).where(ProcessingPlaceholder.meeting_id == UUID(meeting["meeting_id"]))
            )
            assert meeting_model is not None
            assert session_model is not None
            assert placeholder is not None
            return meeting_model, session_model, placeholder

    meeting_model, session_model, placeholder = client.portal.call(persisted_fields)
    assert meeting_model.started_at is not None
    assert meeting_model.ended_at is not None
    assert meeting_model.processing_status == "not_submitted"
    assert session_model.processing_status == "not_submitted"
    assert session_model.finalized_at is not None
    assert placeholder.status == "not_submitted"


def test_upload_session_status_can_be_loaded_after_process_store_reset(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "persistent-cold-read", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"system": 16}},
    ).json()
    data = deterministic_wav_bytes(4)
    digest = sha256(data).hexdigest()
    assert (
        client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
            content=data,
        ).status_code
        == 200
    )

    store_module.store = InMemoryIngestStore()

    status = client.get(f"/api/v1/upload-sessions/{session['session_id']}", headers=auth_headers())
    missing = client.get(
        f"/api/v1/upload-sessions/{session['session_id']}/missing-ranges",
        headers=auth_headers(),
    )

    assert status.status_code == 200
    assert status.json()["accepted_bytes_by_track"] == {"system": 4}
    assert missing.json()["missing_ranges_by_track"] == {"system": [{"start": 4, "end": 16}]}


def test_legacy_empty_expected_roles_rehydrate_to_required_upload_roles(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "persistent-legacy-empty-roles", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"microphone": 16}},
    ).json()

    async def clear_expected_roles() -> None:
        async with client.app_state["sessionmaker"]() as db:
            model = await db.get(UploadSession, UUID(session["session_id"]))
            assert model is not None
            model.expected_track_roles = []
            await db.commit()

    client.portal.call(clear_expected_roles)
    store_module.store = InMemoryIngestStore()
    data = deterministic_wav_bytes(4)
    digest = sha256(data).hexdigest()

    response = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/microphone/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
        content=data,
    )

    assert response.status_code == 200


def test_finalize_can_reload_upload_session_after_process_store_reset(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "persistent-cold-finalize", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"manifest": 8, "microphone": 9, "system": 10}},
    ).json()

    tracks = []
    for size, role in [(8, "manifest"), (9, "microphone"), (10, "system")]:
        data = deterministic_wav_bytes(size)
        digest = sha256(data).hexdigest()
        response = client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/{role}/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
            content=data,
        )
        assert response.status_code == 200
        tracks.append(track_descriptor(role, size) | {"sha256": digest, "byte_length": size})

    store_module.store = InMemoryIngestStore()

    finalized = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/finalize",
        headers=auth_headers(),
        json={"manifest_sha256": tracks[0]["sha256"], "tracks": tracks},
    )

    assert finalized.status_code == 200
    assert finalized.json()["meeting"]["status"] == "ingested_pending_processing"
    assert finalized.json()["upload_session"]["status"] == "finalized"
