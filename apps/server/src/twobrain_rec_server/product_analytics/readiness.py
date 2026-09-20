from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.advertising_transfer import (
    RECIPIENT_YANDEX_METRICA,
    TRANSFER_PURPOSE_OFFLINE_CONVERSIONS,
    read_advertising_transfer_register,
)
from twobrain_rec_server.product_analytics.approvals import (
    APPROVAL_STATE_RECORDED,
    LaunchApprovalGate,
    build_launch_approval_gate,
)
from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
    measurement_level_basis_states,
    read_basis_withdrawal_register,
    withdrawn_level_keys,
)
from twobrain_rec_server.product_analytics.page_inventory import approved_provider_page_classes
from twobrain_rec_server.product_analytics.provider_config import ProductAnalyticsProviderConfig
from twobrain_rec_server.product_analytics.provider_readiness import (
    ProductAnalyticsProviderReadiness,
    build_provider_readiness,
    operations_block_claim,
)

# FR-048: a level whose legal basis was withdrawn stops processing, so the
# readiness claim is blocked and the level is named in the report.
BLOCKER_LEGAL_BASIS_WITHDRAWN = "legal_basis_withdrawn"


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
    approval_gate: dict[str, Any]

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
            "approval_gate": dict(self.approval_gate),
        }


def build_rollout_readiness_report(
    settings: Settings,
    *,
    environ: Mapping[str, str] | None = None,
) -> ProductAnalyticsReadinessReport:
    blockers: list[str] = []
    caveats: list[str] = [
        "internal/support/smoke/test traffic is counted by default",
        "public 093 scope remains limited to / and /download until rollout",
        "provider-held aggregates and exported reports may remain outside direct GRAF erasure control",
        (
            "launch approvals live outside the repository, in a metadata-only state file; "
            "the repository holds the roles and the format, never the values"
        ),
        (
            "an offline-conversion transfer needs a recorded basis and a disclosure the "
            "visitor can read; the site copy must name the transfer before it may happen"
        ),
    ]
    # The approval register is read from the environment, so a caller that wants
    # to answer "what would this configuration be allowed to do" has to say
    # which environment it means instead of inheriting the process one.
    environment = os.environ if environ is None else environ

    provider_readiness = build_provider_readiness(settings, environ=environment)
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
    # Operations evidence (backup, restore, retention) is reported under its own
    # label. Folding it into `posthog_not_ready` would blame a provider
    # configuration problem that does not exist, and would make the real reason
    # impossible to act on. The label blocks the verdict only when the
    # configuration actually claims live delivery; a smoke lane stays usable.
    operations_blockers = provider_readiness.analytics_operations.blockers
    operations_gate_the_claim = operations_block_claim(settings)
    if operations_blockers and operations_gate_the_claim:
        blockers.append("analytics_operations_not_ready")
    if _provider_configuration_blockers(provider_readiness):
        blockers.append("posthog_not_ready")
    access_blockers = provider_readiness.posthog.metadata.get("access_governance", {}).get("blockers", [])
    # Access governance is a separate live-claim gate. A smoke lane may report
    # missing metadata without pretending that a provider account is approved.
    if access_blockers and operations_gate_the_claim:
        blockers.append("analytics_access_governance_not_ready")
    if settings.product_analytics_yandex_all_pages_enabled and provider_readiness.yandex_all_pages.blockers:
        blockers.append("yandex_all_pages_not_ready")
    if settings.product_analytics_yandex_offline_enabled and provider_readiness.yandex_offline.blockers:
        blockers.append("yandex_offline_not_ready")
    if (
        settings.product_analytics_validation_mode == "live_safe"
        and not settings.product_analytics_live_provider_delivery_allowed()
    ):
        blockers.append("live_provider_delivery_not_approved")

    # FR-048: a withdrawn legal basis stops the level, so it also stops the
    # readiness claim. The register only ever adds a lost basis; an absent file
    # leaves the level states computed from configuration.
    withdrawal_register = read_basis_withdrawal_register(environment)
    basis_states = measurement_level_basis_states(
        ProductAnalyticsProviderConfig.from_settings(settings, environ=environment),
        withdrawals=withdrawal_register,
    )
    withdrawn_levels = withdrawn_level_keys(basis_states)
    if withdrawn_levels or withdrawal_register.file_errors:
        blockers.append(BLOCKER_LEGAL_BASIS_WITHDRAWN)

    # FR-028/FR-049: the advertising transfer needs a recorded basis, and the
    # report says so rather than letting a flag imply it.
    transfer_register = read_advertising_transfer_register(environment)
    transfer_basis = transfer_register.basis(
        purpose=TRANSFER_PURPOSE_OFFLINE_CONVERSIONS,
        recipient=RECIPIENT_YANDEX_METRICA,
    )

    # The record gate is computed from the same blocker set the report already
    # publishes, so a technical gap and a missing approval cannot disagree.
    readiness_blockers = tuple(dict.fromkeys(blockers))
    approval_gate = build_launch_approval_gate(readiness_blockers, environ=environment)

    verdict = "infra_smoke_ready" if not blockers else "blocked"
    states = {
        "legal": "approved_for_provider_setup" if settings.product_analytics_legal_approved else "blocked",
        "privacy": _approval_or_separate(settings.product_analytics_privacy_approved),
        "security": _approval_or_separate(settings.product_analytics_security_approved),
        "qa": _approval_or_separate(settings.product_analytics_qa_approved),
        "disclosure": _approval_or_separate(settings.product_analytics_disclosure_approved),
        "dashboard": "metadata_only_ready" if settings.product_analytics_dashboard_ready else "blocked",
        # Access control is a separate metadata-only gate. It is descriptive
        # in smoke/non-live lanes, but fail-closed when live delivery is claimed.
        "rbac_audit": (
            "metadata_verified"
            if not access_blockers
            else ("documented" if not operations_gate_the_claim else "blocked")
        ),
        "retention_deletion_lifecycle": _retention_lifecycle_state(
            operations_blockers, claim_gated=operations_gate_the_claim
        ),
        "deploy_dry_run": "documented_pending_final_run",
        "provider_smoke": "approved" if settings.product_analytics_provider_smoke_approved else "blocked",
        "rollback": "approved" if settings.product_analytics_rollback_approved else "blocked",
        "live_provider_delivery": (
            "approved" if settings.product_analytics_live_provider_delivery_allowed() else "blocked"
        ),
        "campaign_readiness": "blocked_operator_confirmation_required",
        "legal_basis_lifecycle": _legal_basis_lifecycle_state(withdrawn_levels),
        **{f"legal_basis_{basis.level_key}": basis.state for basis in basis_states},
        "advertising_transfer": (
            "basis_recorded" if transfer_basis is not None and transfer_basis.recorded()
            else "blocked_no_recorded_basis"
        ),
        # Advertising distributed through telecommunication networks is not
        # implemented, and it stays blocked until a subscriber gives prior
        # consent for it (FR-029). The gate that enforces this lives in
        # `advertising_transfer`; the state only publishes the condition.
        "telecom_advertising": "blocked_subscriber_prior_consent_required",
        "product_rollout": _rollout_state(approval_gate),
        "campaign_launch": _launch_state(approval_gate),
        **{f"approval_{kind}": state for kind, state in approval_gate.states.items()},
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
        blockers=readiness_blockers,
        rollout_blockers=rollout_blockers,
        caveats=tuple(caveats),
        states=states,
        approved_page_classes=approved_provider_page_classes(),
        product_rollout_allowed=approval_gate.campaign_launch_allowed,
        campaign_launch_allowed=approval_gate.campaign_launch_allowed,
        approval_gate=approval_gate.as_dict(),
    )


