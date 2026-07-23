from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    GenerationCall,
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    ProcessingResult,
    SummaryTemplate,
    TranscriptSegment,
)
from twobrain_rec_server.db.tenant_context import TenantDatabaseContext, apply_tenant_context
from twobrain_rec_server.observability.langfuse import (
    GenerationTraceContext,
    create_langfuse_client,
    deterministic_observation_id,
    deterministic_trace_id,
    fetch_production_prompt,
    publish_completed_generation,
    shutdown_langfuse,
)
from twobrain_rec_server.outcomes.generator import (
    LiteLLMError,
    LiteLLMGateway,
    canonical_transcript,
    compile_prompt_messages,
)
from twobrain_rec_server.outcomes.models import OutcomeTranscriptSegment
from twobrain_rec_server.outcomes.prompt_optimization import (
    load_verified_promoted_snapshot,
    persist_verified_promoted_snapshot,
)
from twobrain_rec_server.outcomes.prompts import (
    PromptSnapshot,
    canonical_json,
    validate_outcome_result,
    validate_prompt_snapshot,
)
from twobrain_rec_server.outcomes.templates import (
    BUILT_IN_BY_KEY,
    OUTCOME_CATEGORIES,
    prompt_name_for_template,
)
from twobrain_rec_server.storage.minio_client import get_storage
from twobrain_rec_server.workflows.outcome_generation_workflow import (
    TranscriptSnapshotError,
    split_plaintext_transcript,
)
from twobrain_rec_server.workflows.temporal_client import outcome_generation_workflow_id

AI_GENERATOR_VERSION = "outcomes-ai-v1"
ZERO_UUID = UUID(int=0)


class OutcomeGenerationTerminalError(RuntimeError):
    pass


class OutcomeGenerationDependencyError(RuntimeError):
    pass


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
) -> MeetingOutcomeGenerationAttempt:
    meeting = await db.scalar(
        select(Meeting)
        .where(Meeting.workspace_id == workspace_id, Meeting.id == meeting_id)
        .with_for_update()
    )
    if meeting is None:
        raise OutcomeGenerationTerminalError("meeting_not_found")
    if meeting.deletion_state not in {None, "none"} or meeting.deleted_at is not None:
        raise OutcomeGenerationTerminalError("meeting_deleting")
    if meeting.current_outcome_set_id != expected_current_outcome_set_id:
        raise OutcomeGenerationTerminalError("summary_revision_conflict")
    result = await db.scalar(
        select(ProcessingResult)
        .where(
            ProcessingResult.workspace_id == workspace_id,
            ProcessingResult.meeting_id == meeting_id,
        )
        .order_by(ProcessingResult.imported_at.desc(), ProcessingResult.created_at.desc())
    )
    if result is None or result.segment_count < 1 or result.transcript_status != "available":
        raise OutcomeGenerationTerminalError("summary_transcript_unavailable")
    template: SummaryTemplate | None = None
    if template_id is not None:
        template = await db.scalar(
            select(SummaryTemplate).where(
                SummaryTemplate.id == template_id,
                SummaryTemplate.workspace_id == workspace_id,
                SummaryTemplate.owner_user_id == requested_by_user_id,
                SummaryTemplate.template_key == template_key,
                SummaryTemplate.version == template_version,
                SummaryTemplate.status == "active",
            )
        )
        if template is None:
            raise OutcomeGenerationTerminalError("summary_template_unavailable")
        prompt_name = prompt_name_for_template(template_key, built_in=False)
        output_language = template.output_language
        detail_level = template.detail_level
        template_sections = tuple(str(section) for section in template.sections_json)
    else:
        definition = BUILT_IN_BY_KEY.get(template_key)
        if definition is None or definition.version != template_version:
            raise OutcomeGenerationTerminalError("summary_template_unavailable")
        prompt_name = definition.prompt_name
        output_language = "ru"
        detail_level = "standard"
        template_sections = definition.sections
    reusable = await db.scalar(
        select(MeetingOutcomeGenerationAttempt)
        .where(
            MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
            MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
            MeetingOutcomeGenerationAttempt.source_result_id == result.id,
            MeetingOutcomeGenerationAttempt.template_key == template_key,
            MeetingOutcomeGenerationAttempt.template_version == template_version,
            MeetingOutcomeGenerationAttempt.requested_by_user_id == requested_by_user_id,
            MeetingOutcomeGenerationAttempt.status.in_(
                {"queued", "generating", "blocked_dependency", "candidate"}
            ),
        )
        .order_by(MeetingOutcomeGenerationAttempt.created_at.desc())
    )
    if reusable is not None:
        return reusable
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
        candidate_id=candidate_id,
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
        metadata_json={"template_sections": list(template_sections)},
    )
    db.add(attempt)
    await db.flush()
    return attempt


