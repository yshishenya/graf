import asyncio
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

import twobrain_rec_server.ingest.store as store_module
from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.fakes.fake_minio import FailOnceDeleteStorage
from tests.fixtures.artifacts import deterministic_wav_bytes, track_descriptor
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.db.models import Meeting, PurgeJournal, UploadSession
from twobrain_rec_server.ingest.desktop_sync import _mark_expired_if_needed
from twobrain_rec_server.ingest.finalize import (
    _cleanup_materialized_track_objects,
    _lock_finalize_upload_session,
)
from twobrain_rec_server.ingest.lifecycle import expire_upload_session
from twobrain_rec_server.ingest.parts import (
    _delete_or_record_uploaded_object,
    get_session_for_tenant,
)
from twobrain_rec_server.ingest.sessions import create_upload_session
from twobrain_rec_server.ingest.store import (
    InMemoryIngestStore,
    load_meeting_record,
    load_upload_session_record,
)

BOUNDED_DELETE_COPY = "Delete this meeting everywhere GRAF controls."


def _create_meeting(client, local_recording_id: str = "lifecycle") -> dict:
    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": local_recording_id, "duration_seconds": 60},
    )
    assert response.status_code == 200
    return response.json()


def _create_upload_session(
    client, meeting_id: str, expected_track_sizes: dict[str, int] | None = None
) -> dict:
    response = client.post(
        f"/api/v1/meetings/{meeting_id}/upload-sessions",
        headers=auth_headers(),
        json={
            "expected_track_sizes": expected_track_sizes
            or {"manifest": 8, "microphone": 9, "system": 10}
        },
    )
    assert response.status_code == 200
    return response.json()


def _upload_tracks(client, session_id: str) -> list[dict[str, object]]:
    tracks = []
    for size, role in [(8, "manifest"), (9, "microphone"), (10, "system")]:
        data = deterministic_wav_bytes(size)
        digest = sha256(data).hexdigest()
        response = client.put(
            f"/api/v1/upload-sessions/{session_id}/tracks/{role}/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
            content=data,
        )
        assert response.status_code == 200
        tracks.append(track_descriptor(role, size) | {"sha256": digest, "byte_length": size})
    return tracks


def _finalize(client, session_id: str, tracks: list[dict[str, object]]):
    return client.post(
        f"/api/v1/upload-sessions/{session_id}/finalize",
        headers=auth_headers(),
        json={"manifest_sha256": tracks[0]["sha256"], "tracks": tracks},
    )


def test_one_active_upload_session_per_meeting(client) -> None:
    meeting = _create_meeting(client, "lifecycle-one-active")
    first = _create_upload_session(client, meeting["meeting_id"])

    second = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"manifest": 8, "microphone": 9, "system": 10}},
    )

    assert first["status"] == "pending"
    assert second.status_code == 409
    assert second.json()["code"] == "active_upload_session_exists"


def test_concurrent_legacy_session_creation_has_one_winner(client) -> None:
    meeting = _create_meeting(client, "lifecycle-concurrent-create")

    async def run() -> list[tuple[str, str | None]]:
        scope = TenantScope(
            organization_id=ORG_ID,
            workspace_id=WORKSPACE_ID,
            user_id=USER_ID,
            device_id=DEVICE_ID,
        )

        async def create_one() -> tuple[str, str | None]:
            async with client.app_state["sessionmaker"]() as db:
                try:
                    session = await create_upload_session(
                        settings=client.app.state.settings,
                        tenant_scope=scope,
                        db=db,
                        meeting_id=UUID(meeting["meeting_id"]),
                        expected_track_sizes={"manifest": 8, "microphone": 9, "system": 10},
                    )
                    await db.commit()
                    return "ok", str(session.id)
                except ProblemDetail as exc:
                    await db.rollback()
                    return exc.code, None

        return list(await asyncio.gather(create_one(), create_one()))

    outcomes = asyncio.run(run())
    assert sorted(outcome[0] for outcome in outcomes) == ["active_upload_session_exists", "ok"]
    assert len({outcome[1] for outcome in outcomes if outcome[1] is not None}) == 1


