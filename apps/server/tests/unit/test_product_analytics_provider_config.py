from pathlib import Path

import pytest
from pydantic import ValidationError

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.provider_config import (
    ProductAnalyticsProviderConfig,
)


def _production_settings(**overrides):
    values = {
        "env": "production",
        "database_url": "postgresql+asyncpg://twobrain_rec:secret@rec-postgres:5432/twobrain_rec",
        "minio_endpoint": "rec-minio:9000",
        "minio_access_key": "twobrain_rec_api",
        "minio_secret_key": "prod-api-secret",
        "minio_bucket": "twobrain-rec-ingest",
        "web_csrf_secret": "prod-web-csrf-secret-32-bytes-minimum",
        "auth_ru_local_storage_attested": True,
    }
    values.update(overrides)
    return Settings(**values)


def test_provider_config_defaults_are_disabled_but_096_policy_is_declared() -> None:
    config = ProductAnalyticsProviderConfig.from_settings(Settings())

    assert config.provider_mode == "disabled"
    assert config.validation_mode == "disabled"
    assert config.rollback_mode == "none"
    assert config.posthog.enabled is False
    assert config.posthog.autocapture_enabled is True
    assert config.posthog.credential_suppression_enabled is True
    assert config.posthog.web_direct_enabled is True
    assert config.posthog.desktop_direct_enabled is False
    assert config.posthog.replay_enabled is False
    assert config.yandex.all_pages_enabled is False
    assert config.yandex.offline_enabled is False
    assert config.yandex.future_page_default == "blocked"
    assert config.live_provider_delivery_allowed is False
    assert config.approval_states["campaign_readiness"] == "blocked_by_096"
    assert config.campaign_launch_allowed is False


def test_provider_config_exposes_metadata_only_runtime_summary(tmp_path: Path) -> None:
    project_key_file = tmp_path / "posthog_project_key"
    oauth_file = tmp_path / "yandex_oauth_token"
    project_key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    oauth_file.write_text("synthetic-yandex-token", encoding="utf-8")

    config = ProductAnalyticsProviderConfig.from_settings(
        Settings(
            product_analytics_enabled=True,
            product_analytics_validation_mode="provider_smoke",
            product_analytics_provider_mode="parallel_measurement",
            product_analytics_posthog_enabled=True,
            product_analytics_posthog_host="https://analytics.example.test",
            product_analytics_posthog_project_key_file=project_key_file,
            product_analytics_yandex_all_pages_enabled=True,
            product_analytics_yandex_offline_enabled=True,
            product_analytics_yandex_counter_id="12345678",
            product_analytics_yandex_oauth_token_file=oauth_file,
        )
    )

    summary = config.as_redacted_dict()

    assert summary["posthog"]["project_key"] == "configured_redacted"
    assert summary["yandex"]["oauth_token"] == "configured_redacted"
    assert "synthetic-posthog-key" not in str(summary)
    assert "synthetic-yandex-token" not in str(summary)
    assert summary["posthog"]["autocapture_scope"] == "all_browser_rendered_pages"
    assert summary["yandex"]["counter_id"] == "configured_redacted"
    assert summary["live_provider_delivery_allowed"] is False
    assert summary["approval_states"]["campaign_readiness"] == "blocked_by_096"


def test_provider_modes_and_rollback_modes_are_restricted() -> None:
    with pytest.raises(ValidationError, match="product_analytics_provider_mode"):
        Settings(product_analytics_provider_mode="cloud_posthog")
    with pytest.raises(ValidationError, match="product_analytics_rollback_mode"):
        Settings(product_analytics_rollback_mode="delete_provider_data")


def test_production_rejects_posthog_autocapture_without_credential_suppression(tmp_path: Path) -> None:
    project_key_file = tmp_path / "posthog_project_key"
    project_key_file.write_text("synthetic-posthog-key", encoding="utf-8")

    with pytest.raises(ValidationError, match="credential suppression"):
        _production_settings(
            product_analytics_enabled=True,
            product_analytics_validation_mode="provider_smoke",
            product_analytics_provider_mode="posthog_primary",
            product_analytics_posthog_enabled=True,
            product_analytics_posthog_host="https://analytics.example.test",
            product_analytics_posthog_project_key_file=project_key_file,
            product_analytics_posthog_autocapture_enabled=True,
            product_analytics_posthog_credential_suppression_enabled=False,
        )


def test_production_rejects_yandex_offline_without_oauth_secret_file() -> None:
    with pytest.raises(ValidationError, match="yandex_oauth_token_file"):
        _production_settings(
            product_analytics_enabled=True,
            product_analytics_validation_mode="provider_smoke",
            product_analytics_provider_mode="parallel_measurement",
            product_analytics_yandex_offline_enabled=True,
            product_analytics_yandex_counter_id="12345678",
        )


def test_direct_desktop_posthog_route_requires_existing_approval_gate() -> None:
    with pytest.raises(ValidationError, match="direct desktop product analytics egress"):
        _production_settings(
            product_analytics_posthog_desktop_direct_enabled=True,
            product_analytics_direct_desktop_egress_enabled=True,
            product_analytics_direct_desktop_egress_approved=True,
            product_analytics_legal_approved=True,
            product_analytics_provider_smoke_approved=False,
        )


def test_live_safe_mode_requires_all_provider_delivery_approvals_in_production(tmp_path: Path) -> None:
    project_key_file = tmp_path / "posthog_project_key"
    project_key_file.write_text("synthetic-posthog-key", encoding="utf-8")

    with pytest.raises(ValidationError, match="live-safe product analytics provider delivery"):
        _production_settings(
            product_analytics_enabled=True,
            product_analytics_validation_mode="live_safe",
            product_analytics_provider_mode="posthog_primary",
            product_analytics_posthog_enabled=True,
            product_analytics_posthog_host="https://analytics.example.test",
            product_analytics_posthog_project_key_file=project_key_file,
            product_analytics_legal_approved=True,
            product_analytics_dashboard_ready=True,
            product_analytics_provider_smoke_approved=True,
            product_analytics_live_provider_delivery_approved=True,
        )


def test_campaign_readiness_flag_never_approves_096_campaign_launch(tmp_path: Path) -> None:
    project_key_file = tmp_path / "posthog_project_key"
    project_key_file.write_text("synthetic-posthog-key", encoding="utf-8")

    config = ProductAnalyticsProviderConfig.from_settings(
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
    )

    assert config.live_provider_delivery_allowed is True
    assert config.campaign_launch_allowed is False
