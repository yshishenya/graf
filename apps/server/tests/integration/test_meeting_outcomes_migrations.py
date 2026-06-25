from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from tests.fixtures.rls import RLS_COVERED_TABLES as TEST_RLS_COVERED_TABLES
from twobrain_rec_server.db import models
from twobrain_rec_server.db.base import Base
from twobrain_rec_server.db.rls_validation import RLS_COVERED_TABLES

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0009_meeting_outcomes_mvp.py"
)

OUTCOME_TABLES = {
    "meeting_outcome_sets",
    "meeting_outcome_items",
    "meeting_outcome_generation_attempts",
}


def _load_migration_module(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_outcome_models_are_registered_in_metadata() -> None:
    assert models.MeetingOutcomeSet.__tablename__ == "meeting_outcome_sets"
    assert models.MeetingOutcomeItem.__tablename__ == "meeting_outcome_items"
    assert models.MeetingOutcomeGenerationAttempt.__tablename__ == "meeting_outcome_generation_attempts"
    assert OUTCOME_TABLES.issubset(Base.metadata.tables)

    outcome_set = Base.metadata.tables["meeting_outcome_sets"]
    outcome_item = Base.metadata.tables["meeting_outcome_items"]
    attempt = Base.metadata.tables["meeting_outcome_generation_attempts"]

    for table in [outcome_set, outcome_item, attempt]:
        assert "workspace_id" in table.c
        assert "meeting_id" in table.c

    assert "summary_state" in outcome_set.c
    assert "source_refs_json" in outcome_item.c
    assert "metadata_json" in attempt.c


def test_outcome_migration_declares_revision_chain_tables_indexes_and_rls() -> None:
    assert MIGRATION.exists()
    migration_text = MIGRATION.read_text(encoding="utf-8")
    migration = _load_migration_module(MIGRATION, "meeting_outcomes_migration")

    assert migration.revision == "0009_meeting_outcomes_mvp"
    assert migration.down_revision == "0008_recording_sync_loop"
    assert OUTCOME_TABLES.issubset(set(migration.CONTENT_WORKSPACE_POLICIES))
    for table_name in OUTCOME_TABLES:
        assert f'"{table_name}"' in migration_text
        assert f"{table_name}_tenant_isolation" in migration_text
    assert "uq_meeting_outcome_sets_current_generator" in migration_text
    assert "ix_meeting_outcome_items_set_category_sequence" in migration_text


def test_outcome_tables_are_in_rls_inventory_and_test_fixture() -> None:
    assert OUTCOME_TABLES.issubset(set(RLS_COVERED_TABLES))
    assert OUTCOME_TABLES.issubset(TEST_RLS_COVERED_TABLES)
