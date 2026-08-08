from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

REFERRER_CAP_DAYS = 180
MATURITY_DAYS = 14
REFERRAL_TOKEN_MAX_AGE_DAYS = 30


@dataclass(frozen=True, slots=True)
class ReferralRiskSignals:
    """Non-decisive abuse signals; raw identity/network values never persist."""

    same_device: bool = False
    same_payment_profile: bool = False
    same_email_domain: bool = False
    same_ip: bool = False
    velocity_count: int = 0

    def __post_init__(self) -> None:
        if self.velocity_count < 0:
            raise ValueError("referral velocity cannot be negative")


def classify_referral_risk(signals: ReferralRiskSignals) -> str:
    """Return a bounded review signal, never an automatic entitlement denial."""
    matches = sum(
        (
            signals.same_device,
            signals.same_payment_profile,
            signals.same_email_domain,
            signals.same_ip,
        )
    )
    return "review" if matches >= 2 or signals.velocity_count >= 5 else "none"


@dataclass(frozen=True, slots=True)
class ReferralReward:
    invitee_discount_percent: int
    inviter_days: int
    maturity_at: datetime
    expires_at: datetime


def create_referral_token(*, user_id: UUID, secret: str) -> str:
    """Create an opaque, non-guessable first-touch token bound to the inviter."""
    signature = hmac.new(secret.encode(), str(user_id).encode(), sha256).hexdigest()
    return f"r1_{signature}"


def referral_token_hash(token: str) -> str:
    normalized = token.strip()
    if not normalized or len(normalized) > 240:
        raise ValueError("referral token is invalid")
    return sha256(normalized.encode()).hexdigest()


def validate_referral_token(token: str) -> str:
    """Validate the public opaque-token shape before hashing or setting cookies."""
    if not isinstance(token, str) or len(token) != 67 or not token.startswith("r1_"):
        raise ValueError("referral token is invalid")
    if any(not char.isascii() or not (char.isalnum() or char == "_") for char in token[3:]):
        raise ValueError("referral token is invalid")
    return token


def first_payment_reward(*, paid_at: datetime, cycle: str) -> ReferralReward:
    if cycle not in {"month", "year"}:
        raise ValueError("cycle must be month or year")
    paid_at = paid_at.astimezone(UTC)
    inviter_days = 7 if cycle == "month" else 30
    return ReferralReward(
        invitee_discount_percent=10,
        inviter_days=inviter_days,
        maturity_at=paid_at + timedelta(days=MATURITY_DAYS),
        expires_at=paid_at + timedelta(days=MATURITY_DAYS + 365),
    )


def grantable_days(*, reward: ReferralReward, granted_rolling_days: int, now: datetime) -> int:
    if now.astimezone(UTC) < reward.maturity_at or now.astimezone(UTC) >= reward.expires_at:
        return 0
    return max(0, min(reward.inviter_days, REFERRER_CAP_DAYS - granted_rolling_days))
