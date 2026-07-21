import asyncio
from hashlib import sha256
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.artifacts import deterministic_wav_bytes, track_descriptor
from twobrain_rec_server.db.models import (
    IngestAuditEvent,
    MediaRevision,
    Meeting,
    PlaybackNormalizationJob,
    TrackArtifact,
    UploadSession,
)
from twobrain_rec_server.domain.statuses import MeetingStatus, UploadSessionStatus
from twobrain_rec_server.ingest import store as store_module
from twobrain_rec_server.ingest.media_revisions import ensure_media_revision_acceptance_is_safe


class FinalizeStreamingOnlyStorage:
    def __init__(self, delegate: object) -> None:
        self.delegate = delegate

    def ensure_bucket(self) -> None:
        self.delegate.ensure_bucket()

    def put_stream(self, object_key: str, stream, length: int) -> None:
        self.delegate.put_stream(object_key, stream, length)

    def get_bytes(self, _object_key: str) -> bytes:
        raise AssertionError("finalize must not load full upload parts into memory")

    async def get_bytes_async(self, _object_key: str) -> bytes:
        raise AssertionError("finalize must not load full upload parts into memory")

    def iter_object(
        self,
        object_key: str,
        *,
        offset: int = 0,
        length: int | None = None,
        chunk_size: int = 4 * 1024 * 1024,
    ):
        import asyncio

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise AssertionError("finalize must not read storage objects on the event loop")
        return self.delegate.iter_object(object_key, offset=offset, length=length, chunk_size=chunk_size)


def _create_session_with_parts(
    client: TestClient,
    expected_track_sizes: dict[str, int] | None = None,
    meeting_id: str | None = None,
    sizes: tuple[int, int, int] = (8, 9, 10),
) -> tuple[str, list[dict[str, object]]]:
    if meeting_id is None:
        meeting = client.post(
            "/api/v1/meetings",
            headers=auth_headers(),
            json={"local_recording_id": "finalize-integrity", "duration_seconds": 60},
        ).json()
        meeting_id = meeting["meeting_id"]
    session = client.post(
        f"/api/v1/meetings/{meeting_id}/upload-sessions",
        headers=auth_headers(),
        json={
            "expected_track_sizes": expected_track_sizes
            or {"manifest": sizes[0], "microphone": sizes[1], "system": sizes[2]}
        },
    ).json()

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
    return session["session_id"], tracks


def _finalize(client: TestClient, session_id: str, tracks: list[dict[str, object]], manifest_sha256: str):
    return client.post(
        f"/api/v1/upload-sessions/{session_id}/finalize",
        headers=auth_headers(),
        json={"manifest_sha256": manifest_sha256, "tracks": tracks},
    )


def test_finalize_rejects_mismatched_manifest_sha(client: TestClient) -> None:
    session_id, tracks = _create_session_with_parts(client)

    response = _finalize(client, session_id, tracks, sha256(b"wrong-manifest").hexdigest())

    assert response.status_code == 400
    assert response.json()["code"] == "manifest_checksum_mismatch"


def test_finalize_validation_failure_persists_degraded_state_and_audit(client: TestClient) -> None:
    session_id, tracks = _create_session_with_parts(client)

    response = _finalize(client, session_id, tracks, sha256(b"wrong-manifest").hexdigest())

    assert response.status_code == 400

    async def persisted_state():
        async with client.app_state["sessionmaker"]() as db:
            session = await db.get(UploadSession, UUID(session_id))
            meeting = await db.get(Meeting, session.meeting_id)
            audit = await db.scalar(
                select(IngestAuditEvent)
                .where(
                    IngestAuditEvent.upload_session_id == session.id,
                    IngestAuditEvent.event_type == "finalize_degraded",
                )
                .order_by(IngestAuditEvent.created_at.desc())
            )
            return meeting, session, audit

    import asyncio

    meeting, session, audit = asyncio.run(persisted_state())
    assert meeting.status == "degraded"
    assert session.status == "degraded"
    assert audit is not None
    assert audit.meeting_id == meeting.id
    assert audit.workspace_id == meeting.workspace_id
    assert audit.actor_user_id is not None
    assert audit.device_id is not None
    assert audit.metadata_json == {
        "reason_code": "manifest_checksum_mismatch",
        "reason": "Manifest checksum mismatch",
    }


