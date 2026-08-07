from pathlib import Path

from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.product_analytics.browser_context import build_browser_provider_context
from twobrain_rec_server.product_analytics.page_inventory import page_class_policies

REPO_ROOT = Path(__file__).parents[4]
ANALYTICS_JS = REPO_ROOT / "apps/server/src/twobrain_rec_server/public/static/public/analytics.js"


def _settings(tmp_path: Path) -> Settings:
    key_file = tmp_path / "posthog_project_key"
    key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    return Settings(
        product_analytics_enabled=True,
        product_analytics_provider_mode="posthog_primary",
        product_analytics_validation_mode="provider_smoke",
        product_analytics_posthog_enabled=True,
        product_analytics_posthog_host="https://analytics.example.test",
        product_analytics_posthog_project_key_file=key_file,
    )


def test_posthog_autocapture_context_excludes_financial_page_classes(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    contexts = {
        policy.page_class: build_browser_provider_context(settings, policy.page_class)
        for policy in page_class_policies()
    }
    financial_page_classes = {
        policy.page_class for policy in page_class_policies() if policy.sensitivity == "financial"
    }
    enabled_contexts = [
        context for page_class, context in contexts.items() if page_class not in financial_page_classes
    ]
    financial_contexts = [contexts[page_class] for page_class in financial_page_classes]

    assert all(context["posthog"]["enabled"] is True for context in enabled_contexts)
    assert all(context["posthog"]["autocapture_enabled"] is True for context in enabled_contexts)
    assert all(context["enabled"] is False for context in financial_contexts)
    assert all(context["posthog"]["enabled"] is False for context in financial_contexts)
    assert all(context["posthog"]["autocapture_enabled"] is False for context in financial_contexts)
    assert all(context["yandex"]["enabled"] is False for context in financial_contexts)
    assert all(context["posthog"]["replay_enabled"] is False for context in contexts.values())
    assert all(context["posthog"]["autocapture_scope"] == "all_browser_rendered_pages" for context in contexts.values())
    assert all(context["posthog"]["delivery_route"] == "first_party_browser_proxy" for context in contexts.values())
    assert all(
        context["posthog"]["capture_endpoint"] == "/api/v1/product-analytics/posthog-web-capture"
        for context in contexts.values()
    )


def test_future_pages_default_to_posthog_autocapture_and_yandex_blocked(tmp_path: Path) -> None:
    context = build_browser_provider_context(_settings(tmp_path), "future_browser_page")

    assert context["posthog"]["autocapture_enabled"] is True
    assert context["yandex"]["enabled"] is False
    assert context["yandex"]["state"] == "blocked"
    assert context["rollback"]["product_impact"] == "measurement_gap_only"


def test_posthog_autocapture_controller_uses_first_party_proxy_not_posthog_sdk() -> None:
    controller = ANALYTICS_JS.read_text(encoding="utf-8")

    assert "/api/v1/product-analytics/posthog-web-capture" not in controller
    assert "capture_endpoint" in controller
    assert "sendBeacon" in controller
    assert "fetch(captureEndpoint" in controller
    assert "posthog.init" not in controller
    assert "posthog-js" not in controller
    assert "posthog.com" not in controller


def test_posthog_web_capture_endpoint_accepts_safe_proxy_event_without_provider_secret(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/product-analytics/posthog-web-capture",
            json={
                "event_type": "click",
                "page_class": "cabinet",
                "tag_name": "button",
                "role": "tab",
                "analytics_action": "nav_recordings",
                "sensitivity": "product",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "dry_run"
    assert "synthetic-posthog-key" not in str(body)
    assert "properties" not in str(body)


def test_posthog_web_capture_endpoint_uses_pseudonymous_identity_and_rejects_secret_material(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app = create_app(settings)

    with TestClient(app) as client:
        safe = client.post(
            "/api/v1/product-analytics/posthog-web-capture",
            json={
                "distinct_id": "graf_pseudo_user_c0ffee0000000000",
                "event_type": "click",
                "page_class": "settings",
                "role": "owner@example.test",
                "analytics_action": "calendar_settings_opened",
                "identity_state": "authenticated_pseudonymous",
                "workspace_pseudonym": "graf_pseudo_workspace_c0ffee0000000000",
                "device_class": "browser",
                "sensitivity": "product",
            },
        )
        secret = client.post(
            "/api/v1/product-analytics/posthog-web-capture",
            json={
                "distinct_id": "graf_pseudo_user_c0ffee0000000000",
                "event_type": "click",
                "page_class": "settings",
                "role": "owner@example.test",
                "analytics_action": "access_token",
                "sensitivity": "product",
            },
        )
        raw_identity = client.post(
            "/api/v1/product-analytics/posthog-web-capture",
            json={
                "distinct_id": "owner@example.test",
                "event_type": "click",
                "page_class": "settings",
                "analytics_action": "calendar_settings_opened",
            },
        )

    assert safe.status_code == 200
    assert safe.json()["status"] == "dry_run"
    assert secret.status_code == 400
    assert secret.json()["code"] == "posthog_autocapture_rejected"
    assert raw_identity.status_code == 400
    assert raw_identity.json()["code"] == "posthog_autocapture_identity_rejected"
