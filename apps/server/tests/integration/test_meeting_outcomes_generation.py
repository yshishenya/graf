from __future__ import annotations

import asyncio
import importlib
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, func, select

from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
from tests.fixtures.cabinet import create_outcome_ready_meeting
from tests.fixtures.meeting_protocol import (
    extraction_result,
    prepare_protocol_candidate,
    protocol_gateway_response,
    protocol_outcome,
    protocol_result,
    seed_accepted_protocol,
)
from twobrain_rec_server.api.schemas import CreateSummaryCandidateRequest
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
    ProcessingAuditEvent,
    ProcessingResult,
    TranscriptSegment,
    Workspace,
)
from twobrain_rec_server.domain.statuses import ProcessingAvailabilityStatus
from twobrain_rec_server.outcomes import service as outcome_service
from twobrain_rec_server.outcomes.ai_service import (
    AI_GENERATOR_VERSION,
    OutcomeGenerationTerminalError,
    _content_hash,
    _enrich_protocol,
    create_summary_candidate,
    ensure_automatic_summary_candidate,
    execute_candidate_generation,
    finalize_candidate_generation_failure,
    publish_model_generated_outcome,
)
from twobrain_rec_server.outcomes.dispatch import (
    reconcile_missing_summary_defaults,
    reconcile_unrequested_summary_candidates,
)
from twobrain_rec_server.outcomes.generator import LiteLLMError
from twobrain_rec_server.outcomes.prompts import EXTRACTOR_PROMPT_NAME, VERIFIER_PROMPT_NAME
from twobrain_rec_server.outcomes.service import mark_meeting_default_slot
from twobrain_rec_server.processing.store import ProcessingLifecycleBlocked


async def _protocol_row(db, **fields) -> MeetingOutcomeSet:
    """Full synthetic content for DB-only lifecycle tests, not publication proof."""
    result = await db.get(ProcessingResult, fields["processing_result_id"])
    meeting = await db.get(Meeting, fields["meeting_id"])
    assert result is not None and meeting is not None
    outcome = protocol_outcome()
    outcome.source_result_hash = result.source_result_hash
    outcome.media_revision_id = result.media_revision_id
    outcome.deletion_epoch_at_start = meeting.deletion_epoch or 0
    outcome.template_key = "graf-auto-v1"
    outcome.template_version = 2
    for key, value in fields.items():
        setattr(outcome, key, value)
    if outcome.revision_state == "accepted":
        outcome.accepted_at = datetime.now(UTC)
    segments = await outcome_service.load_outcome_transcript_segments(db, result=result)
    header = {
        **outcome.protocol_json["header"], "source_result_id": str(result.id),
        "template_key": outcome.template_key, "template_version": outcome.template_version,
    }
    outcome.protocol_json = _enrich_protocol(protocol_result(segments), header, segments)
    outcome.content_hash = _content_hash(outcome.protocol_json)
    return outcome


def test_feature_183_publication_prerequisite_matrix_is_fail_closed_and_non_mutating(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "publication-prerequisite-matrix")

    async def run() -> tuple[UUID | None, str, UUID | None, str | None, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            attempt = await ensure_automatic_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
            )
            assert attempt is not None and attempt.candidate_id is not None
            slot = await db.scalar(
                select(MeetingSummarySlot).where(
                    MeetingSummarySlot.workspace_id == meeting.workspace_id,
                    MeetingSummarySlot.meeting_id == meeting.id,
                    MeetingSummarySlot.template_key == attempt.template_key,
                )
            )
            dispatch = await db.scalar(
                select(DispatchIntent).where(
                    DispatchIntent.workspace_id == meeting.workspace_id,
                    DispatchIntent.meeting_id == meeting.id,
                    DispatchIntent.candidate_id == attempt.candidate_id,
                )
            )
            assert slot is not None and dispatch is not None
            before = (
                slot.current_outcome_set_id,
                attempt.status,
                attempt.outcome_set_id,
                dispatch.state,
                meeting.current_outcome_set_id,
            )
            proofs = (
                None,
                {},
                {"canonical_artifact": "missing"},
                {"publication_receipt": "missing"},
                {"generation_call": "missing"},
                {"calibration": "missing"},
                {"source_fence": "missing"},
                {"deletion_fence": "missing"},
                {"authorization": "missing"},
            )
            for proof in proofs:
                with pytest.raises(
                    OutcomeGenerationTerminalError,
                    match=r"summary_publication_(?:proof_missing|proof_invalid|fence_failed)",
                ):
                    await publish_model_generated_outcome(
                        db,
                        workspace_id=meeting.workspace_id,
                        meeting_id=meeting.id,
                        candidate_id=attempt.candidate_id,
                        expected_current_outcome_set_id=slot.current_outcome_set_id,
                        publication_proof=proof,
                        settings=Settings(langfuse_project_id="synthetic-project"),
                    )
            after = (
                slot.current_outcome_set_id,
                attempt.status,
                attempt.outcome_set_id,
                dispatch.state,
                meeting.current_outcome_set_id,
            )
            assert before == after
            await db.rollback()
            return after

    assert asyncio.run(run()) == (None, "queued", None, "created", None)


@pytest.mark.parametrize(
    "forbidden_field",
    [
        "my_actions",
        "private_self",
        "MeetingIntentV1",
        "AudienceContextV1",
        "privacy",
        "FocusV1",
        "DetailBudgetV1",
    ],
)
def test_feature_183_rejects_subject_scoped_and_unapproved_generation_controls(
    forbidden_field: str,
) -> None:
    payload = {
        "template_key": "graf-auto-v1",
        "template_id": None,
        "template_version": 2,
        forbidden_field: {},
    }

    with pytest.raises(ValidationError):
        CreateSummaryCandidateRequest.model_validate(payload)


def _service_module():
    try:
        return importlib.import_module("twobrain_rec_server.outcomes.service")
    except ModuleNotFoundError as exc:
        raise AssertionError("outcome service module is missing") from exc