def test_finalize_accepts_contiguous_multipart_track(client: TestClient) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "finalize-multipart-track", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"manifest": 4, "microphone": 4, "system": 8}},
    ).json()
    session_id = session["session_id"]

    manifest = b"m123"
    microphone = b"u123"
    system_head = b"s123"
    system_tail = b"s456"
    uploads = [
        ("manifest", 0, 0, manifest),
        ("microphone", 0, 0, microphone),
        ("system", 1, 4, system_tail),
        ("system", 0, 0, system_head),
    ]
    for role, part_number, offset, data in uploads:
        response = client.put(
            f"/api/v1/upload-sessions/{session_id}/tracks/{role}/parts/{part_number}",
            headers=auth_headers() | {"X-Byte-Offset": str(offset), "X-Content-SHA256": sha256(data).hexdigest()},
            content=data,
        )
        assert response.status_code == 200

    system = system_head + system_tail
    tracks = [
        track_descriptor("manifest", len(manifest)) | {"sha256": sha256(manifest).hexdigest(), "byte_length": len(manifest)},
        track_descriptor("microphone", len(microphone))
        | {"sha256": sha256(microphone).hexdigest(), "byte_length": len(microphone)},
        track_descriptor("system", len(system)) | {"sha256": sha256(system).hexdigest(), "byte_length": len(system)},
    ]

    original_storage = client.app.state.storage
    client.app.state.storage = FinalizeStreamingOnlyStorage(client.app_state["storage"])
    try:
        response = _finalize(client, session_id, tracks, sha256(manifest).hexdigest())
    finally:
        client.app.state.storage = original_storage

    assert response.status_code == 200

    async def persisted_system_artifact() -> TrackArtifact:
        async with client.app_state["sessionmaker"]() as db:
            artifact = await db.scalar(
                select(TrackArtifact).where(
                    TrackArtifact.meeting_id == UUID(meeting["meeting_id"]),
                    TrackArtifact.track_role == "system",
                )
            )
            assert artifact is not None
            return artifact

    import asyncio

    artifact = asyncio.run(persisted_system_artifact())
    assert artifact.byte_length == len(system)
    assert artifact.sha256 == sha256(system).hexdigest()
    assert client.app_state["storage"].objects[artifact.storage_object_key] == system


def test_finalize_rejects_mismatched_track_sha(client: TestClient) -> None:
    session_id, tracks = _create_session_with_parts(client)
    tracks[1] = tracks[1] | {"sha256": sha256(b"wrong-microphone").hexdigest()}

    response = _finalize(client, session_id, tracks, str(tracks[0]["sha256"]))

    assert response.status_code == 400
    assert response.json()["code"] == "track_checksum_mismatch"


