from datetime import UTC, datetime, timedelta

from twobrain_rec_server.billing.referral_rewards import mature_credit
from twobrain_rec_server.billing.referrals import first_payment_reward


def test_monthly_and_annual_rewards_mature_once_and_expire() -> None:
    paid_at = datetime(2026, 8, 1, tzinfo=UTC)
    monthly = first_payment_reward(paid_at=paid_at, cycle="month")
    annual = first_payment_reward(paid_at=paid_at, cycle="year")
    assert mature_credit(
        reward=monthly,
        source_ref="referral:payment:month",
        granted_rolling_days=0,
        now=paid_at + timedelta(days=14),
    ).days == 7
    assert mature_credit(
        reward=annual,
        source_ref="referral:payment:year",
        granted_rolling_days=0,
        now=paid_at + timedelta(days=14),
    ).days == 30
    assert mature_credit(
        reward=monthly,
        source_ref="referral:payment:expired",
        granted_rolling_days=0,
        now=monthly.expires_at,
    ) is None
