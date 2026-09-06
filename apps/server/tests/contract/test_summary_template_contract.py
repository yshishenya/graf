from __future__ import annotations

from pathlib import Path


def test_summary_template_and_candidate_routes_are_explicit_and_csrf_protected(client) -> None:
    schema = client.get("/openapi.json").json()
    expected = {
        ("/api/v1/cabinet/summary-templates", "get"): "listSummaryTemplates",
        ("/api/v1/cabinet/summary-templates", "post"): "createSummaryTemplate",
        ("/api/v1/cabinet/summary-templates/{template_id}", "patch"): ("updateSummaryTemplate"),
        ("/api/v1/cabinet/summary-templates/{template_id}", "delete"): ("deleteSummaryTemplate"),
        ("/api/v1/cabinet/summary-templates/{template_id}/duplicate", "post"): (
            "duplicateSummaryTemplate"
        ),
        ("/api/v1/cabinet/summary-templates/{template_id}/archive", "post"): (
            "archiveSummaryTemplate"
        ),
        ("/api/v1/cabinet/meetings/{meeting_id}/summary-candidates", "post"): (
            "createSummaryCandidate"
        ),
        (
            "/api/v1/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}",
            "get",
        ): "getSummaryCandidate",
        (
            "/api/v1/cabinet/meetings/{meeting_id}/summaries/{template_key}/refresh",
            "post",
        ): "refreshMeetingSummaryType",
    }
    for (path, method), operation_id in expected.items():
        assert schema["paths"][path][method]["operationId"] == operation_id
    for suffix in ("preview", "accept", "reject"):
        path = (
            "/api/v1/cabinet/meetings/{meeting_id}/summary-candidates/"
            f"{{candidate_id}}/{suffix}"
        )
        assert schema["paths"][path]["get" if suffix == "preview" else "post"]["deprecated"] is True


def test_type_scoped_summary_routes_have_one_click_ensure_and_no_private_controls(client) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert (
        paths["/api/v1/cabinet/meetings/{meeting_id}/summary-types"]["get"]["operationId"]
        == "listMeetingSummaryTypes"
    )
    assert (
        paths["/api/v1/cabinet/meetings/{meeting_id}/summaries/{template_key}"]["get"][
            "operationId"
        ]
        == "getMeetingSummaryType"
    )
    assert (
        paths["/api/v1/cabinet/meetings/{meeting_id}/summaries/{template_key}/ensure"]["post"][
            "operationId"
        ]
        == "ensureMeetingSummaryType"
    )
    ensure_schema = client.get("/openapi.json").json()["components"]["schemas"][
        "EnsureSummaryTypeRequest"
    ]
    assert set(ensure_schema["properties"]) == {"schema_version", "idempotency_key"}
    assert not any(
        name in ensure_schema["properties"]
        for name in ("my_actions", "private_self", "subject", "participant")
    )
    refresh_schema = client.get("/openapi.json").json()["components"]["schemas"][
        "RefreshSummaryTypeRequest"
    ]
    assert set(refresh_schema["properties"]) == {
        "schema_version",
        "idempotency_key",
        "expected_current_outcome_set_id",
        "template_id",
        "template_version",
        "generation_options",
    }
    assert refresh_schema["additionalProperties"] is False


def test_template_schema_is_bounded_structured_and_includes_evidence(client) -> None:
    schema = client.get("/openapi.json").json()["components"]["schemas"]
    request = schema["CreateSummaryTemplateRequest"]
    sections = request["properties"]["sections"]
    assert sections["minItems"] == 1
    assert sections["maxItems"] == 8
    assert "evidence" in sections["items"]["enum"]
    assert request["additionalProperties"] is False


def test_candidate_request_has_optimistic_revision_and_no_observability_controls(client) -> None:
    schema = client.get("/openapi.json").json()["components"]["schemas"]
    request = schema["CreateSummaryCandidateRequest"]
    assert set(request["properties"]) == {
        "template_key",
        "template_id",
        "template_version",
        "expected_current_outcome_set_id",
        "request_intent",
        "request_intent_id",
    }
    assert not any("langfuse" in name or "temporal" in name for name in request["properties"])


def test_refresh_ui_uses_the_type_scoped_route_and_keeps_review_surface_private() -> None:
    script = (
        Path(__file__).resolve().parents[2]
        / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
    ).read_text(encoding="utf-8")
    assert "requestSummaryRefresh" in script
    assert "/api/v1/cabinet/meetings/${meetingId}/summaries/${encodeURIComponent(template.key)}/refresh" in script
    assert "summary-candidate-preview" not in script
    assert 'text: "Использовать"' not in script
    assert 'text: "Оставить текущие"' not in script