async def resolve_candidate_prompt(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    settings: Settings,
    workspace_id: UUID,
    candidate_id: UUID,
) -> dict[str, object]:
    async with sessionmaker() as db:
        await _apply_worker_workspace(db, workspace_id)
        attempt = await _candidate_attempt(db, workspace_id, candidate_id)
        if attempt.prompt_name is None:
            raise OutcomeGenerationTerminalError("summary_prompt_not_selected")
        stored = _stored_prompt_snapshot(attempt)
        if stored is not None:
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
            try:
                snapshot = await asyncio.to_thread(
                    load_verified_promoted_snapshot,
                    get_storage(settings),
                    prompt_name=prompt_name,
                )
            except Exception as fallback_exc:
                raise OutcomeGenerationDependencyError(
                    "langfuse_prompt_unavailable"
                ) from fallback_exc
        else:
            snapshot = validate_prompt_snapshot(
                name=prompt_name,
                version=int(remote.version),
                prompt_type="chat",
                prompt=remote.prompt,
                config=remote.config or {},
                source="langfuse_production",
            )
            try:
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
        attempt = await _candidate_attempt(db, workspace_id, candidate_id, for_update=True)
        concurrent = _stored_prompt_snapshot(attempt)
        if concurrent is not None:
            if concurrent.canonical_hash != snapshot.canonical_hash:
                raise OutcomeGenerationTerminalError("summary_prompt_resolution_conflict")
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
            "max_completion_tokens": snapshot.config["max_completion_tokens"],
            "response_format": snapshot.config["response_format"],
        }
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
        attempt = await _candidate_attempt(db, workspace_id, candidate_id, for_update=True)
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
) -> dict[str, object]:
    api_key = _read_secret(settings.litellm_api_key_file)
    if settings.litellm_base_url is None:
        raise OutcomeGenerationDependencyError("litellm_endpoint_unavailable")
    started_at = datetime.now(UTC)
    async with sessionmaker() as db:
        await _apply_worker_workspace(db, workspace_id)
        # Deletion takes the Meeting lock before dependent attempts/outcomes.
        # Read the candidate without a lock only to discover its meeting, then
        # establish the canonical Meeting -> attempt -> call order below.
        attempt = await _candidate_attempt(db, workspace_id, candidate_id)
        meeting = await db.scalar(
            select(Meeting)
            .where(
                Meeting.workspace_id == workspace_id,
                Meeting.id == attempt.meeting_id,
            )
            .with_for_update()
        )
        attempt = await _candidate_attempt(db, workspace_id, candidate_id, for_update=True)
        if meeting is None or meeting.deletion_state not in {None, "none"}:
            raise OutcomeGenerationTerminalError("meeting_deleting")
        snapshot = _stored_prompt_snapshot(attempt)
        if snapshot is None or attempt.source_result_id is None:
            raise OutcomeGenerationTerminalError("summary_prompt_not_pinned")
        segments = await _candidate_segments(db, attempt)
        transcript = canonical_transcript(segments)
        transcript_hash = sha256(transcript.encode("utf-8")).hexdigest()
        if transcript_hash != expected_snapshot_hash or transcript_hash != attempt.temporal_transcript_hash:
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
        )
        provider_attempt = 1
        if existing is not None:
            if existing.call_state == "completed" and existing.validated_result_json is not None:
                state = "candidate" if attempt.outcome_set_id is not None else "failed"
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
        meeting = await db.scalar(
            select(Meeting)
            .where(Meeting.workspace_id == workspace_id, Meeting.id == meeting_id)
            .with_for_update()
        )
        attempt = await _candidate_attempt(db, workspace_id, candidate_id, for_update=True)
        call = await db.scalar(
            select(GenerationCall).where(GenerationCall.id == call_id).with_for_update()
        )
        if call is None or meeting is None or meeting.deletion_state not in {None, "none"}:
            if call is not None:
                _complete_generation_call_without_response(call, call_state="failed")
            attempt.status = "cancelled"
            attempt.failure_code = "meeting_deleted"
            await db.commit()
            raise OutcomeGenerationTerminalError("meeting_deleting")
        # Hold the meeting row through the one provider call and candidate write. This gives
        # deletion and inference one database-serialized order: a committed deletion wins
        # before egress, while a call already holding the lock finishes before deletion starts.
        try:
            response = await gateway.generate(snapshot=snapshot, messages=messages)
        except LiteLLMError as exc:
            completed_at = datetime.now(UTC)
            validation_result = {
                "generation_error": {
                    "code": exc.code,
                    "response_received": exc.raw_response is not None,
                    "retryable_classification": exc.retryable,
                    "egress_state": exc.egress_state,
                }
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
                raise OutcomeGenerationTerminalError(
                    "summary_provider_outcome_ambiguous"
                ) from exc
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
            attempt.ended_at = completed_at
            await db.commit()
            return {
                "candidate_id": str(candidate_id),
                "generation_call_id": str(call_id),
                "state": "failed",
                "failure_code": exc.code,
                "reused": False,
            }
        validation_failure: str | None = None
        try:
            validated = validate_outcome_result(
                response.parsed_content,
                allowed_categories=sections,
                allowed_segment_ids={str(segment.segment_id) for segment in segments},
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
            attempt.ended_at = completed_at
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
            status="available",
            source_kind="litellm",
            generator_kind="litellm",
            generator_version=f"{AI_GENERATOR_VERSION}:{candidate_id}",
            source_result_hash=transcript_hash,
            content_hash=_content_hash(validated),
            template_id=template_id,
            template_key=template_key,
            template_version=template_version,
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
                    source_refs_json=item["source_refs"],
                )
            )
        attempt.outcome_set_id = outcome_set.id
        attempt.status = "candidate"
        attempt.ended_at = completed_at
        attempt.failure_code = None
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
        call = await db.get(GenerationCall, call_id)
        if call is None or not _generation_call_is_publishable(call):
            raise OutcomeGenerationTerminalError("generation_call_not_completed")
        if call.export_status == "confirmed":
            return
        attempt = await _candidate_attempt(db, workspace_id, call.candidate_id)
        snapshot = _stored_prompt_snapshot(attempt)
        if snapshot is None or attempt.prompt_name is None or attempt.prompt_version is None:
            raise OutcomeGenerationTerminalError("summary_prompt_not_pinned")
        _verify_generation_call_hashes(call)
        call.export_attempt_count += 1
        call.last_export_attempt_at = datetime.now(UTC)
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
        async with sessionmaker() as db:
            await _apply_worker_workspace(db, workspace_id)
            current = await db.get(GenerationCall, call_id)
            if current is not None:
                current.export_status = "pending"
                current.last_export_error_code = "langfuse_delivery_failed"
                current.next_export_attempt_at = datetime.now(UTC) + timedelta(minutes=5)
                await db.commit()
        raise OutcomeGenerationDependencyError("langfuse_delivery_failed") from exc
    finally:
        shutdown_langfuse(client)
    async with sessionmaker() as db:
        await _apply_worker_workspace(db, workspace_id)
        current = await db.get(GenerationCall, call_id)
        if current is not None:
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
        "candidate_terminal": attempt is None
        or attempt.status not in {"queued", "generating", "blocked_dependency"},
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