def test_create_upload_session_reloads_persisted_meeting_after_store_reset(client) -> None:
    meeting = _create_meeting(client, "lifecycle-cold-meeting")
    store_module.store = InMemoryIngestStore()

    session = _create_upload_session(client, meeting["meeting_id"])

    assert session["meeting_id"] == meeting["meeting_id"]


def test_create_upload_session_persists_meeting_uploading_status(client) -> None:
    meeting = _create_meeting(client, "lifecycle-meeting-status")

    _create_upload_session(client, meeting["meeting_id"])

    async def persisted_status() -> str | None:
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(Meeting.status).where(Meeting.id == UUID(meeting["meeting_id"]))
            )

    import asyncio

    assert asyncio.run(persisted_status()) == "uploading"


def test_get_session_for_tenant_rejects_other_user_even_if_device_matches(client) -> None:
    meeting = _create_meeting(client, "lifecycle-session-user-scope")
    session = _create_upload_session(client, meeting["meeting_id"])

    async def load_with_wrong_user() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await get_session_for_tenant(
                UUID(session["session_id"]),
                TenantScope(
                    organization_id=ORG_ID,
                    workspace_id=WORKSPACE_ID,
                    user_id=uuid4(),
                    device_id=DEVICE_ID,
                ),
                db,
            )

    import asyncio

    with pytest.raises(ProblemDetail) as exc_info:
        asyncio.run(load_with_wrong_user())

    assert exc_info.value.status == 404
    assert exc_info.value.code == "upload_session_not_found"


def test_get_session_for_tenant_rejects_wrong_device_for_owner(client) -> None:
    meeting = _create_meeting(client, "lifecycle-session-device-scope")
    session = _create_upload_session(client, meeting["meeting_id"])

    async def load_with_wrong_device() -> None:
        async with client.app_state["sessionmaker"]() as db:
            await get_session_for_tenant(
                UUID(session["session_id"]),
                TenantScope(
                    organization_id=ORG_ID,
                    workspace_id=WORKSPACE_ID,
                    user_id=USER_ID,
                    device_id=uuid4(),
                ),
                db,
            )

    import asyncio

    with pytest.raises(ProblemDetail) as exc_info:
        asyncio.run(load_with_wrong_device())

    assert exc_info.value.status == 403
    assert exc_info.value.code == "device_scope_denied"


def test_create_upload_session_rejects_deleting_meeting(client) -> None:
    meeting = _create_meeting(client, "lifecycle-deleting-meeting")
    deletion = client.post(
        f"/api/v1/cabinet/meetings/{meeting['meeting_id']}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )
    assert deletion.status_code == 202

    response = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"manifest": 8, "microphone": 9, "system": 10}},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "meeting_deletion_active"


