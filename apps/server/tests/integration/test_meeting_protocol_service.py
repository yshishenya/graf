"""Storage/projection boundaries; no model calls or production data."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from hashlib import sha256

import pytest
from sqlalchemy import func, select

from tests.fixtures.cabinet import create_outcome_ready_meeting
from tests.fixtures.meeting_protocol import protocol_result
from twobrain_rec_server.db.models import (
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    MeetingSummarySlot,
    ProcessingResult,
)
from twobrain_rec_server.outcomes import service, store
from twobrain_rec_server.outcomes.models import PROTOCOL_SCHEMA_VERSION
from twobrain_rec_server.outcomes.prompts import canonical_json


@pytest.mark.parametrize("ai_dispatch_planned", [None, False, True])
def test_processing_only_projects_wait_without_extracting_or_creating_attempts(
    client, monkeypatch, ai_dispatch_planned
):
    meeting_id = create_outcome_ready_meeting(client, "protocol-wait-only")
    invoked = []

    def forbidden_generation(*_args, **_kwargs):
        invoked.append(True)
        raise AssertionError("Local generation is retired")

    # Works both before retirement and after the import has been removed.
    monkeypatch.setattr(service, "generate_outcomes", forbidden_generation, raising=False)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            first = await service.ensure_outcomes_for_processing_result(
                db, result=result,
                ai_dispatch_planned=ai_dispatch_planned,
            )
            second = await service.ensure_outcomes_for_processing_result(
                db, result=result,
                ai_dispatch_planned=ai_dispatch_planned,
            )
            assert not invoked
            assert first.id == second.id
            assert first.protocol_json is None and first.content_hash is None
            assert first.protocol_schema_version == PROTOCOL_SCHEMA_VERSION
            assert first.protocol_state == ("processing" if ai_dispatch_planned else "unavailable")
            assert first.status == ("generating" if ai_dispatch_planned else "blocked")
            assert first.failure_reason == (None if ai_dispatch_planned else "summary_generation_unavailable")
            assert first.source_result_hash == result.source_result_hash
            assert first.source_fingerprint
            assert first.candidate_id is None
            assert first.generated_at is None
            assert first.generator_kind != "deterministic_extractive"
            for model in (MeetingOutcomeItem, MeetingOutcomeGenerationAttempt, MeetingSummarySlot):
                assert await db.scalar(select(func.count()).select_from(model).where(model.meeting_id == meeting_id)) == 0
            meeting = await db.get(Meeting, meeting_id)
            assert meeting.current_outcome_set_id is None
            await db.commit()

    asyncio.run(run())


def test_wait_reconciles_dispatch_state_but_never_becomes_generated_content(client):
    meeting_id = create_outcome_ready_meeting(client, "protocol-wait-transition")

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            outcome_id = None
            for planned in (False, True, False):
                outcome = await service.ensure_outcomes_for_processing_result(db, result=result, ai_dispatch_planned=planned)
                if outcome_id is None:
                    outcome_id = outcome.id
                assert outcome.id == outcome_id
                assert outcome.protocol_state == ("processing" if planned else "unavailable")
                assert outcome.protocol_json is None
                assert outcome.content_hash is None
                await db.commit()

    asyncio.run(run())


def test_terminal_no_speech_retains_source_reason_without_claiming_ai_is_running(client):
    meeting_id = create_outcome_ready_meeting(client, "protocol-no-speech")

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            result.transcript_status = "unavailable"
            result.diarization_status = "unavailable"
            result.segment_count = 0
            result.diarization_segment_count = 0
            result.failure_reason = "no_recognizable_speech"
            result.failure_source = "input_audio"
            outcome = await service.ensure_outcomes_for_processing_result(db, result=result, ai_dispatch_planned=True)
            assert outcome.protocol_state == "unavailable"
            assert outcome.failure_reason == result.failure_reason
            assert outcome.failure_source == result.failure_source
            assert outcome.protocol_json is None
            assert outcome.generated_at is None

    asyncio.run(run())


async def _seed_protocol(db, meeting_id):
    meeting = await db.get(Meeting, meeting_id)
    result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
    segments = await service.load_outcome_transcript_segments(db, result=result)
    document = {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "header": {"title": "Синтетический закреплённый заголовок"},
        **protocol_result(segments),
    }
    outcome = MeetingOutcomeSet(
        workspace_id=meeting.workspace_id, meeting_id=meeting.id,
        processing_result_id=result.id, media_revision_id=result.media_revision_id,
        status="available", revision_state="accepted", accepted_at=datetime.now(UTC),
        protocol_state="available", protocol_schema_version=PROTOCOL_SCHEMA_VERSION,
        protocol_json=document, content_hash=sha256(canonical_json(document).encode()).hexdigest(),
        source_result_hash=result.source_result_hash, generator_kind="litellm", generator_version="meeting-protocol-v2",
        source_kind="litellm",
        deletion_epoch_at_start=meeting.deletion_epoch or 0,
        template_key="graf-auto-v1", template_version=2,
    )
    db.add(outcome)
    await db.flush()
    slot = MeetingSummarySlot(
        workspace_id=meeting.workspace_id, meeting_id=meeting.id, template_key=outcome.template_key,
        current_outcome_set_id=outcome.id, current_binding_class="verified_complete",
        is_meeting_default=True, default_resolution_source="explicit_meeting",
        default_resolution_version="synthetic:1", default_resolved_at=datetime.now(UTC),
    )
    db.add(slot)
    meeting.current_outcome_set_id = outcome.id
    await db.commit()
    return meeting, result, outcome, slot


@pytest.mark.parametrize("scenario", [
    "accepted", "superseded", "flat", "wrong_schema", "wrong_document_schema", "bad_hash",
    "processing", "candidate", "missing_revision", "missing_acceptance", "source_hash",
    "missing_source_hash", "missing_result_hash", "synthetic_result_hash", "media_mismatch", "deleted", "epoch", "wrong_template",
])
def test_only_accepted_intact_protocols_can_leave_the_pinned_boundary(client, scenario):
    meeting_id = create_outcome_ready_meeting(client, "protocol-egress")

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            meeting, result, outcome, slot = await _seed_protocol(db, meeting_id)
            if scenario == "flat":
                outcome.protocol_json = None
            elif scenario == "wrong_schema":
                outcome.protocol_schema_version = "other"
            elif scenario == "wrong_document_schema":
                outcome.protocol_json = {**outcome.protocol_json, "schema_version": "other"}
                outcome.content_hash = sha256(canonical_json(outcome.protocol_json).encode()).hexdigest()
            elif scenario == "bad_hash":
                outcome.content_hash = "f" * 64
            elif scenario == "processing":
                outcome.protocol_state = "processing"
            elif scenario in {"candidate", "superseded"}:
                outcome.revision_state = scenario
            elif scenario == "missing_revision":
                outcome.revision_state = None
            elif scenario == "missing_acceptance":
                outcome.accepted_at = None
            elif scenario == "source_hash":
                outcome.source_result_hash = "different-source"
            elif scenario == "missing_source_hash":
                outcome.source_result_hash = None
            elif scenario in {"missing_result_hash", "synthetic_result_hash"}:
                legacy_hash = sha256(f"legacy-processing-result:{result.id}".encode()).hexdigest()
                result.source_result_hash = legacy_hash if scenario == "synthetic_result_hash" else None
                outcome.source_result_hash = legacy_hash
            elif scenario == "media_mismatch":
                outcome.media_revision_id = None
            elif scenario == "deleted":
                meeting.deleted_at = datetime.now(UTC)
            elif scenario == "epoch":
                meeting.deletion_epoch += 1
            await db.commit()
            key = "graf-outline-v1" if scenario == "wrong_template" else outcome.template_key
            pinned = await service.load_pinned_egress_outcome(
                db, meeting=meeting, template_key=key, outcome_set_id=outcome.id,
            )
            assert (pinned is not None) == (scenario in {"accepted", "superseded"})
            default = await service.load_egress_default_outcome(db, meeting=meeting, slot=slot)
            assert (default is not None) == (scenario in {"accepted", "wrong_template"})

    asyncio.run(run())


def test_wait_preserves_accepted_protocol_and_historical_flat_rows(client):
    meeting_id = create_outcome_ready_meeting(client, "protocol-preserve-history")

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            meeting, result, outcome, slot = await _seed_protocol(db, meeting_id)
            original = {column.name: getattr(outcome, column.name) for column in outcome.__table__.c}
            same = await service.ensure_outcomes_for_processing_result(db, result=result, ai_dispatch_planned=False)
            assert same.id == outcome.id
            assert {column.name: getattr(outcome, column.name) for column in outcome.__table__.c} == original
            # Old accepted data must not be reused, rewritten, or erased as a side effect of processing.
            outcome.protocol_json = None
            outcome.protocol_schema_version = None
            outcome.protocol_state = "unavailable"
            outcome.template_version = 1
            item = MeetingOutcomeItem(
                workspace_id=meeting.workspace_id, meeting_id=meeting.id, outcome_set_id=outcome.id,
                category="summary", sequence=1, text="Синтетический старый итог", source_refs_json=[],
            )
            db.add(item)
            await db.commit()
            await db.refresh(outcome)
            original = {column.name: getattr(outcome, column.name) for column in outcome.__table__.c}
            waiting = await service.ensure_outcomes_for_processing_result(db, result=result, ai_dispatch_planned=True)
            assert waiting.id != outcome.id and waiting.protocol_json is None
            assert {column.name: getattr(outcome, column.name) for column in outcome.__table__.c} == original
            assert slot.current_outcome_set_id == outcome.id
            assert meeting.current_outcome_set_id == outcome.id
            await db.refresh(item)
            assert item.text == "Синтетический старый итог"

    asyncio.run(run())


@pytest.mark.parametrize("changed_field", ["deletion", "source", "slot"])
def test_egress_rechecks_live_state_when_caller_has_stale_objects(client, changed_field):
    meeting_id = create_outcome_ready_meeting(client, "protocol-stale-deletion")

    async def run():
        async with client.app_state["sessionmaker"]() as reader:
            meeting, result, outcome, slot = await _seed_protocol(reader, meeting_id)
            original_source_hash = result.source_result_hash
            async with client.app_state["sessionmaker"]() as writer:
                if changed_field == "deletion":
                    changed = await writer.get(Meeting, meeting_id)
                    changed.deletion_state = "requested"
                    changed.deletion_epoch += 1
                elif changed_field == "slot":
                    changed = await writer.get(MeetingSummarySlot, slot.id)
                    changed.current_outcome_set_id = None
                    changed.current_binding_class = None
                else:
                    changed = await writer.get(ProcessingResult, result.id)
                    changed.source_result_hash = "changed-after-reader-load"
                await writer.commit()
            assert meeting.deletion_state == "none"
            assert result.source_result_hash == original_source_hash
            assert await service.load_egress_default_outcome(reader, meeting=meeting, slot=slot) is None

    asyncio.run(run())


def test_removed_store_has_no_flat_write_or_attempt_factory():
    for retired_name in ("replace_outcome_items", "record_generation_attempt", "category_states", "set_outcome_category_states"):
        assert not hasattr(store, retired_name)


def test_wait_never_invents_missing_source_hash(client):
    meeting_id = create_outcome_ready_meeting(client, "protocol-unattested-source")

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            result.source_result_hash = None
            outcome = await service.ensure_outcomes_for_processing_result(db, result=result, ai_dispatch_planned=True)
            assert result.source_result_hash is None
            assert outcome.protocol_state == "unavailable"
            assert outcome.protocol_json is None

    asyncio.run(run())
