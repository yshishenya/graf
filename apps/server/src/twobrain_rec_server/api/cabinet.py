from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.ingest import get_request_db_session, get_request_storage
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    AccessState,
    ArtifactClass,
    CreateExportPackageRequest,
    CreateShareGrantRequest,
    ExportPackageResponse,
    MeetingAccessResponse,
    MeetingActivityResponse,
    MeetingListResponse,
    MeetingReviewResponse,
    MeetingReviewStatus,
    ShareGrantResponse,
)
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, DeviceContext, TenantScope
from twobrain_rec_server.auth.dependencies import (
    get_device_context,
    get_principal,
    get_tenant_scope,
)
from twobrain_rec_server.cabinet.access import (
    create_share_grant,
    decide_meeting_access,
    grant_view,
    resolve_share_token,
    revoke_share_grant,
    share_panel_state,
)
from twobrain_rec_server.cabinet.constants import DELETION_TRUTH_COPY
from twobrain_rec_server.cabinet.egress import (
    activity_response,
    artifact_egress_states,
    create_export_package,
    download_artifact,
    export_package_bytes,
)
from twobrain_rec_server.cabinet.queries import (
    get_cabinet_meeting_review,
    latest_processing_result,
    list_cabinet_meetings,
)
from twobrain_rec_server.db.models import Meeting

router = APIRouter(prefix="/api/v1", tags=["cabinet"])

TenantDependency = Depends(get_tenant_scope)
PrincipalDependency = Depends(get_principal)
DeviceDependency = Depends(get_device_context)
DbDependency = Depends(get_request_db_session)
StorageDependency = Depends(get_request_storage)
CabinetSearchQuery = Query(default=None, max_length=120)
CabinetStatusQuery = Query(default=None)
CabinetAccessQuery = Query(default=None)
CabinetSortQuery = Query(default="updated_desc")
CabinetLimitQuery = Query(default=50, ge=1, le=100)


