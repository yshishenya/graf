"""Fail-closed billing status independent of provider payloads."""

from __future__ import annotations


def billing_readiness_status(*, checkout_enabled: bool, emergency_stop: bool) -> str:
    """Return a bounded, metadata-only status for internal launch diagnostics.

    Billing being disabled must not make the general service health check fail:
    this value is deliberately a small allowlisted state, never a provider
    payload or an operator secret.
    """
    if emergency_stop:
        return "emergency_stop"
    if not checkout_enabled:
        return "disabled"
    return "ready"
