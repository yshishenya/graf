from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from tests.fakes.auth_contexts import WORKSPACE_ID
from tests.integration.test_playback_normalization_backfill import _seed_legacy_revision
from twobrain_rec_server.db.models import PlaybackNormalizationJob
from twobrain_rec_server.normalization.pickup import enumerate_normalization_pickup_candidates
from twobrain_rec_server.normalization.service import inventory_playback_backfill_page


def test_pickup_is_bounded_and_prioritizes_new_then_due_retry_then_legacy(client) -> None:
    now = datetime(2026, 7, 14, 11, 0, tzinfo=UTC)

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            for ordinal in range(30):
                await _seed_legacy_revision(
                    db,
                    ordinal=2000 + ordinal,
                    created_at=now + timedelta(seconds=ordinal),
                )
            await inventory_playback_backfill_page(
                db,
                workspace_id=WORKSPACE_ID,
                page_size=100,
                now=now + timedelta(minutes=1),
            )
            jobs = list(
                await db.scalars(
                    select(PlaybackNormalizationJob).order_by(PlaybackNormalizationJob.created_at)
                )
            )
            new_job, due_job, future_job = jobs[:3]
            new_job.trigger_kind = "finalize"
            new_job.priority_class = "new_ingest"
            new_job.backfill_run_id = None
            due_job.trigger_kind = "reconcile"
            due_job.priority_class = "due_retry"
            due_job.backfill_run_id = None
            due_job.state = "retry_wait"
            due_job.reason_code = "storage_unavailable"
            due_job.next_attempt_at = now - timedelta(seconds=1)
            future_job.trigger_kind = "reconcile"
            future_job.priority_class = "due_retry"
            future_job.backfill_run_id = None
            future_job.state = "retry_wait"
            future_job.reason_code = "storage_unavailable"
            future_job.next_attempt_at = now + timedelta(hours=1)
            await db.commit()
            selected = await enumerate_normalization_pickup_candidates(
                db,
                now=now,
                batch_size=25,
            )
            return new_job.id, due_job.id, future_job.id, selected

    new_id, due_id, future_id, selected = asyncio.run(exercise())
    assert len(selected) == 25
    assert [candidate.job_id for candidate in selected[:2]] == [new_id, due_id]
    assert future_id not in {candidate.job_id for candidate in selected}


def test_inventory_and_dispatch_budget_guards_reject_unbounded_calls(client) -> None:
    now = datetime(2026, 7, 14, 11, 30, tzinfo=UTC)

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            with pytest.raises(ValueError, match="page_size"):
                await inventory_playback_backfill_page(
                    db,
                    workspace_id=WORKSPACE_ID,
                    page_size=101,
                    now=now,
                )
            with pytest.raises(ValueError, match="batch_size"):
                await enumerate_normalization_pickup_candidates(
                    db,
                    now=now,
                    batch_size=26,
                )

    asyncio.run(exercise())
