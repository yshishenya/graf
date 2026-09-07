from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from tests.fixtures.cabinet import create_outcome_ready_meeting
from tests.fixtures.postgres_test_database import prepare_schema
from twobrain_rec_server.cli.meeting_protocol_eval import (
    mirror_source,
    purge_shadow_source,
    snapshot_source,
)
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    GenerationCall,
    MediaRevision,
    MediaScribeJob,
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeSet,
    MeetingSpeakerName,
    MeetingSummarySlot,
    ProcessingResult,
    ProcessingWorkflow,
    TrackArtifact,
    TranscriptSegment,
    UserIdentity,
    WorkspaceMembership,
)
from twobrain_rec_server.outcomes.ai_service import OutcomeGenerationTerminalError
from twobrain_rec_server.outcomes.generator import canonical_transcript
from twobrain_rec_server.outcomes.service import load_outcome_transcript_segments


@pytest.mark.parametrize("partial", [False, True])
@pytest.mark.parametrize("source_only", [False, True])
def test_readonly_snapshot_mirrors_into_separate_migrated_database(
    client, postgres_clean_database_url, partial, source_only
):
    meeting_id = create_outcome_ready_meeting(client, f"synthetic-evaluation-{partial}")
    prepare_schema(postgres_clean_database_url)

    async def run():
        source_sessions = client.app_state["sessionmaker"]
        async with source_sessions() as db:
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            original_user = (await db.get(Meeting, meeting_id)).created_by_user_id
            result.downloads_json = {"transcript": "https://private.invalid/synthetic-secret"}
            result.provenance_json = {"private": "synthetic-secret"}
            for row in (
                await db.scalars(
                    select(DiarizationSegment).where(DiarizationSegment.meeting_id == meeting_id)
                )
            ).all():
                row.words_json = [
                    {
                        "word": row.text,
                        "start": float(row.start_seconds),
                        "end": float(row.end_seconds),
                    }
                ]
            if partial:
                result.diarization_status = "unavailable"
                result.diarization_segment_count = 0
                for row in (
                    await db.scalars(
                        select(DiarizationSegment).where(
                            DiarizationSegment.meeting_id == meeting_id
                        )
                    )
                ).all():
                    await db.delete(row)
            db.add(
                MeetingSpeakerName(
                    workspace_id=result.workspace_id,
                    meeting_id=meeting_id,
                    speaker_key="mic",
                    display_name="Синтетическое имя",
                    updated_by_user_id=original_user,
                    updated_at=datetime.now(UTC),
                )
            )
            await db.commit()
        readonly = create_async_engine(
            str(client.app_state["engine"].url.render_as_string(hide_password=False)),
            poolclass=NullPool,
            isolation_level="REPEATABLE READ",
            connect_args={"server_settings": {"default_transaction_read_only": "on"}},
        )
        statements = []
        event.listen(
            readonly.sync_engine,
            "before_cursor_execute",
            lambda _c, _cu, stmt, _p, _ct, _m: statements.append(stmt),
        )
        shadow = create_async_engine(
            postgres_clean_database_url, poolclass=NullPool, hide_parameters=True
        )
        try:
            async with async_sessionmaker(readonly, autoflush=False)() as db:
                assert await db.scalar(text("SHOW transaction_read_only")) == "on"
                snapshot = await snapshot_source(db, meeting_id)
                inventory = await snapshot_source(db)
                assert len(inventory) == 1
                assert set(inventory[0]) == {"meeting_id", "selection_status", "source_hash"}
                assert snapshot["selection_status"] == ("partial" if partial else "available")
                serialized = json.dumps(snapshot)
                assert "synthetic-secret" not in serialized
                assert "downloads_json" not in serialized and "provenance_json" not in serialized
                assert "updated_by_user_id" not in serialized and "device_id" not in serialized
                assert snapshot["access"] == {"owner_active": True, "membership_active": True}
                assert "UserIdentity" not in snapshot["rows"]
                assert "LIMIT" not in " ".join(statements)
                assert not any(
                    sql.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
                    for sql in statements
                )
            async with async_sessionmaker(shadow, expire_on_commit=False)() as db:
                run_id = uuid4()
                if source_only:
                    meeting = await mirror_source(db, snapshot, run_id, create_attempt=False)
                    assert meeting.id == meeting_id
                    assert meeting.created_by_user_id != original_user
                    for model in (MeetingOutcomeGenerationAttempt, GenerationCall, MeetingSummarySlot):
                        assert await db.scalar(select(func.count()).select_from(model)) == 0
                    assert meeting.current_outcome_set_id is None
                    result = await db.scalar(select(ProcessingResult))
                    assert canonical_transcript(
                        await load_outcome_transcript_segments(db, result=result)
                    ) == snapshot["canonical_transcript"]
                    await db.commit()
                    return
                attempt = await mirror_source(db, snapshot, run_id)
                assert attempt.metadata_json["evaluation_only"] is True
                assert attempt.metadata_json["evaluation_source"] == {
                    "meeting_id": str(meeting_id),
                    "snapshot_hash": snapshot["source_hash"],
                }
                assert attempt.requested_by_user_id != original_user
                assert attempt.status == "queued"
                assert await db.get(UserIdentity, original_user) is None
                assert await db.scalar(select(func.count()).select_from(TrackArtifact)) == 0
                result = await db.get(ProcessingResult, attempt.source_result_id)
                assert result.downloads_json is None and result.provenance_json is None
                assert (
                    await db.scalar(select(TranscriptSegment))
                ).source_role_original == snapshot["rows"]["TranscriptSegment"][0][
                    "source_role_original"
                ]
                if not partial:
                    assert (await db.scalar(select(DiarizationSegment))).words_json == snapshot[
                        "rows"
                    ]["DiarizationSegment"][0]["words_json"]
                assert (
                    canonical_transcript(await load_outcome_transcript_segments(db, result=result))
                    == snapshot["canonical_transcript"]
                )
                slot = await db.scalar(select(MeetingSummarySlot))
                assert slot.current_outcome_set_id is None
                assert (await db.get(Meeting, meeting_id)).current_outcome_set_id is None
                await db.commit()
                with pytest.raises(
                    OutcomeGenerationTerminalError, match="evaluation_shadow_source_exists"
                ):
                    await mirror_source(db, snapshot, run_id)
                attempt.header_snapshot_json = {"title": "Синтетическая шапка"}
                attempt.prompt_definition = {"synthetic": "retained prompt"}
                attempt.metadata_json = {
                    **attempt.metadata_json,
                    "prompt_bundle": {"synthetic": True},
                    "verifier_prompt": {"synthetic": "retained verifier"},
                }
                original_metadata = dict(attempt.metadata_json)
                outcome = MeetingOutcomeSet(
                    workspace_id=attempt.workspace_id,
                    meeting_id=meeting_id,
                    processing_result_id=attempt.source_result_id,
                    generator_version="synthetic-evaluation",
                    source_kind="synthetic",
                    generator_kind="synthetic",
                    protocol_json={"synthetic": "private output"},
                    protocol_state="available",
                    content_hash="a" * 64,
                )
                call = GenerationCall(
                    workspace_id=attempt.workspace_id,
                    meeting_id=meeting_id,
                    candidate_id=attempt.candidate_id,
                    provider_attempt=1,
                    call_sequence=1,
                    trace_id=uuid4().hex,
                    observation_id=uuid4().hex,
                    call_state="completed",
                    started_at=datetime.now(UTC),
                    transcript_text=snapshot["canonical_transcript"],
                    request_json={"synthetic": "private request"},
                    raw_response_json={"synthetic": "private response"},
                    validated_result_json={"synthetic": "private result"},
                )
                db.add_all([outcome, call])
                await db.commit()
                call_before = {
                    column.name: getattr(call, column.name) for column in call.__table__.columns
                }
                await purge_shadow_source(db, meeting_id)
                await db.commit()
                epoch = (await db.get(Meeting, meeting_id)).deletion_epoch
                await purge_shadow_source(db, meeting_id)
                await db.commit()
                assert (await db.get(Meeting, meeting_id)).deletion_epoch == epoch
                assert (await db.get(Meeting, meeting_id)).title is None
                for model in (TranscriptSegment, DiarizationSegment, MeetingSpeakerName):
                    assert await db.scalar(select(func.count()).select_from(model)) == 0
                assert outcome.protocol_json is None and outcome.protocol_state == "unavailable"
                assert attempt.header_snapshot_json is None and attempt.status == "cancelled"
                assert attempt.metadata_json == {**original_metadata, "purged_for_deletion": True}
                assert attempt.prompt_definition == {"synthetic": "retained prompt"}
                await db.refresh(call)
                assert {
                    column.name: getattr(call, column.name) for column in call.__table__.columns
                } == call_before
            async with source_sessions() as db:
                assert (
                    await db.scalar(
                        select(func.count()).select_from(MeetingOutcomeGenerationAttempt)
                    )
                    == 0
                )
                assert await db.scalar(select(func.count()).select_from(MeetingSummarySlot)) == 0
                assert (await snapshot_source(db, meeting_id))["source_hash"] == snapshot[
                    "source_hash"
                ]
        finally:
            await shadow.dispose()
            await readonly.dispose()

    asyncio.run(run())


