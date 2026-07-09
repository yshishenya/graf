from __future__ import annotations

from typing import Any

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.page_inventory import get_page_class_policy
from twobrain_rec_server.product_analytics.provider_config import ProductAnalyticsProviderConfig
from twobrain_rec_server.public.analytics import build_product_yandex_provider_context


def build_browser_provider_context(settings: Settings, page_class: str) -> dict[str, Any]:
    policy = get_page_class_policy(page_class)
    provider_config = ProductAnalyticsProviderConfig.from_settings(settings)
    posthog_active = bool(
        settings.product_analytics_enabled
        and provider_config.posthog.enabled
        and provider_config.posthog.autocapture_enabled
        and policy.posthog_autocapture_state == "enabled"
        and provider_config.posthog.credential_suppression_enabled
    )
    yandex_context = build_product_yandex_provider_context(settings, page_class)
    yandex_active = bool(yandex_context["enabled"])
    return {
        "enabled": posthog_active or yandex_active,
        "feature": "096-product-analytics-provider-rollout",
        "page_class": policy.page_class,
        "sensitivity": policy.sensitivity,
        "private_attributes": {
            "data-graf-analytics-private": "true",
            "data-ph-mask": "true",
            "data-ym-hide-content": "true",
            "data-ym-disable-keys": "true",
        },
        "posthog": {
            "enabled": posthog_active,
            "autocapture_enabled": posthog_active,
            "autocapture_scope": "all_browser_rendered_pages",
            "delivery_route": "first_party_browser_proxy",
            "capture_endpoint": "/api/v1/product-analytics/posthog-web-capture",
            "identity_state": "anonymous",
            "distinct_id": "graf_pseudo_browser_anonymous",
            "replay_enabled": False,
            "project_key": "configured_redacted" if provider_config.posthog.project_key_configured else "not_configured",
            "host": "configured_redacted" if provider_config.posthog.host else "not_configured",
            "credential_suppression": list(policy.credential_suppression),
            "retention_deletion_truth": "provider_lifecycle_documented",
        },
        "yandex": {
            **yandex_context,
            "state": policy.yandex_state,
            "webvisor_enabled": False,
            "click_map_enabled": False,
            "scroll_map_enabled": False,
            "form_analytics_enabled": False,
        },
        "rollback": {
            "mode": settings.product_analytics_rollback_mode,
            "behavior": policy.rollback_behavior,
            "product_impact": "measurement_gap_only",
        },
        "disclosure": {
            "posthog_first_party": True,
            "yandex_external": True,
            "paid_campaign_launch": "blocked",
        },
    }
