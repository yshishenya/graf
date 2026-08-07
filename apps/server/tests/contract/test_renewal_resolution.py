from datetime import UTC, datetime, timedelta

import pytest

from twobrain_rec_server.billing.operations import BillingEmergencyStop, require_billing_enabled
from twobrain_rec_server.billing.renewal_resolution import (
    RenewalResolution,
    resolve_renewal_resolution,
)

NOW = datetime(2026, 8, 7, tzinfo=UTC)
CUTOFF = NOW - timedelta(seconds=1)


def test_unknown_at_cutoff_is_free_but_blocks_pay_again() -> None:
    decision = resolve_renewal_resolution(
        now=NOW,
        paid_through=CUTOFF,
        provider_status="unknown",
    )
    assert decision.resolution is RenewalResolution.UNKNOWN_PENDING
    assert decision.plan_code == "free"
    assert decision.manual_resume_allowed is False


def test_key_expiry_allows_manual_resume_without_automatic_retry() -> None:
    decision = resolve_renewal_resolution(
        now=NOW,
        paid_through=CUTOFF,
        provider_status="unknown",
        provider_key_expired=True,
    )
    assert decision.resolution is RenewalResolution.MANUAL_RESUME_REQUIRED
    assert decision.manual_resume_allowed is True


def test_late_success_after_refusal_stays_free_and_requires_incident() -> None:
    decision = resolve_renewal_resolution(
        now=NOW,
        paid_through=CUTOFF,
        provider_status="succeeded",
        effective_refusal=True,
    )
    assert decision.resolution is RenewalResolution.LATE_SUCCESS_REFUSED
    assert decision.plan_code == "free"
    assert decision.incident_required is True
    assert decision.support_notice_required is True


def test_late_success_without_refusal_restores_paid_access_once() -> None:
    decision = resolve_renewal_resolution(
        now=NOW,
        paid_through=CUTOFF,
        provider_status="succeeded",
    )
    assert decision.resolution is RenewalResolution.LATE_SUCCESS_RESTORED
    assert decision.plan_code == "personal"


def test_emergency_stop_blocks_renewal_mutation() -> None:
    with pytest.raises(BillingEmergencyStop):
        require_billing_enabled(checkout_enabled=True, emergency_stop=True)
