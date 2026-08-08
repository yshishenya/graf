from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import WORKSPACE_ID
from tests.integration.test_playback_normalization_backfill import _seed_legacy_revision
from twobrain_rec_server.db.models import PlaybackNormalizationJob
from twobrain_rec_server.normalization.service import inventory_playback_backfill_page


def test_admin_metrics_expose_only_aggregate_backfill_backlog_age_and_reasons(client) -> None:
    now = datetime(2026, 7, 14, 13, 0, tzinfo=UTC)

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            recoverable = await _seed_legacy_revision(db, ordinal=5000, created_at=now)
            terminal = await _seed_legacy_revision(
                db,
                ordinal=5001,
                created_at=now + timedelta(seconds=1),
                source_state="missing",
            )
            await inventory_playback_backfill_page(
                db,
                workspace_id=WORKSPACE_ID,
                page_size=100,
                now=now + timedelta(minutes=1),
            )
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.media_revision_id == recoverable.media_revision_id
                )
            )
            assert job is not None
            job.state = "retry_wait"
            job.reason_code = "storage_unavailable"
            job.next_attempt_at = now + timedelta(hours=1)
            await db.commit()
            return recoverable, terminal

    recoverable, terminal = asyncio.run(seed())
    response = client.get("/api/v1/admin/metrics", headers=auth_headers())
    assert response.status_code == 200
    payload = response.json()
    summary = payload["playback_normalization"]
    assert set(summary) == {
        "run_states",
        "job_states",
        "reason_counts",
        "backlog_total",
        "oldest_backlog_age_seconds",
        "retry_cycle_buckets",
        "cleanup_pending_count",
        "purge_journal_terminal_unknown_count",
        "purge_journal_terminal_unknown_orphan_count",
        "last_safe_heartbeat_at",
        "backfill_progress",
    }
    assert summary["run_states"] == {"dispatching": 1}
    assert summary["job_states"] == {"retry_wait": 1, "terminal": 1}
    assert summary["reason_counts"] == {
        "source_missing": 1,
        "storage_unavailable": 1,
    }
    assert summary["backlog_total"] == 1
    assert isinstance(summary["oldest_backlog_age_seconds"], int)
    assert summary["oldest_backlog_age_seconds"] >= 0
    assert summary["retry_cycle_buckets"] == {"0": 2, "1": 0, "2": 0, "3_plus": 0}
    assert summary["cleanup_pending_count"] == 0
    assert summary["purge_journal_terminal_unknown_count"] == 0
    assert summary["purge_journal_terminal_unknown_orphan_count"] == 0
    assert summary["last_safe_heartbeat_at"] is None
    assert set(summary["backfill_progress"]) == {
        "evaluated",
        "preserve_valid",
        "validate_candidate",
        "normalize_source",
        "unavailable_source",
        "ready",
        "terminal",
        "cancelled",
    }
    assert all(isinstance(value, int) for value in summary["backfill_progress"].values())
    body = response.text
    assert str(recoverable.meeting_id) not in body
    assert str(terminal.meeting_id) not in body
    assert recoverable.title not in body
    assert terminal.title not in body
    for forbidden in (
        "storage_object_key",
        "local_recording_id",
        "local_media_revision_id",
        "transcript",
        "summary_text",
        "retry_action",
        "backfill_action",
    ):
        assert forbidden not in body


def test_metrics_view_model_keeps_aggregate_normalization_summary() -> None:
    from twobrain_rec_server.admin.view_models import build_metrics_view

    summary = {
        "run_states": {"complete": 2},
        "job_states": {"ready": 4},
        "reason_counts": {},
        "backlog_total": 0,
        "oldest_backlog_age_seconds": 0,
        "retry_cycle_buckets": {"0": 4, "1": 0, "2": 0, "3_plus": 0},
        "cleanup_pending_count": 0,
        "purge_journal_terminal_unknown_count": 0,
        "purge_journal_terminal_unknown_orphan_count": 0,
        "last_safe_heartbeat_at": None,
        "backfill_progress": {
            "evaluated": 4,
            "preserve_valid": 0,
            "validate_candidate": 0,
            "normalize_source": 4,
            "unavailable_source": 0,
            "ready": 4,
            "terminal": 0,
            "cancelled": 0,
        },
    }
    view = build_metrics_view(
        workspace_name="Workspace",
        actor_role="owner",
        metrics={"metrics": [], "playback_normalization": summary},
    )
    assert view.playback_normalization == summary
