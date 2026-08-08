from __future__ import annotations

import asyncio
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from twobrain_rec_server.config import get_settings

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0017_meeting_detection_registry.py"
)
PUBLISH_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0019_publish_meeting_detection_registry.py"
)
EXPAND_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0030_expand_meeting_target_registry.py"
)


def _load_migration_module(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _alembic_config(database_url: str, monkeypatch) -> Config:
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(REPO_ROOT / "apps/server/alembic.ini"))
    config.set_main_option(
        "script_location",
        str(REPO_ROOT / "apps/server/src/twobrain_rec_server/db/migrations"),
    )
    return config


async def _migration_summary(
    database_url: str,
) -> tuple[set[str], set[str], set[str], tuple[str, str, str], int]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            tables, candidate_indexes, non_target_indexes = await connection.run_sync(
                lambda sync_connection: (
                    set(inspect(sync_connection).get_table_names()),
                    {
                        index["name"]
                        for index in inspect(sync_connection).get_indexes("meeting_detection_candidates")
                    },
                    {
                        index["name"]
                        for index in inspect(sync_connection).get_indexes("meeting_detection_non_target_rules")
                    },
                )
            )
            registry_row = tuple(
                (
                    await connection.execute(
                        text(
                            "select registry_version, status, source "
                            "from meeting_target_registry_versions where status = 'published'"
                        )
                    )
                ).one()
            )
            entry_count = int(
                (
                    await connection.execute(text("select count(*) from meeting_target_registry_entries"))
                ).scalar_one()
            )
    finally:
        await engine.dispose()
    return tables, candidate_indexes, non_target_indexes, registry_row, entry_count


async def _seed_previous_registry(database_url: str, previous_registry: dict[str, object]) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    insert into meeting_target_registry_versions (
                        id, registry_version, schema_version, status, source,
                        published_at, document_json, etag, created_at, updated_at
                    ) values (
                        :id, :registry_version, :schema_version, :status, :source,
                        :published_at, cast(:document_json as jsonb), :etag, :created_at, :updated_at
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "registry_version": previous_registry["registryVersion"],
                    "schema_version": previous_registry["schemaVersion"],
                    "status": "published",
                    "source": "admin",
                    "published_at": datetime(2026, 7, 8, tzinfo=UTC),
                    "document_json": json.dumps(previous_registry),
                    "etag": "previous-etag",
                    "created_at": datetime(2026, 7, 8, tzinfo=UTC),
                    "updated_at": datetime(2026, 7, 8, tzinfo=UTC),
                },
            )
    finally:
        await engine.dispose()


async def _registry_rows(database_url: str) -> list[tuple[str, str, str]]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "select registry_version, status, source "
                    "from meeting_target_registry_versions order by registry_version"
                )
            )
            return [tuple(row) for row in result]
    finally:
        await engine.dispose()


def test_meeting_detection_models_are_exported() -> None:
    from twobrain_rec_server import db
    from twobrain_rec_server.db import models

    assert hasattr(models, "MeetingTargetRegistryVersion")
    assert hasattr(models, "MeetingDetectionCandidate")
    assert hasattr(db.models, "MeetingDetectionTelemetryBatch")


def test_meeting_detection_migration_declares_all_required_tables_and_rls() -> None:
    migration = _load_migration_module(MIGRATION, "meeting_detection_registry_migration")

    assert migration.revision == "0017_meeting_detection"
    assert migration.down_revision == "0016_single_track_media_upload"
    assert set(migration.MEETING_DETECTION_TABLES) == {
        "meeting_target_registry_versions",
        "meeting_target_registry_entries",
        "meeting_detection_telemetry_batches",
        "meeting_detection_target_health_rollups",
        "meeting_detection_candidates",
        "meeting_detection_review_actions",
        "meeting_detection_non_target_rules",
        "meeting_detection_telemetry_rate_limit_buckets",
    }


def test_meeting_detection_publish_migration_uses_explicit_registry_data() -> None:
    migration = _load_migration_module(PUBLISH_MIGRATION, "meeting_detection_publish_registry_migration")

    assert migration.revision == "0019_publish_meeting_registry"
    assert migration.down_revision == "0018_mediascribe_result"
    assert migration.REGISTRY_DATA_PATH.exists()

    expansion = _load_migration_module(EXPAND_MIGRATION, "meeting_detection_expand_registry_migration")
    assert expansion.revision == "0030_expand_meeting_registry"
    assert expansion.down_revision == "0029_speaker_names"
    assert expansion.REGISTRY_DATA_PATH.exists()


def test_clean_postgres_database_migrates_meeting_detection_tables(
    postgres_clean_database_url: str,
    monkeypatch,
) -> None:
    alembic_config = _alembic_config(postgres_clean_database_url, monkeypatch)

    command.upgrade(alembic_config, "head")
    tables, candidate_indexes, non_target_indexes, registry_row, entry_count = asyncio.run(
        _migration_summary(postgres_clean_database_url)
    )
    get_settings.cache_clear()

    assert "meeting_target_registry_versions" in tables
    assert "meeting_detection_candidates" in tables
    assert "meeting_detection_telemetry_rate_limit_buckets" in tables
    assert "uq_meeting_detection_candidates_workspace_bundle" in candidate_indexes
    assert "uq_meeting_detection_non_target_rules_workspace_rule" in non_target_indexes
    assert registry_row == ("2026.07.21.1", "published", "migration")
    assert entry_count == 116


def test_publish_registry_migration_downgrade_restores_previous_published_registry(
    postgres_clean_database_url: str,
    monkeypatch,
) -> None:
    alembic_config = _alembic_config(postgres_clean_database_url, monkeypatch)
    previous_registry: dict[str, object] = {
        "schemaVersion": 1,
        "registryVersion": "2026.07.08.99",
        "generatedAt": "2026-07-08T00:00:00Z",
        "targets": [],
    }

    command.upgrade(alembic_config, "0017_meeting_detection")
    asyncio.run(_seed_previous_registry(postgres_clean_database_url, previous_registry))

    command.upgrade(alembic_config, "head")
    upgraded_rows = asyncio.run(_registry_rows(postgres_clean_database_url))

    command.downgrade(alembic_config, "0018_mediascribe_result")
    downgraded_rows = asyncio.run(_registry_rows(postgres_clean_database_url))
    get_settings.cache_clear()

    assert ("2026.07.08.99", "superseded", "admin") in upgraded_rows
    assert ("2026.07.09.4", "superseded", "migration") in upgraded_rows
    assert ("2026.07.21.1", "published", "migration") in upgraded_rows
    assert downgraded_rows == [("2026.07.08.99", "published", "admin")]