def test_finalize_cleans_materialized_track_after_checksum_mismatch(client: TestClient) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "finalize-multipart-checksum-conflict", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"manifest": 4, "microphone": 4, "system": 8}},
    ).json()
    session_id = session["session_id"]
    manifest = b"m123"
    microphone = b"u123"
    system_head = b"s123"
    system_tail = b"s456"
    for role, part_number, offset, data in [
        ("manifest", 0, 0, manifest),
        ("microphone", 0, 0, microphone),
        ("system", 0, 0, system_head),
        ("system", 1, 4, system_tail),
    ]:
        response = client.put(
            f"/api/v1/upload-sessions/{session_id}/tracks/{role}/parts/{part_number}",
            headers=auth_headers() | {"X-Byte-Offset": str(offset), "X-Content-SHA256": sha256(data).hexdigest()},
            content=data,
        )
        assert response.status_code == 200

    system = system_head + system_tail
    tracks = [
        track_descriptor("manifest", len(manifest)) | {"sha256": sha256(manifest).hexdigest(), "byte_length": len(manifest)},
        track_descriptor("microphone", len(microphone))
        | {"sha256": sha256(microphone).hexdigest(), "byte_length": len(microphone)},
        track_descriptor("system", len(system))
        | {"sha256": sha256(b"wrong-system").hexdigest(), "byte_length": len(system)},
    ]

    response = _finalize(client, session_id, tracks, sha256(manifest).hexdigest())

    assert response.status_code == 400
    assert response.json()["code"] == "track_checksum_mismatch"
    assert all("/media-revisions/" not in key for key in client.app_state["storage"].objects)


def test_finalize_cleans_prior_materialized_track_after_later_track_gap(client: TestClient) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "finalize-cleans-prior-materialized", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"manifest": 8, "microphone": 4, "system": 8}},
    ).json()
    session_id = session["session_id"]
    manifest_head = b"m123"
    manifest_tail = b"m456"
    microphone = b"u123"
    system_tail = b"s456"
    for role, part_number, offset, data in [
        ("manifest", 0, 0, manifest_head),
        ("manifest", 1, 4, manifest_tail),
        ("microphone", 0, 0, microphone),
        ("system", 1, 4, system_tail),
    ]:
        response = client.put(
            f"/api/v1/upload-sessions/{session_id}/tracks/{role}/parts/{part_number}",
            headers=auth_headers() | {"X-Byte-Offset": str(offset), "X-Content-SHA256": sha256(data).hexdigest()},
            content=data,
        )
        assert response.status_code == 200

    manifest = manifest_head + manifest_tail
    tracks = [
        track_descriptor("manifest", len(manifest)) | {"sha256": sha256(manifest).hexdigest(), "byte_length": len(manifest)},
        track_descriptor("system", 8) | {"sha256": sha256(b"system-with-gap").hexdigest(), "byte_length": 8},
        track_descriptor("microphone", len(microphone))
        | {"sha256": sha256(microphone).hexdigest(), "byte_length": len(microphone)},
    ]

    response = _finalize(client, session_id, tracks, sha256(manifest).hexdigest())

    assert response.status_code == 409
    assert response.json()["code"] == "missing_required_parts"
    assert all("/media-revisions/" not in key for key in client.app_state["storage"].objects)


def test_finalize_rejects_mismatched_track_byte_length(client: TestClient) -> None:
    session_id, tracks = _create_session_with_parts(client, {"manifest": 8, "microphone": 9, "system": 11})
    tracks[2] = tracks[2] | {"byte_length": 11}

    response = _finalize(client, session_id, tracks, str(tracks[0]["sha256"]))

    assert response.status_code == 400
    assert response.json()["code"] == "track_length_mismatch"


def test_finalize_rejects_role_object_mapping_mismatch(client: TestClient) -> None:
    session_id, tracks = _create_session_with_parts(client)
    microphone = next(track for track in tracks if track["track_role"] == "microphone")
    system = next(track for track in tracks if track["track_role"] == "system")
    tracks = [
        track
        if track["track_role"] == "manifest"
        else track | {"sha256": system["sha256"]}
        if track["track_role"] == "microphone"
        else track | {"sha256": microphone["sha256"]}
        for track in tracks
    ]

    response = _finalize(client, session_id, tracks, str(tracks[0]["sha256"]))

    assert response.status_code == 400
    assert response.json()["code"] == "track_checksum_mismatch"


def test_finalize_rejects_expected_track_size_mismatch(client: TestClient) -> None:
    session_id, tracks = _create_session_with_parts(client, {"manifest": 8, "microphone": 99, "system": 10})

    response = _finalize(client, session_id, tracks, str(tracks[0]["sha256"]))

    assert response.status_code == 409
    assert response.json()["code"] == "expected_track_size_mismatch"


