from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
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
    MeetingOutcomeSet,
    MeetingSummarySlot,
    ProcessingResult,
    SummaryTemplate,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.db.tenant_context import (
    TenantDatabaseContext,
    apply_tenant_context,
    rehydrate_tenant_context,
)
from twobrain_rec_server.domain.speaker_turns import canonical_speech_available
from twobrain_rec_server.ingest.media_revisions import source_fingerprint_for_revision
from twobrain_rec_server.observability.langfuse import (
    GenerationTraceContext,
    create_langfuse_client,
    deterministic_observation_id,
    deterministic_trace_id,
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
    model_transcript,
    reported_model_provenance,
)
from twobrain_rec_server.outcomes.models import (
    PROTOCOL_SCHEMA_VERSION,
    TEMPLATE_PROTOCOL_SECTIONS,
    OutcomeTranscriptSegment,
)
from twobrain_rec_server.outcomes.prompt_bundle import (
    PromptBundleError,
    bind_snapshot_from_metadata,
    load_execution_authority,
    snapshot_bundle_metadata,
)
from twobrain_rec_server.outcomes.prompts import (
    EXTRACTOR_PROMPT_NAME,
    VERIFIER_PROMPT_NAME,
    PromptSnapshot,
    canonical_json,
    prompt_snapshot_hash,
    validate_factual_extraction,
    validate_prompt_snapshot,
    validate_protocol_result,
    validate_protocol_verification,
)
from twobrain_rec_server.outcomes.service import (
    SummarySlotDefaultConflict,
    advance_summary_slot_state_version,
    ensure_summary_slot,
    load_outcome_transcript_segments,
    load_summary_slot,
    mark_meeting_default_slot,
)
from twobrain_rec_server.outcomes.templates import (
    BUILT_IN_BY_KEY,
    OUTCOME_CATEGORIES,
    built_in_template_for_key,
    built_in_template_for_version,
    prompt_name_for_template,
)
from twobrain_rec_server.processing.fences import (
    is_expired,
    lock_meeting_fence,
    meeting_is_deleted_or_deleting,
    normalize_db_timestamp,
)
from twobrain_rec_server.processing.results import (
    latest_processing_result_query,
    result_source_hash_is_attested,
)
from twobrain_rec_server.workflows.outcome_generation_workflow import (
    TranscriptSnapshotError,
    split_plaintext_transcript,
)
from twobrain_rec_server.workflows.temporal_client import outcome_generation_workflow_id

AI_GENERATOR_VERSION = "meeting-protocol-v2"
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


def _protocol_publication_proof(attempt, extract_call, draft_call, verify_call):
    if extract_call is None or draft_call is None or verify_call is None:
        raise OutcomeGenerationTerminalError("summary_publication_proof_invalid")
    envelope = verify_call.validated_result_json
    if not isinstance(envelope, dict) or "protocol" not in envelope:
        raise OutcomeGenerationTerminalError("summary_publication_proof_invalid")
    snapshot = _stored_prompt_snapshot(attempt)
    if snapshot is None:
        raise OutcomeGenerationTerminalError("summary_publication_proof_invalid")
    return {
        "extraction_call_id": str(extract_call.id),
        "extraction_hash": extract_call.validated_result_hash,
        "draft_call_id": str(draft_call.id), "verification_call_id": str(verify_call.id),
        "draft_hash": draft_call.validated_result_hash,
        "verification_result_hash": verify_call.validated_result_hash,
        "protocol_hash": _content_hash(envelope["protocol"]),
        "transcript_hash": draft_call.transcript_hash,
        "root_bundle_hash": snapshot.root_bundle_hash,
        "execution_authority_hash": extract_call.execution_authority_hash,
        "header_snapshot_hash": extract_call.header_snapshot_hash,
        "outcome_set_id": str(attempt.outcome_set_id),
    }


def _call_output(call):
    try:
        choice = call.raw_response_json["choices"][0]
        if choice.get("finish_reason") != "stop" or choice["message"].get("refusal"):
            raise ValueError("incomplete_response")
        return json.loads(choice["message"]["content"])
    except (KeyError, IndexError, TypeError, ValueError):
        raise OutcomeGenerationTerminalError("summary_publication_proof_invalid") from None


