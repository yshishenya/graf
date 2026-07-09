import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

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


def _load_migration_module(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_clean_sqlite_database_migrates_meeting_detection_tables(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "meeting-detection.db"
    database_url = f"sqlite+aiosqlite:///{database_path}"
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", database_url)
    get_settings.cache_clear()
    alembic_config = Config(str(REPO_ROOT / "apps/server/alembic.ini"))
    alembic_config.set_main_option(
        "script_location",
        str(REPO_ROOT / "apps/server/src/twobrain_rec_server/db/migrations"),
    )

    command.upgrade(alembic_config, "head")

    sync_engine = create_engine(f"sqlite:///{database_path}")
    try:
        inspector = inspect(sync_engine)
        tables = set(inspector.get_table_names())
        candidate_indexes = {index["name"] for index in inspector.get_indexes("meeting_detection_candidates")}
        non_target_indexes = {index["name"] for index in inspector.get_indexes("meeting_detection_non_target_rules")}
        with sync_engine.connect() as connection:
            registry_row = connection.exec_driver_sql(
                "select registry_version, status, source from meeting_target_registry_versions"
            ).one()
            entry_count = connection.exec_driver_sql("select count(*) from meeting_target_registry_entries").scalar_one()
    finally:
        sync_engine.dispose()
        get_settings.cache_clear()

    assert "meeting_target_registry_versions" in tables
    assert "meeting_detection_candidates" in tables
    assert "meeting_detection_telemetry_rate_limit_buckets" in tables
    assert "uq_meeting_detection_candidates_workspace_bundle" in candidate_indexes
    assert "uq_meeting_detection_non_target_rules_workspace_rule" in non_target_indexes
    assert tuple(registry_row) == ("2026.07.09.4", "published", "migration")
    assert entry_count >= 20


def test_publish_registry_migration_downgrade_restores_previous_published_registry(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "meeting-detection-rollback.db"
    database_url = f"sqlite+aiosqlite:///{database_path}"
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", database_url)
    get_settings.cache_clear()
    alembic_config = Config(str(REPO_ROOT / "apps/server/alembic.ini"))
    alembic_config.set_main_option(
        "script_location",
        str(REPO_ROOT / "apps/server/src/twobrain_rec_server/db/migrations"),
    )
    previous_registry = {
        "schemaVersion": 1,
        "registryVersion": "2026.07.08.99",
        "generatedAt": "2026-07-08T00:00:00Z",
        "targets": [],
    }
    previous_id = uuid4().hex
    timestamp = datetime(2026, 7, 8, tzinfo=UTC).isoformat()

    command.upgrade(alembic_config, "0017_meeting_detection")
    sync_engine = create_engine(f"sqlite:///{database_path}")
    try:
        with sync_engine.begin() as connection:
            connection.exec_driver_sql(
                """
                insert into meeting_target_registry_versions (
                    id,
                    registry_version,
                    schema_version,
                    status,
                    source,
                    published_at,
                    document_json,
                    etag,
                    created_at,
                    updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    previous_id,
                    previous_registry["registryVersion"],
                    previous_registry["schemaVersion"],
                    "published",
                    "admin",
                    timestamp,
                    json.dumps(previous_registry),
                    "previous-etag",
                    timestamp,
                    timestamp,
                ),
            )

        command.upgrade(alembic_config, "head")
        with sync_engine.connect() as connection:
            upgraded_rows = [
                tuple(row)
                for row in connection.exec_driver_sql(
                    "select registry_version, status, source from meeting_target_registry_versions order by registry_version"
                )
            ]

        command.downgrade(alembic_config, "0018_mediascribe_result")
        with sync_engine.connect() as connection:
            downgraded_rows = [
                tuple(row)
                for row in connection.exec_driver_sql(
                    "select registry_version, status, source from meeting_target_registry_versions order by registry_version"
                )
            ]
    finally:
        sync_engine.dispose()
        get_settings.cache_clear()

    assert ("2026.07.08.99", "superseded", "admin") in upgraded_rows
    assert ("2026.07.09.4", "published", "migration") in upgraded_rows
    assert downgraded_rows == [("2026.07.08.99", "published", "admin")]
