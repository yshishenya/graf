from __future__ import annotations

import asyncio
import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from tests.fixtures.cabinet import create_outcome_ready_meeting
from twobrain_rec_server.cabinet import queries
from twobrain_rec_server.cabinet.egress import (
    _processing_result_is_current,
    current_outcome_set,
)
from twobrain_rec_server.db.base import Base
from twobrain_rec_server.db.models import (
    Meeting,
    MeetingOutcomeSet,
    MeetingSummarySlot,
    ProcessingResult,
)
from twobrain_rec_server.outcomes import service as outcome_service
from twobrain_rec_server.outcomes.ai_service import (
    SummarySlotCASConflict,
    _cas_summary_slot,
    create_summary_candidate,
)
from twobrain_rec_server.outcomes.service import (
    SummarySlotDefaultConflict,
    ensure_summary_slot,
    load_meeting_default_slot,
    mark_meeting_default_slot,
)


async def _seed_model_candidate(
    db,
    *,
    meeting: Meeting,
    template_key: str = "graf-auto-v1",
    expected_current_outcome_set_id: UUID | None = None,
    access_policy_epoch: int = 7,
) -> tuple[MeetingOutcomeSet, object]:
    attempt = await create_summary_candidate(
        db,
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        requested_by_user_id=meeting.created_by_user_id,
        template_key=template_key,
        template_id=None,
        template_version=1,
        expected_current_outcome_set_id=expected_current_outcome_set_id,
    )
    assert attempt.candidate_id is not None
    candidate = MeetingOutcomeSet(
        workspace_id=meeting.workspace_id,
        meeting_id=meeting.id,
        media_revision_id=attempt.media_revision_id,
        processing_result_id=attempt.processing_result_id,
        candidate_id=attempt.candidate_id,
        status="available",
        generator_version=attempt.generator_version,
        source_result_hash=attempt.source_result_hash,
        source_fingerprint=attempt.source_fingerprint,
        deletion_epoch_at_start=attempt.deletion_epoch_at_start,
        template_key=template_key,
        template_version=1,
        revision_state="candidate",
    )
    db.add(candidate)
    await db.flush()
    attempt.outcome_set_id = candidate.id
    attempt.status = "candidate"
    attempt.metadata_json = {
        **(attempt.metadata_json or {}),
        "access_policy_epoch": access_policy_epoch,
    }
    await db.flush()
    return candidate, attempt


def test_default_marker_is_persisted_once_and_never_moves_with_a_second_choice(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-slot-default-marker")
    resolved_at = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)

    async def run() -> UUID:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            assert meeting is not None
            first = await mark_meeting_default_slot(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                template_key="graf-auto-v1",
                resolution_source="workspace",
                resolution_version="workspace-default-v1",
                resolved_at=resolved_at,
            )
            same = await mark_meeting_default_slot(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                template_key="graf-auto-v1",
                resolution_source="workspace",
                resolution_version="workspace-default-v1",
                resolved_at=resolved_at,
            )
            assert same.id == first.id
            persisted = await load_meeting_default_slot(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
            )
            assert persisted is not None
            assert persisted.template_key == "graf-auto-v1"
            assert persisted.default_resolution_source == "workspace"
            assert persisted.default_resolution_version == "workspace-default-v1"
            assert persisted.default_resolved_at == resolved_at
            with pytest.raises(SummarySlotDefaultConflict, match="summary_default_conflict"):
                await mark_meeting_default_slot(
                    db,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    template_key="meeting_minutes",
                    resolution_source="workspace",
                    resolution_version="workspace-default-v1",
                    resolved_at=resolved_at,
                )
            db.add(
                MeetingSummarySlot(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    template_key="standup",
                    is_meeting_default=True,
                    default_resolution_source="workspace",
                    default_resolution_version="workspace-default-v1",
                    default_resolved_at=resolved_at,
                )
            )
            with pytest.raises(IntegrityError):
                await db.flush()
            await db.rollback()
            return first.id

    asyncio.run(run())


