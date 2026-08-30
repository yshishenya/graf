from __future__ import annotations

import asyncio
import importlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, func, select

from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
from tests.fixtures.cabinet import create_outcome_ready_meeting
from twobrain_rec_server.api.schemas import CreateSummaryCandidateRequest
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    DispatchIntent,
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
from twobrain_rec_server.outcomes.ai_service import (
    AI_GENERATOR_VERSION,
    OutcomeGenerationTerminalError,
    ensure_automatic_summary_candidate,
    publish_model_generated_outcome,
)
from twobrain_rec_server.processing.store import ProcessingLifecycleBlocked


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
        "template_version": 1,
        forbidden_field: {},
    }

    with pytest.raises(ValidationError):
        CreateSummaryCandidateRequest.model_validate(payload)


def _service_module():
    try:
        return importlib.import_module("twobrain_rec_server.outcomes.service")
    except ModuleNotFoundError as exc:
        raise AssertionError("outcome service module is missing") from exc


def test_outcome_generation_is_idempotent_and_stores_source_evidence(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    service = _service_module()

    async def generate_twice() -> tuple[int, int, list[MeetingOutcomeItem]]:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            assert result is not None
            first = await service.ensure_outcomes_for_processing_result(db, result=result)
            second = await service.ensure_outcomes_for_processing_result(db, result=result)
            sets = (await db.scalars(select(MeetingOutcomeSet).where(MeetingOutcomeSet.meeting_id == meeting_id))).all()
            items = (
                await db.scalars(
                    select(MeetingOutcomeItem)
                    .where(MeetingOutcomeItem.meeting_id == meeting_id)
                    .order_by(MeetingOutcomeItem.category, MeetingOutcomeItem.sequence)
                )
            ).all()
            await db.commit()
            assert first.id == second.id
            return len(sets), len(items), items

    set_count, item_count, items = asyncio.run(generate_twice())

    assert set_count == 1
    assert item_count >= 3
    assert all(item.workspace_id for item in items)
    assert all(item.source_refs_json for item in items if item.state == "available")
    assert {item.category for item in items} >= {"summary", "key_points", "evidence"}


def test_provider_only_legacy_result_generates_outcomes_from_canonical_turns(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "provider-only-outcomes")
    service = _service_module()

    async def generate() -> tuple[str, set[str], set[str]]:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert result is not None
            provider_ids = {
                str(value)
                for value in (
                    await db.scalars(
                        select(DiarizationSegment.id).where(
                            DiarizationSegment.processing_result_id == result.id
                        )
                    )
                ).all()
            }
            await db.execute(
                delete(TranscriptSegment).where(
                    TranscriptSegment.processing_result_id == result.id
                )
            )
            result.segment_count = 0
            outcome_set = await service.ensure_outcomes_for_processing_result(db, result=result)
            items = (
                await db.scalars(
                    select(MeetingOutcomeItem).where(
                        MeetingOutcomeItem.outcome_set_id == outcome_set.id
                    )
                )
            ).all()
            referenced_ids = {
                str(reference["transcript_segment_id"])
                for item in items
                for reference in item.source_refs_json
            }
            await db.commit()
            return outcome_set.status, provider_ids, referenced_ids

    status, provider_ids, referenced_ids = asyncio.run(generate())

    assert status == "available"
    assert referenced_ids
    assert referenced_ids <= provider_ids


def test_first_baseline_outcome_remains_an_unpublished_candidate(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    service = _service_module()

    async def generate_and_repair() -> tuple:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            meeting = await db.get(Meeting, meeting_id)
            assert result is not None
            assert meeting is not None
            outcome_set = await service.ensure_outcomes_for_processing_result(db, result=result)
            await db.commit()
            first = (
                meeting.current_outcome_set_id,
                outcome_set.revision_state,
                outcome_set.accepted_at is not None,
                outcome_set.requested_by_user_id,
                outcome_set.accepted_by_user_id,
                outcome_set.template_key,
                outcome_set.template_version,
                outcome_set.output_language,
                outcome_set.detail_level,
            )

            repaired = await service.ensure_outcomes_for_processing_result(db, result=result)
            await db.commit()
            return first, (
                meeting.current_outcome_set_id,
                repaired.revision_state,
                repaired.accepted_at is not None,
                repaired.requested_by_user_id,
                repaired.accepted_by_user_id,
                repaired.template_key,
                repaired.template_version,
                repaired.output_language,
                repaired.detail_level,
            ), outcome_set.id

    first, repaired, _outcome_set_id = asyncio.run(generate_and_repair())

    expected = (
        None,
        "candidate",
        False,
        None,
        None,
        "graf-auto-v1",
        1,
        None,
        None,
    )
    assert first == expected
    assert repaired == expected


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

            repeated = await service.ensure_outcomes_for_processing_result(
                db,
                result=result,
                publish_initial_baseline=True,
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
    assert attempt_statuses == ["blocked_dependency"]
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
                publish_initial_baseline=True,
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
            await db.commit()
            assert first is not None and second is not None
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
    ) = asyncio.run(create_twice())
    assert current_before is None
    assert current_after is None
    assert first_candidate == second_candidate
    assert (template_key, template_version) == ("graf-meeting-minutes-v1", 1)
    assert requested_by == USER_ID
    assert status == "queued"
    assert attempt_count == intent_count == 1
    assert intent_state == "created"


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
            generated = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                candidate_id=first.candidate_id,
                status="available",
                generator_version=f"test:auto:{first.candidate_id}",
                revision_state="superseded",
            )
            replacement = MeetingOutcomeSet(
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


def test_outcome_generation_preserves_not_inferable_category_truth(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    service = _service_module()

    async def generate() -> dict[str, str]:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            assert result is not None
            outcome_set = await service.ensure_outcomes_for_processing_result(db, result=result)
            await db.commit()
            return {
                "decisions": outcome_set.decisions_state,
                "action_items": outcome_set.action_items_state,
                "followups": outcome_set.followups_state,
            }

    states = asyncio.run(generate())

    assert set(states.values()) <= {"not_found", "not_inferable", "available"}
    assert states["action_items"] in {"not_found", "not_inferable"}


def test_blocked_outcome_can_retry_after_transcript_becomes_available(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    service = _service_module()

    async def block_then_retry() -> tuple[str, str, str | None, str | None, dict, int, int]:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            assert result is not None
            result.transcript_status = ProcessingAvailabilityStatus.UNAVAILABLE.value
            result.segment_count = 0
            result.failure_reason = "no_recognizable_speech"
            result.failure_source = "input_audio"
            blocked = await service.ensure_outcomes_for_processing_result(db, result=result)
            attempt = await db.scalar(
                select(MeetingOutcomeGenerationAttempt)
                .where(MeetingOutcomeGenerationAttempt.meeting_id == meeting_id)
                .order_by(MeetingOutcomeGenerationAttempt.created_at.desc())
            )
            await db.commit()
            assert blocked.status == "blocked"
            assert attempt is not None
            blocked_snapshot = (
                blocked.status,
                blocked.failure_reason,
                blocked.failure_source,
                attempt.failure_source,
                attempt.metadata_json,
            )

        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            assert result is not None
            result.transcript_status = ProcessingAvailabilityStatus.AVAILABLE.value
            result.segment_count = 2
            result.failure_reason = None
            result.failure_source = None
            retried = await service.ensure_outcomes_for_processing_result(db, result=result)
            items = (
                await db.scalars(
                    select(MeetingOutcomeItem)
                    .where(MeetingOutcomeItem.outcome_set_id == retried.id)
                    .order_by(MeetingOutcomeItem.category, MeetingOutcomeItem.sequence)
                )
            ).all()
            attempts = (
                await db.scalars(
                    select(MeetingOutcomeGenerationAttempt)
                    .where(MeetingOutcomeGenerationAttempt.meeting_id == meeting_id)
                    .order_by(MeetingOutcomeGenerationAttempt.created_at)
                )
            ).all()
            await db.commit()
            return (*blocked_snapshot, retried.status, len(items), len(attempts))

    (
        blocked_status,
        blocked_reason,
        blocked_source,
        attempt_source,
        attempt_metadata,
        retried_status,
        item_count,
        attempt_count,
    ) = asyncio.run(block_then_retry())

    assert blocked_status == "blocked"
    assert blocked_reason == "no_recognizable_speech"
    assert blocked_source == "input_audio"
    assert attempt_source == "input_audio"
    assert attempt_metadata["failure_source"] == "input_audio"
    assert retried_status == "available"
    assert item_count >= 3
    assert attempt_count >= 2


def test_revision_scoped_blocked_outcome_recovery_creates_new_candidate_lineage(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "revision-blocked-lineage")
    service = _service_module()

    async def block_then_retry() -> tuple[str, str, str, str, int]:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            assert result is not None and result.media_revision_id is not None
            result.transcript_status = ProcessingAvailabilityStatus.UNAVAILABLE.value
            result.segment_count = 0
            result.failure_reason = "no_recognizable_speech"
            blocked = await service.ensure_outcomes_for_processing_result(db, result=result)
            blocked_attempt = await db.scalar(
                select(MeetingOutcomeGenerationAttempt)
                .where(MeetingOutcomeGenerationAttempt.outcome_set_id == blocked.id)
            )
            assert blocked_attempt is not None and blocked_attempt.candidate_id == blocked.candidate_id
            await db.commit()

        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            assert result is not None
            result.transcript_status = ProcessingAvailabilityStatus.AVAILABLE.value
            result.segment_count = 2
            result.failure_reason = None
            result.failure_source = None
            retried = await service.ensure_outcomes_for_processing_result(db, result=result)
            attempts = (
                await db.scalars(
                    select(MeetingOutcomeGenerationAttempt)
                    .where(MeetingOutcomeGenerationAttempt.meeting_id == meeting_id)
                    .order_by(MeetingOutcomeGenerationAttempt.created_at)
                )
            ).all()
            await db.commit()
            assert retried.candidate_id is not None
            return (
                str(blocked.id),
                str(blocked.candidate_id),
                str(retried.id),
                str(retried.candidate_id),
                len(attempts),
            )

    blocked_id, blocked_candidate, retried_id, retried_candidate, attempt_count = asyncio.run(block_then_retry())

    assert blocked_id != retried_id
    assert blocked_candidate != retried_candidate
    assert attempt_count >= 2


def test_generation_failure_records_safe_blocked_attempt_without_losing_review(client, monkeypatch) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    service = _service_module()

    def fail_generation(_segments):
        raise RuntimeError("synthetic generator failure with no meeting content")

    monkeypatch.setattr(service, "generate_outcomes", fail_generation)

    async def generate() -> tuple[str, str | None, str, dict]:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            assert result is not None
            outcome_set = await service.ensure_outcomes_for_processing_result(db, result=result)
            attempt = await db.scalar(
                select(MeetingOutcomeGenerationAttempt)
                .where(MeetingOutcomeGenerationAttempt.meeting_id == meeting_id)
                .order_by(MeetingOutcomeGenerationAttempt.created_at.desc())
            )
            assert attempt is not None
            await db.commit()
            return outcome_set.status, outcome_set.failure_reason, attempt.status, attempt.metadata_json

    status, reason, attempt_status, metadata = asyncio.run(generate())

    assert status == "blocked"
    assert reason == "outcomes_generation_failed"
    assert attempt_status == "failed_terminal"
    assert "synthetic generator failure" not in str(metadata)


def test_expired_revision_baseline_is_restarted_with_new_bounded_candidate(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "expired-baseline-retry")
    service = _service_module()

    async def expire_then_retry() -> tuple[
        object,
        object,
        datetime | None,
        datetime | None,
        int,
        str,
        str | None,
        datetime | None,
    ]:
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            assert result is not None
            first = await service.ensure_outcomes_for_processing_result(db, result=result)
            first.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()

        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            assert result is not None
            retried = await service.ensure_outcomes_for_processing_result(db, result=result)
            attempts = (
                await db.scalars(
                    select(MeetingOutcomeGenerationAttempt).where(
                        MeetingOutcomeGenerationAttempt.meeting_id == meeting_id
                    )
                )
            ).all()
            expired_attempt = next(attempt for attempt in attempts if attempt.outcome_set_id == first.id)
            await db.commit()
            return (
                first.id,
                retried.id,
                first.expires_at,
                retried.expires_at,
                len(attempts),
                expired_attempt.status,
                expired_attempt.failure_code,
                expired_attempt.ended_at,
            )

    (
        old_id,
        new_id,
        old_expiry,
        new_expiry,
        attempt_count,
        expired_attempt_status,
        expired_attempt_failure_code,
        expired_attempt_ended_at,
    ) = asyncio.run(expire_then_retry())
    assert old_id != new_id
    assert old_expiry is not None and new_expiry is not None
    assert new_expiry > datetime.now(UTC)
    assert new_expiry > old_expiry
    assert attempt_count == 2
    assert expired_attempt_status == "expired"
    assert expired_attempt_failure_code == "summary_candidate_expired"
    assert expired_attempt_ended_at is not None


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
                template_version=1,
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
                template_version=1,
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
                template_version=1,
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
                template_version=1,
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
