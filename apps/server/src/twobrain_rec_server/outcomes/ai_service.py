from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, nullslast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from twobrain_rec_server.cabinet.speakers import (
    candidate_speaker_attribution_is_current,
    speaker_attribution_revision,
)
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    DispatchIntent,
    GenerationCall,
    MediaRevision,
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    MeetingSummarySlot,
    ProcessingResult,
    SummaryTemplate,
    Workspace,
)
from twobrain_rec_server.db.tenant_context import TenantDatabaseContext, apply_tenant_context
from twobrain_rec_server.domain.speaker_turns import canonical_speech_available
from twobrain_rec_server.domain.statuses import ProcessingResultStatus
from twobrain_rec_server.ingest.media_revisions import source_fingerprint_for_revision
from twobrain_rec_server.observability.langfuse import (
    GenerationTraceContext,
    create_langfuse_client,
    deterministic_observation_id,
    deterministic_trace_id,
    fetch_production_prompt,
    publish_completed_generation,
    shutdown_langfuse,
)
from twobrain_rec_server.outcomes.dispatch import (
    ensure_dispatch_intent,
    finalize_dispatch_for_candidate,
)
from twobrain_rec_server.outcomes.generator import (
    LiteLLMError,
    LiteLLMGateway,
    canonical_transcript,
    compile_prompt_messages,
)
from twobrain_rec_server.outcomes.models import OutcomeSourceReference, OutcomeTranscriptSegment
from twobrain_rec_server.outcomes.prompt_optimization import (
    PromptOptimizationError,
    load_verified_promoted_snapshot,
    persist_verified_promoted_snapshot,
)
from twobrain_rec_server.outcomes.prompts import (
    PromptSnapshot,
    canonical_json,
    validate_outcome_result,
    validate_prompt_snapshot,
)
from twobrain_rec_server.outcomes.service import (
    ensure_summary_slot,
    load_outcome_transcript_segments,
)
from twobrain_rec_server.outcomes.store import set_outcome_category_states
from twobrain_rec_server.outcomes.templates import (
    OUTCOME_CATEGORIES,
    built_in_template_for_version,
    prompt_name_for_template,
)
from twobrain_rec_server.processing.fences import (
    is_expired,
    lock_meeting_fence,
    meeting_is_deleted_or_deleting,
    normalize_db_timestamp,
)
from twobrain_rec_server.storage.minio_client import get_storage
from twobrain_rec_server.workflows.outcome_generation_workflow import (
    TranscriptSnapshotError,
    split_plaintext_transcript,
)
from twobrain_rec_server.workflows.temporal_client import outcome_generation_workflow_id

AI_GENERATOR_VERSION = "outcomes-ai-v1"
ZERO_UUID = UUID(int=0)
_ACTIVE_CANDIDATE_STATUSES = ("queued", "generating", "blocked_dependency")
_RETRYABLE_CANDIDATE_FAILURES = frozenset(
    {
        "summary_dispatch_retries_exhausted",
        "summary_generation_retries_exhausted",
        "summary_generation_unavailable",
        "langfuse_prompt_unavailable",
        "prompt_snapshot_export_unavailable",
        "litellm_endpoint_unavailable",
        "litellm_unavailable",
        "litellm_retryable_response",
    }
)
ACTIVE_CANDIDATE_STATUSES = {"queued", "generating", "blocked_dependency"}
EXPORT_CLAIM_STALE_AFTER = timedelta(minutes=5)


class OutcomeGenerationTerminalError(RuntimeError):
    pass


class OutcomeGenerationDependencyError(RuntimeError):
    pass


class SummarySlotCASConflict(OutcomeGenerationTerminalError):
    """The requested replacement no longer matches the fenced slot state."""

    def __init__(self, reason: str = "summary_slot_conflict") -> None:
        super().__init__(reason)
        self.reason = reason


async def publish_model_generated_outcome(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    candidate_id: UUID,
    expected_current_outcome_set_id: UUID | None,
    publication_proof: object | None = None,
) -> MeetingOutcomeSet:
    """Own the only model-publication boundary.

    Feature 183 intentionally has no receipt, canonical-artifact, calibration,
    or presentation proof that can authorize publication. Feature 195 extends
    this function in place; it must not add a second publisher. Keeping the
    denial before any database access also makes a missing proof incapable of
    changing a slot, candidate visibility, or dispatch state.
    """

    del db, workspace_id, meeting_id, candidate_id, expected_current_outcome_set_id
    del publication_proof
    raise OutcomeGenerationTerminalError("verified_runtime_unavailable")


def _expire_candidate_attempt(
    attempt: MeetingOutcomeGenerationAttempt,
    *,
    ended_at: datetime | None = None,
) -> None:
    attempt.status = "expired"
    attempt.failure_code = "summary_candidate_expired"
    attempt.failure_reason = "summary_candidate_expired"
    attempt.ended_at = ended_at or datetime.now(UTC)