async def publish_model_generated_outcome(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    candidate_id: UUID,
    expected_current_outcome_set_id: UUID | str | None,
    settings: Settings,
    publication_proof: object | None = None,
    validate_only: bool = False,
) -> MeetingOutcomeSet:
    """Publish only the exact full document backed by all three retained calls."""
    if not isinstance(publication_proof, dict):
        raise OutcomeGenerationTerminalError("summary_publication_proof_missing")
    if not {"extraction_call_id", "draft_call_id", "verification_call_id"} <= publication_proof.keys():
        raise OutcomeGenerationTerminalError("summary_publication_proof_invalid")
    meeting, attempt = await _lock_candidate_meeting_and_attempt(
        db, workspace_id=workspace_id, candidate_id=candidate_id,
    )
    if bool((attempt.metadata_json or {}).get("evaluation_only")) != validate_only:
        raise OutcomeGenerationTerminalError("summary_evaluation_not_publishable")
    if (
        meeting is None or meeting.id != meeting_id or meeting_is_deleted_or_deleting(meeting)
        or attempt.status not in {"candidate", "accepted"} or attempt.outcome_set_id is None
    ):
        raise OutcomeGenerationTerminalError("summary_publication_fence_failed")
    await _ensure_candidate_access(db, meeting, attempt)
    await _ensure_execution_authority(db, attempt, settings)
    calls = [await _latest_protocol_call(db, attempt, sequence) for sequence in (1, 2, 3)]
    extract_call, draft_call, verify_call = calls
    outcome_set = await db.scalar(
        select(MeetingOutcomeSet).where(
            MeetingOutcomeSet.id == attempt.outcome_set_id,
            MeetingOutcomeSet.workspace_id == workspace_id, MeetingOutcomeSet.meeting_id == meeting_id,
            MeetingOutcomeSet.candidate_id == candidate_id, MeetingOutcomeSet.template_key == attempt.template_key,
            MeetingOutcomeSet.lifecycle_state == "active",
        ).with_for_update().execution_options(populate_existing=True)
    )
    try:
        if (
            any(call is None for call in calls) or outcome_set is None
            or outcome_set.protocol_state != "available"
            or outcome_set.protocol_schema_version != PROTOCOL_SCHEMA_VERSION
            or attempt.header_snapshot_json is None
            or publication_proof != _protocol_publication_proof(attempt, *calls)
        ):
            raise ValueError("incomplete_proof")
        segments = await _candidate_segments(db, attempt)
        transcript = canonical_transcript(segments)
        transcript_hash = sha256(transcript.encode("utf-8")).hexdigest()
        _, _, envelope = _validate_protocol_chain(attempt, calls, segments, transcript)
        protocol = envelope["protocol"]
        if (
            outcome_set.protocol_json != protocol
            or outcome_set.content_hash != _content_hash(protocol)
            or attempt.temporal_transcript_hash != transcript_hash
        ):
            raise ValueError("document_mismatch")
    except (KeyError, TypeError, ValueError, OutcomeGenerationTerminalError):
        raise OutcomeGenerationTerminalError("summary_publication_proof_invalid") from None
    if validate_only:
        await _ensure_candidate_fence(db, attempt)
        identity = await _current_source_identity(db, workspace_id=workspace_id, meeting_id=meeting_id)
        if identity != (
            attempt.media_revision_id, attempt.source_result_id,
            attempt.source_result_hash, attempt.source_fingerprint,
        ) or not await candidate_speaker_attribution_is_current(db, attempt):
            raise OutcomeGenerationTerminalError("summary_source_revision_stale")
        if is_expired(attempt.expires_at) or is_expired(outcome_set.expires_at):
            raise OutcomeGenerationTerminalError("summary_candidate_expired")
        return outcome_set
    try:
        expected_current_id = (
            expected_current_outcome_set_id
            if expected_current_outcome_set_id is None
            or isinstance(expected_current_outcome_set_id, UUID)
            else UUID(str(expected_current_outcome_set_id))
        )
    except (TypeError, ValueError):
        raise OutcomeGenerationTerminalError("summary_publication_proof_invalid") from None
    await _cas_summary_slot(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        template_key=str(attempt.template_key),
        replacement_outcome_set_id=outcome_set.id,
        expected_current_outcome_set_id=expected_current_id,
        expected_source_fingerprint=str(attempt.source_fingerprint),
        expected_deletion_epoch=int(attempt.deletion_epoch_at_start or 0),
        expected_access_policy_epoch=int(
            (attempt.metadata_json or {}).get("access_policy_epoch", 0)
        ),
    )
    attempt.status = "accepted"
    attempt.ended_at = attempt.ended_at or datetime.now(UTC)
    attempt.failure_code = None
    attempt.failure_reason = None
    await finalize_dispatch_for_candidate(
        db,
        workspace_id=workspace_id,
        candidate_id=candidate_id,
        outcome="completed",
    )
    await db.flush()
    return outcome_set


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
    slot = await load_summary_slot(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        template_key=template_key,
    )
    slot = slot or await ensure_summary_slot(
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
    result = (
        await db.scalar(
            latest_processing_result_query(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=latest_revision.id,
            )
        )
        if latest_revision is not None
        else None
    )
    if not canonical_speech_available(result):
        raise OutcomeGenerationTerminalError("summary_transcript_unavailable")
    if not result_source_hash_is_attested(result):
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
        current_definition = BUILT_IN_BY_KEY.get(template_key)
        if (
            definition is None
            or current_definition is None
            or current_definition.version != template_version
        ):
            raise OutcomeGenerationTerminalError("summary_template_unavailable")
        prompt_name = definition.prompt_name
        output_language = "ru"
        detail_level = "detailed"
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
        if (
            accepted_automatic is not None
            and accepted_automatic.outcome_set_id == current_outcome_set_id
        ):
            return accepted_automatic
    if template is not None and template.status != "active":
        # Archived/deleted templates remain valid only for an exact replay of
        # their pinned candidate; they cannot start a new intent.
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
                    MeetingOutcomeGenerationAttempt.outcome_set_id == current_outcome_set_id,
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
            "summary_slot_id": str(slot.id),
            "expected_current_outcome_set_id": (
                str(current_outcome_set_id) if current_outcome_set_id is not None else None
            ),
            "speaker_attribution_revision": speaker_revision,
            # The current cabinet path has no mutable per-meeting access epoch
            # yet; pin the explicit zero so publication cannot silently omit
            # the CAS input. A future access-policy revision increments this
            # value at request creation.
            "access_policy_epoch": 0,
            **(
                {"request_intent_id": str(request_intent_id)}
                if request_intent_id is not None
                else {}
            ),
        },
    )
    db.add(attempt)
    advance_summary_slot_state_version(slot)
    await db.flush()
    return attempt


