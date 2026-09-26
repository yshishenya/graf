"""Approval records and the computed paid launch gate (T062, T063, T066, SC-013).

The records are read from a metadata-only file outside git, so the tests build
that file themselves: a person's name, an email address or a live link must
never be needed, and must never be accepted in its place.
"""

from __future__ import annotations

import re
import time
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.product_analytics.access_governance import (
    ACCESS_GOVERNANCE_STATE_FILE_ENV,
)
from twobrain_rec_server.product_analytics.approvals import (
    APPROVAL_KINDS,
    APPROVAL_STATE_EXPIRED,
    APPROVAL_STATE_MISSING,
    APPROVAL_STATE_RECORDED,
    APPROVAL_STATE_UNREADABLE,
    APPROVAL_STATE_VERSION,
    APPROVAL_STATES,
    LAUNCH_APPROVAL_KIND_SPECS,
    approval_state_file_path,
    build_launch_approval_gate,
    campaign_launch_allowed_for_settings,
    read_launch_approval_register,
)
from twobrain_rec_server.product_analytics.readiness import build_rollout_readiness_report

APPROVAL_STATE_ENV = "GRAF_PRODUCT_ANALYTICS_APPROVAL_STATE_FILE"
APPROVAL_APPROVERS = {
    "legal": "product_owner",
    "privacy": "privacy_reviewer",
    "security": "security_reviewer",
    "qa": "qa_reviewer",
    "rollback": "infra_operator",
    "delivery": "analytics_operator",
    "check": "release_owner",
}

# A launch needs measurement to run, so the "everything else is ready" settings
# are shared: the point of the tests below is only what the records add.
LAUNCH_READY_SETTINGS = {
    "product_analytics_enabled": True,
    "product_analytics_validation_mode": "live_safe",
    "product_analytics_provider_mode": "posthog_primary",
    "product_analytics_legal_approved": True,
    "product_analytics_privacy_approved": True,
    "product_analytics_security_approved": True,
    "product_analytics_qa_approved": True,
    "product_analytics_disclosure_approved": True,
    "product_analytics_dashboard_ready": True,
    "product_analytics_provider_smoke_approved": True,
    "product_analytics_rollback_approved": True,
    "product_analytics_live_provider_delivery_approved": True,
}


def _approval_line(kind: str, **overrides: str) -> str:
    fields = {
        "state": APPROVAL_STATE_RECORDED,
        "approved_by": APPROVAL_APPROVERS[kind],
        "approved_at": "2026-09-18",
        "scope": "measurement_scope",
        "evidence_ref": f"ref-{kind}",
    }
    fields.update(overrides)
    tokens = " ".join(f"{key}={value}" for key, value in fields.items() if value != "")
    return f"approval kind={kind} {tokens}"