def _complete_generation_call_without_response(
    call: GenerationCall, *, call_state: str
) -> None:
    call.call_state = call_state
    call.completed_at = datetime.now(UTC)
    call.export_status = "not_required"


async def finalize_candidate_generation_failure(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    workspace_id: UUID,
    candidate_id: UUID,
    failure_code: str = "summary_generation_retries_exhausted",
) -> None:
    """Project exhausted durable retries into a bounded user-visible terminal state."""
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
        attempt.failure_code = failure_code
        attempt.ended_at = datetime.now(UTC)
        await db.commit()


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
    meeting = await db.scalar(
        select(Meeting)
        .where(Meeting.workspace_id == workspace_id, Meeting.id == meeting_id)
        .with_for_update()
    )
    attempt = await db.scalar(
        select(MeetingOutcomeGenerationAttempt)
        .where(
            MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
            MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
            MeetingOutcomeGenerationAttempt.candidate_id == candidate_id,
        )
        .with_for_update()
    )
    if attempt is None or attempt.outcome_set_id is None:
        raise OutcomeGenerationTerminalError("summary_candidate_unavailable")
    outcome_set = await db.get(MeetingOutcomeSet, attempt.outcome_set_id)
    if meeting is None or outcome_set is None:
        raise OutcomeGenerationTerminalError("summary_candidate_unavailable")
    if meeting.deletion_state not in {None, "none"}:
        raise OutcomeGenerationTerminalError("meeting_deleting")
    if meeting.current_outcome_set_id != expected_current_outcome_set_id:
        raise OutcomeGenerationTerminalError("summary_revision_conflict")
    if attempt.status != "candidate":
        raise OutcomeGenerationTerminalError("summary_candidate_unavailable")
    if not accept:
        outcome_set.revision_state = "rejected"
        attempt.status = "rejected"
        attempt.ended_at = datetime.now(UTC)
        return outcome_set
    if meeting.current_outcome_set_id is not None:
        previous = await db.get(MeetingOutcomeSet, meeting.current_outcome_set_id)
        if previous is not None:
            previous.revision_state = "superseded"
            outcome_set.supersedes_outcome_set_id = previous.id
    now = datetime.now(UTC)
    outcome_set.revision_state = "accepted"
    outcome_set.accepted_by_user_id = requested_by_user_id
    outcome_set.accepted_at = now
    attempt.status = "accepted"
    attempt.ended_at = now
    meeting.current_outcome_set_id = outcome_set.id
    await db.flush()
    return outcome_set


