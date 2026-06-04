from hashlib import sha256

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.artifacts import deterministic_wav_bytes


def test_interrupted_upload_can_report_status_and_replay_part(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "resume", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={},
    ).json()
    data = deterministic_wav_bytes(64)
    digest = sha256(data).hexdigest()
    path = f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/0"
    assert client.put(path, headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest}, content=data).status_code == 200
    status = client.get(f"/api/v1/upload-sessions/{session['session_id']}", headers=auth_headers())
    assert status.status_code == 200
    assert status.json()["accepted_bytes_by_track"]["system"] == 64
    replay = client.put(path, headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest}, content=data)
    assert replay.status_code == 200
