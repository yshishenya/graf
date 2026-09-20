"""Degradation order: measurement goes first, the product keeps working (T067, FR-032).

The failure this covers is the one that motivated the whole feature: a traffic
spike on the site must degrade *measurement*, never the product. The order is
asserted on the two surfaces that actually decide it — the runtime guard that
disables measurement, and the application that must keep answering — instead of
being asserted in prose.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.product_analytics.readiness import build_rollout_readiness_report

REPO_ROOT = Path(__file__).resolve().parents[4]
GUARD_PATH = REPO_ROOT / "infra/scripts/posthog-runtime-guard.sh"
ROLLBACK_PATH = REPO_ROOT / "infra/scripts/rollback-product-analytics-providers.sh"
BASH = shutil.which("bash") or "/bin/bash"

# The variables the guard may switch off. Everything the product itself needs to
# keep running is deliberately absent from this list.
MEASUREMENT_SWITCHES = (
    "TWOBRAIN_PRODUCT_ANALYTICS_ENABLED",
    "TWOBRAIN_PRODUCT_ANALYTICS_PROVIDER_MODE",
    "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_ENABLED",
    "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_WEB_DIRECT_ENABLED",
    "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_DESKTOP_DIRECT_ENABLED",
    "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_AUTOCAPTURE_ENABLED",
    "TWOBRAIN_PRODUCT_ANALYTICS_REPLAY_ENABLED",
    "TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_ALL_PAGES_ENABLED",
    "TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_OFFLINE_ENABLED",
    "TWOBRAIN_PRODUCT_ANALYTICS_VALIDATION_MODE",
)

PRODUCT_SURFACES_NEVER_TOUCHED = (
    "TWOBRAIN_DATABASE_URL",
    "TWOBRAIN_MINIO_BUCKET",
    "TWOBRAIN_INGEST_ENABLED",
    "TWOBRAIN_CABINET_ENABLED",
)

DISABLED_MEASUREMENT_SETTINGS = {
    "product_analytics_enabled": False,
    "product_analytics_validation_mode": "disabled",
    "product_analytics_provider_mode": "disabled",
    "product_analytics_posthog_enabled": False,
    "product_analytics_yandex_all_pages_enabled": False,
    "product_analytics_yandex_offline_enabled": False,
    "product_analytics_replay_enabled": False,
}


def _application() -> TestClient:
    return TestClient(
        create_app(
            Settings(
                database_url="postgresql+asyncpg://nobody@127.0.0.1:1/none",
                minio_access_key="test",
                minio_secret_key="test",
                minio_bucket="test-bucket",
                **DISABLED_MEASUREMENT_SETTINGS,
            )
        )
    )


def test_the_product_answers_over_http_while_measurement_is_disabled() -> None:
    """FR-032: measurement off must not be product off."""

    with _application() as client:
        live = client.get("/api/v1/health/live")
        catalog = client.get("/api/v1/product-analytics/catalog")
        ingest = client.post(
            "/api/v1/product-analytics/events", json={"event_name": "desktop_first_opened"}
        )
        web_capture = client.post(
            "/api/v1/product-analytics/posthog-web-capture",
            json={
                "distinct_id": "graf_pseudo_visitor_abc",
                "consent_state": "accepted_all",
                "page_class": "public_landing",
            },
        )

    assert live.status_code == 200
    assert live.json() == {"status": "ok"}

    assert catalog.status_code == 200
    payload = catalog.json()
    assert payload["enabled"] is False
    assert payload["provider_config"]["enabled"] is False
    assert payload["rollout_readiness"]["campaign_launch_allowed"] is False

    # The measurement routes refuse, and they refuse for the honest reason.
    assert ingest.status_code == 403
    assert ingest.json()["code"] == "product_analytics_disabled"
    assert web_capture.status_code == 403
    assert web_capture.json()["code"] == "posthog_autocapture_disabled"


def test_disabling_measurement_is_reported_as_a_measurement_gap_only() -> None:
    """The readiness report names the consequence instead of staying silent."""

    report = build_rollout_readiness_report(Settings(**DISABLED_MEASUREMENT_SETTINGS)).as_dict()

    assert report["verdict"] == "blocked"
    assert "product_analytics_disabled" in report["blockers"]
    assert report["states"]["live_provider_delivery"] == "blocked"
    assert report["states"]["provider_smoke"] == "blocked"
    assert report["campaign_launch_allowed"] is False
    assert report["approval_gate"]["campaign_launch_allowed"] is False


def test_the_guard_switches_off_measurement_and_nothing_else() -> None:
    """The disable list is measurement-only, and the product keys are absent."""

    script = GUARD_PATH.read_text(encoding="utf-8")

    for key in MEASUREMENT_SWITCHES:
        assert script.count(key) >= 1, f"{key} is not switched off by the guard"
    for key in PRODUCT_SURFACES_NEVER_TOUCHED:
        assert key not in script, f"the guard must not touch {key}"


def test_only_analytics_scope_reasons_may_disable_measurement() -> None:
    """FR-030, FR-031, FR-032: ordering is by scope, analytics first."""

    script = GUARD_PATH.read_text(encoding="utf-8")

    assert 'if [[ -n "$analytics_disable_reasons" ]]; then' in script
    assert 'analytics_disable_reasons+=(' not in script, (
        "disable reasons must be collected by the analytics scope only"
    )
    assert 'host_disable_reasons' not in script
    assert "posthog_guard_product_impact=measurement_gap_only" in script
    assert "product_impact=measurement_gap_only" in script


def test_the_operator_rollback_path_states_the_same_order() -> None:
    """T064: the documented procedure keeps the product out of the rollback."""

    result = subprocess.run(
        [BASH, str(ROLLBACK_PATH), "--metadata-only", "--target", "all"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "product_impact=measurement_gap_only" in result.stdout
    assert "normal_product_workflows=preserved" in result.stdout
    assert "rollback_execution=metadata_only_no_state_change" in result.stdout
    assert "provider_state_mutation=not_requested" in result.stdout
    assert "operator_executor_hook=not_invoked" in result.stdout
    assert "TWOBRAIN_PRODUCT_ANALYTICS_ENABLED=false" not in result.stdout, (
        "the rollback contract disables the provider keys, not the runtime flag "
        "the product reads"
    )
