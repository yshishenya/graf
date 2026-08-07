"""Bounded, reviewable fair-use state; it never behaves like paid quota."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Literal

FairUseReason = Literal["automated_bulk", "resale", "limit_circumvention", "security_abuse"]
FairUseState = Literal["notice", "restricted", "appealed", "cleared", "confirmed"]

_REASONS = frozenset({"automated_bulk", "resale", "limit_circumvention", "security_abuse"})


@dataclass(frozen=True, slots=True)
class FairUseReview:
    capability: str
    reason: FairUseReason
    evidence_ref: str
    starts_at: datetime
    review_by: datetime
    state: FairUseState = "notice"
    appealed_at: datetime | None = None


def create_review(
    *,
    capability: str,
    reason: str,
    evidence_ref: str,
    starts_at: datetime,
    urgent: bool = False,
) -> FairUseReview:
    start = _aware(starts_at)
    if not capability or len(capability) > 64 or reason not in _REASONS:
        raise ValueError("fair-use review classification is invalid")
    lowered_ref = evidence_ref.lower()
    if (
        not evidence_ref
        or len(evidence_ref) > 160
        or not evidence_ref.isascii()
        or any(part in lowered_ref for part in ("meeting", "content", "email", "card", "token", "payload"))
    ):
        raise ValueError("fair-use evidence reference is invalid")
    review_by = start + timedelta(hours=24)
    return FairUseReview(capability, reason, evidence_ref, start, review_by, "restricted" if urgent else "notice")


def appeal_review(review: FairUseReview, *, at: datetime) -> FairUseReview:
    if review.state in {"cleared", "confirmed"}:
        return review
    return replace(review, state="appealed", appealed_at=_aware(at))


def resolve_review(review: FairUseReview, *, state: Literal["cleared", "confirmed"]) -> FairUseReview:
    return replace(review, state=state)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("fair-use timestamp must be timezone-aware")
    return value.astimezone(UTC)
