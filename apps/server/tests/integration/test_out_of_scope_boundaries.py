from tests.contract.test_ingest_openapi_contract import auth_headers


def test_dashboard_share_download_and_deletion_endpoints_are_absent(client) -> None:
    for path in [
        "/api/v1/meetings/example/transcript",
        "/api/v1/meetings/example/summary",
        "/api/v1/meetings/example/audio",
        "/api/v1/meetings/example/share",
        "/api/v1/meetings/example/delete",
        "/api/v1/dashboard/meetings/example",
        "/api/v1/assisted-recording/start",
    ]:
        response = client.get(path, headers=auth_headers())
        assert response.status_code == 404
