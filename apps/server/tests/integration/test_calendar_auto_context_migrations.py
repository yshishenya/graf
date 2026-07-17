from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from types import ModuleType
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from twobrain_rec_server.config import get_settings

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0021_calendar_auto_context_match.py"
)


def _load_migration_module(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _alembic_config(database_url: str, monkeypatch: pytest.MonkeyPatch) -> Config:
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(REPO_ROOT / "apps/server/alembic.ini"))
    config.set_main_option(
        "script_location",
        str(REPO_ROOT / "apps/server/src/twobrain_rec_server/db/migrations"),
    )
    return config


async def _seed_legacy_rows(database_url: str) -> dict[str, UUID]:
    ids = {
        name: uuid4()
        for name in ("organization", "workspace", "user", "device", "meeting")
    }
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("insert into organizations (id, slug, name) values (:id, 'calendar-auto-match', 'Calendar Auto Match')"),
                {"id": ids["organization"]},
            )
            await connection.execute(
                text("""
                    insert into workspaces (id, organization_id, slug, name)
                    values (:id, :organization_id, 'calendar-auto-match', 'Calendar Auto Match')
                """),
                {"id": ids["workspace"], "organization_id": ids["organization"]},
            )
            await connection.execute(
                text("""
                    insert into user_identities (id, organization_id, external_subject, display_name)
                    values (:id, :organization_id, 'calendar-auto-match@example.test', 'Synthetic Owner')
                """),
                {"id": ids["user"], "organization_id": ids["organization"]},
            )
            await connection.execute(
                text("""
                    insert into registered_devices
                        (id, workspace_id, user_id, device_public_id, status, registration_state)
                    values (:id, :workspace_id, :user_id, 'calendar-auto-match-device', 'active', 'approved')
                """),
                {"id": ids["device"], "workspace_id": ids["workspace"], "user_id": ids["user"]},
            )
            await connection.execute(
                text("""
                    insert into meetings
                        (id, workspace_id, created_by_user_id, device_id, local_recording_id, title,
                         duration_seconds, status)
                    values (:id, :workspace_id, :user_id, :device_id, 'calendar-auto-match',
                            'Legacy title', 60, 'ready')
                """),
                {
                    "id": ids["meeting"],
                    "workspace_id": ids["workspace"],
                    "user_id": ids["user"],
                    "device_id": ids["device"],
                },
            )
    finally:
        await engine.dispose()
    return ids


async def _upgrade_summary(database_url: str, ids: dict[str, UUID]) -> tuple[set[str], set[str], str]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            tables, meeting_columns = await connection.run_sync(
                lambda sync_connection: (
                    set(inspect(sync_connection).get_table_names()),
                    {column["name"] for column in inspect(sync_connection).get_columns("meetings")},
                )
            )
            title_source = await connection.scalar(
                text("select title_source from meetings where id = :meeting_id"),
                {"meeting_id": ids["meeting"]},
            )
    finally:
        await engine.dispose()
    assert isinstance(title_source, str)
    return tables, meeting_columns, title_source


async def _duplicate_attempt_is_rejected(database_url: str, ids: dict[str, UUID]) -> None:
    values = {
        "workspace_id": ids["workspace"],
        "owner_user_id": ids["user"],
        "device_id": ids["device"],
        "local_recording_id": "duplicate-calendar-recording",
        "idempotency_key_sha256": "a" * 64,
        "request_fingerprint_sha256": "b" * 64,
    }
    statement = text("""
        insert into recording_calendar_match_attempts
            (id, workspace_id, owner_user_id, device_id, local_recording_id,
             idempotency_key_sha256, request_fingerprint_sha256, recording_started_at,
             decision_intent, attempt_state, context_confidence, candidate_event_ids_json,
             candidate_count, matched_title_state, matched_roster_json, matched_roster_state,
             matched_roster_count, freshness_class, matcher_version, evaluated_at, expires_at)
        values
            (:id, :workspace_id, :owner_user_id, :device_id, :local_recording_id,
             :idempotency_key_sha256, :request_fingerprint_sha256,
             '2026-07-13 12:00:00+00:00', 'automatic', 'no_context', 'none',
             '[]'::jsonb, 0, 'unavailable', '[]'::jsonb, 'not_available', 0,
             'current', 'calendar_auto_match_v1', '2026-07-13 12:00:00+00:00',
             '2026-07-14 12:00:00+00:00')
    """)
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(statement, {**values, "id": uuid4()})
        with pytest.raises(IntegrityError):
            async with engine.begin() as connection:
                await connection.execute(statement, {**values, "id": uuid4()})
    finally:
        await engine.dispose()


def test_calendar_auto_context_models_are_exported() -> None:
    from twobrain_rec_server import db
    from twobrain_rec_server.db import models

    assert hasattr(models, "RecordingCalendarMatchAttempt")
    assert hasattr(db.models, "RecordingCalendarMatchAttempt")
    assert hasattr(models.Meeting, "title_source")
    assert hasattr(models.Meeting, "title_updated_at")
    assert hasattr(models.Meeting, "create_request_fingerprint_sha256")


def test_calendar_auto_context_migration_declares_revision_and_rls_boundary() -> None:
    assert MIGRATION.exists()
    migration = _load_migration_module(MIGRATION, "calendar_auto_context_match_migration")

    assert migration.revision == "0021_calendar_auto_context_match"
    assert migration.down_revision == "0020_user_scoped_recording_ids"
    assert "recording_calendar_match_attempts" in migration.CALENDAR_AUTO_CONTEXT_TABLES


def test_postgres_upgrade_backfills_title_provenance_and_enforces_attempt_identity(
    postgres_clean_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _alembic_config(postgres_clean_database_url, monkeypatch)
    command.upgrade(config, "0020_user_scoped_recording_ids")
    ids = asyncio.run(_seed_legacy_rows(postgres_clean_database_url))
    command.upgrade(config, "head")

    tables, meeting_columns, title_source = asyncio.run(
        _upgrade_summary(postgres_clean_database_url, ids)
    )
    asyncio.run(_duplicate_attempt_is_rejected(postgres_clean_database_url, ids))
    get_settings.cache_clear()

    assert "recording_calendar_match_attempts" in tables
    assert {"title_source", "title_updated_at", "create_request_fingerprint_sha256"} <= meeting_columns
    assert title_source == "legacy_unknown"


def test_postgres_downgrade_restores_pre_calendar_auto_context_schema(
    postgres_clean_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _alembic_config(postgres_clean_database_url, monkeypatch)
    command.upgrade(config, "head")
    command.downgrade(config, "0020_user_scoped_recording_ids")

    async def summary() -> tuple[set[str], set[str]]:
        engine = create_async_engine(postgres_clean_database_url)
        try:
            async with engine.connect() as connection:
                return await connection.run_sync(
                    lambda sync_connection: (
                        set(inspect(sync_connection).get_table_names()),
                        {column["name"] for column in inspect(sync_connection).get_columns("meetings")},
                    )
                )
        finally:
            await engine.dispose()

    tables, meeting_columns = asyncio.run(summary())
    get_settings.cache_clear()

    assert "recording_calendar_match_attempts" not in tables
    assert "title_source" not in meeting_columns