# Operations evidence gaps that say "the retention lifecycle was not proven".
RETENTION_BLOCKER_PREFIXES = (
    "retention_",
    "backup_",
    "restore_",
)


def _provider_configuration_blockers(
    provider_readiness: ProductAnalyticsProviderReadiness,
) -> tuple[str, ...]:
    """Provider setup gaps, excluding the operations evidence reported separately."""

    return tuple(
        blocker
        for blocker in provider_readiness.posthog.blockers
        if not blocker.startswith(RETENTION_BLOCKER_PREFIXES)
    )


def _retention_lifecycle_state(
    operations_blockers: tuple[str, ...],
    *,
    claim_gated: bool,
) -> str:
    """The lifecycle is contradicted only when the configuration claims live delivery.

    A dry-run or smoke configuration already says it does not claim live
    analytics, so missing operations evidence is expected there and must not be
    reported as a broken lifecycle. Once live delivery is claimed, the same
    evidence becomes part of the claim and a gap is reported as `blocked`.
    """

    if not claim_gated:
        return "documented"
    if any(blocker.startswith(RETENTION_BLOCKER_PREFIXES) for blocker in operations_blockers):
        return "blocked"
    return "enforced_and_verified"


def _rollout_state(gate: LaunchApprovalGate) -> str:
    return "allowed_by_records" if gate.campaign_launch_allowed else "blocked_by_records"


def _legal_basis_lifecycle_state(withdrawn_levels: tuple[str, ...]) -> str:
    """Name what happened to the legal basis of the levels (FR-048).

    A recorded withdrawal means data already collected lost its basis, so the
    state says both halves: processing stopped, and erasure is owed.
    """

    if withdrawn_levels:
        return "processing_stopped_erasure_required:" + ",".join(withdrawn_levels)
    return "no_recorded_withdrawal"


def _launch_state(gate: LaunchApprovalGate) -> str:
    """The launch state names the missing release decision, not just 'blocked'."""

    if gate.campaign_launch_allowed:
        return "allowed_by_records"
    release_check = gate.register.approval("check")
    if release_check is not None and release_check.state != APPROVAL_STATE_RECORDED:
        return "blocked_pending_launch_approval_record"
    return "blocked_by_records"


def _approval_or_separate(approved: bool) -> str:
    return "approved" if approved else "separate_rollout_approval_required"
