from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    AbortUploadRequest,
    CreateMeetingRequest,
    CreateUploadSessionRequest,
    DesktopRecordingSyncStateResponse,
    FinalizeUploadRequest,
    FinalizeUploadResponse,
    MediaRevisionSummary,
    MeetingResponse,
    MissingRange,
    MissingRangesResponse,
    Problem,
    UploadPartResponse,
    UploadSessionResponse,
)
from twobrain_rec_server.api.upload_stream import read_bounded_upload_body
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.auth.dependencies import (
    get_device_context,
    get_principal,
    get_tenant_scope,
)
from twobrain_rec_server.db.tenant_context import apply_tenant_scope
from twobrain_rec_server.domain.statuses import TrackRole
from twobrain_rec_server.ingest.desktop_status import upload_session_desktop_status
from twobrain_rec_server.ingest.desktop_sync import get_desktop_recording_sync_state
from twobrain_rec_server.ingest.finalize import finalize_upload
from twobrain_rec_server.ingest.lifecycle import abort_upload_session
from twobrain_rec_server.ingest.meetings import create_or_get_meeting
from twobrain_rec_server.ingest.parts import accept_part
from twobrain_rec_server.ingest.policy import IngestLimitViolation
from twobrain_rec_server.ingest.processing_dispatch import dispatch_processing_after_finalize
from twobrain_rec_server.ingest.ranges import missing_ranges_for_expected_sizes
from twobrain_rec_server.ingest.sessions import create_upload_session
from twobrain_rec_server.ingest.status import get_upload_session_status
from twobrain_rec_server.storage.minio_client import get_storage

PROBLEM_RESPONSES = {
    400: {"model": Problem, "description": "Bad request"},
    401: {"model": Problem, "description": "Unauthorized"},
    403: {"model": Problem, "description": "Forbidden"},
    404: {"model": Problem, "description": "Not found"},
    409: {"model": Problem, "description": "Conflict"},
    413: {"model": Problem, "description": "Payload too large"},
    422: {"model": Problem, "description": "Validation error"},
    503: {"model": Problem, "description": "Dependency unavailable"},
}

router = APIRouter(prefix="/api/v1", tags=["ingest"], responses=PROBLEM_RESPONSES)


TenantDependency = Depends(get_tenant_scope)
PrincipalDependency = Depends(get_principal)
DeviceDependency = Depends(get_device_context)


async def get_request_db_session(
    request: Request,
    tenant_scope: TenantScope = TenantDependency,
):
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        yield None
        return
    async with sessionmaker() as session:
        await apply_tenant_scope(session, tenant_scope)
        yield session


def get_request_storage(request: Request) -> object:
    storage = getattr(request.app.state, "storage", None)
    if storage is None:
        storage = get_storage(request.app.state.settings)
        request.app.state.storage = storage
    return storage


DbDependency = Depends(get_request_db_session)
StorageDependency = Depends(get_request_storage)


async def commit_if_available(db: AsyncSession | None) -> None:
    if db is not None:
        await db.commit()


def meeting_response(meeting: object) -> MeetingResponse:
    media_revision = MediaRevisionSummary(
        media_revision_id=meeting.media_revision_id,
        local_media_revision_id=meeting.local_media_revision_id,
        revision_number=1,
        source_kind=meeting.media_revision_source_kind,
        status=meeting.media_revision_status,
    )
    return MeetingResponse(
        meeting_id=meeting.id,
        workspace_id=meeting.workspace_id,
        local_recording_id=meeting.local_recording_id,
        local_media_revision_id=meeting.local_media_revision_id,
        media_revision=media_revision,
        status=meeting.status,
        processing_status=meeting.processing_status,
        started_at=meeting.started_at,
        ended_at=meeting.ended_at,
        recording_display_timezone_offset_minutes=meeting.recording_display_timezone_offset_minutes,
        created_at=meeting.created_at,
    )


def session_response(session: object) -> UploadSessionResponse:
    accepted: dict[str, int] = {}
    for (role, _part_number), part in session.parts.items():
        accepted[role.value] = accepted.get(role.value, 0) + part.byte_length
    desktop = upload_session_desktop_status(session.status)
    return UploadSessionResponse(
        session_id=session.id,
        meeting_id=session.meeting_id,
        media_revision_id=session.media_revision_id,
        status=session.status,
        upload_strategy=session.upload_strategy,
        expires_at=session.expires_at,
        accepted_bytes_by_track=accepted,
        processing_status=session.processing_status,
        desktop_label=desktop.label,
        desktop_truth_rule=desktop.truth_rule,
    )


