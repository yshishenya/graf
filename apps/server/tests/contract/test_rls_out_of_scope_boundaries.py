from __future__ import annotations

from tests.contract.test_auth_contracts import auth_headers


def test_rls_slice_does_not_add_dashboard_share_download_retention_or_deletion_routes(client) -> None:
    forbidden_paths = [
        "/api/v1/dashboard/meetings/example",
        "/api/v1/meetings/example/dashboard",
        "/api/v1/meetings/example/share",
        "/api/v1/meetings/example/download",
        "/api/v1/meetings/example/retention",
        "/api/v1/meetings/example/delete",
        "/api/v1/admin/tenant-isolation",
        "/api/v1/billing",
    ]

    for path in forbidden_paths:
        response = client.get(path, headers=auth_headers())
        assert response.status_code == 404


def test_rls_slice_does_not_add_desktop_capture_or_mediascribe_direct_routes(client) -> None:
    forbidden_paths = [
        "/api/v1/desktop/capture/start",
        "/api/v1/desktop/upload/direct",
        "/api/v1/mediascribe/direct-submit",
    ]

    for path in forbidden_paths:
        response = client.post(path, headers=auth_headers(), json={})
        assert response.status_code == 404
