from hashlib import sha256

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.artifacts import deterministic_wav_bytes


def test_ingest_responses_do_not_expose_storage_or_processing_credentials(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "no-egress", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={},
    ).json()
    serialized = str(session).lower()
    assert "minio" not in serialized
    assert "signed" not in serialized
    assert session["workflow_id"] is None
    assert session["mediascribe_job_id"] is None

    data = deterministic_wav_bytes(32)
    digest = sha256(data).hexdigest()
    response = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/microphone/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
        content=data,
    )
    assert "object_key" not in response.text
    assert "credential" not in response.text.lower()
