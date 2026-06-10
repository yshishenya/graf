from hashlib import sha256

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.artifacts import deterministic_wav_bytes


def test_aborted_session_rejects_later_part_upload(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "abort-truth", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={},
    ).json()
    abort = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/abort",
        headers=auth_headers(),
        json={"reason": "user_cancelled"},
    )
    assert abort.status_code == 200
    assert abort.json()["status"] == "aborted"
    data = deterministic_wav_bytes(64)
    digest = sha256(data).hexdigest()
    upload = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/microphone/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
        content=data,
    )
    assert upload.status_code == 409
    assert upload.json()["code"] == "session_terminal"
