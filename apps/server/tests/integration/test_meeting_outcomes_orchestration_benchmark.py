from __future__ import annotations

import asyncio
import importlib
from datetime import UTC, datetime
from decimal import Decimal
from time import perf_counter

from sqlalchemy import delete, func, select

from tests.fixtures.cabinet import create_outcome_ready_meeting
from twobrain_rec_server.db.models import (
    Meeting,
    MeetingOutcomeItem,
    ProcessingResult,
    TranscriptSegment,
)


def _service_module():
    try:
        return importlib.import_module("twobrain_rec_server.outcomes.service")
    except ModuleNotFoundError as exc:
        raise AssertionError("outcome service module is missing") from exc


def test_one_hour_outcome_generation_does_not_block_review_budget(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    service = _service_module()

    async def seed_one_hour_transcript() -> ProcessingResult:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            meeting.duration_seconds = 3600
            meeting.ended_at = datetime(2026, 6, 16, 9, 0, tzinfo=UTC)
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            assert result is not None
            await db.execute(delete(TranscriptSegment).where(TranscriptSegment.processing_result_id == result.id))
            for sequence in range(360):
                start = Decimal(sequence * 10)
                end = Decimal((sequence + 1) * 10)
                db.add(
                    TranscriptSegment(
                        processing_result_id=result.id,
                        workspace_id=result.workspace_id,
                        meeting_id=result.meeting_id,
                        sequence=sequence,
                        start_seconds=start,
                        end_seconds=end,
                        text=f"Синтетический фрагмент {sequence}: обсудили тему и следующие шаги.",
                        source_role="mic" if sequence % 2 == 0 else "incoming",
                        source_role_original="microphone" if sequence % 2 == 0 else "system",
                    )
                )
            result.segment_count = 360
            await db.commit()
            return result

    result = asyncio.run(seed_one_hour_transcript())
    started = perf_counter()

    async def generate() -> tuple[str, int]:
        async with client.app_state["sessionmaker"]() as db:
            fresh_result = await db.get(ProcessingResult, result.id)
            assert fresh_result is not None
            outcome_set = await service.ensure_outcomes_for_processing_result(db, result=fresh_result)
            item_count = await db.scalar(
                select(func.count(MeetingOutcomeItem.id)).where(MeetingOutcomeItem.outcome_set_id == outcome_set.id)
            )
            await db.commit()
            return outcome_set.status, int(item_count or 0)

    status, item_count = asyncio.run(generate())
    elapsed_seconds = perf_counter() - started

    assert elapsed_seconds < 30
    assert status == "available"
    assert item_count > 0