def summary_workflow_payload(attempt: MeetingOutcomeGenerationAttempt) -> dict[str, object]:
    """Return the immutable slot-scoped identity carried into Temporal."""
    metadata = attempt.metadata_json or {}
    return {
        "candidate_id": str(attempt.candidate_id),
        "source_result_id": str(attempt.source_result_id),
        "template_key": attempt.template_key,
        "template_version": attempt.template_version,
        "summary_slot_id": metadata.get("summary_slot_id"),
        "expected_current_outcome_set_id": metadata.get(
            "expected_current_outcome_set_id"
        ),
    }


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
    ):
        return None
    definition = built_in_template_for_key(workspace.default_summary_template_key)
    template_id = workspace.default_summary_template_id
    if definition is None and template_id is None:
        return None
    template_key = workspace.default_summary_template_key
    template_version = definition.version if template_id is None else workspace.default_summary_template_version
    with suppress(SummarySlotDefaultConflict):
        # The workspace automatic format is the product default for a meeting.
        # Persist that fact before creating the candidate so fresh imports and
        # populated slots are both visible through the default egress. An
        # explicit default selected earlier remains authoritative.
        await mark_meeting_default_slot(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            template_key=template_key,
            resolution_source="workspace",
            resolution_version=f"workspace-default:{template_key}:v{template_version}",
            resolved_at=datetime.now(UTC),
        )
    slot = await ensure_summary_slot(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        template_key=template_key,
    )
    try:
        attempt = await create_summary_candidate(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            requested_by_user_id=meeting.created_by_user_id,
            template_key=template_key,
            template_id=template_id,
            template_version=template_version,
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
        payload=summary_workflow_payload(attempt),
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
        _, attempt = await _lock_candidate_meeting_and_attempt(
            db, workspace_id=workspace_id, candidate_id=candidate_id,
        )
        attempt = await _ensure_candidate_source_or_mark_stale(db, attempt)
        if attempt.prompt_name is None:
            raise OutcomeGenerationTerminalError("summary_prompt_not_selected")
        try:
            stored = _stored_prompt_snapshot(attempt)
        except ValueError as exc:
            raise OutcomeGenerationTerminalError("summary_prompt_snapshot_corrupt") from exc
        if stored is not None:
            await _ensure_execution_authority(db, attempt, settings)
            await db.commit()
            return _prompt_result(stored, settings)
        try:
            bundle, authority = await load_execution_authority(db, settings)
            snapshot = bundle.child(attempt.prompt_name)
        except PromptBundleError:
            raise OutcomeGenerationDependencyError("summary_execution_authority_unavailable") from None
        extractor = bundle.child(EXTRACTOR_PROMPT_NAME)
        verifier = bundle.child(VERIFIER_PROMPT_NAME)
        attempt.prompt_version = snapshot.version
        attempt.prompt_source = snapshot.source
        attempt.prompt_definition = snapshot.prompt
        attempt.prompt_config = snapshot.config
        attempt.prompt_hash = snapshot.canonical_hash
        attempt.output_schema_version = str(
            snapshot.config["response_format"]["json_schema"]["name"]
        )
        attempt.model_route = snapshot.model
        attempt.model_parameters = snapshot.model_parameters
        metadata = dict(attempt.metadata_json or {})
        metadata["prompt_bundle"] = snapshot_bundle_metadata(snapshot)
        metadata["execution_authority"] = authority
        metadata["pipeline"] = "extract-synthesize-verify-v1"
        metadata["evaluation_only"] = authority["kind"] == "evaluation"
        for key, child in (("extractor_prompt", extractor), ("verifier_prompt", verifier)):
            metadata[key] = {
                "name": child.name, "version": child.version,
                "prompt": child.prompt, "config": child.config,
                "hash": child.canonical_hash, "source": child.source,
            }
        attempt.metadata_json = metadata
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
    return _prompt_result(snapshot, settings)


async def _ensure_execution_authority(db, attempt, settings):
    metadata = attempt.metadata_json or {}
    pinned = metadata.get("execution_authority")
    if not isinstance(pinned, dict) or metadata.get("pipeline") != "extract-synthesize-verify-v1":
        raise OutcomeGenerationTerminalError("summary_execution_authority_missing")
    try:
        bundle, authority = await load_execution_authority(db, settings, pinned=pinned)
        for sequence in (1, 2, 3):
            stored = _stage_snapshot(attempt, sequence)
            expected = bundle.child(stored.name)
            if (stored.version != expected.version or stored.canonical_hash != expected.canonical_hash
                    or snapshot_bundle_metadata(stored) != snapshot_bundle_metadata(expected)):
                raise ValueError
        if bool(metadata.get("evaluation_only")) != (authority["kind"] == "evaluation"):
            raise ValueError
        return authority
    except (PromptBundleError, ValueError):
        raise OutcomeGenerationTerminalError("summary_execution_authority_invalid") from None


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
    evaluation_source_guard: Callable[[], Awaitable[None]] | None = None,
) -> dict[str, Any]:
    """Extract, synthesize and verify through independently durable zero-replay calls."""
    if (settings.env == "protocol-evaluation") != (evaluation_source_guard is not None):
        raise OutcomeGenerationTerminalError("summary_evaluation_isolation_required")
    async with sessionmaker() as db:
        await _apply_worker_workspace(db, workspace_id)
        meeting, attempt = await _lock_candidate_meeting_and_attempt(
            db, workspace_id=workspace_id, candidate_id=candidate_id,
        )
        if meeting is None or meeting_is_deleted_or_deleting(meeting):
            raise OutcomeGenerationTerminalError("meeting_deleting")
        authority = await _ensure_execution_authority(db, attempt, settings)
        evaluation_only = authority["kind"] == "evaluation"
        if evaluation_only != (evaluation_source_guard is not None):
            raise OutcomeGenerationTerminalError("summary_evaluation_source_guard_required")
        await _check_evaluation_source(evaluation_source_guard)
        if attempt.status in {"candidate", "accepted"}:
            if attempt.temporal_transcript_hash != expected_snapshot_hash:
                raise OutcomeGenerationTerminalError("summary_transcript_changed")
            calls = [await _latest_protocol_call(db, attempt, sequence) for sequence in (1, 2, 3)]
            verify_call = calls[2]
            outcome = await publish_model_generated_outcome(
                db, workspace_id=workspace_id, meeting_id=meeting.id, candidate_id=candidate_id,
                expected_current_outcome_set_id=(
                    attempt.outcome_set_id if attempt.status == "accepted"
                    else (attempt.metadata_json or {}).get("expected_current_outcome_set_id")
                ),
                publication_proof=_protocol_publication_proof(attempt, *calls), settings=settings,
                validate_only=evaluation_only,
            )
            await db.commit()
            return _execution_result(attempt, verify_call, reused=True, outcome_id=outcome.id)
    for sequence in (1, 2, 3):
        result = await _execute_protocol_call(
            sessionmaker, workspace_id=workspace_id, candidate_id=candidate_id,
            expected_snapshot_hash=expected_snapshot_hash, settings=settings, sequence=sequence,
            evaluation_source_guard=evaluation_source_guard,
        )
        if result["state"] != "stage_ready":
            return result
    raise OutcomeGenerationTerminalError("summary_verification_missing")


async def _latest_protocol_call(db, attempt, sequence):
    return await db.scalar(
        select(GenerationCall).where(
            GenerationCall.workspace_id == attempt.workspace_id,
            GenerationCall.meeting_id == attempt.meeting_id,
            GenerationCall.candidate_id == attempt.candidate_id,
            GenerationCall.call_sequence == sequence,
        ).order_by(GenerationCall.provider_attempt.desc()).with_for_update()
        .execution_options(populate_existing=True)
    )


def _execution_result(attempt, call, *, reused=False, outcome_id=None):
    return {
        "candidate_id": str(attempt.candidate_id),
        "generation_call_id": str(call.id) if call is not None else None,
        "outcome_set_id": str(outcome_id or attempt.outcome_set_id) if outcome_id or attempt.outcome_set_id else None,
        "state": attempt.status, "failure_code": attempt.failure_code, "reused": reused,
    }


