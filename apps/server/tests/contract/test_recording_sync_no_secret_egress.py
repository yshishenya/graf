from __future__ import annotations

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.processing import create_finalized_meeting

FORBIDDEN_RESPONSE_MARKERS = [
    "rawAudio",
    "transcriptText",
    "meetingContent",
    "storage_object_key",
    "signed_url",
    "signedUrl",
    "Authorization",
    "Bearer ",
    "mediaScribeApiKey",
    "minio_secret",
    "/Users/",
]


def test_recording_sync_state_response_is_metadata_only(client) -> None:
    local_id = "no-secret-sync-001"
    create_finalized_meeting(client, local_id)

    response = client.get(
        f"/api/v1/desktop/recordings/{local_id}/sync-state",
        headers=auth_headers(),
        params={"local_media_revision_id": f"{local_id}--initial"},
    )

    assert response.status_code == 200
    assert response.json()["media_revision"]["media_revision_id"] is not None
    for marker in FORBIDDEN_RESPONSE_MARKERS:
        assert marker not in response.text


def test_recording_sync_uploaded_review_surface_does_not_expose_private_dependency_ids(client) -> None:
    local_id = "no-secret-review-001"
    finalized = create_finalized_meeting(client, local_id)
    meeting_id = finalized["meeting"]["meeting_id"]

    response = client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["provenance"]["media_revision_id"] == finalized["meeting"]["media_revision"]["media_revision_id"]
    for marker in FORBIDDEN_RESPONSE_MARKERS:
        assert marker not in response.text
