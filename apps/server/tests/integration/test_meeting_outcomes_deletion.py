from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text

from tests.contract.test_ingest_openapi_contract import auth_headers
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
from twobrain_rec_server.deletion.service import _purge_meeting_outcomes
from twobrain_rec_server.outcomes.ai_service import (
    OutcomeGenerationTerminalError,
    SummarySlotCASConflict,
    _cas_summary_slot,
    publish_model_generated_outcome,
)

BOUNDED_COPY = "Delete this meeting everywhere GRAF controls."


def test_deletion_report_accounts_for_stored_outcomes_without_content(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "outcome-deletion-report")
    asyncio.run(_seed_stored_outcomes(client, meeting_id))
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
    asyncio.run(_seed_stored_outcomes(client, meeting_id))
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
    asyncio.run(_seed_stored_outcomes(client, meeting_id, protocol=True))
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
    asyncio.run(_assert_protocol_purged(client, meeting_id))


def test_model_publication_stays_fail_closed_after_deletion_path_changes(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "outcome-deletion-publication-gate")
    asyncio.run(_seed_stored_outcomes(client, meeting_id))

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
                    settings=Settings(langfuse_project_id="synthetic-project"),
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


@pytest.mark.parametrize("revision_state", ["accepted", "candidate"])
def test_deletion_purges_protocol_and_header_repeatedly_without_touching_ledger(
    client, revision_state
) -> None:
    meeting_id = create_outcome_ready_meeting(client, "protocol-deletion")
    other_id = create_outcome_ready_meeting(client, "protocol-deletion-other")
    asyncio.run(_seed_stored_outcomes(client, meeting_id, protocol=True, revision_state=revision_state))
    asyncio.run(_seed_stored_outcomes(client, other_id, protocol=True))
    call_id = asyncio.run(_seed_generation_call(client, meeting_id))

    async def inspect_retained():
        async with client.app_state["sessionmaker"]() as db:
            call = await db.get(GenerationCall, call_id)
            assert call is not None
            other = await db.scalar(select(MeetingOutcomeSet).where(MeetingOutcomeSet.meeting_id == other_id))
            other_attempt = await db.scalar(select(MeetingOutcomeGenerationAttempt).where(
                MeetingOutcomeGenerationAttempt.meeting_id == other_id
            ))
            assert other is not None and other_attempt is not None
            assert other.protocol_json["topics"][0]["title"] == "Синтетический протокол"
            assert other.protocol_state == "available"
            assert other_attempt.header_snapshot_json == other.protocol_json["header"]
            return (
                {column.name: getattr(call, column.name) for column in GenerationCall.__table__.c},
                other.protocol_json, other.protocol_state, other.lifecycle_state,
                other_attempt.header_snapshot_json,
            )

    retained = asyncio.run(inspect_retained())
    for expected_status in (202, 404):
        response = client.post(
            f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
            headers=auth_headers(),
            json={"confirmation_boundary": BOUNDED_COPY},
        )
        # The public API hides an already-deleted meeting on a repeated request.
        assert response.status_code == expected_status
        asyncio.run(_assert_protocol_purged(client, meeting_id))
        assert asyncio.run(inspect_retained()) == retained
    # Exercise the purge itself again, not only the idempotent request path.
    async def repeat_purge():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            await _purge_meeting_outcomes(db, meeting=meeting)
            await db.commit()

    asyncio.run(repeat_purge())
    asyncio.run(_assert_protocol_purged(client, meeting_id))
    assert asyncio.run(inspect_retained()) == retained
    report = client.get(f"/api/v1/cabinet/meetings/{meeting_id}/deletion-report", headers=auth_headers())
    assert report.status_code == 200
    notes_row = next(row for row in report.json()["artifact_states"] if row["artifact_class"] == "notes_summary")
    assert notes_row["state"] == "purged"
    assert "Синтетический заголовок" not in report.text
    assert "Синтетический протокол" not in report.text


def test_deletion_accounts_for_header_snapshot_before_outcome_materializes(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "protocol-header-only-deletion")

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            assert result is not None
            attempt = MeetingOutcomeGenerationAttempt(
                workspace_id=result.workspace_id,
                meeting_id=meeting_id,
                processing_result_id=result.id,
                generator_version="synthetic-header-only",
                provider_kind="synthetic",
                status="generating",
                header_snapshot_json={"title": "Синтетический заголовок"},
            )
            db.add(attempt)
            await db.commit()
            return attempt.id

    attempt_id = asyncio.run(seed())
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert response.status_code == 202
    report = client.get(f"/api/v1/cabinet/meetings/{meeting_id}/deletion-report", headers=auth_headers())
    assert report.status_code == 200
    notes_row = next(row for row in report.json()["artifact_states"] if row["artifact_class"] == "notes_summary")
    assert notes_row["state"] == "purged"

    async def inspect():
        async with client.app_state["sessionmaker"]() as db:
            attempt = await db.get(MeetingOutcomeGenerationAttempt, attempt_id)
            assert attempt is not None
            assert attempt.header_snapshot_json is None
            assert attempt.status == "cancelled"
            assert attempt.failure_code == "meeting_deleted"

    asyncio.run(inspect())


