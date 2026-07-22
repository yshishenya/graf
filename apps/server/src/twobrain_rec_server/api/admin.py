from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.admin.audit import read_admin_audit_journal
from twobrain_rec_server.admin.files import (
    admin_meeting_access,
    get_admin_file_detail,
    list_admin_files,
    record_admin_review_access,
)
from twobrain_rec_server.admin.invitations import (
    complete_workspace_invitation,
    create_workspace_invitation,
    invitation_to_dict,
    resend_workspace_invitation,
    revoke_workspace_invitation,
)
from twobrain_rec_server.admin.meeting_detection import build_meeting_detection_admin_model
from twobrain_rec_server.admin.metrics import get_admin_metrics
from twobrain_rec_server.admin.queries import (
    get_admin_overview_payload,
    load_admin_workspace_context,
)
from twobrain_rec_server.admin.usage import get_usage_summary, load_quota_policy
from twobrain_rec_server.admin.users import (
    get_workspace_user_detail,
    list_workspace_users,
    update_workspace_membership,
)
from twobrain_rec_server.api.ingest import get_request_db_session, get_request_storage
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import ArtifactClass, CreateExportPackageRequest
from twobrain_rec_server.auth import email_delivery
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, DeviceContext, TenantScope
from twobrain_rec_server.auth.dependencies import (
    get_device_context,
    get_principal,
    get_tenant_scope,
    require_web_csrf,
)
from twobrain_rec_server.cabinet.egress import create_export_package, download_artifact
from twobrain_rec_server.cabinet.queries import latest_processing_result
from twobrain_rec_server.db.models import Meeting
from twobrain_rec_server.db.tenant_context import TenantDatabaseContext, apply_tenant_context
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY
from twobrain_rec_server.deletion.service import deletion_report_response, request_meeting_deletion
from twobrain_rec_server.domain.statuses import DeletionReasonCode, DeletionRequestSource
from twobrain_rec_server.meeting_detection.admin_review import (
    add_diagnostic_only_draft,
    load_meeting_detection_review,
    mark_candidate_non_target,
    merge_candidate_with_target,
    request_candidate_validation,
)
from twobrain_rec_server.meeting_detection.registry import (
    MeetingTargetRegistryError,
    publish_registry_draft,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

TenantDependency = Depends(get_tenant_scope)
PrincipalDependency = Depends(get_principal)
DeviceDependency = Depends(get_device_context)
WebCSRFDependency = Depends(require_web_csrf)
DbDependency = Depends(get_request_db_session)
StorageDependency = Depends(get_request_storage)
AdminLimitQuery = Query(default=50, ge=1, le=100)
AdminSearchQuery = Query(default=None, max_length=120)
AdminStatusQuery = Query(default=None, max_length=64)
AdminRoleQuery = Query(default=None, pattern="^(owner|admin|member)$")
AdminInvitationStatusQuery = Query(default=None, max_length=32)
AdminDateQuery = Query(default=None)
AdminIntQuery = Query(default=None, ge=0)


class InvitationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_contact: str = Field(min_length=1, max_length=240)
    target_provider: str | None = Field(default=None, max_length=64)
    invited_role: str = Field(pattern="^(owner|admin|member)$")
    expires_at: datetime | None = None


class InvitationRevokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason_code: str | None = Field(default=None, max_length=120)


class InvitationCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    login_contact: str = Field(min_length=1, max_length=240)
    provider: str | None = Field(default=None, max_length=64)


class MembershipPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str | None = Field(default=None, pattern="^(owner|admin|member)$")
    status: str | None = Field(default=None, pattern="^(active|inactive|blocked|revoked)$")
    reason_code: str | None = Field(default=None, max_length=120)


class AdminDeletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm: bool
    reason_code: DeletionReasonCode = DeletionReasonCode.USER_REQUEST


class MeetingDetectionAdminActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason_code: str | None = Field(default=None, max_length=120)


class MeetingDetectionMergeRequest(MeetingDetectionAdminActionRequest):
    target_id: str = Field(min_length=3, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]{2,80}$")


class MeetingDetectionDiagnosticDraftRequest(MeetingDetectionAdminActionRequest):
    target_id: str = Field(min_length=3, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]{2,80}$")
    display_name: str = Field(min_length=1, max_length=80)
    market: str = Field(pattern="^(global|russia|enterprise|unknown)$")


class MeetingDetectionValidationRequest(MeetingDetectionAdminActionRequest):
    validation_kind: str = Field(default="runtime", pattern="^(runtime|package)$")


@router.get("/overview", operation_id="getAdminOverview")
async def get_admin_overview(
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    return await get_admin_overview_payload(db, context=context)


@router.get("/meeting-detection", operation_id="getAdminMeetingDetectionReview")
async def get_admin_meeting_detection_review(
    limit: int = AdminLimitQuery,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    review = await load_meeting_detection_review(db, context=context, limit=limit)
    return build_meeting_detection_admin_model(review)


@router.post(
    "/meeting-detection/candidates/{candidate_id}/mark-non-target",
    operation_id="markMeetingDetectionCandidateNonTarget",
    dependencies=[WebCSRFDependency],
)
async def mark_admin_meeting_detection_candidate_non_target(
    candidate_id: UUID,
    payload: MeetingDetectionAdminActionRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    row = await mark_candidate_non_target(
        db,
        context=context,
        candidate_id=candidate_id,
        reason_code=payload.reason_code,
    )
    await db.commit()
    return row


@router.post(
    "/meeting-detection/candidates/{candidate_id}/merge",
    operation_id="mergeMeetingDetectionCandidate",
    dependencies=[WebCSRFDependency],
)
async def merge_admin_meeting_detection_candidate(
    candidate_id: UUID,
    payload: MeetingDetectionMergeRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    row = await merge_candidate_with_target(
        db,
        context=context,
        candidate_id=candidate_id,
        target_id=payload.target_id,
        reason_code=payload.reason_code,
    )
    await db.commit()
    return row


@router.post(
    "/meeting-detection/candidates/{candidate_id}/add-diagnostic-only-draft",
    operation_id="addMeetingDetectionDiagnosticDraft",
    dependencies=[WebCSRFDependency],
)
async def add_admin_meeting_detection_diagnostic_draft(
    candidate_id: UUID,
    payload: MeetingDetectionDiagnosticDraftRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    row = await add_diagnostic_only_draft(
        db,
        context=context,
        candidate_id=candidate_id,
        target_id=payload.target_id,
        display_name=payload.display_name,
        market=payload.market,
        reason_code=payload.reason_code,
    )
    await db.commit()
    return row


@router.post(
    "/meeting-detection/candidates/{candidate_id}/request-validation",
    operation_id="requestMeetingDetectionCandidateValidation",
    dependencies=[WebCSRFDependency],
)
async def request_admin_meeting_detection_candidate_validation(
    candidate_id: UUID,
    payload: MeetingDetectionValidationRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    row = await request_candidate_validation(
        db,
        context=context,
        candidate_id=candidate_id,
        validation_kind=payload.validation_kind,
        reason_code=payload.reason_code,
    )
    await db.commit()
    return row


@router.post(
    "/meeting-detection/registry-drafts/{draft_id}/publish",
    operation_id="publishMeetingDetectionRegistryDraft",
    dependencies=[WebCSRFDependency],
)
async def publish_admin_meeting_detection_registry_draft(
    draft_id: UUID,
    payload: MeetingDetectionAdminActionRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    try:
        row = await publish_registry_draft(
            db,
            context=context,
            draft_id=draft_id,
            reason_code=payload.reason_code,
        )
    except MeetingTargetRegistryError as exc:
        status_code = 404 if "not found" in str(exc) else 400
        raise ProblemDetail(
            status=status_code,
            code="meeting_detection_registry_publish_failed",
            title="Meeting detection registry draft could not be published",
            detail=str(exc),
        ) from exc
    await db.commit()
    return row


@router.get("/users", operation_id="listAdminUsers")
async def list_admin_users(
    search: str | None = AdminSearchQuery,
    role: str | None = AdminRoleQuery,
    status: str | None = AdminStatusQuery,
    invitation_status: str | None = AdminInvitationStatusQuery,
    limit: int = AdminLimitQuery,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    return await list_workspace_users(
        db,
        context=context,
        search=search,
        role=role,
        status=status,
        invitation_status=invitation_status,
        limit=limit,
    )


@router.get("/users/{user_id}", operation_id="getAdminUser")
async def get_admin_user(
    user_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    return await get_workspace_user_detail(db, context=context, user_id=user_id)


@router.post(
    "/invitations",
    status_code=201,
    operation_id="createAdminInvitation",
    dependencies=[WebCSRFDependency],
)
async def create_admin_invitation(
    payload: InvitationCreateRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    invitation = await create_workspace_invitation(
        db,
        context=context,
        target_contact=payload.target_contact,
        target_provider=payload.target_provider,
        invited_role=payload.invited_role,
        expires_at=payload.expires_at,
    )
    await db.commit()
    return invitation_to_dict(invitation)


@router.post(
    "/invitations/{invitation_id}/revoke",
    operation_id="revokeAdminInvitation",
    dependencies=[WebCSRFDependency],
)
async def revoke_admin_invitation(
    invitation_id: UUID,
    payload: InvitationRevokeRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    invitation = await revoke_workspace_invitation(
        db,
        context=context,
        invitation_id=invitation_id,
        reason_code=payload.reason_code,
    )
    await db.commit()
    return invitation_to_dict(invitation)


@router.post(
    "/invitations/{invitation_id}/resend",
    operation_id="resendAdminInvitation",
    dependencies=[WebCSRFDependency],
)
async def resend_admin_invitation(
    invitation_id: UUID,
    request: Request,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    invitation = await resend_workspace_invitation(
        db,
        context=context,
        invitation_id=invitation_id,
    )
    if "@" not in invitation.target_contact:
        raise ProblemDetail(
            status=409,
            code="invitation_resend_unavailable",
            title="Invitation resend unavailable",
        )
    try:
        await email_delivery.send_workspace_invitation_review_notice(
            settings=request.app.state.settings,
            recipient_email=invitation.target_contact,
        )
    except email_delivery.EmailLoginDeliveryError as exc:
        raise ProblemDetail(
            status=503,
            code="invitation_delivery_unavailable",
            title="Invitation delivery unavailable",
        ) from exc
    await db.commit()
    return invitation_to_dict(invitation)


@router.post(
    "/invitations/{invitation_id}/complete",
    operation_id="completeAdminInvitation",
    dependencies=[WebCSRFDependency],
)
async def complete_admin_invitation(
    invitation_id: UUID,
    payload: InvitationCompleteRequest,
    request: Request,
    principal: AuthenticatedPrincipal = PrincipalDependency,
) -> dict[str, object]:
    if payload.workspace_id not in principal.workspace_ids:
        raise ProblemDetail(
            status=403, code="workspace_scope_denied", title="Workspace scope denied"
        )
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    async with sessionmaker() as db:
        await apply_tenant_context(
            db,
            TenantDatabaseContext(
                organization_id=principal.organization_id,
                workspace_id=payload.workspace_id,
                user_id=principal.user_id,
            ),
        )
        invitation = await complete_workspace_invitation(
            db,
            workspace_id=payload.workspace_id,
            invitation_id=invitation_id,
            completed_user_id=principal.user_id,
            provider=payload.provider,
            login_contacts=[payload.login_contact, principal.subject],
        )
        await db.commit()
        return invitation_to_dict(invitation)


@router.patch(
    "/users/{user_id}/membership",
    operation_id="patchAdminUserMembership",
    dependencies=[WebCSRFDependency],
)
async def patch_admin_user_membership(
    user_id: UUID,
    payload: MembershipPatchRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    response = await update_workspace_membership(
        db,
        context=context,
        target_user_id=user_id,
        requested_role=payload.role,
        requested_status=payload.status,
        reason_code=payload.reason_code,
    )
    await db.commit()
    return response


@router.get("/files", operation_id="listAdminFiles")
async def list_admin_file_rows(
    search: str | None = AdminSearchQuery,
    owner_user_id: UUID | None = None,
    type: str | None = Query(default=None, max_length=32),
    date_from: date | None = AdminDateQuery,
    date_to: date | None = AdminDateQuery,
    processing_state: str | None = AdminStatusQuery,
    deletion_state: str | None = AdminStatusQuery,
    retention_state: str | None = AdminStatusQuery,
    min_size: int | None = AdminIntQuery,
    max_size: int | None = AdminIntQuery,
    min_duration: int | None = AdminIntQuery,
    max_duration: int | None = AdminIntQuery,
    limit: int = AdminLimitQuery,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    return await list_admin_files(
        db,
        context=context,
        q=search,
        owner_user_id=owner_user_id,
        file_type=type,
        date_from=date_from,
        date_to=date_to,
        processing_state=processing_state,
        deletion_state=deletion_state,
        retention_state=retention_state,
        min_size=min_size,
        max_size=max_size,
        min_duration=min_duration,
        max_duration=max_duration,
        limit=limit,
    )


@router.get("/files/{meeting_id}", operation_id="getAdminFile")
async def get_admin_file(
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    return await get_admin_file_detail(db, context=context, meeting_id=meeting_id)


@router.post(
    "/files/{meeting_id}/review-access",
    operation_id="createAdminFileReviewAccess",
    dependencies=[WebCSRFDependency],
)
async def create_admin_file_review_access(
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    response = await record_admin_review_access(db, context=context, meeting_id=meeting_id)
    await db.commit()
    return response


@router.get(
    "/files/{meeting_id}/downloads/{artifact_class}", operation_id="downloadAdminMeetingArtifact"
)
async def download_admin_meeting_artifact(
    meeting_id: UUID,
    artifact_class: ArtifactClass,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = DbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    meeting = await _load_admin_meeting(db, context.workspace_id, meeting_id)
    access = admin_meeting_access(context)
    result = await latest_processing_result(
        db, workspace_id=context.workspace_id, meeting_id=meeting_id
    )
    download = await download_artifact(
        db,
        storage=storage,
        meeting=meeting,
        access=access,
        artifact_class=artifact_class,
        result=result,
        actor_user_id=principal.user_id,
        device_id=device.device_id,
    )
    await db.commit()
    headers = {
        "Content-Disposition": f'attachment; filename="{download.filename}"',
        "Content-Length": str(download.byte_length),
    }
    if not isinstance(download.body, bytes):
        return StreamingResponse(
            download.body,
            media_type="application/octet-stream",
            headers=headers,
        )
    return Response(
        content=download.body,
        media_type="application/octet-stream",
        headers=headers,
    )


@router.post(
    "/files/{meeting_id}/exports",
    status_code=202,
    operation_id="createAdminMeetingExport",
    dependencies=[WebCSRFDependency],
)
async def create_admin_meeting_export(
    meeting_id: UUID,
    payload: CreateExportPackageRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    db: AsyncSession | None = DbDependency,
):
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    meeting = await _load_admin_meeting(db, context.workspace_id, meeting_id)
    access = admin_meeting_access(context)
    result = await latest_processing_result(
        db, workspace_id=context.workspace_id, meeting_id=meeting_id
    )
    response = await create_export_package(
        db,
        meeting=meeting,
        access=access,
        requested_artifacts=payload.artifact_classes,
        result=result,
        actor_user_id=principal.user_id,
        device_id=device.device_id,
    )
    await db.commit()
    return response


@router.post(
    "/files/{meeting_id}/deletion-requests",
    status_code=202,
    operation_id="createAdminMeetingDeletion",
    dependencies=[WebCSRFDependency],
)
async def create_admin_meeting_deletion(
    request: Request,
    meeting_id: UUID,
    payload: AdminDeletionRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = DbDependency,
):
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    if not payload.confirm:
        raise ProblemDetail(
            status=422,
            code="deletion_confirmation_required",
            title="Deletion confirmation required",
        )
    meeting = await _load_admin_meeting(db, context.workspace_id, meeting_id)
    response = await request_meeting_deletion(
        db,
        meeting=meeting,
        actor_user_id=principal.user_id,
        device_id=device.device_id,
        confirmation_boundary=BOUNDED_DELETE_COPY,
        request_source=DeletionRequestSource.ADMIN,
        reason_code=payload.reason_code,
        storage=storage,
        temporal_client=getattr(request.app.state, "temporal_client", None),
    )
    await db.commit()
    return response


@router.get("/files/{meeting_id}/deletion-report", operation_id="getAdminMeetingDeletionReport")
async def get_admin_meeting_deletion_report(
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
):
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    meeting = await _load_admin_meeting(db, context.workspace_id, meeting_id)
    return await deletion_report_response(db, meeting=meeting)


@router.get("/usage", operation_id="getAdminUsage")
async def get_admin_usage(
    date_from: date | None = AdminDateQuery,
    date_to: date | None = AdminDateQuery,
    limit: int = AdminLimitQuery,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    return await get_usage_summary(
        db, context=context, date_from=date_from, date_to=date_to, limit=limit
    )


@router.get("/quota-policy", operation_id="getAdminQuotaPolicy")
async def get_admin_quota_policy(
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    return await load_quota_policy(db, context=context)


@router.get("/metrics", operation_id="getAdminMetrics")
async def get_admin_metrics_route(
    family: str | None = Query(
        default=None, pattern="^(adoption|usage|funnel|reliability|governance)$"
    ),
    date_from: date | None = AdminDateQuery,
    date_to: date | None = AdminDateQuery,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    metrics = await get_admin_metrics(
        db, context=context, family=family, date_from=date_from, date_to=date_to
    )
    return {
        "metrics": metrics["metrics"],
        "playback_normalization": metrics["playback_normalization"],
    }


@router.get("/audit", operation_id="getAdminAudit")
async def get_admin_audit_route(
    date_from: date | None = AdminDateQuery,
    date_to: date | None = AdminDateQuery,
    user_id: UUID | None = None,
    action: str | None = Query(default=None, max_length=120),
    object_kind: str | None = Query(default=None, max_length=64),
    object_id: str | None = Query(default=None, max_length=160),
    outcome: str | None = Query(default=None, max_length=32),
    limit: int = AdminLimitQuery,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> dict[str, object]:
    if db is None:
        raise ProblemDetail(
            status=503, code="admin_store_unavailable", title="Admin store unavailable"
        )
    context = await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    return await read_admin_audit_journal(
        db,
        context=context,
        date_from=date_from,
        date_to=date_to,
        user_id=user_id,
        action=action,
        object_kind=object_kind,
        object_id=object_id,
        outcome=outcome,
        limit=limit,
    )


async def _load_admin_meeting(db: AsyncSession, workspace_id: UUID, meeting_id: UUID) -> Meeting:
    meeting = await db.scalar(
        select(Meeting).where(Meeting.workspace_id == workspace_id, Meeting.id == meeting_id)
    )
    if meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return meeting
