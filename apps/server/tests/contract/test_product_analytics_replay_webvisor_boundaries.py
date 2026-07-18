from pathlib import Path

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.browser_context import build_browser_provider_context
from twobrain_rec_server.product_analytics.page_inventory import get_page_class_policy
from twobrain_rec_server.product_analytics.replay_masking import replay_decision_for_policy


def test_posthog_autocapture_does_not_enable_posthog_replay_or_yandex_webvisor(tmp_path: Path) -> None:
    key_file = tmp_path / "posthog_project_key"
    key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    settings = Settings(
        product_analytics_enabled=True,
        product_analytics_provider_mode="parallel_measurement",
        product_analytics_validation_mode="provider_smoke",
        product_analytics_posthog_enabled=True,
        product_analytics_posthog_host="https://analytics.example.test",
        product_analytics_posthog_project_key_file=key_file,
        product_analytics_yandex_all_pages_enabled=True,
        product_analytics_yandex_counter_id="12345678",
        product_analytics_legal_approved=True,
    )

    context = build_browser_provider_context(settings, "meeting_result_detail")

    assert context["posthog"]["autocapture_enabled"] is True
    assert context["posthog"]["replay_enabled"] is False
    assert context["yandex"]["enabled"] is False
    assert context["yandex"]["webvisor_enabled"] is False
    assert context["yandex"]["click_map_enabled"] is False
    assert context["yandex"]["scroll_map_enabled"] is False
    assert context["yandex"]["form_analytics_enabled"] is False


def test_replay_masking_keeps_private_attributes_for_unavailable_pages() -> None:
    decision = replay_decision_for_policy(get_page_class_policy("admin"))

    assert decision.replay_allowed is False
    assert decision.attributes["data-ph-mask"] == "true"
    assert decision.attributes["data-graf-replay-disabled"] == "true"
    assert "data-ph-no-capture" not in decision.attributes
    assert decision.attributes["data-ym-hide-content"] == "true"
