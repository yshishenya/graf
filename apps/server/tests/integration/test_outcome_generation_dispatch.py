from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import func, select

from tests.fixtures.cabinet import create_outcome_ready_meeting
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    GenerationCall,
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    MeetingSummarySlot,
    ProcessingResult,
)
from twobrain_rec_server.outcomes.ai_service import (
    OutcomeGenerationDependencyError,
    _candidate_segments,
    _content_hash,
    ensure_automatic_summary_candidate,
    execute_candidate_generation,
    publish_model_generated_outcome,
)
from twobrain_rec_server.outcomes.generator import canonical_transcript
from twobrain_rec_server.outcomes.prompts import outcome_config, prompt_snapshot_hash
from twobrain_rec_server.outcomes.templates import OUTCOME_CATEGORIES
from twobrain_rec_server.workflows.temporal_client import (
    outcome_generation_workflow_id,
    start_outcome_generation_workflow,
)


class _AlreadyStartedError(RuntimeError):
    def __init__(self, message: str = "already started", *, run_id: str | None = None) -> None:
        super().__init__(message)
        self.run_id = run_id


class _Handle:
    run_id = None
    result_run_id = "run-1"


class _TemporalClient:
    def __init__(self, *, already_started: bool = False) -> None:
        self.already_started = already_started
        self.calls: list[tuple[object, dict[str, str], dict[str, object]]] = []

    async def start_workflow(self, workflow, payload, **kwargs):
        self.calls.append((workflow, payload, kwargs))
        if self.already_started:
            raise _AlreadyStartedError("already started")
        return _Handle()


@pytest.mark.anyio
async def test_candidate_dispatch_uses_deterministic_id_and_plaintext_identifiers() -> None:
    candidate_id = UUID("11111111-1111-1111-1111-111111111111")
    client = _TemporalClient()

    started = await start_outcome_generation_workflow(
        temporal_client=client,
        settings=Settings(temporal_task_queue="graf-processing"),
        candidate_id=candidate_id,
        meeting_id=UUID("22222222-2222-2222-2222-222222222222"),
        workspace_id=UUID("33333333-3333-3333-3333-333333333333"),
        source_result_id=UUID("44444444-4444-4444-4444-444444444444"),
        template_key="graf-auto-v1",
        template_version=1,
        prompt_name="graf/meeting-outcome/auto",
        summary_slot_id=UUID("55555555-5555-5555-5555-555555555555"),
        expected_current_outcome_set_id=UUID("66666666-6666-6666-6666-666666666666"),
    )

    assert started.workflow_id == outcome_generation_workflow_id(candidate_id)
    assert started.run_id == "run-1"
    assert started.reused is False
    _, payload, options = client.calls[0]
    assert payload["candidate_id"] == str(candidate_id)
    assert payload["prompt_name"] == "graf/meeting-outcome/auto"
    assert payload["summary_slot_id"] == "55555555-5555-5555-5555-555555555555"
    assert payload["expected_current_outcome_set_id"] == "66666666-6666-6666-6666-666666666666"
    assert options["id"] == f"outcome-generation/{candidate_id}"
    assert options["task_queue"] == "graf-processing-outcomes"
    from temporalio.common import WorkflowIDReusePolicy

    assert options["id_reuse_policy"] == WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY


@pytest.mark.anyio
async def test_duplicate_candidate_dispatch_reuses_existing_workflow() -> None:
    candidate_id = UUID("11111111-1111-1111-1111-111111111111")
    client = _TemporalClient(already_started=True)

    started = await start_outcome_generation_workflow(
        temporal_client=client,
        settings=Settings(),
        candidate_id=candidate_id,
        meeting_id=UUID("22222222-2222-2222-2222-222222222222"),
        workspace_id=UUID("33333333-3333-3333-3333-333333333333"),
        source_result_id=UUID("44444444-4444-4444-4444-444444444444"),
        template_key="graf-auto-v1",
        template_version=1,
        prompt_name="graf/meeting-outcome/auto",
    )

    assert started.workflow_id == f"outcome-generation/{candidate_id}"
    assert started.reused is True
    assert started.run_id is None


