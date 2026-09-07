from __future__ import annotations

import asyncio
import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from uuid import UUID, uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import JSON, String, inspect, select, text

from tests.fakes.auth_contexts import PERSONAL_WORKSPACE_ID
from tests.fixtures.cabinet import create_outcome_ready_meeting
from tests.fixtures.rls import RLS_COVERED_TABLES as TEST_RLS_COVERED_TABLES
from twobrain_rec_server.db import models
from twobrain_rec_server.db.base import Base
from twobrain_rec_server.db.models import (
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    MeetingSummarySlot,
    ProcessingResult,
)
from twobrain_rec_server.db.rls_validation import RLS_COVERED_TABLES

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0009_meeting_outcomes_mvp.py"
)
PROTOCOL_MIGRATION = MIGRATION.with_name("0086_full_meeting_protocol.py")

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


def test_protocol_storage_columns_have_safe_defaults() -> None:
    outcome = MeetingOutcomeSet.__table__.c
    attempt = MeetingOutcomeGenerationAttempt.__table__.c
    for column in (outcome.source_kind, outcome.generator_kind, attempt.provider_kind):
        assert not column.nullable
        assert column.default is None
        assert column.server_default is None
    for column in (outcome.protocol_json, attempt.header_snapshot_json):
        assert isinstance(column.type, JSON)
        assert column.nullable
        assert column.default is None
        assert column.server_default is None
    assert isinstance(outcome.protocol_schema_version.type, String)
    assert outcome.protocol_schema_version.type.length == 64
    assert outcome.protocol_schema_version.nullable
    assert isinstance(outcome.protocol_state.type, String)
    assert outcome.protocol_state.type.length == 32
    assert not outcome.protocol_state.nullable
    assert outcome.protocol_state.default.arg == "unavailable"
    assert str(outcome.protocol_state.server_default.arg) == "'unavailable'"


def test_protocol_migration_roundtrip_preserves_history_and_bindings(client) -> None:
    migration = _load_migration_module(PROTOCOL_MIGRATION, "full_meeting_protocol_migration")
    assert migration.revision == "0086_full_meeting_protocol"
    assert migration.down_revision == "0087_merge_calendar_timezone"
    meeting_id = create_outcome_ready_meeting(client, "protocol-migration-history")

    async def run() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            outcome = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                generator_version="synthetic-historical",
                source_kind="extractive_generator",
                generator_kind="deterministic_extractive",
                template_key="graf-auto-v1",
                template_version=1,
                status="available",
                revision_state="accepted",
                content_hash="a" * 64,
            )
            db.add(outcome)
            await db.flush()
            attempt = MeetingOutcomeGenerationAttempt(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                outcome_set_id=outcome.id,
                generator_version="synthetic-historical",
                provider_kind="deterministic_extractive",
                metadata_json={"template_sections": ["summary", "decisions"]},
                prompt_config={"synthetic": True},
            )
            db.add_all([
                attempt,
                MeetingOutcomeItem(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    outcome_set_id=outcome.id,
                    category="summary",
                    sequence=1,
                    text="Синтетический исторический итог.",
                    source_refs_json=[{"sequence": 1}],
                ),
                MeetingSummarySlot(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    template_key="graf-auto-v1",
                    current_outcome_set_id=outcome.id,
                    current_binding_class="migrated_legacy_read_only",
                    legacy_migration_proof_hash="b" * 64,
                    is_meeting_default=True,
                    default_resolution_source="legacy_pointer",
                    default_resolution_version="1",
                    default_resolved_at=datetime(2026, 8, 24, tzinfo=UTC),
                ),
            ])
            meeting.current_outcome_set_id = outcome.id
            await db.commit()
            outcome_id, attempt_id = outcome.id, attempt.id

        async with client.app_state["engine"].connect() as connection:
            # Roll back DDL even on assertion failure; other tests share this schema.
            transaction = await connection.begin()
            try:
                def migrate(sync_connection, direction):
                    with Operations.context(MigrationContext.configure(sync_connection)):
                        getattr(migration, direction)()

                def snapshot(sync_connection):
                    return {
                        table: sync_connection.execute(
                            text(f"select to_jsonb(t) from {table} t order by id")
                        ).scalars().all()
                        for table in (
                            "meetings", "meeting_outcome_sets", "meeting_outcome_items",
                            "meeting_outcome_generation_attempts", "meeting_summary_slots",
                            "summary_templates", "generation_calls",
                        )
                    }

                await connection.run_sync(migrate, "downgrade")
                before = await connection.run_sync(snapshot)
                await connection.run_sync(migrate, "upgrade")
                columns = await connection.run_sync(
                    lambda sync: {
                        column["name"]: column
                        for column in inspect(sync).get_columns("meeting_outcome_sets")
                    }
                )
                assert columns["protocol_json"]["nullable"]
                assert columns["protocol_json"]["default"] is None
                assert columns["source_kind"]["default"] is None
                assert columns["generator_kind"]["default"] is None
                attempt_columns = await connection.run_sync(
                    lambda sync: {
                        column["name"]: column
                        for column in inspect(sync).get_columns("meeting_outcome_generation_attempts")
                    }
                )
                assert attempt_columns["provider_kind"]["default"] is None
                assert not columns["protocol_state"]["nullable"]
                assert "unavailable" in columns["protocol_state"]["default"]
                assert (await connection.execute(text(
                    "select protocol_json, protocol_schema_version, protocol_state "
                    "from meeting_outcome_sets where id = :id"
                ), {"id": outcome_id})).one() == (None, None, "unavailable")
                assert await connection.scalar(text(
                    "select header_snapshot_json from meeting_outcome_generation_attempts "
                    "where id = :id"
                ), {"id": attempt_id}) is None

                after = await connection.run_sync(snapshot)
                for row in after["meeting_outcome_sets"]:
                    for key in ("protocol_json", "protocol_schema_version", "protocol_state"):
                        row.pop(key)
                for row in after["meeting_outcome_generation_attempts"]:
                    row.pop("header_snapshot_json")
                assert after == before

                # Downgrade removes only the new fields, including populated JSON.
                await connection.execute(text(
                    "update meeting_outcome_sets set protocol_json = '{\"topics\": []}', "
                    "protocol_schema_version = 'synthetic.v2', protocol_state = 'available' "
                    "where id = :id"
                ), {"id": outcome_id})
                await connection.execute(text(
                    "update meeting_outcome_generation_attempts "
                    "set header_snapshot_json = '{\"title\": \"Synthetic\"}' where id = :id"
                ), {"id": attempt_id})
                await connection.run_sync(migrate, "downgrade")
                assert await connection.run_sync(snapshot) == before
                await connection.run_sync(migrate, "upgrade")
            finally:
                await transaction.rollback()

    asyncio.run(run())


