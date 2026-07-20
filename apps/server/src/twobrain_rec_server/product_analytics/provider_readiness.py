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
    metadata: dict[str, str] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "enabled": self.enabled,
            "configured": self.configured,
            "blockers": list(self.blockers),
            "metadata": dict(self.metadata or {}),
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
            {
                "rbac_access_model": "role_based_metadata_only",
                "audit_expectation": "provider_config_access_export_replay_retention_changes",
                "retention_deletion_lifecycle": "documented",
                "dashboard_caveat": "required",
                "deploy_handoff": "dry_run_documented",
                "resource_thresholds": "configured",
                "backup_restore": "documented",
            },
        ),
        yandex_all_pages=ProviderReadiness(
            "yandex_all_pages",
            settings.product_analytics_yandex_all_pages_enabled,
            settings.product_analytics_yandex_all_pages_enabled and not yandex_all_pages_blockers,
            tuple(yandex_all_pages_blockers),
            {
                "counter_strategy": "reuse_093_runtime_only",
                "future_page_default": "blocked",
                "webvisor_maps_forms": "separate_page_class_proof_required",
            },
        ),
        yandex_offline=ProviderReadiness(
            "yandex_offline",
            settings.product_analytics_yandex_offline_enabled,
            settings.product_analytics_yandex_offline_enabled and not yandex_offline_blockers,
            tuple(yandex_offline_blockers),
            {
                "approved_conversions": "desktop_account_connected,first_value_session_completed",
                "identity_values": "redacted_metadata_only",
                "duplicate_protection": "required",
            },
        ),
    )
