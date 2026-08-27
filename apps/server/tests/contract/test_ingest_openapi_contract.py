from hashlib import sha256
from pathlib import Path

from fastapi.testclient import TestClient

from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.artifacts import deterministic_wav_bytes, track_descriptor


def auth_headers() -> dict[str, str]:
    return {
        "X-Organization-Id": str(ORG_ID),
        "X-Workspace-Id": str(WORKSPACE_ID),
        "X-User-Id": str(USER_ID),
        "X-Device-Id": str(DEVICE_ID),
    }


def test_normalization_remains_internal_to_existing_accepted_ingest_routes(
    client: TestClient,
) -> None:
    paths = client.app.openapi()["paths"]
    forbidden_mutation_fragments = (
        "/normalization",
        "/normalize",
        "/reprocess",
        "/backfill",
        "/playback/retry",
    )

    assert not any(fragment in path for path in paths for fragment in forbidden_mutation_fragments)
    assert set(paths["/api/v1/media-uploads"]) == {"post"}
    assert set(paths["/api/v1/upload-sessions/{session_id}/finalize"]) == {"post"}
    assert set(paths["/api/v1/internal/processing/pickup"]) == {"post"}


def test_openapi_declares_v5_mixed_recording_source_without_provider_details(
    client: TestClient,
) -> None:
    schema = client.app.openapi()
    source_kind = schema["components"]["schemas"]["MediaRevisionSourceKind"]

    assert "initial_mixed_recording" in source_kind["enum"]
    assert "single_wav_v1" in str(schema)
    assert "mediascribe_api_key" not in str(schema).lower()
    assert "external_job_id" not in str(schema)


def test_v5_integration_document_separates_active_wav_from_historical_dual_drain() -> None:
    document = (
        Path(__file__).resolve().parents[4]
        / "docs"
        / "integrations"
        / "mediascribe-dual-track-api.md"
    ).read_text(encoding="utf-8")

    assert "## Active v5 contract" in document
    assert "`meeting-transcription.wav`" in document
    assert "`meeting-review.m4a`" in document
    assert "`meeting-review.m4a` is never sent to MediaScribe" in document
    assert "POST /v1/audio/transcriptions" in document
    assert "## Historical dual compatibility drain" in document
    assert "`initial_mixed_recording`" in document
    assert "cannot be selected by a new v5 writer" in document


def test_happy_path_contract_exposes_server_mediated_ingest(client: TestClient) -> None:
    meeting_response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "local-001",
            "title": "Contract test",
            "duration_seconds": 1800,
        },
    )
    assert meeting_response.status_code == 200
    meeting = meeting_response.json()

    session_response = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_tracks": ["manifest", "microphone", "system"]},
    )
    assert session_response.status_code == 200
    session = session_response.json()
    assert session["upload_strategy"] == "server_mediated"

    uploaded_tracks = []
    for index, role in enumerate(["manifest", "microphone", "system"]):
        data = deterministic_wav_bytes(128 + index)
        digest = sha256(data).hexdigest()
        part_response = client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/{role}/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
            content=data,
        )
        assert part_response.status_code == 200
        uploaded_tracks.append(
            track_descriptor(role, len(data)) | {"sha256": digest, "byte_length": len(data)}
        )

    finalize_response = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/finalize",
        headers=auth_headers(),
        json={"manifest_sha256": uploaded_tracks[0]["sha256"], "tracks": uploaded_tracks},
    )
    assert finalize_response.status_code == 200
    finalized = finalize_response.json()
    assert finalized["meeting"]["status"] == "ingested_pending_processing"
    assert finalized["workflow_started"] is False
    assert finalized["mediascribe_job_created"] is False
    assert finalized["upload_session"]["workflow_id"] is None
    assert finalized["upload_session"]["mediascribe_job_id"] is None


def test_finalize_contract_exposes_processing_start_when_enabled(client: TestClient) -> None:
    client.app.state.settings.processing_enabled = True
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.temporal_client = FakeTemporalClient()
    meeting_response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "local-processing-enabled",
            "duration_seconds": 1800,
        },
    )
    assert meeting_response.status_code == 200
    meeting = meeting_response.json()

    session_response = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_tracks": ["manifest", "microphone", "system"]},
    )
    assert session_response.status_code == 200
    session = session_response.json()

    uploaded_tracks = []
    for index, role in enumerate(["manifest", "microphone", "system"]):
        data = deterministic_wav_bytes(128 + index)
        digest = sha256(data).hexdigest()
        part_response = client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/{role}/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
            content=data,
        )
        assert part_response.status_code == 200
        uploaded_tracks.append(
            track_descriptor(role, len(data)) | {"sha256": digest, "byte_length": len(data)}
        )

    finalize_response = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/finalize",
        headers=auth_headers(),
        json={"manifest_sha256": uploaded_tracks[0]["sha256"], "tracks": uploaded_tracks},
    )
    assert finalize_response.status_code == 200
    finalized = finalize_response.json()
    assert finalized["meeting"]["status"] == "ingested_pending_processing"
    assert finalized["meeting"]["processing_status"] == "workflow_started"
    assert finalized["workflow_started"] is True
    assert finalized["mediascribe_job_created"] is False


def test_manual_media_upload_contract_is_server_mediated_without_dependency_leaks(
    client: TestClient,
) -> None:
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.settings.playback_normalization_automatic_dispatch_enabled = True
    schema = client.app.openapi()
    media_upload = schema["paths"]["/api/v1/media-uploads"]["post"]
    request_body = media_upload["requestBody"]["content"]
    assert "multipart/form-data" in request_body
    response_schema = str(media_upload["responses"])
    assert "storage_object_key" not in response_schema
    assert "external_job_id" not in response_schema
    assert "mediascribe_job_id" not in response_schema

    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "title": "Manual upload",
            "duration_seconds": "60",
            "local_recording_id": "manual-contract-001",
        },
        files={"file": ("meeting.wav", deterministic_wav_bytes(96), "audio/wav")},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["request_mode"] == "single_track"
    assert body["upload_session"]["expected_tracks"] == ["manifest", "media"]
    assert "storage_object_key" not in str(body)
    assert "external_job_id" not in str(body)


def test_cabinet_manual_media_upload_contract_is_multipart_and_csrf_safe(
    client: TestClient,
) -> None:
    schema = client.app.openapi()
    operation = schema["paths"]["/api/v1/cabinet/media-uploads"]["post"]
    request_body = operation["requestBody"]["content"]
    operation_dump = str(operation)

    assert operation["operationId"] == "createCabinetManualMediaUpload"
    assert "multipart/form-data" in request_body
    assert "ManualMediaUploadResponse" in operation_dump
    assert "X-CSRF-Token" not in operation_dump
    assert "storage_object_key" not in operation_dump
    assert "external_job_id" not in operation_dump
    assert "mediascribe_job_id" not in operation_dump
