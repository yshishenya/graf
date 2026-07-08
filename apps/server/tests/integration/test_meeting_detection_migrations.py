import importlib.util
from pathlib import Path
from types import ModuleType

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from twobrain_rec_server.config import get_settings

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0017_meeting_detection_registry.py"
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
    finally:
        sync_engine.dispose()
        get_settings.cache_clear()

    assert "meeting_target_registry_versions" in tables
    assert "meeting_detection_candidates" in tables
    assert "meeting_detection_telemetry_rate_limit_buckets" in tables
    assert "uq_meeting_detection_candidates_workspace_bundle" in candidate_indexes
    assert "uq_meeting_detection_non_target_rules_workspace_rule" in non_target_indexes
