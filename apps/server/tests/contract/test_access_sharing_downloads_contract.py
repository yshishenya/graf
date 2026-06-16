def test_access_sharing_downloads_openapi_contract_is_exposed(client) -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]

    expected_operations = {
        "/api/v1/cabinet/meetings/{meeting_id}/access": "getMeetingAccessState",
        "/api/v1/cabinet/meetings/{meeting_id}/activity": "listMeetingAccessActivity",
        "/api/v1/cabinet/meetings/{meeting_id}/shares": "createMeetingShareGrant",
        "/api/v1/cabinet/meetings/{meeting_id}/shares/{grant_id}": "revokeMeetingShareGrant",
        "/api/v1/cabinet/share/{share_token}": "resolveLoginRequiredShareLink",
        "/api/v1/cabinet/meetings/{meeting_id}/downloads/{artifact_class}": "downloadMeetingArtifact",
        "/api/v1/cabinet/meetings/{meeting_id}/exports": "createMeetingExportPackage",
        "/api/v1/cabinet/meetings/{meeting_id}/exports/{export_id}/download": "downloadMeetingExportPackage",
    }

    for path, operation_id in expected_operations.items():
        assert path in paths
        path_operations = paths[path]
        assert any(operation["operationId"] == operation_id for operation in path_operations.values())


def test_cabinet_list_contract_accepts_access_filter(client) -> None:
    schema = client.get("/openapi.json").json()
    parameters = schema["paths"]["/api/v1/cabinet/meetings"]["get"]["parameters"]

    assert any(parameter["name"] == "access" and parameter["in"] == "query" for parameter in parameters)