async def _candidate_attempt(
    db: AsyncSession,
    workspace_id: UUID,
    candidate_id: UUID,
    *,
    for_update: bool = False,
) -> MeetingOutcomeGenerationAttempt:
    query = select(MeetingOutcomeGenerationAttempt).where(
        MeetingOutcomeGenerationAttempt.workspace_id == workspace_id,
        MeetingOutcomeGenerationAttempt.candidate_id == candidate_id,
    )
    if for_update:
        query = query.with_for_update()
    attempt = await db.scalar(query)
    if attempt is None:
        raise OutcomeGenerationTerminalError("summary_candidate_unavailable")
    return attempt


async def _candidate_segments(
    db: AsyncSession, attempt: MeetingOutcomeGenerationAttempt
) -> list[OutcomeTranscriptSegment]:
    if attempt.source_result_id is None:
        raise OutcomeGenerationTerminalError("summary_source_unavailable")
    rows = (
        await db.scalars(
            select(TranscriptSegment)
            .where(
                TranscriptSegment.workspace_id == attempt.workspace_id,
                TranscriptSegment.meeting_id == attempt.meeting_id,
                TranscriptSegment.processing_result_id == attempt.source_result_id,
            )
            .order_by(TranscriptSegment.sequence, TranscriptSegment.start_seconds)
        )
    ).all()
    if not rows:
        raise OutcomeGenerationTerminalError("summary_transcript_unavailable")
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
    snapshot = validate_prompt_snapshot(
        name=attempt.prompt_name,
        version=attempt.prompt_version,
        prompt_type="chat",
        prompt=attempt.prompt_definition,
        config=attempt.prompt_config,
        source=attempt.prompt_source or "verified_promoted_snapshot",
    )
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
    if attempt.template_id is None and attempt.template_key in BUILT_IN_BY_KEY:
        return BUILT_IN_BY_KEY[attempt.template_key].sections
    raise OutcomeGenerationTerminalError("summary_template_snapshot_invalid")


def _content_hash(value: object) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


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
