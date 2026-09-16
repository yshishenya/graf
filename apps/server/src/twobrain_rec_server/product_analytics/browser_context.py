from __future__ import annotations

from typing import Any

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.identity import build_safe_identity
from twobrain_rec_server.product_analytics.page_inventory import (
    get_page_class_policy,
    product_analytics_action_allowlist,
    product_analytics_target_allowlist,
)
from twobrain_rec_server.product_analytics.provider_config import ProductAnalyticsProviderConfig
from twobrain_rec_server.public.analytics import (
    PUBLIC_ANALYTICS_CONSENT_REVISION,
    PUBLIC_ANALYTICS_CONSENT_STORAGE_KEY,
    build_product_yandex_provider_context,
    public_analytics_consent_states,
    public_analytics_consent_transitions,
)


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
    browser_consent = {
        "copy_version": settings.public_analytics_consent_copy_version,
        "revision": PUBLIC_ANALYTICS_CONSENT_REVISION,
        "storage_key": PUBLIC_ANALYTICS_CONSENT_STORAGE_KEY,
        "categories": ["necessary", "analytics", "advertising_attribution", "behavior_replay"],
        "states": list(public_analytics_consent_states()),
        "transitions": {
            key: list(values) for key, values in public_analytics_consent_transitions().items()
        },
        "required_category": "analytics",
        "replay_category": "behavior_replay",
    }
    return {
        "enabled": posthog_active or yandex_active,
        "feature": "096-product-analytics-provider-rollout",
        "validation_mode": settings.product_analytics_validation_mode,
        "provider_mode": settings.product_analytics_provider_mode,
        "page_class": policy.page_class,
        "sensitivity": policy.sensitivity,
        "browser_consent": browser_consent,
        "consent_copy_version": browser_consent["copy_version"],
        "consent_revision": browser_consent["revision"],
        "consent_storage_key": browser_consent["storage_key"],
        "consent_categories": browser_consent["categories"],
        "analytics_action_allowlist": list(product_analytics_action_allowlist()),
        "analytics_target_allowlist": list(product_analytics_target_allowlist()),
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
            "consent_category": "analytics",
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


def build_request_browser_provider_context(
    request: Any,
    page_class: str,
    *,
    principal: Any | None = None,
    tenant_scope: Any | None = None,
    device_class: str = "browser",
    include_workspace: bool = True,
) -> dict[str, Any]:
    """Build page analytics context from the request's runtime settings."""
    app_state = getattr(getattr(request, "app", None), "state", None)
    settings = getattr(app_state, "settings", None) or Settings()
    provider = build_browser_provider_context(settings, page_class)
    if principal is None:
        return provider

    workspace_source_id = getattr(tenant_scope, "workspace_id", None)
    if workspace_source_id is None:
        workspace_source_id = getattr(principal, "session_workspace_id", None)
    if include_workspace and workspace_source_id is None:
        workspace_ids = getattr(principal, "workspace_ids", frozenset()) or frozenset()
        if len(workspace_ids) == 1:
            workspace_source_id = next(iter(workspace_ids))
    identity = build_safe_identity(
        user_source_id=str(principal.user_id),
        workspace_source_id=(
            str(workspace_source_id) if include_workspace and workspace_source_id else None
        ),
        device_class=device_class,
    )
    posthog = provider["posthog"]
    posthog.update(
        {
            "identity_state": "authenticated_pseudonymous",
            "distinct_id": identity.posthog_distinct_id,
            "workspace_pseudonym": identity.workspace_pseudonym,
            "device_class": identity.device_class,
        }
    )
    yandex = provider["yandex"]
    yandex.update(
        {
            "user_id": identity.stable_pseudonymous_user_id,
            "user_id_source": "graf_pseudonymous_user",
        }
    )
    return provider
