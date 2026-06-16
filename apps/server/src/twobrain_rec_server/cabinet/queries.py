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
from twobrain_rec_server.cabinet.egress import activity_response, artifact_egress_states
from twobrain_rec_server.cabinet.view_models import build_list_item, build_review_response
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    Meeting,
    ProcessingDependencyState,
    ProcessingResult,
    ProcessingWorkflow,
    TranscriptSegment,
)


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
    query = select(Meeting).where(Meeting.workspace_id == workspace_id)
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
        workflow = await _latest_workflow(db, workspace_id=workspace_id, meeting_id=meeting.id)
        result = await _latest_result(db, workspace_id=workspace_id, meeting_id=meeting.id)
        artifacts = await artifact_egress_states(db, meeting=meeting, access=decision, result=result)
        item = build_list_item(
            meeting,
            result=result,
            workflow=workflow,
            access=decision.to_schema(),
            artifacts=artifacts,
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
    workflow = await _latest_workflow(db, workspace_id=workspace_id, meeting_id=meeting_id)
    result = await _latest_result(db, workspace_id=workspace_id, meeting_id=meeting_id)
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
        result=result,
        workflow=workflow,
        transcript_segments=transcript_segments,
        diarization_segments=diarization_segments,
        dependency=dependency,
        access=decision.to_schema(),
        share=await share_panel_state(db, meeting, decision),
        artifacts=await artifact_egress_states(db, meeting=meeting, access=decision, result=result),
        activity=await activity_response(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            viewer_user_id=viewer_user_id,
        ),
    )


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
) -> ProcessingWorkflow | None:
    return await db.scalar(
        select(ProcessingWorkflow)
        .where(
            ProcessingWorkflow.workspace_id == workspace_id,
            ProcessingWorkflow.meeting_id == meeting_id,
        )
        .order_by(ProcessingWorkflow.updated_at.desc())
    )


async def _latest_result(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> ProcessingResult | None:
    return await db.scalar(
        select(ProcessingResult)
        .where(
            ProcessingResult.workspace_id == workspace_id,
            ProcessingResult.meeting_id == meeting_id,
        )
        .order_by(ProcessingResult.imported_at.desc(), ProcessingResult.created_at.desc())
    )


async def latest_processing_result(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> ProcessingResult | None:
    return await _latest_result(db, workspace_id=workspace_id, meeting_id=meeting_id)
