from __future__ import annotations

from twobrain_rec_server.api.problems import (
    tenant_context_missing,
    tenant_mutation_denied,
    tenant_resource_not_found,
    tenant_scope_denied,
)
from twobrain_rec_server.ingest.audit import denied_access_metadata
from twobrain_rec_server.processing.audit import safe_denied_access_metadata


def test_cross_tenant_read_problem_does_not_confirm_foreign_existence() -> None:
    problem = tenant_resource_not_found()

    assert problem.status == 404
    assert problem.code == "tenant_resource_not_found"
    assert "forbidden" not in problem.title.lower()


def test_cross_tenant_mutation_problem_is_authorization_failure() -> None:
    problem = tenant_mutation_denied()

    assert problem.status == 403
    assert problem.code == "tenant_mutation_denied"


def test_missing_context_problem_is_distinct_from_empty_read() -> None:
    problem = tenant_context_missing()

    assert problem.status == 403
    assert problem.code == "tenant_context_missing"


def test_scope_denial_problem_is_distinct_from_missing_resource() -> None:
    problem = tenant_scope_denied()

    assert problem.status == 403
    assert problem.code == "tenant_scope_denied"


def test_ingest_denied_access_metadata_is_content_safe() -> None:
    metadata = denied_access_metadata(
        request_class="api",
        feature_area="ingest",
        reason_category="cross_tenant_read",
        validation_outcome="blocked",
        transcript_text="do not keep",
        signed_url="do not keep",
    )

    assert metadata == {
        "request_class": "api",
        "feature_area": "ingest",
        "reason_category": "cross_tenant_read",
        "validation_outcome": "blocked",
    }


def test_processing_denied_access_metadata_is_content_safe() -> None:
    metadata = safe_denied_access_metadata(
        request_class="worker",
        feature_area="processing",
        reason_category="missing_context",
        validation_outcome="blocked",
        raw_audio_path="do not keep",
    )

    assert metadata == {
        "request_class": "worker",
        "feature_area": "processing",
        "reason_category": "missing_context",
        "validation_outcome": "blocked",
    }