def test_concurrent_first_ensure_returns_one_slot_without_unique_violation(
    client, monkeypatch
) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-slot-concurrent-first-ensure")

    async def run() -> tuple[UUID, UUID, int]:
        gate = asyncio.Barrier(2)
        first_loads: set[int] = set()
        original_load = outcome_service.load_summary_slot

        async def gated_load(*args, **kwargs):
            slot = await original_load(*args, **kwargs)
            task = asyncio.current_task()
            task_key = id(task)
            if not kwargs.get("for_update") and task_key not in first_loads:
                first_loads.add(task_key)
                await gate.wait()
            return slot

        monkeypatch.setattr(outcome_service, "load_summary_slot", gated_load)

        async def worker() -> UUID:
            async with client.app_state["sessionmaker"]() as db:
                meeting = await db.get(Meeting, meeting_id)
                assert meeting is not None
                slot = await ensure_summary_slot(
                    db,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    template_key="graf-outline-v1",
                )
                await db.commit()
                return slot.id

        first_id, second_id = await asyncio.wait_for(
            asyncio.gather(worker(), worker()), timeout=5
        )
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            workspace_id = meeting.workspace_id
        async with client.app_state["sessionmaker"]() as db:
            count = await db.scalar(
                select(func.count(MeetingSummarySlot.id)).where(
                    MeetingSummarySlot.workspace_id == workspace_id,
                    MeetingSummarySlot.meeting_id == meeting_id,
                    MeetingSummarySlot.template_key == "graf-outline-v1",
                )
            )
        return first_id, second_id, int(count or 0)

    first_id, second_id, count = asyncio.run(run())
    assert first_id == second_id
    assert count == 1


def test_mapped_metadata_create_all_is_compatible_with_migrated_slot_schema(client) -> None:
    async def run() -> None:
        async with client.app_state["engine"].begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(run())


def test_slot_migration_head_is_idempotent(
    postgres_schema_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", postgres_schema_database_url)
    server_root = Path(__file__).resolve().parents[2]
    config = Config(str(server_root / "alembic.ini"))
    config.set_main_option(
        "script_location",
        str(server_root / "src/twobrain_rec_server/db/migrations"),
    )
    command.upgrade(config, "head")
    command.upgrade(config, "head")


def test_legacy_backfill_only_materializes_the_explicit_meeting_pointer(client) -> None:
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "src/twobrain_rec_server/db/migrations/versions/0076_meeting_summary_slots.py"
    )
    module_spec = importlib.util.spec_from_file_location("summary_slots_0076", migration_path)
    assert module_spec is not None and module_spec.loader is not None
    migration = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(migration)
    meeting_id = create_outcome_ready_meeting(client, "summary-slot-legacy-backfill")

    async def run() -> tuple[UUID, str, str, str]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            outcome_id = uuid4()
            outcome = MeetingOutcomeSet(
                id=outcome_id,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                status="available",
                source_kind="legacy_fixture",
                generator_kind="legacy_fixture",
                generator_version="legacy-v1",
                source_result_hash=result.source_result_hash,
                source_fingerprint=f"result:{result.id}",
                template_key="graf-auto-v1",
                template_version=1,
                revision_state="accepted",
            )
            db.add(outcome)
            await db.flush()
            meeting.current_outcome_set_id = outcome.id
            await db.commit()
            workspace_id = meeting.workspace_id

        async with client.app_state["engine"].begin() as connection:
            def run_backfill(sync_connection) -> None:
                context = MigrationContext.configure(sync_connection)
                with Operations.context(context):
                    migration._backfill_explicit_pointers()

            await connection.run_sync(run_backfill)

        async with client.app_state["sessionmaker"]() as db:
            slot = await db.scalar(
                select(MeetingSummarySlot).where(
                    MeetingSummarySlot.workspace_id == workspace_id,
                    MeetingSummarySlot.meeting_id == meeting_id,
                    MeetingSummarySlot.template_key == "graf-auto-v1",
                )
            )
            assert slot is not None
            assert slot.current_outcome_set_id == outcome_id
            assert slot.current_binding_class == "migrated_legacy_read_only"
            assert slot.is_meeting_default is True
            assert slot.default_resolution_source == "legacy_pointer"
            assert slot.default_resolution_version == "0076-legacy-pointer-v1"
            assert slot.legacy_migration_proof_hash == migration._legacy_proof(
                workspace_id=workspace_id,
                meeting_id=meeting_id,
                template_key="graf-auto-v1",
                outcome_set_id=outcome_id,
                source_basis_hash=f"result:{result.id}",
            )
            return (
                slot.current_outcome_set_id,
                slot.current_binding_class,
                slot.default_resolution_source,
                slot.legacy_migration_proof_hash,
            )

    outcome_id, binding_class, resolution_source, proof = asyncio.run(run())
    assert outcome_id is not None
    assert binding_class == "migrated_legacy_read_only"
    assert resolution_source == "legacy_pointer"
    assert len(proof) == 64


