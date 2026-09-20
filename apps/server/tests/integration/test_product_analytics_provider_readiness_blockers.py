import time
from pathlib import Path

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.provider_readiness import build_provider_readiness
from twobrain_rec_server.product_analytics.readiness import build_rollout_readiness_report


def test_readiness_report_records_separate_legal_privacy_security_qa_and_campaign_states() -> None:
    report = build_rollout_readiness_report(Settings()).as_dict()

    assert report["verdict"] == "blocked"
    assert "product_analytics_disabled" in report["blockers"]
    assert report["states"]["legal"] == "blocked"
    assert report["states"]["privacy"] == "separate_rollout_approval_required"
    assert report["states"]["security"] == "separate_rollout_approval_required"
    assert report["states"]["qa"] == "separate_rollout_approval_required"
    assert report["states"]["disclosure"] == "separate_rollout_approval_required"
    assert report["states"]["dashboard"] == "blocked"
    assert report["states"]["provider_smoke"] == "blocked"
    assert report["states"]["rollback"] == "blocked"
    assert report["states"]["live_provider_delivery"] == "blocked"
    assert report["states"]["product_rollout"] == "blocked_by_records"
    # The launch state is computed from the approval records, so it names the
    # missing record instead of a fixed feature label (FR-044, SC-013).
    assert report["states"]["campaign_launch"] == "blocked_pending_launch_approval_record"
    assert report["product_rollout_allowed"] is False
    assert report["campaign_launch_allowed"] is False
    assert report["approval_gate"]["available"] is False
    assert report["approval_gate"]["campaign_launch_allowed"] is False
    assert report["approval_gate"]["missing_kinds"] == [
        "legal",
        "privacy",
        "security",
        "qa",
        "rollback",
        "delivery",
        "check",
    ]


def test_provider_smoke_ready_still_does_not_approve_product_rollout_or_campaign_launch(tmp_path: Path) -> None:
    project_key_file = tmp_path / "posthog_project_key"
    project_key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    report = build_rollout_readiness_report(
        Settings(
            product_analytics_enabled=True,
            product_analytics_validation_mode="provider_smoke",
            product_analytics_provider_mode="posthog_primary",
            product_analytics_posthog_enabled=True,
            product_analytics_posthog_host="https://analytics.example.test",
            product_analytics_posthog_project_key_file=project_key_file,
            product_analytics_legal_approved=True,
            product_analytics_dashboard_ready=True,
            product_analytics_provider_smoke_approved=True,
            product_analytics_campaign_readiness_approved=True,
        )
    ).as_dict()

    assert report["verdict"] == "infra_smoke_ready"
    assert report["states"]["legal"] == "approved_for_provider_setup"
    assert report["states"]["dashboard"] == "metadata_only_ready"
    assert report["states"]["rbac_audit"] == "documented"
    assert report["states"]["retention_deletion_lifecycle"] == "documented"
    assert report["states"]["deploy_dry_run"] == "documented_pending_final_run"
    assert report["states"]["provider_smoke"] == "approved"
    assert report["states"]["live_provider_delivery"] == "blocked"
    assert report["states"]["product_rollout"] == "blocked_by_records"
    assert report["states"]["campaign_launch"] == "blocked_pending_launch_approval_record"
    assert "product_rollout_separate_approval_required" in report["rollout_blockers"]
    assert "paid_campaign_launch_blocked_by_096" in report["rollout_blockers"]
    assert report["product_rollout_allowed"] is False
    assert report["campaign_launch_allowed"] is False


