from hashlib import sha256
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text

import twobrain_rec_server.ingest.store as store_module
from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.artifacts import track_descriptor
from twobrain_rec_server.db.models import MediaRevision, Meeting, UploadSession


def _saved_historical_session(client, *, old_roles: bool, newer_revision: bool):
    """Seed pre-upgrade state directly; no public producer of old uploads."""
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "historical-admission",
            "duration_seconds": 60,
            "source_kind": "initial_mixed_recording",
            "media_scribe_source_mode": "single_wav_v1",
        },
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_tracks": ["manifest", "media", "playback"]},
    ).json()
    data = b"{}"
    digest = sha256(data).hexdigest()
    assert (
        client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/manifest/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
            content=data,
        ).status_code
        == 200
    )

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            model = await db.get(UploadSession, UUID(session["session_id"]))
            revision = await db.get(MediaRevision, model.media_revision_id)
            revision.source_kind = "initial_recording"
            if old_roles:
                model.expected_track_roles = ["manifest", "microphone", "system"]
            if newer_revision:
                db.add(
                    MediaRevision(
                        id=uuid4(),
                        workspace_id=revision.workspace_id,
                        meeting_id=revision.meeting_id,
                        local_media_revision_id="newer-supported",
                        revision_number=2,
                        source_kind="initial_mixed_recording",
                        status="pending_upload",
                        duration_seconds=60,
                        immutable=False,
                    )
                )
            await db.commit()

    client.portal.call(seed)
    # Simulate restart: admission must use durable session provenance.
    store_module.store = store_module.InMemoryIngestStore()
    return meeting, session, data, digest


@pytest.mark.parametrize("mode", [None, "dual", "single_wav_v1"])
def test_new_historical_meeting_is_rejected(client, mode):
    payload = {
        "local_recording_id": "old-client",
        "duration_seconds": 60,
        "source_kind": "initial_recording",
    }
    if mode is not None:
        payload["media_scribe_source_mode"] = mode
    response = client.post("/api/v1/meetings", headers=auth_headers(), json=payload)
    assert response.status_code in {400, 422}
    assert not store_module.store.meetings


@pytest.mark.parametrize(
    "old_roles,newer_revision", [(True, False), (False, False), (True, True), (False, True)]
)
def test_historical_session_cannot_resume_or_finalize_after_restart(
    client, old_roles, newer_revision
):
    meeting, session, data, digest = _saved_historical_session(
        client,
        old_roles=old_roles,
        newer_revision=newer_revision,
    )
    objects_before = dict(client.app_state["storage"].objects)
    # Even an identical replay of an already accepted manifest must fail.
    for role, part_number in [("manifest", 0), ("manifest", 1), ("microphone", 0), ("media", 0)]:
        response = client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/{role}/parts/{part_number}",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
            content=data,
        )
        assert response.status_code == 400
        assert response.json()["code"] == "unsupported_recording_source_kind"
    finalize = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/finalize",
        headers=auth_headers(),
        json={
            "manifest_sha256": digest,
            "tracks": [
                track_descriptor(role, data=data) for role in ("manifest", "media", "playback")
            ],
        },
    )
    assert finalize.status_code == 400
    assert finalize.json()["code"] == "unsupported_recording_source_kind"
    assert client.app_state["storage"].objects == objects_before
    read = client.get(f"/api/v1/upload-sessions/{session['session_id']}", headers=auth_headers())
    assert read.status_code == 200
    assert read.json()["expected_tracks"] == (
        ["manifest", "microphone", "system"] if old_roles else ["manifest", "media", "playback"]
    )
    abort = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/abort",
        headers=auth_headers(),
        json={"reason": "user_cancelled"},
    )
    assert abort.status_code == 200

    async def source_kind():
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(MediaRevision.source_kind).where(
                    MediaRevision.id == UUID(session["media_revision_id"])
                )
            )

    assert client.portal.call(source_kind) == "initial_recording"


def test_new_revision_rejects_historical_source_and_roles(client):
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "revision-admission", "duration_seconds": 60},
    ).json()
    for source, roles in [
        ("initial_recording", ["manifest", "microphone", "system"]),
        ("initial_recording", ["manifest", "media", "playback"]),
        ("reprocess", ["manifest", "microphone", "system"]),
    ]:
        response = client.post(
            f"/api/v1/meetings/{meeting['meeting_id']}/media-revisions/upload-sessions",
            headers=auth_headers(),
            json={
                "local_media_revision_id": "rejected",
                "source_kind": source,
                "duration_seconds": 60,
                "expected_tracks": roles,
            },
        )
        assert response.status_code == 400


def test_new_session_for_historical_meeting_is_rejected(client):
    meeting, session, _, _ = _saved_historical_session(client, old_roles=True, newer_revision=False)
    for roles in (["manifest", "microphone", "system"], ["manifest", "media", "playback"]):
        response = client.post(
            f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
            headers=auth_headers(),
            json={"expected_tracks": roles},
        )
        assert response.status_code == 400


def test_default_meeting_and_session_are_v5(client):
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "defaults-v5", "duration_seconds": 60},
    ).json()
    assert meeting["media_revision"]["source_kind"] == "initial_mixed_recording"
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={},
    )
    assert session.status_code == 200
    assert session.json()["expected_tracks"] == ["manifest", "media", "playback"]


def test_database_revision_default_does_not_rewrite_historical_rows(client):
    meeting, session, _, _ = _saved_historical_session(client, old_roles=True, newer_revision=False)

    async def insert_with_database_default():
        async with client.app_state["sessionmaker"]() as db:
            # Raw SQL deliberately bypasses the ORM default and exercises migration 0099.
            source = await db.scalar(
                text(
                    "INSERT INTO media_revisions "
                    "(id, workspace_id, meeting_id, local_media_revision_id, revision_number, duration_seconds) "
                    "VALUES (:id, :workspace, :meeting, :local_id, 2, 60) RETURNING source_kind"
                ),
                {
                    "id": uuid4(),
                    "workspace": WORKSPACE_ID,
                    "meeting": UUID(meeting["meeting_id"]),
                    "local_id": "database-default-v5",
                },
            )
            old_source = await db.scalar(
                select(MediaRevision.source_kind).where(
                    MediaRevision.id == UUID(session["media_revision_id"])
                )
            )
            await db.commit()
            return source, old_source

    assert client.portal.call(insert_with_database_default) == (
        "initial_mixed_recording",
        "initial_recording",
    )


def test_meeting_without_revision_keeps_historical_read_fallback(client):
    meeting_id = uuid4()

    async def read_saved_meeting():
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                Meeting(
                    id=meeting_id,
                    workspace_id=WORKSPACE_ID,
                    created_by_user_id=USER_ID,
                    device_id=DEVICE_ID,
                    local_recording_id="historical-no-revision",
                    duration_seconds=60,
                    status="draft",
                    processing_status="not_submitted",
                )
            )
            await db.commit()
            record = await store_module.load_meeting_record(db, meeting_id=meeting_id)
            return record.media_revision_source_kind.value

    assert client.portal.call(read_saved_meeting) == "initial_recording"
    response = client.post(
        f"/api/v1/meetings/{meeting_id}/upload-sessions",
        headers=auth_headers(),
        json={},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "unsupported_recording_source_kind"
