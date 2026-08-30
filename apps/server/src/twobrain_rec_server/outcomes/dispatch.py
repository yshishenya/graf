"""Durable candidate dispatch intent helpers."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import (
    DispatchIntent,
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeSet,
    ProcessingResult,
)
from twobrain_rec_server.processing.fences import meeting_is_deleted_or_deleting
from twobrain_rec_server.workflows.temporal_client import outcome_generation_workflow_id

MAX_DISPATCH_ATTEMPTS = 5
DISPATCH_RETRY_DELAYS = (5, 30, 120, 600)
DISPATCH_LEASE = timedelta(seconds=60)
# Provider start is deterministic by candidate id. Bound the client call so a
# stalled SDK call cannot outlive its lease and race a maintenance retry.
DISPATCH_START_TIMEOUT_SECONDS = 45.0
logger = logging.getLogger(__name__)


async def reconcile_orphaned_summary_candidates(
    db: AsyncSession,
    *,
    limit: int = 25,
) -> int:
    """Repair imported AI-only outcome placeholders with no dispatch ledger row.

    A short-lived regression could commit the revision-scoped placeholder before
    candidate creation. Such rows are not visible to the normal dispatch
    reconciler because they have no attempt or intent to claim. Re-enqueue the
    canonical automatic candidate through the same idempotent path used by a
    fresh import, then quarantine the empty placeholder as stale.
    """

    if limit <= 0:
        return 0
    candidate_has_attempt = exists(
        select(MeetingOutcomeGenerationAttempt.id).where(
            MeetingOutcomeGenerationAttempt.workspace_id == MeetingOutcomeSet.workspace_id,
            MeetingOutcomeGenerationAttempt.candidate_id == MeetingOutcomeSet.candidate_id,
        )
    )
    orphaned = (
        await db.execute(
            select(
                MeetingOutcomeSet.id,
                MeetingOutcomeSet.workspace_id,
                MeetingOutcomeSet.meeting_id,
                MeetingOutcomeSet.candidate_id,
            )
            .join(
                ProcessingResult,
                ProcessingResult.id == MeetingOutcomeSet.processing_result_id,
            )
            .join(Meeting, Meeting.id == MeetingOutcomeSet.meeting_id)
            .where(
                MeetingOutcomeSet.candidate_id.is_not(None),
                MeetingOutcomeSet.media_revision_id.is_not(None),
                MeetingOutcomeSet.generator_kind == "deterministic_extractive",
                MeetingOutcomeSet.status == "generating",
                MeetingOutcomeSet.revision_state == "candidate",
                ProcessingResult.status == "imported",
                ProcessingResult.transcript_status == "available",
                ProcessingResult.segment_count > 0,
                Meeting.deleted_at.is_(None),
                or_(Meeting.deletion_state.is_(None), Meeting.deletion_state == "none"),
                ~candidate_has_attempt,
            )
            .order_by(MeetingOutcomeSet.created_at.asc(), MeetingOutcomeSet.id.asc())
            .limit(limit)
            .with_for_update(skip_locked=True, of=MeetingOutcomeSet)
        )
    ).all()
    await db.commit()

    if not orphaned:
        return 0

    # Import lazily: ai_service imports this module for the ordinary dispatch
    # helpers, so a top-level import would introduce a circular dependency.
    from twobrain_rec_server.outcomes.ai_service import ensure_automatic_summary_candidate

    repaired = 0
    for outcome_set_id, workspace_id, meeting_id, candidate_id in orphaned:
        try:
            attempt = await ensure_automatic_summary_candidate(
                db,
                workspace_id=workspace_id,
                meeting_id=meeting_id,
            )
            if attempt is None:
                await db.rollback()
                continue
            placeholder = await db.scalar(
                select(MeetingOutcomeSet)
                .where(
                    MeetingOutcomeSet.id == outcome_set_id,
                    MeetingOutcomeSet.workspace_id == workspace_id,
                    MeetingOutcomeSet.meeting_id == meeting_id,
                    MeetingOutcomeSet.candidate_id == candidate_id,
                )
                .with_for_update()
            )
            if placeholder is not None and placeholder.revision_state == "candidate":
                placeholder.status = "blocked"
                placeholder.revision_state = "stale"
                placeholder.failure_reason = "summary_candidate_orphan_repaired"
                placeholder.failure_source = "reconciliation"
            await db.commit()
            repaired += 1
        except Exception:
            await db.rollback()
            logger.exception(
                "orphaned summary candidate reconciliation failed",
                extra={
                    "workspace_id": str(workspace_id),
                    "meeting_id": str(meeting_id),
                    "outcome_set_id": str(outcome_set_id),
                },
            )
    return repaired


def _workflow_slot_identity(
    attempt: MeetingOutcomeGenerationAttempt | None,
) -> tuple[UUID, UUID | None] | None:
    if attempt is None:
        return None
    metadata = attempt.metadata_json or {}
    raw_slot_id = metadata.get("summary_slot_id")
    if not isinstance(raw_slot_id, str) or not raw_slot_id:
        return None
    if "expected_current_outcome_set_id" not in metadata:
        return None
    raw_expected = metadata.get("expected_current_outcome_set_id")
    try:
        slot_id = UUID(raw_slot_id)
        expected_id = UUID(raw_expected) if isinstance(raw_expected, str) and raw_expected else None
    except (AttributeError, TypeError, ValueError):
        return None
    return slot_id, expected_id


async def ensure_dispatch_intent(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting: Meeting,
    candidate_id: UUID,
    idempotency_key: str,
    source_fingerprint: str | None,
    payload: dict[str, object] | None = None,
) -> DispatchIntent:
    existing = await db.scalar(
        select(DispatchIntent)
        .where(
            DispatchIntent.workspace_id == workspace_id,
            DispatchIntent.idempotency_key == idempotency_key,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if existing is not None:
        return existing
    # A manual retry reuses the candidate identity but rotates its dispatch
    # key. Reuse the one durable intent for that candidate instead of creating
    # a second row that terminal reconciliation could overlook.
    existing = await db.scalar(
        select(DispatchIntent)
        .where(
            DispatchIntent.workspace_id == workspace_id,
            DispatchIntent.candidate_id == candidate_id,
        )
        .order_by(DispatchIntent.created_at.desc())
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if existing is not None:
        attempt = await db.scalar(
            select(MeetingOutcomeGenerationAttempt)
            .where(
                MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
                MeetingOutcomeGenerationAttempt.candidate_id == candidate_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if existing.idempotency_key != idempotency_key:
            existing.idempotency_key = idempotency_key
        if attempt is not None and attempt.status in {
            "queued",
            "generating",
            "blocked_dependency",
        } and existing.state in {"completed", "cancelled", "terminal_failed"}:
            existing.state = "created"
            existing.reconciliation_state = "pending"
            existing.attempt_count = 0
            existing.failure_code = None
            existing.lease_expires_at = None
            existing.next_attempt_at = datetime.now(UTC)
            existing.external_workflow_id = None
            existing.external_run_id = None
            existing.started_at = None
            existing.completed_at = None
        if meeting_is_deleted_or_deleting(meeting):
            existing.state = "cancelled"
            existing.reconciliation_state = "cancelled"
            existing.next_attempt_at = None
        if payload is not None:
            existing.payload_json = payload
        existing.source_fingerprint = source_fingerprint
        await db.flush()
        return existing
    state = "cancelled" if meeting_is_deleted_or_deleting(meeting) else "created"
    intent = DispatchIntent(
        workspace_id=workspace_id,
        meeting_id=meeting.id,
        candidate_id=candidate_id,
        intent_kind="summary_generation",
        idempotency_key=idempotency_key,
        state=state,
        reconciliation_state="pending",
        payload_json=payload or {},
        source_fingerprint=source_fingerprint,
        deletion_epoch=int(meeting.deletion_epoch or 0),
        next_attempt_at=datetime.now(UTC) if state == "created" else None,
    )
    db.add(intent)
    await db.flush()
    return intent


async def mark_dispatch_started(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    idempotency_key: str,
    workflow_id: str,
    run_id: str | None,
) -> DispatchIntent | None:
    seed_intent = await db.scalar(
        select(DispatchIntent).where(
            DispatchIntent.workspace_id == workspace_id,
            DispatchIntent.idempotency_key == idempotency_key,
        ).execution_options(populate_existing=True)
    )
    if seed_intent is None:
        return None
    meeting = await db.scalar(
        select(Meeting)
        .where(
            Meeting.workspace_id == workspace_id,
            Meeting.id == seed_intent.meeting_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    attempt = await db.scalar(
        select(MeetingOutcomeGenerationAttempt)
        .where(
            MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
            MeetingOutcomeGenerationAttempt.candidate_id == seed_intent.candidate_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    intent = await db.scalar(
        select(DispatchIntent)
        .where(
            DispatchIntent.workspace_id == workspace_id,
            DispatchIntent.id == seed_intent.id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if intent is None:
        return None
    if (
        meeting is None
        or meeting_is_deleted_or_deleting(meeting)
        or (
            attempt is not None
            and int(meeting.deletion_epoch or 0)
            != int(attempt.deletion_epoch_at_start or 0)
        )
        or (attempt is not None and attempt.status in {"cancelled", "stale", "expired", "rejected"})
    ):
        if intent.state not in {"completed", "cancelled", "terminal_failed"}:
            intent.state = "cancelled"
            intent.reconciliation_state = "cancelled"
            intent.failure_code = "meeting_deleting"
            intent.completed_at = datetime.now(UTC)
            intent.lease_expires_at = None
        await db.flush()
        return intent
    if intent.state in {"completed", "cancelled", "terminal_failed"}:
        return intent
    intent.state = "started"
    intent.reconciliation_state = "started"
    intent.external_workflow_id = workflow_id
    if run_id is not None:
        intent.external_run_id = run_id
    intent.started_at = intent.started_at or datetime.now(UTC)
    intent.completed_at = None
    # Keep a durable handoff lease after Temporal acknowledges the start. A
    # worker may be cancelled before the first workflow callback; maintenance
    # must be able to retry this deterministic candidate workflow.
    intent.lease_expires_at = datetime.now(UTC) + DISPATCH_LEASE
    intent.next_attempt_at = None
    intent.failure_code = None
    intent.last_reconciled_at = datetime.now(UTC)
    await db.flush()
    return intent


async def mark_dispatch_failure(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    idempotency_key: str,
    failure_code: str,
    retryable: bool,
    increment_attempt: bool = True,
) -> DispatchIntent | None:
    intent = await db.scalar(
        select(DispatchIntent)
        .where(
            DispatchIntent.workspace_id == workspace_id,
            DispatchIntent.idempotency_key == idempotency_key,
        )
        .execution_options(populate_existing=True)
        .with_for_update()
    )
    if intent is None:
        return None
    if increment_attempt:
        intent.attempt_count += 1
    intent.failure_code = failure_code
    intent.last_reconciled_at = datetime.now(UTC)
    if retryable and intent.attempt_count < MAX_DISPATCH_ATTEMPTS:
        delay = DISPATCH_RETRY_DELAYS[min(intent.attempt_count - 1, len(DISPATCH_RETRY_DELAYS) - 1)]
        intent.state = "retryable_failed"
        intent.reconciliation_state = "pending"
        intent.next_attempt_at = datetime.now(UTC) + timedelta(seconds=delay)
        intent.lease_expires_at = None
    else:
        intent.state = "terminal_failed"
        intent.reconciliation_state = "terminal"
        intent.next_attempt_at = None
        intent.lease_expires_at = None
        intent.completed_at = datetime.now(UTC)
    await db.flush()
    return intent


async def finalize_dispatch_for_candidate(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    candidate_id: UUID,
    outcome: str,
    failure_code: str | None = None,
) -> DispatchIntent | None:
    """Close durable dispatch state when generation reaches a terminal state."""
    intents = (
        await db.scalars(
            select(DispatchIntent)
            .where(
                DispatchIntent.workspace_id == workspace_id,
                DispatchIntent.candidate_id == candidate_id,
            )
            .order_by(DispatchIntent.created_at.desc(), DispatchIntent.id.desc())
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()
    if not intents:
        return None
    now = datetime.now(UTC)
    for intent in intents:
        if intent.state in {"completed", "terminal_failed", "cancelled"}:
            continue
        if outcome == "completed":
            intent.state = "completed"
            intent.reconciliation_state = "completed"
            intent.failure_code = None
        elif outcome == "cancelled":
            intent.state = "cancelled"
            intent.reconciliation_state = "cancelled"
            intent.failure_code = failure_code
        else:
            intent.state = "terminal_failed"
            intent.reconciliation_state = "terminal"
            intent.failure_code = failure_code or "summary_generation_failed"
        intent.lease_expires_at = None
        intent.next_attempt_at = None
        intent.completed_at = now
        intent.last_reconciled_at = now
    return intents[0]


async def list_due_dispatch_intents(
    db: AsyncSession, *, limit: int = 100
) -> list[DispatchIntent]:
    now = datetime.now(UTC)
    rows = await db.scalars(
        select(DispatchIntent)
        .where(
            (
                DispatchIntent.state.in_({"created", "retryable_failed"})
                | (
                    (
                        (DispatchIntent.state == "dispatching")
                        | (DispatchIntent.state == "started")
                    )
                    & (
                        DispatchIntent.lease_expires_at.is_(None)
                        | (DispatchIntent.lease_expires_at <= now)
                    )
                )
            ),
            DispatchIntent.reconciliation_state.in_({"pending", "in_progress", "started"}),
            (
                DispatchIntent.next_attempt_at.is_(None)
                | (DispatchIntent.next_attempt_at <= now)
            ),
        )
        .order_by(DispatchIntent.created_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
        .execution_options(populate_existing=True)
    )
    intents = list(rows)
    for intent in intents:
        if intent.state in {"dispatching", "started"}:
            intent.state = "retryable_failed"
            intent.reconciliation_state = "pending"
            intent.failure_code = "summary_dispatch_started_lease_expired"
            intent.next_attempt_at = now
            intent.lease_expires_at = None
    return intents


async def reconcile_dispatch_intent(
    db: AsyncSession,
    *,
    intent: DispatchIntent,
    settings: object,
    temporal_client: object,
) -> bool:
    """Start one durable intent and project the result back into its candidate."""
    from twobrain_rec_server.workflows.temporal_client import start_outcome_generation_workflow

    meeting = await db.scalar(
        select(Meeting)
        .where(
            Meeting.workspace_id == intent.workspace_id,
            Meeting.id == intent.meeting_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    # Keep the canonical Meeting → Attempt → DispatchIntent lock order used
    # by generation and candidate resolution. The maintenance reconciler must
    # not hold the intent while waiting for the attempt row.
    attempt = await db.scalar(
        select(MeetingOutcomeGenerationAttempt)
        .where(
            MeetingOutcomeGenerationAttempt.workspace_id == intent.workspace_id,
            MeetingOutcomeGenerationAttempt.candidate_id == intent.candidate_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    current_intent = await db.scalar(
        select(DispatchIntent)
        .where(DispatchIntent.id == intent.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if current_intent is None:
        return False
    intent = current_intent
    workflow_slot_identity = _workflow_slot_identity(attempt)
    if (
        intent.state in {"started", "dispatching"}
        and intent.lease_expires_at is not None
        and intent.lease_expires_at > datetime.now(UTC)
    ):
        await db.rollback()
        return False
    if (
        attempt is None
        or attempt.candidate_id is None
        or attempt.source_result_id is None
        or attempt.template_key is None
        or workflow_slot_identity is None
    ):
        await mark_dispatch_failure(
            db,
            workspace_id=intent.workspace_id,
            idempotency_key=intent.idempotency_key,
            failure_code="summary_dispatch_state_invalid",
            retryable=False,
        )
        if attempt is not None:
            attempt.status = "failed"
            attempt.failure_code = "summary_dispatch_state_invalid"
        await db.commit()
        return False
    if (
        meeting is None
        or meeting_is_deleted_or_deleting(meeting)
        or intent.state not in {"created", "retryable_failed", "dispatching"}
        or intent.reconciliation_state not in {"pending", "in_progress"}
        or attempt.status not in {"queued", "generating", "blocked_dependency"}
    ):
        intent.state = "cancelled"
        intent.reconciliation_state = "cancelled"
        intent.lease_expires_at = None
        attempt.status = "cancelled"
        attempt.failure_code = "meeting_deleting"
        await db.commit()
        return False
    if (
        int(meeting.deletion_epoch or 0) != int(intent.deletion_epoch or 0)
        or int(attempt.deletion_epoch_at_start or 0) != int(intent.deletion_epoch or 0)
        or (
            intent.source_fingerprint is not None
            and intent.source_fingerprint != attempt.source_fingerprint
        )
    ):
        intent.state = "cancelled"
        intent.reconciliation_state = "cancelled"
        intent.lease_expires_at = None
        intent.failure_code = "summary_dispatch_stale"
        attempt.status = "cancelled"
        attempt.failure_code = "summary_dispatch_stale"
        await db.commit()
        return False
    if intent.attempt_count >= MAX_DISPATCH_ATTEMPTS:
        failure_code = "summary_dispatch_retries_exhausted"
        attempt.status = "failed"
        attempt.failure_code = attempt.failure_code or failure_code
        attempt.failure_reason = attempt.failure_reason or failure_code
        attempt.ended_at = attempt.ended_at or datetime.now(UTC)
        await mark_dispatch_failure(
            db,
            workspace_id=intent.workspace_id,
            idempotency_key=intent.idempotency_key,
            failure_code=failure_code,
            retryable=False,
            increment_attempt=False,
        )
        await db.commit()
        return False
    intent.state = "dispatching"
    intent.reconciliation_state = "in_progress"
    intent.attempt_count += 1
    dispatch_attempt_count = intent.attempt_count
    intent.lease_expires_at = datetime.now(UTC) + DISPATCH_LEASE
    await db.commit()
    try:
        summary_slot_id, expected_current_outcome_set_id = workflow_slot_identity
        started = await asyncio.wait_for(
            start_outcome_generation_workflow(
                temporal_client=temporal_client,
                settings=settings,
                candidate_id=attempt.candidate_id,
                meeting_id=attempt.meeting_id,
                workspace_id=attempt.workspace_id,
                source_result_id=attempt.source_result_id,
                template_key=attempt.template_key,
                template_version=attempt.template_version or 1,
                prompt_name=attempt.prompt_name or "graf-summary",
                requested_by_user_id=attempt.requested_by_user_id,
                summary_slot_id=summary_slot_id,
                expected_current_outcome_set_id=expected_current_outcome_set_id,
            ),
            timeout=DISPATCH_START_TIMEOUT_SECONDS,
        )
    except Exception as dispatch_error:
        if not isinstance(dispatch_error, asyncio.TimeoutError):
            await _cancel_started_workflow(
                temporal_client,
                outcome_generation_workflow_id(attempt.candidate_id),
            )
        # Temporal start can race with a deletion or a user cancellation after
        # the lease commit. Re-read the authoritative rows before projecting a
        # retryable failure so a stale worker cannot resurrect the attempt.
        current_meeting = await db.scalar(
            select(Meeting)
            .where(
                Meeting.workspace_id == intent.workspace_id,
                Meeting.id == intent.meeting_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        current_attempt = await db.scalar(
            select(MeetingOutcomeGenerationAttempt)
            .where(MeetingOutcomeGenerationAttempt.id == attempt.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        current_intent = await db.scalar(
            select(DispatchIntent)
            .where(DispatchIntent.id == intent.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        stale = (
            current_meeting is None
            or current_intent is None
            or current_attempt is None
            or current_intent.state != "dispatching"
            or current_intent.reconciliation_state != "in_progress"
            or current_intent.lease_expires_at is None
            or current_intent.lease_expires_at <= datetime.now(UTC)
            or current_intent.attempt_count != dispatch_attempt_count
            or current_attempt.status not in {"queued", "generating", "blocked_dependency"}
            or meeting_is_deleted_or_deleting(current_meeting)
            or int(current_meeting.deletion_epoch or 0) != int(intent.deletion_epoch or 0)
            or int(current_attempt.deletion_epoch_at_start or 0)
            != int(intent.deletion_epoch or 0)
            or (
                intent.source_fingerprint is not None
                and intent.source_fingerprint != current_attempt.source_fingerprint
            )
        )
        if stale:
            same_lease_owner = (
                current_intent is not None
                and current_intent.state == "dispatching"
                and current_intent.reconciliation_state == "in_progress"
                and current_intent.attempt_count == dispatch_attempt_count
                and current_intent.lease_expires_at is not None
                and current_intent.lease_expires_at > datetime.now(UTC)
            )
            if same_lease_owner and current_attempt is not None and (
                current_attempt.status in {"queued", "generating", "blocked_dependency"}
                and (
                    current_meeting is None
                    or meeting_is_deleted_or_deleting(current_meeting)
                    or int(current_meeting.deletion_epoch or 0)
                    != int(intent.deletion_epoch or 0)
                    or (
                        intent.source_fingerprint is not None
                        and intent.source_fingerprint != current_attempt.source_fingerprint
                    )
                )
            ):
                current_intent.state = "cancelled"
                current_intent.reconciliation_state = "cancelled"
                current_intent.lease_expires_at = None
                current_intent.failure_code = "summary_dispatch_stale"
                current_attempt.status = "cancelled"
                current_attempt.failure_code = "summary_dispatch_stale"
                await db.commit()
            else:
                await db.rollback()
            return False
        if isinstance(dispatch_error, asyncio.TimeoutError):
            # wait_for cancelled only the client-side acknowledgement. The
            # deterministic Temporal start may already be accepted, so keep
            # the workflow identity and lease for reconciliation instead of
            # cancelling a possibly running workflow.
            current_intent.state = "started"
            current_intent.reconciliation_state = "started"
            current_intent.external_workflow_id = outcome_generation_workflow_id(
                attempt.candidate_id
            )
            current_intent.lease_expires_at = datetime.now(UTC) + DISPATCH_LEASE
            current_intent.next_attempt_at = None
            current_intent.failure_code = None
            if (
                current_attempt.status == "queued"
                and current_attempt.failure_source == "temporal_dispatch"
            ):
                current_attempt.failure_code = None
                current_attempt.failure_source = None
            await db.commit()
            return False
        failure_intent = await mark_dispatch_failure(
            db,
            workspace_id=intent.workspace_id,
            idempotency_key=intent.idempotency_key,
            failure_code="summary_dispatch_unavailable",
            retryable=True,
            increment_attempt=False,
        )
        if failure_intent is not None and failure_intent.state == "terminal_failed":
            current_attempt.status = "failed"
            current_attempt.failure_code = "summary_dispatch_retries_exhausted"
            current_attempt.failure_reason = (
                current_attempt.failure_reason or "summary_dispatch_retries_exhausted"
            )
            current_attempt.failure_source = "temporal_dispatch"
            current_attempt.ended_at = current_attempt.ended_at or datetime.now(UTC)
        elif current_attempt.status in {"queued", "blocked_dependency"} or current_attempt.failure_source != "worker":
            if isinstance(dispatch_error, asyncio.TimeoutError):
                current_attempt.status = "blocked_dependency"
                current_attempt.failure_code = "summary_dispatch_unavailable"
            else:
                current_attempt.failure_code = "summary_generation_unavailable"
            current_attempt.failure_source = "temporal_dispatch"
        await db.commit()
        return False
    meeting = await db.scalar(
        select(Meeting)
        .where(Meeting.workspace_id == intent.workspace_id, Meeting.id == intent.meeting_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    current_attempt = await db.scalar(
        select(MeetingOutcomeGenerationAttempt)
        .where(MeetingOutcomeGenerationAttempt.id == attempt.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    current_intent = await db.scalar(
        select(DispatchIntent)
        .where(DispatchIntent.id == intent.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    stale = (
        meeting is None
        or current_intent is None
        or current_attempt is None
        or current_intent.state != "dispatching"
        or current_intent.reconciliation_state != "in_progress"
        or current_intent.lease_expires_at is None
        or current_intent.lease_expires_at <= datetime.now(UTC)
        or current_intent.attempt_count != dispatch_attempt_count
        or current_attempt.status not in {"queued", "generating", "blocked_dependency"}
        or meeting_is_deleted_or_deleting(meeting)
        or int(meeting.deletion_epoch or 0) != int(intent.deletion_epoch or 0)
        or int(current_attempt.deletion_epoch_at_start or 0) != int(intent.deletion_epoch or 0)
        or (
            intent.source_fingerprint is not None
            and intent.source_fingerprint != current_attempt.source_fingerprint
        )
    )
    if stale:
        lifecycle_stale = (
            meeting is None
            or current_attempt is None
            or meeting_is_deleted_or_deleting(meeting)
            or int(meeting.deletion_epoch or 0) != int(intent.deletion_epoch or 0)
            or int(current_attempt.deletion_epoch_at_start or 0)
            != int(intent.deletion_epoch or 0)
            or (
                intent.source_fingerprint is not None
                and intent.source_fingerprint != current_attempt.source_fingerprint
            )
        )
        same_lease_owner = (
            current_intent is not None
            and current_intent.state == "dispatching"
            and current_intent.reconciliation_state == "in_progress"
            and current_intent.attempt_count == dispatch_attempt_count
            and current_intent.lease_expires_at is not None
            and current_intent.lease_expires_at > datetime.now(UTC)
        )
        if same_lease_owner and current_attempt is not None and (
            current_attempt.status in {"queued", "generating", "blocked_dependency"}
            and (
                meeting is None
                or meeting_is_deleted_or_deleting(meeting)
                or int(meeting.deletion_epoch or 0) != int(intent.deletion_epoch or 0)
                or (
                    intent.source_fingerprint is not None
                    and intent.source_fingerprint != current_attempt.source_fingerprint
                )
            )
        ):
            current_intent.state = "cancelled"
            current_intent.reconciliation_state = "cancelled"
            current_intent.lease_expires_at = None
            current_intent.failure_code = "summary_dispatch_stale"
            current_attempt.status = "cancelled"
            current_attempt.failure_code = "summary_dispatch_stale"
            await db.commit()
        else:
            await db.rollback()
        # A lease/attempt mismatch alone means another worker may own the
        # same deterministic provider workflow. Cancel only when the lifecycle
        # fence is stale; never cancel a valid slow start from an old worker.
        if lifecycle_stale:
            await _cancel_started_workflow(temporal_client, started.workflow_id)
        return False
    current_attempt.workflow_id = started.workflow_id
    if started.run_id is not None:
        current_attempt.workflow_run_id = started.run_id
    await mark_dispatch_started(
        db,
        workspace_id=intent.workspace_id,
        idempotency_key=intent.idempotency_key,
        workflow_id=started.workflow_id,
        run_id=started.run_id
        or current_attempt.workflow_run_id
        or (current_intent.external_run_id if current_intent is not None else None),
    )
    await db.commit()
    return True


async def _cancel_started_workflow(temporal_client: object, workflow_id: str) -> None:
    try:
        handle = temporal_client.get_workflow_handle(workflow_id)
        await handle.cancel()
    except Exception:
        # The durable cancellation fence remains authoritative if the provider
        # is unavailable; its retry/reconciliation path can observe the failure.
        return