def test_finalize_rejects_immutable_media_revision_fingerprint_change(client: TestClient) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "finalize-fingerprint-conflict", "duration_seconds": 60},
    ).json()
    first_session_id, first_tracks = _create_session_with_parts(client, meeting_id=meeting["meeting_id"])
    first_finalize = _finalize(client, first_session_id, first_tracks, str(first_tracks[0]["sha256"]))
    assert first_finalize.status_code == 200
    before_artifacts = _track_artifacts_for_meeting(client, meeting["meeting_id"])

    second_session_id, second_tracks = _create_session_with_parts(
        client,
        meeting_id=meeting["meeting_id"],
        sizes=(8, 11, 12),
    )
    response = _finalize(client, second_session_id, second_tracks, str(second_tracks[0]["sha256"]))

    assert response.status_code == 409
    assert response.json()["code"] == "media_revision_fingerprint_conflict"
    assert _track_artifacts_for_meeting(client, meeting["meeting_id"]) == before_artifacts


def test_media_revision_acceptance_lock_serializes_concurrent_checks(client: TestClient) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "finalize-fingerprint-lock", "duration_seconds": 60},
    ).json()
    media_revision_id = UUID(meeting["media_revision"]["media_revision_id"])

    async def exercise_lock() -> None:
        first = client.app_state["sessionmaker"]()
        second = client.app_state["sessionmaker"]()
        try:
            await first.begin()
            await ensure_media_revision_acceptance_is_safe(
                first,
                media_revision_id=media_revision_id,
                manifest_sha256="m" * 64,
                tracks=[
                    {"track_role": "microphone", "sha256": "u" * 64},
                    {"track_role": "system", "sha256": "s" * 64},
                ],
            )

            second_started = asyncio.Event()

            async def blocked_check() -> None:
                await second.begin()
                second_started.set()
                await ensure_media_revision_acceptance_is_safe(
                    second,
                    media_revision_id=media_revision_id,
                    manifest_sha256="m" * 64,
                    tracks=[
                        {"track_role": "microphone", "sha256": "u" * 64},
                        {"track_role": "system", "sha256": "s" * 64},
                    ],
                )
                await second.commit()

            waiter = asyncio.create_task(blocked_check())
            await asyncio.wait_for(second_started.wait(), timeout=1)
            await asyncio.sleep(0.1)
            assert not waiter.done(), "the second acceptance check must wait for the row lock"

            await first.commit()
            await asyncio.wait_for(waiter, timeout=2)
        finally:
            if first.in_transaction():
                await first.rollback()
            if second.in_transaction():
                await second.rollback()
            await first.close()
            await second.close()

    asyncio.run(exercise_lock())


def test_finalize_fingerprint_conflict_preserves_existing_multipart_objects(client: TestClient) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "finalize-preserve-multipart-conflict", "duration_seconds": 60},
    ).json()

    def upload_multipart(session_id: str, *, prefix: bytes) -> list[dict[str, object]]:
        manifest = prefix + b"manifest"
        microphone = prefix + b"microphone"
        system_head = prefix + b"system-head"
        system_tail = b"-tail"
        parts = [
            ("manifest", 0, 0, manifest),
            ("microphone", 0, 0, microphone),
            ("system", 0, 0, system_head),
            ("system", 1, len(system_head), system_tail),
        ]
        for role, part_number, offset, data in parts:
            response = client.put(
                f"/api/v1/upload-sessions/{session_id}/tracks/{role}/parts/{part_number}",
                headers=auth_headers()
                | {"X-Byte-Offset": str(offset), "X-Content-SHA256": sha256(data).hexdigest()},
                content=data,
            )
            assert response.status_code == 200, response.text
        tracks = []
        for role, data in [("manifest", manifest), ("microphone", microphone), ("system", system_head + system_tail)]:
            tracks.append(
                track_descriptor(role, len(data))
                | {"sha256": sha256(data).hexdigest(), "byte_length": len(data)}
            )
        return tracks

    first_session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"manifest": 14, "microphone": 16, "system": 22}},
    ).json()["session_id"]
    first_tracks = upload_multipart(first_session, prefix=b"first-")
    first_finalize = _finalize(client, first_session, first_tracks, str(first_tracks[0]["sha256"]))
    assert first_finalize.status_code == 200
    before_materialized_objects = {
        key: value
        for key, value in client.app_state["storage"].objects.items()
        if "/media-revisions/" in key
    }

    second_session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"manifest": 15, "microphone": 17, "system": 23}},
    ).json()["session_id"]
    second_tracks = upload_multipart(second_session, prefix=b"second-")
    response = _finalize(client, second_session, second_tracks, str(second_tracks[0]["sha256"]))

    assert response.status_code == 409
    assert response.json()["code"] == "media_revision_fingerprint_conflict"
    after_materialized_objects = {
        key: value
        for key, value in client.app_state["storage"].objects.items()
        if "/media-revisions/" in key
    }
    assert after_materialized_objects == before_materialized_objects