def test_outcome_generation_is_idempotent_and_stores_source_evidence(client, monkeypatch) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    calls = []
    monkeypatch.setattr(
        "twobrain_rec_server.outcomes.ai_service._read_secret", lambda _path: "synthetic-unused",
    )

    async def run() -> None:
        sessionmaker = client.app_state["sessionmaker"]
        async with sessionmaker() as db:
            attempt, segments = await prepare_protocol_candidate(db, meeting_id)
            assert attempt.detail_level == "detailed"
        draft = protocol_result(segments)
        draft["uncertain_sections"] = ["action_items"]

        async def generate(_self, *, snapshot, messages, **_kwargs):
            calls.append(snapshot.name)
            if snapshot.name == EXTRACTOR_PROMPT_NAME:
                result = extraction_result(segments)
            elif snapshot.name == VERIFIER_PROMPT_NAME:
                result = {"verdict": "pass", "findings": []}
            else:
                result = draft
            return protocol_gateway_response(snapshot, messages, result)

        monkeypatch.setattr("twobrain_rec_server.outcomes.ai_service.LiteLLMGateway.generate", generate)
        kwargs = dict(
            workspace_id=attempt.workspace_id, candidate_id=attempt.candidate_id,
            expected_snapshot_hash=attempt.temporal_transcript_hash,
            settings=Settings(litellm_base_url="https://example.invalid", langfuse_project_id="synthetic-project"),
        )
        first = await execute_candidate_generation(sessionmaker, **kwargs)
        second = await execute_candidate_generation(sessionmaker, **kwargs)
        assert first["state"] == second["state"] == "accepted"
        assert first["outcome_set_id"] == second["outcome_set_id"]
        assert second["reused"] is True
        async with sessionmaker() as db:
            sets = (await db.scalars(select(MeetingOutcomeSet).where(
                MeetingOutcomeSet.meeting_id == meeting_id,
            ))).all()
            assert len(sets) == 1
            outcome = sets[0]
            assert outcome.workspace_id == attempt.workspace_id
            assert outcome.protocol_state == "available"
            assert outcome.content_hash == _content_hash(outcome.protocol_json)
            assert outcome.protocol_json["uncertain_sections"] == ["action_items"]
            assert outcome.protocol_json["action_items"] == []
            assert outcome.protocol_json["decisions"] == []
            ref = outcome.protocol_json["executive_summary"][0]["source_refs"][0]
            assert ref["transcript_segment_id"] == str(segments[0].segment_id)
            assert ref["sequence"] == segments[0].sequence
            assert ref["start_seconds"] == float(segments[0].start_seconds)
            assert ref["end_seconds"] == float(segments[0].end_seconds)
            ledger = (await db.scalars(select(GenerationCall).where(
                GenerationCall.candidate_id == attempt.candidate_id,
            ).order_by(GenerationCall.call_sequence))).all()
            assert [call.call_sequence for call in ledger] == [1, 2, 3]
            assert all(call.call_state == "completed" for call in ledger)
            assert await db.scalar(select(func.count()).select_from(MeetingOutcomeItem).where(
                MeetingOutcomeItem.meeting_id == meeting_id,
            )) == 0

    asyncio.run(run())
    assert calls == [EXTRACTOR_PROMPT_NAME, "graf/meeting-outcome/auto", VERIFIER_PROMPT_NAME]


def test_provider_only_legacy_result_does_not_start_new_outcomes(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "provider-only-outcomes")
    service = _service_module()

    async def generate() -> None:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert result is not None
            await db.execute(
                delete(TranscriptSegment).where(
                    TranscriptSegment.processing_result_id == result.id
                )
            )
            result.segment_count = 0
            with pytest.raises(
                ProcessingLifecycleBlocked,
                match="summary_source_result_stale",
            ):
                await service.ensure_outcomes_for_processing_result(db, result=result)

    asyncio.run(generate())


