from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.product_analytics.identity import build_safe_identity
from twobrain_rec_server.product_analytics.ingest import ProductAnalyticsIngestService

REPO_ROOT = Path(__file__).parents[4]
COMPOSE_PATH = REPO_ROOT / "infra/docker-compose.yml"
ENV_TEMPLATE_PATH = REPO_ROOT / "infra/env/rec.production.env.example"


def _compose() -> dict:
    return yaml.safe_load(COMPOSE_PATH.read_text())


def _active_env_template_keys() -> set[str]:
    keys: set[str] = set()
    for line in ENV_TEMPLATE_PATH.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        keys.add(stripped.split("=", maxsplit=1)[0])
    return keys


def test_product_analytics_runtime_env_is_api_only_and_disabled_by_default() -> None:
    compose = _compose()
    api_env = compose["services"]["rec-api"]["environment"]
    worker_env = compose["services"]["rec-processing-worker"]["environment"]
    migrate_env = compose["services"]["rec-migrate"]["environment"]
    env_keys = _active_env_template_keys()
    env_template = ENV_TEMPLATE_PATH.read_text(encoding="utf-8")

    assert api_env["TWOBRAIN_PRODUCT_ANALYTICS_ENABLED"] == "${TWOBRAIN_PRODUCT_ANALYTICS_ENABLED:-false}"
    assert api_env["TWOBRAIN_PRODUCT_ANALYTICS_VALIDATION_MODE"] == (
        "${TWOBRAIN_PRODUCT_ANALYTICS_VALIDATION_MODE:-disabled}"
    )
    assert api_env["TWOBRAIN_PRODUCT_ANALYTICS_PROVIDER_MODE"] == (
        "${TWOBRAIN_PRODUCT_ANALYTICS_PROVIDER_MODE:-disabled}"
    )
    assert api_env["TWOBRAIN_PRODUCT_ANALYTICS_RETENTION_MIN_DAYS"] == (
        "${TWOBRAIN_PRODUCT_ANALYTICS_RETENTION_MIN_DAYS:-90}"
    )
    assert "TWOBRAIN_PRODUCT_ANALYTICS_ENABLED" not in worker_env
    assert "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_PROJECT_KEY_FILE" not in worker_env
    assert "TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_OAUTH_TOKEN_FILE" not in worker_env
    assert "TWOBRAIN_PRODUCT_ANALYTICS_ENABLED" not in migrate_env
    assert "TWOBRAIN_PRODUCT_ANALYTICS_ENABLED" not in env_keys
    assert "TWOBRAIN_PRODUCT_ANALYTICS_RETENTION_MIN_DAYS" not in env_keys
    assert "# TWOBRAIN_PRODUCT_ANALYTICS_ENABLED=false" in env_template
    assert "# TWOBRAIN_PRODUCT_ANALYTICS_RETENTION_MIN_DAYS=90" in env_template


def test_product_analytics_api_is_disabled_by_default() -> None:
    app = create_app(Settings())

    with TestClient(app) as client:
        catalog = client.get("/api/v1/product-analytics/catalog")
        event_response = client.post(
            "/api/v1/product-analytics/events",
            json={"event_name": "desktop_first_opened", "properties": {"platform": "macos"}},
        )

    assert catalog.status_code == 200
    assert catalog.json()["enabled"] is False
    assert event_response.status_code == 403
    assert event_response.json()["code"] == "product_analytics_disabled"


def test_product_analytics_ingress_rejects_oversized_json_before_validation() -> None:
    settings = Settings(product_analytics_enabled=True)
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/product-analytics/events",
            content=b"{" + b"a" * 262_144 + b"}",
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 413
    assert response.json()["code"] == "product_analytics_body_too_large"


def test_synthetic_source_to_first_value_funnel_is_safe_and_server_mediated() -> None:
    identity = build_safe_identity(user_source_id="user-094")
    service = ProductAnalyticsIngestService(
        Settings(product_analytics_enabled=True, product_analytics_validation_mode="render_only")
    )
    events = [
        ("desktop_first_opened", {"platform": "macos", "bridge_present": True}),
        (
            "desktop_account_connected",
            {
                "auth_method_category": "oauth_provider",
                "account_connection_state": "connected",
                "bridge_present": True,
                "attribution_reliability": "campaign_linked_reliable",
            },
        ),
        (
            "desktop_autorecord_enabled",
            {"policy_state": "enabled", "previous_state": "disabled", "source": "user_action", "surface": "desktop"},
        ),
        (
            "first_recording_completed",
            {"duration_bucket": "5_15m", "capture_mode": "system_audio", "completion_state": "completed"},
        ),
        (
            "first_result_viewed",
            {"result_state": "ready", "surface": "cabinet_web", "useful_output_present": True},
        ),
        (
            "first_value_session_completed",
            {
                "first_recording_completed": True,
                "first_result_viewed": True,
                "useful_output_present": True,
                "useful_result_type": "summary",
                "attribution_reliability": "campaign_linked_reliable",
            },
        ),
    ]

    results = [
        service.ingest(
            {
                "event_name": event_name,
                "stable_pseudonymous_user_id": identity.stable_pseudonymous_user_id,
                "properties": properties,
            }
        )
        for event_name, properties in events
    ]

    assert [result.accepted for result in results] == [True, True, True, True, True, True]
    assert [result.event.event_name for result in results if result.event] == [event_name for event_name, _ in events]
    assert all(result.event and result.event.delivery_mode == "server_mediated" for result in results)
    assert all(result.delivery_gap for result in results)