@router.get(
    "/cabinet/meetings",
    response_model=MeetingListResponse,
    operation_id="listCabinetMeetings",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def list_cabinet_meetings_route(
    q: str | None = CabinetSearchQuery,
    status: MeetingReviewStatus | None = CabinetStatusQuery,
    access: AccessState | None = CabinetAccessQuery,
    sort: str = CabinetSortQuery,
    limit: int = CabinetLimitQuery,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> MeetingListResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    return await list_cabinet_meetings(
        db,
        workspace_id=tenant_scope.workspace_id,
        viewer_user_id=principal.user_id,
        q=q,
        status=status,
        access=access,
        sort=sort,
        limit=limit,
    )


@router.get(
    "/cabinet/meetings/{meeting_id}",
    response_model=MeetingReviewResponse,
    operation_id="getCabinetMeetingReview",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def get_cabinet_meeting_review_route(
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> MeetingReviewResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    response = await get_cabinet_meeting_review(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    if response is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return response


@router.get(
    "/cabinet/meetings/{meeting_id}/access",
    response_model=MeetingAccessResponse,
    operation_id="getMeetingAccessState",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def get_meeting_access_state_route(
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> MeetingAccessResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    meeting, decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    result = await latest_processing_result(db, workspace_id=tenant_scope.workspace_id, meeting_id=meeting_id)
    return MeetingAccessResponse(
        meeting_id=meeting.id,
        access=decision.to_schema(),
        share=await share_panel_state(db, meeting, decision),
        artifacts=await artifact_egress_states(db, meeting=meeting, access=decision, result=result),
        deletion_truth_copy=DELETION_TRUTH_COPY,
    )


@router.get(
    "/cabinet/meetings/{meeting_id}/activity",
    response_model=MeetingActivityResponse,
    operation_id="listMeetingAccessActivity",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def list_meeting_activity_route(
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> MeetingActivityResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    return await activity_response(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )


@router.post(
    "/cabinet/meetings/{meeting_id}/shares",
    response_model=ShareGrantResponse,
    status_code=201,
    operation_id="createMeetingShareGrant",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def create_meeting_share_grant_route(
    meeting_id: UUID,
    payload: CreateShareGrantRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    db: AsyncSession | None = DbDependency,
) -> ShareGrantResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    meeting, _decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    grant, raw_token = await create_share_grant(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting=meeting,
        actor_user_id=principal.user_id,
        device_id=device.device_id,
        grantee_user_id=payload.grantee_user_id,
    )
    await db.commit()
    return ShareGrantResponse(
        grant=grant_view(grant, display_name="Authenticated user"),
        share_url=f"/cabinet/share/{raw_token}",
    )


@router.delete(
    "/cabinet/meetings/{meeting_id}/shares/{grant_id}",
    status_code=204,
    operation_id="revokeMeetingShareGrant",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def revoke_meeting_share_grant_route(
    meeting_id: UUID,
    grant_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    db: AsyncSession | None = DbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    meeting, _decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    await revoke_share_grant(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting=meeting,
        actor_user_id=principal.user_id,
        device_id=device.device_id,
        grant_id=grant_id,
    )
    await db.commit()
    return Response(status_code=204)


@router.get(
    "/cabinet/share/{share_token}",
    operation_id="resolveLoginRequiredShareLink",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def resolve_login_required_share_link_route(
    share_token: str,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    db: AsyncSession | None = DbDependency,
) -> RedirectResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    meeting = await resolve_share_token(
        db,
        workspace_id=tenant_scope.workspace_id,
        viewer_user_id=principal.user_id,
        device_id=device.device_id,
        share_token=share_token,
    )
    if meeting is None:
        raise ProblemDetail(status=404, code="share_not_found", title="Share not found")
    await db.commit()
    return RedirectResponse(url=f"/meetings/{meeting.id}", status_code=302)


@router.get(
    "/cabinet/meetings/{meeting_id}/downloads/{artifact_class}",
    operation_id="downloadMeetingArtifact",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def download_meeting_artifact_route(
    meeting_id: UUID,
    artifact_class: ArtifactClass,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = DbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    meeting, decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    result = await latest_processing_result(db, workspace_id=tenant_scope.workspace_id, meeting_id=meeting_id)
    download = await download_artifact(
        db,
        storage=storage,
        meeting=meeting,
        access=decision,
        artifact_class=artifact_class,
        result=result,
        actor_user_id=principal.user_id,
        device_id=device.device_id,
    )
    await db.commit()
    return Response(
        content=download.body,
        media_type=download.media_type,
        headers={"Content-Disposition": f'attachment; filename="{download.filename}"'},
    )


@router.post(
    "/cabinet/meetings/{meeting_id}/exports",
    response_model=ExportPackageResponse,
    status_code=202,
    operation_id="createMeetingExportPackage",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def create_meeting_export_package_route(
    meeting_id: UUID,
    payload: CreateExportPackageRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    db: AsyncSession | None = DbDependency,
) -> ExportPackageResponse:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    meeting, decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    result = await latest_processing_result(db, workspace_id=tenant_scope.workspace_id, meeting_id=meeting_id)
    response = await create_export_package(
        db,
        meeting=meeting,
        access=decision,
        requested_artifacts=payload.artifact_classes,
        result=result,
        actor_user_id=principal.user_id,
        device_id=device.device_id,
    )
    await db.commit()
    return response


@router.get(
    "/cabinet/meetings/{meeting_id}/exports/{export_id}/download",
    operation_id="downloadMeetingExportPackage",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def download_meeting_export_package_route(
    meeting_id: UUID,
    export_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    db: AsyncSession | None = DbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
    meeting, decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    download = await export_package_bytes(
        db,
        meeting=meeting,
        access=decision,
        export_id=export_id,
        actor_user_id=principal.user_id,
        device_id=device.device_id,
    )
    await db.commit()
    return Response(
        content=download.body,
        media_type=download.media_type,
        headers={"Content-Disposition": f'attachment; filename="{download.filename}"'},
    )


async def _authorized_meeting(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    viewer_user_id: UUID,
):
    meeting = await db.scalar(
        select(Meeting).where(
            Meeting.workspace_id == workspace_id,
            Meeting.id == meeting_id,
        )
    )
    if meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    decision = await decide_meeting_access(
        db,
        meeting,
        workspace_id=workspace_id,
        viewer_user_id=viewer_user_id,
    )
    if not decision.can_view:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return meeting, decision
