from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.processing import create_finalized_meeting


def test_processing_status_denies_foreign_workspace_context(client) -> None:
    finalized = create_finalized_meeting(client, "processing-tenant")
    meeting_id = finalized["meeting"]["meeting_id"]
    headers = auth_headers() | {
        "X-Workspace-Id": "99999999-0000-0000-0000-000000000001",
        "X-Device-Id": "99999999-0000-0000-0000-000000000002",
    }
    response = client.get(f"/api/v1/meetings/{meeting_id}/processing", headers=headers)
    assert response.status_code == 403


def test_processing_status_unknown_meeting_returns_not_found(client) -> None:
    response = client.get(
        "/api/v1/meetings/99999999-0000-0000-0000-000000000003/processing",
        headers=auth_headers(),
    )
    assert response.status_code == 404
