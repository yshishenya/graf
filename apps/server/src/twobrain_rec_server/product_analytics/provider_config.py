from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.approvals import build_launch_approval_gate
from twobrain_rec_server.product_analytics.provider_secrets import redact_provider_value
from twobrain_rec_server.product_analytics.retention import retention_rule


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


# The three measurement levels of feature 273 in the order a reviewer reads
# them: the cheapest and most anonymous first, the one that needs consent last.
MEASUREMENT_LEVEL_KEYS = (
    "anonymous_aggregate",
    "attribution_profiles",
    "provider_analytics",
)

# Each level stores data under exactly one registered retention category, so the
# term and the storage of a level cannot drift away from the retention rules
# (FR-036, FR-050).
ANONYMOUS_AGGREGATE_RETENTION_CATEGORY = "anonymous_page_aggregate"
ATTRIBUTION_PROFILES_RETENTION_CATEGORY = "client_acquisition_attribute"
PROVIDER_ANALYTICS_RETENTION_CATEGORY = "posthog_product_events"


@dataclass(frozen=True, slots=True)
class MeasurementLevel:
    """One of the three measurement levels of feature 273 (FR-001, FR-002).

    ``enabled`` is computed from configuration only. ``identifiers_allowed``,
    ``requires_consent`` and ``provider_delivery`` describe what the level does
    by design, so a reviewer can read the privacy cost of a level even while it
    is switched off.
    """

    level: int
    key: str
    title: str
    enabled: bool
    identifiers_allowed: bool
    requires_consent: bool
    provider_delivery: bool
    legal_basis: str
    storage: str
    retention_days: int
    blocked_reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "key": self.key,
            "title": self.title,
            "enabled": self.enabled,
            "identifiers_allowed": self.identifiers_allowed,
            "requires_consent": self.requires_consent,
            "provider_delivery": self.provider_delivery,
            "legal_basis": self.legal_basis,
            "storage": self.storage,
            "retention_days": self.retention_days,
            "blocked_reasons": list(self.blocked_reasons),
        }


def build_measurement_levels(
    settings: Settings,
    *,
    posthog: PostHogProviderConfig,
    yandex: YandexProviderConfig,
    live_provider_delivery_allowed: bool,
    environ: Mapping[str, str] | None = None,
) -> tuple[MeasurementLevel, ...]:
    """Describe the three measurement levels, all of them off by default.

    Fail closed at every level: a level is enabled only when every one of its
    conditions holds, and every condition that does not hold is named in
    ``blocked_reasons``. Level 3 additionally reads the recorded launch
    approvals, because FR-044 forbids a technical flag from granting provider
    measurement on its own — the flag can only withhold the permission.
    """

    aggregate_rule = retention_rule(ANONYMOUS_AGGREGATE_RETENTION_CATEGORY)
    attribution_rule = retention_rule(ATTRIBUTION_PROFILES_RETENTION_CATEGORY)
    provider_rule = retention_rule(PROVIDER_ANALYTICS_RETENTION_CATEGORY)

    level_one_reasons: tuple[str, ...] = (
        () if settings.product_analytics_anonymous_aggregate_enabled else ("flag_disabled",)
    )
    level_two_reasons: tuple[str, ...] = (
        () if settings.product_analytics_enabled else ("flag_disabled",)
    )

    level_three_reasons: list[str] = []
    if not settings.product_analytics_enabled:
        level_three_reasons.append("flag_disabled")
    if not (posthog.enabled or yandex.all_pages_enabled or yandex.offline_enabled):
        level_three_reasons.append("provider_disabled")
    if not live_provider_delivery_allowed:
        level_three_reasons.append("live_provider_delivery_not_allowed")
    configuration_approvals = (
        ("legal", settings.product_analytics_legal_approved),
        ("privacy", settings.product_analytics_privacy_approved),
        ("security", settings.product_analytics_security_approved),
        ("disclosure", settings.product_analytics_disclosure_approved),
    )
    for approval, approved in configuration_approvals:
        if not approved:
            level_three_reasons.append(f"{approval}_not_approved")
    level_three_reasons.extend(
        build_launch_approval_gate(
            tuple(level_three_reasons),
            environ=environ,
        ).blockers
    )

    return (
        MeasurementLevel(
            level=1,
            key="anonymous_aggregate",
            title="Анонимный агрегат публичных страниц",
            enabled=not level_one_reasons,
            identifiers_allowed=False,
            requires_consent=False,
            provider_delivery=False,
            legal_basis=(
                "no personal data: the level stores coarse page dimensions and visit "
                "counters of a public page, with no identifier of the visitor"
            ),
            storage=aggregate_rule.storage,
            retention_days=aggregate_rule.enforced_retention_days(),
            blocked_reasons=level_one_reasons,
        ),
        MeasurementLevel(
            level=2,
            key="attribution_profiles",
            title="Профили привлечения на своей стороне",
            enabled=not level_two_reasons,
            identifiers_allowed=True,
            requires_consent=False,
            provider_delivery=False,
            legal_basis=(
                "contract performance and legitimate interest: the campaign label of a "
                "client record stays pseudonymous and inside GRAF-owned storage"
            ),
            storage=attribution_rule.storage,
            retention_days=attribution_rule.enforced_retention_days(),
            blocked_reasons=level_two_reasons,
        ),
        MeasurementLevel(
            level=3,
            key="provider_analytics",
            title="Измерение через внешние счётчики",
            enabled=not level_three_reasons,
            identifiers_allowed=True,
            requires_consent=True,
            provider_delivery=True,
            legal_basis=(
                "consent of the visitor: a provider counter receives personal data only "
                "after an explicit opt-in on the public page"
            ),
            storage=provider_rule.storage,
            retention_days=provider_rule.enforced_retention_days(),
            blocked_reasons=tuple(level_three_reasons),
        ),
    )


