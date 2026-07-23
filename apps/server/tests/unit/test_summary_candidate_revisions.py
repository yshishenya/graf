from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select

from tests.fixtures.cabinet import create_outcome_ready_meeting
from twobrain_rec_server.cabinet.egress import current_outcome_set
from twobrain_rec_server.db.models import Meeting, MeetingOutcomeSet, ProcessingResult
from twobrain_rec_server.outcomes.ai_service import (
    OutcomeGenerationTerminalError,
    create_summary_candidate,
    resolve_summary_candidate,
)


def test_candidate_request_is_idempotent_and_does_not_replace_accepted_notes(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            assert meeting is not None
            accepted_before = meeting.current_outcome_set_id
            first = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-auto-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=accepted_before,
            )
            second = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-auto-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=accepted_before,
            )
            await db.commit()
            return first.candidate_id, second.candidate_id, meeting.current_outcome_set_id

    first, second, accepted_after = asyncio.run(run())
    assert first == second
    assert accepted_after is None


def test_review_reads_the_accepted_pointer_instead_of_the_newest_outcome(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None
            assert result is not None
            accepted = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=result.media_revision_id,
                processing_result_id=result.id,
                status="available",
                generator_version="accepted-test-v1",
                revision_state="accepted",
            )
            db.add(accepted)
            await db.flush()
            meeting.current_outcome_set_id = accepted.id
            candidate = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=result.media_revision_id,
                processing_result_id=result.id,
                status="available",
                generator_version="newer-candidate-test-v1",
                revision_state="candidate",
            )
            db.add(candidate)
            await db.flush()
            selected = await current_outcome_set(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
            )
            return selected.id if selected is not None else None, accepted.id, candidate.id

    selected_id, accepted_id, candidate_id = asyncio.run(run())

    assert selected_id == accepted_id
    assert selected_id != candidate_id


def test_accept_candidate_is_atomic_and_rejects_stale_expected_revision(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            assert meeting is not None
            attempt = await create_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                requested_by_user_id=meeting.created_by_user_id,
                template_key="graf-auto-v1",
                template_id=None,
                template_version=1,
                expected_current_outcome_set_id=None,
            )
            candidate = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=attempt.media_revision_id,
                processing_result_id=attempt.source_result_id,
                status="available",
                generator_version=f"test:{attempt.candidate_id}",
                revision_state="candidate",
            )
            db.add(candidate)
            await db.flush()
            attempt.outcome_set_id = candidate.id
            attempt.status = "candidate"
            await resolve_summary_candidate(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                candidate_id=attempt.candidate_id,
                requested_by_user_id=meeting.created_by_user_id,
                accept=True,
                expected_current_outcome_set_id=None,
            )
            await db.commit()
            accepted_id = meeting.current_outcome_set_id
            accepted_state = candidate.revision_state
            accepted_actor = candidate.accepted_by_user_id
            with pytest.raises(OutcomeGenerationTerminalError, match="conflict"):
                await resolve_summary_candidate(
                    db,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    candidate_id=attempt.candidate_id,
                    requested_by_user_id=meeting.created_by_user_id,
                    accept=True,
                    expected_current_outcome_set_id=None,
                )
            await db.rollback()
            return accepted_id, accepted_state, accepted_actor

    accepted_id, state, actor = asyncio.run(run())
    assert accepted_id is not None
    assert state == "accepted"
    assert actor is not None
