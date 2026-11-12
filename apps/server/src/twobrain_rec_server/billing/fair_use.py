"""Bounded, reviewable fair-use state; it never behaves like paid quota."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.database import require_billing_maintenance_database
from twobrain_rec_server.billing.events import enqueue_billing_event
from twobrain_rec_server.billing.trial import merged_user_lineage
from twobrain_rec_server.db.models import (
    AccountClosureRequest,
    BillingAuditEvent,
    BillingNotificationDelivery,
    ExternalIdentity,
    FairUseReviewRecord,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)

FairUseReason = Literal["automated_bulk", "resale", "limit_circumvention", "security_abuse"]
FairUseState = Literal["notice", "restricted", "appealed", "cleared", "confirmed"]

_REASONS = frozenset({"automated_bulk", "resale", "limit_circumvention", "security_abuse"})
_CAPABILITY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
_RESTRICTED_STATES = frozenset({"restricted", "appealed", "confirmed"})
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
    review: FairUseReviewRecord,
) -> bool:
    """Queue a mandatory, metadata-only review notice.

    Review identity and phase bind the outbox to its source; evidence is absent.
    """
    return await enqueue_billing_event(
        db,
        workspace_id=workspace_id,
        recipient_id=recipient_id,
        event_type="fair_use.review",
        subject_ref=f"{review.id.hex}:{review.state}",
        payload={
            "phase": review.state,
            "fair_use_review_id": str(review.id),
            "action_path": "/account/fair-use",
            "capability": review.capability,
            "reason": review.reason_code,
            "review_by": _aware(review.review_by).astimezone(MOSCOW).strftime("%d.%m.%Y %H:%M"),
        },
        marketing_allowed=False,
    )


async def fair_use_restricted_for_lineage(
    db: AsyncSession,
    *,
    user_id: UUID,
    capability: str | None = None,
    include_confirmed: bool = True,
) -> bool:
    lineage = merged_user_lineage(user_id)
    restricted_states = _RESTRICTED_STATES if include_confirmed else _RESTRICTED_STATES - {"confirmed"}
    query = select(FairUseReviewRecord.id).where(
        FairUseReviewRecord.subject_user_id.in_(select(lineage.c.user_id)),
        FairUseReviewRecord.state.in_(restricted_states),
    )
    if capability is not None:
        query = query.where(FairUseReviewRecord.capability == capability)
    return await db.scalar(query.limit(1)) is not None


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
        # Explicit columns preserve the guard's column grants, including on INSERT.
        row = await db.scalar(insert(FairUseReviewRecord).values(
            workspace_id=workspace_id,
            subject_user_id=subject_user_id,
            capability=review.capability,
            reason_code=review.reason,
            evidence_ref=review.evidence_ref,
            starts_at=review.starts_at,
            review_by=review.review_by,
            state=review.state,
        ).returning(FairUseReviewRecord))
    elif (
        row.subject_user_id != subject_user_id
        or row.capability != review.capability
        or row.reason_code != review.reason
    ):
        raise ValueError("fair-use evidence reference is already bound to another review")
    else:
        return row
    await enqueue_review_notification(
        db,
        workspace_id=workspace_id,
        recipient_id=subject_user_id,
        review=row,
    )
    owner_user_id = await db.scalar(select(Workspace.owner_user_id).where(Workspace.id == workspace_id))
    if owner_user_id is not None and owner_user_id != subject_user_id:
        await enqueue_review_notification(
            db,
            workspace_id=workspace_id,
            recipient_id=owner_user_id,
            review=row,
        )
    return row


def _operator_declaration(operator_ref: str, evidence_reviewed: bool) -> None:
    if (not isinstance(operator_ref, str) or not re.fullmatch(r"op-[0-9a-f]{32}", operator_ref)
            or evidence_reviewed is not True):
        raise ValueError("fair-use operator declaration rejected")


async def _operator_workspace(db, *, workspace_id, execute):
    query = select(Workspace).where(Workspace.id == workspace_id)
    workspace = await db.scalar(query.with_for_update(nowait=True) if execute else query)
    if workspace is None or workspace.owner_user_id is None:
        raise ValueError("fair-use workspace unavailable")
    return workspace


async def _review_members(db, *, workspace, user_ids, execute):
    for user_id in sorted(user_ids, key=str):
        # Merge locks identities before Workspace; never wait backwards here.
        query = select(UserIdentity).where(UserIdentity.id == user_id)
        identity = await db.scalar(query.with_for_update(read=True, nowait=True) if execute else query)
        query = select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace.id, WorkspaceMembership.user_id == user_id,
        )
        membership = await db.scalar(query.with_for_update(read=True, nowait=True) if execute else query)
        if (identity is None or identity.status != "active" or identity.merged_into_user_id is not None
                or identity.organization_id != workspace.organization_id or membership is None
                or membership.status != "active"
                or (user_id == workspace.owner_user_id and membership.role != "owner")):
            raise ValueError("fair-use subject unavailable")
        query = select(AccountClosureRequest).where(AccountClosureRequest.requested_by_user_id == user_id).order_by(AccountClosureRequest.id)
        closures = await db.scalars(query.with_for_update(read=True, nowait=True) if execute else query)
        if any(item.state in {"finalizing", "completed"} or (
            item.state == "blocked" and "content_workspace_ids" in (item.metadata_json or {})
        ) for item in closures):
            raise ValueError("fair-use subject unavailable")


async def _declare_operator(db, operator_ref):
    await db.execute(text("SELECT set_config('app.fair_use_operator_ref', :operator, true)"), {"operator": operator_ref})
    await db.execute(text("SELECT set_config('app.fair_use_evidence_reviewed', 'true', true)"))


async def _operator_review_dates(db, row):
    # Check in PostgreSQL: asyncpg maps infinity to finite Python extrema.
    valid = await db.scalar(text("""
        SELECT CASE WHEN isfinite(starts_at) AND isfinite(review_by)
                         AND starts_at <= transaction_timestamp()
            THEN starts_at <= review_by AND review_by <= starts_at + interval '24 hours'
                AND (appealed_at IS NULL OR (isfinite(appealed_at)
                     AND appealed_at BETWEEN starts_at AND transaction_timestamp()))
                AND (resolved_at IS NULL OR (isfinite(resolved_at)
                     AND resolved_at BETWEEN starts_at AND transaction_timestamp()
                     AND (appealed_at IS NULL OR appealed_at <= resolved_at)))
            ELSE false END
        FROM public.fair_use_reviews WHERE id=:id
    """), {"id": row.id})
    if valid is not True:
        raise ValueError("fair-use review dates unavailable")


async def create_operator_review(
    db: AsyncSession, *, workspace_id: UUID, subject_user_id: UUID, capability: str,
    reason: str, evidence_ref: str, operator_ref: str, evidence_reviewed: bool, execute: bool,
) -> tuple[str, bool]:
    _operator_declaration(operator_ref, evidence_reviewed)
    _validate_review_fields(capability, reason, evidence_ref)
    if capability not in {"server_processing", "storage"}:
        raise ValueError("fair-use capability rejected")
    await require_billing_maintenance_database(db)
    workspace = await _operator_workspace(db, workspace_id=workspace_id, execute=execute)
    await _review_members(db, workspace=workspace,
                          user_ids={subject_user_id, workspace.owner_user_id}, execute=execute)
    query = select(FairUseReviewRecord).where(
        FairUseReviewRecord.workspace_id == workspace_id, FairUseReviewRecord.evidence_ref == evidence_ref,
    )
    row = await db.scalar(query.with_for_update(nowait=True) if execute else query)
    if row is not None:
        await _operator_review_dates(db, row)
        if (row.subject_user_id, row.capability, row.reason_code) != (subject_user_id, capability, reason):
            raise ValueError("fair-use review conflict")
        return row.state, False
    if not execute:
        return "notice", False
    await _declare_operator(db, operator_ref)
    started = await db.scalar(select(func.transaction_timestamp()))
    row = await persist_review(db, workspace_id=workspace_id, subject_user_id=subject_user_id,
                               review=create_review(capability=capability, reason=reason,
                                                    evidence_ref=evidence_ref, starts_at=started))
    return row.state, True


async def resolve_persisted_review(
    db: AsyncSession, *, workspace_id: UUID, evidence_ref: str, decision: str,
    resolution_code: str, operator_ref: str, evidence_reviewed: bool, execute: bool,
) -> tuple[str, bool]:
    _operator_declaration(operator_ref, evidence_reviewed)
    _validate_review_fields("server_processing", "resale", evidence_ref)
    if (decision, resolution_code) not in {
        ("cleared", "not_substantiated"), ("cleared", "no_longer_applicable"), ("confirmed", "basis_confirmed"),
    }:
        raise ValueError("fair-use resolution rejected")
    await require_billing_maintenance_database(db)
    workspace = await _operator_workspace(db, workspace_id=workspace_id, execute=execute)
    query = select(FairUseReviewRecord).where(
        FairUseReviewRecord.workspace_id == workspace_id, FairUseReviewRecord.evidence_ref == evidence_ref,
    )
    row = await db.scalar(query.with_for_update(nowait=True) if execute else query)
    if row is None:
        raise ValueError("fair-use review unavailable")
    await _review_members(db, workspace=workspace,
                          user_ids={row.subject_user_id, workspace.owner_user_id}, execute=execute)
    await _operator_review_dates(db, row)
    created = await db.scalar(select(BillingAuditEvent.id).where(
        BillingAuditEvent.workspace_id == workspace_id, BillingAuditEvent.target_ref == str(row.id),
        BillingAuditEvent.target_kind == "fair_use_review", BillingAuditEvent.action == "fair_use.review.created",
    ).limit(1))
    if created is None:
        raise ValueError("fair-use review source unavailable")
    if row.state in {"cleared", "confirmed"}:
        if (row.state, row.resolution_code) != (decision, resolution_code):
            raise ValueError("fair-use resolution conflict")
        return row.state, False
    if row.state not in {"notice", "restricted", "appealed"} or row.resolved_at is not None or row.resolution_code is not None:
        raise ValueError("fair-use review state unavailable")
    if not execute:
        return decision, False
    await _declare_operator(db, operator_ref)
    row.state, row.resolution_code = decision, resolution_code
    await db.flush()
    await db.refresh(row)
    for recipient in sorted({row.subject_user_id, workspace.owner_user_id}, key=str):
        await enqueue_review_notification(db, workspace_id=workspace_id, recipient_id=recipient, review=row)
    return row.state, True


async def appeal_persisted_review(
    db: AsyncSession,
    *,
    review_id: UUID,
    subject_user_id: UUID,
) -> tuple[FairUseReviewRecord | None, bool]:
    """Record an idempotent appeal without accepting user-supplied rationale."""
    allowed = await db.scalar(text("""
        SELECT session_user = 'twobrain_rec_app' AND current_user = session_user
            AND current_setting('row_security') = 'on'
            AND public.rec_context_kind() = 'request'
            AND public.rec_current_user_id() = :user_id
    """), {"user_id": subject_user_id})
    if allowed is not True:
        return None, False
    lineage = merged_user_lineage(subject_user_id)
    source = select(FairUseReviewRecord).where(
        FairUseReviewRecord.id == review_id,
        FairUseReviewRecord.subject_user_id.in_(select(lineage.c.user_id)),
    )
    workspace_id = await db.scalar(source.with_only_columns(FairUseReviewRecord.workspace_id))
    if workspace_id is None:
        return None, False
    previous_workspace = await db.scalar(select(func.current_setting('app.workspace_id', True)))
    linked = previous_workspace != str(workspace_id)
    if linked and await db.scalar(select(func.rec_current_user_owns_lineage_workspace(workspace_id))) is not True:
        return None, False
    try:
        # A savepoint restores the narrowed DB context even after a SQL failure.
        async with db.begin_nested():
            if linked:
                await db.execute(select(func.set_config('app.workspace_id', str(workspace_id), True)))
            workspace = await _operator_workspace(db, workspace_id=workspace_id, execute=True)
            # Request RLS exposes only the actor's membership and closure history.
            await _review_members(db, workspace=workspace, user_ids={subject_user_id}, execute=True)
            if linked and await db.scalar(select(func.rec_current_user_owns_lineage_workspace(workspace_id))) is not True:
                return None, False
            row = await db.scalar(source.with_for_update(nowait=True).execution_options(populate_existing=True))
            if row is None or row.workspace_id != workspace_id:
                return None, False
            if row.state in {"appealed", "cleared", "confirmed"}:
                return row, False
            if row.state not in {"notice", "restricted"} or row.appealed_at is not None or row.appeal_ref is not None:
                raise ValueError("fair-use appeal unavailable")
            row.state = "appealed"
            await db.flush()
            await db.refresh(row)
            for recipient in sorted({row.subject_user_id, workspace.owner_user_id}, key=str):
                await enqueue_review_notification(db, workspace_id=workspace_id, recipient_id=recipient, review=row)
            return row, True
    finally:
        if linked:
            await db.execute(select(func.set_config('app.workspace_id', previous_workspace, True)))


async def fair_use_notice_recipient(db: AsyncSession, delivery: BillingNotificationDelivery) -> str | None:
    """Lock the recorded source and original recipient until the durable claim."""
    await require_billing_maintenance_database(db)
    payload = delivery.safe_payload or {}
    if not isinstance(payload, dict):
        return None
    phase = payload.get("phase")
    if phase not in ("notice", "appealed", "cleared", "confirmed"):
        return None
    try:
        review_id = UUID(payload.get("fair_use_review_id", ""))
    except (ValueError, TypeError, AttributeError):
        return None
    if delivery.event_id != f"fair_use.review:{review_id.hex}:{phase}":
        return None
    try:
        workspace = await _operator_workspace(db, workspace_id=delivery.workspace_id, execute=True)
        row = await db.scalar(select(FairUseReviewRecord).where(
            FairUseReviewRecord.id == review_id, FairUseReviewRecord.workspace_id == workspace.id,
        ).with_for_update(read=True, nowait=True))
        if row is None or delivery.recipient_id not in {row.subject_user_id, workspace.owner_user_id}:
            return None
        await _operator_review_dates(db, row)
        if any(payload.get(key) != expected for key, expected in {
            "capability": row.capability, "reason": row.reason_code,
            "review_by": _aware(row.review_by).astimezone(MOSCOW).strftime("%d.%m.%Y %H:%M"),
            "action_path": "/account/fair-use",
        }.items()):
            return None
        action, occurred_at = {
            "notice": ("created", row.starts_at), "appealed": ("appealed", row.appealed_at),
            "cleared": ("resolved", row.resolved_at), "confirmed": ("resolved", row.resolved_at),
        }[phase]
        audit = await db.scalar(select(BillingAuditEvent).where(
            BillingAuditEvent.workspace_id == workspace.id,
            BillingAuditEvent.target_kind == "fair_use_review", BillingAuditEvent.target_ref == str(row.id),
            BillingAuditEvent.action == f"fair_use.review.{action}", BillingAuditEvent.outcome == "applied",
        ))
        metadata = audit.metadata_json if audit is not None else {}
        if (audit is None or occurred_at is None or audit.created_at != occurred_at
                or not isinstance(metadata, dict) or type(metadata.get("version")) is not int
                or metadata.get("version") != 1 or metadata.get("state") != phase
                or metadata.get("db_writer") != "twobrain_rec_fair_use_audit_writer"):
            return None
        await _review_members(db, workspace=workspace, user_ids={delivery.recipient_id}, execute=True)
    except ValueError:
        return None
    emails = await db.scalars(select(ExternalIdentity).where(
        ExternalIdentity.user_id == delivery.recipient_id, ExternalIdentity.is_active.is_(True),
        ExternalIdentity.is_verified.is_(True), ExternalIdentity.email.is_not(None), ExternalIdentity.email != "",
    ).order_by(ExternalIdentity.id).with_for_update(read=True, nowait=True))
    return min((item.email for item in emails), default=None)


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
