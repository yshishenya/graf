from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, asc, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.schemas import (
    AccessState,
    MeetingFilterState,
    MeetingListResponse,
    MeetingReviewResponse,
    MeetingReviewStatus,
)
from twobrain_rec_server.cabinet.access import decide_meeting_access, share_panel_state
from twobrain_rec_server.cabinet.egress import (
    activity_response,
    artifact_egress_states,
    review_playback_state,
)
from twobrain_rec_server.cabinet.view_models import build_list_item, build_review_response
from twobrain_rec_server.db.models import (
    CalendarParticipant,
    DiarizationSegment,
    MediaRevision,
    Meeting,
    MeetingOutcomeSet,
    ProcessingDependencyState,
    ProcessingResult,
    ProcessingWorkflow,
    RecordingCalendarContextLink,
    TranscriptSegment,
)
from twobrain_rec_server.domain.statuses import DeletionState
from twobrain_rec_server.outcomes.service import load_outcome_items


async def list_cabinet_meetings(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    viewer_user_id: UUID,
    q: str | None = None,
    status: MeetingReviewStatus | None = None,
    access: AccessState | None = None,
    sort: str = "updated_desc",
    limit: int = 50,
) -> MeetingListResponse:
    query = select(Meeting).where(
        Meeting.workspace_id == workspace_id,
        or_(Meeting.deletion_state.is_(None), Meeting.deletion_state == DeletionState.NONE.value),
    )
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(or_(Meeting.title.ilike(pattern), Meeting.local_recording_id.ilike(pattern)))
    query = _apply_sort(query, sort)
    meetings = (await db.scalars(query)).all()

    items = []
    for meeting in meetings:
        decision = await decide_meeting_access(
            db,
            meeting,
            workspace_id=workspace_id,
            viewer_user_id=viewer_user_id,
        )
        if not decision.can_view:
            continue
        if access is not None and decision.state != access:
            continue
        media_revision = await _latest_media_revision(db, workspace_id=workspace_id, meeting_id=meeting.id)
        media_revision_id = media_revision.id if media_revision is not None else None
        workflow = await _latest_workflow(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting.id,
            media_revision_id=media_revision_id,
        )
        result = await _latest_result(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting.id,
            media_revision_id=media_revision_id,
        )
        outcome_set = await _latest_outcome_set(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting.id,
            processing_result_id=result.id if result is not None else None,
        )
        artifacts = await artifact_egress_states(db, meeting=meeting, access=decision, result=result)
        item = build_list_item(
            meeting,
            media_revision=media_revision,
            result=result,
            workflow=workflow,
            access=decision.to_schema(),
            artifacts=artifacts,
            outcome_set=outcome_set,
            outcome_items=[],
        )
        if status is not None and item.status != status:
            continue
        items.append(item)
        if len(items) >= limit:
            break
    return MeetingListResponse(
        items=items,
        filters=MeetingFilterState(q=q, status=status, access=access, sort=sort),
        generated_at=datetime.now(UTC),
    )


async def get_cabinet_meeting_review(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    viewer_user_id: UUID,
) -> MeetingReviewResponse | None:
    meeting = await db.scalar(
        select(Meeting).where(
            Meeting.workspace_id == workspace_id,
            Meeting.id == meeting_id,
        )
    )
    if meeting is None:
        return None
    decision = await decide_meeting_access(
        db,
        meeting,
        workspace_id=workspace_id,
        viewer_user_id=viewer_user_id,
    )
    if not decision.can_view:
        return None
    media_revision = await _latest_media_revision(db, workspace_id=workspace_id, meeting_id=meeting_id)
    media_revision_id = media_revision.id if media_revision is not None else None
    workflow = await _latest_workflow(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
    )
    result = await _latest_result(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
    )
    transcript_segments: list[TranscriptSegment] = []
    diarization_segments: list[DiarizationSegment] = []
    if result is not None:
        transcript_segments = (
            await db.scalars(
                select(TranscriptSegment)
                .where(
                    TranscriptSegment.workspace_id == workspace_id,
                    TranscriptSegment.meeting_id == meeting_id,
                    TranscriptSegment.processing_result_id == result.id,
                )
                .order_by(TranscriptSegment.sequence.asc(), TranscriptSegment.start_seconds.asc())
            )
        ).all()
        diarization_segments = (
            await db.scalars(
                select(DiarizationSegment)
                .where(
                    DiarizationSegment.workspace_id == workspace_id,
                    DiarizationSegment.meeting_id == meeting_id,
                    DiarizationSegment.processing_result_id == result.id,
                )
                .order_by(DiarizationSegment.sequence.asc(), DiarizationSegment.start_seconds.asc())
            )
        ).all()
    outcome_set = await _latest_outcome_set(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        processing_result_id=result.id if result is not None else None,
    )
    dependency = await db.scalar(
        select(ProcessingDependencyState)
        .where(
            ProcessingDependencyState.workspace_id == workspace_id,
            ProcessingDependencyState.meeting_id == meeting_id,
        )
        .order_by(ProcessingDependencyState.updated_at.desc())
    )
    return build_review_response(
        meeting,
        media_revision=media_revision,
        result=result,
        workflow=workflow,
        transcript_segments=transcript_segments,
        diarization_segments=diarization_segments,
        dependency=dependency,
        access=decision.to_schema(),
        share=await share_panel_state(db, meeting, decision),
        artifacts=await artifact_egress_states(db, meeting=meeting, access=decision, result=result),
        review_playback=await review_playback_state(db, meeting=meeting, access=decision, result=result),
        calendar_roster=await _calendar_roster_state(db, workspace_id=workspace_id, meeting_id=meeting_id),
        activity=await activity_response(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            viewer_user_id=viewer_user_id,
        ),
        outcome_set=outcome_set,
        outcome_items=await load_outcome_items(db, outcome_set=outcome_set),
    )


