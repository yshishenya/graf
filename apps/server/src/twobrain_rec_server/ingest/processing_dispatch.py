from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import Meeting
from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.ingest.store import (
    MeetingRecord,
    UploadSessionRecord,
    persist_upload_session,
)
from twobrain_rec_server.processing.pickup import pick_up_processing


@dataclass(frozen=True, slots=True)
class FinalizeProcessingDispatchResult:
    workflow_started: bool = False
    mediascribe_job_created: bool = False


async def dispatch_processing_after_finalize(
    *,
    db: AsyncSession | None,
    settings: Settings,
    tenant_scope: TenantScope,
    meeting: MeetingRecord,
    session: UploadSessionRecord,
    temporal_client: object | None = None,
) -> FinalizeProcessingDispatchResult:
    if not settings.processing_enabled or db is None:
        return FinalizeProcessingDispatchResult()

    result = await pick_up_processing(
        db=db,
        settings=settings,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        limit=1,
        temporal_client=temporal_client,
        tenant_scope=tenant_scope,
    )

    stored_meeting = await db.get(Meeting, meeting.id)
    if stored_meeting is not None:
        meeting.processing_status = ProcessingStatus(stored_meeting.processing_status)
        session.processing_status = meeting.processing_status
        await persist_upload_session(db, session, commit=False)

    return FinalizeProcessingDispatchResult(
        workflow_started=result.started_count > 0 or result.reused_count > 0,
        mediascribe_job_created=False,
    )