def _live_provider_settings(tmp_path: Path) -> Settings:
    project_key_file = tmp_path / "posthog_project_key"
    project_key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    return Settings(
        product_analytics_enabled=True,
        product_analytics_validation_mode="live_safe",
        product_analytics_provider_mode="posthog_primary",
        product_analytics_posthog_enabled=True,
        product_analytics_posthog_host="https://analytics.example.test",
        product_analytics_posthog_project_key_file=project_key_file,
        product_analytics_legal_approved=True,
        product_analytics_privacy_approved=True,
        product_analytics_security_approved=True,
        product_analytics_qa_approved=True,
        product_analytics_disclosure_approved=True,
        product_analytics_dashboard_ready=True,
        product_analytics_provider_smoke_approved=True,
        product_analytics_rollback_approved=True,
        product_analytics_live_provider_delivery_approved=True,
        product_analytics_campaign_readiness_approved=True,
    )


def _write_operations_states(
    directory: Path,
    *,
    now: int,
    backup_age_hours: int = 1,
    copies_local: int = 3,
    copies_offsite: int = 1,
    restore_age_days: int = 2,
    restore_result: str = "pass",
    retention_override: dict[str, str] | None = None,
) -> dict[str, Path]:
    backup = directory / "backup-state"
    backup.write_text(
        "\n".join(
            [
                "backup_state_version=1",
                "last_attempt_result=pass",
                f"last_success_epoch={now - backup_age_hours * 3600}",
                f"copies_local={copies_local}",
                f"copies_offsite={copies_offsite}",
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
                f"last_verify_result={restore_result}",
                f"last_verify_epoch={now - restore_age_days * 86400}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    terms = {
        "measurement_events": "365",
        "anonymous_aggregate": "1095",
        "visit_attribution": "90",
        "acquisition_attribute": "1095",
    }
    terms.update(retention_override or {})
    retention_lines = ["retention_state_version=1", "result=pass"]
    for category, term in terms.items():
        storage = "clickhouse" if category == "measurement_events" else "postgres"
        enforcement = "row_ttl" if category == "measurement_events" else "scheduled_task"
        retention_lines.append(
            f"category={category} retention_days={term} storage={storage} enforcement={enforcement} "
            f"last_enforced_at=recent rows_deleted=0 enforcement_verified=true"
        )
    retention = directory / "retention-state"
    retention.write_text("\n".join(retention_lines) + "\n", encoding="utf-8")
    return {"backup": backup, "restore": restore, "retention": retention}


def _write_access_governance_state(directory: Path, *, now: int) -> Path:
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


def _apply_states(monkeypatch, state: dict[str, Path]) -> None:
    monkeypatch.setenv("GRAF_POSTHOG_BACKUP_STATE_FILE", str(state["backup"]))
    monkeypatch.setenv("GRAF_POSTHOG_RESTORE_STATE_FILE", str(state["restore"]))
    monkeypatch.setenv("GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_FILE", str(state["retention"]))


def _apply_access_governance(monkeypatch, path: Path) -> None:
    monkeypatch.setenv("GRAF_PRODUCT_ANALYTICS_ACCESS_GOVERNANCE_STATE_FILE", str(path))


def test_live_provider_delivery_claim_requires_fresh_operations_evidence(tmp_path: Path, monkeypatch) -> None:
    """T025: a live claim is blocked while backup, restore or retention is unproven."""

    settings = _live_provider_settings(tmp_path)
    for name in ("GRAF_POSTHOG_BACKUP_STATE_FILE", "GRAF_POSTHOG_RESTORE_STATE_FILE",
                 "GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_FILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GRAF_POSTHOG_BACKUP_STATE_DIR", str(tmp_path / "no-such-state-dir"))

    blocked = build_rollout_readiness_report(settings).as_dict()
    assert blocked["verdict"] == "blocked"
    # Operations evidence carries its own label. Reporting it as
    # `posthog_not_ready` would hide the real reason behind a provider
    # configuration problem that does not exist in this configuration.
    assert "analytics_operations_not_ready" in blocked["blockers"]
    assert "posthog_not_ready" not in blocked["blockers"]
    assert blocked["states"]["live_provider_delivery"] == "approved"
    # Missing access-governance evidence is independently fail-closed for a live
    # claim; operations and access are separate gates.
    assert blocked["states"]["rbac_audit"] == "blocked"
    assert blocked["states"]["retention_deletion_lifecycle"] == "blocked"

    now = int(time.time())
    state = _write_operations_states(tmp_path, now=now)
    _apply_states(monkeypatch, state)
    _apply_access_governance(monkeypatch, _write_access_governance_state(tmp_path, now=now))

    ready = build_rollout_readiness_report(settings).as_dict()
    assert ready["verdict"] == "infra_smoke_ready"
    assert "posthog_not_ready" not in ready["blockers"]
    assert "analytics_operations_not_ready" not in ready["blockers"]
    assert ready["states"]["retention_deletion_lifecycle"] == "enforced_and_verified"
    assert ready["states"]["live_provider_delivery"] == "approved"
    assert ready["states"]["rbac_audit"] == "metadata_verified"
    assert ready["states"]["campaign_launch"] == "blocked_pending_launch_approval_record"
    assert ready["product_rollout_allowed"] is False
    assert ready["campaign_launch_allowed"] is False

    provider_state = build_provider_readiness(settings).as_dict()
    assert provider_state["analytics_operations"]["configured"] is True
    assert provider_state["analytics_operations"]["blockers"] == []
    assert provider_state["posthog"]["metadata"]["operations_claim_gate"] == "enforced"


def test_a_smoke_configuration_still_reports_operations_blockers_without_claiming_readiness(
    tmp_path: Path, monkeypatch
) -> None:
    """The smoke lane must stay usable while the blockers remain visible."""

    project_key_file = tmp_path / "posthog_project_key"
    project_key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    settings = Settings(
        product_analytics_enabled=True,
        product_analytics_validation_mode="provider_smoke",
        product_analytics_provider_mode="posthog_primary",
        product_analytics_posthog_enabled=True,
        product_analytics_posthog_host="https://analytics.example.test",
        product_analytics_posthog_project_key_file=project_key_file,
        product_analytics_legal_approved=True,
        product_analytics_dashboard_ready=True,
        product_analytics_provider_smoke_approved=True,
    )
    monkeypatch.setenv("GRAF_POSTHOG_BACKUP_STATE_DIR", str(tmp_path / "no-such-state-dir"))
    for name in ("GRAF_POSTHOG_BACKUP_STATE_FILE", "GRAF_POSTHOG_RESTORE_STATE_FILE",
                 "GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_FILE"):
        monkeypatch.delenv(name, raising=False)

    report = build_rollout_readiness_report(settings).as_dict()
    assert report["verdict"] == "infra_smoke_ready"
    assert report["states"]["live_provider_delivery"] == "blocked"

    operations = build_provider_readiness(settings).as_dict()["analytics_operations"]
    assert operations["configured"] is False
    assert "backup_state_unavailable" in operations["blockers"]
    assert "restore_verification_missing" in operations["blockers"]
    assert "retention_state_unavailable" in operations["blockers"]
    assert operations["metadata"]["evidence"] == "metadata_only"
    assert operations["metadata"]["product_impact"] == "measurement_gap_only"
    assert build_provider_readiness(settings).as_dict()["posthog"]["metadata"]["operations_claim_gate"] == "not_claimed"


def test_readiness_blocks_when_the_newest_copy_is_stale(tmp_path: Path, monkeypatch) -> None:
    settings = _live_provider_settings(tmp_path)
    now = int(time.time())

    stale = _write_operations_states(tmp_path, now=now, backup_age_hours=30)
    _apply_states(monkeypatch, stale)
    state = build_provider_readiness(settings).as_dict()["analytics_operations"]
    assert "backup_stale" in state["blockers"]
    assert state["configured"] is False
    assert state["metadata"]["backup_last_success_age_hours"].startswith("30")
    assert build_rollout_readiness_report(settings).as_dict()["verdict"] == "blocked"

    fresh = _write_operations_states(tmp_path, now=now, backup_age_hours=2)
    _apply_states(monkeypatch, fresh)
    _apply_access_governance(monkeypatch, _write_access_governance_state(tmp_path, now=now))
    refreshed = build_provider_readiness(settings).as_dict()["analytics_operations"]
    assert refreshed["blockers"] == []
    assert build_rollout_readiness_report(settings).as_dict()["verdict"] == "infra_smoke_ready"


def test_readiness_blocks_on_missing_offsite_copy_and_copy_count(tmp_path: Path, monkeypatch) -> None:
    settings = _live_provider_settings(tmp_path)
    now = int(time.time())
    state = _write_operations_states(tmp_path, now=now, copies_local=1, copies_offsite=0)
    _apply_states(monkeypatch, state)

    operations = build_provider_readiness(settings).as_dict()["analytics_operations"]
    assert "backup_copy_count_below_minimum" in operations["blockers"]
    assert "backup_offsite_copy_missing" in operations["blockers"]
    assert operations["metadata"]["backup_minimum_copies"] == "2"
    assert operations["metadata"]["backup_minimum_offsite_copies"] == "1"


def test_readiness_blocks_on_a_failed_or_stale_restore_verification(tmp_path: Path, monkeypatch) -> None:
    settings = _live_provider_settings(tmp_path)
    now = int(time.time())

    failed = _write_operations_states(tmp_path, now=now, restore_result="fail")
    _apply_states(monkeypatch, failed)
    assert "restore_verification_failed" in build_provider_readiness(settings).as_dict()[
        "analytics_operations"
    ]["blockers"]

    stale = _write_operations_states(tmp_path, now=now, restore_age_days=45)
    _apply_states(monkeypatch, stale)
    operations = build_provider_readiness(settings).as_dict()["analytics_operations"]
    assert "restore_verification_stale" in operations["blockers"]
    assert operations["metadata"]["restore_verification_max_age_days"] == "30"


def test_readiness_blocks_when_a_retention_term_is_missing_or_too_short(tmp_path: Path, monkeypatch) -> None:
    settings = _live_provider_settings(tmp_path)
    now = int(time.time())

    missing = _write_operations_states(tmp_path, now=now, retention_override={"visit_attribution": "0"})
    _apply_states(monkeypatch, missing)
    assert "retention_term_missing:visit_attribution" in build_provider_readiness(settings).as_dict()[
        "analytics_operations"
    ]["blockers"]

    shortened = _write_operations_states(tmp_path, now=now, retention_override={"measurement_events": "90"})
    _apply_states(monkeypatch, shortened)
    assert "retention_term_below_required:measurement_events" in build_provider_readiness(settings).as_dict()[
        "analytics_operations"
    ]["blockers"]
    assert build_rollout_readiness_report(settings).as_dict()["verdict"] == "blocked"


def test_readiness_names_a_category_that_has_no_retention_record(tmp_path: Path, monkeypatch) -> None:
    settings = _live_provider_settings(tmp_path)
    now = int(time.time())
    state = _write_operations_states(tmp_path, now=now)
    state["retention"].write_text(
        "\n".join(
            [
                "retention_state_version=1",
                "result=pass",
                "category=measurement_events retention_days=365 storage=clickhouse enforcement=row_ttl "
                "last_enforced_at=recent rows_deleted=0 enforcement_verified=true",
                "missing_category=visit_attribution",
                "",
            ]
        ),
        encoding="utf-8",
    )
    _apply_states(monkeypatch, state)

    operations = build_provider_readiness(settings).as_dict()["analytics_operations"]
    assert "retention_category_missing:anonymous_aggregate" in operations["blockers"]
    assert "retention_category_missing:visit_attribution" in operations["blockers"]
    assert operations["metadata"]["retention_required_terms"] == (
        "measurement_events=365,anonymous_aggregate=1095,visit_attribution=90,acquisition_attribute=1095"
    )