async def _calendar_roster_state(db: AsyncSession, *, workspace_id: UUID, meeting_id: UUID):
    link = await db.scalar(
        select(RecordingCalendarContextLink).where(
            RecordingCalendarContextLink.workspace_id == workspace_id,
            RecordingCalendarContextLink.meeting_id == meeting_id,
            RecordingCalendarContextLink.unlinked_at.is_(None),
        )
    )
    if link is None:
        return None
    participants = (
        await db.scalars(
            select(CalendarParticipant)
            .where(
                CalendarParticipant.workspace_id == workspace_id,
                CalendarParticipant.calendar_event_snapshot_id == link.calendar_event_snapshot_id,
            )
            .order_by(
                CalendarParticipant.participant_kind.asc(),
                CalendarParticipant.display_name.asc(),
            )
        )
    ).all()
    from twobrain_rec_server.cabinet.view_models import calendar_roster_state

    return calendar_roster_state(participants)


def _apply_sort(query: Select[tuple[Meeting]], sort: str) -> Select[tuple[Meeting]]:
    sorters = {
        "updated_desc": desc(Meeting.updated_at),
        "updated_asc": asc(Meeting.updated_at),
        "started_desc": desc(Meeting.started_at),
        "started_asc": asc(Meeting.started_at),
        "duration_desc": desc(Meeting.duration_seconds),
        "duration_asc": asc(Meeting.duration_seconds),
    }
    return query.order_by(sorters.get(sort, desc(Meeting.updated_at)), desc(Meeting.created_at))


async def _latest_workflow(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None = None,
) -> ProcessingWorkflow | None:
    query = select(ProcessingWorkflow).where(
            ProcessingWorkflow.workspace_id == workspace_id,
            ProcessingWorkflow.meeting_id == meeting_id,
    )
    if media_revision_id is not None:
        query = query.where(ProcessingWorkflow.media_revision_id == media_revision_id)
    return await db.scalar(query.order_by(ProcessingWorkflow.updated_at.desc()))


async def _latest_result(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID | None = None,
) -> ProcessingResult | None:
    query = select(ProcessingResult).where(
            ProcessingResult.workspace_id == workspace_id,
            ProcessingResult.meeting_id == meeting_id,
    )
    if media_revision_id is not None:
        query = query.where(ProcessingResult.media_revision_id == media_revision_id)
    return await db.scalar(query.order_by(ProcessingResult.imported_at.desc(), ProcessingResult.created_at.desc()))


async def _latest_media_revision(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> MediaRevision | None:
    return await db.scalar(
        select(MediaRevision)
        .where(
            MediaRevision.workspace_id == workspace_id,
            MediaRevision.meeting_id == meeting_id,
        )
        .order_by(MediaRevision.revision_number.desc(), MediaRevision.updated_at.desc())
    )


async def _latest_outcome_set(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    processing_result_id: UUID | None,
) -> MeetingOutcomeSet | None:
    if processing_result_id is None:
        return None
    return await db.scalar(
        select(MeetingOutcomeSet)
        .where(
            MeetingOutcomeSet.workspace_id == workspace_id,
            MeetingOutcomeSet.meeting_id == meeting_id,
            MeetingOutcomeSet.processing_result_id == processing_result_id,
            MeetingOutcomeSet.lifecycle_state == "active",
        )
        .order_by(MeetingOutcomeSet.generated_at.desc(), MeetingOutcomeSet.created_at.desc())
    )


async def latest_processing_result(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> ProcessingResult | None:
    media_revision = await _latest_media_revision(db, workspace_id=workspace_id, meeting_id=meeting_id)
    return await _latest_result(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision.id if media_revision is not None else None,
    )
