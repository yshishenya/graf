from datetime import UTC, datetime, timedelta
from uuid import UUID

from twobrain_rec_server.billing.referral_rewards import mature_credit
from twobrain_rec_server.billing.referrals import (
    create_referral_token,
    first_payment_reward,
    referral_token_hash,
)


def test_referral_reward_is_discount_plus_bounded_mature_credit() -> None:
    paid_at = datetime(2026, 8, 1, tzinfo=UTC)
    reward = first_payment_reward(paid_at=paid_at, cycle="month")
    assert reward.invitee_discount_percent == 10
    credit = mature_credit(reward=reward, source_ref="payment-1", granted_rolling_days=0, now=paid_at + timedelta(days=15))
    assert credit is not None and credit.days == 7


def test_referral_token_is_opaque_and_stable_for_inviter() -> None:
    user_id = UUID("11111111-1111-1111-1111-111111111111")
    first = create_referral_token(user_id=user_id, secret="a" * 32)
    assert first == create_referral_token(user_id=user_id, secret="a" * 32)
    assert first.startswith("r1_") and len(first) == 67
    assert referral_token_hash(first) != referral_token_hash(
        create_referral_token(user_id=user_id, secret="b" * 32)
    )