def test_first_wait_projection_remains_unpublished_without_model_identity(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    service = _service_module()

    async def run() -> None:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            meeting = await db.get(Meeting, meeting_id)
            assert result is not None and meeting is not None
            first = await service.ensure_outcomes_for_processing_result(db, result=result, ai_dispatch_planned=True)
            await db.commit()
            repaired = await service.ensure_outcomes_for_processing_result(db, result=result, ai_dispatch_planned=True)
            assert first.id == repaired.id
            assert meeting.current_outcome_set_id is None
            assert repaired.revision_state == "candidate"
            assert repaired.status == "generating" and repaired.protocol_state == "processing"
            assert repaired.protocol_json is None and repaired.content_hash is None
            assert repaired.candidate_id is None and repaired.accepted_at is None
            assert repaired.requested_by_user_id is None and repaired.accepted_by_user_id is None
            assert repaired.template_key is None and repaired.template_version is None
            assert repaired.output_language is None and repaired.detail_level is None
            assert await db.scalar(select(func.count()).select_from(MeetingOutcomeGenerationAttempt).where(
                MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
            )) == 0
            assert await db.scalar(select(func.count()).select_from(GenerationCall).where(
                GenerationCall.meeting_id == meeting_id,
            )) == 0

    asyncio.run(run())


def test_trusted_reconcile_cannot_promote_the_initial_baseline(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "trusted-baseline-reconcile")
    service = _service_module()

    async def reconcile() -> tuple:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            meeting = await db.get(Meeting, meeting_id)
            assert result is not None and meeting is not None
            candidate = await service.ensure_outcomes_for_processing_result(db, result=result)
            await db.commit()
            assert meeting.current_outcome_set_id is None
            assert candidate.revision_state == "candidate"
            assert candidate.protocol_json is None and candidate.protocol_state == "unavailable"

            repeated = await service.ensure_outcomes_for_processing_result(
                db,
                result=result,
                ai_dispatch_planned=False,
            )
            attempts = (
                await db.scalars(
                    select(MeetingOutcomeGenerationAttempt).where(
                        MeetingOutcomeGenerationAttempt.meeting_id == meeting_id
                    )
                )
            ).all()
            sets = (
                await db.scalars(
                    select(MeetingOutcomeSet).where(MeetingOutcomeSet.meeting_id == meeting_id)
                )
            ).all()
            item_count = await db.scalar(
                select(func.count())
                .select_from(MeetingOutcomeItem)
                .where(MeetingOutcomeItem.outcome_set_id == repeated.id)
            )
            await db.commit()
            assert repeated.protocol_json is None and repeated.content_hash is None
            assert repeated.protocol_state == "unavailable"
            assert repeated.failure_reason == "summary_generation_unavailable"
            return (
                candidate.id,
                repeated.id,
                meeting.current_outcome_set_id,
                repeated.revision_state,
                repeated.accepted_at is not None,
                [attempt.status for attempt in attempts],
                len(sets),
                int(item_count or 0),
            )

    (
        candidate_id,
        repeated_id,
        current_id,
        revision_state,
        accepted,
        attempt_statuses,
        set_count,
        item_count,
    ) = asyncio.run(reconcile())
    assert candidate_id == repeated_id
    assert current_id is None
    assert revision_state == "candidate"
    assert accepted is False
    assert attempt_statuses == []
    assert set_count == 1
    assert item_count == 0


def test_automatic_candidate_uses_exact_workspace_builtin_default_once(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "automatic-summary-candidate")
    service = _service_module()

    async def create_twice() -> tuple:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            workspace = await db.get(Workspace, meeting.workspace_id)
            assert workspace is not None
            workspace.default_summary_template_key = "graf-meeting-minutes-v1"
            workspace.default_summary_template_id = None
            workspace.default_summary_template_version = 1
            baseline = await service.ensure_outcomes_for_processing_result(
                db,
                result=result,
            )
            current_before = meeting.current_outcome_set_id
            first = await ensure_automatic_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
            )
            second = await ensure_automatic_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
            )
            attempts = (
                await db.scalars(
                    select(MeetingOutcomeGenerationAttempt).where(
                        MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
                        MeetingOutcomeGenerationAttempt.generator_version
                        == AI_GENERATOR_VERSION,
                    )
                )
            ).all()
            intents = (
                await db.scalars(
                    select(DispatchIntent).where(DispatchIntent.meeting_id == meeting_id)
                )
            ).all()
            slot = await db.scalar(
                select(MeetingSummarySlot).where(
                    MeetingSummarySlot.workspace_id == meeting.workspace_id,
                    MeetingSummarySlot.meeting_id == meeting.id,
                    MeetingSummarySlot.template_key == "graf-meeting-minutes-v1",
                )
            )
            assert slot is not None
            await db.commit()
            assert first is not None and second is not None
            assert first.detail_level == "detailed"
            assert workspace.default_summary_template_version == 1
            assert slot.default_resolution_version == "workspace-default:graf-meeting-minutes-v1:v2"
            return (
                baseline.id,
                current_before,
                meeting.current_outcome_set_id,
                first.candidate_id,
                second.candidate_id,
                first.template_key,
                first.template_version,
                first.requested_by_user_id,
                first.status,
                len(attempts),
                len(intents),
                intents[0].state,
                slot.is_meeting_default,
                slot.default_resolution_source,
            )

    (
        baseline_id,
        current_before,
        current_after,
        first_candidate,
        second_candidate,
        template_key,
        template_version,
        requested_by,
        status,
        attempt_count,
        intent_count,
        intent_state,
        is_default,
        resolution_source,
    ) = asyncio.run(create_twice())
    assert current_before is None
    assert current_after is None
    assert first_candidate == second_candidate
    assert (template_key, template_version) == ("graf-meeting-minutes-v1", 2)
    assert requested_by == USER_ID
    assert status == "queued"
    assert attempt_count == intent_count == 1
    assert intent_state == "created"
    assert is_default is True
    assert resolution_source == "workspace"


def test_automatic_candidate_preserves_an_existing_explicit_default(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "automatic-summary-default-conflict")

    async def run() -> tuple[bool, bool, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            workspace = await db.get(Workspace, meeting.workspace_id)
            assert workspace is not None
            workspace.default_summary_template_key = "graf-meeting-minutes-v1"
            workspace.default_summary_template_version = 1
            explicit = await mark_meeting_default_slot(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                template_key="graf-auto-v1",
                resolution_source="explicit_meeting",
                resolution_version="test-explicit-v1",
                resolved_at=datetime(2026, 8, 31, tzinfo=UTC),
            )
            candidate = await ensure_automatic_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
            )
            automatic = await db.scalar(
                select(MeetingSummarySlot).where(
                    MeetingSummarySlot.workspace_id == meeting.workspace_id,
                    MeetingSummarySlot.meeting_id == meeting.id,
                    MeetingSummarySlot.template_key == "graf-meeting-minutes-v1",
                )
            )
            assert candidate is not None and automatic is not None
            result = (explicit.is_meeting_default, automatic.is_meeting_default, explicit.template_key)
            await db.rollback()
            return result

    assert asyncio.run(run()) == (True, False, "graf-auto-v1")


def test_missing_summary_default_reconciliation_only_marks_populated_slot(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "missing-summary-default-reconciliation")

    async def run() -> tuple[int, int, bool, object, object]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            workspace = await db.get(Workspace, meeting.workspace_id)
            assert workspace is not None
            workspace.default_summary_template_key = "graf-auto-v1"
            workspace.default_summary_template_version = 1
            outcome = await _protocol_row(db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=result.media_revision_id,
                processing_result_id=result.id,
                status="available",
                source_kind="db_fixture",
                generator_kind="litellm",
                generator_version="test:automatic-ai",
                source_result_hash=result.source_result_hash,
                source_fingerprint=f"result:{result.id}",
                template_key="graf-auto-v1",
                template_version=2,
                revision_state="accepted",
            )
            db.add(outcome)
            await db.flush()
            slot = MeetingSummarySlot(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                template_key="graf-auto-v1",
                current_outcome_set_id=outcome.id,
                current_binding_class="verified_complete",
                is_meeting_default=False,
            )
            db.add(slot)
            await db.flush()
            document_hash_before = _content_hash(outcome.protocol_json)
            repaired = await reconcile_missing_summary_defaults(db, limit=10)
            await db.refresh(slot)
            second_pass = await reconcile_missing_summary_defaults(db, limit=10)
            await db.refresh(slot)
            await db.refresh(outcome)
            assert slot.current_outcome_set_id == outcome.id
            assert outcome.revision_state == "accepted"
            assert outcome.protocol_state == "available"
            assert outcome.content_hash == document_hash_before == _content_hash(outcome.protocol_json)
            assert workspace.default_summary_template_version == 1
            result_tuple = (
                repaired,
                second_pass,
                slot.is_meeting_default,
                slot.default_resolution_source,
                slot.default_resolution_version,
            )
            await db.rollback()
            return result_tuple

    assert asyncio.run(run()) == (
        1,
        0,
        True,
        "workspace",
        "workspace-default:graf-auto-v1:v1",
    )


