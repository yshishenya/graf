import subprocess
from pathlib import Path

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.provider_config import ProductAnalyticsProviderConfig

REPO_ROOT = Path(__file__).parents[4]
ROLLBACK_PATH = REPO_ROOT / "infra/scripts/rollback-product-analytics-providers.sh"


def test_rollback_script_reports_switches_without_state_change() -> None:
    result = subprocess.run(
        [str(ROLLBACK_PATH), "--target", "all"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    output = result.stdout

    assert "provider_rollback_result=pass" in output
    assert "rollback_execution=dry_run_no_state_change" in output
    assert "target=all" in output
    assert "product_impact=measurement_gap_only" in output
    assert "posthog_delivery_switch=TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_ENABLED=false" in output
    assert "posthog_stack_stop=dry_run_metadata_only" in output
    assert "posthog_deploy_dry_run=required_after_switch" in output
    assert "posthog_move_out_failure=restore_endpoint_or_disable_delivery" in output
    assert "yandex_all_pages_switch=TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_ALL_PAGES_ENABLED=false" in output
    assert "yandex_offline_switch=TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_OFFLINE_ENABLED=false" in output
    assert "provider_validation_switch=TWOBRAIN_PRODUCT_ANALYTICS_VALIDATION_MODE=disabled" in output
    assert "normal_product_workflows=preserved" in output
    assert "secrets=not_printed" in output


def test_rollback_mode_is_configured_as_measurement_gap_not_product_failure() -> None:
    config = ProductAnalyticsProviderConfig.from_settings(
        Settings(product_analytics_rollback_mode="all_disabled")
    ).as_redacted_dict()

    assert config["rollback_mode"] == "all_disabled"
    assert config["posthog"]["replay_enabled"] is False
    assert config["campaign_launch_allowed"] is False
