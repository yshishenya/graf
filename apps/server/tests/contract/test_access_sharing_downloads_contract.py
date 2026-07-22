def test_access_sharing_downloads_openapi_contract_is_exposed(client) -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]

    expected_operations = {
        "/api/v1/cabinet/meetings/{meeting_id}/access": "getMeetingAccessState",
        "/api/v1/cabinet/meetings/{meeting_id}/activity": "listMeetingAccessActivity",
        "/api/v1/cabinet/meetings/{meeting_id}/shares": "createMeetingShareGrant",
        "/api/v1/cabinet/meetings/{meeting_id}/shares/{grant_id}": "revokeMeetingShareGrant",
        "/api/v1/cabinet/meetings/{meeting_id}/shares/{grant_id}/rotate": "rotateMeetingShareLink",
        "/api/v1/cabinet/share-recipients": "searchMeetingShareRecipients",
        "/api/v1/cabinet/meetings/{meeting_id}/share-invitations": "createMeetingShareInvitation",
        "/api/v1/cabinet/meetings/{meeting_id}/share-invitations/{invitation_id}": "revokeMeetingShareInvitation",
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


def test_artifact_egress_contract_keeps_download_export_actions_bounded(client) -> None:
    schema = client.get("/openapi.json").json()
    artifact_schema = schema["components"]["schemas"]["ArtifactEgressState"]

    assert artifact_schema["properties"]["artifact_class"]["type"] == "string"
    assert artifact_schema["properties"]["state"]["type"] == "string"
    assert artifact_schema["properties"]["action"]["enum"] == ["download", "export", "disabled"]
    assert "public_link" not in artifact_schema["properties"]