@dataclass(frozen=True, slots=True)
class ProductAnalyticsProviderConfig:
    enabled: bool
    validation_mode: str
    provider_mode: str
    rollback_mode: str
    posthog: PostHogProviderConfig
    yandex: YandexProviderConfig
    live_provider_delivery_allowed: bool
    # Provider-setup flags, not approval records. They describe what an operator
    # switched on; they cannot grant the launch permission, and the launch gate
    # below is the only thing that can.
    configuration_flags: dict[str, str]
    campaign_launch_allowed: bool
    # Always filled by `from_settings`, which is the only place that knows the
    # settings and the approval register. The default keeps an externally built
    # instance from claiming levels it did not compute.
    measurement_levels: tuple[MeasurementLevel, ...] = ()

    def measurement_level(self, key: str) -> MeasurementLevel | None:
        """Return one level by key, or ``None`` for an unknown level."""
        for level in self.measurement_levels:
            if level.key == key:
                return level
        return None

    def enabled_measurement_levels(self) -> tuple[MeasurementLevel, ...]:
        return tuple(level for level in self.measurement_levels if level.enabled)

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        environ: Mapping[str, str] | None = None,
        resolve_campaign: bool = True,
    ) -> ProductAnalyticsProviderConfig:
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
        live_provider_delivery_allowed = settings.product_analytics_live_provider_delivery_allowed()
        instance = cls(
            enabled=settings.product_analytics_enabled,
            validation_mode=settings.product_analytics_validation_mode,
            provider_mode=settings.product_analytics_provider_mode,
            rollback_mode=settings.product_analytics_rollback_mode,
            posthog=posthog,
            yandex=yandex,
            live_provider_delivery_allowed=live_provider_delivery_allowed,
            configuration_flags={
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
            measurement_levels=build_measurement_levels(
                settings,
                posthog=posthog,
                yandex=yandex,
                live_provider_delivery_allowed=live_provider_delivery_allowed,
                environ=environ,
            ),
        )
        if not resolve_campaign:
            return instance
        # The catalog must use the exact same resolver as readiness.  Passing
        # this already-built instance avoids a provider_config -> gate cycle.
        from twobrain_rec_server.product_analytics.provider_delivery_gate import (
            resolve_provider_delivery_gate,
        )

        gate = resolve_provider_delivery_gate(
            settings,
            provider="campaign",
            environ=environ,
            config=instance,
        )
        return replace(instance, campaign_launch_allowed=gate.campaign_launch_allowed)

    def as_redacted_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "validation_mode": self.validation_mode,
            "provider_mode": self.provider_mode,
            "rollback_mode": self.rollback_mode,
            "posthog": self.posthog.as_redacted_dict(),
            "yandex": self.yandex.as_redacted_dict(),
            "live_provider_delivery_allowed": self.live_provider_delivery_allowed,
            "configuration_flags": dict(self.configuration_flags),
            "campaign_launch_allowed": self.campaign_launch_allowed,
            "measurement_levels": [level.as_dict() for level in self.measurement_levels],
        }


def _approval_state(approved: bool) -> str:
    return "approved" if approved else "blocked"
