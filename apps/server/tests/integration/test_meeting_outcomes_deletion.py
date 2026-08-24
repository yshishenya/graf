from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import create_outcome_ready_meeting
from twobrain_rec_server.db.models import (
    GenerationCall,
    Meeting,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    MeetingSummarySlot,
)
from twobrain_rec_server.outcomes.ai_service import (
    OutcomeGenerationTerminalError,
    SummarySlotCASConflict,
    _cas_summary_slot,
    publish_model_generated_outcome,
)
from twobrain_rec_server.outcomes.service import ensure_outcomes_for_meeting

BOUNDED_COPY = "Delete this meeting everywhere GRAF controls."


def test_deletion_report_accounts_for_stored_outcomes_without_content(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "outcome-deletion-report")
    asyncio.run(ensure_outcomes_for_meeting(client.app_state["sessionmaker"], meeting_id=meeting_id))
    outcome_text = asyncio.run(_first_outcome_text(client, meeting_id))
    assert outcome_text

    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    report = client.get(f"/api/v1/cabinet/meetings/{meeting_id}/deletion-report", headers=auth_headers())
    lifecycle_state = asyncio.run(_outcome_lifecycle_state(client, meeting_id))
    content_count = asyncio.run(_stored_outcome_content_count(client, meeting_id))
    slot_count = asyncio.run(_summary_slot_count(client, meeting_id))

    assert delete_response.status_code == 202
    assert report.status_code == 200
    notes_row = next(row for row in report.json()["artifact_states"] if row["artifact_class"] == "notes_summary")
    assert notes_row["control_scope"] == "controlled"
    assert notes_row["state"] == "purged"
    assert lifecycle_state == "deleted"
    assert content_count == 0
    assert slot_count == 0
    assert outcome_text not in report.text
    assert "source_refs_json" not in report.text


def test_deletion_purges_summary_slots_but_retains_generation_call_ledger(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "outcome-deletion-retained-call")
    asyncio.run(ensure_outcomes_for_meeting(client.app_state["sessionmaker"], meeting_id=meeting_id))
    call_id = asyncio.run(_seed_generation_call(client, meeting_id))

    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    report = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-report",
        headers=auth_headers(),
    )
    slot_count, retained_call_count = asyncio.run(
        _slot_and_generation_call_counts(client, meeting_id, call_id)
    )

    assert delete_response.status_code == 202
    assert report.status_code == 200
    notes_row = next(
        row for row in report.json()["artifact_states"] if row["artifact_class"] == "notes_summary"
    )
    assert notes_row["state"] == "purged"
    assert slot_count == 0
    assert retained_call_count == 1


def test_delete_fence_rejects_late_slot_cas_without_republishing(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "outcome-deletion-cas-fence")
    asyncio.run(ensure_outcomes_for_meeting(client.app_state["sessionmaker"], meeting_id=meeting_id))
    expected_epoch, expected_current = asyncio.run(_slot_cas_identity(client, meeting_id))

    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )

    async def run() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            with pytest.raises(SummarySlotCASConflict, match="summary_slot_conflict"):
                await _cas_summary_slot(
                    db,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    template_key="graf-auto-v1",
                    replacement_outcome_set_id=uuid4(),
                    expected_current_outcome_set_id=expected_current,
                    expected_source_fingerprint="opaque-test-source",
                    expected_deletion_epoch=expected_epoch,
                )
            assert (
                await db.scalar(
                    select(MeetingSummarySlot.id).where(MeetingSummarySlot.meeting_id == meeting_id)
                )
                is None
            )
            await db.rollback()

    assert delete_response.status_code == 202
    asyncio.run(run())