def test_upload_part_rejects_session_after_meeting_deletion_starts(client) -> None:
    meeting = _create_meeting(client, "lifecycle-active-session-then-delete")
    session = _create_upload_session(client, meeting["meeting_id"])
    deletion = client.post(
        f"/api/v1/cabinet/meetings/{meeting['meeting_id']}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )
    assert deletion.status_code == 202
    data = deterministic_wav_bytes(4)
    digest = sha256(data).hexdigest()

    response = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
        content=data,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "meeting_deletion_active"


def test_storage_cleanup_race_keeps_part_and_materialized_keys_in_purge_journal(client) -> None:
    """A failed eager delete remains recoverable after lifecycle rollback."""
    meeting = _create_meeting(client, "lifecycle-cleanup-journal-race")
    meeting_id = UUID(meeting["meeting_id"])
    storage = FailOnceDeleteStorage(client.app_state["storage"])
    part_key = "tests/cleanup-race/part-object"
    materialized_key = "tests/cleanup-race/materialized-object"
    storage.put_bytes(part_key, b"part")
    storage.put_bytes(materialized_key, b"materialized")
    storage.arm(part_key)
    storage.arm(materialized_key)

    async def record_cleanup() -> list[tuple[str, str, str | None]]:
        async with client.app_state["sessionmaker"]() as db:
            await _delete_or_record_uploaded_object(
                storage=storage,
                object_key=part_key,
                db=db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                reason="part_rejected_after_session_removed",
            )
            await _cleanup_materialized_track_objects(
                storage,
                [materialized_key],
                db=db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                reason="finalize_lifecycle_fence_rejected",
            )
            rows = (
                await db.scalars(
                    select(PurgeJournal)
                    .where(
                        PurgeJournal.workspace_id == WORKSPACE_ID,
                        PurgeJournal.meeting_id == meeting_id,
                        PurgeJournal.object_key.in_([part_key, materialized_key]),
                    )
                    .order_by(PurgeJournal.object_key)
                )
            ).all()
            return [(row.object_key, row.state, row.safe_reason) for row in rows]

    journal_rows = asyncio.run(record_cleanup())
    assert journal_rows == [
        (materialized_key, "pending", "finalize_lifecycle_fence_rejected"),
        (part_key, "pending", "part_rejected_after_session_removed"),
    ]
    assert part_key in storage.objects
    assert materialized_key in storage.objects


def test_upload_part_reloads_terminal_session_status_from_db(client) -> None:
    meeting = _create_meeting(client, "lifecycle-db-terminal-session")
    session = _create_upload_session(client, meeting["meeting_id"])

    async def mark_terminal_in_db() -> None:
        async with client.app_state["sessionmaker"]() as db:
            model = await db.get(UploadSession, UUID(session["session_id"]))
            assert model is not None
            model.status = "finalized"
            await db.commit()

    import asyncio

    asyncio.run(mark_terminal_in_db())
    data = deterministic_wav_bytes(4)
    digest = sha256(data).hexdigest()
    response = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
        content=data,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "session_terminal"


def test_finalize_commit_fence_rejects_session_terminalized_after_snapshot(client) -> None:
    meeting = _create_meeting(client, "lifecycle-finalize-fence")
    session = _create_upload_session(client, meeting["meeting_id"])

    async def terminalize_and_check() -> None:
        async with client.app_state["sessionmaker"]() as db:
            model = await db.get(UploadSession, UUID(session["session_id"]))
            assert model is not None
            model.status = "aborted"
            await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            with pytest.raises(ProblemDetail) as raised:
                await _lock_finalize_upload_session(
                    db,
                    session_id=UUID(session["session_id"]),
                    workspace_id=WORKSPACE_ID,
                )
            assert raised.value.code == "session_terminal"

    asyncio.run(terminalize_and_check())


def test_conflicting_meeting_create_is_rejected(client) -> None:
    first = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "lifecycle-meeting-conflict",
            "duration_seconds": 60,
            "title": "Original",
        },
    )
    assert first.status_code == 200

    replay = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "lifecycle-meeting-conflict",
            "duration_seconds": 60,
            "title": "Original",
        },
    )
    conflict = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "lifecycle-meeting-conflict",
            "duration_seconds": 61,
            "title": "Changed",
        },
    )

    assert replay.status_code == 200
    assert replay.json()["meeting_id"] == first.json()["meeting_id"]
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"


def test_upload_session_idempotency_key_replays_matching_request(client) -> None:
    meeting = _create_meeting(client, "lifecycle-session-idempotency")
    headers = auth_headers() | {"Idempotency-Key": "session-create-001"}
    first = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=headers,
        json={"expected_track_sizes": {"system": 4}},
    )
    replay = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=headers,
        json={"expected_track_sizes": {"system": 4}},
    )

    assert first.status_code == 200
    assert replay.status_code == 200
    assert replay.json()["session_id"] == first.json()["session_id"]


def test_upload_session_idempotency_key_conflict_is_rejected(client) -> None:
    meeting = _create_meeting(client, "lifecycle-session-idempotency-conflict")
    headers = auth_headers() | {"Idempotency-Key": "session-create-002"}
    first = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=headers,
        json={"expected_track_sizes": {"system": 4}},
    )
    conflict = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=headers,
        json={"expected_track_sizes": {"system": 5}},
    )

    assert first.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"