def _protocol_sections(attempt):
    return tuple(section for category in _template_sections(attempt) for section in TEMPLATE_PROTOCOL_SECTIONS[category])


def _freeze_protocol_header(meeting, attempt, segments):
    participants = {}
    for segment in segments:
        key = segment.speaker_key or segment.speaker_label
        participants.setdefault(key, {
            "speaker_key": key, "label": segment.speaker_label,
            "attribution_state": segment.attribution_state,
        })
    return {
        "title": meeting.title,
        "started_at": meeting.started_at.isoformat() if meeting.started_at else None,
        "ended_at": meeting.ended_at.isoformat() if meeting.ended_at else None,
        "duration_seconds": meeting.duration_seconds,
        "timezone_offset_minutes": meeting.recording_display_timezone_offset_minutes,
        "input_type": "transcript", "participants": list(participants.values()),
        "output_language": attempt.output_language, "detail_level": attempt.detail_level,
        "template_key": attempt.template_key, "template_version": attempt.template_version,
        "template_name": attempt.display_format_name, "sections": list(_protocol_sections(attempt)),
        "source_result_id": str(attempt.source_result_id),
    }


def _enrich_protocol(draft, header, segments):
    by_sequence = {segment.sequence: segment for segment in segments}

    def enrich(value):
        if isinstance(value, list):
            return [enrich(child) for child in value]
        if not isinstance(value, dict):
            return value
        if "sequence" in value and "quote" in value:
            segment = by_sequence[value["sequence"]]
            return {
                **value, "transcript_segment_id": str(segment.segment_id),
                "start_seconds": float(segment.start_seconds),
                "end_seconds": float(segment.end_seconds), "speaker_label": segment.speaker_label,
                "source_role": segment.source_role, "evidence_kind": "segment",
            }
        return {key: enrich(child) for key, child in value.items()}

    return {"schema_version": PROTOCOL_SCHEMA_VERSION, "header": header, **enrich(draft)}


def _protocol_messages(snapshot, attempt, transcript, draft=None, *, extraction=None):
    return compile_prompt_messages(
        snapshot, transcript_json=model_transcript(transcript), output_language=attempt.output_language or "ru",
        detail_level=attempt.detail_level or "detailed", template_sections=_template_sections(attempt),
        draft_json=canonical_json(draft) if draft is not None else None,
        extraction_json=canonical_json(extraction) if extraction is not None else None,
    )


async def _finish_protocol_failure(db, attempt, code, *, status="failed"):
    attempt.status = status
    attempt.failure_code = code
    attempt.failure_reason = code
    attempt.ended_at = datetime.now(UTC)
    await finalize_dispatch_for_candidate(
        db, workspace_id=attempt.workspace_id, candidate_id=attempt.candidate_id,
        outcome="cancelled" if status in {"stale", "cancelled", "expired"} else "failed",
        failure_code=code,
    )


async def _check_evaluation_source(guard):
    if guard is None:
        return
    try:
        await guard()
    except OutcomeGenerationTerminalError as exc:
        if str(exc) == "evaluation_source_read_failed":
            raise OutcomeGenerationDependencyError("evaluation_source_read_failed") from None
        raise


