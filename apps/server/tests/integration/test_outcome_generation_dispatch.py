from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import func, select

from tests.fixtures.cabinet import create_outcome_ready_meeting
from tests.fixtures.meeting_protocol import (
    extraction_result,
    prepare_protocol_candidate,
    protocol_gateway_response,
    protocol_result,
)
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
    ensure_automatic_summary_candidate,
    execute_candidate_generation,
)
from twobrain_rec_server.outcomes.prompts import EXTRACTOR_PROMPT_NAME, VERIFIER_PROMPT_NAME
from twobrain_rec_server.workflows.temporal_client import (
    outcome_generation_workflow_id,
    start_outcome_generation_workflow,
)
from twobrain_rec_server.workflows.worker import resolve_outcome_prompt_config_activity


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
        template_version=2,
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
        template_version=2,
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
        template_version=2,
        prompt_name="graf/meeting-outcome/auto",
    )

    assert started.reused is True
    assert started.run_id == "existing-run"


@pytest.mark.anyio
async def test_ambiguous_candidate_dispatch_keeps_workflow_reconcilable() -> None:
    candidate_id = UUID("11111111-1111-1111-1111-111111111111")

    class _AmbiguousClient(_TemporalClient):
        async def start_workflow(self, workflow, payload, **kwargs):
            self.calls.append((workflow, payload, kwargs))
            raise ConnectionError("Temporal acknowledgement was lost")

    started = await start_outcome_generation_workflow(
        temporal_client=_AmbiguousClient(),
        settings=Settings(),
        candidate_id=candidate_id,
        meeting_id=UUID("22222222-2222-2222-2222-222222222222"),
        workspace_id=UUID("33333333-3333-3333-3333-333333333333"),
        source_result_id=UUID("44444444-4444-4444-4444-444444444444"),
        template_key="graf-auto-v1",
        template_version=2,
        prompt_name="graf/meeting-outcome/auto",
    )

    assert started.workflow_id == f"outcome-generation/{candidate_id}"
    assert started.reused is True
    assert started.ambiguous is True
    assert started.run_id is None


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


def test_prompt_activity_accepts_nullable_slot_fence() -> None:
    """First-generation formats have no previous slot pointer yet."""
    from typing import Any, get_type_hints

    assert get_type_hints(resolve_outcome_prompt_config_activity)["payload"] == dict[str, Any]


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
            )
            repeated = await ensure_outcomes_for_processing_result(
                db,
                result=result,
                ai_dispatch_planned=False,
            )
            item_count = await db.scalar(
                select(func.count())
                .select_from(MeetingOutcomeItem)
                .where(MeetingOutcomeItem.outcome_set_id == first.id)
            )
            await db.commit()
            assert first.protocol_json is None and first.candidate_id is None
            assert repeated.protocol_json is None and repeated.content_hash is None
            assert await db.scalar(select(func.count()).select_from(MeetingOutcomeGenerationAttempt).where(
                MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
            )) == 0
            return (
                first.id,
                repeated.id,
                first.status,
                first.failure_reason,
                first.revision_state,
                first.protocol_state,
                int(item_count or 0),
                repeated.status,
                repeated.failure_reason,
                repeated.revision_state,
                repeated.protocol_state,
                meeting.current_outcome_set_id,
            )

    (
        first_id,
        repeated_id,
        first_status,
        first_reason,
        first_revision_state,
        first_protocol_state,
        item_count,
        repeated_status,
        repeated_reason,
        repeated_revision_state,
        repeated_protocol_state,
        current_id,
    ) = asyncio.run(run())
    assert first_id == repeated_id
    assert first_status == repeated_status == "blocked"
    assert first_reason == repeated_reason == "summary_generation_unavailable"
    assert first_revision_state == repeated_revision_state == "candidate"
    assert first_protocol_state == repeated_protocol_state == "unavailable"
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
                ai_dispatch_planned=True,
            )
            item_count = await db.scalar(
                select(func.count())
                .select_from(MeetingOutcomeItem)
                .where(MeetingOutcomeItem.outcome_set_id == outcome_set.id)
            )
            await db.commit()
            assert outcome_set.protocol_json is None and outcome_set.candidate_id is None
            assert outcome_set.content_hash is None and outcome_set.accepted_at is None
            return (
                outcome_set.status,
                outcome_set.failure_reason,
                outcome_set.protocol_state,
                int(item_count or 0),
            )

    status, reason, protocol_state, item_count = asyncio.run(run())
    assert status == "generating"
    assert reason is None
    assert protocol_state == "processing"
    assert item_count == 0


