from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.page_inventory import approved_provider_page_classes
from twobrain_rec_server.product_analytics.provider_readiness import build_provider_readiness


@dataclass(frozen=True, slots=True)
class ProductAnalyticsReadinessReport:
    verdict: str
    blockers: tuple[str, ...]
    caveats: tuple[str, ...]
    approved_page_classes: tuple[str, ...]
    campaign_launch_allowed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "blockers": list(self.blockers),
            "caveats": list(self.caveats),
            "approved_page_classes": list(self.approved_page_classes),
            "campaign_launch_allowed": self.campaign_launch_allowed,
        }


def build_rollout_readiness_report(settings: Settings) -> ProductAnalyticsReadinessReport:
    blockers: list[str] = []
    caveats: list[str] = [
        "internal/support/smoke/test traffic is counted by default",
        "public 093 scope remains limited to / and /download until rollout",
        "provider-held aggregates and exported reports may remain outside direct GRAF erasure control",
    ]

    provider_readiness = build_provider_readiness(settings)
    if not settings.product_analytics_enabled:
        blockers.append("product_analytics_disabled")
    if settings.product_analytics_validation_mode == "disabled":
        blockers.append("validation_mode_disabled")
    if not settings.product_analytics_legal_approved:
        blockers.append("legal_not_approved")
    if not settings.product_analytics_dashboard_ready:
        blockers.append("dashboard_not_ready")
    if not settings.product_analytics_provider_smoke_approved:
        blockers.append("provider_smoke_not_approved")
    if provider_readiness.posthog.blockers:
        blockers.append("posthog_not_ready")
    if settings.product_analytics_yandex_all_pages_enabled and provider_readiness.yandex_all_pages.blockers:
        blockers.append("yandex_all_pages_not_ready")
    if settings.product_analytics_yandex_offline_enabled and provider_readiness.yandex_offline.blockers:
        blockers.append("yandex_offline_not_ready")

    verdict = "infra_smoke_ready" if not blockers else "blocked"
    return ProductAnalyticsReadinessReport(
        verdict=verdict,
        blockers=tuple(dict.fromkeys(blockers)),
        caveats=tuple(caveats),
        approved_page_classes=approved_provider_page_classes(),
        campaign_launch_allowed=bool(verdict == "infra_smoke_ready" and settings.product_analytics_campaign_readiness_approved),
    )
