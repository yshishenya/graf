from __future__ import annotations

import importlib.util
from pathlib import Path
from uuid import UUID

from twobrain_rec_server.db import models
from twobrain_rec_server.db.base import Base

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0076_meeting_summary_slots.py"
)


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("meeting_summary_slots_migration", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_slot_migration_is_the_next_idempotent_revision_with_composite_bindings() -> None:
    assert MIGRATION.exists()
    migration_text = MIGRATION.read_text(encoding="utf-8")
    migration = _load_migration_module()

    assert migration.revision == "0076_meeting_summary_slots"
    assert migration.down_revision == "0075_calendar_sync_maintenance"
    assert "meeting_summary_slots" in migration_text
    assert "uq_meetings_id_workspace_id" in migration_text
    assert "fk_meeting_summary_slots_meeting_workspace" in migration_text
    assert "fk_meeting_summary_slots_current_outcome_target" in migration_text
    assert "migrated_legacy_read_only" in migration_text
    assert "legacy_migration_proof_hash" in migration_text


def test_slot_model_and_migration_contract_forbid_feature_183_receipt_schema() -> None:
    slot = Base.metadata.tables["meeting_summary_slots"]
    assert not any("receipt" in column.name or "fingerprint" in column.name for column in slot.columns)
    migration_text = MIGRATION.read_text(encoding="utf-8") if MIGRATION.exists() else ""
    assert "publication_receipt" not in migration_text
    assert "canonical_artifact" not in migration_text
    assert "generation_call_owner" not in migration_text


def test_only_explicit_pointer_can_create_legacy_read_only_slot() -> None:
    migration_text = MIGRATION.read_text(encoding="utf-8") if MIGRATION.exists() else ""
    assert "current_outcome_set_id" in migration_text
    assert "legacy_pointer" in migration_text
    backfill_text = migration_text.split("def _backfill_explicit_pointers", 1)[1].split(
        "def _stable_slot_id", 1
    )[0]
    assert "ORDER BY" not in backfill_text.upper()
    assert "LIMIT 1" not in backfill_text.upper()
    assert models.MeetingSummarySlot.__tablename__ == "meeting_summary_slots"


def test_legacy_proof_hash_uses_the_normative_domain_and_is_reproducible() -> None:
    migration = _load_migration_module()
    kwargs = {
        "workspace_id": UUID("00000000-0000-0000-0000-000000000001"),
        "meeting_id": UUID("00000000-0000-0000-0000-000000000002"),
        "template_key": "legacy-default",
        "outcome_set_id": UUID("00000000-0000-0000-0000-000000000003"),
        "source_basis_hash": "a" * 64,
    }
    assert migration._legacy_proof(**kwargs) == (
        "af9c044c38adef055b4740fd95b7a1cd8372ceb89987edd9f764d0a9749f49d6"
    )
    assert migration._legacy_proof(**kwargs) == migration._legacy_proof(**kwargs)
