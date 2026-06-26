from hashlib import sha256

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.artifacts import deterministic_wav_bytes

LEGACY_UI_ACTIONS = {"manual_review", "stop_upload", "retry_later", "retry_future", "open_desktop_queue"}


def _assert_problem_custody_contract(body: dict[str, object]) -> None:
    assert body["custody_owner"] in {
        "product_automatic",
        "meeting_owner",
        "workspace_admin",
        "support",
        "policy_lifecycle",
    }
    assert body["retry_class"] in {
        "automatic",
        "paused_until_user_action",
        "paused_until_admin_action",
        "not_retryable",
        "terminal",
    }
    assert body["normal_user_action"] in {
        "none",
        "sign_in",
        "choose_workspace",
        "grant_permission",
        "open_review",
        "open_diagnostics",
        "copy_safe_report",
        "delete_local_copy",
    }
    assert body["normal_user_action"] not in LEGACY_UI_ACTIONS
    assert body["metadata_safety"] == "metadata_only"


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
    body = upload.json()
    assert body["code"] == "session_terminal"
    _assert_problem_custody_contract(body)


def test_storage_failure_problem_uses_custody_contract_not_legacy_actions(client) -> None:
    class FailingStorage:
        def put_stream(self, _object_key, _stream, _length) -> None:
            raise RuntimeError("storage unavailable")

    client.app.state.storage = FailingStorage()
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "custody-storage-failure", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"microphone": 64}},
    ).json()
    data = deterministic_wav_bytes(64)
    digest = sha256(data).hexdigest()
    upload = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/microphone/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
        content=data,
    )

    assert upload.status_code == 503
    body = upload.json()
    assert body["code"] == "storage_unavailable"
    _assert_problem_custody_contract(body)
    assert body["custody_owner"] == "product_automatic"
    assert body["normal_user_action"] == "none"