async def _seed_stored_outcomes(client, meeting_id, *, protocol=False, revision_state="accepted"):
    """Seed stored artifacts directly; deletion must not depend on any generator."""
    async with client.app_state["sessionmaker"]() as db:
        meeting = await db.get(Meeting, meeting_id)
        result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
        assert meeting is not None and result is not None
        outcome = MeetingOutcomeSet(
            workspace_id=meeting.workspace_id,
            meeting_id=meeting_id,
            processing_result_id=result.id,
            generator_version="synthetic-deletion",
            source_kind="synthetic",
            generator_kind="synthetic",
            template_key="graf-auto-v1",
            template_version=1,
            status="available",
            revision_state=revision_state,
            content_hash="a" * 64,
        )
        db.add(outcome)
        await db.flush()
        attempt = MeetingOutcomeGenerationAttempt(
            workspace_id=meeting.workspace_id,
            meeting_id=meeting_id,
            processing_result_id=result.id,
            outcome_set_id=outcome.id,
            generator_version="synthetic-deletion",
            provider_kind="synthetic",
            candidate_id=uuid4(),
            metadata_json={"synthetic_private_metadata": "Синтетический заголовок"},
            prompt_definition=[{"role": "system", "content": "Synthetic prompt"}],
            prompt_config={"synthetic": True},
        )
        if protocol:
            header = {"title": "Синтетический заголовок", "participants": ["Участник 1"]}
            outcome.protocol_json = {
                "header": header,
                "topics": [{"title": "Синтетический протокол", "discussion": [{"text": "Тест"}]}],
            }
            outcome.protocol_schema_version = "synthetic.v2"
            outcome.protocol_state = "available"
            attempt.header_snapshot_json = header
        db.add_all([
            attempt,
            MeetingOutcomeItem(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting_id,
                outcome_set_id=outcome.id,
                category="summary",
                sequence=1,
                text="Синтетический исторический итог.",
                owner_text="Синтетический владелец",
                due_date_text="Не указан",
                source_refs_json=[{"sequence": 1}],
            ),
            MeetingSummarySlot(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting_id,
                template_key="graf-auto-v1",
                current_outcome_set_id=outcome.id if revision_state == "accepted" else None,
                current_binding_class="verified_complete" if revision_state == "accepted" else None,
            ),
        ])
        if revision_state == "accepted":
            meeting.current_outcome_set_id = outcome.id
        await db.commit()


async def _assert_protocol_purged(client, meeting_id):
    async with client.app_state["sessionmaker"]() as db:
        outcome = await db.scalar(select(MeetingOutcomeSet).where(MeetingOutcomeSet.meeting_id == meeting_id))
        attempt = await db.scalar(select(MeetingOutcomeGenerationAttempt).where(
            MeetingOutcomeGenerationAttempt.meeting_id == meeting_id
        ))
        assert outcome is not None and attempt is not None
        assert outcome.protocol_json is None
        assert outcome.protocol_state == "unavailable"
        assert outcome.lifecycle_state == "deleted"
        assert outcome.failure_reason == "meeting_deleted"
        assert outcome.content_hash is None
        assert attempt.header_snapshot_json is None
        assert attempt.status == "cancelled"
        assert attempt.failure_code == "meeting_deleted"
        assert attempt.metadata_json == {"purged_for_deletion": True}
        assert attempt.prompt_definition == [{"role": "system", "content": "Synthetic prompt"}]
        assert attempt.prompt_config == {"synthetic": True}
        assert await db.scalar(text(
            "select protocol_json is null from meeting_outcome_sets where id = :id"
        ), {"id": outcome.id})
        assert await db.scalar(text(
            "select header_snapshot_json is null from meeting_outcome_generation_attempts where id = :id"
        ), {"id": attempt.id})
    assert await _stored_outcome_content_count(client, meeting_id) == 0
    assert await _summary_slot_count(client, meeting_id) == 0


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
                request_json={"messages": [{"content": "Synthetic retained request"}]},
                transcript_text="Synthetic retained transcript",
                raw_response_json={"text": "Synthetic retained response"},
                validated_result_json={"protocol": {"header": {"title": "Synthetic retained title"}}},
                validated_result_hash="c" * 64,
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
