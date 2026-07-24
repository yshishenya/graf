from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import func, nullslast, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from twobrain_rec_server.db.models import (
    MediaRevision,
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    ProcessingResult,
    TranscriptSegment,
)
from twobrain_rec_server.domain.statuses import (
    OutcomeCategoryState,
    OutcomeGenerationAttemptStatus,
    OutcomeSetStatus,
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
)
from twobrain_rec_server.ingest.media_revisions import source_fingerprint_for_revision
from twobrain_rec_server.outcomes.generator import generate_outcomes
from twobrain_rec_server.outcomes.models import OutcomeTranscriptSegment
from twobrain_rec_server.outcomes.store import (
    OUTCOME_GENERATOR_VERSION,
    create_outcome_set,
    record_generation_attempt,
    replace_outcome_items,
    set_outcome_category_states,
    should_reuse_outcome_set,
)
from twobrain_rec_server.outcomes.templates import BUILT_IN_BY_KEY
from twobrain_rec_server.processing.fences import (
    is_expired,
    lock_meeting_fence,
    meeting_is_deleted_or_deleting,
)
from twobrain_rec_server.processing.store import ProcessingLifecycleBlocked

BASELINE_TEMPLATE_KEY = "graf-auto-v1"


def _baseline_template_provenance() -> tuple[str, int, str]:
    definition = BUILT_IN_BY_KEY[BASELINE_TEMPLATE_KEY]
    config = {
        "detail_level": "standard",
        "generator_version": OUTCOME_GENERATOR_VERSION,
        "output_language": "ru",
        "sections": list(definition.sections),
        "template_key": definition.key,
        "template_version": definition.version,
    }
    encoded = json.dumps(config, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return definition.key, definition.version, sha256(encoded).hexdigest()


async def ensure_outcomes_for_meeting(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    meeting_id: UUID,
) -> MeetingOutcomeSet | None:
    async with sessionmaker() as db:
        latest_revision = await db.scalar(
            select(MediaRevision)
            .where(
                MediaRevision.meeting_id == meeting_id,
                MediaRevision.status == "accepted",
                MediaRevision.immutable.is_(True),
            )
            .order_by(MediaRevision.revision_number.desc(), MediaRevision.updated_at.desc())
        )
        result_query = select(ProcessingResult).where(
            ProcessingResult.meeting_id == meeting_id,
            ProcessingResult.status == ProcessingResultStatus.IMPORTED.value,
        )
        result_query = result_query.where(
            ProcessingResult.media_revision_id == latest_revision.id
            if latest_revision is not None
            else ProcessingResult.media_revision_id.is_(None)
        )
        result = await db.scalar(
            result_query.order_by(
                ProcessingResult.result_version.desc(),
                nullslast(ProcessingResult.imported_at.desc()),
                ProcessingResult.created_at.desc(),
                ProcessingResult.id.desc(),
            )
        )
        if result is None:
            return None
        outcome_set = await ensure_outcomes_for_processing_result(db, result=result)
        await db.commit()
        return outcome_set


async def ensure_outcomes_for_processing_result(
    db: AsyncSession,
    *,
    result: ProcessingResult,
) -> MeetingOutcomeSet:
    meeting = await lock_meeting_fence(
        db, workspace_id=result.workspace_id, meeting_id=result.meeting_id
    )
    if meeting is None or meeting_is_deleted_or_deleting(meeting):
        raise ProcessingLifecycleBlocked("meeting_deleting")
    # The meeting lock serializes this baseline with revision acceptance. Do
    # not let a result that lost the source race create a new outcome lineage.
    latest_revision = await db.scalar(
        select(MediaRevision)
        .where(
            MediaRevision.workspace_id == result.workspace_id,
            MediaRevision.meeting_id == result.meeting_id,
            MediaRevision.status == "accepted",
            MediaRevision.immutable.is_(True),
        )
        .order_by(MediaRevision.revision_number.desc(), MediaRevision.updated_at.desc())
    )
    if (latest_revision.id if latest_revision is not None else None) != result.media_revision_id:
        raise ProcessingLifecycleBlocked("summary_source_revision_stale")
    latest_result = await db.scalar(
        select(ProcessingResult)
        .where(
            ProcessingResult.workspace_id == result.workspace_id,
            ProcessingResult.meeting_id == result.meeting_id,
            ProcessingResult.media_revision_id == result.media_revision_id,
            ProcessingResult.status == ProcessingResultStatus.IMPORTED.value,
        )
        .order_by(
            ProcessingResult.result_version.desc(),
            nullslast(ProcessingResult.imported_at.desc()),
            ProcessingResult.created_at.desc(),
            ProcessingResult.id.desc(),
        )
    )
    if latest_result is None or latest_result.id != result.id:
        raise ProcessingLifecycleBlocked("summary_source_result_stale")
    if (
        latest_result.source_result_hash is not None
        and result.source_result_hash is not None
        and latest_result.source_result_hash != result.source_result_hash
    ):
        raise ProcessingLifecycleBlocked("summary_source_result_stale")
    if result.source_result_hash is None:
        # Legacy imports predate provider result hashes; bind them once to the
        # immutable result identity so every later candidate has provenance.
        result.source_result_hash = sha256(
            f"legacy-processing-result:{result.id}".encode()
        ).hexdigest()
    template_key, template_version, generator_config_hash = _baseline_template_provenance()
    existing = await _load_current_outcome_set(
        db, result=result, generator_config_hash=generator_config_hash
    )
    initial_trusted_baseline = result.media_revision_id is None
    transcript_is_available = result.transcript_status == ProcessingAvailabilityStatus.AVAILABLE.value and result.segment_count > 0
    if existing is not None and existing.failure_reason == "outcomes_generation_failed":
        # Deterministic baseline failures are terminal. Automatic reopen must
        # not recycle this set without a matching candidate lineage; an owner
        # can request a fresh manual candidate through the candidate API.
        return existing
    existing_is_immutable_history = existing is not None and existing.revision_state in {
        "accepted",
        "superseded",
    }
    if existing is not None and not existing_is_immutable_history:
        existing.template_key = existing.template_key or template_key
        existing.template_version = existing.template_version or template_version
        existing.generator_config_hash = existing.generator_config_hash or generator_config_hash
    if existing is not None and should_reuse_outcome_set(existing, transcript_is_available=transcript_is_available):
        await _accept_initial_outcome_set(db, meeting=meeting, outcome_set=existing)
        return existing
    if existing is not None and existing.revision_state in {"accepted", "superseded"}:
        # Accepted history is immutable; a new processing result gets a new set.
        return existing
    automatic_candidate_id = None if initial_trusted_baseline else uuid4()
    replace_blocked_revision = (
        existing is not None
        and not initial_trusted_baseline
        and transcript_is_available
        and existing.status == OutcomeSetStatus.BLOCKED.value
    )
    expired_existing = existing is not None and (
        is_expired(existing.expires_at) or replace_blocked_revision
    )
    if expired_existing:
        existing.revision_state = "expired"
        expired_at = datetime.now(UTC)
        if replace_blocked_revision:
            existing.expires_at = expired_at
        expired_attempts = (
            await db.scalars(
                select(MeetingOutcomeGenerationAttempt)
                .where(
                    MeetingOutcomeGenerationAttempt.outcome_set_id == existing.id,
                    MeetingOutcomeGenerationAttempt.status.in_(
                        {
                            "queued",
                            "generating",
                            "candidate",
                            "blocked_dependency",
                            "failed_retryable",
                        }
                    ),
                )
                .with_for_update()
            )
        ).all()
        for expired_attempt in expired_attempts:
            expired_attempt.status = OutcomeGenerationAttemptStatus.EXPIRED.value
            expired_attempt.failure_reason = "summary_candidate_expired"
            expired_attempt.failure_code = "summary_candidate_expired"
            expired_attempt.ended_at = expired_at
    started_at = datetime.now(UTC)
    candidate_expires_at = started_at + timedelta(hours=24) if automatic_candidate_id is not None else None
    outcome_set = (None if expired_existing else existing) or await create_outcome_set(
        db,
        workspace_id=result.workspace_id,
        meeting_id=result.meeting_id,
        media_revision_id=result.media_revision_id,
        processing_result_id=result.id,
        candidate_id=automatic_candidate_id,
        source_result_hash=result.source_result_hash,
        source_fingerprint=await _result_source_fingerprint(db, result=result),
        generator_config_hash=generator_config_hash,
        deletion_epoch_at_start=int(meeting.deletion_epoch or 0),
        started_at=started_at,
        expires_at=candidate_expires_at,
    )
    if replace_blocked_revision:
        outcome_set.supersedes_outcome_set_id = existing.id
    outcome_set.status = OutcomeSetStatus.GENERATING.value
    outcome_set.failure_reason = None
    outcome_set.failure_source = None
    outcome_set.started_at = outcome_set.started_at or started_at
    outcome_set.source_result_hash = result.source_result_hash
    outcome_set.template_key = outcome_set.template_key or template_key
    outcome_set.template_version = outcome_set.template_version or template_version
    outcome_set.generator_config_hash = outcome_set.generator_config_hash or generator_config_hash
    if automatic_candidate_id is not None and (
        outcome_set.expires_at is None or is_expired(outcome_set.expires_at)
    ):
        outcome_set.expires_at = candidate_expires_at
        outcome_set.revision_state = "candidate"
    set_outcome_category_states(outcome_set, OutcomeCategoryState.PROCESSING.value)
    if not transcript_is_available:
        failure_reason = result.failure_reason or "outcomes_transcript_unavailable"
        failure_source = result.failure_source
        outcome_set.status = OutcomeSetStatus.BLOCKED.value
        outcome_set.failure_reason = failure_reason
        outcome_set.failure_source = failure_source
        set_outcome_category_states(outcome_set, OutcomeCategoryState.BLOCKED.value)
        await record_generation_attempt(
            db,
            workspace_id=result.workspace_id,
            meeting_id=result.meeting_id,
            media_revision_id=result.media_revision_id,
            processing_result_id=result.id,
            outcome_set_id=outcome_set.id,
            candidate_id=automatic_candidate_id,
            status=OutcomeGenerationAttemptStatus.BLOCKED.value,
            failure_reason=failure_reason,
            failure_source=failure_source,
            idempotency_key=await _next_baseline_attempt_idempotency_key(db, result=result),
            source_result_id=result.id,
            source_result_hash=result.source_result_hash,
            source_fingerprint=outcome_set.source_fingerprint,
            generator_config_hash=generator_config_hash,
            deletion_epoch_at_start=int(meeting.deletion_epoch or 0),
            display_format_name="Базовые итоги",
            template_key=template_key,
            template_version=template_version,
            metadata_json={
                "segment_count": result.segment_count,
                "transcript_status": result.transcript_status,
                "failure_source": failure_source,
            },
        )
        await db.flush()
        return outcome_set

    segments = await _load_transcript_segments(db, result=result)
    try:
        payload = generate_outcomes(segments)
    except Exception:
        ended_at = datetime.now(UTC)
        outcome_set.status = OutcomeSetStatus.BLOCKED.value
        outcome_set.failure_reason = "outcomes_generation_failed"
        outcome_set.failure_source = None
        outcome_set.generated_at = None
        outcome_set.latency_ms = max(0, int((ended_at - started_at).total_seconds() * 1000))
        set_outcome_category_states(outcome_set, OutcomeCategoryState.BLOCKED.value)
        await record_generation_attempt(
            db,
            workspace_id=result.workspace_id,
            meeting_id=result.meeting_id,
            media_revision_id=result.media_revision_id,
            processing_result_id=result.id,
            outcome_set_id=outcome_set.id,
            candidate_id=automatic_candidate_id,
            # The deterministic local generator has no transient dependency to
            # retry. Keep the failure terminal so reopening a meeting cannot
            # loop indefinitely; an operator/manual re-run can create a new
            # outcome lineage after the defect is fixed.
            status=OutcomeGenerationAttemptStatus.FAILED_TERMINAL.value,
            started_at=started_at,
            ended_at=ended_at,
            latency_ms=outcome_set.latency_ms,
            failure_reason="outcomes_generation_failed",
            idempotency_key=await _next_baseline_attempt_idempotency_key(db, result=result),
            source_result_id=result.id,
            source_result_hash=result.source_result_hash,
            source_fingerprint=outcome_set.source_fingerprint,
            generator_config_hash=generator_config_hash,
            deletion_epoch_at_start=int(meeting.deletion_epoch or 0),
            display_format_name="Базовые итоги",
            template_key=template_key,
            template_version=template_version,
            metadata_json={"segment_count": len(segments)},
        )
        await db.flush()
        return outcome_set
    outcome_set.status = OutcomeSetStatus.AVAILABLE.value
    if outcome_set.revision_state is None:
        if initial_trusted_baseline:
            # Legacy imports predate immutable media-revision provenance. Keep
            # their historical auto-publish behavior; every revision-scoped
            # baseline is a candidate until the owner accepts it.
            outcome_set.revision_state = "accepted"
            meeting.current_outcome_set_id = outcome_set.id
        else:
            outcome_set.revision_state = "candidate"
    outcome_set.generated_at = datetime.now(UTC)
    outcome_set.latency_ms = max(0, int((outcome_set.generated_at - started_at).total_seconds() * 1000))
    for category, state in payload.category_states.items():
        setattr(outcome_set, f"{category}_state", state)
    outcome_set.content_hash = _payload_hash(payload.items)
    stored_items = [item.as_store_item() for item in payload.items]
    await replace_outcome_items(db, outcome_set=outcome_set, items=stored_items)
    await record_generation_attempt(
        db,
        workspace_id=result.workspace_id,
        meeting_id=result.meeting_id,
        media_revision_id=result.media_revision_id,
        processing_result_id=result.id,
        outcome_set_id=outcome_set.id,
        status=(
            "candidate" if automatic_candidate_id is not None else OutcomeGenerationAttemptStatus.STORED.value
        ),
        started_at=started_at,
        ended_at=outcome_set.generated_at,
        latency_ms=outcome_set.latency_ms,
        candidate_id=automatic_candidate_id,
        idempotency_key=await _next_baseline_attempt_idempotency_key(db, result=result),
        request_intent="automatic_baseline",
        source_result_id=result.id,
        source_result_hash=result.source_result_hash,
        source_fingerprint=outcome_set.source_fingerprint,
        generator_config_hash=generator_config_hash,
        deletion_epoch_at_start=int(meeting.deletion_epoch or 0),
        expires_at=candidate_expires_at,
        display_format_name="Базовые итоги",
        template_key=template_key,
        template_version=template_version,
        metadata_json={
            "segment_count": len(segments),
            "category_count": len(payload.category_states),
            "item_count": len(stored_items),
        },
    )
    await _accept_initial_outcome_set(db, meeting=meeting, outcome_set=outcome_set)
    await db.flush()
    return outcome_set


async def _accept_initial_outcome_set(
    db: AsyncSession,
    *,
    meeting: Meeting,
    outcome_set: MeetingOutcomeSet,
) -> None:
    if outcome_set.status not in {
        OutcomeSetStatus.AVAILABLE.value,
        OutcomeSetStatus.PARTIAL.value,
    }:
        return
    if (
        meeting.deleted_at is not None
        or meeting.deletion_state not in {None, "none"}
        or meeting.current_outcome_set_id not in {None, outcome_set.id}
        or outcome_set.candidate_id is not None
        or outcome_set.revision_state in {"candidate", "rejected", "stale", "expired"}
    ):
        return
    outcome_set.revision_state = "accepted"
    outcome_set.accepted_at = outcome_set.accepted_at or outcome_set.generated_at or datetime.now(UTC)
    if meeting.current_outcome_set_id is None:
        meeting.current_outcome_set_id = outcome_set.id
    await db.flush()


def _baseline_idempotency_key(result: ProcessingResult) -> str:
    _template_key, _template_version, generator_config_hash = _baseline_template_provenance()
    return ":".join(
        (
            "baseline",
            str(result.meeting_id),
            str(result.media_revision_id or "legacy"),
            str(result.id),
            result.source_result_hash or f"result:{result.id}",
            OUTCOME_GENERATOR_VERSION,
            generator_config_hash,
        )
    )[:240]


async def _next_baseline_attempt_idempotency_key(
    db: AsyncSession,
    *,
    result: ProcessingResult,
) -> str:
    baseline_key = _baseline_idempotency_key(result)
    attempt_count = await db.scalar(
        select(func.count(MeetingOutcomeGenerationAttempt.id)).where(
            MeetingOutcomeGenerationAttempt.workspace_id == result.workspace_id,
            MeetingOutcomeGenerationAttempt.processing_result_id == result.id,
            MeetingOutcomeGenerationAttempt.idempotency_key.like(f"{baseline_key}%"),
        )
    )
    if not attempt_count:
        return baseline_key
    return f"{baseline_key[:220]}:retry:{int(attempt_count)}"


async def _result_source_fingerprint(
    db: AsyncSession,
    *,
    result: ProcessingResult,
) -> str:
    if result.media_revision_id is None:
        return f"result:{result.id}"
    revision = await db.get(MediaRevision, result.media_revision_id)
    if revision is None:
        raise ProcessingLifecycleBlocked("summary_source_revision_unavailable")
    try:
        return source_fingerprint_for_revision(revision)
    except ValueError as exc:
        raise ProcessingLifecycleBlocked("summary_source_revision_unavailable") from exc


async def _load_current_outcome_set(
    db: AsyncSession,
    *,
    result: ProcessingResult,
    generator_config_hash: str | None = None,
) -> MeetingOutcomeSet | None:
    conditions = [
        MeetingOutcomeSet.workspace_id == result.workspace_id,
        MeetingOutcomeSet.meeting_id == result.meeting_id,
        MeetingOutcomeSet.media_revision_id == result.media_revision_id,
        MeetingOutcomeSet.processing_result_id == result.id,
        MeetingOutcomeSet.generator_version == OUTCOME_GENERATOR_VERSION,
    ]
    if generator_config_hash is not None:
        conditions.append(
            (MeetingOutcomeSet.generator_config_hash == generator_config_hash)
            | MeetingOutcomeSet.generator_config_hash.is_(None)
        )
    return await db.scalar(
        select(MeetingOutcomeSet)
        .where(*conditions)
        .order_by(MeetingOutcomeSet.created_at.desc())
    )


async def _load_transcript_segments(
    db: AsyncSession,
    *,
    result: ProcessingResult,
) -> list[OutcomeTranscriptSegment]:
    rows = (
        await db.scalars(
            select(TranscriptSegment)
            .where(
                TranscriptSegment.workspace_id == result.workspace_id,
                TranscriptSegment.meeting_id == result.meeting_id,
                TranscriptSegment.processing_result_id == result.id,
            )
            .order_by(TranscriptSegment.sequence.asc(), TranscriptSegment.start_seconds.asc())
        )
    ).all()
    return [
        OutcomeTranscriptSegment(
            segment_id=row.id,
            sequence=row.sequence,
            start_seconds=row.start_seconds,
            end_seconds=row.end_seconds,
            speaker_label=f"Speaker {row.sequence + 1}",
            source_role=row.source_role,
            text=row.text,
        )
        for row in rows
    ]


def _payload_hash(items: list[object]) -> str:
    payload = "|".join(repr(item) for item in items)
    return sha256(payload.encode("utf-8")).hexdigest()


async def load_outcome_items(
    db: AsyncSession,
    *,
    outcome_set: MeetingOutcomeSet | None,
) -> list[MeetingOutcomeItem]:
    if outcome_set is None:
        return []
    return (
        await db.scalars(
            select(MeetingOutcomeItem)
            .where(MeetingOutcomeItem.outcome_set_id == outcome_set.id)
            .order_by(MeetingOutcomeItem.category.asc(), MeetingOutcomeItem.sequence.asc())
        )
    ).all()