@pytest.mark.parametrize(
    "mutation",
    [
        "source",
        "owner",
        "access",
        "deletion",
        "title",
        "speaker",
        "revision",
        "owner_disabled",
        "membership_revoked",
    ],
)
def test_snapshot_fences_all_mutable_source_inputs(client, mutation):
    meeting_id = create_outcome_ready_meeting(client, f"synthetic-fence-{mutation}")

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            before = await snapshot_source(db, meeting_id)
            meeting = await db.get(Meeting, meeting_id)
            if mutation == "source":
                segment = await db.scalar(
                    select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id)
                )
                segment.text += " Синтетическая поправка."
            elif mutation == "owner":
                owner = await db.get(UserIdentity, meeting.created_by_user_id)
                new_owner = UserIdentity(
                    organization_id=owner.organization_id, external_subject="synthetic-new-owner"
                )
                db.add(new_owner)
                await db.flush()
                meeting.created_by_user_id = new_owner.id
            elif mutation == "access":
                meeting.visibility = "workspace"
            elif mutation == "deletion":
                meeting.deletion_epoch += 1
                meeting.deletion_state = "requested"
            elif mutation == "title":
                meeting.title = "Новое синтетическое название"
                meeting.title_updated_at = datetime.now(UTC)
            elif mutation == "speaker":
                db.add(
                    MeetingSpeakerName(
                        workspace_id=meeting.workspace_id,
                        meeting_id=meeting.id,
                        updated_by_user_id=meeting.created_by_user_id,
                        speaker_key="synthetic",
                        display_name="Синтетик",
                    )
                )
            elif mutation == "owner_disabled":
                (await db.get(UserIdentity, meeting.created_by_user_id)).status = "disabled"
            elif mutation == "membership_revoked":
                (
                    await db.get(
                        WorkspaceMembership, (meeting.workspace_id, meeting.created_by_user_id)
                    )
                ).status = "revoked"
            else:
                db.add(
                    MediaRevision(
                        workspace_id=meeting.workspace_id,
                        meeting_id=meeting.id,
                        local_media_revision_id="synthetic-new-revision",
                        revision_number=2,
                        status="accepted",
                        immutable=True,
                    )
                )
            await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            after = await snapshot_source(db, meeting_id)
            assert after["source_hash"] != before["source_hash"]
            if mutation == "deletion":
                assert after["selection_status"] == "deleted"
                assert after["canonical_transcript"] == "[]"
                assert after["rows"]["TranscriptSegment"] == []
            if mutation == "revision":
                assert after["selection_status"] == "source_unavailable"
                assert after["rows"]["ProcessingResult"] == []
            if mutation in {"owner_disabled", "membership_revoked"}:
                assert after["selection_status"] == "inaccessible"
                assert after["canonical_transcript"] == "[]"
                assert after["rows"]["TranscriptSegment"] == []
                assert "title" not in after["rows"]["Meeting"][0]
                assert (
                    after["rows"]["Meeting"][0]["updated_at"]
                    == before["rows"]["Meeting"][0]["updated_at"]
                )

    asyncio.run(run())


