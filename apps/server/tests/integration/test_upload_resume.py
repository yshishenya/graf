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


def test_missing_ranges_uses_expected_track_sizes_from_session(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "resume-missing-ranges", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"microphone": 10, "system": 12}},
    ).json()

    data = deterministic_wav_bytes(4)
    digest = sha256(data).hexdigest()
    response = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
        content=data,
    )
    assert response.status_code == 200

    missing = client.get(
        f"/api/v1/upload-sessions/{session['session_id']}/missing-ranges",
        headers=auth_headers(),
    )

    assert missing.status_code == 200
    assert missing.json()["missing_ranges_by_track"] == {
        "microphone": [{"start": 0, "end": 10}],
        "system": [{"start": 4, "end": 12}],
    }


def test_missing_ranges_use_byte_intervals_for_gaps_and_out_of_order_parts(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "resume-interval-gaps", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"system": 12}},
    ).json()

    tail = deterministic_wav_bytes(4)
    tail_digest = sha256(tail).hexdigest()
    assert (
        client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/1",
            headers=auth_headers() | {"X-Byte-Offset": "8", "X-Content-SHA256": tail_digest},
            content=tail,
        ).status_code
        == 200
    )
    head = deterministic_wav_bytes(4)
    head_digest = sha256(head).hexdigest()
    assert (
        client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": head_digest},
            content=head,
        ).status_code
        == 200
    )

    missing = client.get(
        f"/api/v1/upload-sessions/{session['session_id']}/missing-ranges",
        headers=auth_headers(),
    )

    assert missing.status_code == 200
    assert missing.json()["missing_ranges_by_track"] == {"system": [{"start": 4, "end": 8}]}


def test_upload_rejects_negative_and_overlapping_ranges(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "resume-invalid-ranges", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"system": 12}},
    ).json()
    data = deterministic_wav_bytes(4)
    digest = sha256(data).hexdigest()

    negative = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "-1", "X-Content-SHA256": digest},
        content=data,
    )
    accepted = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
        content=data,
    )
    overlap = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/1",
        headers=auth_headers() | {"X-Byte-Offset": "2", "X-Content-SHA256": digest},
        content=data,
    )
    replay_wrong_offset = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "1", "X-Content-SHA256": digest},
        content=data,
    )

    assert negative.status_code == 400
    assert negative.json()["code"] == "invalid_byte_offset"
    assert accepted.status_code == 200
    assert overlap.status_code == 409
    assert overlap.json()["code"] == "range_overlap"
    assert replay_wrong_offset.status_code == 409
    assert replay_wrong_offset.json()["code"] == "range_conflict"


def test_upload_rejects_expected_size_and_package_limit_violations(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "resume-size-limits", "duration_seconds": 60},
    ).json()
    invalid_session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"system": -1}},
    )
    assert invalid_session.status_code == 400
    assert invalid_session.json()["code"] == "invalid_expected_track_size"

    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"system": 4}},
    ).json()
    data = deterministic_wav_bytes(5)
    digest = sha256(data).hexdigest()
    oversized = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
        content=data,
    )

    assert oversized.status_code == 409
    assert oversized.json()["code"] == "expected_track_size_exceeded"


def test_upload_rejects_cumulative_package_limit_before_accepting_part(client) -> None:
    client.app.state.settings.max_package_bytes = 6
    client.app.state.settings.max_track_bytes = 100
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "resume-package-limit", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"microphone": 4, "system": 4}},
    ).json()
    first = deterministic_wav_bytes(4)
    first_digest = sha256(first).hexdigest()
    assert (
        client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/microphone/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": first_digest},
            content=first,
        ).status_code
        == 200
    )

    second = deterministic_wav_bytes(4)
    second_digest = sha256(second).hexdigest()
    rejected = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": second_digest},
        content=second,
    )

    assert rejected.status_code == 413
    assert rejected.json()["code"] == "package_bytes_exceeded"


def test_upload_storage_failure_returns_problem_response(client) -> None:
    class FailingStorage:
        def put_stream(self, _object_key, _stream, _length) -> None:
            raise RuntimeError("storage unavailable")

    client.app.state.storage = FailingStorage()
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "resume-storage-failure", "duration_seconds": 60},
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

    assert response.status_code == 503
    assert response.json()["code"] == "storage_unavailable"
