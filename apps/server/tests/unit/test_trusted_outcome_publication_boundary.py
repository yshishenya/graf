from __future__ import annotations

import asyncio
import inspect
import json
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from sqlalchemy import select

import twobrain_rec_server.outcomes.ai_service as ai_service
from tests.fixtures.cabinet import create_outcome_ready_meeting
from twobrain_rec_server.db.models import (
    DispatchIntent,
    GenerationCall,
    MediaRevision,
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeSet,
    MeetingSummarySlot,
    ProcessingResult,
)
from twobrain_rec_server.ingest.media_revisions import source_fingerprint_for_revision
from twobrain_rec_server.outcomes.ai_service import (
    OutcomeGenerationTerminalError,
    _cas_summary_slot,
    publish_model_generated_outcome,
)
from twobrain_rec_server.outcomes.generator import compile_prompt_messages
from twobrain_rec_server.outcomes.prompts import outcome_config, validate_prompt_snapshot
from twobrain_rec_server.outcomes.service import ensure_summary_slot


def _pin_synthetic_prompt(attempt, transcript):
    snapshot = validate_prompt_snapshot(
        name="graf/meeting-outcome/auto", version=3, prompt_type="chat",
        prompt=[
            {"role": "system", "content": "{{output_language}} {{detail_level}} {{template_sections_json}}"},
            {"role": "user", "content": "{{transcript_json}}"},
        ],
        config={**outcome_config(schema_name="graf_meeting_outcome_auto_v1"),
                "model": "synthetic-route", "temperature": 0, "reasoning_effort": "high"},
        source="langfuse_evaluation",
    )
    attempt.prompt_name = snapshot.name
    attempt.prompt_version = snapshot.version
    attempt.prompt_hash = snapshot.canonical_hash
    attempt.prompt_definition = snapshot.prompt
    attempt.prompt_config = snapshot.config
    attempt.prompt_source = snapshot.source
    attempt.model_route = snapshot.model
    attempt.model_parameters = snapshot.model_parameters
    attempt.output_language = "ru"
    attempt.detail_level = "standard"
    attempt.metadata_json = {**attempt.metadata_json, "template_sections": ["summary"]}
    attempt.generator_config_hash = ai_service._ai_generator_config_hash(
        template_id=attempt.template_id, template_key=attempt.template_key,
        template_version=attempt.template_version, template_sections=("summary",),
        output_language="ru", detail_level="standard", snapshot=snapshot,
    )
    return snapshot.litellm_request(compile_prompt_messages(
        snapshot, transcript_json=transcript, output_language="ru",
        detail_level="standard", template_sections=("summary",),
    ))


def test_model_publication_entry_point_is_fail_closed_without_provider_call_proof() -> None:
    async def run() -> None:
        with pytest.raises(OutcomeGenerationTerminalError, match="summary_publication_proof_missing"):
            await publish_model_generated_outcome(
                None,
                workspace_id=UUID("00000000-0000-0000-0000-000000000001"),
                meeting_id=UUID("00000000-0000-0000-0000-000000000002"),
                candidate_id=UUID("00000000-0000-0000-0000-000000000003"),
                expected_current_outcome_set_id=None,
            )

    asyncio.run(run())