@pytest.mark.anyio
async def test_duplicate_candidate_dispatch_keeps_temporal_run_id_when_available() -> None:
    candidate_id = UUID("11111111-1111-1111-1111-111111111111")

    class _Client(_TemporalClient):
        async def start_workflow(self, workflow, payload, **kwargs):
            self.calls.append((workflow, payload, kwargs))
            raise _AlreadyStartedError(run_id="existing-run")

    started = await start_outcome_generation_workflow(
        temporal_client=_Client(),
        settings=Settings(),
        candidate_id=candidate_id,
        meeting_id=UUID("22222222-2222-2222-2222-222222222222"),
        workspace_id=UUID("33333333-3333-3333-3333-333333333333"),
        source_result_id=UUID("44444444-4444-4444-4444-444444444444"),
        template_key="graf-auto-v1",
        template_version=1,
        prompt_name="graf/meeting-outcome/auto",
    )

    assert started.reused is True
    assert started.run_id == "existing-run"


@pytest.mark.anyio
async def test_temporal_converter_accepts_mixed_payload_with_any_type_hint() -> None:
    from typing import Any

    from temporalio.converter import DataConverter

    payload = {"candidate_id": "candidate", "chunk_index": 0, "enabled": True}
    encoded = await DataConverter.default.encode([payload])

    assert await DataConverter.default.decode(encoded, [dict[str, Any]]) == [payload]


def test_ai_temporal_boundaries_never_annotate_mixed_payload_as_object() -> None:
    paths = (
        Path("src/twobrain_rec_server/workflows/worker.py"),
        Path("src/twobrain_rec_server/workflows/prompt_optimization_workflow.py"),
        Path("src/twobrain_rec_server/workflows/prompt_rollback_workflow.py"),
        Path("src/twobrain_rec_server/outcomes/prompt_optimization.py"),
    )

    for path in paths:
        assert "payload: dict[str, object]" not in path.read_text(encoding="utf-8")


async def _ready_automatic_candidate(db, meeting_id):
    meeting = await db.get(Meeting, meeting_id)
    result = await db.scalar(
        select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
    )
    assert meeting is not None and result is not None
    first = await ensure_automatic_summary_candidate(
        db, workspace_id=meeting.workspace_id, meeting_id=meeting.id
    )
    repeated = await ensure_automatic_summary_candidate(
        db, workspace_id=meeting.workspace_id, meeting_id=meeting.id
    )
    assert first is not None and repeated is not None
    assert first.candidate_id == repeated.candidate_id
    outcome_set = MeetingOutcomeSet(
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        media_revision_id=result.media_revision_id,
        processing_result_id=result.id,
        candidate_id=first.candidate_id,
        status="available",
        source_kind="litellm",
        generator_kind="litellm",
        generator_version="test:automatic-ai",
        source_result_hash=first.source_result_hash,
        source_fingerprint=first.source_fingerprint,
        deletion_epoch_at_start=first.deletion_epoch_at_start,
        template_key=first.template_key,
        template_version=first.template_version,
        revision_state="candidate",
    )
    db.add(outcome_set)
    await db.flush()
    first.outcome_set_id = outcome_set.id
    first.status = "candidate"
    return meeting, result, first, outcome_set