@router.post("/meetings", response_model=MeetingResponse, dependencies=[PrincipalDependency, DeviceDependency])
async def create_meeting(
    payload: CreateMeetingRequest,
    request: Request,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> MeetingResponse:
    try:
        meeting = await create_or_get_meeting(
            settings=request.app.state.settings,
            tenant_scope=tenant_scope,
            db=db,
            local_recording_id=payload.local_recording_id,
            local_media_revision_id=payload.local_media_revision_id,
            duration_seconds=payload.duration_seconds,
            title=payload.title,
            started_at=payload.started_at,
            ended_at=payload.ended_at,
            recording_display_timezone_offset_minutes=payload.recording_display_timezone_offset_minutes,
        )
    except IngestLimitViolation as exc:
        raise ProblemDetail(
            status=400,
            code=exc.code,
            title="Ingest limit exceeded",
            detail=f"{exc.limit_name}={exc.limit_value}, actual={exc.actual_value}",
        ) from exc
    await commit_if_available(db)
    return meeting_response(meeting)


@router.get(
    "/desktop/recordings/{local_recording_id}/sync-state",
    response_model=DesktopRecordingSyncStateResponse,
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def get_recording_sync_state(
    local_recording_id: str,
    local_media_revision_id: str | None = Query(default=None),
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> DesktopRecordingSyncStateResponse:
    return await get_desktop_recording_sync_state(
        tenant_scope=tenant_scope,
        db=db,
        local_recording_id=local_recording_id,
        local_media_revision_id=local_media_revision_id,
    )


@router.post(
    "/meetings/{meeting_id}/upload-sessions",
    response_model=UploadSessionResponse,
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def create_session(
    meeting_id: UUID,
    payload: CreateUploadSessionRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> UploadSessionResponse:
    session = await create_upload_session(
        settings=request.app.state.settings,
        tenant_scope=tenant_scope,
        db=db,
        meeting_id=meeting_id,
        expected_track_roles=payload.expected_tracks,
        expected_track_sizes=payload.expected_track_sizes,
        idempotency_key=idempotency_key,
    )
    await commit_if_available(db)
    return session_response(session)


@router.put(
    "/upload-sessions/{session_id}/tracks/{track_role}/parts/{part_number}",
    response_model=UploadPartResponse,
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def put_part(
    session_id: UUID,
    track_role: TrackRole,
    part_number: int,
    request: Request,
    x_byte_offset: int = Header(alias="X-Byte-Offset"),
    x_content_sha256: str = Header(alias="X-Content-SHA256"),
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
    storage: object = StorageDependency,
) -> UploadPartResponse:
    data = await read_bounded_upload_body(
        request,
        expected_sha256=x_content_sha256,
        max_bytes=request.app.state.settings.max_upload_part_bytes,
        spool_memory_bytes=request.app.state.settings.max_upload_spool_memory_bytes,
    )
    part = await accept_part(
        settings=request.app.state.settings,
        tenant_scope=tenant_scope,
        db=db,
        storage=storage,
        session_id=session_id,
        track_role=track_role,
        part_number=part_number,
        byte_offset=x_byte_offset,
        content_sha256=x_content_sha256,
        data=data,
    )
    await commit_if_available(db)
    return UploadPartResponse(
        session_id=session_id,
        track_role=part.track_role,
        part_number=part.part_number,
        byte_offset=part.byte_offset,
        byte_length=part.byte_length,
        sha256=part.sha256,
    )


@router.get(
    "/upload-sessions/{session_id}",
    response_model=UploadSessionResponse,
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def get_session(
    session_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> UploadSessionResponse:
    return session_response(await get_upload_session_status(session_id, tenant_scope, db))


@router.get(
    "/upload-sessions/{session_id}/missing-ranges",
    response_model=MissingRangesResponse,
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def get_missing_ranges(
    session_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> MissingRangesResponse:
    session = await get_upload_session_status(session_id, tenant_scope, db)
    expected = session.expected_track_sizes or {
        role: sum(part.byte_length for (part_role, _), part in session.parts.items() if part_role == role)
        for role in session.expected_track_roles
    }
    ranges = missing_ranges_for_expected_sizes(session, expected)
    return MissingRangesResponse(
        session_id=session.id,
        missing_ranges_by_track={
            role: [MissingRange(start=start, end=end) for start, end in role_ranges]
            for role, role_ranges in ranges.items()
            if role_ranges
        },
    )


@router.post(
    "/upload-sessions/{session_id}/abort",
    response_model=UploadSessionResponse,
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def abort_session(
    session_id: UUID,
    payload: AbortUploadRequest,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
) -> UploadSessionResponse:
    session = await abort_upload_session(tenant_scope=tenant_scope, db=db, session_id=session_id, reason=payload.reason)
    await commit_if_available(db)
    return session_response(session)


@router.post(
    "/upload-sessions/{session_id}/finalize",
    response_model=FinalizeUploadResponse,
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def finalize_session(
    session_id: UUID,
    payload: FinalizeUploadRequest,
    request: Request,
    tenant_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = DbDependency,
    storage: object = StorageDependency,
) -> FinalizeUploadResponse:
    meeting, session = await finalize_upload(
        tenant_scope=tenant_scope,
        db=db,
        session_id=session_id,
        manifest_sha256=payload.manifest_sha256,
        tracks=payload.tracks,
        storage=storage,
    )
    processing = await dispatch_processing_after_finalize(
        db=db,
        settings=request.app.state.settings,
        tenant_scope=tenant_scope,
        meeting=meeting,
        session=session,
        temporal_client=getattr(request.app.state, "temporal_client", None),
    )
    await commit_if_available(db)
    return FinalizeUploadResponse(
        meeting=meeting_response(meeting),
        upload_session=session_response(session),
        object_count=len(session.parts),
        workflow_started=processing.workflow_started,
        mediascribe_job_created=processing.mediascribe_job_created,
    )
