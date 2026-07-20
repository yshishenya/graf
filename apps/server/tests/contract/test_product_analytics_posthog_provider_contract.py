from pathlib import Path

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.provider_config import ProductAnalyticsProviderConfig
from twobrain_rec_server.product_analytics.provider_readiness import build_provider_readiness
from twobrain_rec_server.product_analytics.retention import provider_lifecycle_records


def test_posthog_provider_readiness_declares_access_lifecycle_and_dashboard_caveats(tmp_path: Path) -> None:
    project_key_file = tmp_path / "posthog_project_key"
    project_key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    settings = Settings(
        product_analytics_enabled=True,
        product_analytics_validation_mode="provider_smoke",
        product_analytics_provider_mode="posthog_primary",
        product_analytics_posthog_enabled=True,
        product_analytics_posthog_host="https://analytics.example.test",
        product_analytics_posthog_project_key_file=project_key_file,
    )

    readiness = build_provider_readiness(settings).posthog.as_dict()

    assert readiness["configured"] is True
    assert readiness["metadata"]["rbac_access_model"] == "role_based_metadata_only"
    assert readiness["metadata"]["audit_expectation"] == "provider_config_access_export_replay_retention_changes"
    assert readiness["metadata"]["retention_deletion_lifecycle"] == "documented"
    assert readiness["metadata"]["dashboard_caveat"] == "required"
    assert readiness["metadata"]["deploy_handoff"] == "dry_run_documented"
    assert readiness["metadata"]["resource_thresholds"] == "configured"


def test_posthog_config_redacts_host_and_project_key(tmp_path: Path) -> None:
    project_key_file = tmp_path / "posthog_project_key"
    project_key_file.write_text("synthetic-posthog-key", encoding="utf-8")

    config = ProductAnalyticsProviderConfig.from_settings(
        Settings(
            product_analytics_enabled=True,
            product_analytics_validation_mode="provider_smoke",
            product_analytics_provider_mode="posthog_primary",
            product_analytics_posthog_enabled=True,
            product_analytics_posthog_host="https://analytics.example.test",
            product_analytics_posthog_project_key_file=project_key_file,
        )
    ).as_redacted_dict()

    assert config["posthog"]["host"] == "configured_redacted"
    assert config["posthog"]["project_key"] == "configured_redacted"
    assert "synthetic-posthog-key" not in str(config)
    assert "analytics.example.test" not in str(config)


def test_posthog_lifecycle_truth_covers_events_autocapture_replay_backups_and_exports() -> None:
    records = {
        (record.provider, record.data_class): record
        for record in provider_lifecycle_records()
        if record.provider == "posthog"
    }

    assert ("posthog", "activation_event") in records
    assert ("posthog", "autocapture_event") in records
    assert ("posthog", "replay_recording") in records
    assert ("posthog", "backup") in records
    assert records[("posthog", "activation_event")].retention_days >= 90
    assert records[("posthog", "replay_recording")].deletion_scope == "not_collected"
    assert records[("posthog", "backup")].export_policy == "forbidden_content_bearing_export"