def test_revision_scoped_ai_wait_replaces_blocked_lineage_without_deterministic_content(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "ai-disabled-initial-outcome")
    from twobrain_rec_server.outcomes.service import ensure_outcomes_for_processing_result

    async def run() -> tuple:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            meeting = await db.get(Meeting, meeting_id)
            assert result is not None and meeting is not None
            first = await ensure_outcomes_for_processing_result(
                db,
                result=result,
                publish_initial_baseline=True,
            )
            repeated = await ensure_outcomes_for_processing_result(
                db,
                result=result,
                publish_initial_baseline=True,
                ai_dispatch_planned=False,
            )
            item_count = await db.scalar(
                select(func.count())
                .select_from(MeetingOutcomeItem)
                .where(MeetingOutcomeItem.outcome_set_id == first.id)
            )
            await db.commit()
            return (
                first.id,
                repeated.id,
                first.status,
                first.failure_reason,
                first.revision_state,
                {getattr(first, f"{category}_state") for category in OUTCOME_CATEGORIES},
                int(item_count or 0),
                repeated.status,
                repeated.failure_reason,
                repeated.revision_state,
                {getattr(repeated, f"{category}_state") for category in OUTCOME_CATEGORIES},
                meeting.current_outcome_set_id,
            )

    (
        first_id,
        repeated_id,
        first_status,
        first_reason,
        first_revision_state,
        first_category_states,
        item_count,
        repeated_status,
        repeated_reason,
        repeated_revision_state,
        repeated_category_states,
        current_id,
    ) = asyncio.run(run())
    assert first_id == repeated_id
    assert first_status == repeated_status == "blocked"
    assert first_reason == repeated_reason == "summary_generation_unavailable"
    assert first_revision_state == repeated_revision_state == "candidate"
    assert first_category_states == repeated_category_states == {"unavailable"}
    assert item_count == 0
    assert current_id is None


def test_planned_ai_dispatch_keeps_initial_outcome_generating_without_content(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "planned-ai-initial-outcome")
    from twobrain_rec_server.outcomes.service import ensure_outcomes_for_processing_result

    async def run() -> tuple:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert result is not None
            outcome_set = await ensure_outcomes_for_processing_result(
                db,
                result=result,
                publish_initial_baseline=True,
                ai_dispatch_planned=True,
            )
            item_count = await db.scalar(
                select(func.count())
                .select_from(MeetingOutcomeItem)
                .where(MeetingOutcomeItem.outcome_set_id == outcome_set.id)
            )
            await db.commit()
            return (
                outcome_set.status,
                outcome_set.failure_reason,
                {
                    getattr(outcome_set, f"{category}_state")
                    for category in OUTCOME_CATEGORIES
                },
                int(item_count or 0),
            )

    status, reason, category_states, item_count = asyncio.run(run())
    assert status == "generating"
    assert reason is None
    assert category_states == {"processing"}
    assert item_count == 0