async def _execute_protocol_call(
    sessionmaker, *, workspace_id, candidate_id, expected_snapshot_hash, settings, sequence,
    evaluation_source_guard=None,
):
    started_at = datetime.now(UTC)
    await _check_evaluation_source(evaluation_source_guard)
    async with sessionmaker() as db:
        await _apply_worker_workspace(db, workspace_id)
        meeting, attempt = await _lock_candidate_meeting_and_attempt(
            db, workspace_id=workspace_id, candidate_id=candidate_id,
        )
        attempt = await _ensure_candidate_source_or_mark_stale(db, attempt)
        if is_expired(attempt.expires_at):
            _expire_candidate_attempt(attempt)
            await db.commit()
            raise OutcomeGenerationTerminalError("summary_candidate_expired")
        authority = await _ensure_execution_authority(db, attempt, settings)
        evaluation_only = authority["kind"] == "evaluation"
        if evaluation_only != (evaluation_source_guard is not None):
            raise OutcomeGenerationTerminalError("summary_evaluation_source_guard_required")
        snapshot = _stage_snapshot(attempt, sequence)
        segments = await _candidate_segments(db, attempt)
        transcript = canonical_transcript(segments)
        transcript_hash = sha256(transcript.encode("utf-8")).hexdigest()
        if transcript_hash != expected_snapshot_hash or transcript_hash != attempt.temporal_transcript_hash:
            raise OutcomeGenerationTerminalError("summary_transcript_changed")
        sections = _protocol_sections(attempt)
        prior_calls = [await _latest_protocol_call(db, attempt, index) for index in range(1, sequence)]
        prior_outputs = _validate_protocol_chain(attempt, prior_calls, segments, transcript) if prior_calls else []
        extraction = prior_outputs[0] if sequence > 1 else None
        draft = prior_outputs[1] if sequence == 3 else None
        predecessor = prior_calls[-1] if prior_calls else None
        existing = await _latest_protocol_call(db, attempt, sequence)
        provider_attempt = 1
        if existing is not None:
            if existing.call_state == "completed":
                _validate_protocol_chain(attempt, [*prior_calls, existing], segments, transcript)
                if sequence < 3:
                    return {**_execution_result(attempt, existing, reused=True), "state": "stage_ready"}
                return await _project_protocol_outcome(
                    db, attempt, [*prior_calls, existing], settings=settings,
                    validate_only=evaluation_only, reused=True,
                )
            if existing.call_state in {"reserved", "ambiguous"}:
                if existing.call_state == "reserved":
                    _complete_generation_call_without_response(existing, call_state="ambiguous")
                await _finish_protocol_failure(db, attempt, "summary_provider_outcome_ambiguous")
                await db.commit()
                raise OutcomeGenerationTerminalError("summary_provider_outcome_ambiguous")
            if not _generation_call_is_retryable(existing):
                raise OutcomeGenerationTerminalError("summary_provider_attempt_not_retryable")
            provider_attempt = existing.provider_attempt + 1
        if settings.litellm_base_url is None:
            raise OutcomeGenerationDependencyError("litellm_endpoint_unavailable")
        api_key = _read_secret(settings.litellm_api_key_file)
        if attempt.header_snapshot_json is None:
            if sequence != 1 or existing is not None:
                raise OutcomeGenerationTerminalError("summary_header_snapshot_missing")
            attempt.header_snapshot_json = _freeze_protocol_header(meeting, attempt, segments)
        header = attempt.header_snapshot_json
        messages = _protocol_messages(
            snapshot, attempt, transcript, draft, extraction=extraction if sequence == 2 else None,
        )
        request = snapshot.litellm_request(messages)
        call = GenerationCall(
            workspace_id=workspace_id, meeting_id=attempt.meeting_id, candidate_id=candidate_id,
            provider_attempt=provider_attempt, call_sequence=sequence,
            trace_id=attempt.langfuse_trace_id or deterministic_trace_id(candidate_id),
            observation_id=deterministic_observation_id(candidate_id, provider_attempt=provider_attempt, call_sequence=sequence),
            call_state="reserved", started_at=started_at, request_json=request, transcript_text=transcript,
            request_hash=_content_hash(request), transcript_hash=transcript_hash, export_status="pending",
            execution_authority_json=authority, execution_authority_hash=_content_hash(authority),
            predecessor_call_id=predecessor.id if predecessor else None,
            predecessor_result_hash=predecessor.validated_result_hash if predecessor else None,
            header_snapshot_hash=_content_hash(header),
        )
        db.add(call)
        attempt.attempt_count += 1
        attempt.status = "generating"
        await db.commit()
        call_id = call.id
        # Each logical stage has its own provider idempotency identity.
        idempotency_key = f"{attempt.idempotency_key}:call:{sequence}"

    gateway = LiteLLMGateway(
        base_url=str(settings.litellm_base_url),
        api_key=api_key,
        timeout_seconds=settings.litellm_request_timeout_seconds,
    )
    async with sessionmaker() as db:
        await _apply_worker_workspace(db, workspace_id)
        _, attempt = await _lock_candidate_meeting_and_attempt(db, workspace_id=workspace_id, candidate_id=candidate_id)
        try:
            await _ensure_candidate_source_fence(db, attempt)
            await _ensure_execution_authority(db, attempt, settings)
            await _check_evaluation_source(evaluation_source_guard)
        except OutcomeGenerationDependencyError as exc:
            # The provider was not called: a later attempt is safe, not ambiguous.
            call = await db.get(GenerationCall, call_id, with_for_update=True)
            _complete_generation_call_without_response(call, call_state="failed")
            call.validated_result_json = {"generation_error": {
                "code": str(exc), "retryable_classification": True,
                "egress_state": "not_sent", "response_received": False,
            }}
            call.validated_result_hash = _content_hash(call.validated_result_json)
            await db.commit()
            raise
        except OutcomeGenerationTerminalError as exc:
            call = await db.get(GenerationCall, call_id, with_for_update=True)
            _complete_generation_call_without_response(call, call_state="failed")
            await _finish_protocol_failure(
                db, attempt, str(exc), status="stale" if str(exc) == "summary_source_revision_stale" else "cancelled",
            )
            await db.commit()
            raise
        # Release the fence before network I/O so source changes and deletion never wait on the provider.
        await db.commit()
        response = None
        error = None
        try:
            response = await gateway.generate(snapshot=snapshot, messages=messages, idempotency_key=idempotency_key)
        except LiteLLMError as exc:
            error = exc
        meeting, attempt = await _lock_candidate_meeting_and_attempt(db, workspace_id=workspace_id, candidate_id=candidate_id)
        call = await db.get(GenerationCall, call_id, with_for_update=True, populate_existing=True)
        if call is None:
            raise OutcomeGenerationTerminalError("summary_generation_call_missing")
        completed_at = datetime.now(UTC)
        validation_failure = None
        if error is not None:
            call.completed_at = completed_at
            call.raw_response_json = error.raw_response
            call.actual_model, call.actual_provider = reported_model_provenance(error.raw_response)
            call.raw_response_hash = _content_hash(error.raw_response) if error.raw_response is not None else None
            call.validated_result_json = {"generation_error": {
                "code": error.code, "retryable_classification": error.retryable,
                "egress_state": error.egress_state, "response_received": error.raw_response is not None,
            }}
            call.validated_result_hash = _content_hash(call.validated_result_json)
            call.call_state = "ambiguous" if error.egress_state == "unknown" else "failed" if error.retryable else "completed"
            call.export_status = "pending" if error.raw_response is not None else "not_required"
            validation_failure = "summary_provider_outcome_ambiguous" if error.egress_state == "unknown" else error.code
        else:
            try:
                if sequence == 1:
                    validated = validate_factual_extraction(response.parsed_content, segments=segments)
                elif sequence == 2:
                    validated = validate_protocol_result(response.parsed_content, segments=segments, sections=sections)
                else:
                    verification = validate_protocol_verification(response.parsed_content, segments=segments)
                    if verification["verdict"] != "pass":
                        validated = {"verification": verification, "draft_hash": predecessor.validated_result_hash,
                                     "extraction_hash": prior_calls[0].validated_result_hash}
                        validation_failure = "summary_verification_failed"
                    else:
                        validated = {
                            "verification": verification, "draft_hash": predecessor.validated_result_hash,
                            "extraction_hash": prior_calls[0].validated_result_hash,
                            "protocol": _enrich_protocol(draft, header, segments),
                        }
            except ValueError:
                validated = {"validation_error": {"code": "summary_response_invalid"}}
                validation_failure = "summary_response_invalid"
            _complete_generation_call_with_response(call, response=response, validated_result=validated, completed_at=completed_at)
            if call.validated_result_json != validated:
                validation_failure = "generation_call_provenance_mismatch"

        # Always retain completed response truth, even if deletion/cancellation won the race.
        if evaluation_source_guard is not None:
            try:
                await _check_evaluation_source(evaluation_source_guard)
            except OutcomeGenerationDependencyError:
                # Capture precedes source recheck. Preserve completed response truth
                # and the active candidate so retry can validate/project without inference.
                if (
                    attempt.status in ACTIVE_CANDIDATE_STATUSES
                    and validation_failure
                    and not (error is not None and error.retryable)
                ):
                    await _finish_protocol_failure(db, attempt, validation_failure)
                await db.commit()
                raise
            except OutcomeGenerationTerminalError as exc:
                await _finish_protocol_failure(db, attempt, str(exc), status="cancelled")
                await db.commit()
                raise
        if attempt.status not in ACTIVE_CANDIDATE_STATUSES:
            await db.commit()
            return _execution_result(attempt, call)
        if meeting is None or meeting_is_deleted_or_deleting(meeting) or int(meeting.deletion_epoch or 0) != int(attempt.deletion_epoch_at_start or 0):
            await _finish_protocol_failure(db, attempt, "meeting_deleting", status="cancelled")
            await db.commit()
            raise OutcomeGenerationTerminalError("meeting_deleting")
        if is_expired(attempt.expires_at):
            _expire_candidate_attempt(attempt, ended_at=completed_at)
            await db.commit()
            raise OutcomeGenerationTerminalError("summary_candidate_expired")
        try:
            await _ensure_candidate_source_fence(db, attempt)
            await _ensure_execution_authority(db, attempt, settings)
        except OutcomeGenerationTerminalError as exc:
            await _finish_protocol_failure(db, attempt, str(exc), status="stale")
            await db.commit()
            return _execution_result(attempt, call)
        if validation_failure:
            if error is not None and error.retryable:
                attempt.failure_code = error.code
                await db.commit()
                raise OutcomeGenerationDependencyError(error.code)
            await _finish_protocol_failure(db, attempt, validation_failure)
            await db.commit()
            return _execution_result(attempt, call)
        if sequence < 3:
            await db.commit()
            return {**_execution_result(attempt, call), "state": "stage_ready"}
        return await _project_protocol_outcome(
            db, attempt, [*prior_calls, call], settings=settings, validate_only=evaluation_only,
        )


