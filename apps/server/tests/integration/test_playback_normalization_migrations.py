from __future__ import annotations

import asyncio
import importlib.util
from datetime import UTC, datetime
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
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0022_playback_normalization.py"
)
PROFILE = "review_m4a_aac_lc_48k_mono_64k_v1"


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("playback_normalization_migration", MIGRATION)
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


async def _seed_legacy_playback_rows(database_url: str) -> dict[str, UUID]:
    ids = {
        name: uuid4()
        for name in ("organization", "workspace", "user", "device", "meeting", "revision")
    }
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("insert into organizations (id, slug, name) values (:id, 'normalization', 'Normalization')"),
                {"id": ids["organization"]},
            )
            await connection.execute(
                text("""
                    insert into workspaces (id, organization_id, slug, name)
                    values (:id, :organization_id, 'normalization', 'Normalization')
                """),
                {"id": ids["workspace"], "organization_id": ids["organization"]},
            )
            await connection.execute(
                text("""
                    insert into user_identities (id, organization_id, external_subject)
                    values (:id, :organization_id, 'normalization@example.test')
                """),
                {"id": ids["user"], "organization_id": ids["organization"]},
            )
            await connection.execute(
                text("""
                    insert into registered_devices
                        (id, workspace_id, user_id, device_public_id, status, registration_state)
                    values (:id, :workspace_id, :user_id, 'normalization-device', 'active', 'approved')
                """),
                {"id": ids["device"], "workspace_id": ids["workspace"], "user_id": ids["user"]},
            )
            await connection.execute(
                text("""
                    insert into meetings
                        (id, workspace_id, created_by_user_id, device_id, local_recording_id,
                         duration_seconds, status)
                    values (:id, :workspace_id, :user_id, :device_id, 'normalization-meeting',
                            60, 'ready')
                """),
                {
                    "id": ids["meeting"],
                    "workspace_id": ids["workspace"],
                    "user_id": ids["user"],
                    "device_id": ids["device"],
                },
            )
            await connection.execute(
                text("""
                    insert into media_revisions
                        (id, workspace_id, meeting_id, local_media_revision_id, source_kind,
                         status, immutable, accepted_at)
                    values (:id, :workspace_id, :meeting_id, 'normalization-revision',
                            'manual_upload', 'accepted', true, '2026-07-14 08:00:00+00:00')
                """),
                {
                    "id": ids["revision"],
                    "workspace_id": ids["workspace"],
                    "meeting_id": ids["meeting"],
                },
            )
            for suffix in ("one", "two"):
                await connection.execute(
                    text("""
                        insert into track_artifacts
                            (id, meeting_id, media_revision_id, workspace_id, track_role,
                             codec, sample_rate_hz, channel_count, duration_seconds,
                             byte_length, sha256, storage_object_key, status)
                        values (:id, :meeting_id, :media_revision_id, :workspace_id, 'playback',
                                'aac', 48000, 1, 60, 480000, :sha256, :storage_object_key, 'stored')
                    """),
                    {
                        "id": uuid4(),
                        "meeting_id": ids["meeting"],
                        "media_revision_id": ids["revision"],
                        "workspace_id": ids["workspace"],
                        "sha256": ("a" if suffix == "one" else "b") * 64,
                        "storage_object_key": f"legacy/{suffix}",
                    },
                )
    finally:
        await engine.dispose()
    return ids


async def _legacy_count(database_url: str, revision_id: UUID) -> int:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            return int(
                await connection.scalar(
                    text("""
                        select count(*) from track_artifacts
                        where media_revision_id = :revision_id
                          and normalization_profile_version is null
                    """),
                    {"revision_id": revision_id},
                )
            )
    finally:
        await engine.dispose()


async def _canonical_duplicate_is_rejected(database_url: str, ids: dict[str, UUID]) -> None:
    values = {
        "meeting_id": ids["meeting"],
        "media_revision_id": ids["revision"],
        "workspace_id": ids["workspace"],
        "profile": PROFILE,
        "validated_at": datetime(2026, 7, 14, 9, tzinfo=UTC),
    }
    statement = text("""
        insert into track_artifacts
            (id, meeting_id, media_revision_id, workspace_id, track_role, codec,
             sample_rate_hz, channel_count, duration_seconds, byte_length, sha256,
             storage_object_key, status, normalization_profile_version, validated_at,
             derivation_kind, source_fingerprint_sha256, validation_version)
        values
            (:id, :meeting_id, :media_revision_id, :workspace_id, 'playback', 'aac',
             48000, 1, 60, 480000, :sha256, :storage_object_key, 'stored', :profile,
             :validated_at, 'source_byte_copy', :source_fingerprint_sha256,
             'playback_validator_v1')
    """)
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                statement,
                {
                    **values,
                    "id": uuid4(),
                    "sha256": "c" * 64,
                    "storage_object_key": "normalization/attempts/one/meeting-review.m4a",
                    "source_fingerprint_sha256": "f" * 64,
                },
            )
        with pytest.raises(IntegrityError):
            async with engine.begin() as connection:
                await connection.execute(
                    statement,
                    {
                        **values,
                        "id": uuid4(),
                        "sha256": "d" * 64,
                        "storage_object_key": "normalization/attempts/two/meeting-review.m4a",
                        "source_fingerprint_sha256": "e" * 64,
                    },
                )
    finally:
        await engine.dispose()


def test_migration_declares_additive_revision_contract() -> None:
    assert MIGRATION.exists()
    migration = _load_migration()

    assert migration.revision == "0022_playback_normalization"
    assert migration.down_revision == "0021_calendar_auto_context_match"
    assert set(migration.PLAYBACK_NORMALIZATION_TABLES) == {
        "playback_normalization_jobs",
        "playback_normalization_attempts",
        "playback_backfill_runs",
    }


def test_postgres_upgrade_preserves_legacy_rows_and_enforces_one_canonical(
    postgres_test_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _alembic_config(postgres_test_database_url, monkeypatch)
    command.upgrade(config, "0021_calendar_auto_context_match")
    ids = asyncio.run(_seed_legacy_playback_rows(postgres_test_database_url))
    command.upgrade(config, "head")

    assert asyncio.run(_legacy_count(postgres_test_database_url, ids["revision"])) == 2
    asyncio.run(_canonical_duplicate_is_rejected(postgres_test_database_url, ids))
    get_settings.cache_clear()


def test_postgres_downgrade_removes_only_playback_normalization_schema(
    postgres_test_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _alembic_config(postgres_test_database_url, monkeypatch)
    command.upgrade(config, "head")
    command.downgrade(config, "0021_calendar_auto_context_match")

    async def summary() -> tuple[set[str], set[str]]:
        engine = create_async_engine(postgres_test_database_url)
        try:
            async with engine.connect() as connection:
                return await connection.run_sync(
                    lambda sync_connection: (
                        set(inspect(sync_connection).get_table_names()),
                        {column["name"] for column in inspect(sync_connection).get_columns("track_artifacts")},
                    )
                )
        finally:
            await engine.dispose()

    tables, artifact_columns = asyncio.run(summary())
    get_settings.cache_clear()

    assert "playback_normalization_jobs" not in tables
    assert "normalization_profile_version" not in artifact_columns
