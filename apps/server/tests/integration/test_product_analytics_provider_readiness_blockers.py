from pathlib import Path

from twobrain_rec_server.config import Settings
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
    assert report["states"]["product_rollout"] == "blocked_not_approved_by_096"
    assert report["states"]["campaign_launch"] == "blocked_not_approved_by_096"
    assert report["product_rollout_allowed"] is False
    assert report["campaign_launch_allowed"] is False


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
    assert report["states"]["product_rollout"] == "blocked_not_approved_by_096"
    assert report["states"]["campaign_launch"] == "blocked_not_approved_by_096"
    assert "product_rollout_separate_approval_required" in report["rollout_blockers"]
    assert "paid_campaign_launch_blocked_by_096" in report["rollout_blockers"]
    assert report["product_rollout_allowed"] is False
    assert report["campaign_launch_allowed"] is False


def test_live_safe_provider_delivery_can_be_approved_without_product_or_campaign_rollout(tmp_path: Path) -> None:
    project_key_file = tmp_path / "posthog_project_key"
    project_key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    report = build_rollout_readiness_report(
        Settings(
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
    ).as_dict()

    assert report["verdict"] == "infra_smoke_ready"
    assert report["states"]["live_provider_delivery"] == "approved"
    assert report["states"]["campaign_launch"] == "blocked_not_approved_by_096"
    assert report["product_rollout_allowed"] is False
    assert report["campaign_launch_allowed"] is False
