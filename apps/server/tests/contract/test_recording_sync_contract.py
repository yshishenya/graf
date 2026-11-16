from __future__ import annotations

from fastapi.testclient import TestClient

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.recording_sync import revision_aware_recording_fixture


def test_openapi_exposes_desktop_recording_sync_state(client: TestClient) -> None:
    openapi = client.get("/openapi.json").json()
    path = "/api/v1/desktop/recordings/{local_recording_id}/sync-state"

    assert path in openapi["paths"]
    assert "get" in openapi["paths"][path]

    response_schema = openapi["paths"][path]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    schema_name = response_schema["$ref"].split("/")[-1]
    properties = openapi["components"]["schemas"][schema_name]["properties"]
    upload_session_properties = openapi["components"]["schemas"]["DesktopSyncUploadSessionState"]["properties"]
    meeting_properties = openapi["components"]["schemas"]["DesktopSyncMeetingState"]["properties"]

    for field in [
        "local_recording_id",
        "local_media_revision_id",
        "meeting",
        "media_revision",
        "upload_session",
        "processing",
        "review",
        "playback",
        "finalized_upload",
        "conflict",
    ]:
        assert field in properties
    assert "accepted_bytes_by_track" in upload_session_properties
    assert "missing_ranges_by_track" in upload_session_properties
    assert "expected_tracks" in upload_session_properties
    assert "desktop_truth_rule" in upload_session_properties
    assert not {"media_revision_id", "archive_audio", "finalized_at"} & upload_session_properties.keys()
    assert "retention" in meeting_properties

    playback_properties = openapi["components"]["schemas"]["DesktopPlaybackProof"]["properties"]
    assert playback_properties["can_play"]["default"] is False
    assert playback_properties["object_verified"]["default"] is False
    assert playback_properties["reason_code"]["default"] == "no_audio"
    assert "local_media_revision_id" in playback_properties
    finalized_properties = openapi["components"]["schemas"][
        "DesktopSyncFinalizedUploadState"
    ]["properties"]
    assert {
        "session_id",
        "media_revision_id",
        "local_media_revision_id",
        "archive_audio",
        "finalized_at",
        "status",
    } == finalized_properties.keys()
    assert finalized_properties["status"]["default"] == "finalized"
    retention_properties = openapi["components"]["schemas"]["DesktopSyncRetentionState"]["properties"]
    assert retention_properties["policy_state"]["default"] == "not_configured"
    assert "delete_after" in retention_properties


def test_ingest_responses_include_media_revision_identity(client: TestClient) -> None:
    fixture = revision_aware_recording_fixture("contract-revision-001")
    meeting_response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": fixture.local_recording_id,
            "local_media_revision_id": fixture.local_media_revision_id,
            "duration_seconds": 60,
        },
    )
    assert meeting_response.status_code == 200
    meeting = meeting_response.json()

    assert meeting["local_media_revision_id"] == fixture.local_media_revision_id
    assert meeting["media_revision"]["revision_number"] == 1
    assert meeting["media_revision"]["source_kind"] == "initial_mixed_recording"