def test_model_publication_stays_fail_closed_after_deletion_path_changes(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "outcome-deletion-publication-gate")
    asyncio.run(ensure_outcomes_for_meeting(client.app_state["sessionmaker"], meeting_id=meeting_id))

    async def run() -> tuple[object, object]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            before = (
                meeting.current_outcome_set_id,
                await db.scalar(
                    select(MeetingSummarySlot.current_outcome_set_id).where(
                        MeetingSummarySlot.meeting_id == meeting_id,
                        MeetingSummarySlot.template_key == "graf-auto-v1",
                    )
                ),
            )
            with pytest.raises(
                OutcomeGenerationTerminalError,
                match="summary_publication_proof_invalid",
            ):
                await publish_model_generated_outcome(
                    db,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    candidate_id=uuid4(),
                    expected_current_outcome_set_id=before[1],
                    publication_proof={"canonical_artifact": "missing"},
                )
            after = (
                meeting.current_outcome_set_id,
                await db.scalar(
                    select(MeetingSummarySlot.current_outcome_set_id).where(
                        MeetingSummarySlot.meeting_id == meeting_id,
                        MeetingSummarySlot.template_key == "graf-auto-v1",
                    )
                ),
            )
            await db.rollback()
            return before, after

    before, after = asyncio.run(run())
    assert before == after


async def _first_outcome_text(client, meeting_id) -> str:
    async with client.app_state["sessionmaker"]() as db:
        text = await db.scalar(
            select(MeetingOutcomeItem.text)
            .where(MeetingOutcomeItem.meeting_id == meeting_id)
            .where(MeetingOutcomeItem.text.is_not(None))
            .order_by(MeetingOutcomeItem.category, MeetingOutcomeItem.sequence)
        )
        assert text is not None
        return text


async def _outcome_lifecycle_state(client, meeting_id) -> str:
    async with client.app_state["sessionmaker"]() as db:
        state = await db.scalar(
            select(MeetingOutcomeSet.lifecycle_state).where(MeetingOutcomeSet.meeting_id == meeting_id)
        )
        assert state is not None
        return state


async def _stored_outcome_content_count(client, meeting_id) -> int:
    async with client.app_state["sessionmaker"]() as db:
        items = (
            await db.scalars(select(MeetingOutcomeItem).where(MeetingOutcomeItem.meeting_id == meeting_id))
        ).all()
        return sum(1 for item in items if item.text or item.owner_text or item.due_date_text or item.source_refs_json)


async def _summary_slot_count(client, meeting_id) -> int:
    async with client.app_state["sessionmaker"]() as db:
        return int(
            await db.scalar(
                select(func.count(MeetingSummarySlot.id)).where(
                    MeetingSummarySlot.meeting_id == meeting_id
                )
            )
        )


async def _seed_generation_call(client, meeting_id):
    async with client.app_state["sessionmaker"]() as db:
        meeting = await db.get(Meeting, meeting_id)
        assert meeting is not None
        call_id = uuid4()
        now = datetime.now(UTC)
        db.add(
            MeetingSummarySlot(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                template_key="opaque-empty-type",
            )
        )
        db.add(
            GenerationCall(
                id=call_id,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                candidate_id=uuid4(),
                provider_attempt=1,
                call_sequence=1,
                trace_id="a" * 32,
                observation_id="b" * 32,
                call_state="completed",
                started_at=now,
                completed_at=now,
                export_status="pending",
            )
        )
        await db.commit()
        return call_id


async def _slot_and_generation_call_counts(client, meeting_id, call_id) -> tuple[int, int]:
    async with client.app_state["sessionmaker"]() as db:
        slot_count = int(
            await db.scalar(
                select(func.count(MeetingSummarySlot.id)).where(
                    MeetingSummarySlot.meeting_id == meeting_id
                )
            )
        )
        call_count = int(
            await db.scalar(
                select(func.count(GenerationCall.id)).where(GenerationCall.id == call_id)
            )
        )
        return slot_count, call_count


async def _slot_cas_identity(client, meeting_id):
    async with client.app_state["sessionmaker"]() as db:
        meeting = await db.get(Meeting, meeting_id)
        assert meeting is not None
        current = await db.scalar(
            select(MeetingSummarySlot.current_outcome_set_id).where(
                MeetingSummarySlot.meeting_id == meeting_id,
                MeetingSummarySlot.template_key == "graf-auto-v1",
            )
        )
        return meeting.deletion_epoch, current
