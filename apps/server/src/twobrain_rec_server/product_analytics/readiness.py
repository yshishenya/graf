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
    rollout_blockers: tuple[str, ...]
    caveats: tuple[str, ...]
    states: dict[str, str]
    approved_page_classes: tuple[str, ...]
    product_rollout_allowed: bool
    campaign_launch_allowed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "blockers": list(self.blockers),
            "rollout_blockers": list(self.rollout_blockers),
            "caveats": list(self.caveats),
            "states": dict(self.states),
            "approved_page_classes": list(self.approved_page_classes),
            "product_rollout_allowed": self.product_rollout_allowed,
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
    if (
        settings.product_analytics_validation_mode == "live_safe"
        and not settings.product_analytics_live_provider_delivery_allowed()
    ):
        blockers.append("live_provider_delivery_not_approved")

    verdict = "infra_smoke_ready" if not blockers else "blocked"
    states = {
        "legal": "approved_for_provider_setup" if settings.product_analytics_legal_approved else "blocked",
        "privacy": _approval_or_separate(settings.product_analytics_privacy_approved),
        "security": _approval_or_separate(settings.product_analytics_security_approved),
        "qa": _approval_or_separate(settings.product_analytics_qa_approved),
        "disclosure": _approval_or_separate(settings.product_analytics_disclosure_approved),
        "dashboard": "metadata_only_ready" if settings.product_analytics_dashboard_ready else "blocked",
        "rbac_audit": "documented" if not provider_readiness.posthog.blockers else "blocked",
        "retention_deletion_lifecycle": "documented",
        "deploy_dry_run": "documented_pending_final_run",
        "provider_smoke": "approved" if settings.product_analytics_provider_smoke_approved else "blocked",
        "rollback": "approved" if settings.product_analytics_rollback_approved else "blocked",
        "live_provider_delivery": (
            "approved" if settings.product_analytics_live_provider_delivery_allowed() else "blocked"
        ),
        "product_rollout": "blocked_not_approved_by_096",
        "campaign_launch": "blocked_not_approved_by_096",
    }
    rollout_blockers = (
        "privacy_separate_approval_required",
        "security_separate_approval_required",
        "qa_separate_approval_required",
        "disclosure_separate_approval_required",
        "product_rollout_separate_approval_required",
        "paid_campaign_launch_blocked_by_096",
    )
    return ProductAnalyticsReadinessReport(
        verdict=verdict,
        blockers=tuple(dict.fromkeys(blockers)),
        rollout_blockers=rollout_blockers,
        caveats=tuple(caveats),
        states=states,
        approved_page_classes=approved_provider_page_classes(),
        product_rollout_allowed=False,
        campaign_launch_allowed=False,
    )


def _approval_or_separate(approved: bool) -> str:
    return "approved" if approved else "separate_rollout_approval_required"