def test_finalize_cleans_materialized_track_after_immutable_conflict(client: TestClient) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "finalize-materialized-conflict", "duration_seconds": 60},
    ).json()
    first_session_id, first_tracks = _create_session_with_parts(client, meeting_id=meeting["meeting_id"])
    first_finalize = _finalize(client, first_session_id, first_tracks, str(first_tracks[0]["sha256"]))
    assert first_finalize.status_code == 200
    before_artifacts = _track_artifacts_for_meeting(client, meeting["meeting_id"])

    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"manifest": 4, "microphone": 4, "system": 8}},
    ).json()
    session_id = session["session_id"]
    manifest = b"m456"
    microphone = b"u456"
    system_head = b"s456"
    system_tail = b"s789"
    uploads = [
        ("manifest", 0, 0, manifest),
        ("microphone", 0, 0, microphone),
        ("system", 0, 0, system_head),
        ("system", 1, 4, system_tail),
    ]
    for role, part_number, offset, data in uploads:
        response = client.put(
            f"/api/v1/upload-sessions/{session_id}/tracks/{role}/parts/{part_number}",
            headers=auth_headers() | {"X-Byte-Offset": str(offset), "X-Content-SHA256": sha256(data).hexdigest()},
            content=data,
        )
        assert response.status_code == 200
    system = system_head + system_tail
    tracks = [
        track_descriptor("manifest", len(manifest)) | {"sha256": sha256(manifest).hexdigest(), "byte_length": len(manifest)},
        track_descriptor("microphone", len(microphone))
        | {"sha256": sha256(microphone).hexdigest(), "byte_length": len(microphone)},
        track_descriptor("system", len(system)) | {"sha256": sha256(system).hexdigest(), "byte_length": len(system)},
    ]

    response = _finalize(client, session_id, tracks, sha256(manifest).hexdigest())

    assert response.status_code == 409
    assert response.json()["code"] == "media_revision_fingerprint_conflict"
    assert _track_artifacts_for_meeting(client, meeting["meeting_id"]) == before_artifacts
    assert all("/media-revisions/" not in key for key in client.app_state["storage"].objects)