def test_summary_slot_backfill_preserves_proven_legacy_rows_and_reports_ambiguity(client) -> None:
    migration = _load_migration_module(
        REPO_ROOT
        / "apps/server/src/twobrain_rec_server/db/migrations/versions/0076_meeting_summary_slots.py",
        "meeting_summary_slots_migration_integration",
    )
    valid_id = create_outcome_ready_meeting(client, "migration-valid")
    keyless_id = create_outcome_ready_meeting(client, "migration-keyless")
    missing_id = create_outcome_ready_meeting(client, "migration-missing")
    cross_scope_id = create_outcome_ready_meeting(client, "migration-cross-scope")
    ambiguous_id = create_outcome_ready_meeting(client, "migration-ambiguous")
    deleted_id = create_outcome_ready_meeting(client, "migration-deleted")

    async def seed() -> dict[str, object]:
        async with client.app_state["sessionmaker"]() as db:
            meetings = {
                meeting.id: meeting
                for meeting in (
                    await db.scalars(
                        select(Meeting).where(
                            Meeting.id.in_(
                                [
                                    valid_id,
                                    keyless_id,
                                    missing_id,
                                    cross_scope_id,
                                    ambiguous_id,
                                    deleted_id,
                                ]
                            )
                        )
                    )
                ).all()
            }
            results = {
                meeting_id: await db.scalar(
                    select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
                )
                for meeting_id in meetings
            }
            assert all(results.values())

            def outcome(meeting_id: UUID, template_key: str | None, *, workspace_id: UUID | None = None):
                result = results[meeting_id]
                assert result is not None
                return MeetingOutcomeSet(
                    workspace_id=workspace_id or meetings[meeting_id].workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=result.media_revision_id,
                    processing_result_id=result.id,
                    status="available",
                    summary_state="available",
                    source_kind="legacy_fixture",
                    generator_kind="legacy_fixture",
                    generator_version=f"legacy-{meeting_id.hex}",
                    source_result_hash=f"source-{meeting_id.hex}",
                    source_fingerprint=f"fingerprint-{meeting_id.hex}",
                    template_key=template_key,
                    template_version=1,
                    content_hash=f"content-{meeting_id.hex}",
                    lifecycle_state="active",
                    revision_state="accepted",
                    generated_at=datetime(2026, 8, 24, tzinfo=UTC),
                )

            valid = outcome(valid_id, "legacy-valid-v1")
            keyless = outcome(keyless_id, None)
            missing_pointer = uuid4()
            cross_scope = outcome(
                cross_scope_id,
                "legacy-cross-scope-v1",
                workspace_id=PERSONAL_WORKSPACE_ID,
            )
            ambiguous_a = outcome(ambiguous_id, "legacy-ambiguous-a")
            ambiguous_b = outcome(ambiguous_id, "legacy-ambiguous-b")
            deleted = outcome(deleted_id, "legacy-deleted-v1")
            db.add_all([valid, keyless, cross_scope, ambiguous_a, ambiguous_b, deleted])
            await db.flush()
            meetings[valid_id].current_outcome_set_id = valid.id
            meetings[keyless_id].current_outcome_set_id = keyless.id
            meetings[cross_scope_id].current_outcome_set_id = cross_scope.id
            meetings[deleted_id].current_outcome_set_id = deleted.id
            meetings[deleted_id].deletion_state = "deleted"
            await db.commit()
            return {
                "content_hashes": {
                    valid.id: valid.content_hash,
                    keyless.id: keyless.content_hash,
                    deleted.id: deleted.content_hash,
                },
                "missing_pointer": missing_pointer,
                "outcome_ids": {
                    valid_id: valid.id,
                    keyless_id: keyless.id,
                    deleted_id: deleted.id,
                },
            }

    seeded = asyncio.run(seed())

    async def run_backfill() -> tuple[dict[str, object], dict[str, object]]:
        async with client.app_state["engine"].begin() as connection:
            await connection.execute(
                text("alter table meetings drop constraint fk_meetings_current_outcome_set")
            )
            await connection.execute(
                text("update meetings set current_outcome_set_id = :missing where id = :meeting"),
                {"missing": seeded["missing_pointer"], "meeting": missing_id},
            )

            def invoke(sync_connection) -> tuple[dict[str, object], dict[str, object]]:
                context = MigrationContext.configure(sync_connection)
                with Operations.context(context):
                    first = migration._backfill_explicit_pointers()
                    migration._verify_post_backfill(first)
                    second = migration._backfill_explicit_pointers()
                    migration._verify_post_backfill(second)
                    return first, second

            first, second = await connection.run_sync(invoke)
            await connection.execute(
                text("update meetings set current_outcome_set_id = null where id = :meeting"),
                {"meeting": missing_id},
            )
            await connection.execute(
                text(
                    """
                    alter table meetings
                    add constraint fk_meetings_current_outcome_set
                    foreign key (current_outcome_set_id) references meeting_outcome_sets(id)
                    """
                )
            )
            return first, second

    first, second = asyncio.run(run_backfill())

    assert first == {
        "schema_version": "graf.summary_slot_migration_receipt.v1",
        "migration_revision": "0076_meeting_summary_slots",
        "mode": "metadata_only",
        "status": "pass",
        "active_pointer_count": 4,
        "ambiguous_unpointed_count": 1,
        "cross_scope_target_count": 1,
        "deleted_pointer_count": 1,
        "materialized_count": 2,
        "missing_target_count": 1,
        "pointed_keyless_count": 1,
    }
    assert second["status"] == "pass"
    assert second["materialized_count"] == 2
    assert second["missing_target_count"] == 1

    async def inspect() -> tuple[list[MeetingSummarySlot], dict[UUID, str | None], UUID | None]:
        async with client.app_state["sessionmaker"]() as db:
            slots = (
                await db.scalars(
                    select(MeetingSummarySlot).where(
                        MeetingSummarySlot.meeting_id.in_(
                            [valid_id, keyless_id, missing_id, cross_scope_id, ambiguous_id, deleted_id]
                        )
                    )
                )
            ).all()
            outcomes = (
                await db.scalars(
                    select(MeetingOutcomeSet).where(
                        MeetingOutcomeSet.id.in_(list(seeded["outcome_ids"].values()))
                    )
                )
            ).all()
            missing_pointer = await db.scalar(
                select(Meeting.current_outcome_set_id).where(Meeting.id == missing_id)
            )
            return list(slots), {outcome.id: outcome.content_hash for outcome in outcomes}, missing_pointer

    slots, content_hashes, missing_pointer = asyncio.run(inspect())
    assert {(slot.meeting_id, slot.template_key) for slot in slots} == {
        (valid_id, "legacy-valid-v1"),
        (keyless_id, "legacy-default"),
    }
    assert all(slot.current_binding_class == "migrated_legacy_read_only" for slot in slots)
    assert content_hashes == seeded["content_hashes"]
    assert missing_pointer is None
