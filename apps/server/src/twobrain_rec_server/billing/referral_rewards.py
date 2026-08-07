from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from twobrain_rec_server.billing.referrals import ReferralReward, grantable_days


@dataclass(frozen=True, slots=True)
class TimeCredit:
    source_ref: str
    days: int
    state: str = "pending"


def mature_credit(*, reward: ReferralReward, source_ref: str, granted_rolling_days: int, now: datetime) -> TimeCredit | None:
    days = grantable_days(reward=reward, granted_rolling_days=granted_rolling_days, now=now)
    return TimeCredit(source_ref, days, "matured") if days else None