def test_expired_session_rejects_upload_finalize_and_abort(client) -> None:
    meeting = _create_meeting(client, "lifecycle-expired")
    session = _create_upload_session(client, meeting["meeting_id"])

    async def expire_session() -> None:
        async with client.app_state["sessionmaker"]() as db:
            model = await db.get(UploadSession, UUID(session["session_id"]))
            assert model is not None
            model.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()

    import asyncio

    asyncio.run(expire_session())
    store_module.store = InMemoryIngestStore()

    data = deterministic_wav_bytes(4)
    digest = sha256(data).hexdigest()
    upload = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
        content=data,
    )
    finalize = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/finalize",
        headers=auth_headers(),
        json={
            "manifest_sha256": "a" * 64,
            "tracks": [
                track_descriptor("manifest", 8) | {"sha256": "a" * 64},
                track_descriptor("microphone", 9),
                track_descriptor("system", 10),
            ],
        },
    )
    abort = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/abort",
        headers=auth_headers(),
        json={"reason": "too late"},
    )

    assert upload.status_code == 409
    assert upload.json()["code"] == "session_expired"
    assert finalize.status_code == 409
    assert finalize.json()["code"] == "session_expired"
    assert abort.status_code == 409
    assert abort.json()["code"] == "session_expired"


def test_terminal_sessions_reject_additional_mutations_and_persist_finalized_at(client) -> None:
    meeting = _create_meeting(client, "lifecycle-terminal")
    session = _create_upload_session(client, meeting["meeting_id"])
    tracks = _upload_tracks(client, session["session_id"])

    finalized = _finalize(client, session["session_id"], tracks)
    assert finalized.status_code == 200

    data = deterministic_wav_bytes(4)
    digest = sha256(data).hexdigest()
    upload = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/1",
        headers=auth_headers() | {"X-Byte-Offset": "10", "X-Content-SHA256": digest},
        content=data,
    )
    abort = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/abort",
        headers=auth_headers(),
        json={"reason": "late abort"},
    )
    replay_finalize = _finalize(client, session["session_id"], tracks)

    async def finalized_at():
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(UploadSession.finalized_at).where(
                    UploadSession.id == UUID(session["session_id"])
                )
            )

    import asyncio

    assert upload.status_code == 409
    assert upload.json()["code"] == "session_terminal"
    assert abort.status_code == 409
    assert abort.json()["code"] == "session_terminal"
    assert replay_finalize.status_code == 409
    assert replay_finalize.json()["code"] == "session_terminal"
    assert asyncio.run(finalized_at()) is not None


def test_expiry_does_not_rewrite_finalized_or_aborted_sessions(client) -> None:
    finalized_meeting = _create_meeting(client, "lifecycle-expiry-finalized")
    finalized_session = _create_upload_session(client, finalized_meeting["meeting_id"])
    finalized_tracks = _upload_tracks(client, finalized_session["session_id"])
    assert _finalize(client, finalized_session["session_id"], finalized_tracks).status_code == 200

    aborted_meeting = _create_meeting(client, "lifecycle-expiry-aborted")
    aborted_session = _create_upload_session(client, aborted_meeting["meeting_id"])
    aborted = client.post(
        f"/api/v1/upload-sessions/{aborted_session['session_id']}/abort",
        headers=auth_headers(),
        json={"reason": "test"},
    )
    assert aborted.status_code == 200

    async def expire_terminal_sessions() -> tuple[str, str, str, str]:
        scope = TenantScope(
            organization_id=ORG_ID,
            workspace_id=WORKSPACE_ID,
            user_id=USER_ID,
            device_id=DEVICE_ID,
        )
        async with client.app_state["sessionmaker"]() as db:
            for session_id in (finalized_session["session_id"], aborted_session["session_id"]):
                model = await db.get(UploadSession, UUID(session_id))
                assert model is not None
                model.expires_at = datetime.now(UTC) - timedelta(minutes=1)
            await db.commit()
        errors: list[str] = []
        for session_id in (finalized_session["session_id"], aborted_session["session_id"]):
            async with client.app_state["sessionmaker"]() as db:
                with pytest.raises(ProblemDetail) as raised:
                    await expire_upload_session(
                        tenant_scope=scope,
                        db=db,
                        session_id=UUID(session_id),
                    )
                errors.append(raised.value.code)
        async with client.app_state["sessionmaker"]() as db:
            persisted_finalized = await db.scalar(
                select(UploadSession.status).where(
                    UploadSession.id == UUID(finalized_session["session_id"])
                )
            )
            persisted_aborted = await db.scalar(
                select(UploadSession.status).where(
                    UploadSession.id == UUID(aborted_session["session_id"])
                )
            )
        assert persisted_finalized is not None and persisted_aborted is not None
        return errors[0], errors[1], persisted_finalized, persisted_aborted

    assert asyncio.run(expire_terminal_sessions()) == (
        "session_terminal",
        "session_terminal",
        "finalized",
        "aborted",
    )