def test_finalize_cleans_materialized_track_after_persistence_failure(client: TestClient, monkeypatch) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "finalize-persistence-failure", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"manifest": 4, "microphone": 4, "system": 8}},
    ).json()
    session_id = session["session_id"]
    manifest = b"m123"
    microphone = b"u123"
    system_head = b"s123"
    system_tail = b"s456"
    for role, part_number, offset, data in [
        ("manifest", 0, 0, manifest),
        ("microphone", 0, 0, microphone),
        ("system", 0, 0, system_head),
        ("system", 1, 4, system_tail),
    ]:
        response = client.put(
            f"/api/v1/upload-sessions/{session_id}/tracks/{role}/parts/{part_number}",
            headers=auth_headers() | {"X-Byte-Offset": str(offset), "X-Content-SHA256": sha256(data).hexdigest()},
            content=data,
        )
        assert response.status_code == 200
    before_meeting_status = store_module.store.meetings[UUID(meeting["meeting_id"])].status
    before_session_status = store_module.store.sessions[UUID(session_id)].status
    system = system_head + system_tail
    tracks = [
        track_descriptor("manifest", len(manifest)) | {"sha256": sha256(manifest).hexdigest(), "byte_length": len(manifest)},
        track_descriptor("microphone", len(microphone))
        | {"sha256": sha256(microphone).hexdigest(), "byte_length": len(microphone)},
        track_descriptor("system", len(system)) | {"sha256": sha256(system).hexdigest(), "byte_length": len(system)},
    ]

    async def fail_persist_finalized_tracks(*_args, **_kwargs) -> None:
        raise RuntimeError("simulated finalized track persistence failure")

    monkeypatch.setattr(
        "twobrain_rec_server.ingest.finalize.persist_finalized_tracks",
        fail_persist_finalized_tracks,
    )

    response = _finalize(client, session_id, tracks, sha256(manifest).hexdigest())

    assert response.status_code == 503
    assert response.json()["code"] == "persistence_unavailable"
    assert all("/media-revisions/" not in key for key in client.app_state["storage"].objects)
    cached_meeting = store_module.store.meetings[UUID(meeting["meeting_id"])]
    cached_session = store_module.store.sessions[UUID(session_id)]
    assert cached_meeting.status == before_meeting_status == MeetingStatus.UPLOADING
    assert cached_session.status == before_session_status == UploadSessionStatus.UPLOADING
    assert cached_session.finalized_at is None


def test_normalization_job_failure_rolls_back_accepted_source_transaction(
    client: TestClient,
    monkeypatch,
) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "normalization-job-transaction", "duration_seconds": 60},
    ).json()
    session_id, tracks = _create_session_with_parts(client, meeting_id=meeting["meeting_id"])

    async def fail_job_upsert(*_args, **_kwargs):
        raise RuntimeError("simulated normalization job persistence failure")

    monkeypatch.setattr(
        "twobrain_rec_server.ingest.finalize.upsert_playback_normalization_job",
        fail_job_upsert,
    )

    response = _finalize(client, session_id, tracks, str(tracks[0]["sha256"]))

    assert response.status_code == 503
    assert response.json()["code"] == "persistence_unavailable"

    async def persisted_truth():
        async with client.app_state["sessionmaker"]() as db:
            revision = await db.get(MediaRevision, UUID(meeting["media_revision"]["media_revision_id"]))
            artifacts = (
                await db.scalars(
                    select(TrackArtifact).where(
                        TrackArtifact.meeting_id == UUID(meeting["meeting_id"])
                    )
                )
            ).all()
            jobs = (
                await db.scalars(
                    select(PlaybackNormalizationJob).where(
                        PlaybackNormalizationJob.meeting_id == UUID(meeting["meeting_id"])
                    )
                )
            ).all()
            return revision, artifacts, jobs

    revision, artifacts, jobs = asyncio.run(persisted_truth())
    assert revision.status == "pending_upload"
    assert artifacts == []
    assert jobs == []


def _track_artifacts_for_meeting(client: TestClient, meeting_id: str) -> list[tuple[str, int, str]]:
    async def load() -> list[tuple[str, int, str]]:
        async with client.app_state["sessionmaker"]() as db:
            rows = (
                await db.scalars(
                    select(TrackArtifact)
                    .where(TrackArtifact.meeting_id == UUID(meeting_id))
                    .order_by(TrackArtifact.track_role)
                )
            ).all()
            return [(row.track_role, row.byte_length, row.sha256) for row in rows]

    import asyncio

    return asyncio.run(load())
