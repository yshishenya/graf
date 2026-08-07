"""Fail-closed billing launch checks independent of provider payloads."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BillingReadiness:
    provider_mutations_allowed: bool
    blocked_reasons: tuple[str, ...]


def evaluate_billing_readiness(
    *,
    checkout_enabled: bool,
    emergency_stop: bool,
    required_evidence: Mapping[str, bool] | None = None,
) -> BillingReadiness:
    """Require every named launch gate before checkout/binding/renewal mutations."""
    blocked: list[str] = []
    if not checkout_enabled:
        blocked.append("checkout_disabled")
    if emergency_stop:
        blocked.append("emergency_stop")
    for name, passed in sorted((required_evidence or {}).items()):
        if not isinstance(name, str) or not name or not isinstance(passed, bool):
            raise ValueError("billing readiness evidence must be named booleans")
        if not passed:
            blocked.append(f"evidence_missing:{name}")
    return BillingReadiness(not blocked, tuple(blocked))