@pytest.mark.parametrize("existing_wait_projection", [False, True])
def test_unrequested_ready_result_is_backfilled_once(client, existing_wait_projection) -> None:
    meeting_id = create_outcome_ready_meeting(client, "unrequested-summary-backfill")

    async def reconcile() -> tuple[int, int, int, str]:
        async with client.app_state["sessionmaker"]() as db:
            if existing_wait_projection:
                result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
                waiting = await outcome_service.ensure_outcomes_for_processing_result(
                    db, result=result, ai_dispatch_planned=True,
                )
                assert waiting.candidate_id is None and waiting.protocol_json is None
                await db.commit()
            first = await reconcile_unrequested_summary_candidates(db, limit=10)
            second = await reconcile_unrequested_summary_candidates(db, limit=10)
            attempts = await db.scalar(
                select(func.count())
                .select_from(MeetingOutcomeGenerationAttempt)
                .where(MeetingOutcomeGenerationAttempt.meeting_id == meeting_id)
            )
            intents = await db.scalar(
                select(func.count())
                .select_from(DispatchIntent)
                .where(DispatchIntent.meeting_id == meeting_id)
            )
            attempt = await db.scalar(
                select(MeetingOutcomeGenerationAttempt).where(
                    MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
                    MeetingOutcomeGenerationAttempt.request_intent == "automatic_baseline",
                )
            )
            assert attempt is not None
            status = attempt.status
            await db.rollback()
            return first, second, int(attempts or 0), int(intents or 0), status

    assert asyncio.run(reconcile()) == (1, 0, 1, 1, "queued")


def test_automatic_replay_replaces_an_attempt_not_current_in_its_slot(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "automatic-summary-replay")

    async def replay_after_supersession() -> tuple:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            first = await ensure_automatic_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
            )
            assert first is not None and first.candidate_id is not None
            generated = await _protocol_row(db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                candidate_id=first.candidate_id,
                status="available",
                generator_version=f"test:auto:{first.candidate_id}",
                revision_state="superseded",
            )
            replacement = await _protocol_row(db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                candidate_id=None,
                status="available",
                generator_version="test:manual-replacement",
                revision_state="accepted",
            )
            db.add_all([generated, replacement])
            await db.flush()
            first.status = "accepted"
            first.outcome_set_id = generated.id
            # The legacy global pointer is deliberately not part of the
            # replay decision; the target slot remains the source of truth.
            db.add(
                ProcessingAuditEvent(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    actor_user_id=meeting.created_by_user_id,
                    event_type="speaker_display_name_set",
                    metadata_json={"speaker_key": "speaker_00"},
                )
            )
            await db.flush()
            replay = await ensure_automatic_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
            )
            attempts = await db.scalar(
                select(func.count())
                .select_from(MeetingOutcomeGenerationAttempt)
                .where(MeetingOutcomeGenerationAttempt.meeting_id == meeting_id)
            )
            intents = await db.scalar(
                select(func.count())
                .select_from(DispatchIntent)
                .where(DispatchIntent.meeting_id == meeting_id)
            )
            await db.rollback()
            assert replay is not None
            return first.candidate_id, replay.candidate_id, int(attempts or 0), int(intents or 0)

    first_id, replay_id, attempt_count, intent_count = asyncio.run(replay_after_supersession())
    assert replay_id != first_id
    assert attempt_count == intent_count == 2


def test_automatic_candidate_skips_invalid_policy_and_deleting_meeting(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "automatic-summary-policy-fences")

    async def exercise() -> tuple[object, object, int]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            workspace = await db.get(Workspace, meeting.workspace_id)
            assert workspace is not None
            workspace.default_summary_template_key = "missing-template"
            invalid_policy = await ensure_automatic_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
            )
            workspace.default_summary_template_key = "graf-auto-v1"
            meeting.deletion_state = "requested"
            deleting = await ensure_automatic_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
            )
            attempts = await db.scalar(
                select(func.count())
                .select_from(MeetingOutcomeGenerationAttempt)
                .where(
                    MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
                    MeetingOutcomeGenerationAttempt.generator_version
                    == AI_GENERATOR_VERSION,
                )
            )
            await db.rollback()
            return invalid_policy, deleting, int(attempts or 0)

    assert asyncio.run(exercise()) == (None, None, 0)