@pytest.mark.parametrize("tamper", [None, "actual_model", "actual_provider", "effort_missing", "effort_changed"])
def test_completed_validated_call_publishes_only_its_target_slot(client, tamper) -> None:
    meeting_id = create_outcome_ready_meeting(client, "trusted-positive-publication")

    async def run() -> tuple[UUID | None, str, str, UUID | None]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None and result.media_revision_id is not None
            revision = await db.get(MediaRevision, result.media_revision_id)
            assert revision is not None
            source_fingerprint = source_fingerprint_for_revision(revision)
            slot = await ensure_summary_slot(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                template_key="graf-auto-v1",
            )
            attempt = MeetingOutcomeGenerationAttempt(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=result.media_revision_id,
                processing_result_id=result.id,
                source_result_id=result.id,
                status="candidate",
                provider_kind="litellm",
                generator_version="test-positive-publication",
                candidate_id=UUID("00000000-0000-0000-0000-000000000123"),
                idempotency_key="test-positive-publication",
                source_result_hash=result.source_result_hash,
                source_fingerprint=source_fingerprint,
                deletion_epoch_at_start=meeting.deletion_epoch,
                template_key="graf-auto-v1",
                template_version=1,
                metadata_json={"access_policy_epoch": 0},
            )
            db.add(attempt)
            await db.flush()
            validated = {"category_states": {}, "items": []}
            validated_hash = sha256(
                json.dumps(validated, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            transcript = "fixture transcript"
            request = _pin_synthetic_prompt(attempt, transcript)
            raw_response = {"choices": []}
            outcome = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=result.media_revision_id,
                processing_result_id=result.id,
                candidate_id=attempt.candidate_id,
                status="available",
                source_kind="litellm",
                generator_kind="litellm",
                generator_version="test-positive-publication",
                source_result_hash=result.source_result_hash,
                source_fingerprint=source_fingerprint,
                deletion_epoch_at_start=meeting.deletion_epoch,
                content_hash=validated_hash,
                template_key="graf-auto-v1",
                template_version=1,
                revision_state="candidate",
            )
            db.add(outcome)
            await db.flush()
            attempt.outcome_set_id = outcome.id
            now = datetime.now(UTC)
            call = GenerationCall(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                candidate_id=attempt.candidate_id,
                provider_attempt=1,
                call_sequence=1,
                trace_id="test-trace",
                observation_id="test-observation",
                call_state="completed",
                started_at=now,
                completed_at=now,
                request_json=request,
                transcript_text=transcript,
                raw_response_json=raw_response,
                validated_result_json=validated,
                validated_result_hash=validated_hash,
                raw_response_hash=sha256(
                    json.dumps(raw_response, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest(),
                request_hash=sha256(
                    json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest(),
                transcript_hash=sha256(transcript.encode()).hexdigest(),
                export_status="pending",
            )
            db.add(call)
            await db.flush()
            call.request_hash = "tampered"
            with pytest.raises(OutcomeGenerationTerminalError, match="summary_publication_proof_invalid"):
                await publish_model_generated_outcome(
                    db,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    candidate_id=attempt.candidate_id,
                    expected_current_outcome_set_id=None,
                    publication_proof={
                        "generation_call_id": str(call.id),
                        "outcome_set_id": str(outcome.id),
                        "validated_result_hash": validated_hash,
                    },
                )
            slot_before_publish = await db.scalar(
                select(MeetingSummarySlot).where(MeetingSummarySlot.id == slot.id)
            )
            assert slot_before_publish is not None
            assert slot_before_publish.current_outcome_set_id is None
            call.request_hash = sha256(
                json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            if tamper is not None:
                if tamper.startswith("actual_"):
                    setattr(call, tamper, "not-reported-in-raw")
                else:
                    modified_request = deepcopy(request)
                    if tamper == "effort_missing":
                        modified_request.pop("reasoning_effort")
                    else:
                        modified_request["reasoning_effort"] = "low"
                    call.request_json = modified_request
                    call.request_hash = ai_service._content_hash(modified_request)
                retained = (deepcopy(call.request_json), call.request_hash, call.actual_model, call.actual_provider)
                with pytest.raises(OutcomeGenerationTerminalError, match="summary_publication_proof_invalid"):
                    await publish_model_generated_outcome(
                        db, workspace_id=meeting.workspace_id, meeting_id=meeting.id,
                        candidate_id=attempt.candidate_id, expected_current_outcome_set_id=None,
                        publication_proof={"generation_call_id": str(call.id), "validated_result_hash": validated_hash},
                    )
                assert (call.request_json, call.request_hash, call.actual_model, call.actual_provider) == retained
                assert slot.current_outcome_set_id is None
                return None, attempt.status, outcome.revision_state, meeting.current_outcome_set_id
            published = await publish_model_generated_outcome(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                candidate_id=attempt.candidate_id,
                expected_current_outcome_set_id=None,
                publication_proof={
                    "generation_call_id": str(call.id),
                    "outcome_set_id": str(outcome.id),
                    "validated_result_hash": validated_hash,
                },
            )
            await db.commit()
            slot = await db.scalar(
                select(MeetingSummarySlot).where(
                    MeetingSummarySlot.meeting_id == meeting.id,
                    MeetingSummarySlot.template_key == "graf-auto-v1",
                )
            )
            return (
                slot.current_outcome_set_id if slot is not None else None,
                attempt.status,
                published.revision_state or "",
                meeting.current_outcome_set_id,
            )

    slot_id, attempt_status, revision_state, legacy_pointer = asyncio.run(run())
    if tamper is not None:
        assert (slot_id, attempt_status, revision_state, legacy_pointer) == (None, "candidate", "candidate", None)
        return
    assert slot_id is not None
    assert attempt_status == "accepted"
    assert revision_state == "accepted"
    assert legacy_pointer is None


@pytest.mark.parametrize("field", ["actual_model", "actual_provider"])
def test_new_response_save_rejects_unreported_provenance_but_retains_raw(field):
    call = SimpleNamespace()
    response = SimpleNamespace(
        raw_response={"model": "reported-model", "provider": "reported-provider"},
        actual_model="reported-model", actual_provider="reported-provider",
    )
    setattr(response, field, "forged")
    validated = {"items": []}
    ai_service._complete_generation_call_with_response(
        call, response=response, validated_result=validated, completed_at=datetime.now(UTC),
    )
    assert call.raw_response_json == response.raw_response
    assert call.raw_response_hash == ai_service._content_hash(response.raw_response)
    assert (call.actual_model, call.actual_provider) == ("reported-model", "reported-provider")
    assert call.validated_result_json == {"validation_error": {"code": "generation_call_provenance_mismatch"}}


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel_during_call", [False, True])
async def test_new_error_save_preserves_reported_provenance_and_states(monkeypatch, cancel_during_call):
    transcript = ai_service.canonical_transcript([])
    transcript_hash = sha256(transcript.encode()).hexdigest()
    attempt = SimpleNamespace(
        source_result_id=UUID(int=4), meeting_id=UUID(int=2), candidate_id=UUID(int=3),
        media_revision_id=UUID(int=5), template_id=None, template_key="graf-auto-v1",
        template_version=1, metadata_json={}, status="generating", expires_at=None,
        temporal_transcript_hash=transcript_hash, langfuse_trace_id=None, attempt_count=0,
        requested_by_user_id=None, idempotency_key="synthetic-call", deletion_epoch_at_start=0,
        failure_code=None, failure_reason=None,
    )
    request = _pin_synthetic_prompt(attempt, transcript)
    generator_hash = attempt.generator_config_hash
    meeting = SimpleNamespace(deleted_at=None, deletion_state="none", deletion_epoch=0)
    raw = {"model": "reported-model", "provider": "reported-provider",
           "choices": [{"message": {"content": "not-json"}}]}
    raw_before = deepcopy(raw)
    failure_code = "litellm_invalid_structured_output"

    class Session:
        call = None
        commit = AsyncMock()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def scalar(self, _query):
            return self.call

        def add(self, call):
            assert isinstance(call, GenerationCall) and self.call is None
            call.id = UUID(int=6)
            self.call = call

    async def fail_generation(**_kwargs):
        if cancel_during_call:
            attempt.status = "cancelled"
            attempt.failure_code = "cancelled_during_call"
        raise ai_service.LiteLLMError(failure_code, retryable=False, raw_response=raw)

    db = Session()
    gateway = SimpleNamespace(generate=AsyncMock(side_effect=fail_generation))
    finalize = AsyncMock()
    monkeypatch.setattr(ai_service, "_apply_worker_workspace", AsyncMock())
    monkeypatch.setattr(ai_service, "_candidate_attempt", AsyncMock(return_value=attempt))
    monkeypatch.setattr(ai_service, "lock_meeting_fence", AsyncMock(return_value=meeting))
    monkeypatch.setattr(ai_service, "_lock_candidate_meeting_and_attempt", AsyncMock(return_value=(meeting, attempt)))
    monkeypatch.setattr(ai_service, "_ensure_candidate_source_fence", AsyncMock(return_value=attempt))
    monkeypatch.setattr(ai_service, "_candidate_segments", AsyncMock(return_value=[]))
    monkeypatch.setattr(ai_service, "_read_secret", lambda _path: "synthetic-key")
    monkeypatch.setattr(ai_service, "LiteLLMGateway", lambda **_kwargs: gateway)
    monkeypatch.setattr(ai_service, "finalize_dispatch_for_candidate", finalize)

    result = await ai_service.execute_candidate_generation(
        lambda: db, workspace_id=UUID(int=1), candidate_id=attempt.candidate_id,
        expected_snapshot_hash=transcript_hash,
        settings=SimpleNamespace(litellm_base_url="https://synthetic.invalid",
                                 litellm_api_key_file=None, litellm_request_timeout_seconds=1),
    )

    call = db.call
    assert (call.actual_model, call.actual_provider) == ("reported-model", "reported-provider")
    assert call.raw_response_json == raw == raw_before
    assert call.raw_response_hash == ai_service._content_hash(raw_before)
    assert call.request_json == request
    assert call.request_hash == ai_service._content_hash(request)
    assert (call.transcript_text, call.transcript_hash) == (transcript, transcript_hash)
    assert call.validated_result_json == {"generation_error": {
        "code": failure_code, "response_received": True,
        "retryable_classification": False, "egress_state": "response_received",
    }}
    assert call.validated_result_hash == ai_service._content_hash(call.validated_result_json)
    assert call.call_state == ("failed" if cancel_during_call else "completed")
    assert call.export_status == ("not_required" if cancel_during_call else "pending")
    assert attempt.status == result["state"] == ("cancelled" if cancel_during_call else "failed")
    assert attempt.failure_code == result["failure_code"] == (
        "cancelled_during_call" if cancel_during_call else failure_code
    )
    assert result["reused"] is False
    assert attempt.generator_config_hash == generator_hash
    assert attempt.attempt_count == 1
    gateway.generate.assert_awaited_once()
    assert finalize.await_count == (0 if cancel_during_call else 1)


@pytest.mark.asyncio
async def test_execution_does_not_repair_tampered_generator_hash(monkeypatch):
    attempt = SimpleNamespace(
        source_result_id=UUID(int=4), meeting_id=UUID(int=2), template_id=None,
        template_key="graf-auto-v1", template_version=1, metadata_json={},
    )
    _pin_synthetic_prompt(attempt, "synthetic")
    attempt.generator_config_hash = "tampered"

    class Session:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *_args):
            return None

    async def candidate(*_args, **_kwargs):
        return attempt
    async def workspace(*_args):
        pass
    async def no_meeting(*_args, **_kwargs):
        return None

    monkeypatch.setattr(ai_service, "_apply_worker_workspace", workspace)
    monkeypatch.setattr(ai_service, "_candidate_attempt", candidate)
    monkeypatch.setattr(ai_service, "lock_meeting_fence", no_meeting)
    with pytest.raises(OutcomeGenerationTerminalError):
        await ai_service.execute_candidate_generation(
            Session, workspace_id=UUID(int=1), candidate_id=UUID(int=3),
            expected_snapshot_hash="unused", settings=SimpleNamespace(),
        )
    assert attempt.generator_config_hash == "tampered"


@pytest.mark.asyncio
@pytest.mark.parametrize("corrupt_hash", [None, "request_hash", "transcript_hash", "raw_response_hash", "validated_result_hash"])
async def test_historical_observer_does_not_validate_current_config_or_raw_provenance(monkeypatch, corrupt_hash):
    candidate_id = UUID(int=3)
    call = SimpleNamespace(
        id=UUID(int=4), workspace_id=UUID(int=1), meeting_id=UUID(int=2), candidate_id=candidate_id,
        call_state="completed", completed_at=datetime.now(UTC), export_status="pending",
        request_json={"model": "historical-selected", "messages": []}, transcript_text="complete synthetic transcript",
        raw_response_json={"choices": []}, validated_result_json={"items": []},
        actual_model="historical-header-model", actual_provider="historical-header-provider",
        last_export_attempt_at=None, next_export_attempt_at=None, export_attempt_count=0,
    )
    call.request_hash = ai_service._content_hash(call.request_json)
    call.transcript_hash = sha256(call.transcript_text.encode()).hexdigest()
    call.raw_response_hash = ai_service._content_hash(call.raw_response_json)
    call.validated_result_hash = ai_service._content_hash(call.validated_result_json)
    if corrupt_hash is not None:
        setattr(call, corrupt_hash, "corrupt")
    attempt = SimpleNamespace(
        candidate_id=candidate_id, prompt_name="historical-prompt", prompt_version=1,
        prompt_hash="historical-hash", model_route="historical-selected", requested_by_user_id=None,
    )
    class Session:
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): return None
        async def scalar(self, _query): return call
        async def commit(self): pass
    async def workspace(*_args): pass
    async def locked(*_args, **_kwargs): return None, attempt
    async def candidate(*_args, **_kwargs): return attempt
    def forbidden(*_args, **_kwargs): pytest.fail("historical observer consulted current execution contract")
    sent = []
    client = SimpleNamespace(get_prompt=lambda *_args, **_kwargs: object(), flush=lambda: None)
    monkeypatch.setattr(ai_service, "_apply_worker_workspace", workspace)
    monkeypatch.setattr(ai_service, "_lock_candidate_meeting_and_attempt", locked)
    monkeypatch.setattr(ai_service, "_candidate_attempt", candidate)
    monkeypatch.setattr(ai_service, "_stored_prompt_snapshot", forbidden)
    monkeypatch.setattr(ai_service, "create_langfuse_client", lambda _settings: client)
    monkeypatch.setattr(ai_service, "publish_completed_generation", lambda *_args, **kwargs: sent.append(kwargs))
    retained = deepcopy(vars(call))
    if corrupt_hash is not None:
        with pytest.raises(OutcomeGenerationTerminalError, match="generation_call_content_hash_mismatch"):
            await ai_service.publish_generation_call(
                Session, workspace_id=call.workspace_id, call_id=call.id,
                settings=SimpleNamespace(langfuse_environment="test"), activity_attempt=1,
            )
        assert sent == []
        assert vars(call) == retained
        return
    await ai_service.publish_generation_call(
        Session, workspace_id=call.workspace_id, call_id=call.id,
        settings=SimpleNamespace(langfuse_environment="test"), activity_attempt=1,
    )
    assert len(sent) == 1 and call.export_status == "confirmed"
    for key in ("request_json", "transcript_text", "raw_response_json", "validated_result_json",
                "request_hash", "transcript_hash", "raw_response_hash", "validated_result_hash",
                "actual_model", "actual_provider"):
        assert getattr(call, key) == retained[key]


def test_ai_service_has_one_fail_closed_publisher_and_no_legacy_pointer_writes() -> None:
    source = inspect.getsource(ai_service)
    assert "async def publish_model_generated_outcome" in source
    assert "meeting.current_outcome_set_id =" not in source
    assert "accepted_by_user_id =" not in source


def test_slot_cas_moves_only_target_type_and_has_typed_conflict(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "trusted-slot-cas")

    async def run() -> tuple[UUID, UUID, UUID, int]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            source = result.source_result_hash or f"result:{result.id}"
            slot = await ensure_summary_slot(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                template_key="graf-auto-v1",
            )
            other_slot = await ensure_summary_slot(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                template_key="meeting_minutes",
            )
            first = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                status="available",
                source_kind="db_fixture",
                generator_kind="db_fixture",
                generator_version="test-db-only",
                source_result_hash=result.source_result_hash,
                source_fingerprint=source,
                deletion_epoch_at_start=meeting.deletion_epoch,
                template_key=slot.template_key,
                revision_state="candidate",
            )
            replacement = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                status="available",
                source_kind="db_fixture",
                generator_kind="db_fixture",
                generator_version="test-db-only",
                source_result_hash=result.source_result_hash,
                source_fingerprint=source,
                deletion_epoch_at_start=meeting.deletion_epoch,
                template_key=slot.template_key,
                revision_state="candidate",
            )
            other = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                status="available",
                source_kind="db_fixture",
                generator_kind="db_fixture",
                generator_version="test-db-only",
                source_result_hash=result.source_result_hash,
                source_fingerprint=source,
                deletion_epoch_at_start=meeting.deletion_epoch,
                template_key=other_slot.template_key,
                revision_state="candidate",
            )
            db.add_all([first, replacement, other])
            await db.flush()
            await _cas_summary_slot(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                template_key=slot.template_key,
                replacement_outcome_set_id=first.id,
                expected_current_outcome_set_id=None,
                expected_source_fingerprint=source,
                expected_deletion_epoch=meeting.deletion_epoch,
            )
            await _cas_summary_slot(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                template_key=other_slot.template_key,
                replacement_outcome_set_id=other.id,
                expected_current_outcome_set_id=None,
                expected_source_fingerprint=source,
                expected_deletion_epoch=meeting.deletion_epoch,
            )
            with pytest.raises(OutcomeGenerationTerminalError, match="summary_slot_conflict"):
                await _cas_summary_slot(
                    db,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    template_key=slot.template_key,
                    replacement_outcome_set_id=replacement.id,
                    expected_current_outcome_set_id=None,
                    expected_source_fingerprint=source,
                    expected_deletion_epoch=meeting.deletion_epoch,
                )
            persisted_slot = await db.scalar(
                select(MeetingSummarySlot).where(MeetingSummarySlot.id == slot.id)
            )
            persisted_other = await db.scalar(
                select(MeetingSummarySlot).where(MeetingSummarySlot.id == other_slot.id)
            )
            dispatch_count = await db.scalar(select(DispatchIntent.id))
            assert persisted_slot is not None and persisted_other is not None
            assert persisted_slot.current_outcome_set_id == first.id
            assert persisted_other.current_outcome_set_id == other.id
            return first.id, replacement.id, other.id, int(dispatch_count is not None)

    first_id, replacement_id, other_id, dispatch_exists = asyncio.run(run())
    assert first_id != replacement_id
    assert first_id != other_id
    assert dispatch_exists == 0
