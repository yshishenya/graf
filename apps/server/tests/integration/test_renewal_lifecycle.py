from datetime import UTC, datetime, timedelta

from twobrain_rec_server.billing.renewal import renewal_due
from twobrain_rec_server.billing.renewal_resolution import (
    RenewalResolution,
    resolve_renewal_resolution,
)


def test_renewal_reminder_and_cutoff_have_no_grace_window() -> None:
    paid_through = datetime(2026, 8, 10, tzinfo=UTC)
    assert renewal_due(
        now=paid_through - timedelta(hours=72),
        paid_through=paid_through,
    )
    decision = resolve_renewal_resolution(
        now=paid_through,
        paid_through=paid_through,
        provider_status="declined",
    )
    assert decision.resolution is RenewalResolution.MANUAL_RESUME_REQUIRED
    assert decision.plan_code == "free"


def test_active_term_is_not_downgraded_by_pending_provider_result() -> None:
    paid_through = datetime(2026, 8, 10, tzinfo=UTC)
    decision = resolve_renewal_resolution(
        now=paid_through - timedelta(seconds=1),
        paid_through=paid_through,
        provider_status="unknown",
    )
    assert decision.resolution is RenewalResolution.ACTIVE
    assert decision.plan_code == "personal"