def test_browser_processing_read_uses_default_slot_when_legacy_pointer_is_null(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-slot-browser-read")

    async def run() -> UUID:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            outcome = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=result.media_revision_id,
                processing_result_id=result.id,
                status="available",
                source_kind="db_fixture",
                generator_kind="db_fixture",
                generator_version="test-db-only",
                source_result_hash=result.source_result_hash,
                source_fingerprint=f"result:{result.id}",
                template_key="graf-auto-v1",
                revision_state="accepted",
            )
            db.add(outcome)
            await db.flush()
            db.add(
                MeetingSummarySlot(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    template_key="graf-auto-v1",
                    current_outcome_set_id=outcome.id,
                    current_binding_class="verified_complete",
                    is_meeting_default=True,
                    default_resolution_source="explicit_meeting",
                    default_resolution_version="test-fixture-v1",
                    default_resolved_at=datetime(2026, 8, 24, tzinfo=UTC),
                )
            )
            newer = ProcessingResult(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=result.media_revision_id,
                mediascribe_job_id=result.mediascribe_job_id,
                processing_workflow_id=result.processing_workflow_id,
                result_version=result.result_version + 1,
                status="imported",
                transcript_status=result.transcript_status,
                diarization_status=result.diarization_status,
                summary_status=result.summary_status,
                language=result.language,
                segment_count=result.segment_count,
                diarization_segment_count=result.diarization_segment_count,
                source_result_hash="newer-result-hash",
                imported_at=datetime(2026, 8, 24, 12, 1, tzinfo=UTC),
            )
            db.add(newer)
            await db.flush()
            selected = await queries.latest_processing_result(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
            )
            assert selected is not None and selected.id == result.id
            assert await _processing_result_is_current(
                db,
                meeting=meeting,
                result=result,
            )
            selected_id = selected.id
            await db.rollback()
            return selected_id

    asyncio.run(run())


def test_default_read_does_not_fall_back_to_legacy_pointer_when_slots_have_no_default(
    client,
) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-slot-default-missing")

    async def run() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            outcome = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                media_revision_id=result.media_revision_id,
                processing_result_id=result.id,
                status="available",
                source_kind="db_fixture",
                generator_kind="db_fixture",
                generator_version="test-db-only",
                source_result_hash=result.source_result_hash,
                template_key="graf-auto-v1",
                revision_state="accepted",
            )
            db.add(outcome)
            await db.flush()
            meeting.current_outcome_set_id = outcome.id
            db.add(
                MeetingSummarySlot(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    template_key="meeting_minutes",
                )
            )
            await db.flush()
            assert (
                await current_outcome_set(
                    db,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    processing_result_id=result.id,
                )
                is None
            )
            await db.rollback()

    asyncio.run(run())