def _write_approvals(
    directory: Path,
    lines: list[str],
    *,
    header: str | None = f"approval_state_version={APPROVAL_STATE_VERSION}",
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    body = [line for line in ([header] if header else []) + lines if line]
    path = directory / "launch-approvals"
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    return path


def _complete_lines() -> list[str]:
    return [_approval_line(kind) for kind in APPROVAL_KINDS]


def _environment(path: Path) -> dict[str, str]:
    return {APPROVAL_STATE_ENV: str(path)}


def _complete_approval_lines() -> list[str]:
    return [_approval_line(kind) for kind in APPROVAL_KINDS]


def _operations_state_files(directory: Path, *, now: int) -> dict[str, str]:
    """Fresh backup, restore and retention evidence, in the task's own format."""

    backup = directory / "backup-state"
    backup.write_text(
        "\n".join(
            [
                "backup_state_version=1",
                "last_attempt_result=pass",
                f"last_success_epoch={now - 3600}",
                "copies_local=3",
                "copies_offsite=1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    restore = directory / "restore-state"
    restore.write_text(
        "\n".join(
            [
                "restore_state_version=1",
                "last_verify_result=pass",
                f"last_verify_epoch={now - 2 * 86400}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    retention = directory / "retention-state"
    retention_lines = ["retention_state_version=1", "result=pass"]
    for category, term in (
        ("measurement_events", "365"),
        ("anonymous_aggregate", "1095"),
        ("visit_attribution", "90"),
        ("acquisition_attribute", "1095"),
    ):
        storage = "clickhouse" if category == "measurement_events" else "postgres"
        retention_lines.append(
            f"category={category} retention_days={term} storage={storage} "
            "enforcement=scheduled_task enforcement_verified=true"
        )
    retention.write_text("\n".join(retention_lines) + "\n", encoding="utf-8")
    return {
        "GRAF_POSTHOG_BACKUP_STATE_FILE": str(backup),
        "GRAF_POSTHOG_RESTORE_STATE_FILE": str(restore),
        "GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_FILE": str(retention),
    }


def _write_access_governance_state(directory: Path, *, now: int) -> Path:
    """Fresh synthetic metadata-only access evidence for a live-safe fixture."""

    state = directory / "access-governance-state"
    digest = "sha256:" + "a" * 64
    state.write_text(
        "\n".join(
            [
                "access_governance_state_version=1",
                f"reviewed_at={now - 60}",
                f"expires_at={now + 86400}",
                "accepted_operator_count=2",
                "mfa_operator_count=2",
                f"repository_digest={digest}",
                f"config_digest={digest}",
                f"installed_guard_digest={digest}",
                "revocation_review=complete",
                "credential_rotation_review=complete",
                "audit_review=complete",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return state


def _launch_ready_settings(tmp_path: Path, **overrides: object) -> Settings:
    """Settings whose only remaining unknown is the approval register.

    The provider has to be configured for real, otherwise the readiness report
    keeps its own configuration blockers and the tests would be measuring those
    instead of the records.
    """

    project_key_file = tmp_path / "posthog_project_key"
    project_key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    return Settings(
        product_analytics_posthog_enabled=True,
        product_analytics_posthog_host="https://analytics.example.test",
        product_analytics_posthog_project_key_file=project_key_file,
        **LAUNCH_READY_SETTINGS,
        **overrides,
    )


def test_default_state_file_path_is_outside_the_repository() -> None:
    assert approval_state_file_path({}) == (
        "/var/lib/graf-product-analytics-approvals/launch-approvals"
    )
    assert approval_state_file_path({APPROVAL_STATE_ENV: "/tmp/records"}) == "/tmp/records"


def test_every_approval_kind_carries_a_contract_and_an_owner_role() -> None:
    """T062: each record says what is confirmed, by which role and why."""

    assert [spec.kind for spec in LAUNCH_APPROVAL_KIND_SPECS] == list(APPROVAL_KINDS)
    for spec in LAUNCH_APPROVAL_KIND_SPECS:
        assert spec.title
        assert spec.requirement.startswith("FR-")
        assert re.fullmatch(r"[a-z][a-z0-9_]{2,39}", spec.confirmed_by_role)
        assert spec.instruction


def test_a_missing_state_file_approves_nothing(tmp_path: Path) -> None:
    """FR-044: fail closed — no records means no permission at all."""

    gate = build_launch_approval_gate(environ=_environment(tmp_path / "absent"))

    assert gate.register.available is False
    assert gate.campaign_launch_allowed is False
    assert gate.missing_kinds == APPROVAL_KINDS
    assert "approval_state_file_unavailable" in gate.blockers
    for kind in APPROVAL_KINDS:
        assert gate.register.approval(kind).state == APPROVAL_STATE_MISSING


def test_missing_kinds_are_named_one_by_one(tmp_path: Path) -> None:
    """Acceptance scenario 1: the owner sees exactly which approval is absent."""

    path = _write_approvals(tmp_path, [_approval_line("legal"), _approval_line("privacy")])
    gate = build_launch_approval_gate(environ=_environment(path))

    assert gate.register.approval("legal").state == APPROVAL_STATE_RECORDED
    assert gate.register.approval("legal").approved_by == "product_owner"
    assert gate.register.approval("legal").approved_at == "2026-09-18"
    assert gate.register.approval("legal").scope == "measurement_scope"
    assert gate.missing_kinds == ("security", "qa", "rollback", "delivery", "check")
    for kind in ("security", "qa", "rollback", "delivery", "check"):
        assert f"approval_missing:{kind}" in gate.blockers
    assert "approval_missing:legal" not in gate.blockers
    assert gate.campaign_launch_allowed is False


def test_a_complete_register_is_the_only_thing_that_allows_launch(tmp_path: Path) -> None:
    """T063: the permission comes from the records, not from a flag."""

    path = _write_approvals(tmp_path, _complete_lines())
    gate = build_launch_approval_gate(environ=_environment(path))

    assert gate.register.available is True
    assert gate.blockers == ()
    assert gate.missing_kinds == ()
    assert gate.campaign_launch_allowed is True
    settings = Settings(**LAUNCH_READY_SETTINGS)
    assert campaign_launch_allowed_for_settings(settings, environ=_environment(path)) is True


def test_every_flag_approved_without_records_still_blocks_launch(tmp_path: Path) -> None:
    """FR-044: a technical flag cannot stand in for an approval record."""

    settings = Settings(**LAUNCH_READY_SETTINGS)
    environment = _environment(tmp_path / "absent")

    assert settings.product_analytics_legal_approved is True
    assert settings.product_analytics_live_provider_delivery_allowed() is True
    assert campaign_launch_allowed_for_settings(settings, environ=environment) is False

    report = build_rollout_readiness_report(settings, environ=environment).as_dict()
    assert report["campaign_launch_allowed"] is False
    assert report["product_rollout_allowed"] is False
    assert report["states"]["campaign_launch"] == "blocked_pending_launch_approval_record"
    assert report["approval_gate"]["missing_kinds"] == list(APPROVAL_KINDS)


def test_an_expired_record_blocks_launch_again(tmp_path: Path) -> None:
    """FR-044: a stale confirmation is reported as expired, not as approved."""

    lines = [
        _approval_line(kind, valid_until="2026-09-01") if kind == "rollback" else _approval_line(kind)
        for kind in APPROVAL_KINDS
    ]
    path = _write_approvals(tmp_path, lines)
    gate = build_launch_approval_gate(environ=_environment(path))

    assert gate.register.approval("rollback").state == APPROVAL_STATE_EXPIRED
    assert gate.register.approval("rollback").reason == "valid_until_passed"
    assert gate.blockers == ("approval_expired:rollback",)
    assert gate.campaign_launch_allowed is False


def test_a_record_that_is_not_a_role_based_confirmation_is_not_trusted(tmp_path: Path) -> None:
    """Records must not carry personal names, contacts or links."""

    lines = _complete_lines()
    lines[0] = _approval_line("legal", approved_by="yan@example.test")
    lines[1] = _approval_line("privacy", approved_at="not-a-date")
    lines[2] = _approval_line("security", scope="https://example.test/scope")
    lines[3] = _approval_line("qa", state="approved")
    path = _write_approvals(tmp_path, lines)
    gate = build_launch_approval_gate(environ=_environment(path))

    assert gate.register.approval("legal").state == APPROVAL_STATE_UNREADABLE
    assert gate.register.approval("legal").reason == "approved_by_is_not_a_role_identifier"
    assert gate.register.approval("privacy").reason == "approved_at_is_invalid"
    assert gate.register.approval("security").reason == "scope_is_invalid"
    # `state=approved` is not a state this contract knows, so it stays blocking.
    assert gate.register.approval("qa").state == APPROVAL_STATE_MISSING
    assert "approval_unreadable:legal" in gate.blockers
    assert "approval_unreadable:privacy" in gate.blockers
    assert "approval_unreadable:security" in gate.blockers
    assert "approval_missing:qa" in gate.blockers
    assert gate.campaign_launch_allowed is False


def test_a_future_confirmation_date_is_not_trusted(tmp_path: Path) -> None:
    path = _write_approvals(
        tmp_path,
        [_approval_line(kind, approved_at="2099-01-01") for kind in APPROVAL_KINDS],
    )
    register = read_launch_approval_register(
        _environment(path), today=date(2026, 9, 18)
    )

    assert register.approval("legal").state == APPROVAL_STATE_UNREADABLE
    assert register.approval("legal").reason == "approved_at_is_in_the_future"


def test_a_max_age_limit_expires_an_old_confirmation(tmp_path: Path) -> None:
    path = _write_approvals(
        tmp_path,
        [_approval_line(kind, max_age_days="90") for kind in APPROVAL_KINDS],
    )
    gate = build_launch_approval_gate(environ=_environment(path), today=date(2027, 6, 1))

    assert gate.register.approval("legal").state == APPROVAL_STATE_EXPIRED
    assert gate.register.approval("legal").reason == "max_age_days_passed"
    assert gate.campaign_launch_allowed is False


def test_a_duplicated_kind_invalidates_the_register(tmp_path: Path) -> None:
    lines = [*_complete_lines(), _approval_line("legal")]
    path = _write_approvals(tmp_path, lines)
    gate = build_launch_approval_gate(environ=_environment(path))

    assert "approval_record_count_mismatch" in gate.blockers
    for kind in APPROVAL_KINDS:
        assert gate.register.approval(kind).state == APPROVAL_STATE_UNREADABLE
    assert gate.campaign_launch_allowed is False


def test_a_record_key_that_only_starts_with_the_keyword_is_still_parsed(tmp_path: Path) -> None:
    """`approved_by=...` must not be read as the start of a new record."""

    path = _write_approvals(tmp_path, _complete_lines())
    register = read_launch_approval_register(_environment(path))

    assert register.approval("legal").approved_by == "product_owner"
    assert register.approval("legal").state == APPROVAL_STATE_RECORDED


def test_an_unsupported_state_version_invalidates_the_register(tmp_path: Path) -> None:
    path = _write_approvals(tmp_path, _complete_lines(), header="approval_state_version=99")
    gate = build_launch_approval_gate(environ=_environment(path))

    assert "approval_state_version_unsupported" in gate.blockers
    assert gate.register.approval("legal").state == APPROVAL_STATE_UNREADABLE
    assert gate.campaign_launch_allowed is False


def test_a_record_without_the_version_header_is_not_trusted(tmp_path: Path) -> None:
    path = _write_approvals(tmp_path, _complete_lines(), header=None)
    gate = build_launch_approval_gate(environ=_environment(path))

    assert "approval_state_version_unsupported" in gate.blockers
    assert gate.campaign_launch_allowed is False


def test_recorded_approvals_do_not_authorise_launch_while_measurement_is_blocked(
    tmp_path: Path,
) -> None:
    """A recorded approval cannot override a blocked measurement configuration."""

    path = _write_approvals(tmp_path, _complete_lines())
    gate = build_launch_approval_gate(
        ("product_analytics_disabled", "posthog_not_ready", "dashboard_not_ready"),
        environ=_environment(path),
    )

    assert gate.blockers == ()
    assert gate.configuration_blockers == (
        "product_analytics_disabled",
        "posthog_not_ready",
        "dashboard_not_ready",
    )
    assert gate.campaign_launch_allowed is False


def test_readiness_report_reflects_the_records_truthfully(tmp_path: Path) -> None:
    """T066 / SC-013: the report says what is recorded at this moment."""

    now = int(time.time())
    operations = _operations_state_files(tmp_path, now=now)
    partial_path = _write_approvals(tmp_path / "partial", [_approval_line("legal")])
    complete_path = _write_approvals(tmp_path / "complete", _complete_approval_lines())
    access_path = _write_access_governance_state(tmp_path, now=now)
    settings = _launch_ready_settings(tmp_path)

    blocked = build_rollout_readiness_report(
        settings, environ=operations | _environment(tmp_path / "absent-file")
    ).as_dict()
    partial = build_rollout_readiness_report(
        settings, environ=operations | _environment(partial_path)
    ).as_dict()
    allowed = build_rollout_readiness_report(
        settings,
        environ=operations
        | _environment(complete_path)
        | {ACCESS_GOVERNANCE_STATE_FILE_ENV: str(access_path)},
    ).as_dict()

    assert blocked["approval_gate"]["states"]["legal"] == APPROVAL_STATE_MISSING
    assert partial["approval_gate"]["states"]["legal"] == APPROVAL_STATE_RECORDED
    assert partial["approval_gate"]["states"]["privacy"] == APPROVAL_STATE_MISSING
    assert partial["campaign_launch_allowed"] is False
    assert allowed["approval_gate"]["states"] == dict.fromkeys(
        APPROVAL_KINDS, APPROVAL_STATE_RECORDED
    )
    # Every technical condition holds and every record is present, so the launch
    # gate finally reports the truth: allowed.
    assert list(allowed["approval_gate"]["configuration_blockers"]) == []
    assert allowed["campaign_launch_allowed"] is True
    assert allowed["product_rollout_allowed"] is True
    assert allowed["states"]["campaign_launch"] == "allowed_by_records"
    assert allowed["states"]["product_rollout"] == "allowed_by_records"

    for report in (blocked, partial, allowed):
        assert set(report["approval_gate"]["states"]) == set(APPROVAL_KINDS)
        assert all(state in APPROVAL_STATES for state in report["approval_gate"]["states"].values())
        # The gate never leaks an approver identity into the readiness report.
        assert "approved_by" not in str(report["approval_gate"])
        assert "product_owner" not in str(report["approval_gate"])


def test_catalog_exposes_the_approval_gate_without_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The operator-facing surface names what is missing, not who signed."""

    path = _write_approvals(tmp_path, [_approval_line("legal")])
    monkeypatch.setenv(APPROVAL_STATE_ENV, str(path))
    for name, value in _operations_state_files(tmp_path, now=int(time.time())).items():
        monkeypatch.setenv(name, value)
    app = create_app(
        Settings(
            database_url="postgresql+asyncpg://nobody@127.0.0.1:1/none",
            minio_access_key="test",
            minio_secret_key="test",
            minio_bucket="test-bucket",
        )
    )
    app.state.settings = _launch_ready_settings(tmp_path)

    with TestClient(app) as client:
        payload = client.get("/api/v1/product-analytics/catalog").json()

    assert payload["provider_config"]["campaign_launch_allowed"] is False
    readiness = payload["rollout_readiness"]
    assert readiness["campaign_launch_allowed"] is False
    assert readiness["approval_gate"]["available"] is True
    assert readiness["approval_gate"]["states"]["legal"] == APPROVAL_STATE_RECORDED
    assert "privacy" in readiness["approval_gate"]["missing_kinds"]
    assert "product_owner" not in str(readiness["approval_gate"])