async def _project_protocol_outcome(db, attempt, calls, *, settings, validate_only, reused=False):
    """Rebuild only the local projection; publication revalidates all retained calls."""
    extract_call, _, call = calls
    envelope = call.validated_result_json
    if not isinstance(envelope, dict) or "protocol" not in envelope or call.completed_at is None:
        raise OutcomeGenerationTerminalError("summary_publication_proof_invalid")
    protocol = envelope["protocol"]
    completed_at = normalize_db_timestamp(call.completed_at)
    workspace_id, candidate_id = attempt.workspace_id, attempt.candidate_id
    outcome = MeetingOutcomeSet(
        workspace_id=workspace_id, meeting_id=attempt.meeting_id, media_revision_id=attempt.media_revision_id,
        processing_result_id=attempt.source_result_id, candidate_id=candidate_id,
        status="available", protocol_state="available", protocol_schema_version=PROTOCOL_SCHEMA_VERSION,
        protocol_json=protocol, source_kind="litellm", generator_kind="litellm", generator_version=AI_GENERATOR_VERSION,
        source_result_hash=attempt.source_result_hash, source_fingerprint=attempt.source_fingerprint,
        deletion_epoch_at_start=attempt.deletion_epoch_at_start, expires_at=attempt.expires_at,
        content_hash=_content_hash(protocol), template_id=attempt.template_id, template_key=attempt.template_key,
        template_version=attempt.template_version, generator_config_hash=attempt.generator_config_hash,
        output_language=attempt.output_language, detail_level=attempt.detail_level, revision_state="candidate",
        requested_by_user_id=attempt.requested_by_user_id, started_at=extract_call.started_at, generated_at=completed_at,
        latency_ms=max(0, int((completed_at - normalize_db_timestamp(extract_call.started_at)).total_seconds() * 1000)),
    )
    db.add(outcome)
    await db.flush()
    attempt.outcome_set_id = outcome.id
    attempt.status = "candidate"
    attempt.failure_code = None
    try:
        await publish_model_generated_outcome(
            db, workspace_id=workspace_id, meeting_id=attempt.meeting_id, candidate_id=candidate_id,
            expected_current_outcome_set_id=(attempt.metadata_json or {}).get("expected_current_outcome_set_id"),
            publication_proof=_protocol_publication_proof(attempt, *calls), settings=settings,
            validate_only=validate_only,
        )
    except OutcomeGenerationTerminalError as exc:
        outcome.status = "blocked"
        outcome.protocol_state = "blocked"
        outcome.failure_reason = str(exc)
        outcome.failure_source = "publication"
        await _finish_protocol_failure(db, attempt, str(exc))
    await db.commit()
    return _execution_result(attempt, call, outcome_id=outcome.id, reused=reused)


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
        # Observability replays immutable provenance, never an executable old
        # generator. It must remain deliverable after deletion or a code upgrade.
        prompt_name, prompt_version, prompt_hash, selected_model = _observation_prompt_identity(attempt, call.call_sequence)
        _verify_generation_call_hashes(call)
        claim_started_at = now
        call.export_status = "publishing"
        call.export_attempt_count += 1
        call.last_export_attempt_at = claim_started_at
        call.next_export_attempt_at = None
        call.last_export_error_code = None
        await db.commit()
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
                prompt_hash=prompt_hash,
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
    return call.call_state in {"completed", "failed", "ambiguous"}


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
    call.provider_request_id = getattr(response, "provider_request_id", None)
    call.token_usage = getattr(response, "token_usage", None)
    call.cost_details = getattr(response, "cost_details", None)
    call.raw_response_json = getattr(response, "raw_response", None)
    call.actual_model, call.actual_provider = reported_model_provenance(call.raw_response_json)
    if (getattr(response, "actual_model", None), getattr(response, "actual_provider", None)) != (
        call.actual_model, call.actual_provider,
    ):
        validated_result = {"validation_error": {"code": "generation_call_provenance_mismatch"}}
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
        or is_expired(replacement.expires_at)
        or replacement.source_fingerprint != expected_source_fingerprint
        or int(replacement.deletion_epoch_at_start or 0) != int(expected_deletion_epoch)
    ):
        raise SummarySlotCASConflict()

    source_identity = None
    if replacement.candidate_id is not None or replacement.source_result_hash is not None:
        source_identity = await _current_source_identity(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
        )
    if replacement.candidate_id is not None and (
        source_identity is None
        or replacement.media_revision_id != source_identity[0]
        or replacement.processing_result_id != source_identity[1]
        or replacement.source_result_hash != source_identity[2]
        or replacement.source_fingerprint != source_identity[3]
    ):
        raise SummarySlotCASConflict()
    if (
        replacement.candidate_id is None
        and replacement.source_result_hash is not None
        and (
            source_identity is None
            or replacement.source_result_hash != source_identity[2]
        )
    ):
        raise SummarySlotCASConflict()

    attempt = None
    if replacement.candidate_id is not None:
        attempt = await db.scalar(
            select(MeetingOutcomeGenerationAttempt)
            .where(
                MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
                MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
                MeetingOutcomeGenerationAttempt.candidate_id == replacement.candidate_id,
                MeetingOutcomeGenerationAttempt.outcome_set_id == replacement.id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if (
            attempt is None
            or attempt.template_key != template_key
            or attempt.processing_result_id != replacement.processing_result_id
            or attempt.media_revision_id != replacement.media_revision_id
            or attempt.source_result_hash != replacement.source_result_hash
            or attempt.source_fingerprint != replacement.source_fingerprint
            or int(attempt.deletion_epoch_at_start or 0) != int(expected_deletion_epoch)
            or is_expired(attempt.expires_at)
            or attempt.status not in {"candidate", "accepted"}
        ):
            raise SummarySlotCASConflict()
        actual_access_policy_epoch = (attempt.metadata_json or {}).get("access_policy_epoch")
        if (
            expected_access_policy_epoch is None
            or expected_access_policy_epoch != actual_access_policy_epoch
        ):
            raise SummarySlotCASConflict()
    elif expected_access_policy_epoch is not None:
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
    advance_summary_slot_state_version(slot)
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
    del db, workspace_id, meeting_id, candidate_id, requested_by_user_id
    del accept, expected_current_outcome_set_id
    raise OutcomeGenerationTerminalError("summary_candidate_deprecated")


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


async def _current_source_identity(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> tuple[UUID | None, UUID, str | None, str] | None:
    """Return the locked-meeting source tuple used by publication fences."""
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
    expected_revision_id = latest_revision.id if latest_revision is not None else None
    latest_result = (
        await db.scalar(
            latest_processing_result_query(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                media_revision_id=expected_revision_id,
            )
        )
        if expected_revision_id is not None
        else None
    )
    if latest_result is None:
        return None
    if latest_revision is None:
        fingerprint = f"result:{latest_result.id}"
    else:
        try:
            fingerprint = source_fingerprint_for_revision(latest_revision)
        except ValueError:
            return None
    return (
        expected_revision_id,
        latest_result.id,
        latest_result.source_result_hash,
        fingerprint,
    )


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


async def _ensure_candidate_access(db, meeting, attempt):
    """Reauthorize the owner-only generation contract under existing request RLS.

    Worker RLS cannot see identity/membership rows. Use only the locked meeting's
    exact owner/workspace, read status (no profiles), then restore the caller.
    Shared locks serialize publication with deactivation/membership revocation;
    pre-egress transactions release them before any provider I/O.
    """
    owner_id = meeting.created_by_user_id
    if owner_id is None or attempt.requested_by_user_id != owner_id:
        raise OutcomeGenerationTerminalError("summary_source_access_revoked")
    previous = db.info.get("tenant_context")
    try:
        await apply_tenant_context(db, TenantDatabaseContext(
            organization_id=ZERO_UUID, workspace_id=meeting.workspace_id,
            user_id=owner_id, context_kind="request",
        ))
        organization_id = await db.scalar(select(Workspace.organization_id).where(
            Workspace.id == meeting.workspace_id,
        ))
        if organization_id is None:
            raise OutcomeGenerationTerminalError("summary_source_access_revoked")
        await apply_tenant_context(db, TenantDatabaseContext(
            organization_id=organization_id, workspace_id=meeting.workspace_id,
            user_id=owner_id, context_kind="request",
        ))
        active_owner = await db.scalar(
            select(UserIdentity.id).join(WorkspaceMembership, WorkspaceMembership.user_id == UserIdentity.id)
            .where(
                UserIdentity.id == owner_id, UserIdentity.status == "active",
                WorkspaceMembership.workspace_id == meeting.workspace_id,
                WorkspaceMembership.status == "active",
            ).with_for_update(read=True)
        )
        if active_owner is None:
            raise OutcomeGenerationTerminalError("summary_source_access_revoked")
    finally:
        if previous is None:
            await _apply_worker_workspace(db, meeting.workspace_id)
        else:
            db.info["tenant_context"] = previous
            await rehydrate_tenant_context(db)


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
    await _ensure_candidate_access(db, meeting, attempt)
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
    latest_result = (
        await db.scalar(
            latest_processing_result_query(
                workspace_id=attempt.workspace_id,
                meeting_id=attempt.meeting_id,
                media_revision_id=expected_revision_id,
            )
        )
        if expected_revision_id is not None
        else None
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
        or not result_source_hash_is_attested(latest_result)
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
    bundle_metadata = (attempt.metadata_json or {}).get("prompt_bundle")
    if bundle_metadata is not None:
        try:
            snapshot = bind_snapshot_from_metadata(snapshot, bundle_metadata)
        except PromptBundleError as exc:
            raise OutcomeGenerationTerminalError("summary_prompt_snapshot_corrupt") from exc
    elif snapshot.source == "langfuse_production":
        raise OutcomeGenerationTerminalError("summary_prompt_snapshot_corrupt")
    expected_generator_hash = _ai_generator_config_hash(
        template_id=attempt.template_id, template_key=attempt.template_key,
        template_version=attempt.template_version, template_sections=_template_sections(attempt),
        output_language=attempt.output_language, detail_level=attempt.detail_level,
        snapshot=snapshot,
    )
    if (
        attempt.model_route != snapshot.model
        or canonical_json(attempt.model_parameters) != canonical_json(snapshot.model_parameters)
        or attempt.generator_config_hash != expected_generator_hash
    ):
        raise OutcomeGenerationTerminalError("generation_call_request_mismatch")
    return snapshot


def _observation_prompt_identity(attempt, sequence):
    metadata = attempt.metadata_json or {}
    # Historical observation delivery has its retained stage layout, never execution authority.
    three_stage = metadata.get("pipeline") == "extract-synthesize-verify-v1"
    if sequence == (2 if three_stage else 1):
        name, version, prompt, config, digest = (
            attempt.prompt_name, attempt.prompt_version, attempt.prompt_definition,
            attempt.prompt_config, attempt.prompt_hash,
        )
    elif sequence == (3 if three_stage else 2) or (three_stage and sequence == 1):
        value = metadata.get("extractor_prompt" if sequence == 1 else "verifier_prompt") or {}
        name, version, prompt, config, digest = (value.get(key) for key in ("name", "version", "prompt", "config", "hash"))
    else:
        raise OutcomeGenerationTerminalError("summary_prompt_not_pinned")
    if (
        not isinstance(name, str) or type(version) is not int or version < 1
        or not isinstance(config, dict) or prompt is None
        or prompt_snapshot_hash(prompt=prompt, config=config) != digest
        or not isinstance(config.get("model"), str)
    ):
        raise OutcomeGenerationTerminalError("summary_prompt_snapshot_corrupt")
    return name, version, digest, config["model"]


def _stored_verifier_snapshot(attempt: MeetingOutcomeGenerationAttempt) -> PromptSnapshot:
    return _stored_stage_child(attempt, "verifier_prompt", VERIFIER_PROMPT_NAME)


def _stored_stage_child(attempt, key, name):
    value = (attempt.metadata_json or {}).get(key)
    try:
        if not isinstance(value, dict) or value["name"] != name:
            raise ValueError("stage_missing")
        snapshot = validate_prompt_snapshot(
            name=value["name"], version=value["version"], prompt_type="chat",
            prompt=value["prompt"], config=value["config"], source=value["source"],
        )
        if snapshot.canonical_hash != value["hash"]:
            raise ValueError("verifier_hash_mismatch")
        return bind_snapshot_from_metadata(snapshot, (attempt.metadata_json or {}).get("prompt_bundle"))
    except (KeyError, TypeError, ValueError):
        raise OutcomeGenerationTerminalError("summary_stage_snapshot_corrupt") from None


def _stage_snapshot(attempt, sequence):
    if sequence == 1:
        return _stored_stage_child(attempt, "extractor_prompt", EXTRACTOR_PROMPT_NAME)
    if sequence == 2:
        snapshot = _stored_prompt_snapshot(attempt)
        if snapshot is not None:
            return snapshot
    if sequence == 3:
        return _stored_verifier_snapshot(attempt)
    raise OutcomeGenerationTerminalError("summary_prompt_not_pinned")


def _prompt_result(snapshot: PromptSnapshot, settings: Settings) -> dict[str, object]:
    return {
        "prompt_name": snapshot.name,
        "prompt_version": snapshot.version,
        "prompt_hash": snapshot.canonical_hash,
        "model_route": snapshot.model,
        # Extraction, synthesis, verification plus source checks and durable storage.
        "generation_timeout_seconds": 3 * settings.litellm_request_timeout_seconds + 120,
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
        model_parameters = snapshot.model_parameters
        response_format = snapshot.config.get("response_format")
        if isinstance(response_format, dict):
            json_schema = response_format.get("json_schema")
            if isinstance(json_schema, dict):
                output_schema_version = str(json_schema.get("name") or "")
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
                "root_bundle": snapshot_bundle_metadata(snapshot) if snapshot else None,
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


def _verify_generation_call_execution(
    attempt: MeetingOutcomeGenerationAttempt, call: GenerationCall, *, draft=None, extraction=None,
) -> None:
    """New publication/reuse only; never apply this to historical observation delivery."""
    if (call.actual_model, call.actual_provider) != reported_model_provenance(call.raw_response_json):
        raise OutcomeGenerationTerminalError("generation_call_provenance_mismatch")
    if ((call.call_sequence == 2) != (extraction is not None)
            or (call.call_sequence == 3) != (draft is not None)):
        raise OutcomeGenerationTerminalError("generation_call_request_mismatch")
    snapshot = _stage_snapshot(attempt, call.call_sequence)
    expected_request = snapshot.litellm_request(
        _protocol_messages(snapshot, attempt, call.transcript_text, draft, extraction=extraction)
    )
    if canonical_json(call.request_json) != canonical_json(expected_request):
        raise OutcomeGenerationTerminalError("generation_call_request_mismatch")


def _validate_protocol_chain(attempt, calls, segments, transcript):
    """Reparse every retained prefix; never repair output or trust a stored PASS alone."""
    if not 1 <= len(calls) <= 3:
        raise OutcomeGenerationTerminalError("summary_publication_proof_invalid")
    authority = (attempt.metadata_json or {}).get("execution_authority")
    if not isinstance(authority, dict) or attempt.header_snapshot_json is None:
        raise OutcomeGenerationTerminalError("summary_execution_authority_missing")
    outputs = []
    previous = None
    for sequence, call in enumerate(calls, 1):
        if (call is None or call.call_sequence != sequence or call.call_state != "completed"
                or call.transcript_text != transcript
                or call.execution_authority_json != authority
                or call.execution_authority_hash != _content_hash(authority)
                or call.header_snapshot_hash != _content_hash(attempt.header_snapshot_json)
                or call.predecessor_call_id != (previous.id if previous else None)
                or call.predecessor_result_hash != (previous.validated_result_hash if previous else None)):
            raise OutcomeGenerationTerminalError("summary_call_chain_invalid")
        _verify_generation_call_hashes(call)
        _verify_generation_call_execution(
            attempt, call, extraction=outputs[0] if sequence == 2 else None,
            draft=outputs[1] if sequence == 3 else None,
        )
        raw = _call_output(call)
        if sequence == 1:
            validated = validate_factual_extraction(raw, segments=segments)
        elif sequence == 2:
            validated = validate_protocol_result(raw, segments=segments, sections=_protocol_sections(attempt))
        else:
            verification = validate_protocol_verification(raw, segments=segments)
            if verification != {"verdict": "pass", "findings": []}:
                raise OutcomeGenerationTerminalError("summary_verification_failed")
            validated = {
                "verification": verification, "draft_hash": _content_hash(outputs[1]),
                "extraction_hash": _content_hash(outputs[0]),
                "protocol": _enrich_protocol(outputs[1], attempt.header_snapshot_json, segments),
            }
        if call.validated_result_json != validated:
            raise OutcomeGenerationTerminalError("summary_call_chain_invalid")
        outputs.append(validated)
        previous = call
    return outputs


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