def test_null_current_slot_cannot_cross_workspace_bind_to_a_meeting(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-slot-null-cross-workspace")

    async def run() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            assert meeting is not None
            db.add(
                MeetingSummarySlot(
                    workspace_id=UUID("20000000-0000-0000-0000-000000000099"),
                    meeting_id=meeting.id,
                    template_key="graf-auto-v1",
                )
            )
            with pytest.raises(IntegrityError):
                await db.flush()
            await db.rollback()

    asyncio.run(run())


def test_current_outcome_pointer_is_bound_to_the_same_meeting_and_type(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-slot-composite-pointer")

    async def run() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            outcome = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                status="available",
                source_kind="db_fixture",
                generator_kind="db_fixture",
                generator_version="test-db-only",
                template_key="meeting_minutes",
                revision_state="accepted",
            )
            db.add(outcome)
            await db.flush()
            db.add(
                MeetingSummarySlot(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    template_key="graf-auto-v1",
                    current_outcome_set_id=outcome.id,
                    current_binding_class="verified_complete",
                )
            )
            with pytest.raises(IntegrityError):
                await db.flush()
            await db.rollback()

    asyncio.run(run())


def test_complete_and_grandfathered_bindings_keep_type_specific_current_reads(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-slot-binding-classes")

    async def run() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            outcomes = [
                MeetingOutcomeSet(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    media_revision_id=result.media_revision_id,
                    processing_result_id=result.id,
                    status="available",
                    source_kind="db_fixture",
                    generator_kind="db_fixture",
                    generator_version="test-db-only",
                    source_result_hash=result.source_result_hash,
                    source_fingerprint=f"result:{result.id}",
                    template_key=template_key,
                    revision_state="accepted",
                )
                for template_key in ("graf-auto-v1", "meeting_minutes")
            ]
            db.add_all(outcomes)
            await db.flush()
            db.add_all(
                [
                    MeetingSummarySlot(
                        workspace_id=meeting.workspace_id,
                        meeting_id=meeting.id,
                        template_key="graf-auto-v1",
                        current_outcome_set_id=outcomes[0].id,
                        current_binding_class="verified_complete",
                    ),
                    MeetingSummarySlot(
                        workspace_id=meeting.workspace_id,
                        meeting_id=meeting.id,
                        template_key="meeting_minutes",
                        current_outcome_set_id=outcomes[1].id,
                        current_binding_class="migrated_legacy_read_only",
                        legacy_migration_proof_hash="a" * 64,
                    ),
                ]
            )
            await db.flush()
            complete = await current_outcome_set(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                template_key="graf-auto-v1",
            )
            grandfathered = await current_outcome_set(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                template_key="meeting_minutes",
            )
            grandfathered_egress = await current_outcome_set(
                db,
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                template_key="meeting_minutes",
                allow_legacy_read_only=False,
            )
            assert complete is not None and complete.id == outcomes[0].id
            assert grandfathered is not None and grandfathered.id == outcomes[1].id
            assert grandfathered_egress is None

    asyncio.run(run())


def test_db_only_cas_operations_are_isolated_by_summary_type(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-slot-cross-type-cas")

    async def run() -> tuple[UUID, UUID, UUID, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            source_fingerprint = f"result:{result.id}"

            async def seed_type(template_key: str) -> tuple[MeetingSummarySlot, MeetingOutcomeSet]:
                old = MeetingOutcomeSet(
                    id=uuid4(),
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    processing_result_id=result.id,
                    template_key=template_key,
                    status="available",
                    revision_state="accepted",
                    generator_version=f"old:{template_key}",
                    source_fingerprint=source_fingerprint,
                    deletion_epoch_at_start=meeting.deletion_epoch,
                )
                slot = MeetingSummarySlot(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    template_key=template_key,
                    current_outcome_set_id=old.id,
                )
                db.add_all([old, slot])
                await db.flush()
                return slot, old

            first_slot, first_old = await seed_type("graf-auto-v1")
            second_slot, second_old = await seed_type("graf-outline-v1")
            first_new = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                template_key="graf-auto-v1",
                status="available",
                revision_state="candidate",
                generator_version="new:graf-auto-v1",
                source_fingerprint=source_fingerprint,
                deletion_epoch_at_start=meeting.deletion_epoch,
            )
            second_new = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                template_key="graf-outline-v1",
                status="available",
                revision_state="candidate",
                generator_version="new:graf-outline-v1",
                source_fingerprint=source_fingerprint,
                deletion_epoch_at_start=meeting.deletion_epoch,
            )
            db.add_all([first_new, second_new])
            await db.flush()

            for template_key, _slot, old, replacement in (
                ("graf-auto-v1", first_slot, first_old, first_new),
                ("graf-outline-v1", second_slot, second_old, second_new),
            ):
                await _cas_summary_slot(
                    db,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    template_key=template_key,
                    replacement_outcome_set_id=replacement.id,
                    expected_current_outcome_set_id=old.id,
                    expected_source_fingerprint=source_fingerprint,
                    expected_deletion_epoch=meeting.deletion_epoch,
                )

            await db.flush()
            return (
                first_slot.current_outcome_set_id,
                second_slot.current_outcome_set_id,
                first_new.id,
                second_new.id,
            )

    first_current, second_current, first_new_id, second_new_id = asyncio.run(run())
    assert first_current == first_new_id
    assert second_current == second_new_id
    assert first_current != second_current


def test_db_only_cas_rejects_deletion_epoch_change_and_keeps_current(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-slot-deletion-fence")

    async def run() -> tuple[UUID, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            source_fingerprint = f"result:{result.id}"
            old = MeetingOutcomeSet(
                id=uuid4(),
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                template_key="graf-auto-v1",
                status="available",
                revision_state="accepted",
                generator_version="old:graf-auto-v1",
                source_fingerprint=source_fingerprint,
                deletion_epoch_at_start=meeting.deletion_epoch,
            )
            replacement = MeetingOutcomeSet(
                id=uuid4(),
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                template_key="graf-auto-v1",
                status="available",
                revision_state="candidate",
                generator_version="new:graf-auto-v1",
                source_fingerprint=source_fingerprint,
                deletion_epoch_at_start=meeting.deletion_epoch,
            )
            slot = MeetingSummarySlot(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                template_key="graf-auto-v1",
                current_outcome_set_id=old.id,
            )
            db.add_all([old, replacement, slot])
            await db.flush()
            expected_epoch = meeting.deletion_epoch
            meeting.deletion_epoch += 1
            meeting.deletion_state = "requested"
            with pytest.raises(SummarySlotCASConflict, match="summary_slot_conflict"):
                await _cas_summary_slot(
                    db,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    template_key="graf-auto-v1",
                    replacement_outcome_set_id=replacement.id,
                    expected_current_outcome_set_id=old.id,
                    expected_source_fingerprint=source_fingerprint,
                    expected_deletion_epoch=expected_epoch,
                )
            assert slot.current_outcome_set_id == old.id
            assert old.revision_state == "accepted"
            assert replacement.revision_state == "candidate"
            await db.rollback()
            return old.id, replacement.id

    old_id, replacement_id = asyncio.run(run())
    assert old_id != replacement_id


def test_same_type_cas_race_has_one_winner_and_keeps_other_replacement_unpublished(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-slot-same-type-race")

    async def run() -> tuple[str, str, UUID, UUID, UUID, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            source_fingerprint = f"result:{result.id}"
            old = MeetingOutcomeSet(
                id=uuid4(),
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                template_key="graf-auto-v1",
                status="available",
                revision_state="accepted",
                generator_version="race-old",
                source_fingerprint=source_fingerprint,
                deletion_epoch_at_start=meeting.deletion_epoch,
            )
            replacements = [
                MeetingOutcomeSet(
                    id=uuid4(),
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    processing_result_id=result.id,
                    template_key="graf-auto-v1",
                    status="available",
                    revision_state="candidate",
                    generator_version=f"race-new-{index}",
                    source_fingerprint=source_fingerprint,
                    deletion_epoch_at_start=meeting.deletion_epoch,
                )
                for index in (1, 2)
            ]
            slot = MeetingSummarySlot(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                template_key="graf-auto-v1",
                current_outcome_set_id=old.id,
            )
            db.add_all([old, *replacements, slot])
            await db.commit()
            workspace_id = meeting.workspace_id
            expected_epoch = meeting.deletion_epoch
            expected_current = old.id

        gate = asyncio.Barrier(2)

        async def worker(replacement_id: UUID) -> str:
            async with client.app_state["sessionmaker"]() as db:
                await gate.wait()
                try:
                    await _cas_summary_slot(
                        db,
                        workspace_id=workspace_id,
                        meeting_id=meeting_id,
                        template_key="graf-auto-v1",
                        replacement_outcome_set_id=replacement_id,
                        expected_current_outcome_set_id=expected_current,
                        expected_source_fingerprint=source_fingerprint,
                        expected_deletion_epoch=expected_epoch,
                    )
                except SummarySlotCASConflict:
                    await db.rollback()
                    return "lost"
                await db.commit()
                return "won"

        results = await asyncio.wait_for(
            asyncio.gather(*(worker(replacement.id) for replacement in replacements)),
            timeout=5,
        )
        async with client.app_state["sessionmaker"]() as db:
            persisted_slot = await db.scalar(
                select(MeetingSummarySlot).where(
                    MeetingSummarySlot.workspace_id == workspace_id,
                    MeetingSummarySlot.meeting_id == meeting_id,
                    MeetingSummarySlot.template_key == "graf-auto-v1",
                )
            )
            persisted_old = await db.get(MeetingOutcomeSet, old.id)
            persisted_replacements = [
                await db.get(MeetingOutcomeSet, replacement.id) for replacement in replacements
            ]
            assert persisted_slot is not None and persisted_old is not None
            assert all(replacement is not None for replacement in persisted_replacements)
            return (
                results[0],
                results[1],
                persisted_slot.current_outcome_set_id,
                old.id,
                replacements[0].id,
                replacements[1].id,
            )

    first_result, second_result, current_id, old_id, first_replacement_id, second_replacement_id = (
        asyncio.run(run())
    )
    assert sorted((first_result, second_result)) == ["lost", "won"]
    assert current_id != old_id
    assert current_id in {first_replacement_id, second_replacement_id}


def test_model_cas_rejects_expired_replacement_and_keeps_slot_unbound(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-slot-expired-replacement")

    async def run() -> tuple[UUID | None, str, str]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            candidate, attempt = await _seed_model_candidate(db, meeting=meeting)
            candidate.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            with pytest.raises(SummarySlotCASConflict):
                await _cas_summary_slot(
                    db,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    template_key="graf-auto-v1",
                    replacement_outcome_set_id=candidate.id,
                    expected_current_outcome_set_id=None,
                    expected_source_fingerprint=candidate.source_fingerprint or "",
                    expected_deletion_epoch=meeting.deletion_epoch,
                    expected_access_policy_epoch=7,
                )
            slot = await db.scalar(
                select(MeetingSummarySlot).where(
                    MeetingSummarySlot.meeting_id == meeting.id,
                    MeetingSummarySlot.template_key == "graf-auto-v1",
                )
            )
            assert slot is not None
            return slot.current_outcome_set_id, candidate.revision_state or "", attempt.status

    current_id, candidate_state, attempt_status = asyncio.run(run())
    assert current_id is None
    assert candidate_state == "candidate"
    assert attempt_status == "candidate"


def test_model_cas_rejects_expired_attempt_and_keeps_slot_unbound(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-slot-expired-attempt")

    async def run() -> tuple[UUID | None, str, str]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            candidate, attempt = await _seed_model_candidate(db, meeting=meeting)
            candidate.expires_at = datetime.now(UTC) + timedelta(hours=1)
            attempt.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            with pytest.raises(SummarySlotCASConflict):
                await _cas_summary_slot(
                    db,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    template_key="graf-auto-v1",
                    replacement_outcome_set_id=candidate.id,
                    expected_current_outcome_set_id=None,
                    expected_source_fingerprint=candidate.source_fingerprint or "",
                    expected_deletion_epoch=meeting.deletion_epoch,
                    expected_access_policy_epoch=7,
                )
            slot = await db.scalar(
                select(MeetingSummarySlot).where(
                    MeetingSummarySlot.meeting_id == meeting.id,
                    MeetingSummarySlot.template_key == "graf-auto-v1",
                )
            )
            assert slot is not None
            return slot.current_outcome_set_id, candidate.revision_state or "", attempt.status

    current_id, candidate_state, attempt_status = asyncio.run(run())
    assert current_id is None
    assert candidate_state == "candidate"
    assert attempt_status == "candidate"


def test_model_cas_rejects_access_policy_epoch_mismatch(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-slot-access-policy-fence")

    async def run() -> tuple[UUID | None, str, str]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            candidate, attempt = await _seed_model_candidate(db, meeting=meeting)
            with pytest.raises(SummarySlotCASConflict):
                await _cas_summary_slot(
                    db,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    template_key="graf-auto-v1",
                    replacement_outcome_set_id=candidate.id,
                    expected_current_outcome_set_id=None,
                    expected_source_fingerprint=candidate.source_fingerprint or "",
                    expected_deletion_epoch=meeting.deletion_epoch,
                    expected_access_policy_epoch=8,
                )
            slot = await db.scalar(
                select(MeetingSummarySlot).where(
                    MeetingSummarySlot.meeting_id == meeting.id,
                    MeetingSummarySlot.template_key == "graf-auto-v1",
                )
            )
            assert slot is not None
            return slot.current_outcome_set_id, candidate.revision_state or "", attempt.status

    current_id, candidate_state, attempt_status = asyncio.run(run())
    assert current_id is None
    assert candidate_state == "candidate"
    assert attempt_status == "candidate"


def test_model_cas_rejects_candidate_attempt_scope_mismatch(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-slot-attempt-scope-fence")

    async def run() -> tuple[UUID | None, str, str]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            candidate, attempt = await _seed_model_candidate(db, meeting=meeting)
            attempt.template_key = "graf-outline-v1"
            with pytest.raises(SummarySlotCASConflict):
                await _cas_summary_slot(
                    db,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    template_key="graf-auto-v1",
                    replacement_outcome_set_id=candidate.id,
                    expected_current_outcome_set_id=None,
                    expected_source_fingerprint=candidate.source_fingerprint or "",
                    expected_deletion_epoch=meeting.deletion_epoch,
                    expected_access_policy_epoch=7,
                )
            slot = await db.scalar(
                select(MeetingSummarySlot).where(
                    MeetingSummarySlot.meeting_id == meeting.id,
                    MeetingSummarySlot.template_key == "graf-auto-v1",
                )
            )
            assert slot is not None
            return slot.current_outcome_set_id, candidate.revision_state or "", attempt.status

    current_id, candidate_state, attempt_status = asyncio.run(run())
    assert current_id is None
    assert candidate_state == "candidate"
    assert attempt_status == "candidate"


def test_model_cas_source_change_keeps_prior_current_and_candidate_unpublished(client) -> None:
    meeting_id = create_outcome_ready_meeting(client, "summary-slot-source-fence")

    async def run() -> tuple[UUID, UUID, str, str]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert meeting is not None and result is not None
            prior = MeetingOutcomeSet(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                processing_result_id=result.id,
                template_key="graf-auto-v1",
                status="available",
                revision_state="accepted",
                generator_version="prior-db-only",
                source_fingerprint=f"result:{result.id}",
                deletion_epoch_at_start=meeting.deletion_epoch,
            )
            db.add(prior)
            await db.flush()
            slot = MeetingSummarySlot(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                template_key="graf-auto-v1",
                current_outcome_set_id=prior.id,
            )
            db.add(slot)
            await db.flush()
            candidate, attempt = await _seed_model_candidate(
                db,
                meeting=meeting,
                expected_current_outcome_set_id=prior.id,
            )
            db.add(
                ProcessingResult(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    media_revision_id=result.media_revision_id,
                    mediascribe_job_id=result.mediascribe_job_id,
                    processing_workflow_id=result.processing_workflow_id,
                    result_version=result.result_version + 1,
                    status="imported",
                    transcript_status=result.transcript_status,
                    diarization_status=result.diarization_status,
                    summary_status=result.summary_status,
                    language=result.language,
                    source_result_hash="newer-source-for-cas",
                    imported_at=datetime.now(UTC) + timedelta(seconds=1),
                )
            )
            await db.flush()
            with pytest.raises(SummarySlotCASConflict):
                await _cas_summary_slot(
                    db,
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    template_key="graf-auto-v1",
                    replacement_outcome_set_id=candidate.id,
                    expected_current_outcome_set_id=prior.id,
                    expected_source_fingerprint=candidate.source_fingerprint or "",
                    expected_deletion_epoch=meeting.deletion_epoch,
                    expected_access_policy_epoch=7,
                )
            return slot.current_outcome_set_id, prior.id, prior.revision_state or "", attempt.status

    current_id, prior_id, prior_state, attempt_status = asyncio.run(run())
    assert current_id == prior_id
    assert prior_state == "accepted"
    assert attempt_status == "candidate"