def test_generation_activity_replay_returns_matching_published_result(client, monkeypatch) -> None:
    meeting_id = create_outcome_ready_meeting(client, "accepted-generation-activity-replay")
    calls = []
    monkeypatch.setattr(
        "twobrain_rec_server.outcomes.ai_service._read_secret", lambda _path: "synthetic-unused",
    )

    async def unexpected_generation(*_args, **_kwargs):
        raise AssertionError("accepted activity replay must not repeat model inference")

    async def run() -> None:
        sessionmaker = client.app_state["sessionmaker"]
        async with sessionmaker() as db:
            meeting = await db.get(Meeting, meeting_id)
            first = await ensure_automatic_summary_candidate(
                db, workspace_id=meeting.workspace_id, meeting_id=meeting_id,
            )
            repeated = await ensure_automatic_summary_candidate(
                db, workspace_id=meeting.workspace_id, meeting_id=meeting_id,
            )
            assert first.candidate_id == repeated.candidate_id
            attempt, segments = await prepare_protocol_candidate(db, meeting_id)
            assert attempt.candidate_id == first.candidate_id
        draft = protocol_result(segments)

        async def generate(_self, *, snapshot, messages, **_kwargs):
            calls.append(snapshot.name)
            if snapshot.name == VERIFIER_PROMPT_NAME:
                async with sessionmaker() as db:
                    # Completed extraction and draft must not publish a slot or protocol.
                    ledger = (await db.scalars(select(GenerationCall).where(
                        GenerationCall.candidate_id == attempt.candidate_id,
                    ).order_by(GenerationCall.call_sequence))).all()
                    assert [call.call_state for call in ledger] == ["completed", "completed", "reserved"]
                    assert await db.scalar(select(MeetingSummarySlot.current_outcome_set_id).where(
                        MeetingSummarySlot.meeting_id == meeting_id,
                        MeetingSummarySlot.template_key == attempt.template_key,
                    )) is None
                    assert await db.scalar(select(func.count()).select_from(MeetingOutcomeSet).where(
                        MeetingOutcomeSet.meeting_id == meeting_id,
                    )) == 0
                result = {"verdict": "pass", "findings": []}
            elif snapshot.name == EXTRACTOR_PROMPT_NAME:
                result = extraction_result(segments)
            else:
                result = draft
            return protocol_gateway_response(snapshot, messages, result)

        monkeypatch.setattr("twobrain_rec_server.outcomes.ai_service.LiteLLMGateway.generate", generate)
        kwargs = dict(
            workspace_id=attempt.workspace_id, candidate_id=attempt.candidate_id,
            expected_snapshot_hash=attempt.temporal_transcript_hash,
            settings=Settings(litellm_base_url="https://example.invalid", langfuse_project_id="synthetic-project"),
        )
        completed = await execute_candidate_generation(sessionmaker, **kwargs)
        assert completed["state"] == "accepted"
        monkeypatch.setattr(
            "twobrain_rec_server.outcomes.ai_service.LiteLLMGateway.generate", unexpected_generation,
        )
        replay = await execute_candidate_generation(sessionmaker, **kwargs)
        assert replay["state"] == "accepted" and replay["reused"] is True
        assert replay["outcome_set_id"] == completed["outcome_set_id"]
        async with sessionmaker() as db:
            persisted = await db.get(MeetingOutcomeGenerationAttempt, attempt.id)
            assert persisted.status == "accepted"
            slot = await db.scalar(select(MeetingSummarySlot).where(
                MeetingSummarySlot.meeting_id == meeting_id,
                MeetingSummarySlot.template_key == attempt.template_key,
            ))
            assert str(slot.current_outcome_set_id) == completed["outcome_set_id"]
            outcome = await db.get(MeetingOutcomeSet, slot.current_outcome_set_id)
            assert outcome.protocol_state == "available" and outcome.protocol_json
            ledger = (await db.scalars(select(GenerationCall).where(
                GenerationCall.candidate_id == attempt.candidate_id,
            ).order_by(GenerationCall.call_sequence))).all()
            assert [call.call_sequence for call in ledger] == [1, 2, 3]
            assert all(call.call_state == "completed" for call in ledger)

    asyncio.run(run())
    assert calls == [EXTRACTOR_PROMPT_NAME, "graf/meeting-outcome/auto", VERIFIER_PROMPT_NAME]


def test_missing_provider_config_does_not_reserve_generation_call(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "missing-provider-before-reservation")

    async def run() -> int:
        sessionmaker = client.app_state["sessionmaker"]
        async with sessionmaker() as db:
            attempt, _segments = await prepare_protocol_candidate(db, meeting_id)
            candidate_id = attempt.candidate_id
            workspace_id = attempt.workspace_id
            transcript_hash = attempt.temporal_transcript_hash

        with pytest.raises(
            OutcomeGenerationDependencyError,
            match="litellm_endpoint_unavailable",
        ):
            await execute_candidate_generation(
                sessionmaker,
                workspace_id=workspace_id,
                candidate_id=candidate_id,
                expected_snapshot_hash=transcript_hash,
                settings=Settings(langfuse_project_id="synthetic-project"),
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