def test_deletion_state_is_checked_under_the_meeting_lock_before_outcome_mutation(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    service = _service_module()

    async def attempt_while_deletion_commits() -> int:
        sessionmaker = client.app_state["sessionmaker"]
        async with sessionmaker() as locker, sessionmaker() as worker:
            result_a = await locker.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            meeting_a = await locker.scalar(
                select(Meeting)
                .where(Meeting.id == meeting_id)
                .with_for_update()
            )
            result_b = await worker.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert result_a is not None
            assert result_b is not None
            assert meeting_a is not None
            meeting_a.deletion_state = "requested"

            blocked = asyncio.create_task(
                service.ensure_outcomes_for_processing_result(worker, result=result_b)
            )
            await asyncio.sleep(0.05)
            assert not blocked.done(), "generation must wait for the Meeting deletion lock"
            await locker.commit()

            with pytest.raises(RuntimeError, match="meeting_deleting"):
                await asyncio.wait_for(blocked, timeout=5)
            rows = (
                await worker.scalars(
                    select(MeetingOutcomeSet).where(MeetingOutcomeSet.meeting_id == meeting_id)
                )
            ).all()
            await worker.rollback()
            return len(rows)

    assert asyncio.run(attempt_while_deletion_commits()) == 0
def test_old_processing_result_cannot_create_baseline_after_new_revision_is_accepted(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "outcome-source-race")
    service = _service_module()

    async def run() -> int:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            assert result is not None and meeting is not None and result.media_revision_id is not None
            db.add(
                MediaRevision(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    local_media_revision_id="outcome-source-race--replacement",
                    revision_number=2,
                    source_kind="reprocess",
                    status="accepted",
                    manifest_sha256="b" * 64,
                    track_sha256_by_role={"media": "c" * 64},
                    duration_seconds=meeting.duration_seconds,
                    immutable=True,
                    accepted_at=datetime.now(UTC),
                )
            )
            await db.commit()
            with pytest.raises(ProcessingLifecycleBlocked, match="summary_source_revision_stale"):
                await service.ensure_outcomes_for_processing_result(db, result=result)
            return len(
                (
                    await db.scalars(
                        select(MeetingOutcomeSet).where(MeetingOutcomeSet.meeting_id == meeting_id)
                    )
                ).all()
            )

    assert asyncio.run(run()) == 0


def test_old_result_version_cannot_create_baseline_after_same_revision_retry(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "outcome-result-version-race")
    service = _service_module()

    async def run() -> int:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            assert result is not None and meeting is not None and result.media_revision_id is not None
            db.add(
                ProcessingResult(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    media_revision_id=result.media_revision_id,
                    mediascribe_job_id=result.mediascribe_job_id,
                    processing_workflow_id=result.processing_workflow_id,
                    deletion_epoch_at_start=result.deletion_epoch_at_start,
                    result_version=result.result_version + 1,
                    status="imported",
                    transcript_status=ProcessingAvailabilityStatus.AVAILABLE.value,
                    diarization_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
                    segment_count=result.segment_count,
                    source_result_hash="f" * 64,
                    imported_at=datetime.now(UTC) + timedelta(seconds=1),
                )
            )
            await db.commit()
            with pytest.raises(ProcessingLifecycleBlocked, match="summary_source_result_stale"):
                await service.ensure_outcomes_for_processing_result(db, result=result)
            return len(
                (
                    await db.scalars(
                        select(MeetingOutcomeSet).where(MeetingOutcomeSet.meeting_id == meeting_id)
                    )
                ).all()
            )

    assert asyncio.run(run()) == 0


def test_waiting_protocol_does_not_claim_sections_are_absent(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)

    async def run() -> None:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            assert result is not None
            outcome = await outcome_service.ensure_outcomes_for_processing_result(
                db, result=result, ai_dispatch_planned=True,
            )
            assert outcome.protocol_state == "processing"
            assert outcome.protocol_json is None and outcome.content_hash is None
            assert outcome.accepted_at is None
            # No model has read the transcript: empty/not-found semantic claims would be false.
            assert outcome.candidate_id is None
            assert await db.scalar(select(func.count()).select_from(MeetingOutcomeItem).where(
                MeetingOutcomeItem.outcome_set_id == outcome.id,
            )) == 0

    asyncio.run(run())


def test_blocked_outcome_can_retry_after_transcript_becomes_available(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    service = _service_module()

    async def run() -> None:
        sessionmaker = client.app_state["sessionmaker"]
        async with sessionmaker() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            assert result is not None
            result.transcript_status = ProcessingAvailabilityStatus.UNAVAILABLE.value
            result.segment_count = 0
            result.failure_reason = "no_recognizable_speech"
            result.failure_source = "input_audio"
            blocked = await service.ensure_outcomes_for_processing_result(db, result=result)
            assert blocked.status == "blocked" and blocked.protocol_state == "unavailable"
            assert blocked.failure_reason == "no_recognizable_speech"
            assert blocked.failure_source == "input_audio"
            assert blocked.protocol_json is None and blocked.candidate_id is None
            assert await ensure_automatic_summary_candidate(
                db, workspace_id=result.workspace_id, meeting_id=meeting_id,
            ) is None
            assert await db.scalar(select(func.count()).select_from(MeetingOutcomeGenerationAttempt).where(
                MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
            )) == 0
            await db.commit()

        async with sessionmaker() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            result.transcript_status = ProcessingAvailabilityStatus.AVAILABLE.value
            result.segment_count = 2
            result.failure_reason = None
            result.failure_source = None
            attempt = await ensure_automatic_summary_candidate(
                db, workspace_id=result.workspace_id, meeting_id=meeting_id,
            )
            assert attempt is not None and attempt.status == "queued"
            assert attempt.candidate_id is not None and attempt.outcome_set_id is None
            retried = await service.ensure_outcomes_for_processing_result(
                db, result=result, ai_dispatch_planned=True,
            )
            assert retried.id == blocked.id  # State-only projection; not immutable generated content.
            assert retried.status == "generating" and retried.protocol_state == "processing"
            assert retried.failure_reason is None and retried.failure_source is None
            assert retried.protocol_json is None and retried.candidate_id is None
            assert await db.scalar(select(func.count()).select_from(MeetingOutcomeItem).where(
                MeetingOutcomeItem.meeting_id == meeting_id,
            )) == 0
            assert await db.scalar(select(func.count()).select_from(MeetingOutcomeGenerationAttempt).where(
                MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
            )) == 1
            assert (await db.get(Meeting, meeting_id)).current_outcome_set_id is None
            await db.commit()

    asyncio.run(run())


def test_revision_scoped_blocked_outcome_recovery_creates_new_candidate_lineage(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "revision-blocked-lineage")

    async def run() -> None:
        sessionmaker = client.app_state["sessionmaker"]
        async with sessionmaker() as db:
            meeting = await db.get(Meeting, meeting_id)
            first = await ensure_automatic_summary_candidate(
                db, workspace_id=meeting.workspace_id, meeting_id=meeting_id,
            )
            assert first is not None
            result = await db.get(ProcessingResult, first.processing_result_id)
            result.transcript_status = ProcessingAvailabilityStatus.UNAVAILABLE.value
            result.segment_count = 0
            result.failure_reason = "no_recognizable_speech"
            result.failure_source = "input_audio"
            blocked = await outcome_service.ensure_outcomes_for_processing_result(db, result=result)
            assert blocked.protocol_state == "unavailable" and blocked.protocol_json is None
            await db.commit()

        await finalize_candidate_generation_failure(
            sessionmaker, workspace_id=first.workspace_id, candidate_id=first.candidate_id,
            failure_code="summary_transcript_unavailable",
        )
        async with sessionmaker() as db:
            first = await db.get(MeetingOutcomeGenerationAttempt, first.id)
            assert first.status == "failed" and first.ended_at is not None
            result = await db.get(ProcessingResult, first.processing_result_id)
            result.transcript_status = ProcessingAvailabilityStatus.AVAILABLE.value
            result.segment_count = 2
            result.failure_reason = None
            result.failure_source = None
            retry = await create_summary_candidate(
                db, workspace_id=first.workspace_id, meeting_id=meeting_id,
                requested_by_user_id=USER_ID, template_key="graf-auto-v1",
                template_id=None, template_version=2, expected_current_outcome_set_id=None,
                request_intent="manual_refresh", request_intent_id=uuid4(),
            )
            assert retry.id != first.id and retry.candidate_id != first.candidate_id
            assert retry.status == "queued" and retry.outcome_set_id is None
            assert retry.media_revision_id == first.media_revision_id
            assert retry.processing_result_id == first.processing_result_id
            assert first.status == "failed" and first.failure_code == "summary_transcript_unavailable"
            assert await db.scalar(select(func.count()).select_from(MeetingOutcomeGenerationAttempt).where(
                MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
            )) == 2
            prior_dispatch = await db.scalar(select(DispatchIntent).where(
                DispatchIntent.candidate_id == first.candidate_id,
            ))
            assert prior_dispatch.state == "terminal_failed"
            assert (await db.get(Meeting, meeting_id)).current_outcome_set_id is None

    asyncio.run(run())


@pytest.mark.parametrize("failure_stage", ["extract", "draft", "verify"])
def test_generation_failure_records_safe_blocked_attempt_without_losing_review(
    client, monkeypatch, failure_stage,
) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    calls = []
    marker = "synthetic provider detail must not enter attempt metadata"
    stages = [EXTRACTOR_PROMPT_NAME, "graf/meeting-outcome/meeting-minutes", VERIFIER_PROMPT_NAME]
    failing_stage = {"extract": 1, "draft": 2, "verify": 3}[failure_stage]
    monkeypatch.setattr(
        "twobrain_rec_server.outcomes.ai_service._read_secret", lambda _path: "synthetic-unused",
    )

    async def run() -> None:
        sessionmaker = client.app_state["sessionmaker"]
        async with sessionmaker() as db:
            accepted, _ = await seed_accepted_protocol(db, meeting_id)
            attempt, segments = await prepare_protocol_candidate(
                db, meeting_id, template_key="graf-meeting-minutes-v1",
            )
        draft = protocol_result(segments)

        async def generate(_self, *, snapshot, messages, **_kwargs):
            calls.append(snapshot.name)
            if snapshot.name == stages[failing_stage - 1]:
                raise LiteLLMError(
                    "summary_provider_error", retryable=False, raw_response={"error": marker},
                )
            result = extraction_result(segments) if snapshot.name == EXTRACTOR_PROMPT_NAME else draft
            return protocol_gateway_response(snapshot, messages, result)

        monkeypatch.setattr("twobrain_rec_server.outcomes.ai_service.LiteLLMGateway.generate", generate)
        result = await execute_candidate_generation(
            sessionmaker, workspace_id=attempt.workspace_id, candidate_id=attempt.candidate_id,
            expected_snapshot_hash=attempt.temporal_transcript_hash,
            settings=Settings(litellm_base_url="https://example.invalid", langfuse_project_id="synthetic-project"),
        )
        assert result["state"] == "failed" and result["failure_code"] == "summary_provider_error"
        async with sessionmaker() as db:
            attempt = await db.get(MeetingOutcomeGenerationAttempt, attempt.id)
            assert attempt.status == "failed" and attempt.ended_at is not None
            assert attempt.outcome_set_id is None
            assert marker not in str(attempt.metadata_json)
            assert marker not in str(attempt.failure_reason)
            slots = (await db.scalars(select(MeetingSummarySlot).where(
                MeetingSummarySlot.meeting_id == meeting_id,
            ))).all()
            assert {slot.template_key: slot.current_outcome_set_id for slot in slots} == {
                "graf-auto-v1": accepted.id, "graf-meeting-minutes-v1": None,
            }
            prior = await db.get(MeetingOutcomeSet, accepted.id)
            assert prior.revision_state == "accepted"
            assert prior.protocol_state == "available" and prior.protocol_json == accepted.protocol_json
            ledger = (await db.scalars(select(GenerationCall).where(
                GenerationCall.candidate_id == attempt.candidate_id,
            ).order_by(GenerationCall.call_sequence))).all()
            assert len(ledger) == failing_stage
            assert ledger[-1].raw_response_json == {"error": marker}
            assert (await db.get(Meeting, meeting_id)).current_outcome_set_id == accepted.id

    asyncio.run(run())
    assert calls == stages[:failing_stage]


def test_expired_automatic_candidate_requires_explicit_refresh_with_new_bounded_lineage(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "expired-baseline-retry")

    async def run() -> None:
        sessionmaker = client.app_state["sessionmaker"]
        async with sessionmaker() as db:
            meeting = await db.get(Meeting, meeting_id)
            first = await ensure_automatic_summary_candidate(
                db, workspace_id=meeting.workspace_id, meeting_id=meeting_id,
            )
            assert first is not None
            first.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()

        async with sessionmaker() as db:
            replay = await ensure_automatic_summary_candidate(
                db, workspace_id=first.workspace_id, meeting_id=meeting_id,
            )
            assert replay is not None and replay.id == first.id
            assert replay.status == "expired"
            prior_dispatch = await db.scalar(select(DispatchIntent).where(
                DispatchIntent.candidate_id == first.candidate_id,
            ))
            assert prior_dispatch.state == "cancelled"
            retried = await create_summary_candidate(
                db, workspace_id=first.workspace_id, meeting_id=meeting_id,
                requested_by_user_id=USER_ID, template_key="graf-auto-v1",
                template_id=None, template_version=2, expected_current_outcome_set_id=None,
                request_intent="manual_refresh", request_intent_id=uuid4(),
            )
            expired = await db.get(MeetingOutcomeGenerationAttempt, first.id)
            assert expired.id != retried.id and expired.candidate_id != retried.candidate_id
            assert expired.expires_at is not None and retried.expires_at is not None
            assert retried.expires_at > datetime.now(UTC)
            assert retried.expires_at > expired.expires_at
            assert expired.status == "expired"
            assert expired.failure_code == "summary_candidate_expired"
            assert expired.ended_at is not None
            assert retried.status == "queued"
            assert expired.outcome_set_id is None and retried.outcome_set_id is None
            assert await db.scalar(select(func.count()).select_from(MeetingOutcomeGenerationAttempt).where(
                MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
            )) == 2
            assert (await db.get(Meeting, meeting_id)).current_outcome_set_id is None

    asyncio.run(run())


def test_generation_failure_preserves_root_code_and_closes_dispatch(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "generation-failure-lineage")
    import twobrain_rec_server.outcomes.ai_service as ai_service
    from twobrain_rec_server.outcomes.dispatch import ensure_dispatch_intent

    async def project_failure() -> tuple[str, str | None, str | None, str, str]:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            meeting = await db.get(Meeting, meeting_id)
            assert result is not None and meeting is not None
            attempt = await ai_service.create_summary_candidate(
                db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                requested_by_user_id=USER_ID,
                template_key="graf-auto-v1",
                template_id=None,
                template_version=2,
                expected_current_outcome_set_id=meeting.current_outcome_set_id,
            )
            intent = await ensure_dispatch_intent(
                db,
                workspace_id=WORKSPACE_ID,
                meeting=meeting,
                candidate_id=attempt.candidate_id,
                idempotency_key=attempt.idempotency_key or f"candidate:{attempt.candidate_id}",
                source_fingerprint=attempt.source_fingerprint,
            )
            intent.state = "started"
            intent.reconciliation_state = "started"
            attempt.status = "failed"
            attempt.failure_code = "summary_prompt_snapshot_invalid"
            await db.commit()

        await ai_service.finalize_candidate_generation_failure(
            client.app_state["sessionmaker"],
            workspace_id=WORKSPACE_ID,
            candidate_id=attempt.candidate_id,
            failure_code="summary_generation_retries_exhausted",
            failure_reason="summary_generation_retries_exhausted",
        )

        async with client.app_state["sessionmaker"]() as db:
            persisted_attempt = await db.scalar(
                select(MeetingOutcomeGenerationAttempt).where(
                    MeetingOutcomeGenerationAttempt.candidate_id == attempt.candidate_id
                )
            )
            persisted_intent = await db.scalar(
                select(DispatchIntent).where(DispatchIntent.candidate_id == attempt.candidate_id)
            )
            assert persisted_attempt is not None and persisted_intent is not None
            return (
                persisted_attempt.status,
                persisted_attempt.failure_code,
                persisted_attempt.failure_reason,
                persisted_intent.state,
                persisted_intent.reconciliation_state,
            )

    status, failure_code, failure_reason, dispatch_state, reconciliation_state = asyncio.run(
        project_failure()
    )
    assert status == "failed"
    assert failure_code == "summary_prompt_snapshot_invalid"
    assert failure_reason == "summary_generation_retries_exhausted"
    assert dispatch_state == "terminal_failed"
    assert reconciliation_state == "terminal"


def test_started_dispatch_lease_recovers_after_worker_crash(client) -> None:
    """A post-Temporal-start crash must not strand a generating candidate."""
    meeting_id = create_outcome_ready_meeting(client, "dispatch-start-lease")
    import twobrain_rec_server.outcomes.ai_service as ai_service
    from tests.fakes.fake_temporal import FakeTemporalClient
    from twobrain_rec_server.outcomes.dispatch import (
        MAX_DISPATCH_ATTEMPTS,
        ensure_dispatch_intent,
        list_due_dispatch_intents,
        mark_dispatch_started,
        reconcile_dispatch_intent,
    )

    async def exercise() -> tuple[str, str, str | None, bool, str, str]:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            meeting = await db.get(Meeting, meeting_id)
            assert result is not None and meeting is not None
            attempt = await ai_service.create_summary_candidate(
                db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                requested_by_user_id=USER_ID,
                template_key="graf-auto-v1",
                template_id=None,
                template_version=2,
                expected_current_outcome_set_id=meeting.current_outcome_set_id,
            )
            intent = await ensure_dispatch_intent(
                db,
                workspace_id=WORKSPACE_ID,
                meeting=meeting,
                candidate_id=attempt.candidate_id,
                idempotency_key=attempt.idempotency_key or f"candidate:{attempt.candidate_id}",
                source_fingerprint=attempt.source_fingerprint,
            )
            await mark_dispatch_started(
                db,
                workspace_id=WORKSPACE_ID,
                idempotency_key=intent.idempotency_key,
                workflow_id=f"outcome-generation/{attempt.candidate_id}",
                run_id="run-before-crash",
            )
            await db.commit()

        async with client.app_state["sessionmaker"]() as db:
            persisted = await db.scalar(
                select(DispatchIntent).where(DispatchIntent.candidate_id == attempt.candidate_id)
            )
            assert persisted is not None and persisted.lease_expires_at is not None
            # A callback/worker loss after Temporal acknowledged the start is
            # also recoverable: the deterministic workflow id makes the retry
            # safe and Temporal returns AlreadyStarted.
            persisted.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()

        async with client.app_state["sessionmaker"]() as db:
            due = await list_due_dispatch_intents(db)
            assert len(due) == 1
            recovered = due[0]
            recovered_state = (
                recovered.state,
                recovered.reconciliation_state,
                recovered.failure_code,
                recovered.next_attempt_at is not None,
            )
            recovered.attempt_count = MAX_DISPATCH_ATTEMPTS
            await db.commit()
            await reconcile_dispatch_intent(
                db,
                intent=recovered,
                settings=client.app.state.settings,
                temporal_client=FakeTemporalClient(),
            )
            persisted_intent = await db.scalar(
                select(DispatchIntent).where(DispatchIntent.id == recovered.id)
            )
            persisted_attempt = await db.scalar(
                select(MeetingOutcomeGenerationAttempt).where(
                    MeetingOutcomeGenerationAttempt.candidate_id == attempt.candidate_id
                )
            )
            assert persisted_intent is not None and persisted_attempt is not None
            return (*recovered_state, persisted_intent.state, persisted_attempt.status)

    state, reconciliation_state, failure_code, scheduled, terminal_state, attempt_state = asyncio.run(
        exercise()
    )
    assert state == "retryable_failed"
    assert reconciliation_state == "pending"
    assert failure_code == "summary_dispatch_started_lease_expired"
    assert scheduled
    assert terminal_state == "terminal_failed"
    assert attempt_state == "failed"


def test_slow_temporal_start_is_bounded_and_reconcilable(client, monkeypatch) -> None:
    """A stalled SDK start keeps the deterministic workflow recoverable."""
    meeting_id = create_outcome_ready_meeting(client, "dispatch-slow-start")
    import twobrain_rec_server.outcomes.ai_service as ai_service
    import twobrain_rec_server.outcomes.dispatch as dispatch
    import twobrain_rec_server.workflows.temporal_client as temporal_client

    monkeypatch.setattr(dispatch, "DISPATCH_START_TIMEOUT_SECONDS", 0.001)
    submitted: dict[str, object] = {}

    async def slow_start(**kwargs):
        submitted.update(kwargs)
        await asyncio.sleep(0.02)
        raise AssertionError("the bounded start should time out first")

    monkeypatch.setattr(temporal_client, "start_outcome_generation_workflow", slow_start)

    cancelled = False

    class _Handle:
        async def cancel(self):
            nonlocal cancelled
            cancelled = True

    class _TemporalClient:
        def get_workflow_handle(self, _workflow_id):
            return _Handle()

    async def exercise() -> tuple[str, str, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            attempt = await ai_service.create_summary_candidate(
                db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                requested_by_user_id=USER_ID,
                template_key="graf-auto-v1",
                template_id=None,
                template_version=2,
                expected_current_outcome_set_id=meeting.current_outcome_set_id,
            )
            intent = await dispatch.ensure_dispatch_intent(
                db,
                workspace_id=WORKSPACE_ID,
                meeting=meeting,
                candidate_id=attempt.candidate_id,
                idempotency_key=attempt.idempotency_key or f"candidate:{attempt.candidate_id}",
                source_fingerprint=attempt.source_fingerprint,
            )
            await db.commit()
            await dispatch.reconcile_dispatch_intent(
                db,
                intent=intent,
                settings=client.app.state.settings,
                temporal_client=_TemporalClient(),
            )
            persisted_intent = await db.scalar(
                select(DispatchIntent).where(DispatchIntent.id == intent.id)
            )
            persisted_attempt = await db.scalar(
                select(MeetingOutcomeGenerationAttempt).where(
                    MeetingOutcomeGenerationAttempt.candidate_id == attempt.candidate_id
                )
            )
            assert persisted_intent is not None and persisted_attempt is not None
            return persisted_intent.state, persisted_attempt.status, persisted_intent.failure_code

    state, attempt_state, failure_code = asyncio.run(exercise())
    assert state == "started"
    assert attempt_state == "queued"
    assert failure_code is None
    assert cancelled is False
    assert isinstance(submitted["summary_slot_id"], UUID)
    assert submitted["expected_current_outcome_set_id"] is None


def test_temporal_dispatch_retry_exhaustion_closes_candidate_for_manual_retry(client, monkeypatch) -> None:
    meeting_id = create_outcome_ready_meeting(client, "dispatch-retry-exhaustion")
    import twobrain_rec_server.outcomes.ai_service as ai_service
    import twobrain_rec_server.outcomes.dispatch as dispatch
    import twobrain_rec_server.workflows.temporal_client as temporal_client

    async def fail_start(**_kwargs):
        raise RuntimeError("simulated Temporal outage")

    monkeypatch.setattr(temporal_client, "start_outcome_generation_workflow", fail_start)

    async def exercise() -> tuple[str, str, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            attempt = await ai_service.create_summary_candidate(
                db,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                requested_by_user_id=USER_ID,
                template_key="graf-meeting-minutes-v1",
                template_id=None,
                template_version=2,
                expected_current_outcome_set_id=meeting.current_outcome_set_id,
            )
            intent = await dispatch.ensure_dispatch_intent(
                db,
                workspace_id=WORKSPACE_ID,
                meeting=meeting,
                candidate_id=attempt.candidate_id,
                idempotency_key=attempt.idempotency_key or f"candidate:{attempt.candidate_id}",
                source_fingerprint=attempt.source_fingerprint,
            )
            intent.attempt_count = dispatch.MAX_DISPATCH_ATTEMPTS - 1
            await db.commit()
            await dispatch.reconcile_dispatch_intent(
                db,
                intent=intent,
                settings=client.app.state.settings,
                temporal_client=object(),
            )
            persisted_intent = await db.scalar(
                select(DispatchIntent).where(DispatchIntent.id == intent.id)
            )
            persisted_attempt = await db.scalar(
                select(MeetingOutcomeGenerationAttempt).where(
                    MeetingOutcomeGenerationAttempt.candidate_id == attempt.candidate_id
                )
            )
            assert persisted_intent is not None and persisted_attempt is not None
            return persisted_intent.state, persisted_attempt.status, persisted_attempt.failure_code

    state, attempt_state, failure_code = asyncio.run(exercise())
    assert state == "terminal_failed"
    assert attempt_state == "failed"
    assert failure_code == "summary_dispatch_retries_exhausted"
