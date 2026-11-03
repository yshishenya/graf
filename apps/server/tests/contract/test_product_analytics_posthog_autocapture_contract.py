from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.product_analytics.browser_context import build_browser_provider_context
from twobrain_rec_server.product_analytics.page_inventory import page_class_policies
from twobrain_rec_server.public.analytics import PUBLIC_ANALYTICS_CONSENT_VERSION

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
    assert "providerConfig.posthog.capture_endpoint" in controller
    assert "sendBeacon" in controller
    assert "window.fetch(providerConfig.posthog.capture_endpoint" in controller
    assert "path_class: providerConfig.page_class" in controller
    assert "consent_state: currentConsentState" in controller
    assert "posthog.init" not in controller
    assert "posthog-js" not in controller
    assert "posthog.com" not in controller


def test_product_browser_context_exposes_one_opt_in_and_safe_allowlists(tmp_path: Path) -> None:
    context = build_browser_provider_context(_settings(tmp_path), "settings")

    assert context["browser_consent"]["copy_version"] == "2026-10-22.1"
    assert context["browser_consent"]["storage_key"] == "graf_public_cookie_consent"
    assert context["browser_consent"]["required_category"] == "analytics"
    assert context["browser_consent"]["replay_category"] == "behavior_replay"
    assert context["analytics_action_allowlist"] == [
        "nav_recordings",
        "settings_opened",
        "calendar_settings_opened",
    ]
    assert context["analytics_target_allowlist"] == [
        "recordings",
        "settings",
        "calendar",
        "calendar_settings",
        "navigation",
        "tab",
    ]
    assert context["yandex"]["webvisor_enabled"] is False
    assert context["yandex"]["click_map_enabled"] is False
    assert context["yandex"]["scroll_map_enabled"] is False


