from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.provider_secrets import redact_provider_value


@dataclass(frozen=True, slots=True)
class PostHogProviderConfig:
    enabled: bool
    host: str | None
    project_key_configured: bool
    autocapture_enabled: bool
    credential_suppression_enabled: bool
    web_direct_enabled: bool
    desktop_direct_enabled: bool
    replay_enabled: bool
    retention_min_days: int

    @property
    def autocapture_scope(self) -> str:
        return "all_browser_rendered_pages" if self.autocapture_enabled else "disabled"

    def as_redacted_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "host": redact_provider_value(self.host),
            "project_key": "configured_redacted" if self.project_key_configured else "not_configured",
            "autocapture_enabled": self.autocapture_enabled,
            "autocapture_scope": self.autocapture_scope,
            "credential_suppression_enabled": self.credential_suppression_enabled,
            "web_direct_enabled": self.web_direct_enabled,
            "desktop_direct_enabled": self.desktop_direct_enabled,
            "replay_enabled": self.replay_enabled,
            "retention_min_days": self.retention_min_days,
        }


@dataclass(frozen=True, slots=True)
class YandexProviderConfig:
    all_pages_enabled: bool
    offline_enabled: bool
    counter_configured: bool
    oauth_token_configured: bool
    inventory_version: str
    future_page_default: str = "blocked"

    def as_redacted_dict(self) -> dict[str, Any]:
        return {
            "all_pages_enabled": self.all_pages_enabled,
            "offline_enabled": self.offline_enabled,
            "counter_id": "configured_redacted" if self.counter_configured else "not_configured",
            "oauth_token": "configured_redacted" if self.oauth_token_configured else "not_configured",
            "inventory_version": self.inventory_version,
            "future_page_default": self.future_page_default,
        }


@dataclass(frozen=True, slots=True)
class ProductAnalyticsProviderConfig:
    enabled: bool
    validation_mode: str
    provider_mode: str
    rollback_mode: str
    posthog: PostHogProviderConfig
    yandex: YandexProviderConfig
    live_provider_delivery_allowed: bool
    approval_states: dict[str, str]
    campaign_launch_allowed: bool

    @classmethod
    def from_settings(cls, settings: Settings) -> ProductAnalyticsProviderConfig:
        posthog = PostHogProviderConfig(
            enabled=settings.product_analytics_posthog_enabled,
            host=str(settings.product_analytics_posthog_host) if settings.product_analytics_posthog_host else None,
            project_key_configured=settings.product_analytics_posthog_project_key_file is not None,
            autocapture_enabled=settings.product_analytics_posthog_autocapture_enabled,
            credential_suppression_enabled=settings.product_analytics_posthog_credential_suppression_enabled,
            web_direct_enabled=settings.product_analytics_posthog_web_direct_enabled,
            desktop_direct_enabled=settings.product_analytics_posthog_desktop_direct_enabled,
            replay_enabled=settings.product_analytics_replay_enabled,
            retention_min_days=settings.product_analytics_retention_min_days,
        )
        yandex = YandexProviderConfig(
            all_pages_enabled=settings.product_analytics_yandex_all_pages_enabled,
            offline_enabled=settings.product_analytics_yandex_offline_enabled,
            counter_configured=settings.product_analytics_yandex_counter_id is not None,
            oauth_token_configured=settings.product_analytics_yandex_oauth_token_file is not None,
            inventory_version=settings.product_analytics_yandex_inventory_version,
        )
        return cls(
            enabled=settings.product_analytics_enabled,
            validation_mode=settings.product_analytics_validation_mode,
            provider_mode=settings.product_analytics_provider_mode,
            rollback_mode=settings.product_analytics_rollback_mode,
            posthog=posthog,
            yandex=yandex,
            live_provider_delivery_allowed=settings.product_analytics_live_provider_delivery_allowed(),
            approval_states={
                "legal": _approval_state(settings.product_analytics_legal_approved),
                "privacy": _approval_state(settings.product_analytics_privacy_approved),
                "security": _approval_state(settings.product_analytics_security_approved),
                "qa": _approval_state(settings.product_analytics_qa_approved),
                "disclosure": _approval_state(settings.product_analytics_disclosure_approved),
                "dashboard": "approved" if settings.product_analytics_dashboard_ready else "blocked",
                "provider_smoke": _approval_state(settings.product_analytics_provider_smoke_approved),
                "rollback": _approval_state(settings.product_analytics_rollback_approved),
                "live_provider_delivery": _approval_state(
                    settings.product_analytics_live_provider_delivery_approved
                ),
                "campaign_readiness": "blocked_by_096",
            },
            campaign_launch_allowed=False,
        )

    def as_redacted_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "validation_mode": self.validation_mode,
            "provider_mode": self.provider_mode,
            "rollback_mode": self.rollback_mode,
            "posthog": self.posthog.as_redacted_dict(),
            "yandex": self.yandex.as_redacted_dict(),
            "live_provider_delivery_allowed": self.live_provider_delivery_allowed,
            "approval_states": dict(self.approval_states),
            "campaign_launch_allowed": self.campaign_launch_allowed,
        }


def _approval_state(approved: bool) -> str:
    return "approved" if approved else "blocked"
