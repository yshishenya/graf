from __future__ import annotations


def test_summary_template_and_candidate_routes_are_explicit_and_csrf_protected(client) -> None:
    schema = client.get("/openapi.json").json()
    expected = {
        ("/api/v1/cabinet/summary-templates", "get"): "listSummaryTemplates",
        ("/api/v1/cabinet/summary-templates", "post"): "createSummaryTemplate",
        ("/api/v1/cabinet/summary-templates/{template_id}", "patch"): (
            "updateSummaryTemplate"
        ),
        ("/api/v1/cabinet/summary-templates/{template_id}", "delete"): (
            "deleteSummaryTemplate"
        ),
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
            "/api/v1/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}/accept",
            "post",
        ): "acceptSummaryCandidate",
        (
            "/api/v1/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}/reject",
            "post",
        ): "rejectSummaryCandidate",
    }
    for (path, method), operation_id in expected.items():
        assert schema["paths"][path][method]["operationId"] == operation_id


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
