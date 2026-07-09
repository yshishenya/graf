from twobrain_rec_server.config import Settings
from twobrain_rec_server.public.analytics import (
    build_product_yandex_provider_context,
    build_public_analytics_context,
)


def test_093_public_yandex_scope_is_preserved_for_landing_and_download() -> None:
    settings = Settings(
        public_analytics_enabled=True,
        public_analytics_validation_mode="render_only",
        public_analytics_yandex_metrica_id="YA_TEST_COUNTER",
    )

    assert build_public_analytics_context(settings, "/")["enabled"] is True
    assert build_public_analytics_context(settings, "/download")["enabled"] is True
    assert build_public_analytics_context(settings, "/login")["enabled"] is False


def test_096_yandex_product_page_context_is_inventory_gated() -> None:
    settings = Settings(
        product_analytics_yandex_all_pages_enabled=True,
        product_analytics_yandex_counter_id="12345678",
        product_analytics_legal_approved=True,
    )

    public_context = build_product_yandex_provider_context(settings, "public_landing")
    admin_context = build_product_yandex_provider_context(settings, "admin")
    future_context = build_product_yandex_provider_context(settings, "future_browser_page")
    meeting_context = build_product_yandex_provider_context(settings, "meeting_result_detail")

    assert public_context["enabled"] is True
    assert public_context["counter_id"] == "12345678"
    assert admin_context["enabled"] is False
    assert admin_context["blocked_reason"] == "inventory_blocked"
    assert future_context["enabled"] is False
    assert future_context["blocked_reason"] == "inventory_blocked"
    assert meeting_context["enabled"] is False
    assert meeting_context["blocked_reason"] == "replay_unavailable"


def test_browser_controller_has_inventory_aware_yandex_gate() -> None:
    from pathlib import Path

    repo_root = Path(__file__).parents[4]
    analytics_js = (
        repo_root / "apps/server/src/twobrain_rec_server/public/static/public/analytics.js"
    ).read_text(encoding="utf-8")

    assert "isYandexPageAllowed" in analytics_js
    assert "pageConfig.yandex_state === \"approved_page_view_event\"" in analytics_js
    assert "api.providerBlocked = true" in analytics_js
    assert "initializeProductYandexProvider(productConfig)" in analytics_js
    assert "bindProductYandexUserID" in analytics_js
    assert "\"setUserID\"" in analytics_js
    assert "\"userParams\"" in analytics_js
