from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request

from twobrain_rec_server.api.schemas import (
    CreateMeetingRequest,
    CreateUploadSessionRequest,
    AbortUploadRequest,
    FinalizeUploadRequest,
    FinalizeUploadResponse,
    MissingRange,
    MissingRangesResponse,
    MeetingResponse,
    UploadPartResponse,
    UploadSessionResponse,
)
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.auth.dependencies import get_device_context, get_principal, get_tenant_scope
from twobrain_rec_server.domain.statuses import TrackRole
from twobrain_rec_server.ingest.finalize import finalize_upload
from twobrain_rec_server.ingest.desktop_status import upload_session_desktop_status
from twobrain_rec_server.ingest.lifecycle import abort_upload_session
from twobrain_rec_server.ingest.meetings import create_or_get_meeting
from twobrain_rec_server.ingest.parts import accept_part
from twobrain_rec_server.ingest.policy import IngestLimitViolation
from twobrain_rec_server.ingest.ranges import missing_ranges_for_expected_sizes
from twobrain_rec_server.ingest.sessions import create_upload_session
from twobrain_rec_server.ingest.status import get_upload_session_status

router = APIRouter(prefix="/api/v1", tags=["ingest"])


TenantDependency = Depends(get_tenant_scope)
PrincipalDependency = Depends(get_principal)
DeviceDependency = Depends(get_device_context)


def meeting_response(meeting: object) -> MeetingResponse:
    return MeetingResponse(
        meeting_id=meeting.id,
        workspace_id=meeting.workspace_id,
        local_recording_id=meeting.local_recording_id,
        status=meeting.status,
        processing_status=meeting.processing_status,
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
) -> MeetingResponse:
    try:
        meeting = create_or_get_meeting(
            settings=request.app.state.settings,
            tenant_scope=tenant_scope,
            local_recording_id=payload.local_recording_id,
            duration_seconds=payload.duration_seconds,
            title=payload.title,
        )
    except IngestLimitViolation as exc:
        from twobrain_rec_server.api.problems import ProblemDetail

        raise ProblemDetail(
            status=400,
            code=exc.code,
            title="Ingest limit exceeded",
            detail=f"{exc.limit_name}={exc.limit_value}, actual={exc.actual_value}",
        ) from exc
    return meeting_response(meeting)


@router.post(
    "/meetings/{meeting_id}/upload-sessions",
    response_model=UploadSessionResponse,
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def create_session(
    meeting_id: UUID,
    _payload: CreateUploadSessionRequest,
    request: Request,
    tenant_scope: TenantScope = TenantDependency,
) -> UploadSessionResponse:
    session = create_upload_session(
        settings=request.app.state.settings,
        tenant_scope=tenant_scope,
        meeting_id=meeting_id,
    )
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
) -> UploadPartResponse:
    data = await request.body()
    part = accept_part(
        settings=request.app.state.settings,
        tenant_scope=tenant_scope,
        session_id=session_id,
        track_role=track_role,
        part_number=part_number,
        byte_offset=x_byte_offset,
        content_sha256=x_content_sha256,
        data=data,
    )
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
) -> UploadSessionResponse:
    return session_response(get_upload_session_status(session_id, tenant_scope))


@router.get(
    "/upload-sessions/{session_id}/missing-ranges",
    response_model=MissingRangesResponse,
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def get_missing_ranges(
    session_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
) -> MissingRangesResponse:
    session = get_upload_session_status(session_id, tenant_scope)
    expected = {role: sum(part.byte_length for (part_role, _), part in session.parts.items() if part_role == role) for role, _ in session.parts}
    ranges = missing_ranges_for_expected_sizes(session, expected)
    return MissingRangesResponse(
        session_id=session.id,
        missing_ranges_by_track={
            role: [MissingRange(start=start, end=end) for start, end in role_ranges]
            for role, role_ranges in ranges.items()
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
) -> UploadSessionResponse:
    return session_response(
        abort_upload_session(tenant_scope=tenant_scope, session_id=session_id, reason=payload.reason)
    )


@router.post(
    "/upload-sessions/{session_id}/finalize",
    response_model=FinalizeUploadResponse,
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def finalize_session(
    session_id: UUID,
    payload: FinalizeUploadRequest,
    tenant_scope: TenantScope = TenantDependency,
) -> FinalizeUploadResponse:
    meeting, session = finalize_upload(
        tenant_scope=tenant_scope,
        session_id=session_id,
        tracks=payload.tracks,
    )
    return FinalizeUploadResponse(
        meeting=meeting_response(meeting),
        upload_session=session_response(session),
        object_count=len(session.parts),
    )