def test_expiry_preserves_metadata_committed_after_stale_sync_snapshot(client) -> None:
    meeting = _create_meeting(client, "lifecycle-expiry-authoritative-metadata")
    session = _create_upload_session(client, meeting["meeting_id"])

    async def expire_from_stale_snapshot() -> tuple[str, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            stale_meeting = await load_meeting_record(db, meeting_id=UUID(meeting["meeting_id"]))
            stale_session = await load_upload_session_record(db, UUID(session["session_id"]))
            assert stale_meeting is not None and stale_session is not None

            async with client.app_state["sessionmaker"]() as writer:
                persisted_meeting = await writer.get(Meeting, UUID(meeting["meeting_id"]))
                persisted_session = await writer.get(UploadSession, UUID(session["session_id"]))
                assert persisted_meeting is not None and persisted_session is not None
                persisted_meeting.title = "Authoritative calendar title"
                persisted_meeting.title_source = "calendar"
                persisted_session.expires_at = datetime.now(UTC) - timedelta(seconds=5)
                await writer.commit()

            conflict = await _mark_expired_if_needed(
                db=db,
                meeting=stale_meeting,
                session=stale_session,
            )
            current_title = await db.scalar(
                select(Meeting.title).where(Meeting.id == UUID(meeting["meeting_id"]))
            )
            return conflict.state.value, current_title

    assert asyncio.run(expire_from_stale_snapshot()) == (
        "upload_session_expired",
        "Authoritative calendar title",
    )


def test_sync_state_copies_authoritative_meeting_when_session_terminalizes_concurrently(
    client,
) -> None:
    meeting = _create_meeting(client, "lifecycle-sync-terminal-authoritative")
    session = _create_upload_session(client, meeting["meeting_id"])

    async def read_from_stale_snapshot() -> tuple[str, str]:
        async with client.app_state["sessionmaker"]() as db:
            stale_meeting = await load_meeting_record(db, meeting_id=UUID(meeting["meeting_id"]))
            stale_session = await load_upload_session_record(db, UUID(session["session_id"]))
            assert stale_meeting is not None and stale_session is not None

            async with client.app_state["sessionmaker"]() as writer:
                persisted_meeting = await writer.get(Meeting, UUID(meeting["meeting_id"]))
                persisted_session = await writer.get(UploadSession, UUID(session["session_id"]))
                assert persisted_meeting is not None and persisted_session is not None
                persisted_meeting.status = "aborted"
                persisted_meeting.title = "Concurrent abort title"
                persisted_session.status = "aborted"
                persisted_session.expires_at = datetime.now(UTC) - timedelta(seconds=5)
                await writer.commit()

            conflict = await _mark_expired_if_needed(
                db=db,
                meeting=stale_meeting,
                session=stale_session,
            )
            return conflict.state.value, stale_meeting.status.value

    assert asyncio.run(read_from_stale_snapshot()) == ("none", "aborted")
