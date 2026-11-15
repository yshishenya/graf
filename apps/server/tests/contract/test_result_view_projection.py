"""Each projected body keeps its own selected source, without ledger writes."""

from uuid import uuid4

import pytest
from sqlalchemy import select

from tests.contract.test_result_visibility import NOW, START, _run, _seed_source
from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
from twobrain_rec_server.cabinet.view_models import build_review_response
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    MeetingSummarySlot,
    ProcessingResult,
    ProductActivationMilestone,
    TranscriptSegment,
)


async def _seed_projection(db):
    meeting, revision, _, workflow, old, _ = await _seed_source(db)
    current = ProcessingResult(
        id=uuid4(), workspace_id=WORKSPACE_ID, meeting_id=meeting.id,
        media_revision_id=revision.id, processing_workflow_id=workflow.id,
        mediascribe_job_id=old.mediascribe_job_id, result_version=3, status="imported",
        transcript_status="available", segment_count=1,
        diarization_status="available", diarization_segment_count=1,
        deletion_epoch_at_start=0, imported_at=old.imported_at,
    )
    outcome = MeetingOutcomeSet(
        id=uuid4(), workspace_id=WORKSPACE_ID, meeting_id=meeting.id,
        media_revision_id=revision.id, processing_result_id=old.id,
        status="available", summary_state="available", deletion_epoch_at_start=0,
        generator_version="synthetic-pinned", lifecycle_state="active",
    )
    db.add_all([current, outcome])
    await db.flush()
    segment = TranscriptSegment(
        id=uuid4(), workspace_id=WORKSPACE_ID, meeting_id=meeting.id,
        processing_result_id=current.id, sequence=0, start_seconds=0, end_seconds=10,
        text="Тело расшифровки", source_role="canonical_mixed",
    )
    speaker = DiarizationSegment(
        id=uuid4(), workspace_id=WORKSPACE_ID, meeting_id=meeting.id,
        processing_result_id=current.id, sequence=0, start_seconds=0, end_seconds=10,
        speaker_label="SPEAKER_00", text="Тело расшифровки", source_role="canonical_mixed",
    )
    item = MeetingOutcomeItem(
        workspace_id=WORKSPACE_ID, meeting_id=meeting.id, outcome_set_id=outcome.id,
        category="summary", sequence=0, text="Тело закреплённых итогов", truth_label="supported",
    )
    db.add_all([segment, speaker, item])
    await db.commit()
    review = build_review_response(
        meeting, media_revision=revision, result=current, workflow=workflow,
        transcript_segments=[segment], diarization_segments=[speaker], dependency=None,
        outcome_set=outcome, outcome_items=[item],
    )
    return review, outcome, current, old


async def _bindings(db, review, **overrides):
    from twobrain_rec_server.cabinet.result_visibility import load_result_view_bindings

    params = dict(
        review=review, owner_id=USER_ID, workspace_id=WORKSPACE_ID,
        auth_session_id=uuid4(), session_device_id=None, started_at=START, now=NOW,
    )
    return await load_result_view_bindings(db, **(params | overrides))


def test_pinned_summary_and_newer_transcript_bind_their_own_result_without_audio_or_export(
    postgres_seeded_database_url,
):
    async def scenario(sessions):
        async with sessions() as db:
            review, outcome, current, old = await _seed_projection(db)
            assert review.content_exports is None and not review.playback.can_play
            bindings = await _bindings(db, review)
            assert set(bindings) == {"transcript:0", "outcome:summary:0"}
            transcript, summary = bindings["transcript:0"], bindings["outcome:summary:0"]
            assert (transcript.source.result_id, transcript.source.result_version) == (current.id, 3)
            assert (summary.source.result_id, summary.source.result_version) == (old.id, 2)
            assert transcript.outcome_set_id is None and summary.outcome_set_id == outcome.id
            assert transcript.source.first_recording_completed is False
            assert transcript.block_digest != summary.block_digest
            assert not db.new and not db.dirty
            assert (await db.scalars(select(ProductActivationMilestone))).all() == []
    _run(postgres_seeded_database_url, scenario)


