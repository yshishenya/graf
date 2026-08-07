import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from twobrain_rec_server.billing.referral_rewards import mature_credit, payment_source_ref
from twobrain_rec_server.billing.referrals import (
    create_referral_token,
    first_payment_reward,
    referral_token_hash,
)
from twobrain_rec_server.cabinet.web_routes.auth_email_flow import _bind_referral_attribution


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


def test_first_touch_binding_is_single_use_and_masks_no_identity() -> None:
    class FakeDb:
        def __init__(self, attribution) -> None:
            self.attribution = attribution

        async def scalar(self, _query):
            return self.attribution

    inviter = UUID("11111111-1111-1111-1111-111111111111")
    invitee = UUID("22222222-2222-2222-2222-222222222222")
    attribution = type(
        "Attribution",
        (),
        {
            "inviter_user_id": inviter,
            "invitee_user_id": None,
            "state": "issued",
            "bound_at": None,
        },
    )()
    token = create_referral_token(user_id=inviter, secret="a" * 32)

    bound = asyncio.run(
        _bind_referral_attribution(
            FakeDb(attribution),
            workspace_id=UUID("33333333-3333-3333-3333-333333333333"),
            user_id=invitee,
            token=token,
            now=datetime(2026, 8, 7, tzinfo=UTC),
        )
    )

    assert bound is True
    assert attribution.invitee_user_id == invitee
    assert attribution.state == "bound"
    assert attribution.bound_at == datetime(2026, 8, 7, tzinfo=UTC)


def test_annual_credit_waits_for_maturity_and_cap_is_bounded() -> None:
    paid_at = datetime(2026, 8, 1, tzinfo=UTC)
    reward = first_payment_reward(paid_at=paid_at, cycle="year")
    assert mature_credit(
        reward=reward,
        source_ref=payment_source_ref("pay-1"),
        granted_rolling_days=179,
        now=paid_at + timedelta(days=15),
    ).days == 1
    assert mature_credit(
        reward=reward,
        source_ref=payment_source_ref("pay-2"),
        granted_rolling_days=180,
        now=paid_at + timedelta(days=15),
    ) is None
    assert mature_credit(
        reward=reward,
        source_ref=payment_source_ref("pay-3"),
        granted_rolling_days=0,
        now=paid_at + timedelta(days=13),
    ) is None
    with pytest.raises(ValueError):
        payment_source_ref("provider id with spaces")