async def _expire_attempt_projection(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    attempt: MeetingOutcomeGenerationAttempt,
    ended_at: datetime,
) -> None:
    _expire_candidate_attempt(attempt, ended_at=ended_at)
    if attempt.candidate_id is not None:
        await finalize_dispatch_for_candidate(
            db,
            workspace_id=workspace_id,
            candidate_id=attempt.candidate_id,
            outcome="cancelled",
            failure_code="summary_candidate_expired",
        )
    if attempt.outcome_set_id is None:
        return
    outcome_set = await db.scalar(
        select(MeetingOutcomeSet)
        .where(
            MeetingOutcomeSet.workspace_id == workspace_id,
            MeetingOutcomeSet.id == attempt.outcome_set_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if outcome_set is not None and outcome_set.revision_state == "candidate":
        outcome_set.revision_state = "expired"


async def create_summary_candidate(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    requested_by_user_id: UUID,
    template_key: str,
    template_id: UUID | None,
    template_version: int,
    expected_current_outcome_set_id: UUID | None,
    request_intent: str = "automatic_baseline",
    request_intent_id: UUID | None = None,
) -> MeetingOutcomeGenerationAttempt:
    meeting = await lock_meeting_fence(db, workspace_id=workspace_id, meeting_id=meeting_id)
    if meeting is None:
        raise OutcomeGenerationTerminalError("meeting_not_found")
    if meeting_is_deleted_or_deleting(meeting):
        raise OutcomeGenerationTerminalError("meeting_deleting")
    slot = await ensure_summary_slot(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        template_key=template_key,
    )
    if slot.current_outcome_set_id != expected_current_outcome_set_id:
        raise OutcomeGenerationTerminalError("summary_revision_conflict")
    current_outcome_set_id = slot.current_outcome_set_id
    latest_revision = await db.scalar(
        select(MediaRevision)
        .where(
            MediaRevision.workspace_id == workspace_id,
            MediaRevision.meeting_id == meeting_id,
            MediaRevision.status == "accepted",
            MediaRevision.immutable.is_(True),
        )
        .order_by(MediaRevision.revision_number.desc(), MediaRevision.updated_at.desc())
    )
    result_query = select(ProcessingResult).where(
        ProcessingResult.workspace_id == workspace_id,
        ProcessingResult.meeting_id == meeting_id,
        ProcessingResult.status == ProcessingResultStatus.IMPORTED.value,
    )
    if latest_revision is not None:
        result_query = result_query.where(ProcessingResult.media_revision_id == latest_revision.id)
    else:
        result_query = result_query.where(ProcessingResult.media_revision_id.is_(None))
    result = await db.scalar(
        result_query.order_by(
            ProcessingResult.result_version.desc(),
            nullslast(ProcessingResult.imported_at.desc()),
            ProcessingResult.created_at.desc(),
            ProcessingResult.id.desc(),
        )
    )
    if not canonical_speech_available(result):
        raise OutcomeGenerationTerminalError("summary_transcript_unavailable")
    if result.source_result_hash is None:
        raise OutcomeGenerationTerminalError("summary_source_revision_unavailable")
    source_fingerprint = f"result:{result.id}"
    if latest_revision is not None:
        try:
            source_fingerprint = source_fingerprint_for_revision(latest_revision)
        except ValueError as exc:
            raise OutcomeGenerationTerminalError("summary_source_revision_unavailable") from exc
    speaker_revision = await speaker_attribution_revision(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
    )
    template: SummaryTemplate | None = None
    if template_id is not None:
        template = await db.scalar(
            select(SummaryTemplate).where(
                SummaryTemplate.id == template_id,
                SummaryTemplate.workspace_id == workspace_id,
                SummaryTemplate.owner_user_id == requested_by_user_id,
                SummaryTemplate.template_key == template_key,
                SummaryTemplate.version == template_version,
            )
        )
        if template is None:
            raise OutcomeGenerationTerminalError("summary_template_unavailable")
        prompt_name = prompt_name_for_template(template_key, built_in=False)
        output_language = template.output_language
        detail_level = template.detail_level
        template_sections = tuple(str(section) for section in template.sections_json)
    else:
        definition = built_in_template_for_version(template_key, template_version)
        if definition is None:
            raise OutcomeGenerationTerminalError("summary_template_unavailable")
        prompt_name = definition.prompt_name
        output_language = "ru"
        detail_level = "standard"
        template_sections = definition.sections
    if request_intent == "manual_refresh" and request_intent_id is None:
        raise OutcomeGenerationTerminalError("summary_refresh_intent_missing")
    if request_intent == "manual_format" and request_intent_id is not None:
        raise OutcomeGenerationTerminalError("summary_refresh_intent_invalid")
    # ponytail: request-time dedupe uses durable local inputs only; the worker
    # pins the verified remote prompt/model snapshot before any provider call.
    # A deployment never rekeys an active attempt; manual_refresh carries a
    # unique intent when the owner explicitly wants the new configuration.
    generator_config_hash = _ai_generator_config_hash(
        template_id=template_id,
        template_key=template_key,
        template_version=template_version,
        template_sections=template_sections,
        output_language=output_language,
        detail_level=detail_level,
        prompt_name=prompt_name,
    )
    idempotency_key = _candidate_idempotency_key(
        meeting_id=meeting_id,
        result=result,
        template_key=template_key,
        template_version=template_version,
        requested_by_user_id=requested_by_user_id,
        request_intent=request_intent,
        request_intent_id=request_intent_id,
        generator_config_hash=generator_config_hash,
        speaker_attribution_revision=speaker_revision,
    )
    base_idempotency_key = idempotency_key
    retry_prefix = f"{base_idempotency_key[:190]}:retry:"
    key_lineage = or_(
        MeetingOutcomeGenerationAttempt.idempotency_key == base_idempotency_key,
        MeetingOutcomeGenerationAttempt.idempotency_key.like(f"{retry_prefix}%"),
    )
    now = datetime.now(UTC)
    # Request idempotency is keyed by the exact durable request identity.  A
    # terminal attempt is still the answer to a replay of that request; it is
    # never rewritten or replaced with an implicit ``:retry:`` candidate.
    exact_attempt = await db.scalar(
        select(MeetingOutcomeGenerationAttempt)
        .where(
            MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
            MeetingOutcomeGenerationAttempt.idempotency_key == base_idempotency_key,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    superseded_accepted = False
    if exact_attempt is not None:
        superseded_accepted = request_intent == "manual_format" and (
            exact_attempt.status == "accepted"
            and exact_attempt.outcome_set_id != current_outcome_set_id
        )
        if not superseded_accepted and (
            exact_attempt.status in ACTIVE_CANDIDATE_STATUSES | {"candidate"}
            and is_expired(exact_attempt.expires_at, now=now)
        ):
            await _expire_attempt_projection(
                db,
                workspace_id=workspace_id,
                attempt=exact_attempt,
                ended_at=now,
            )
        if not superseded_accepted and not (
            exact_attempt.status == "failed"
            and exact_attempt.failure_code in _RETRYABLE_CANDIDATE_FAILURES
        ):
            return exact_attempt
    if request_intent == "automatic_baseline":
        accepted_automatic = await db.scalar(
            select(MeetingOutcomeGenerationAttempt)
            .where(
                MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
                MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
                MeetingOutcomeGenerationAttempt.processing_result_id == result.id,
                MeetingOutcomeGenerationAttempt.source_result_id == result.id,
                MeetingOutcomeGenerationAttempt.media_revision_id == result.media_revision_id,
                MeetingOutcomeGenerationAttempt.template_id == template_id,
                MeetingOutcomeGenerationAttempt.template_key == template_key,
                MeetingOutcomeGenerationAttempt.template_version == template_version,
                MeetingOutcomeGenerationAttempt.generator_version == AI_GENERATOR_VERSION,
                MeetingOutcomeGenerationAttempt.source_result_hash == result.source_result_hash,
                MeetingOutcomeGenerationAttempt.source_fingerprint == source_fingerprint,
                MeetingOutcomeGenerationAttempt.request_intent == "automatic_baseline",
                MeetingOutcomeGenerationAttempt.status == "accepted",
            )
            .order_by(MeetingOutcomeGenerationAttempt.created_at.desc())
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if accepted_automatic is not None and accepted_automatic.outcome_set_id == current_outcome_set_id:
            return accepted_automatic
    if template is not None and template.status != "active":
        # Archived/deleted templates remain valid only for an exact replay of
        # their pinned candidate; they cannot start a new intent, even when a
        # prior attempt is still queued.
        raise OutcomeGenerationTerminalError("summary_template_unavailable")
    speaker_stale_attempts = (
        await db.scalars(
            select(MeetingOutcomeGenerationAttempt)
            .where(
                MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
                MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
                MeetingOutcomeGenerationAttempt.processing_result_id == result.id,
                MeetingOutcomeGenerationAttempt.candidate_id.is_not(None),
                MeetingOutcomeGenerationAttempt.status.in_(
                    ACTIVE_CANDIDATE_STATUSES | {"candidate"}
                ),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()
    for stale_attempt in speaker_stale_attempts:
        if (stale_attempt.metadata_json or {}).get(
            "speaker_attribution_revision"
        ) == speaker_revision:
            continue
        stale_attempt.status = "stale"
        stale_attempt.failure_code = "summary_source_revision_stale"
        stale_attempt.failure_reason = "summary_source_revision_stale"
        stale_attempt.ended_at = now
        if stale_attempt.candidate_id is not None:
            await finalize_dispatch_for_candidate(
                db,
                workspace_id=workspace_id,
                candidate_id=stale_attempt.candidate_id,
                outcome="cancelled",
                failure_code="summary_source_revision_stale",
            )
        if stale_attempt.outcome_set_id is None:
            continue
        stale_outcome = await db.scalar(
            select(MeetingOutcomeSet)
            .where(
                MeetingOutcomeSet.workspace_id == workspace_id,
                MeetingOutcomeSet.id == stale_attempt.outcome_set_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if stale_outcome is not None and stale_outcome.revision_state == "candidate":
            stale_outcome.revision_state = "stale"
    active_identity = [
        MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
        MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
        MeetingOutcomeGenerationAttempt.processing_result_id == result.id,
        MeetingOutcomeGenerationAttempt.source_result_id == result.id,
        MeetingOutcomeGenerationAttempt.media_revision_id == result.media_revision_id,
        MeetingOutcomeGenerationAttempt.template_id == template_id,
        MeetingOutcomeGenerationAttempt.template_key == template_key,
        MeetingOutcomeGenerationAttempt.template_version == template_version,
        MeetingOutcomeGenerationAttempt.generator_version == AI_GENERATOR_VERSION,
        MeetingOutcomeGenerationAttempt.source_result_hash == result.source_result_hash,
        MeetingOutcomeGenerationAttempt.source_fingerprint == source_fingerprint,
    ]
    expired_active_attempts = (
        await db.scalars(
            select(MeetingOutcomeGenerationAttempt)
            .where(
                *active_identity,
                MeetingOutcomeGenerationAttempt.status.in_(ACTIVE_CANDIDATE_STATUSES),
                MeetingOutcomeGenerationAttempt.expires_at.is_not(None),
                MeetingOutcomeGenerationAttempt.expires_at <= now,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()
    for expired_attempt in expired_active_attempts:
        await _expire_attempt_projection(
            db,
            workspace_id=workspace_id,
            attempt=expired_attempt,
            ended_at=now,
        )
    # A refresh request gets a new intent id. If equivalent work is already
    # active, reuse it before checking the caller's stale pointer; otherwise a
    # polling retry can enqueue a second paid provider job. The worker may pin
    # a remote prompt/model snapshot after this request, so the mutable
    # ``generator_config_hash`` is provenance, not an active-row lookup key.
    active_equivalent = await db.scalar(
        select(MeetingOutcomeGenerationAttempt)
        .where(
            *active_identity,
            MeetingOutcomeGenerationAttempt.status.in_(ACTIVE_CANDIDATE_STATUSES),
            or_(
                MeetingOutcomeGenerationAttempt.expires_at.is_(None),
                MeetingOutcomeGenerationAttempt.expires_at > now,
            ),
        )
        .order_by(MeetingOutcomeGenerationAttempt.created_at.desc())
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if active_equivalent is not None:
        if active_equivalent.status != "blocked_dependency":
            return active_equivalent
        active_dispatch = await db.scalar(
            select(DispatchIntent).where(
                DispatchIntent.workspace_id == workspace_id,
                DispatchIntent.idempotency_key == active_equivalent.idempotency_key,
            )
        )
        if active_dispatch is None or active_dispatch.state != "terminal_failed":
            return active_equivalent
    other_active_attempts = (
        await db.scalars(
            select(MeetingOutcomeGenerationAttempt)
            .where(
                MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
                MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
                MeetingOutcomeGenerationAttempt.candidate_id.is_not(None),
                MeetingOutcomeGenerationAttempt.processing_result_id == result.id,
                MeetingOutcomeGenerationAttempt.status.in_(ACTIVE_CANDIDATE_STATUSES),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()
    for other_attempt in other_active_attempts:
        if is_expired(other_attempt.expires_at, now=now):
            await _expire_attempt_projection(
                db,
                workspace_id=workspace_id,
                attempt=other_attempt,
                ended_at=now,
            )
            continue
        same_template = (
            other_attempt.template_id == template_id
            and other_attempt.template_key == template_key
            and other_attempt.template_version == template_version
        )
        if same_template:
            continue
        other_dispatch = await db.scalar(
            select(DispatchIntent).where(
                DispatchIntent.workspace_id == workspace_id,
                DispatchIntent.candidate_id == other_attempt.candidate_id,
            )
        )
        if other_dispatch is None or other_dispatch.state != "terminal_failed":
            raise OutcomeGenerationTerminalError("summary_generation_in_progress")
    if request_intent == "manual_format" and current_outcome_set_id is not None:
        current_outcome = await db.scalar(
            select(MeetingOutcomeSet).where(
                MeetingOutcomeSet.workspace_id == workspace_id,
                MeetingOutcomeSet.meeting_id == meeting_id,
                MeetingOutcomeSet.id == current_outcome_set_id,
            )
        )
        if (
            current_outcome is not None
            and current_outcome.processing_result_id == result.id
            and current_outcome.revision_state == "accepted"
            and current_outcome.status in {"available", "partial"}
            and (current_outcome.template_key or "graf-auto-v1") == template_key
            and (current_outcome.template_version or 1) == template_version
            and current_outcome.template_id == template_id
        ):
            raise OutcomeGenerationTerminalError("summary_same_format_noop")
    durable_reuse_conditions = [
        (
            (MeetingOutcomeGenerationAttempt.status == "candidate")
            & (
                MeetingOutcomeGenerationAttempt.expires_at.is_(None)
                | (MeetingOutcomeGenerationAttempt.expires_at > now)
            )
        )
    ]
    if request_intent != "manual_refresh":
        durable_reuse_conditions.append(
            (MeetingOutcomeGenerationAttempt.status == "accepted")
            & (MeetingOutcomeGenerationAttempt.outcome_set_id == current_outcome_set_id)
        )
    durable_reusable = await db.scalar(
        select(MeetingOutcomeGenerationAttempt)
        .where(
            *active_identity,
            or_(*durable_reuse_conditions),
        )
        .order_by(MeetingOutcomeGenerationAttempt.created_at.desc())
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if durable_reusable is not None:
        return durable_reusable
    reusable_conditions = [
        MeetingOutcomeGenerationAttempt.status.in_({"queued", "generating"}),
        (
            (MeetingOutcomeGenerationAttempt.status == "candidate")
            & (
                MeetingOutcomeGenerationAttempt.expires_at.is_(None)
                | (MeetingOutcomeGenerationAttempt.expires_at > now)
            )
        ),
    ]
    if request_intent != "manual_refresh":
        reusable_conditions.append(
            (MeetingOutcomeGenerationAttempt.status == "accepted")
            & (MeetingOutcomeGenerationAttempt.outcome_set_id == current_outcome_set_id)
        )
    reusable = await db.scalar(
        select(MeetingOutcomeGenerationAttempt)
        .where(
            MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
            key_lineage,
            or_(*reusable_conditions),
        )
        .order_by(MeetingOutcomeGenerationAttempt.created_at.desc())
    )
    if reusable is not None:
        return reusable
    blocked_attempt = await db.scalar(
        select(MeetingOutcomeGenerationAttempt)
        .where(
            MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
            key_lineage,
            MeetingOutcomeGenerationAttempt.status == "blocked_dependency",
        )
        .order_by(MeetingOutcomeGenerationAttempt.created_at.desc())
    )
    if blocked_attempt is not None:
        dispatch_intent = await db.scalar(
            select(DispatchIntent).where(
                DispatchIntent.workspace_id == workspace_id,
                DispatchIntent.idempotency_key == blocked_attempt.idempotency_key,
            )
        )
        if dispatch_intent is None or dispatch_intent.state != "terminal_failed":
            return blocked_attempt
    expired_attempts = (
        await db.scalars(
            select(MeetingOutcomeGenerationAttempt)
            .where(
                MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
                key_lineage,
                MeetingOutcomeGenerationAttempt.status == "candidate",
                MeetingOutcomeGenerationAttempt.expires_at.is_not(None),
                MeetingOutcomeGenerationAttempt.expires_at <= now,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()
    for expired_attempt in expired_attempts:
        await _expire_attempt_projection(
            db,
            workspace_id=workspace_id,
            attempt=expired_attempt,
            ended_at=now,
        )
    previous_attempt = await db.scalar(
        select(MeetingOutcomeGenerationAttempt)
        .where(
            MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
            key_lineage,
            and_(
                or_(
                    MeetingOutcomeGenerationAttempt.status != "accepted",
                    MeetingOutcomeGenerationAttempt.outcome_set_id
                    == current_outcome_set_id,
                ),
                or_(
                    MeetingOutcomeGenerationAttempt.status != "failed",
                    MeetingOutcomeGenerationAttempt.failure_code.is_(None),
                    ~MeetingOutcomeGenerationAttempt.failure_code.in_(
                        _RETRYABLE_CANDIDATE_FAILURES
                    ),
                ),
            ),
        )
        .order_by(MeetingOutcomeGenerationAttempt.created_at.desc())
    )
    if previous_attempt is not None:
        # Compatibility for attempts created by the previous lineage scheme:
        # replay the latest existing attempt instead of creating another implicit
        # retry key. New explicit refreshes derive a different base key.
        return previous_attempt
    retryable_failed_attempts = (
        await db.scalars(
            select(MeetingOutcomeGenerationAttempt)
            .where(
                MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
                MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
                MeetingOutcomeGenerationAttempt.candidate_id.is_not(None),
                MeetingOutcomeGenerationAttempt.processing_result_id == result.id,
                MeetingOutcomeGenerationAttempt.media_revision_id == result.media_revision_id,
                MeetingOutcomeGenerationAttempt.generator_version == AI_GENERATOR_VERSION,
                MeetingOutcomeGenerationAttempt.source_result_hash == result.source_result_hash,
                MeetingOutcomeGenerationAttempt.source_fingerprint == source_fingerprint,
                MeetingOutcomeGenerationAttempt.template_id == template_id,
                MeetingOutcomeGenerationAttempt.template_key == template_key,
                MeetingOutcomeGenerationAttempt.template_version == template_version,
                MeetingOutcomeGenerationAttempt.outcome_set_id.is_(None),
                MeetingOutcomeGenerationAttempt.status == "failed",
                MeetingOutcomeGenerationAttempt.failure_code.in_(_RETRYABLE_CANDIDATE_FAILURES),
            )
            .order_by(MeetingOutcomeGenerationAttempt.created_at.desc())
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).all()
    retryable_failed_attempt = next(
        (
            attempt
            for attempt in retryable_failed_attempts
            if (attempt.metadata_json or {}).get("speaker_attribution_revision") == speaker_revision
        ),
        None,
    )
    if retryable_failed_attempt is not None:
        retryable_failed_attempt.status = "queued"
        retryable_failed_attempt.failure_code = None
        retryable_failed_attempt.failure_source = None
        retryable_failed_attempt.failure_reason = None
        retryable_failed_attempt.ended_at = None
        retryable_failed_attempt.workflow_run_id = None
        retryable_failed_attempt.expires_at = now + timedelta(hours=24)
        retryable_failed_attempt.request_intent = request_intent
        retryable_failed_attempt.idempotency_key = f"{base_idempotency_key}:retry:{uuid4().hex}"
        metadata = dict(retryable_failed_attempt.metadata_json or {})
        metadata["speaker_attribution_revision"] = speaker_revision
        if request_intent_id is not None:
            metadata["request_intent_id"] = str(request_intent_id)
        retryable_failed_attempt.metadata_json = metadata
        await db.flush()
        return retryable_failed_attempt
    candidate_idempotency_key = idempotency_key
    if superseded_accepted or (
        exact_attempt is not None
        and exact_attempt.status == "failed"
        and exact_attempt.failure_code in _RETRYABLE_CANDIDATE_FAILURES
    ):
        # Preserve the old audit row and make the replacement a distinct
        # durable lineage instead of colliding with the idempotency constraint.
        candidate_idempotency_key = f"{idempotency_key}:retry:{uuid4().hex}"
    candidate_id = uuid4()
    attempt = MeetingOutcomeGenerationAttempt(
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=result.media_revision_id,
        processing_result_id=result.id,
        source_result_id=result.id,
        status="queued",
        provider_kind="litellm",
        generator_version=AI_GENERATOR_VERSION,
        generator_config_hash=generator_config_hash,
        candidate_id=candidate_id,
        idempotency_key=candidate_idempotency_key,
        request_intent=request_intent,
        source_result_hash=result.source_result_hash,
        source_fingerprint=source_fingerprint,
        deletion_epoch_at_start=int(meeting.deletion_epoch or 0),
        expires_at=now + timedelta(hours=24),
        display_format_name=template.name if template is not None else definition.name,
        template_id=template_id,
        template_key=template_key,
        template_version=template_version,
        output_language=output_language,
        detail_level=detail_level,
        requested_by_user_id=requested_by_user_id,
        prompt_name=prompt_name,
        workflow_id=outcome_generation_workflow_id(candidate_id),
        langfuse_trace_id=deterministic_trace_id(candidate_id),
        attempt_count=0,
        metadata_json={
            "template_sections": list(template_sections),
            "speaker_attribution_revision": speaker_revision,
            **(
                {"request_intent_id": str(request_intent_id)}
                if request_intent_id is not None
                else {}
            ),
        },
    )
    db.add(attempt)
    await db.flush()
    return attempt


async def ensure_automatic_summary_candidate(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> MeetingOutcomeGenerationAttempt | None:
    workspace = await db.get(Workspace, workspace_id)
    meeting = await db.get(Meeting, meeting_id)
    if (
        workspace is None
        or meeting is None
        or meeting_is_deleted_or_deleting(meeting)
        or workspace.default_summary_template_id is not None
    ):
        return None
    definition = built_in_template_for_version(
        workspace.default_summary_template_key,
        workspace.default_summary_template_version,
    )
    if definition is None:
        return None
    slot = await ensure_summary_slot(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        template_key=definition.key,
    )
    try:
        attempt = await create_summary_candidate(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            requested_by_user_id=meeting.created_by_user_id,
            template_key=definition.key,
            template_id=None,
            template_version=definition.version,
            expected_current_outcome_set_id=slot.current_outcome_set_id,
        )
    except OutcomeGenerationTerminalError:
        return None
    if attempt.candidate_id is None:
        return None
    await ensure_dispatch_intent(
        db,
        workspace_id=workspace_id,
        meeting=meeting,
        candidate_id=attempt.candidate_id,
        idempotency_key=attempt.idempotency_key or f"candidate:{attempt.candidate_id}",
        source_fingerprint=attempt.source_fingerprint,
        payload={
            "candidate_id": str(attempt.candidate_id),
            "source_result_id": str(attempt.source_result_id),
            "template_key": attempt.template_key,
            "template_version": attempt.template_version,
        },
    )
    terminal_outcome = {
        "candidate": "completed",
        "accepted": "completed",
        "failed": "failed",
        "rejected": "cancelled",
        "cancelled": "cancelled",
        "stale": "cancelled",
        "expired": "cancelled",
    }.get(attempt.status)
    if terminal_outcome is not None:
        await finalize_dispatch_for_candidate(
            db,
            workspace_id=workspace_id,
            candidate_id=attempt.candidate_id,
            outcome=terminal_outcome,
            failure_code=attempt.failure_code,
        )
    return attempt


def _candidate_idempotency_key(
    *,
    meeting_id: UUID,
    result: ProcessingResult,
    template_key: str,
    template_version: int,
    requested_by_user_id: UUID,
    request_intent: str,
    request_intent_id: UUID | None = None,
    generator_config_hash: str,
    speaker_attribution_revision: str,
) -> str:
    source_hash = result.source_result_hash or f"result:{result.id}"
    actor = str(requested_by_user_id) if request_intent.startswith("manual") else "system"
    identity = canonical_json(
        {
            "meeting_id": str(meeting_id),
            "media_revision_id": str(result.media_revision_id or "legacy"),
            # A provider retry can legitimately create a second imported row
            # with the same content hash. Bind the candidate request to the
            # durable result row so that lineage cannot reuse the old attempt.
            "source_result_id": str(result.id),
            "source_hash": source_hash,
            "template_key": template_key,
            "template_version": template_version,
            "generator_config_hash": generator_config_hash,
            "speaker_attribution_revision": speaker_attribution_revision,
            "actor": actor,
            "request_intent": request_intent,
            "request_intent_id": (
                str(request_intent_id) if request_intent == "manual_refresh" else None
            ),
        }
    )
    return f"summary:{sha256(identity.encode('utf-8')).hexdigest()}"


async def resolve_candidate_prompt(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    settings: Settings,
    workspace_id: UUID,
    candidate_id: UUID,
) -> dict[str, Any]:
    async with sessionmaker() as db:
        await _apply_worker_workspace(db, workspace_id)
        attempt = await _candidate_attempt(db, workspace_id, candidate_id)
        attempt = await _ensure_candidate_source_or_mark_stale(db, attempt)
        if attempt.prompt_name is None:
            raise OutcomeGenerationTerminalError("summary_prompt_not_selected")
        try:
            stored = _stored_prompt_snapshot(attempt)
        except ValueError as exc:
            raise OutcomeGenerationTerminalError("summary_prompt_snapshot_corrupt") from exc
        if stored is not None:
            attempt.generator_config_hash = _ai_generator_config_hash(
                template_id=attempt.template_id,
                template_key=attempt.template_key,
                template_version=attempt.template_version,
                template_sections=_template_sections(attempt),
                output_language=attempt.output_language,
                detail_level=attempt.detail_level,
                snapshot=stored,
            )
            await db.commit()
            return _prompt_result(stored)
        prompt_name = attempt.prompt_name
    client = create_langfuse_client(settings)
    try:
        try:
            remote = await asyncio.to_thread(
                fetch_production_prompt,
                client,
                name=prompt_name,
                prompt_type="chat",
            )
        except Exception:
            async with sessionmaker() as guard_db:
                await _apply_worker_workspace(guard_db, workspace_id)
                guard_attempt = await _candidate_attempt(guard_db, workspace_id, candidate_id)
                guard_attempt = await _ensure_candidate_source_or_mark_stale(
                    guard_db, guard_attempt
                )
            try:
                snapshot = await asyncio.to_thread(
                    load_verified_promoted_snapshot,
                    get_storage(settings),
                    prompt_name=prompt_name,
                )
            except (PromptOptimizationError, ValueError) as fallback_exc:
                raise OutcomeGenerationTerminalError(
                    "summary_prompt_snapshot_corrupt"
                ) from fallback_exc
            except Exception as fallback_exc:
                raise OutcomeGenerationDependencyError(
                    "langfuse_prompt_unavailable"
                ) from fallback_exc
            async with sessionmaker() as guard_db:
                await _apply_worker_workspace(guard_db, workspace_id)
                guard_attempt = await _candidate_attempt(guard_db, workspace_id, candidate_id)
                guard_attempt = await _ensure_candidate_source_or_mark_stale(
                    guard_db, guard_attempt
                )
        else:
            try:
                snapshot = validate_prompt_snapshot(
                    name=prompt_name,
                    version=int(remote.version),
                    prompt_type="chat",
                    prompt=remote.prompt,
                    config=remote.config or {},
                    source="langfuse_production",
                )
            except ValueError as exc:
                raise OutcomeGenerationTerminalError("summary_prompt_snapshot_invalid") from exc
            try:
                async with sessionmaker() as guard_db:
                    await _apply_worker_workspace(guard_db, workspace_id)
                    guard_attempt = await _candidate_attempt(guard_db, workspace_id, candidate_id)
                    guard_attempt = await _ensure_candidate_source_or_mark_stale(
                        guard_db, guard_attempt
                    )
                await asyncio.to_thread(
                    persist_verified_promoted_snapshot,
                    get_storage(settings),
                    snapshot,
                )
            except Exception as exc:
                raise OutcomeGenerationDependencyError(
                    "prompt_snapshot_export_unavailable"
                ) from exc
    finally:
        shutdown_langfuse(client)
    async with sessionmaker() as db:
        await _apply_worker_workspace(db, workspace_id)
        _, attempt = await _lock_candidate_meeting_and_attempt(
            db,
            workspace_id=workspace_id,
            candidate_id=candidate_id,
        )
        attempt = await _ensure_candidate_source_or_mark_stale(db, attempt)
        concurrent = _stored_prompt_snapshot(attempt)
        if concurrent is not None:
            if concurrent.canonical_hash != snapshot.canonical_hash:
                raise OutcomeGenerationTerminalError("summary_prompt_resolution_conflict")
            attempt.generator_config_hash = _ai_generator_config_hash(
                template_id=attempt.template_id,
                template_key=attempt.template_key,
                template_version=attempt.template_version,
                template_sections=_template_sections(attempt),
                output_language=attempt.output_language,
                detail_level=attempt.detail_level,
                snapshot=concurrent,
            )
            await db.commit()
            return _prompt_result(concurrent)
        attempt.prompt_version = snapshot.version
        attempt.prompt_source = snapshot.source
        attempt.prompt_definition = snapshot.prompt
        attempt.prompt_config = snapshot.config
        attempt.prompt_hash = snapshot.canonical_hash
        attempt.output_schema_version = str(
            snapshot.config["response_format"]["json_schema"]["name"]
        )
        attempt.model_route = snapshot.model
        attempt.model_parameters = {
            "temperature": snapshot.config["temperature"],
            "response_format": snapshot.config["response_format"],
        }
        attempt.generator_config_hash = _ai_generator_config_hash(
            template_id=attempt.template_id,
            template_key=attempt.template_key,
            template_version=attempt.template_version,
            template_sections=_template_sections(attempt),
            output_language=attempt.output_language,
            detail_level=attempt.detail_level,
            snapshot=snapshot,
        )
        attempt.status = "generating"
        await db.commit()
    return _prompt_result(snapshot)


async def snapshot_candidate_transcript(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    workspace_id: UUID,
    candidate_id: UUID,
    settings: Settings,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    async with sessionmaker() as db:
        await _apply_worker_workspace(db, workspace_id)
        _, attempt = await _lock_candidate_meeting_and_attempt(
            db,
            workspace_id=workspace_id,
            candidate_id=candidate_id,
        )
        attempt = await _ensure_candidate_source_or_mark_stale(db, attempt)
        segments = await _candidate_segments(db, attempt)
        transcript = canonical_transcript(segments)
        metadata, chunks = split_plaintext_transcript(
            transcript,
            candidate_id=str(candidate_id),
            source_result_id=str(attempt.source_result_id),
            max_chunk_bytes=settings.outcome_transcript_chunk_bytes,
            max_snapshot_bytes=settings.outcome_transcript_max_bytes,
            max_serialized_bytes=settings.outcome_temporal_payload_bytes,
        )
        if attempt.temporal_transcript_hash not in {None, metadata["snapshot_hash"]}:
            raise TranscriptSnapshotError("outcome_transcript_changed")
        attempt = await _ensure_candidate_source_or_mark_stale(db, attempt)
        attempt.temporal_transcript_hash = str(metadata["snapshot_hash"])
        attempt.temporal_transcript_chunk_count = int(metadata["chunk_count"])
        await db.commit()
        return metadata, chunks


async def execute_candidate_generation(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    workspace_id: UUID,
    candidate_id: UUID,
    expected_snapshot_hash: str,
    settings: Settings,
) -> dict[str, Any]:
    api_key = _read_secret(settings.litellm_api_key_file)
    if settings.litellm_base_url is None:
        raise OutcomeGenerationDependencyError("litellm_endpoint_unavailable")
    started_at = datetime.now(UTC)
    async with sessionmaker() as db:
        await _apply_worker_workspace(db, workspace_id)
        attempt = await _candidate_attempt(db, workspace_id, candidate_id)
        meeting_id = attempt.meeting_id
        meeting = await lock_meeting_fence(db, workspace_id=workspace_id, meeting_id=meeting_id)
        attempt = await _candidate_attempt(db, workspace_id, candidate_id, for_update=True)
        snapshot = _stored_prompt_snapshot(attempt)
        if snapshot is None or attempt.source_result_id is None:
            raise OutcomeGenerationTerminalError("summary_prompt_not_pinned")
        attempt.generator_config_hash = _ai_generator_config_hash(
            template_id=attempt.template_id,
            template_key=attempt.template_key,
            template_version=attempt.template_version,
            template_sections=_template_sections(attempt),
            output_language=attempt.output_language,
            detail_level=attempt.detail_level,
            snapshot=snapshot,
        )
        if meeting is None or meeting_is_deleted_or_deleting(meeting):
            raise OutcomeGenerationTerminalError("meeting_deleting")
        try:
            attempt = await _ensure_candidate_source_fence(db, attempt)
        except OutcomeGenerationTerminalError as exc:
            if str(exc) != "summary_source_revision_stale":
                raise
            attempt.status = "stale"
            attempt.failure_code = "summary_source_revision_stale"
            attempt.ended_at = datetime.now(UTC)
            await db.commit()
            raise
        if is_expired(attempt.expires_at):
            _expire_candidate_attempt(attempt)
            await db.commit()
            raise OutcomeGenerationTerminalError("summary_candidate_expired")
        segments = await _candidate_segments(db, attempt)
        transcript = canonical_transcript(segments)
        transcript_hash = sha256(transcript.encode("utf-8")).hexdigest()
        if (
            transcript_hash != expected_snapshot_hash
            or transcript_hash != attempt.temporal_transcript_hash
        ):
            raise OutcomeGenerationTerminalError("summary_transcript_changed")
        existing = await db.scalar(
            select(GenerationCall)
            .where(
                GenerationCall.workspace_id == workspace_id,
                GenerationCall.candidate_id == candidate_id,
                GenerationCall.call_sequence == 1,
            )
            .order_by(GenerationCall.provider_attempt.desc())
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        provider_attempt = 1
        if existing is not None:
            if existing.call_state == "completed" and existing.validated_result_json is not None:
                state = "candidate" if attempt.outcome_set_id is not None else "failed"
                if state == "failed":
                    generation_error = (
                        existing.validated_result_json.get("generation_error")
                        if isinstance(existing.validated_result_json, dict)
                        else None
                    )
                    projection_failure = attempt.failure_code or (
                        str(generation_error.get("code"))
                        if isinstance(generation_error, dict) and generation_error.get("code")
                        else "summary_generation_projection_missing"
                    )
                    failure_source = "provider" if generation_error is not None else "system"
                    candidate_set = await db.scalar(
                        select(MeetingOutcomeSet)
                        .where(
                            MeetingOutcomeSet.workspace_id == workspace_id,
                            MeetingOutcomeSet.meeting_id == meeting_id,
                            MeetingOutcomeSet.candidate_id == candidate_id,
                            MeetingOutcomeSet.lifecycle_state == "active",
                        )
                        .with_for_update()
                        .execution_options(populate_existing=True)
                    )
                    if candidate_set is not None:
                        candidate_set.status = "failed"
                        candidate_set.failure_reason = projection_failure
                        candidate_set.failure_source = failure_source
                        set_outcome_category_states(candidate_set, "blocked")
                    attempt.status = "failed"
                    attempt.failure_code = projection_failure
                    attempt.failure_reason = projection_failure
                    attempt.ended_at = datetime.now(UTC)
                await finalize_dispatch_for_candidate(
                    db,
                    workspace_id=workspace_id,
                    candidate_id=candidate_id,
                    outcome="completed" if state == "candidate" else "failed",
                    failure_code=attempt.failure_code,
                )
                await db.commit()
                return {
                    "candidate_id": str(candidate_id),
                    "generation_call_id": str(existing.id),
                    "state": state,
                    "failure_code": attempt.failure_code,
                    "reused": True,
                }
            if existing.call_state == "reserved":
                _complete_generation_call_without_response(existing, call_state="ambiguous")
                attempt.status = "failed"
                attempt.failure_code = "summary_provider_outcome_ambiguous"
                await db.commit()
                raise OutcomeGenerationTerminalError("summary_provider_outcome_ambiguous")
            if existing.call_state == "ambiguous":
                raise OutcomeGenerationTerminalError("summary_provider_outcome_ambiguous")
            if existing.call_state != "failed" or not _generation_call_is_retryable(existing):
                raise OutcomeGenerationTerminalError("summary_provider_attempt_not_retryable")
            provider_attempt = existing.provider_attempt + 1
        sections = _template_sections(attempt)
        messages = compile_prompt_messages(
            snapshot,
            transcript_json=transcript,
            output_language=attempt.output_language or "ru",
            detail_level=attempt.detail_level or "standard",
            template_sections=sections,
        )
        request = snapshot.litellm_request(messages)
        call = GenerationCall(
            workspace_id=workspace_id,
            meeting_id=attempt.meeting_id,
            candidate_id=candidate_id,
            provider_attempt=provider_attempt,
            call_sequence=1,
            trace_id=attempt.langfuse_trace_id or deterministic_trace_id(candidate_id),
            observation_id=deterministic_observation_id(
                candidate_id, provider_attempt=provider_attempt, call_sequence=1
            ),
            call_state="reserved",
            started_at=started_at,
            request_json=request,
            transcript_text=transcript,
            request_hash=_content_hash(request),
            transcript_hash=transcript_hash,
            export_status="pending",
        )
        db.add(call)
        attempt.attempt_count += 1
        await db.commit()
        call_id = call.id
        meeting_id = attempt.meeting_id
        source_result_id = attempt.source_result_id
        media_revision_id = attempt.media_revision_id
        template_id = attempt.template_id
        template_key = attempt.template_key
        template_version = attempt.template_version
        output_language = attempt.output_language
        detail_level = attempt.detail_level
        requested_by_user_id = attempt.requested_by_user_id
    gateway = LiteLLMGateway(
        base_url=str(settings.litellm_base_url),
        api_key=api_key,
        timeout_seconds=settings.litellm_request_timeout_seconds,
    )
    async with sessionmaker() as db:
        await _apply_worker_workspace(db, workspace_id)
        meeting, attempt = await _lock_candidate_meeting_and_attempt(
            db,
            workspace_id=workspace_id,
            candidate_id=candidate_id,
        )
        attempt = await _candidate_attempt(db, workspace_id, candidate_id, for_update=True)
        call = await db.scalar(
            select(GenerationCall)
            .where(GenerationCall.id == call_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if (
            call is None
            or meeting is None
            or meeting_is_deleted_or_deleting(meeting)
            or int(meeting.deletion_epoch or 0) != int(attempt.deletion_epoch_at_start or 0)
        ):
            if call is not None:
                _complete_generation_call_without_response(call, call_state="failed")
            attempt.status = "cancelled"
            attempt.failure_code = "meeting_deleted"
            await db.commit()
            raise OutcomeGenerationTerminalError("meeting_deleting")
        try:
            attempt = await _ensure_candidate_source_fence(db, attempt)
        except OutcomeGenerationTerminalError as exc:
            if str(exc) != "summary_source_revision_stale":
                raise
            _complete_generation_call_without_response(call, call_state="failed")
            attempt.status = "stale"
            attempt.failure_code = "summary_source_revision_stale"
            attempt.ended_at = datetime.now(UTC)
            await db.commit()
            raise
        # Reserve and commit before network egress. A source can change after
        # this point; the post-egress fence retains the provider call but blocks
        # stale projection into a new outcome set.
        await db.commit()
        try:
            # Re-check in a fresh transaction immediately before provider egress.
            # The lock is released before the network call so deletion and source
            # updates are never held behind a provider timeout; the post-egress
            # fence remains authoritative for the unavoidable final race.
            _, attempt = await _lock_candidate_meeting_and_attempt(
                db,
                workspace_id=workspace_id,
                candidate_id=candidate_id,
            )
            attempt = await _ensure_candidate_source_fence(db, attempt)
        except OutcomeGenerationTerminalError as exc:
            call = await db.scalar(
                select(GenerationCall)
                .where(GenerationCall.id == call_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if call is not None:
                _complete_generation_call_without_response(call, call_state="failed")
            if str(exc) == "summary_source_revision_stale":
                attempt.status = "stale"
                attempt.failure_code = "summary_source_revision_stale"
            elif str(exc) == "meeting_deleting":
                attempt.status = "cancelled"
                attempt.failure_code = "meeting_deleted"
            if str(exc) in {"summary_source_revision_stale", "meeting_deleting"}:
                attempt.ended_at = datetime.now(UTC)
            await db.commit()
            raise
        await db.commit()
        try:
            response = await gateway.generate(
                snapshot=snapshot,
                messages=messages,
                idempotency_key=attempt.idempotency_key,
            )
        except LiteLLMError as exc:
            meeting = await lock_meeting_fence(db, workspace_id=workspace_id, meeting_id=meeting_id)
            attempt = await _candidate_attempt(db, workspace_id, candidate_id, for_update=True)
            call = await db.scalar(
                select(GenerationCall)
                .where(GenerationCall.id == call_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if (
                meeting is None
                or call is None
                or meeting_is_deleted_or_deleting(meeting)
                or int(meeting.deletion_epoch or 0) != int(attempt.deletion_epoch_at_start or 0)
            ):
                if call is not None:
                    _complete_generation_call_without_response(call, call_state="failed")
                attempt.status = "cancelled"
                attempt.failure_code = "meeting_deleted"
                await db.commit()
                raise OutcomeGenerationTerminalError("meeting_deleting") from exc
            completed_at = datetime.now(UTC)
            validation_result = {
                "generation_error": {
                    "code": exc.code,
                    "response_received": exc.raw_response is not None,
                    "retryable_classification": exc.retryable,
                    "egress_state": exc.egress_state,
                }
            }
            if attempt.status not in ACTIVE_CANDIDATE_STATUSES:
                call.completed_at = completed_at
                call.raw_response_json = exc.raw_response
                call.raw_response_hash = (
                    _content_hash(exc.raw_response) if exc.raw_response is not None else None
                )
                if exc.egress_state == "unknown":
                    call.call_state = "ambiguous"
                    call.validated_result_json = None
                    call.validated_result_hash = None
                    call.export_status = "not_required"
                else:
                    call.call_state = "failed"
                    call.validated_result_json = validation_result
                    call.validated_result_hash = _content_hash(validation_result)
                    call.export_status = "not_required"
                await db.commit()
                return {
                    "candidate_id": str(candidate_id),
                    "generation_call_id": str(call_id),
                    "state": attempt.status,
                    "failure_code": attempt.failure_code,
                    "reused": False,
                }
            call.completed_at = completed_at
            call.raw_response_json = exc.raw_response
            call.raw_response_hash = (
                _content_hash(exc.raw_response) if exc.raw_response is not None else None
            )
            if exc.egress_state == "unknown":
                call.call_state = "ambiguous"
                call.validated_result_json = None
                call.validated_result_hash = None
                call.export_status = "not_required"
                attempt.status = "failed"
                attempt.failure_code = "summary_provider_outcome_ambiguous"
                attempt.ended_at = completed_at
                await db.commit()
                raise OutcomeGenerationTerminalError("summary_provider_outcome_ambiguous") from exc
            call.validated_result_json = validation_result
            call.validated_result_hash = _content_hash(validation_result)
            if exc.raw_response is None:
                call.export_status = "not_required"
            if exc.retryable:
                call.call_state = "failed"
                attempt.status = "generating"
                attempt.failure_code = exc.code
                await db.commit()
                raise OutcomeGenerationDependencyError(exc.code) from exc
            call.call_state = "completed"
            attempt.status = "failed"
            attempt.failure_code = exc.code
            attempt.failure_reason = attempt.failure_reason or exc.code
            attempt.ended_at = completed_at
            await finalize_dispatch_for_candidate(
                db,
                workspace_id=workspace_id,
                candidate_id=candidate_id,
                outcome="failed",
                failure_code=exc.code,
            )
            await db.commit()
            return {
                "candidate_id": str(candidate_id),
                "generation_call_id": str(call_id),
                "state": "failed",
                "failure_code": exc.code,
                "reused": False,
            }
        meeting = await lock_meeting_fence(db, workspace_id=workspace_id, meeting_id=meeting_id)
        attempt = await _candidate_attempt(db, workspace_id, candidate_id, for_update=True)
        call = await db.scalar(
            select(GenerationCall)
            .where(GenerationCall.id == call_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if meeting is None or call is None:
            raise OutcomeGenerationTerminalError("meeting_deleting")
        if attempt.status not in ACTIVE_CANDIDATE_STATUSES:
            try:
                terminal_validated = validate_outcome_result(
                    response.parsed_content,
                    allowed_categories=sections,
                    allowed_segment_ids={str(segment.segment_id) for segment in segments},
                )
            except ValueError:
                terminal_validated = {"validation_error": {"code": "summary_response_invalid"}}
            _complete_generation_call_with_response(
                call,
                response=response,
                validated_result=terminal_validated,
                completed_at=datetime.now(UTC),
            )
            await db.commit()
            return {
                "candidate_id": str(candidate_id),
                "generation_call_id": str(call_id),
                "state": attempt.status,
                "failure_code": attempt.failure_code,
                "reused": False,
            }
        if meeting_is_deleted_or_deleting(meeting) or int(meeting.deletion_epoch or 0) != int(
            attempt.deletion_epoch_at_start or 0
        ):
            try:
                deleted_validated = validate_outcome_result(
                    response.parsed_content,
                    allowed_categories=sections,
                    allowed_segment_ids={str(segment.segment_id) for segment in segments},
                )
            except ValueError:
                deleted_validated = {"validation_error": {"code": "summary_response_invalid"}}
            deleted_at = datetime.now(UTC)
            _complete_generation_call_with_response(
                call,
                response=response,
                validated_result=deleted_validated,
                completed_at=deleted_at,
            )
            attempt.status = "cancelled"
            attempt.failure_code = "meeting_deleting"
            attempt.ended_at = deleted_at
            await finalize_dispatch_for_candidate(
                db,
                workspace_id=workspace_id,
                candidate_id=candidate_id,
                outcome="cancelled",
                failure_code="meeting_deleting",
            )
            await db.commit()
            raise OutcomeGenerationTerminalError("meeting_deleting")
        if is_expired(attempt.expires_at):
            expired_at = datetime.now(UTC)
            call.call_state = "failed"
            call.completed_at = expired_at
            call.export_status = "not_required"
            _expire_candidate_attempt(attempt, ended_at=expired_at)
            await db.commit()
            raise OutcomeGenerationTerminalError("summary_candidate_expired")
        try:
            attempt = await _ensure_candidate_source_fence(db, attempt)
        except OutcomeGenerationTerminalError as exc:
            if str(exc) != "summary_source_revision_stale":
                raise
            try:
                stale_validated = validate_outcome_result(
                    response.parsed_content,
                    allowed_categories=sections,
                    allowed_segment_ids={str(segment.segment_id) for segment in segments},
                )
            except ValueError as validation_exc:
                stale_validated = {
                    "validation_error": {
                        "code": "summary_response_invalid",
                        "message": str(validation_exc),
                    }
                }
            completed_at = datetime.now(UTC)
            _complete_generation_call_with_response(
                call,
                response=response,
                validated_result=stale_validated,
                completed_at=completed_at,
            )
            attempt.status = "stale"
            attempt.failure_code = "summary_source_revision_stale"
            attempt.ended_at = completed_at
            await finalize_dispatch_for_candidate(
                db,
                workspace_id=workspace_id,
                candidate_id=candidate_id,
                outcome="cancelled",
                failure_code="summary_source_revision_stale",
            )
            # Keep the completed call publishable for the approved observability
            # retention path, but never project its stale result into a set.
            await db.commit()
            return {
                "candidate_id": str(candidate_id),
                "generation_call_id": str(call_id),
                "state": "stale",
                "failure_code": "summary_source_revision_stale",
                "reused": False,
            }
        validation_failure: str | None = None
        try:
            validated = validate_outcome_result(
                response.parsed_content,
                allowed_categories=sections,
                allowed_segment_ids={str(segment.segment_id) for segment in segments},
                allowed_segment_sequences={
                    str(segment.segment_id): segment.sequence for segment in segments
                },
            )
        except ValueError as exc:
            validated = {
                "validation_error": {
                    "code": "summary_response_invalid",
                    "message": str(exc),
                }
            }
            validation_failure = "summary_response_invalid"
        completed_at = datetime.now(UTC)
        call.call_state = "completed"
        call.completed_at = completed_at
        call.actual_model = response.actual_model
        call.actual_provider = response.actual_provider
        call.provider_request_id = response.provider_request_id
        call.token_usage = response.token_usage
        call.cost_details = response.cost_details
        call.raw_response_json = response.raw_response
        call.validated_result_json = validated
        call.raw_response_hash = _content_hash(response.raw_response)
        call.validated_result_hash = _content_hash(validated)
        if validation_failure is not None:
            attempt.status = "failed"
            attempt.failure_code = validation_failure
            attempt.failure_reason = validation_failure
            attempt.ended_at = completed_at
            await finalize_dispatch_for_candidate(
                db,
                workspace_id=workspace_id,
                candidate_id=candidate_id,
                outcome="failed",
                failure_code=validation_failure,
            )
            await db.commit()
            return {
                "candidate_id": str(candidate_id),
                "generation_call_id": str(call_id),
                "state": "failed",
                "failure_code": validation_failure,
                "reused": False,
            }
        outcome_set = MeetingOutcomeSet(
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
            processing_result_id=source_result_id,
            candidate_id=candidate_id,
            status="available",
            source_kind="litellm",
            generator_kind="litellm",
            generator_version=AI_GENERATOR_VERSION,
            source_result_hash=attempt.source_result_hash or transcript_hash,
            source_fingerprint=attempt.source_fingerprint or attempt.source_result_hash,
            deletion_epoch_at_start=attempt.deletion_epoch_at_start,
            expires_at=attempt.expires_at,
            content_hash=_content_hash(validated),
            template_id=template_id,
            template_key=template_key,
            template_version=template_version,
            generator_config_hash=attempt.generator_config_hash,
            output_language=output_language,
            detail_level=detail_level,
            revision_state="candidate",
            requested_by_user_id=requested_by_user_id,
            started_at=started_at,
            generated_at=completed_at,
            latency_ms=max(0, int((completed_at - started_at).total_seconds() * 1000)),
        )
        for category, state in validated["category_states"].items():
            setattr(outcome_set, f"{category}_state", state)
        db.add(outcome_set)
        await db.flush()
        for item in validated["items"]:
            db.add(
                MeetingOutcomeItem(
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    outcome_set_id=outcome_set.id,
                    category=item["category"],
                    sequence=item["sequence"],
                    state="available",
                    text=item["text"],
                    owner_text=item["owner_text"],
                    due_date_text=item["due_date_text"],
                    truth_label=item["truth_label"],
                    source_refs_json=_canonical_source_refs(item["source_refs"], segments),
                )
            )
        attempt.outcome_set_id = outcome_set.id
        attempt.status = "candidate"
        attempt.ended_at = completed_at
        attempt.failure_code = None
        await finalize_dispatch_for_candidate(
            db,
            workspace_id=workspace_id,
            candidate_id=candidate_id,
            outcome="completed",
        )
        await db.commit()
        return {
            "candidate_id": str(candidate_id),
            "generation_call_id": str(call_id),
            "outcome_set_id": str(outcome_set.id),
            "state": "candidate",
            "reused": False,
        }


async def publish_generation_call(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    workspace_id: UUID,
    call_id: UUID,
    settings: Settings,
    activity_attempt: int,
    temporal_workflow_id: str | None = None,
    temporal_run_id: str | None = None,
    temporal_activity_id: str | None = None,
) -> None:
    async with sessionmaker() as db:
        await _apply_worker_workspace(db, workspace_id)
        seed_call = await db.scalar(
            select(GenerationCall).where(
                GenerationCall.id == call_id,
                GenerationCall.workspace_id == workspace_id,
            )
        )
        if seed_call is None or not _generation_call_is_publishable(seed_call):
            raise OutcomeGenerationTerminalError("generation_call_not_completed")
        if seed_call.export_status == "confirmed":
            return
        # Keep the canonical Meeting → Attempt → GenerationCall lock order
        # shared with execution/finalization; the unlocked seed only discovers
        # the candidate key.
        meeting, attempt = await _lock_candidate_meeting_and_attempt(
            db,
            workspace_id=workspace_id,
            candidate_id=seed_call.candidate_id,
        )
        call = await db.scalar(
            select(GenerationCall)
            .where(
                GenerationCall.id == call_id,
                GenerationCall.workspace_id == workspace_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if (
            call is None
            or call.candidate_id != attempt.candidate_id
            or not _generation_call_is_publishable(call)
        ):
            raise OutcomeGenerationTerminalError("generation_call_not_completed")
        if call.export_status == "confirmed":
            return
        now = datetime.now(UTC)
        last_export_attempt_at = normalize_db_timestamp(call.last_export_attempt_at)
        if call.export_status == "publishing":
            if (
                last_export_attempt_at is not None
                and now - last_export_attempt_at < EXPORT_CLAIM_STALE_AFTER
            ):
                return
        elif (
            normalize_db_timestamp(call.next_export_attempt_at) is not None
            and normalize_db_timestamp(call.next_export_attempt_at) > now
        ):
            return
        allow_completed_observability = _generation_call_is_publishable(call)
        if not allow_completed_observability and (
            meeting is None
            or meeting_is_deleted_or_deleting(meeting)
            or int(meeting.deletion_epoch or 0) != int(attempt.deletion_epoch_at_start or 0)
        ):
            _complete_generation_call_without_response(call, call_state="canceled")
            call.last_export_error_code = "meeting_deleting"
            await db.commit()
            return
        snapshot = _stored_prompt_snapshot(attempt)
        if snapshot is None or attempt.prompt_name is None or attempt.prompt_version is None:
            raise OutcomeGenerationTerminalError("summary_prompt_not_pinned")
        _verify_generation_call_hashes(call)
        claim_started_at = now
        call.export_status = "publishing"
        call.export_attempt_count += 1
        call.last_export_attempt_at = claim_started_at
        call.next_export_attempt_at = None
        call.last_export_error_code = None
        await db.commit()
        prompt_name = attempt.prompt_name
        prompt_version = attempt.prompt_version
        selected_model = attempt.model_route or snapshot.model
        requested_by = attempt.requested_by_user_id
    client = create_langfuse_client(settings)
    try:
        prompt = await asyncio.to_thread(
            client.get_prompt,
            prompt_name,
            version=prompt_version,
            type="chat",
            cache_ttl_seconds=60,
            max_retries=0,
            fetch_timeout_seconds=10,
        )
        async with sessionmaker() as guard_db:
            await _apply_worker_workspace(guard_db, workspace_id)
            guard_attempt = await _candidate_attempt(guard_db, workspace_id, call.candidate_id)
            if not allow_completed_observability:
                await _ensure_candidate_fence(guard_db, guard_attempt)
        await asyncio.to_thread(
            publish_completed_generation,
            client,
            call=call,
            context=GenerationTraceContext(
                environment=settings.langfuse_environment,
                selected_model=selected_model,
                prompt_name=prompt_name,
                prompt_version=prompt_version,
                prompt_hash=attempt.prompt_hash,
                user_id=str(requested_by) if requested_by else None,
                session_id=str(call.meeting_id),
                activity_attempt=activity_attempt,
                temporal_workflow_id=temporal_workflow_id,
                temporal_run_id=temporal_run_id,
                temporal_activity_id=temporal_activity_id,
            ),
            prompt=prompt,
        )
    except Exception as exc:
        blocked_by_deletion = False
        async with sessionmaker() as db:
            await _apply_worker_workspace(db, workspace_id)
            current_seed = await db.scalar(
                select(GenerationCall).where(
                    GenerationCall.id == call_id,
                    GenerationCall.workspace_id == workspace_id,
                )
            )
            current = None
            attempt = None
            meeting = None
            if current_seed is not None:
                meeting, attempt = await _lock_candidate_meeting_and_attempt(
                    db,
                    workspace_id=workspace_id,
                    candidate_id=current_seed.candidate_id,
                )
                current = await db.scalar(
                    select(GenerationCall)
                    .where(
                        GenerationCall.id == call_id,
                        GenerationCall.workspace_id == workspace_id,
                    )
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            blocked_by_deletion = not allow_completed_observability and (
                meeting is None
                or meeting_is_deleted_or_deleting(meeting)
                or (
                    attempt is not None
                    and meeting is not None
                    and int(meeting.deletion_epoch or 0)
                    != int(attempt.deletion_epoch_at_start or 0)
                )
            )
            if current is not None and blocked_by_deletion:
                _complete_generation_call_without_response(current, call_state="canceled")
                current.last_export_error_code = "meeting_deleting"
            elif current is not None and (
                current.export_status != "confirmed"
                and normalize_db_timestamp(current.last_export_attempt_at) == claim_started_at
            ):
                current.export_status = "pending"
                current.last_export_error_code = "langfuse_delivery_failed"
                current.next_export_attempt_at = datetime.now(UTC) + timedelta(minutes=5)
            await db.commit()
        if blocked_by_deletion:
            return
        raise OutcomeGenerationDependencyError("langfuse_delivery_failed") from exc
    finally:
        shutdown_langfuse(client)
    async with sessionmaker() as db:
        await _apply_worker_workspace(db, workspace_id)
        current_seed = await db.scalar(
            select(GenerationCall).where(
                GenerationCall.id == call_id,
                GenerationCall.workspace_id == workspace_id,
            )
        )
        if current_seed is not None:
            meeting, attempt = await _lock_candidate_meeting_and_attempt(
                db,
                workspace_id=workspace_id,
                candidate_id=current_seed.candidate_id,
            )
            current = await db.scalar(
                select(GenerationCall)
                .where(
                    GenerationCall.id == call_id,
                    GenerationCall.workspace_id == workspace_id,
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        else:
            current = None
            attempt = None
            meeting = None
        if current is not None and attempt is not None:
            if not allow_completed_observability and (
                meeting is None
                or meeting_is_deleted_or_deleting(meeting)
                or int(meeting.deletion_epoch or 0) != int(attempt.deletion_epoch_at_start or 0)
            ):
                _complete_generation_call_without_response(current, call_state="canceled")
                current.last_export_error_code = "meeting_deleting"
            elif (
                current.export_status == "publishing"
                and normalize_db_timestamp(current.last_export_attempt_at) == claim_started_at
            ):
                current.export_status = "confirmed"
                current.export_confirmed_at = datetime.now(UTC)
                current.next_export_attempt_at = None
                current.last_export_error_code = None
            await db.commit()


async def publish_candidate_generation_calls(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    workspace_id: UUID,
    candidate_id: UUID,
    settings: Settings,
    activity_attempt: int,
    temporal_workflow_id: str | None = None,
    temporal_run_id: str | None = None,
    temporal_activity_id: str | None = None,
) -> dict[str, object]:
    """Publish every durable response for one candidate in provider-attempt order."""
    async with sessionmaker() as db:
        await _apply_worker_workspace(db, workspace_id)
        calls = (
            await db.scalars(
                select(GenerationCall)
                .where(
                    GenerationCall.workspace_id == workspace_id,
                    GenerationCall.candidate_id == candidate_id,
                    GenerationCall.export_status != "confirmed",
                )
                .order_by(
                    GenerationCall.provider_attempt,
                    GenerationCall.call_sequence,
                )
            )
        ).all()
        call_ids = [call.id for call in calls if _generation_call_is_publishable(call)]
    for call_id in call_ids:
        await publish_generation_call(
            sessionmaker,
            workspace_id=workspace_id,
            call_id=call_id,
            settings=settings,
            activity_attempt=activity_attempt,
            temporal_workflow_id=temporal_workflow_id,
            temporal_run_id=temporal_run_id,
            temporal_activity_id=temporal_activity_id,
        )
    async with sessionmaker() as db:
        await _apply_worker_workspace(db, workspace_id)
        attempt = await db.scalar(
            select(MeetingOutcomeGenerationAttempt).where(
                MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
                MeetingOutcomeGenerationAttempt.candidate_id == candidate_id,
            )
        )
        calls = (
            await db.scalars(
                select(GenerationCall).where(
                    GenerationCall.workspace_id == workspace_id,
                    GenerationCall.candidate_id == candidate_id,
                    GenerationCall.export_status != "confirmed",
                )
            )
        ).all()
        pending_count = sum(_generation_call_is_publishable(call) for call in calls)
    return {
        "candidate_terminal": attempt is None or attempt.status not in ACTIVE_CANDIDATE_STATUSES,
        "pending_count": pending_count,
        "published_count": len(call_ids),
    }


def _generation_call_is_publishable(call: GenerationCall) -> bool:
    if (
        call.completed_at is None
        or call.raw_response_json is None
        or call.validated_result_json is None
    ):
        return False
    return call.call_state in {"completed", "failed"}


def _complete_generation_call_without_response(call: GenerationCall, *, call_state: str) -> None:
    call.call_state = call_state
    call.completed_at = datetime.now(UTC)
    call.export_status = "not_required"


def _complete_generation_call_with_response(
    call: GenerationCall,
    *,
    response: object,
    validated_result: dict[str, object],
    completed_at: datetime,
) -> None:
    call.call_state = "completed"
    call.completed_at = completed_at
    call.actual_model = getattr(response, "actual_model", None)
    call.actual_provider = getattr(response, "actual_provider", None)
    call.provider_request_id = getattr(response, "provider_request_id", None)
    call.token_usage = getattr(response, "token_usage", None)
    call.cost_details = getattr(response, "cost_details", None)
    call.raw_response_json = getattr(response, "raw_response", None)
    call.validated_result_json = validated_result
    call.raw_response_hash = _content_hash(call.raw_response_json)
    call.validated_result_hash = _content_hash(validated_result)
    call.export_status = "pending"


async def finalize_candidate_generation_failure(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    workspace_id: UUID,
    candidate_id: UUID,
    failure_code: str = "summary_generation_retries_exhausted",
    failure_reason: str | None = None,
) -> None:
    """Project exhausted durable retries into a bounded user-visible terminal state."""
    async with sessionmaker() as db:
        await _apply_worker_workspace(db, workspace_id)
        # Keep the same Meeting → Attempt → DispatchIntent lock order as the
        # dispatch reconciler. The unlocked lookup only discovers the meeting
        # key; every mutation is protected by the ordered locks below.
        seed_attempt = await _candidate_attempt(db, workspace_id, candidate_id)
        meeting = await lock_meeting_fence(
            db,
            workspace_id=workspace_id,
            meeting_id=seed_attempt.meeting_id,
        )
        if meeting is None:
            return
        attempt = await _candidate_attempt(db, workspace_id, candidate_id, for_update=True)
        await db.scalar(
            select(DispatchIntent)
            .where(
                DispatchIntent.workspace_id == workspace_id,
                DispatchIntent.candidate_id == candidate_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if meeting_is_deleted_or_deleting(meeting):
            attempt.status = "cancelled"
            attempt.failure_code = attempt.failure_code or "meeting_deleted"
            attempt.failure_reason = attempt.failure_reason or "meeting_deleted"
            attempt.ended_at = attempt.ended_at or datetime.now(UTC)
            await finalize_dispatch_for_candidate(
                db,
                workspace_id=workspace_id,
                candidate_id=candidate_id,
                outcome="cancelled",
                failure_code=attempt.failure_code,
            )
            await db.commit()
            return
        if attempt.status in {"candidate", "accepted"} and attempt.outcome_set_id is not None:
            await finalize_dispatch_for_candidate(
                db,
                workspace_id=workspace_id,
                candidate_id=candidate_id,
                outcome="completed",
            )
            await db.commit()
            return
        if attempt.status in {"cancelled", "stale", "expired", "rejected"}:
            await finalize_dispatch_for_candidate(
                db,
                workspace_id=workspace_id,
                candidate_id=candidate_id,
                outcome="cancelled",
                failure_code=attempt.failure_code,
            )
            await db.commit()
            return
        if attempt.status == "failed":
            preserved_code = attempt.failure_code or failure_code
            attempt.failure_code = preserved_code
            attempt.failure_reason = attempt.failure_reason or failure_reason or preserved_code
            attempt.ended_at = attempt.ended_at or datetime.now(UTC)
            await finalize_dispatch_for_candidate(
                db,
                workspace_id=workspace_id,
                candidate_id=candidate_id,
                outcome="failed",
                failure_code=preserved_code,
            )
            await db.commit()
            return
        if attempt.status not in ACTIVE_CANDIDATE_STATUSES:
            return
        preserved_code = attempt.failure_code or failure_code
        attempt.status = "failed"
        attempt.failure_code = preserved_code
        attempt.failure_reason = attempt.failure_reason or failure_reason or preserved_code
        attempt.ended_at = datetime.now(UTC)
        await finalize_dispatch_for_candidate(
            db,
            workspace_id=workspace_id,
            candidate_id=candidate_id,
            outcome="failed",
            failure_code=preserved_code,
        )
        await db.commit()


async def mark_candidate_generation_terminal_failure(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    workspace_id: UUID,
    candidate_id: UUID,
    failure_code: str,
) -> None:
    """Persist a non-retryable candidate outcome before Temporal re-raises it.

    The workflow finalizer intentionally projects exhausted *retryable* errors
    to ``summary_generation_retries_exhausted``.  Terminal activity errors
    must keep their bounded domain code (for example, a changed transcript),
    otherwise the cabinet offers a misleading retry and recovery resurrects a
    candidate that can no longer be accepted.
    """
    async with sessionmaker() as db:
        await _apply_worker_workspace(db, workspace_id)
        attempt = await _candidate_attempt(db, workspace_id, candidate_id, for_update=True)
        if attempt.outcome_set_id is not None or attempt.status not in {
            "queued",
            "generating",
            "blocked_dependency",
        }:
            return
        attempt.status = "failed"
        attempt.failure_code = failure_code[:120]
        attempt.ended_at = datetime.now(UTC)
        await db.commit()


async def _cas_summary_slot(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    template_key: str,
    replacement_outcome_set_id: UUID,
    expected_current_outcome_set_id: UUID | None,
    expected_source_fingerprint: str,
    expected_deletion_epoch: int,
    expected_access_policy_epoch: int | None = None,
) -> MeetingSummarySlot:
    """Atomically move one type slot after its non-model fences pass.

    The meeting deletion fence is always acquired first, followed by the
    target slot and (when present) its prior current revision. This primitive
    deliberately does not touch receipts, dispatch intents, or the meeting's
    legacy global pointer. Feature 195 supplies the proof and invokes this
    same primitive inside its larger publication transaction.
    """

    meeting = await lock_meeting_fence(db, workspace_id=workspace_id, meeting_id=meeting_id)
    if (
        meeting is None
        or meeting_is_deleted_or_deleting(meeting)
        or int(meeting.deletion_epoch or 0) != int(expected_deletion_epoch)
    ):
        raise SummarySlotCASConflict("summary_slot_conflict")

    slot = await db.scalar(
        select(MeetingSummarySlot)
        .where(
            MeetingSummarySlot.workspace_id == workspace_id,
            MeetingSummarySlot.meeting_id == meeting_id,
            MeetingSummarySlot.template_key == template_key,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if slot is None or slot.current_outcome_set_id != expected_current_outcome_set_id:
        raise SummarySlotCASConflict()

    replacement = await db.scalar(
        select(MeetingOutcomeSet).where(
            MeetingOutcomeSet.workspace_id == workspace_id,
            MeetingOutcomeSet.meeting_id == meeting_id,
            MeetingOutcomeSet.id == replacement_outcome_set_id,
            MeetingOutcomeSet.template_key == template_key,
        )
    )
    if (
        replacement is None
        or replacement.lifecycle_state != "active"
        or replacement.status not in {"available", "partial"}
        or replacement.revision_state not in {"candidate", "accepted"}
        or replacement.source_fingerprint != expected_source_fingerprint
        or int(replacement.deletion_epoch_at_start or 0) != int(expected_deletion_epoch)
    ):
        raise SummarySlotCASConflict()

    if expected_access_policy_epoch is not None:
        attempt = await db.scalar(
            select(MeetingOutcomeGenerationAttempt)
            .where(
                MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
                MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
                MeetingOutcomeGenerationAttempt.outcome_set_id == replacement.id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if attempt is None or (attempt.metadata_json or {}).get("access_policy_epoch") != (
            expected_access_policy_epoch
        ):
            raise SummarySlotCASConflict()

    prior = None
    if slot.current_outcome_set_id is not None:
        prior = await db.scalar(
            select(MeetingOutcomeSet)
            .where(
                MeetingOutcomeSet.workspace_id == workspace_id,
                MeetingOutcomeSet.meeting_id == meeting_id,
                MeetingOutcomeSet.id == slot.current_outcome_set_id,
                MeetingOutcomeSet.template_key == template_key,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if prior is None:
            raise SummarySlotCASConflict()

    if slot.current_outcome_set_id == replacement.id:
        return slot

    now = datetime.now(UTC)
    if prior is not None:
        prior.revision_state = "superseded"
        replacement.supersedes_outcome_set_id = prior.id
    replacement.revision_state = "accepted"
    replacement.accepted_at = replacement.accepted_at or now
    replacement.expires_at = None
    slot.current_outcome_set_id = replacement.id
    slot.current_binding_class = "verified_complete"
    slot.legacy_migration_proof_hash = None
    await db.flush()
    return slot


async def resolve_summary_candidate(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    candidate_id: UUID,
    requested_by_user_id: UUID,
    accept: bool,
    expected_current_outcome_set_id: UUID | None,
) -> MeetingOutcomeSet:
    meeting = await lock_meeting_fence(db, workspace_id=workspace_id, meeting_id=meeting_id)
    if meeting is None:
        raise OutcomeGenerationTerminalError("summary_candidate_unavailable")
    if meeting_is_deleted_or_deleting(meeting):
        raise OutcomeGenerationTerminalError("meeting_deleting")
    if meeting.current_outcome_set_id != expected_current_outcome_set_id:
        raise OutcomeGenerationTerminalError("summary_revision_conflict")
    attempt = await db.scalar(
        select(MeetingOutcomeGenerationAttempt)
        .where(
            MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
            MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
            MeetingOutcomeGenerationAttempt.candidate_id == candidate_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if attempt is None or attempt.outcome_set_id is None:
        raise OutcomeGenerationTerminalError("summary_candidate_unavailable")
    outcome_set = await db.scalar(
        select(MeetingOutcomeSet)
        .where(
            MeetingOutcomeSet.workspace_id == workspace_id,
            MeetingOutcomeSet.id == attempt.outcome_set_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if meeting is None or outcome_set is None:
        raise OutcomeGenerationTerminalError("summary_candidate_unavailable")
    if outcome_set.candidate_id != candidate_id:
        raise OutcomeGenerationTerminalError("summary_candidate_unavailable")
    if (
        outcome_set.lifecycle_state != "active"
        or outcome_set.revision_state != "candidate"
        or outcome_set.status not in {"available", "partial"}
    ):
        raise OutcomeGenerationTerminalError("summary_candidate_unavailable")
    if is_expired(attempt.expires_at) or is_expired(outcome_set.expires_at):
        _expire_candidate_attempt(attempt)
        outcome_set.revision_state = "expired"
        await finalize_dispatch_for_candidate(
            db,
            workspace_id=workspace_id,
            candidate_id=candidate_id,
            outcome="cancelled",
            failure_code=attempt.failure_code,
        )
        await db.flush()
        raise OutcomeGenerationTerminalError("summary_candidate_expired")
    if attempt.status != "candidate":
        raise OutcomeGenerationTerminalError("summary_candidate_unavailable")
    source_result = await db.scalar(
        select(ProcessingResult).where(
            ProcessingResult.id == attempt.source_result_id,
            ProcessingResult.workspace_id == workspace_id,
            ProcessingResult.meeting_id == meeting_id,
        )
    )
    latest_revision = await db.scalar(
        select(MediaRevision)
        .where(
            MediaRevision.workspace_id == workspace_id,
            MediaRevision.meeting_id == meeting_id,
            MediaRevision.status == "accepted",
            MediaRevision.immutable.is_(True),
        )
        .order_by(MediaRevision.revision_number.desc(), MediaRevision.updated_at.desc())
    )
    latest_result_query = select(ProcessingResult).where(
        ProcessingResult.workspace_id == workspace_id,
        ProcessingResult.meeting_id == meeting_id,
        ProcessingResult.status == ProcessingResultStatus.IMPORTED.value,
    )
    if latest_revision is None:
        latest_result_query = latest_result_query.where(
            ProcessingResult.media_revision_id.is_(None)
        )
    else:
        latest_result_query = latest_result_query.where(
            ProcessingResult.media_revision_id == latest_revision.id
        )
    latest_result = await db.scalar(
        latest_result_query.order_by(
            ProcessingResult.result_version.desc(),
            nullslast(ProcessingResult.imported_at.desc()),
            ProcessingResult.created_at.desc(),
            ProcessingResult.id.desc(),
        )
    )
    current_source_fingerprint = f"result:{source_result.id}" if source_result is not None else None
    if source_result is not None and source_result.media_revision_id is not None:
        revision = await db.get(MediaRevision, source_result.media_revision_id)
        if revision is not None:
            try:
                current_source_fingerprint = source_fingerprint_for_revision(revision)
            except ValueError:
                current_source_fingerprint = None
    speaker_attribution_current = await candidate_speaker_attribution_is_current(db, attempt)
    if (
        source_result is None
        or latest_result is None
        or latest_result.id != source_result.id
        or (latest_revision is None and attempt.media_revision_id is not None)
        or (latest_revision is not None and attempt.media_revision_id != latest_revision.id)
        or outcome_set.processing_result_id != source_result.id
        or outcome_set.media_revision_id != source_result.media_revision_id
        or attempt.source_result_hash is None
        or source_result.source_result_hash is None
        or source_result.source_result_hash != attempt.source_result_hash
        or attempt.source_fingerprint is None
        or current_source_fingerprint != attempt.source_fingerprint
        or not speaker_attribution_current
        or int(meeting.deletion_epoch or 0) != int(attempt.deletion_epoch_at_start or 0)
    ):
        attempt.status = "stale"
        outcome_set.revision_state = "stale"
        attempt.failure_code = "summary_source_revision_stale"
        attempt.ended_at = datetime.now(UTC)
        await finalize_dispatch_for_candidate(
            db,
            workspace_id=workspace_id,
            candidate_id=candidate_id,
            outcome="cancelled",
            failure_code=attempt.failure_code,
        )
        await db.flush()
        raise OutcomeGenerationTerminalError("summary_source_revision_stale")
    if not accept:
        outcome_set.revision_state = "rejected"
        attempt.status = "rejected"
        attempt.ended_at = datetime.now(UTC)
        await finalize_dispatch_for_candidate(
            db,
            workspace_id=workspace_id,
            candidate_id=candidate_id,
            outcome="cancelled",
            failure_code="summary_candidate_rejected",
        )
        return outcome_set
    await publish_model_generated_outcome(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        candidate_id=candidate_id,
        expected_current_outcome_set_id=expected_current_outcome_set_id,
    )
    raise AssertionError("fail-closed publication entry point must not return")


async def _candidate_attempt(
    db: AsyncSession,
    workspace_id: UUID,
    candidate_id: UUID,
    *,
    for_update: bool = False,
) -> MeetingOutcomeGenerationAttempt:
    query = (
        select(MeetingOutcomeGenerationAttempt)
        .where(
            MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
            MeetingOutcomeGenerationAttempt.candidate_id == candidate_id,
        )
        .execution_options(populate_existing=True)
    )
    if for_update:
        query = query.with_for_update()
    attempt = await db.scalar(query)
    if attempt is None:
        raise OutcomeGenerationTerminalError("summary_candidate_unavailable")
    return attempt


async def _lock_candidate_meeting_and_attempt(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    candidate_id: UUID,
) -> tuple[Meeting | None, MeetingOutcomeGenerationAttempt]:
    """Lock the shared lifecycle fence before the mutable candidate row."""
    seed_attempt = await _candidate_attempt(db, workspace_id, candidate_id)
    meeting = await lock_meeting_fence(
        db,
        workspace_id=workspace_id,
        meeting_id=seed_attempt.meeting_id,
    )
    attempt = await _candidate_attempt(db, workspace_id, candidate_id, for_update=True)
    return meeting, attempt


async def _ensure_candidate_fence(
    db: AsyncSession,
    attempt: MeetingOutcomeGenerationAttempt,
) -> None:
    meeting = await lock_meeting_fence(
        db, workspace_id=attempt.workspace_id, meeting_id=attempt.meeting_id
    )
    if (
        meeting is None
        or meeting_is_deleted_or_deleting(meeting)
        or int(meeting.deletion_epoch or 0) != int(attempt.deletion_epoch_at_start or 0)
    ):
        raise OutcomeGenerationTerminalError("meeting_deleting")


async def _ensure_candidate_source_fence(
    db: AsyncSession,
    attempt: MeetingOutcomeGenerationAttempt,
) -> MeetingOutcomeGenerationAttempt:
    """Ensure a candidate still points at the current accepted source.

    The meeting row is locked before reading the source pointer. Ingestion and
    processing mutations use the same fence, so this check is stable for the
    current transaction. Legacy rows without a media revision are fenced to
    their latest revision-less processing result.
    """
    if attempt.status not in ACTIVE_CANDIDATE_STATUSES:
        raise OutcomeGenerationTerminalError("summary_candidate_terminal")
    meeting = await lock_meeting_fence(
        db, workspace_id=attempt.workspace_id, meeting_id=attempt.meeting_id
    )
    # The caller may have discovered the attempt before another lifecycle
    # transition committed. Refresh it under the same Meeting fence before any
    # stale-state mutation; the identity map updates the caller's instance.
    authoritative_attempt = await db.scalar(
        select(MeetingOutcomeGenerationAttempt)
        .where(
            MeetingOutcomeGenerationAttempt.workspace_id == attempt.workspace_id,
            MeetingOutcomeGenerationAttempt.id == attempt.id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if authoritative_attempt is None:
        raise OutcomeGenerationTerminalError("summary_candidate_unavailable")
    attempt = authoritative_attempt
    if attempt.status not in ACTIVE_CANDIDATE_STATUSES:
        raise OutcomeGenerationTerminalError("summary_candidate_terminal")
    if (
        meeting is None
        or meeting_is_deleted_or_deleting(meeting)
        or int(meeting.deletion_epoch or 0) != int(attempt.deletion_epoch_at_start or 0)
    ):
        raise OutcomeGenerationTerminalError("meeting_deleting")
    if attempt.source_result_id is None or (
        attempt.media_revision_id is None and attempt.source_fingerprint is None
    ):
        raise OutcomeGenerationTerminalError("summary_source_revision_stale")

    latest_revision = await db.scalar(
        select(MediaRevision)
        .where(
            MediaRevision.workspace_id == attempt.workspace_id,
            MediaRevision.meeting_id == attempt.meeting_id,
            MediaRevision.status == "accepted",
            MediaRevision.immutable.is_(True),
        )
        .order_by(MediaRevision.revision_number.desc(), MediaRevision.updated_at.desc())
    )
    expected_revision_id = latest_revision.id if latest_revision is not None else None
    result_query = select(ProcessingResult).where(
        ProcessingResult.workspace_id == attempt.workspace_id,
        ProcessingResult.meeting_id == attempt.meeting_id,
        ProcessingResult.status == ProcessingResultStatus.IMPORTED.value,
    )
    if expected_revision_id is None:
        result_query = result_query.where(ProcessingResult.media_revision_id.is_(None))
    else:
        result_query = result_query.where(
            ProcessingResult.media_revision_id == expected_revision_id
        )
    latest_result = await db.scalar(
        result_query.order_by(
            ProcessingResult.result_version.desc(),
            nullslast(ProcessingResult.imported_at.desc()),
            ProcessingResult.created_at.desc(),
            ProcessingResult.id.desc(),
        )
    )
    if latest_result is None:
        raise OutcomeGenerationTerminalError("summary_source_revision_stale")

    if latest_revision is None:
        expected_source_fingerprint = f"result:{latest_result.id}"
    else:
        try:
            expected_source_fingerprint = source_fingerprint_for_revision(latest_revision)
        except ValueError as exc:
            raise OutcomeGenerationTerminalError("summary_source_revision_stale") from exc

    speaker_attribution_current = await candidate_speaker_attribution_is_current(db, attempt)
    if (
        attempt.media_revision_id != expected_revision_id
        or attempt.processing_result_id != latest_result.id
        or attempt.source_result_id != latest_result.id
        or attempt.source_result_hash is None
        or latest_result.source_result_hash is None
        or attempt.source_result_hash != latest_result.source_result_hash
        or attempt.source_fingerprint != expected_source_fingerprint
        or not speaker_attribution_current
    ):
        raise OutcomeGenerationTerminalError("summary_source_revision_stale")
    return attempt


async def _ensure_candidate_source_or_mark_stale(
    db: AsyncSession,
    attempt: MeetingOutcomeGenerationAttempt,
) -> MeetingOutcomeGenerationAttempt:
    """Fence source egress and persist a terminal stale state for the candidate."""
    try:
        attempt = await _ensure_candidate_source_fence(db, attempt)
    except OutcomeGenerationTerminalError as exc:
        if str(exc) != "summary_source_revision_stale":
            raise
        attempt.status = "stale"
        attempt.failure_code = "summary_source_revision_stale"
        attempt.ended_at = datetime.now(UTC)
        await db.commit()
        raise
    return attempt


async def _candidate_segments(
    db: AsyncSession, attempt: MeetingOutcomeGenerationAttempt
) -> list[OutcomeTranscriptSegment]:
    if attempt.source_result_id is None:
        raise OutcomeGenerationTerminalError("summary_source_unavailable")
    result = await db.scalar(
        select(ProcessingResult).where(
            ProcessingResult.workspace_id == attempt.workspace_id,
            ProcessingResult.meeting_id == attempt.meeting_id,
            ProcessingResult.id == attempt.source_result_id,
        )
    )
    if result is None:
        raise OutcomeGenerationTerminalError("summary_transcript_unavailable")
    segments = await load_outcome_transcript_segments(db, result=result)
    if not segments:
        raise OutcomeGenerationTerminalError("summary_transcript_unavailable")
    return segments


def _canonical_source_refs(
    source_refs: list[dict[str, object]],
    segments: list[OutcomeTranscriptSegment],
) -> list[dict[str, object]]:
    segments_by_id = {str(segment.segment_id): segment for segment in segments}
    canonical_refs = []
    for ref in source_refs:
        segment = segments_by_id[str(ref["transcript_segment_id"])]
        canonical_refs.append(
            OutcomeSourceReference(
                transcript_segment_id=segment.segment_id,
                sequence=segment.sequence,
                start_seconds=float(segment.start_seconds),
                end_seconds=float(segment.end_seconds),
                speaker_label=segment.speaker_label,
                source_role=segment.source_role,
                evidence_kind=str(ref["evidence_kind"]),
            ).as_json()
        )
    return canonical_refs


def _stored_prompt_snapshot(
    attempt: MeetingOutcomeGenerationAttempt,
) -> PromptSnapshot | None:
    if (
        attempt.prompt_name is None
        or attempt.prompt_version is None
        or attempt.prompt_definition is None
        or attempt.prompt_config is None
        or attempt.prompt_hash is None
    ):
        return None
    try:
        snapshot = validate_prompt_snapshot(
            name=attempt.prompt_name,
            version=attempt.prompt_version,
            prompt_type="chat",
            prompt=attempt.prompt_definition,
            config=attempt.prompt_config,
            source=attempt.prompt_source or "verified_promoted_snapshot",
        )
    except ValueError as exc:
        raise OutcomeGenerationTerminalError("summary_prompt_snapshot_corrupt") from exc
    if snapshot.canonical_hash != attempt.prompt_hash:
        raise OutcomeGenerationTerminalError("summary_prompt_snapshot_corrupt")
    return snapshot


def _prompt_result(snapshot: PromptSnapshot) -> dict[str, object]:
    return {
        "prompt_name": snapshot.name,
        "prompt_version": snapshot.version,
        "prompt_hash": snapshot.canonical_hash,
        "model_route": snapshot.model,
    }


def _template_sections(attempt: MeetingOutcomeGenerationAttempt) -> tuple[str, ...]:
    stored = attempt.metadata_json.get("template_sections") if attempt.metadata_json else None
    if isinstance(stored, list):
        sections = tuple(str(section) for section in stored)
        if sections and all(section in OUTCOME_CATEGORIES for section in sections):
            return sections
    if attempt.template_id is None and attempt.template_key:
        definition = built_in_template_for_version(
            attempt.template_key,
            attempt.template_version or 1,
        )
        if definition is not None:
            return definition.sections
    raise OutcomeGenerationTerminalError("summary_template_snapshot_invalid")


def _content_hash(value: object) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _ai_generator_config_hash(
    *,
    template_id: UUID | None,
    template_key: str | None,
    template_version: int | None,
    template_sections: tuple[str, ...],
    output_language: str | None,
    detail_level: str | None,
    prompt_name: str | None = None,
    snapshot: PromptSnapshot | None = None,
) -> str:
    """Hash safe generator inputs without persisting prompt or provider secrets."""

    model_parameters: dict[str, object] | None = None
    output_schema_version: str | None = None
    prompt_version: int | None = None
    prompt_hash: str | None = None
    model_route: str | None = None
    if snapshot is not None:
        prompt_name = snapshot.name
        prompt_version = snapshot.version
        prompt_hash = snapshot.canonical_hash
        model_route = snapshot.model
        response_format = snapshot.config.get("response_format")
        if isinstance(response_format, dict):
            json_schema = response_format.get("json_schema")
            if isinstance(json_schema, dict):
                output_schema_version = str(json_schema.get("name") or "")
            model_parameters = {
                "temperature": snapshot.config.get("temperature"),
                "response_format": response_format,
            }
    return _content_hash(
        {
            "generator_version": AI_GENERATOR_VERSION,
            "template": {
                "id": str(template_id) if template_id is not None else None,
                "key": template_key,
                "version": template_version,
                "sections": list(template_sections),
                "output_language": output_language,
                "detail_level": detail_level,
            },
            "prompt": {
                "name": prompt_name,
                "version": prompt_version,
                "hash": prompt_hash,
            },
            "model_route": model_route,
            "model_parameters": model_parameters,
            "output_schema_version": output_schema_version,
        }
    )


def _generation_call_is_retryable(call: GenerationCall) -> bool:
    result = call.validated_result_json
    if not isinstance(result, dict):
        return False
    error = result.get("generation_error")
    return (
        isinstance(error, dict)
        and error.get("retryable_classification") is True
        and error.get("egress_state") in {"not_sent", "response_received"}
    )


def _verify_generation_call_hashes(call: GenerationCall) -> None:
    if (
        call.request_json is None
        or call.transcript_text is None
        or call.raw_response_json is None
        or call.validated_result_json is None
    ):
        raise OutcomeGenerationTerminalError("generation_call_content_incomplete")
    expected = (
        _content_hash(call.request_json),
        sha256(call.transcript_text.encode("utf-8")).hexdigest(),
        _content_hash(call.raw_response_json),
        _content_hash(call.validated_result_json),
    )
    actual = (
        call.request_hash,
        call.transcript_hash,
        call.raw_response_hash,
        call.validated_result_hash,
    )
    if expected != actual:
        raise OutcomeGenerationTerminalError("generation_call_content_hash_mismatch")


async def _apply_worker_workspace(db: AsyncSession, workspace_id: UUID) -> None:
    await apply_tenant_context(
        db,
        TenantDatabaseContext(
            organization_id=ZERO_UUID,
            workspace_id=workspace_id,
            user_id=ZERO_UUID,
            context_kind="worker",
        ),
    )


def _read_secret(path: Path | None) -> str:
    if path is None:
        raise OutcomeGenerationDependencyError("litellm_credential_unavailable")
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise OutcomeGenerationDependencyError("litellm_credential_unavailable")
    return value
