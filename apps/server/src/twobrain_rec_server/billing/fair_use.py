"""Bounded, reviewable fair-use state; it never behaves like paid quota."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.events import enqueue_billing_event
from twobrain_rec_server.db.models import FairUseReviewRecord, Workspace

FairUseReason = Literal["automated_bulk", "resale", "limit_circumvention", "security_abuse"]
FairUseState = Literal["notice", "restricted", "appealed", "cleared", "confirmed"]

_REASONS = frozenset({"automated_bulk", "resale", "limit_circumvention", "security_abuse"})
_CAPABILITY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
MOSCOW = ZoneInfo("Europe/Moscow")


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
    _validate_review_fields(capability, reason, evidence_ref)
    review_by = start + timedelta(hours=24)
    return FairUseReview(capability, reason, evidence_ref, start, review_by, "restricted" if urgent else "notice")


def appeal_review(review: FairUseReview, *, at: datetime) -> FairUseReview:
    if review.state in {"cleared", "confirmed"}:
        return review
    return replace(review, state="appealed", appealed_at=_aware(at))


def review_subject_ref(review: FairUseReview) -> str:
    """Return a bounded hash subject; the opaque evidence never leaves review state."""
    digest = hashlib.sha256(review.evidence_ref.encode("ascii")).hexdigest()[:32]
    return f"{review.capability}:review:{digest}"


async def enqueue_review_notification(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    recipient_id: UUID,
    review: FairUseReview,
) -> bool:
    """Queue a mandatory, metadata-only review notice.

    The evidence reference is used only as a bounded opaque dedupe key.  It is
    never included in the notification payload or user-facing copy.
    """
    return await enqueue_billing_event(
        db,
        workspace_id=workspace_id,
        recipient_id=recipient_id,
        event_type="fair_use.review",
        subject_ref=review_subject_ref(review),
        payload={
            "action_path": "/account/fair-use",
            "capability": review.capability,
            "reason": review.reason,
            "review_by": _aware(review.review_by).astimezone(MOSCOW).strftime("%d.%m.%Y %H:%M"),
        },
        marketing_allowed=False,
    )


async def persist_review(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    subject_user_id: UUID,
    review: FairUseReview,
) -> FairUseReviewRecord:
    """Persist one review idempotently and enqueue its mandatory notice.

    The evidence reference is an opaque operator reference; raw evidence and
    support correspondence never enter the row or notification payload.
    """
    _validate_review_fields(review.capability, review.reason, review.evidence_ref)
    if review.state not in {"notice", "restricted", "appealed", "cleared", "confirmed"}:
        raise ValueError("fair-use review state is invalid")
    starts_at = _aware(review.starts_at)
    review_by = _aware(review.review_by)
    if not starts_at <= review_by <= starts_at + timedelta(hours=24):
        raise ValueError("fair-use review deadline is outside the 24-hour review window")
    row = await db.scalar(
        select(FairUseReviewRecord)
        .where(
            FairUseReviewRecord.workspace_id == workspace_id,
            FairUseReviewRecord.evidence_ref == review.evidence_ref,
        )
        .with_for_update()
    )
    if row is None:
        row = FairUseReviewRecord(
            workspace_id=workspace_id,
            subject_user_id=subject_user_id,
            capability=review.capability,
            reason_code=review.reason,
            evidence_ref=review.evidence_ref,
            starts_at=review.starts_at,
            review_by=review.review_by,
            state=review.state,
            appealed_at=review.appealed_at,
        )
        db.add(row)
        await db.flush()
    elif (
        row.subject_user_id != subject_user_id
        or row.capability != review.capability
        or row.reason_code != review.reason
        or _aware(row.starts_at) != _aware(review.starts_at)
        or _aware(row.review_by) != _aware(review.review_by)
    ):
        raise ValueError("fair-use evidence reference is already bound to another review")
    await enqueue_review_notification(
        db,
        workspace_id=workspace_id,
        recipient_id=subject_user_id,
        review=review,
    )
    owner_user_id = await db.scalar(select(Workspace.owner_user_id).where(Workspace.id == workspace_id))
    if owner_user_id is not None and owner_user_id != subject_user_id:
        await enqueue_review_notification(
            db,
            workspace_id=workspace_id,
            recipient_id=owner_user_id,
            review=review,
        )
    return row


async def appeal_persisted_review(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    review_id: UUID,
    subject_user_id: UUID,
    at: datetime,
) -> FairUseReviewRecord | None:
    """Record an idempotent appeal without accepting user-supplied rationale."""
    row = await db.scalar(
        select(FairUseReviewRecord)
        .where(
            FairUseReviewRecord.id == review_id,
            FairUseReviewRecord.workspace_id == workspace_id,
            FairUseReviewRecord.subject_user_id == subject_user_id,
        )
        .with_for_update()
    )
    if row is None:
        return None
    if row.state in {"cleared", "confirmed"}:
        return row
    if row.appealed_at is None:
        row.appealed_at = _aware(at)
        row.appeal_ref = f"appeal:{row.id.hex[:24]}"
    row.state = "appealed"
    await db.flush()
    return row


def resolve_review(review: FairUseReview, *, state: Literal["cleared", "confirmed"]) -> FairUseReview:
    return replace(review, state=state)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("fair-use timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _validate_review_fields(capability: str, reason: str, evidence_ref: str) -> None:
    if (
        not capability
        or len(capability) > 64
        or not capability.isascii()
        or not _CAPABILITY_RE.fullmatch(capability)
        or reason not in _REASONS
    ):
        raise ValueError("fair-use review classification is invalid")
    lowered_ref = evidence_ref.lower()
    if (
        not evidence_ref
        or len(evidence_ref) > 160
        or not evidence_ref.isascii()
        or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", evidence_ref)
        or any(part in lowered_ref for part in ("meeting", "content", "email", "card", "token", "payload"))
    ):
        raise ValueError("fair-use evidence reference is invalid")