def test_real_authorized_query_preserves_pinned_summary_instead_of_newer_unselected_output(
    postgres_seeded_database_url,
):
    from twobrain_rec_server.cabinet.queries import get_cabinet_meeting_review

    async def scenario(sessions):
        async with sessions() as db:
            review, pinned, current, old = await _seed_projection(db)
            pinned.template_key = "graf-auto-v1"
            pinned.template_version = 1
            pinned.revision_state = "accepted"
            db.add(MeetingOutcomeSet(
                workspace_id=WORKSPACE_ID, meeting_id=review.meeting.meeting_id,
                media_revision_id=review.provenance.media_revision_id, processing_result_id=current.id,
                status="available", summary_state="available", deletion_epoch_at_start=0,
                generator_version="synthetic-newer-unselected", lifecycle_state="active",
                template_key="graf-auto-v1", template_version=1, revision_state="accepted",
            ))
            await db.flush()
            db.add(MeetingSummarySlot(
                workspace_id=WORKSPACE_ID, meeting_id=review.meeting.meeting_id,
                template_key="graf-auto-v1", current_outcome_set_id=pinned.id,
                current_binding_class="verified_complete", is_meeting_default=True,
                default_resolution_source="explicit_meeting", default_resolution_version="synthetic",
                default_resolved_at=NOW,
            ))
            await db.commit()
            meeting_id, pinned_id, old_id, current_id = (
                review.meeting.meeting_id, pinned.id, old.id, current.id,
            )
        async with sessions() as db:
            authorized = await get_cabinet_meeting_review(
                db, workspace_id=WORKSPACE_ID, meeting_id=meeting_id, viewer_user_id=USER_ID,
            )
            assert authorized is not None and authorized.template.outcome_set_id == pinned_id
            bindings = await _bindings(db, authorized)
            assert bindings["outcome:summary:0"].source.result_id == old_id
            assert bindings["outcome:summary:0"].outcome_set_id == pinned_id
            assert bindings["transcript:0"].source.result_id == current_id
            assert (await db.scalars(select(ProductActivationMilestone))).all() == []
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("broken", [
    "missing", "other_meeting", "other_workspace", "other_revision", "inactive",
    "unavailable", "epoch", "result", "not_stored",
])
def test_bad_summary_binding_does_not_fall_back_to_the_transcript_or_another_result(
    postgres_seeded_database_url, broken,
):
    async def scenario(sessions):
        async with sessions() as db:
            review, outcome, current, old = await _seed_projection(db)
            if broken == "missing":
                review.template.outcome_set_id = uuid4()
            elif broken == "other_meeting":
                review.meeting.meeting_id = uuid4()
            elif broken == "other_workspace":
                overrides = {"workspace_id": uuid4()}
            elif broken == "other_revision":
                review.provenance.media_revision_id = uuid4()
            elif broken == "inactive":
                outcome.lifecycle_state = "deleted"
            elif broken == "unavailable":
                outcome.status = "failed"
            elif broken == "epoch":
                outcome.deletion_epoch_at_start = 1
            elif broken == "result":
                old.transcript_status = "unavailable"
            elif broken == "not_stored":
                review.notes_action_truth.source_basis = "processing_status"
            await db.commit()
            bindings = await _bindings(db, review, **(overrides if broken == "other_workspace" else {}))
            assert "outcome:summary:0" not in bindings
            if broken in {"other_meeting", "other_workspace", "other_revision"}:
                assert bindings == {}
            else:
                assert bindings["transcript:0"].source.result_id == current.id
            assert (await db.scalars(select(ProductActivationMilestone))).all() == []
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("broken", ["other_owner", "shared", "mixed_transcript", "unknown_start"])
def test_unknown_or_unauthorized_projection_never_creates_a_binding(
    postgres_seeded_database_url, broken,
):
    async def scenario(sessions):
        async with sessions() as db:
            review, _, _, _ = await _seed_projection(db)
            overrides = {}
            if broken == "other_owner":
                overrides["owner_id"] = uuid4()
            elif broken == "shared":
                review.access.state = "shared"
            elif broken == "mixed_transcript":
                review.transcript.speaker_turns[0].processing_result_id = uuid4()
            elif broken == "unknown_start":
                overrides["started_at"] = None
            bindings = await _bindings(db, review, **overrides)
            if broken == "mixed_transcript":
                assert "transcript:0" not in bindings
                assert set(bindings) == {"outcome:summary:0"}
            else:
                assert bindings == {}
    _run(postgres_seeded_database_url, scenario)
