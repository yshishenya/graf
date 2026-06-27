from sqlalchemy import JSON

from twobrain_rec_server.db.models.support import (
    SUPPORT_INCIDENT_GITHUB_REPO,
    SupportIncident,
    SupportIncidentRateLimitBucket,
)


def _constraint_names(model: type) -> set[str]:
    return {constraint.name for constraint in model.__table__.constraints if constraint.name}


def _index_names(model: type) -> set[str]:
    return {index.name for index in model.__table__.indexes if index.name}


def test_support_incident_model_has_safe_dedupe_storage_contract() -> None:
    table = SupportIncident.__table__

    assert {
        "workspace_id",
        "reporter_user_id",
        "device_id",
        "incident_number",
        "dedupe_key",
        "problem_code",
        "failure_category",
        "retry_class",
        "status",
        "affected_count",
        "safe_affected_identities",
        "latest_safe_report_json",
        "latest_safe_report_fingerprint",
        "github_repo",
        "github_issue_number",
        "github_issue_url",
        "github_failure_code",
    }.issubset(table.c.keys())
    assert "uq_support_incidents_workspace_dedupe" in _constraint_names(SupportIncident)
    assert "ix_support_incidents_workspace_status" in _index_names(SupportIncident)
    assert "ix_support_incidents_github_issue" in _index_names(SupportIncident)
    assert table.c.github_repo.default.arg == SUPPORT_INCIDENT_GITHUB_REPO
    assert isinstance(table.c.safe_affected_identities.type, JSON)
    assert isinstance(table.c.latest_safe_report_json.type, JSON)
    assert not table.c.workspace_id.nullable
    assert not table.c.dedupe_key.nullable
    assert table.c.incident_number.nullable

    unsafe_name_parts = {"audio", "email", "meeting_title", "raw_path", "signed_url", "token", "transcript"}
    assert not any(
        unsafe_name_part in column.name
        for column in table.c
        for unsafe_name_part in unsafe_name_parts
    )


def test_support_incident_rate_limit_bucket_has_durable_scope() -> None:
    table = SupportIncidentRateLimitBucket.__table__

    assert {
        "workspace_id",
        "reporter_user_id",
        "device_id",
        "dedupe_key",
        "window_started_at",
        "attempt_count",
        "last_attempt_at",
        "blocked_until",
    }.issubset(table.c.keys())
    assert "uq_support_incident_rate_limit_scope" in _constraint_names(SupportIncidentRateLimitBucket)
    assert "ix_support_incident_rate_limit_blocked_until" in _index_names(SupportIncidentRateLimitBucket)
    assert not table.c.workspace_id.nullable
    assert not table.c.reporter_user_id.nullable
    assert not table.c.device_id.nullable
    assert not table.c.dedupe_key.nullable
