from __future__ import annotations

import asyncio
import importlib

from sqlalchemy import select

from tests.fixtures.cabinet import create_outcome_ready_meeting
from twobrain_rec_server.db.models import (
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    ProcessingResult,
)
from twobrain_rec_server.domain.statuses import ProcessingAvailabilityStatus


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
    assert attempt_status == "failed_retryable"
    assert "synthetic generator failure" not in str(metadata)
