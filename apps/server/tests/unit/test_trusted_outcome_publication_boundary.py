from __future__ import annotations

import asyncio
import inspect
import json
from datetime import UTC, datetime
from hashlib import sha256
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
from twobrain_rec_server.outcomes.service import ensure_summary_slot


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


def test_completed_validated_call_publishes_only_its_target_slot(client) -> None:
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
            request = {"messages": []}
            transcript = "fixture transcript"
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
    assert slot_id is not None
    assert attempt_status == "accepted"
    assert revision_state == "accepted"
    assert legacy_pointer is None


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