def test_generation_activity_replay_returns_matching_published_result(client, monkeypatch) -> None:
    meeting_id = create_outcome_ready_meeting(client, "accepted-generation-activity-replay")

    async def unexpected_generation(*_args, **_kwargs):
        raise AssertionError("accepted activity replay must not repeat model inference")

    monkeypatch.setattr(
        "twobrain_rec_server.outcomes.ai_service.LiteLLMGateway.generate",
        unexpected_generation,
    )

    async def run() -> tuple:
        sessionmaker = client.app_state["sessionmaker"]
        async with sessionmaker() as db:
            meeting, _result, attempt, outcome_set = await _ready_automatic_candidate(
                db, meeting_id
            )
            prompt = [
                {
                    "role": "system",
                    "content": (
                        "{{transcript_json}} {{output_language}} "
                        "{{detail_level}} {{template_sections_json}}"
                    ),
                }
            ]
            config = outcome_config(schema_name="graf_outcome")
            attempt.prompt_name = "graf/meeting-outcome/auto"
            attempt.prompt_version = 1
            attempt.prompt_definition = prompt
            attempt.prompt_config = config
            attempt.prompt_source = "verified_promoted_snapshot"
            attempt.prompt_hash = prompt_snapshot_hash(prompt=prompt, config=config)
            transcript = canonical_transcript(await _candidate_segments(db, attempt))
            transcript_hash = sha256(transcript.encode("utf-8")).hexdigest()
            attempt.temporal_transcript_hash = transcript_hash
            validated = {
                "category_states": {
                    category: "not_found" for category in OUTCOME_CATEGORIES
                },
                "items": [],
            }
            validated_hash = _content_hash(validated)
            outcome_set.content_hash = validated_hash
            now = datetime.now(UTC)
            raw_response = {"choices": []}
            request = {"messages": []}
            call = GenerationCall(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                candidate_id=attempt.candidate_id,
                provider_attempt=1,
                call_sequence=1,
                trace_id="1" * 32,
                observation_id="2" * 32,
                call_state="completed",
                started_at=now,
                completed_at=now,
                request_json=request,
                transcript_text=transcript,
                raw_response_json=raw_response,
                request_hash=_content_hash(request),
                transcript_hash=transcript_hash,
                raw_response_hash=_content_hash(raw_response),
                validated_result_json=validated,
                validated_result_hash=validated_hash,
            )
            db.add(call)
            await db.flush()
            await publish_model_generated_outcome(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                candidate_id=attempt.candidate_id,
                expected_current_outcome_set_id=None,
                publication_proof={
                    "generation_call_id": str(call.id),
                    "outcome_set_id": str(outcome_set.id),
                    "validated_result_hash": validated_hash,
                },
            )
            workspace_id = meeting.workspace_id
            candidate_id = attempt.candidate_id
            published_id = outcome_set.id
            await db.commit()
            assert candidate_id is not None

        replay = await execute_candidate_generation(
            sessionmaker,
            workspace_id=workspace_id,
            candidate_id=candidate_id,
            expected_snapshot_hash=transcript_hash,
            settings=Settings(),
        )
        async with sessionmaker() as db:
            attempt = await db.scalar(
                select(MeetingOutcomeGenerationAttempt).where(
                    MeetingOutcomeGenerationAttempt.candidate_id == candidate_id
                )
            )
            meeting = await db.get(Meeting, meeting_id)
            assert attempt is not None and meeting is not None
            current_slot_id = await db.scalar(
                select(MeetingSummarySlot.current_outcome_set_id).where(
                    MeetingSummarySlot.meeting_id == meeting_id,
                    MeetingSummarySlot.template_key == attempt.template_key,
                )
            )
            return replay, attempt.status, current_slot_id, published_id

    replay, attempt_status, current_id, published_id = asyncio.run(run())
    assert replay["state"] == "accepted"
    assert replay["reused"] is True
    assert replay["outcome_set_id"] == str(published_id)
    assert attempt_status == "accepted"
    assert current_id == published_id


def test_missing_provider_config_does_not_reserve_generation_call(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "missing-provider-before-reservation")

    async def run() -> int:
        sessionmaker = client.app_state["sessionmaker"]
        async with sessionmaker() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            attempt = await ensure_automatic_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
            )
            assert attempt is not None and attempt.candidate_id is not None
            prompt = [
                {
                    "role": "system",
                    "content": (
                        "{{transcript_json}} {{output_language}} "
                        "{{detail_level}} {{template_sections_json}}"
                    ),
                }
            ]
            config = outcome_config(schema_name="graf_outcome")
            attempt.prompt_name = "graf/meeting-outcome/auto"
            attempt.prompt_version = 1
            attempt.prompt_definition = prompt
            attempt.prompt_config = config
            attempt.prompt_source = "verified_promoted_snapshot"
            attempt.prompt_hash = prompt_snapshot_hash(prompt=prompt, config=config)
            transcript = canonical_transcript(await _candidate_segments(db, attempt))
            transcript_hash = sha256(transcript.encode("utf-8")).hexdigest()
            attempt.temporal_transcript_hash = transcript_hash
            attempt.status = "generating"
            candidate_id = attempt.candidate_id
            workspace_id = meeting.workspace_id
            await db.commit()

        with pytest.raises(
            OutcomeGenerationDependencyError,
            match="litellm_endpoint_unavailable",
        ):
            await execute_candidate_generation(
                sessionmaker,
                workspace_id=workspace_id,
                candidate_id=candidate_id,
                expected_snapshot_hash=transcript_hash,
                settings=Settings(),
            )
        async with sessionmaker() as db:
            return int(
                await db.scalar(
                    select(func.count())
                    .select_from(GenerationCall)
                    .where(GenerationCall.candidate_id == candidate_id)
                )
                or 0
            )

    assert asyncio.run(run()) == 0
