from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.processing import create_finalized_meeting


def test_processing_slice_does_not_expose_dashboard_share_download_delete_or_assisted_recording(client) -> None:
    finalized = create_finalized_meeting(client, "processing-boundaries")
    meeting_id = finalized["meeting"]["meeting_id"]
    absent_paths = [
        f"/api/v1/meetings/{meeting_id}/dashboard",
        f"/api/v1/meetings/{meeting_id}/share",
        f"/api/v1/meetings/{meeting_id}/download",
        f"/api/v1/meetings/{meeting_id}/delete",
        f"/api/v1/meetings/{meeting_id}/assisted-recording",
        f"/api/v1/meetings/{meeting_id}/processing/transcript",
    ]
    for path in absent_paths:
        response = client.get(path, headers=auth_headers())
        assert response.status_code == 404
