from hashlib import sha256

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.artifacts import deterministic_wav_bytes


def create_session(client):
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "idempotency", "duration_seconds": 60},
    ).json()
    return client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={},
    ).json()


def test_matching_retry_is_idempotent(client) -> None:
    session = create_session(client)
    data = deterministic_wav_bytes(64)
    digest = sha256(data).hexdigest()
    path = f"/api/v1/upload-sessions/{session['session_id']}/tracks/microphone/parts/0"
    first = client.put(path, headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest}, content=data)
    second = client.put(path, headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest}, content=data)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["sha256"] == digest


def test_conflicting_retry_is_rejected(client) -> None:
    session = create_session(client)
    data = deterministic_wav_bytes(64)
    digest = sha256(data).hexdigest()
    path = f"/api/v1/upload-sessions/{session['session_id']}/tracks/microphone/parts/0"
    assert client.put(path, headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest}, content=data).status_code == 200
    other = b"other"
    other_digest = sha256(other).hexdigest()
    conflict = client.put(path, headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": other_digest}, content=other)
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "checksum_conflict"