def test_posthog_web_capture_endpoint_accepts_safe_proxy_event_without_provider_secret(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/product-analytics/posthog-web-capture",
            json={
                "distinct_id": "graf_pseudo_user_c0ffee0000000000",
                "event_type": "click",
                "consent_state": "customized",
                "consent_copy_version": PUBLIC_ANALYTICS_CONSENT_VERSION,
                "page_class": "cabinet_home",
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


def test_posthog_web_capture_refuses_a_visitor_without_a_pseudonymous_identity(tmp_path: Path) -> None:
    """FR-010: no shared anonymous identifier may be invented for the provider.

    A default identifier reused by every unidentified visitor would be a
    long-lived identifier and would merge unrelated visits into one person.
    """

    app = create_app(_settings(tmp_path))

    with TestClient(app) as client:
        missing = client.post(
            "/api/v1/product-analytics/posthog-web-capture",
            json={
                "event_type": "pageview",
                "consent_state": "customized",
                "consent_copy_version": PUBLIC_ANALYTICS_CONSENT_VERSION,
                "page_class": "cabinet_home",
                "sensitivity": "product",
            },
        )
        shared_anonymous = client.post(
            "/api/v1/product-analytics/posthog-web-capture",
            json={
                "distinct_id": "graf_pseudo_browser_anonymous",
                "event_type": "pageview",
                "consent_state": "customized",
                "consent_copy_version": PUBLIC_ANALYTICS_CONSENT_VERSION,
                "page_class": "cabinet_home",
                "sensitivity": "product",
            },
        )

    assert missing.status_code == 422
    assert shared_anonymous.status_code == 400
    assert shared_anonymous.json()["code"] == "posthog_autocapture_identity_rejected"


def test_posthog_web_capture_endpoint_blocks_financial_page_inventory_entries(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/product-analytics/posthog-web-capture",
            json={
                "distinct_id": "graf_pseudo_user_c0ffee0000000000",
                "event_type": "click",
                "consent_state": "customized",
                "consent_copy_version": PUBLIC_ANALYTICS_CONSENT_VERSION,
                "page_class": "billing_invoice",
                "tag_name": "button",
                # Client-provided sensitivity cannot override the inventory.
                "sensitivity": "product",
            },
        )

    assert response.status_code == 403
    assert response.json()["code"] == "posthog_autocapture_page_blocked"


def test_posthog_web_capture_endpoint_uses_pseudonymous_identity_and_rejects_secret_material(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app = create_app(settings)

    with TestClient(app) as client:
        safe = client.post(
            "/api/v1/product-analytics/posthog-web-capture",
            json={
                "distinct_id": "graf_pseudo_user_c0ffee0000000000",
                "event_type": "click",
                "consent_state": "customized",
                "consent_copy_version": PUBLIC_ANALYTICS_CONSENT_VERSION,
                "page_class": "settings",
                "role": "tab",
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
                "consent_state": "customized",
                "consent_copy_version": PUBLIC_ANALYTICS_CONSENT_VERSION,
                "page_class": "settings",
                "role": "tab",
                "analytics_action": "access_token",
                "sensitivity": "product",
            },
        )
        private_identity = client.post(
            "/api/v1/product-analytics/posthog-web-capture",
            json={
                "distinct_id": "graf_pseudo_user_c0ffee0000000000",
                "event_type": "click",
                "consent_state": "customized",
                "consent_copy_version": PUBLIC_ANALYTICS_CONSENT_VERSION,
                "page_class": "settings",
                "role": "owner@example.test",
                "analytics_action": "calendar_settings_opened",
                "sensitivity": "product",
            },
        )
        raw_identity = client.post(
            "/api/v1/product-analytics/posthog-web-capture",
            json={
                "distinct_id": "owner@example.test",
                "event_type": "click",
                "consent_state": "customized",
                "consent_copy_version": PUBLIC_ANALYTICS_CONSENT_VERSION,
                "page_class": "settings",
                "analytics_action": "calendar_settings_opened",
            },
        )

    assert safe.status_code == 200
    assert safe.json()["status"] == "dry_run"
    assert secret.status_code == 400
    assert secret.json()["code"] == "posthog_autocapture_rejected"
    assert private_identity.status_code == 400
    assert private_identity.json()["code"] == "posthog_autocapture_field_rejected"
    assert raw_identity.status_code == 400
    assert raw_identity.json()["code"] == "posthog_autocapture_identity_rejected"


def test_posthog_web_capture_rejects_unallowlisted_proxy_fields(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/product-analytics/posthog-web-capture",
            json={
                "distinct_id": "graf_pseudo_user_c0ffee0000000000",
                "event_type": "click",
                "consent_state": "customized",
                "consent_copy_version": PUBLIC_ANALYTICS_CONSENT_VERSION,
                "page_class": "settings",
                "path_class": "https://private.example/settings?token=secret",
                "role": "owner",
                "identity_state": "raw_user",
                "device_class": "phone",
                "sensitivity": "public",
            },
        )

    assert response.status_code == 400
    assert response.json()["code"] == "posthog_autocapture_field_rejected"


def test_product_navigation_exposes_only_catalogued_internal_actions() -> None:
    sections = (
        Path(__file__).parents[2]
        / "src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html"
    ).read_text(encoding="utf-8")

    for action, target in (
        ("nav_recordings", "recordings"),
        ("settings_opened", "settings"),
        ("calendar_settings_opened", "calendar_settings"),
    ):
        assert f'data-analytics-action="{action}"' in sections
        assert f'data-analytics-target="{target}"' in sections


def test_old_public_revision_disables_internal_browser_measurement(tmp_path: Path) -> None:
    settings = _settings(tmp_path).model_copy(update={
        "public_analytics_consent_copy_version": "2026-09-15.1",
    })
    context = build_browser_provider_context(settings, "settings")
    assert context["enabled"] is False
    assert context["posthog"]["enabled"] is False
    assert context["yandex"]["enabled"] is False


def test_posthog_web_capture_checks_both_revisions_before_delivery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from twobrain_rec_server.product_analytics.posthog_client import PostHogClientWrapper

    settings = _settings(tmp_path)
    app = create_app(settings)
    delivered: list[dict] = []
    original = PostHogClientWrapper.capture_event

    def record(self, **kwargs):
        delivered.append(kwargs)
        return original(self, **kwargs)

    monkeypatch.setattr(PostHogClientWrapper, "capture_event", record)
    payload = {
        "distinct_id": "graf_pseudo_user_c0ffee0000000000",
        "consent_state": "customized",
        "page_class": "settings",
    }
    with TestClient(app) as client:
        assert client.post("/api/v1/product-analytics/posthog-web-capture", json=payload).status_code == 422
        for revision in ("2026-09-15.1", "unknown"):
            response = client.post(
                "/api/v1/product-analytics/posthog-web-capture",
                json={**payload, "consent_copy_version": revision},
            )
            assert response.status_code == 403
            assert response.json()["code"] == "posthog_autocapture_consent_revision_mismatch"
        assert delivered == []
        current = {**payload, "consent_copy_version": PUBLIC_ANALYTICS_CONSENT_VERSION}
        response = client.post("/api/v1/product-analytics/posthog-web-capture", json=current)
        assert response.status_code == 200
        assert len(delivered) == 1
        assert "consent_copy_version" not in delivered[0]["properties"]
        for revision in ("2026-09-15.1", "", "unknown"):
            settings.public_analytics_consent_copy_version = revision
            response = client.post("/api/v1/product-analytics/posthog-web-capture", json=current)
            assert response.status_code == 403
            assert response.json()["code"] == "posthog_autocapture_consent_revision_mismatch"
        assert len(delivered) == 1
