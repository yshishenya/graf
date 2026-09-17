"""Exercise deletion evidence preservation on a real, disposable PostgreSQL database."""

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.integration.test_postgres_migrations import (
    DEVICE_ID,
    USER_ID,
    WORKSPACE_ID,
    _seed_identity,
)
from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.models import LocalPurgeTask, Meeting, MeetingDeletionRequest

PREVIOUS = "0091_comment_reader_projection"
CURRENT = "0092_recording_origin_cancel"


@pytest.fixture
def migration_database(postgres_clean_database_url, monkeypatch):
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", postgres_clean_database_url)
    get_settings.cache_clear()
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "src/twobrain_rec_server/db/migrations"))
    command.upgrade(config, PREVIOUS)
    try:
        yield config, postgres_clean_database_url
    finally:
        get_settings.cache_clear()


async def _seed_evidence(database_url, *, duplicate=False):
    engine = create_async_engine(database_url)
    try:
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        await _seed_identity(sessions)
        now = datetime.now(UTC)
        async with sessions() as db:
            meeting = Meeting(
                workspace_id=WORKSPACE_ID,
                created_by_user_id=USER_ID,
                device_id=DEVICE_ID,
                local_recording_id="synthetic-migration-origin",
                duration_seconds=1,
                deletion_state="deleting",
                deletion_epoch=1,
                deletion_requested_at=now,
            )
            db.add(meeting)
            await db.flush()
            request = MeetingDeletionRequest(
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting.id,
                requested_by_user_id=USER_ID,
                requested_by_device_id=DEVICE_ID,
                request_source="owner",
                reason_code="user_request",
                confirmation_boundary="graf_controlled_storage",
                state="deleting",
                accepted_at=now,
                metadata_json={"synthetic": True},
            )
            db.add(request)
            await db.flush()
            for state in (["pending", "acknowledged"] if duplicate else ["acknowledged"]):
                db.add(LocalPurgeTask(
                    workspace_id=WORKSPACE_ID,
                    meeting_id=meeting.id,
                    deletion_request_id=request.id,
                    device_id=DEVICE_ID,
                    task_type="purge_local_buffers",
                    state=state,
                    acknowledged_at=now if state == "acknowledged" else None,
                    expires_at=now + timedelta(days=7),
                    metadata_json={"synthetic": True, "verified": state == "acknowledged"},
                ))
            await db.commit()
    finally:
        await engine.dispose()


def _query(database_url, sql, parameters=None):
    async def execute():
        engine = create_async_engine(database_url)
        try:
            async with engine.begin() as connection:
                result = await connection.execute(text(sql), parameters or {})
                return result.fetchall() if result.returns_rows else None
        finally:
            await engine.dispose()

    return asyncio.run(execute())


def _evidence(database_url):
    # Compare every persisted column, including receipt timestamps and verification data.
    return {
        table: _query(database_url, f"SELECT to_jsonb(evidence) FROM {table} evidence ORDER BY id")
        for table in ("meetings", "meeting_deletion_requests", "local_purge_tasks")
    }


def test_upgrade_preserves_existing_deletion_evidence_and_enforces_unique_tasks(migration_database):
    config, database_url = migration_database
    asyncio.run(_seed_evidence(database_url))
    before = _evidence(database_url)

    command.upgrade(config, CURRENT)

    assert _query(database_url, "SELECT version_num FROM alembic_version") == [(CURRENT,)]
    assert _evidence(database_url) == before
    assert _query(database_url, "SELECT count(*) FROM recording_origin_cancellations") == [(0,)]
    with pytest.raises(IntegrityError, match="uq_local_purge_request_device_type"):
        _query(database_url, """
            INSERT INTO local_purge_tasks
                (id, workspace_id, meeting_id, deletion_request_id, device_id,
                 task_type, state, metadata_json, expires_at)
            SELECT :id, workspace_id, meeting_id, deletion_request_id, device_id,
                   task_type, state, metadata_json, expires_at FROM local_purge_tasks
        """, {"id": uuid4()})
    assert _evidence(database_url) == before


def test_duplicate_preflight_preserves_all_evidence_and_previous_schema(migration_database):
    config, database_url = migration_database
    asyncio.run(_seed_evidence(database_url, duplicate=True))
    before = _evidence(database_url)
    assert len(before["local_purge_tasks"]) == 2

    with pytest.raises(RuntimeError, match="Duplicate local purge tasks require reviewed reconciliation"):
        command.upgrade(config, CURRENT)

    assert _query(database_url, "SELECT version_num FROM alembic_version") == [(PREVIOUS,)]
    assert _evidence(database_url) == before
    assert _query(database_url, "SELECT to_regclass('recording_origin_cancellations')") == [(None,)]
    assert _query(database_url, """
        SELECT count(*) FROM pg_constraint
        WHERE conrelid = 'local_purge_tasks'::regclass
          AND conname = 'uq_local_purge_request_device_type'
    """) == [(0,)]


def test_downgrade_refuses_to_erase_cancellation_markers(migration_database):
    config, database_url = migration_database
    asyncio.run(_seed_evidence(database_url))
    before = _evidence(database_url)
    command.upgrade(config, CURRENT)
    _query(database_url, """
        INSERT INTO recording_origin_cancellations
            (id, workspace_id, created_by_user_id, local_recording_id)
        VALUES (:id, :workspace, :actor, 'synthetic-cancelled-origin')
    """, {"id": uuid4(), "workspace": WORKSPACE_ID, "actor": USER_ID})
    marker = _query(database_url, "SELECT to_jsonb(marker) FROM recording_origin_cancellations marker")
    assert len(marker) == 1

    with pytest.raises(RuntimeError, match="Origin cancellation markers must be retained"):
        command.downgrade(config, PREVIOUS)

    assert _query(database_url, "SELECT version_num FROM alembic_version") == [(CURRENT,)]
    assert _query(database_url, "SELECT to_jsonb(marker) FROM recording_origin_cancellations marker") == marker
    assert _evidence(database_url) == before
