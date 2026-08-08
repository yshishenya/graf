import inspect

import pytest
from pydantic import ValidationError

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import ContentExportSelectionRequest
from twobrain_rec_server.cabinet.egress import create_content_export
from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app


def test_content_export_routes_are_additive_to_legacy_download_and_package_routes() -> None:
    paths = create_app(Settings()).openapi()["paths"]

    assert "/api/v1/cabinet/meetings/{meeting_id}/content-exports" in paths
    assert set(paths["/api/v1/cabinet/meetings/{meeting_id}/content-exports"]) == {
        "get",
        "post",
    }
    assert (
        paths["/api/v1/cabinet/meetings/{meeting_id}/content-exports"]["get"]["operationId"]
        == "getMeetingContentExportCapabilities"
    )
    assert (
        paths["/api/v1/cabinet/meetings/{meeting_id}/content-exports"]["post"][
            "operationId"
        ]
        == "createMeetingContentExport"
    )
    response_content = paths[
        "/api/v1/cabinet/meetings/{meeting_id}/content-exports"
    ]["post"]["responses"]["200"]["content"]
    assert set(response_content) == {
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/json",
        "application/x-subrip",
    }
    assert all(
        media["schema"] == {"type": "string", "format": "binary"}
        for media in response_content.values()
    )
    assert "/api/v1/cabinet/meetings/{meeting_id}/downloads/{artifact_class}" in paths
    assert "/api/v1/cabinet/meetings/{meeting_id}/exports" in paths
    assert "/api/v1/cabinet/meetings/{meeting_id}/exports/{export_id}/download" in paths


def test_content_export_request_rejects_unknown_formats_fields_and_missing_result() -> None:
    valid = {
        "content_scope": "transcript",
        "format": "json",
        "processing_result_id": "12000000-0000-0000-0000-000000000120",
    }

    assert ContentExportSelectionRequest.model_validate(valid).format == "json"
    with pytest.raises(ProblemDetail) as unsupported:
        ContentExportSelectionRequest.model_validate({**valid, "format": "pdf"})
    assert unsupported.value.code == "unsupported_export_format"
    with pytest.raises(ValidationError):
        ContentExportSelectionRequest.model_validate({**valid, "provider": "mediascribe"})
    with pytest.raises(ValidationError):
        ContentExportSelectionRequest.model_validate(
            {"content_scope": "transcript", "format": "txt"}
        )


def test_content_export_serializers_run_outside_the_async_event_loop() -> None:
    source = inspect.getsource(create_content_export)

    assert "await to_thread.run_sync(render_content_export, snapshot)" in source