def test_canonical_latest_selection_uses_workflow_lineage_not_max_result_version(client):
    meeting_id = create_outcome_ready_meeting(client, "synthetic-latest-lineage")

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            old = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            old.result_version = 99
            workflow = ProcessingWorkflow(
                workspace_id=old.workspace_id,
                meeting_id=meeting_id,
                media_revision_id=old.media_revision_id,
                workflow_id=f"synthetic:{uuid4()}",
                status="processed",
                attempt_ordinal=2,
            )
            db.add(workflow)
            await db.flush()
            job = MediaScribeJob(
                workspace_id=old.workspace_id,
                meeting_id=meeting_id,
                media_revision_id=old.media_revision_id,
                processing_workflow_id=workflow.id,
            )
            db.add(job)
            await db.flush()
            latest = ProcessingResult(
                workspace_id=old.workspace_id,
                meeting_id=meeting_id,
                media_revision_id=old.media_revision_id,
                processing_workflow_id=workflow.id,
                mediascribe_job_id=job.id,
                status="imported",
                result_version=1,
                imported_at=datetime.now(UTC) + timedelta(seconds=1),
            )
            db.add(latest)
            await db.commit()
            snapshot = await snapshot_source(db, meeting_id)
            assert snapshot["rows"]["ProcessingResult"][0]["id"] == str(latest.id)
            assert snapshot["selection_status"] == "transcript_unavailable"
            assert (await snapshot_source(db, UUID(int=1)))["selection_status"] == "inaccessible"

    asyncio.run(run())
