from __future__ import annotations

import asyncio
import inspect
from uuid import UUID

import pytest
import twobrain_rec_server.outcomes.ai_service as ai_service
from sqlalchemy import select
from twobrain_rec_server.db.models import (
    DispatchIntent,
    Meeting,
    MeetingOutcomeSet,
    MeetingSummarySlot,
    ProcessingResult,
)
from twobrain_rec_server.outcomes.ai_service import (
    OutcomeGenerationTerminalError,
    _cas_summary_slot,
    publish_model_generated_outcome,
)
from twobrain_rec_server.outcomes.service import ensure_summary_slot

from tests.fixtures.cabinet import create_outcome_ready_meeting


def test_model_publication_entry_point_is_fail_closed_without_feature_195_proof() -> None:
    async def run() -> None:
        with pytest.raises(OutcomeGenerationTerminalError, match="verified_runtime_unavailable"):
            await publish_model_generated_outcome(
                None,
                workspace_id=UUID("00000000-0000-0000-0000-000000000001"),
                meeting_id=UUID("00000000-0000-0000-0000-000000000002"),
                candidate_id=UUID("00000000-0000-0000-0000-000000000003"),
                expected_current_outcome_set_id=None,
            )

    asyncio.run(run())


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
