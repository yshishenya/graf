from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

from sqlalchemy import select, text

from tests.fixtures.cabinet import create_outcome_ready_meeting
from twobrain_rec_server.db.models import Meeting, MeetingOutcomeSet, ProcessingResult

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0032_backfill_current_outcome_set.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("current_outcome_set_backfill", MIGRATION)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backfill_is_additive_pointer_safe_and_downgrade_is_data_preserving() -> None:
    assert MIGRATION.exists()
    migration = _load_migration()
    source = MIGRATION.read_text(encoding="utf-8")

    assert migration.revision == "0032_outcome_pointer"
    assert migration.down_revision == "0031_recording_workflows"
    assert "current_outcome_set_id IS NULL" in source
    assert "lifecycle_state = 'active'" in source
    assert "status IN ('available', 'partial')" in source
    assert "meeting.deleted_at IS NULL" in source
    assert "COALESCE(meeting.deletion_state, 'none') = 'none'" in source
    assert "revision_state = 'accepted'" in source
    assert "generator_version = 'outcomes-extractive-v1'" in source
    assert "ROW_NUMBER() OVER" in source
    assert "PARTITION BY outcome.workspace_id, outcome.meeting_id" in source
    assert "def downgrade()" in source
    assert "pass" in source


def test_backfill_executes_twice_and_preserves_legacy_template_provenance(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)
    migration = _load_migration()

    async def seed_legacy_outcome():
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert result is not None
            outcome_set = MeetingOutcomeSet(
                workspace_id=result.workspace_id,
                meeting_id=meeting_id,
                media_revision_id=result.media_revision_id,
                processing_result_id=result.id,
                status="available",
                generator_version="outcomes-extractive-v1",
                lifecycle_state="active",
                generated_at=datetime.now(UTC),
            )
            db.add(outcome_set)
            await db.commit()
            return outcome_set.id

    outcome_set_id = client.portal.call(seed_legacy_outcome)

    async def backfill_twice():
        async with client.app_state["sessionmaker"]() as db:
            await db.execute(text(migration.BACKFILL_SQL))
            await db.execute(text(migration.BACKFILL_SQL))
            await db.commit()
            meeting = await db.get(Meeting, meeting_id)
            outcome_set = await db.get(MeetingOutcomeSet, outcome_set_id)
            assert meeting is not None
            assert outcome_set is not None
            return meeting, outcome_set

    meeting, outcome_set = client.portal.call(backfill_twice)

    assert meeting.current_outcome_set_id == outcome_set_id
    assert outcome_set.revision_state == "accepted"
    assert outcome_set.accepted_at is not None
    assert outcome_set.template_key is None
    assert outcome_set.template_version is None
