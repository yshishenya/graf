from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from twobrain_rec_server.config import Settings


@dataclass(frozen=True, slots=True)
class ProviderReadiness:
    provider: str
    enabled: bool
    configured: bool
    blockers: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "enabled": self.enabled,
            "configured": self.configured,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True, slots=True)
class ProductAnalyticsProviderReadiness:
    provider_mode: str
    posthog: ProviderReadiness
    yandex_all_pages: ProviderReadiness
    yandex_offline: ProviderReadiness

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider_mode": self.provider_mode,
            "posthog": self.posthog.as_dict(),
            "yandex_all_pages": self.yandex_all_pages.as_dict(),
            "yandex_offline": self.yandex_offline.as_dict(),
        }


def build_provider_readiness(settings: Settings) -> ProductAnalyticsProviderReadiness:
    posthog_blockers: list[str] = []
    if settings.product_analytics_posthog_enabled:
        if settings.product_analytics_posthog_host is None:
            posthog_blockers.append("missing_posthog_host")
        if settings.product_analytics_posthog_project_key_file is None:
            posthog_blockers.append("missing_posthog_project_key_file")
    else:
        posthog_blockers.append("posthog_disabled")

    yandex_all_pages_blockers: list[str] = []
    if settings.product_analytics_yandex_all_pages_enabled:
        if settings.product_analytics_yandex_counter_id is None:
            yandex_all_pages_blockers.append("missing_yandex_counter_id")
        if not settings.product_analytics_legal_approved:
            yandex_all_pages_blockers.append("legal_not_approved")
    else:
        yandex_all_pages_blockers.append("yandex_all_pages_disabled")

    yandex_offline_blockers: list[str] = []
    if settings.product_analytics_yandex_offline_enabled:
        if settings.product_analytics_yandex_counter_id is None:
            yandex_offline_blockers.append("missing_yandex_counter_id")
        if settings.product_analytics_yandex_oauth_token_file is None:
            yandex_offline_blockers.append("missing_yandex_oauth_token_file")
    else:
        yandex_offline_blockers.append("yandex_offline_disabled")

    return ProductAnalyticsProviderReadiness(
        provider_mode=settings.product_analytics_provider_mode,
        posthog=ProviderReadiness(
            "posthog",
            settings.product_analytics_posthog_enabled,
            settings.product_analytics_posthog_enabled and not posthog_blockers,
            tuple(posthog_blockers),
        ),
        yandex_all_pages=ProviderReadiness(
            "yandex_all_pages",
            settings.product_analytics_yandex_all_pages_enabled,
            settings.product_analytics_yandex_all_pages_enabled and not yandex_all_pages_blockers,
            tuple(yandex_all_pages_blockers),
        ),
        yandex_offline=ProviderReadiness(
            "yandex_offline",
            settings.product_analytics_yandex_offline_enabled,
            settings.product_analytics_yandex_offline_enabled and not yandex_offline_blockers,
            tuple(yandex_offline_blockers),
        ),
    )
