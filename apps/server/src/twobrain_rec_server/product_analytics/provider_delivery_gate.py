"""Shared fail-closed gate for live analytics provider delivery.

The gate is deliberately metadata-only.  It reads settings and the local
readiness evidence files, but never contacts or mutates an analytics provider.
Both provider clients and the catalog use this resolver so a launch decision
cannot drift from the readiness report.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.access_governance import (
    access_governance_blockers,
    read_access_governance_state,
)
from twobrain_rec_server.product_analytics.approvals import (
    LaunchApprovalGate,
    build_launch_approval_gate,
)
from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
    BasisWithdrawalRegister,
    LevelLegalBasis,
    measurement_level_basis_states,
    read_basis_withdrawal_register,
    withdrawn_level_keys,
)
from twobrain_rec_server.product_analytics.provider_readiness import (
    ProductAnalyticsProviderReadiness,
    build_provider_readiness,
    operations_block_claim,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from twobrain_rec_server.product_analytics.provider_config import (
        ProductAnalyticsProviderConfig,
    )


BLOCKER_PROVIDER_BASIS_NOT_CONFIRMED = "provider_analytics_basis_not_confirmed"
BLOCKER_PROVIDER_DELIVERY_NOT_APPROVED = "live_provider_delivery_not_approved"
BLOCKER_PROVIDER_NOT_READY = "posthog_not_ready"
BLOCKER_YANDEX_ALL_PAGES_NOT_READY = "yandex_all_pages_not_ready"
BLOCKER_YANDEX_OFFLINE_NOT_READY = "yandex_offline_not_ready"
BLOCKER_OPERATIONS_NOT_READY = "analytics_operations_not_ready"
BLOCKER_ACCESS_NOT_READY = "analytics_access_governance_not_ready"
BLOCKER_LEGAL_BASIS_WITHDRAWN = "legal_basis_withdrawn"


@dataclass(frozen=True, slots=True)
class ProviderDeliveryGate:
    """A redacted, immutable decision for one provider delivery path."""

    provider: str
    level_key: str
    allowed: bool
    campaign_launch_allowed: bool
    blockers: tuple[str, ...]
    readiness_blockers: tuple[str, ...]
    approval_gate: LaunchApprovalGate
    basis_states: tuple[LevelLegalBasis, ...]
    withdrawals: BasisWithdrawalRegister
    access_blockers: tuple[str, ...]
    operations_blockers: tuple[str, ...]

    @property
    def basis_state(self) -> str:
        for state in self.basis_states:
            if state.level_key == self.level_key:
                return state.state
        return "missing"

    def as_dict(self) -> dict[str, Any]:
        """Return metadata only; approval and state-file paths never leak."""

        return {
            "provider": self.provider,
            "level_key": self.level_key,
            "allowed": self.allowed,
            "campaign_launch_allowed": self.campaign_launch_allowed,
            "blockers": list(self.blockers),
            "readiness_blockers": list(self.readiness_blockers),
            "basis_state": self.basis_state,
            "access_blockers": list(self.access_blockers),
            "operations_blockers": list(self.operations_blockers),
            "approval_gate": self.approval_gate.as_dict(),
        }


def resolve_provider_delivery_gate(
    settings: Settings,
    *,
    provider: str = "campaign",
    environ: Mapping[str, str] | None = None,
    now: float | None = None,
    config: ProductAnalyticsProviderConfig | None = None,
    provider_readiness: ProductAnalyticsProviderReadiness | None = None,
) -> ProviderDeliveryGate:
    """Resolve the common fail-closed gate without contacting a provider.

    ``provider="campaign"`` is the global catalog/readiness decision.  A
    provider-specific value additionally requires that provider's configuration
    while retaining the same access, operations, legal-basis and approval gates.
    """

    environment = os.environ if environ is None else environ
    if config is None:
        # Import locally to avoid provider_config -> gate -> provider_config at
        # module import time.  ``resolve_campaign=False`` prevents recursion.
        from twobrain_rec_server.product_analytics.provider_config import (
            ProductAnalyticsProviderConfig,
        )

        config = ProductAnalyticsProviderConfig.from_settings(
            settings,
            environ=environment,
            resolve_campaign=False,
        )

    readiness = provider_readiness or build_provider_readiness(
        settings,
        environ=environment,
        now=now,
    )
    withdrawals = read_basis_withdrawal_register(environment)
    basis_states = measurement_level_basis_states(config, withdrawals=withdrawals)

    blockers: list[str] = []
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
    if settings.product_analytics_validation_mode != "live_safe":
        blockers.append(BLOCKER_PROVIDER_DELIVERY_NOT_APPROVED)
    if not settings.product_analytics_live_provider_delivery_allowed():
        blockers.append(BLOCKER_PROVIDER_DELIVERY_NOT_APPROVED)

    blockers.extend(_provider_blockers(readiness, settings, provider))

    operations_gate = operations_block_claim(settings)
    operations_blockers = tuple(readiness.analytics_operations.blockers)
    if operations_gate and operations_blockers:
        blockers.append(BLOCKER_OPERATIONS_NOT_READY)

    access_evidence = read_access_governance_state(environment)
    access_blockers = access_governance_blockers(
        access_evidence,
        environ=environment,
        now=int(now) if now is not None else None,
    )
    if operations_gate and access_blockers:
        blockers.append(BLOCKER_ACCESS_NOT_READY)

    level_key = _provider_level(provider)
    withdrawn = set(withdrawn_level_keys(basis_states))
    if withdrawals.file_errors or (
        provider == "campaign" and withdrawn
    ) or (
        provider != "campaign" and level_key in withdrawn
    ):
        blockers.append(BLOCKER_LEGAL_BASIS_WITHDRAWN)
    if provider in {"posthog", "yandex", "yandex_offline", "yandex_all_pages"} and not _basis_processing_allowed(
        basis_states,
        level_key=level_key,
    ):
        blockers.append(BLOCKER_PROVIDER_BASIS_NOT_CONFIRMED)

    readiness_blockers = tuple(dict.fromkeys(blockers))
    approval_gate = build_launch_approval_gate(
        readiness_blockers,
        environ=environment,
    )
    all_blockers = tuple(
        dict.fromkeys(
            (
                *readiness_blockers,
                *approval_gate.blockers,
                *approval_gate.configuration_blockers,
            )
        )
    )
    campaign_allowed = approval_gate.campaign_launch_allowed
    return ProviderDeliveryGate(
        provider=provider,
        level_key=level_key,
        allowed=campaign_allowed and not all_blockers,
        campaign_launch_allowed=campaign_allowed,
        blockers=all_blockers,
        readiness_blockers=readiness_blockers,
        approval_gate=approval_gate,
        basis_states=basis_states,
        withdrawals=withdrawals,
        access_blockers=tuple(access_blockers),
        operations_blockers=operations_blockers,
    )


def _provider_level(provider: str) -> str:
    if provider in {"posthog", "yandex", "yandex_offline", "yandex_all_pages", "campaign"}:
        return "provider_analytics"
    return "__unknown__"


def _provider_blockers(
    readiness: ProductAnalyticsProviderReadiness,
    settings: Settings,
    provider: str,
) -> tuple[str, ...]:
    if provider == "posthog":
        return (
            ("posthog_disabled",)
            if not settings.product_analytics_posthog_enabled
            else tuple(readiness.posthog.blockers)
        )
    if provider in {"yandex", "yandex_offline"}:
        return (
            ("yandex_offline_disabled",)
            if not settings.product_analytics_yandex_offline_enabled
            else tuple(readiness.yandex_offline.blockers)
        )
    if provider == "yandex_all_pages":
        return (
            ("yandex_all_pages_disabled",)
            if not settings.product_analytics_yandex_all_pages_enabled
            else tuple(readiness.yandex_all_pages.blockers)
        )

    # The campaign gate covers whichever provider path is configured.  Do not
    # turn an intentionally disabled secondary provider into a false blocker.
    selected: list[str] = []
    if settings.product_analytics_posthog_enabled:
        selected.extend(readiness.posthog.blockers)
    if settings.product_analytics_yandex_all_pages_enabled:
        selected.extend(readiness.yandex_all_pages.blockers)
    if settings.product_analytics_yandex_offline_enabled:
        selected.extend(readiness.yandex_offline.blockers)
    if not selected:
        selected.append("provider_disabled")
    return tuple(selected)


def _basis_processing_allowed(states: tuple[LevelLegalBasis, ...], *, level_key: str) -> bool:
    return any(state.level_key == level_key and state.processing_allowed for state in states)


__all__ = [
    "BLOCKER_ACCESS_NOT_READY",
    "BLOCKER_LEGAL_BASIS_WITHDRAWN",
    "BLOCKER_OPERATIONS_NOT_READY",
    "BLOCKER_PROVIDER_BASIS_NOT_CONFIRMED",
    "BLOCKER_PROVIDER_DELIVERY_NOT_APPROVED",
    "BLOCKER_PROVIDER_NOT_READY",
    "BLOCKER_YANDEX_ALL_PAGES_NOT_READY",
    "BLOCKER_YANDEX_OFFLINE_NOT_READY",
    "ProviderDeliveryGate",
    "resolve_provider_delivery_gate",
]
