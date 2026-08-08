from datetime import UTC, datetime

import pytest

from twobrain_rec_server.billing.catalog import (
    ADDON_CAPACITY_BYTES,
    FREE_PROCESSING_SECONDS,
    classify_free_processing,
    classify_storage_threshold,
    storage_capacity_bytes,
)
from twobrain_rec_server.billing.entitlements import effective_plan_code
from twobrain_rec_server.billing.referrals import first_payment_reward, grantable_days
from twobrain_rec_server.billing.refund_email import build_refund_mailto
from twobrain_rec_server.billing.storage import (
    StorageAdmissionError,
    StorageProjection,
    StorageReservation,
    admit_storage,
    commit_object_bytes,
)
from twobrain_rec_server.billing.usage import (
    FreeUsageLedger,
    QuotaOverrun,
    SourceRange,
    moscow_window_for,
)
from twobrain_rec_server.cabinet.web_routes.billing import (
    trial_phase,
    trial_remaining_label,
    trial_surface,
)


def test_catalog_uses_exact_launch_capacities_and_thresholds() -> None:
    assert storage_capacity_bytes("free") == 250_000_000
    assert storage_capacity_bytes("trial") == 500_000_000
    assert storage_capacity_bytes("personal") == 2_000_000_000
    assert all(value > 2_000_000_000 for value in ADDON_CAPACITY_BYTES)
    assert classify_storage_threshold(used_bytes=800, capacity_bytes=1_000) == "80%"
    assert classify_storage_threshold(used_bytes=950, capacity_bytes=1_000) == "95%"
    assert classify_storage_threshold(used_bytes=1_000, capacity_bytes=1_000) == "full"
    assert classify_free_processing(committed_seconds=14_400) == "approaching"
    assert classify_free_processing(committed_seconds=FREE_PROCESSING_SECONDS) == "exhausted"


def test_effective_entitlement_obeys_paid_cutoff() -> None:
    now = datetime(2026, 8, 6, tzinfo=UTC)
    assert effective_plan_code(
        plan_code="personal",
        state="personal",
        now=now,
        paid_through=datetime(2026, 8, 5, tzinfo=UTC),
        trial_ends_at=None,
    ) == "free"
    assert effective_plan_code(
        plan_code="personal",
        state="personal",
        now=now,
        paid_through=datetime(2026, 8, 7, tzinfo=UTC),
        trial_ends_at=None,
    ) == "personal"


def test_trial_surface_exposes_exact_moscow_end_and_expired_state() -> None:
    now = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)
    ends_at = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
    days_left, end_label, expired = trial_surface(
        raw_plan_code="trial",
        effective_plan_code_value="trial",
        trial_ends_at=ends_at,
        now=now,
    )
    assert days_left == 3
    assert end_label == "09.08.2026, 15:00:00 (МСК)"
    assert expired is False

    two_days_and_twenty_three_hours = datetime(2026, 8, 6, 13, 0, tzinfo=UTC)
    days_left, _, _ = trial_surface(
        raw_plan_code="trial",
        effective_plan_code_value="trial",
        trial_ends_at=ends_at,
        now=two_days_and_twenty_three_hours,
    )
    assert days_left == 2
    assert trial_remaining_label(trial_ends_at=ends_at, now=two_days_and_twenty_three_hours) == "2 дн. 23 ч."

    almost_three_days = datetime(2026, 8, 9, 11, 0, tzinfo=UTC)
    assert trial_remaining_label(trial_ends_at=ends_at, now=almost_three_days) == "0 дн. 1 ч."
    assert trial_remaining_label(trial_ends_at=ends_at, now=ends_at) is None

    _, _, expired = trial_surface(
        raw_plan_code="trial",
        effective_plan_code_value="free",
        trial_ends_at=now,
        now=now,
    )
    assert expired is True


def test_trial_phase_keeps_the_last_24_hours_visible() -> None:
    ends_at = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
    assert trial_phase(trial_ends_at=ends_at, now=datetime(2026, 8, 6, 12, 0, tzinfo=UTC)) == "t_minus_3"
    assert trial_phase(trial_ends_at=ends_at, now=datetime(2026, 8, 8, 12, 0, tzinfo=UTC)) == "t_minus_1"
    assert trial_phase(trial_ends_at=ends_at, now=ends_at) is None


def test_free_ledger_deduplicates_ranges_and_keeps_reservation_window() -> None:
    before_midnight = datetime(2026, 8, 31, 20, 59, tzinfo=UTC)
    start, _ = moscow_window_for(before_midnight)
    ledger = FreeUsageLedger.for_moment(before_midnight)
    reservation = ledger.reserve("job-1", 10)
    assert reservation.window_start == start
    ranges = [SourceRange("track", 0, 6), SourceRange("track", 0, 6)]
    assert ledger.commit("job-1", ranges) == 6
    assert ledger.commit("job-1", [SourceRange("track", 6, 10)]) == 4
    assert ledger.committed_seconds == 10


def test_free_ledger_rejects_overrun_without_negative_remaining() -> None:
    ledger = FreeUsageLedger.for_moment(datetime.now(UTC))
    ledger.reserve("job-1", 5)
    with pytest.raises(QuotaOverrun):
        ledger.commit("job-1", [SourceRange("track", 0, 6)])
    assert ledger.committed_seconds == 0
    assert ledger.remaining_seconds == FREE_PROCESSING_SECONDS


def test_free_ledger_does_not_charge_overlapping_source_ranges() -> None:
    ledger = FreeUsageLedger.for_moment(datetime.now(UTC))
    ledger.reserve("job-1", 20)
    assert ledger.commit("job-1", [SourceRange("track", 0, 10)]) == 10
    assert ledger.commit("job-1", [SourceRange("track", 5, 15)]) == 5
    assert ledger.committed_seconds == 15


def test_storage_uses_exact_object_stat_and_rejects_overrun() -> None:
    projection = StorageProjection(used_bytes=100, reserved_bytes=50, capacity_bytes=200)
    admit_storage(projection, 50)
    with pytest.raises(StorageAdmissionError):
        admit_storage(projection, 51)
    reservation = StorageReservation("upload-1", declared_bytes=50)
    assert commit_object_bytes(reservation=reservation, actual_bytes=40) == 40


def test_referral_reward_is_non_cash_and_matures_after_fourteen_days() -> None:
    paid_at = datetime(2026, 8, 1, tzinfo=UTC)
    reward = first_payment_reward(paid_at=paid_at, cycle="year")
    assert reward.invitee_discount_percent == 10
    assert reward.inviter_days == 30
    assert grantable_days(reward=reward, granted_rolling_days=0, now=reward.maturity_at) == 30
    assert grantable_days(reward=reward, granted_rolling_days=180, now=reward.maturity_at) == 0


def test_refund_mailto_contains_only_safe_reference() -> None:
    mailto = build_refund_mailto(
        support_email="billing@example.test",
        safe_invoice_number="INV-123",
    )
    assert mailto.startswith("mailto:billing@example.test?")
    assert "INV-123" in mailto
    assert "card" not in mailto.lower()
    with pytest.raises(ValueError):
        build_refund_mailto(support_email="billing@example.test\nBcc:x", safe_invoice_number="INV-123")
