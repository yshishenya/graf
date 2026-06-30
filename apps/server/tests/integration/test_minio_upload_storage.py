from hashlib import sha256

from sqlalchemy import select

import twobrain_rec_server.ingest.store as store_module
from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.artifacts import deterministic_wav_bytes
from twobrain_rec_server.db.models import TemporaryUploadObject


def test_upload_part_writes_bytes_to_storage_not_process_session_state(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "minio-001", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"system": 16}},
    ).json()
    data = deterministic_wav_bytes(16)
    digest = sha256(data).hexdigest()

    response = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
        content=data,
    )

    assert response.status_code == 200
    assert list(client.app_state["storage"].objects.values()) == [data]
    stored_session = store_module.store.sessions.get(session["session_id"])
    assert stored_session is None or all(part.data == b"" for part in stored_session.parts.values())


def test_upload_part_creates_temporary_cleanup_accounting(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "minio-cleanup-accounting", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"system": 4}},
    ).json()
    data = deterministic_wav_bytes(4)
    digest = sha256(data).hexdigest()

    response = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
        content=data,
    )
    assert response.status_code == 200

    async def temporary_objects() -> list[TemporaryUploadObject]:
        async with client.app_state["sessionmaker"]() as db:
            return list((await db.scalars(select(TemporaryUploadObject))).all())

    import asyncio

    rows = asyncio.run(temporary_objects())
    assert len(rows) == 1
    assert rows[0].object_role == "accepted_part"
    assert rows[0].cleanup_status == "pending"
    assert rows[0].failure_reason is None
    assert rows[0].last_error is None
    assert rows[0].byte_length == 4


def test_upload_part_marks_orphaned_cleanup_accounting_after_persistence_failure(client, monkeypatch) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "minio-orphan-accounting", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"system": 4}},
    ).json()
    data = deterministic_wav_bytes(4)
    digest = sha256(data).hexdigest()

    async def fail_persist_upload_part(*_args, **_kwargs) -> None:
        raise RuntimeError("simulated database write failure")

    monkeypatch.setattr(
        "twobrain_rec_server.ingest.parts.persist_upload_part",
        fail_persist_upload_part,
    )

    response = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
        content=data,
    )

    assert response.status_code == 503
    assert response.json()["code"] == "persistence_unavailable"

    async def temporary_objects() -> list[TemporaryUploadObject]:
        async with client.app_state["sessionmaker"]() as db:
            return list((await db.scalars(select(TemporaryUploadObject))).all())

    import asyncio

    rows = asyncio.run(temporary_objects())
    assert len(rows) == 1
    assert rows[0].cleanup_status == "orphaned"
    assert rows[0].failure_reason == "db_persistence_failed_after_object_write"
    assert rows[0].last_error == "RuntimeError"
    assert rows[0].storage_object_key in client.app_state["storage"].objects