def test_provider_failure_is_reported_as_measurement_gap_without_blocking_acceptance() -> None:
    identity = build_safe_identity(user_source_id="user-094")
    service = ProductAnalyticsIngestService(
        Settings(product_analytics_enabled=True, product_analytics_validation_mode="render_only")
    )

    result = service.ingest(
        {
            "event_name": "desktop_account_connected",
            "stable_pseudonymous_user_id": identity.stable_pseudonymous_user_id,
            "properties": {
                "auth_method_category": "oauth_provider",
                "account_connection_state": "connected",
                "bridge_present": True,
            },
        }
    )

    assert result.accepted is True
    assert result.delivery_gap is not None
    assert result.delivery_gap.status == "measurement_gap"
    assert {provider.status for provider in result.provider_results} == {"disabled"}


def test_enabled_api_accepts_synthetic_event_without_live_provider_delivery() -> None:
    identity = build_safe_identity(user_source_id="user-094")
    app = create_app(Settings(product_analytics_enabled=True, product_analytics_validation_mode="render_only"))

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/product-analytics/events",
            json={
                "event_name": "desktop_first_opened",
                "stable_pseudonymous_user_id": identity.stable_pseudonymous_user_id,
                "properties": {"platform": "macos", "bridge_present": True},
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["event"]["event_name"] == "desktop_first_opened"
    assert body["provider_results"][0]["status"] == "disabled"


def test_desktop_posthog_proxy_endpoint_accepts_posthog_style_body_in_provider_smoke(tmp_path: Path) -> None:
    key_file = tmp_path / "posthog_project_key"
    key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    app = create_app(
        Settings(
            product_analytics_enabled=True,
            product_analytics_validation_mode="provider_smoke",
            product_analytics_provider_mode="posthog_primary",
            product_analytics_posthog_enabled=True,
            product_analytics_posthog_host="https://analytics.example.test",
            product_analytics_posthog_project_key_file=key_file,
            product_analytics_posthog_desktop_direct_enabled=True,
            product_analytics_direct_desktop_egress_enabled=True,
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/product-analytics/posthog-desktop-capture",
            json={
                "event": "desktop_account_connected",
                "distinct_id": "graf_pseudo_user_0940000000000000",
                "telemetry_gate_state": "accepted",
                "api_key_state": "server_injected_redacted",
                "properties": {
                    "auth_method_category": "oauth_provider",
                    "account_connection_state": "connected",
                    "bridge_present": True,
                    "delivery_mode": "first_party_desktop_proxy",
                    "source_feature": "096-product-analytics-provider-rollout",
                },
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "dry_run"
    assert "synthetic-posthog-key" not in str(body)
    assert "properties" not in str(body)


def test_desktop_posthog_proxy_requires_pseudonymous_distinct_id(tmp_path: Path) -> None:
    key_file = tmp_path / "posthog_project_key"
    key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    app = create_app(
        Settings(
            product_analytics_enabled=True,
            product_analytics_validation_mode="provider_smoke",
            product_analytics_provider_mode="posthog_primary",
            product_analytics_posthog_enabled=True,
            product_analytics_posthog_host="https://analytics.example.test",
            product_analytics_posthog_project_key_file=key_file,
            product_analytics_posthog_desktop_direct_enabled=True,
            product_analytics_direct_desktop_egress_enabled=True,
        )
    )

    with TestClient(app) as client:
        missing = client.post(
            "/api/v1/product-analytics/posthog-desktop-capture",
            json={
                "event": "desktop_first_opened",
                "telemetry_gate_state": "accepted",
                "api_key_state": "server_injected_redacted",
                "properties": {"platform": "macos", "bridge_present": True},
            },
        )
        raw = client.post(
            "/api/v1/product-analytics/posthog-desktop-capture",
            json={
                "event": "desktop_first_opened",
                "distinct_id": "user@example.test",
                "telemetry_gate_state": "accepted",
                "api_key_state": "server_injected_redacted",
                "properties": {"platform": "macos", "bridge_present": True},
            },
        )

    assert missing.status_code == 422
    assert raw.status_code == 400
    assert raw.json()["code"] == "posthog_desktop_event_rejected"
