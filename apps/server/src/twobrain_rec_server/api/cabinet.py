from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query, Request, status
from fastapi.responses import (
    JSONResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.admin.queries import load_admin_workspace_context
from twobrain_rec_server.api.ingest import (
    commit_if_available,
    content_safe_meeting_response,
    get_request_db_session,
    get_request_storage,
    session_response,
)
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    AccessState,
    ArtifactClass,
    ContentExportCapabilityResponse,
    ContentExportSelectionRequest,
    CreateDeletionRequest,
    CreateExportPackageRequest,
    CreateMeetingShareInvitationRequest,
    CreateShareGrantRequest,
    CreateSummaryCandidateRequest,
    CreateSummaryTemplateRequest,
    DeletionLifecycleState,
    DeletionRequestResponse,
    DeletionVerificationReport,
    ExportPackageResponse,
    LocalPurgeAckRequest,
    LocalPurgeTask,
    LocalPurgeTaskList,
    ManualMediaUploadResponse,
    MeetingAccessResponse,
    MeetingActivityResponse,
    MeetingListResponse,
    MeetingReviewResponse,
    MeetingReviewStatus,
    MeetingShareInvitationResponse,
    PublicShareSummaryResponse,
    ResolveSummaryCandidateRequest,
    RetentionRunRequest,
    RetentionRunResponse,
    ShareGrantResponse,
    ShareRecipientListResponse,
    ShareRecipientView,
    SummaryCandidateListResponse,
    SummaryCandidateNextAction,
    SummaryCandidatePreviewItem,
    SummaryCandidatePreviewResponse,
    SummaryCandidateProvenance,
    SummaryCandidateReasonCode,
    SummaryCandidateResponse,
    SummaryTemplateListResponse,
    SummaryTemplateView,
    UpdateDefaultSummaryTemplateRequest,
    UpdateSummaryTemplateRequest,
)
from twobrain_rec_server.api.upload_stream import (
    MANUAL_MEDIA_UPLOAD_OPENAPI_EXTRA,
    read_manual_media_upload_body,
)
from twobrain_rec_server.auth import email_delivery
from twobrain_rec_server.auth.browser_handoff import (
    DESKTOP_BILLING_HANDOFF_PROVIDER,
    DESKTOP_BILLING_HANDOFF_TTL_SECONDS,
    seal_desktop_billing_session,
)
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, DeviceContext, TenantScope
from twobrain_rec_server.auth.dependencies import (
    get_device_context,
    get_principal,
    get_tenant_scope,
    get_web_owner_tenant_scope,
    require_web_csrf,
)
from twobrain_rec_server.auth.sessions import callback_expiry, issue_callback_nonce
from twobrain_rec_server.cabinet.access import (
    ShareRecipientAccessProof,
    accept_share_invitation,
    create_scoped_share_grant,
    create_share_invitation,
    decide_meeting_access,
    grant_view,
    hash_share_token,
    invitation_address_hashes,
    lock_shareable_meeting,
    narrow_summary_projection,
    normalize_invitation_address,
    recipient_share_access_proof,
    resolve_share_token,
    revoke_share_grant,
    revoke_share_invitation,
    rotate_share_link,
    search_share_recipients,
    share_panel_state,
)
from twobrain_rec_server.cabinet.constants import DELETION_TRUTH_COPY
from twobrain_rec_server.cabinet.egress import (
    activity_response,
    artifact_egress_states,
    content_export_capabilities,
    create_content_export,
    create_export_package,
    current_outcome_set,
    download_artifact,
    export_package_bytes,
    playback_artifact,
)
from twobrain_rec_server.cabinet.exports import MEDIA_TYPES, ExportSelection
from twobrain_rec_server.cabinet.queries import (
    get_cabinet_meeting_review,
    latest_processing_result,
    list_cabinet_meetings,
)
from twobrain_rec_server.cabinet.rendering import render_shared_meeting_summary_page
from twobrain_rec_server.cabinet.speakers import candidate_speaker_attribution_is_current
from twobrain_rec_server.cabinet.templates import cabinet_html_response
from twobrain_rec_server.db.models import (
    AuthCallbackState,
    ExternalIdentity,
    MediaRevision,
    Meeting,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeItem,
    MeetingOutcomeSet,
    MeetingShareGrant,
    ProcessingResult,
    SummaryTemplate,
    TranscriptSegment,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.db.tenant_context import (
    TenantDatabaseContext,
    WorkspaceAuthContext,
    apply_tenant_context,
)
from twobrain_rec_server.deletion.local_purge import (
    acknowledge_local_purge_task,
    list_local_purge_tasks,
)
from twobrain_rec_server.deletion.report import lifecycle_state
from twobrain_rec_server.deletion.retention import run_retention_scan
from twobrain_rec_server.deletion.service import (
    deletion_report_response,
    lifecycle_for_meeting,
    request_meeting_deletion,
    retry_meeting_deletion,
)
from twobrain_rec_server.ingest.manual_media_upload import accept_manual_media_upload
from twobrain_rec_server.outcomes.ai_service import (
    OutcomeGenerationTerminalError,
    create_summary_candidate,
    resolve_summary_candidate,
)
from twobrain_rec_server.outcomes.dispatch import (
    ensure_dispatch_intent,
    finalize_dispatch_for_candidate,
    reconcile_dispatch_intent,
)
from twobrain_rec_server.outcomes.models import OutcomeTranscriptSegment
from twobrain_rec_server.outcomes.service import load_outcome_transcript_segments
from twobrain_rec_server.outcomes.templates import (
    BUILT_IN_BY_KEY,
    BUILT_IN_TEMPLATES,
    built_in_template_for_version,
)
from twobrain_rec_server.processing import store as processing_store
from twobrain_rec_server.processing.fences import (
    is_expired,
    lock_meeting_fence,
    meeting_is_deleted_or_deleting,
    normalize_db_timestamp,
)
from twobrain_rec_server.processing.results import result_source_hash_is_attested
from twobrain_rec_server.workflows.temporal_client import (
    cancel_invitation_delivery_workflow,
    connect_temporal_client,
    start_invitation_delivery_workflow,
)

router = APIRouter(prefix="/api/v1", tags=["cabinet"])

TenantDependency = Depends(get_tenant_scope)
WebOwnerTenantDependency = Depends(get_web_owner_tenant_scope)
PrincipalDependency = Depends(get_principal)
DeviceDependency = Depends(get_device_context)
WebCSRFDependency = Depends(require_web_csrf)
DbDependency = Depends(get_request_db_session)


@router.post("/cabinet/billing/handoff", include_in_schema=False)
async def create_desktop_billing_handoff(
    request: Request,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    tenant_scope: TenantScope = WebOwnerTenantDependency,
    _csrf: None = WebCSRFDependency,
    x_auth_session: str | None = Header(default=None, alias="X-Auth-Session", include_in_schema=False),
) -> JSONResponse:
    """Create a short-lived, one-use browser exchange for the native desktop session."""
    session_token = (x_auth_session or "").strip()
    if not session_token or not principal.auth_via_session:
        raise ProblemDetail(
            status=401,
            code="auth_session_required",
            title="A validated desktop auth session is required",
        )
    key_file = getattr(request.app.state.settings, "credential_encryption_key_file", None)
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if key_file is None or sessionmaker is None:
        raise ProblemDetail(
            status=503,
            code="auth_handoff_unavailable",
            title="Browser handoff is temporarily unavailable",
        )
    key = key_file.read_bytes().strip()
    if not key:
        raise ProblemDetail(
            status=503,
            code="auth_handoff_unavailable",
            title="Browser handoff is temporarily unavailable",
        )

    state_nonce = issue_callback_nonce()
    async with sessionmaker() as db:
        await apply_tenant_context(
            db,
            WorkspaceAuthContext(
                organization_id=tenant_scope.organization_id,
                workspace_id=tenant_scope.workspace_id,
                user_id=principal.user_id,
            ),
        )
        db.add(
            AuthCallbackState(
                provider=DESKTOP_BILLING_HANDOFF_PROVIDER,
                state_nonce=state_nonce,
                workspace_id=tenant_scope.workspace_id,
                requested_redirect="/billing",
                expected_state=seal_desktop_billing_session(session_token, key=key),
                expires_at=callback_expiry(ttl_seconds=DESKTOP_BILLING_HANDOFF_TTL_SECONDS),
                result="pending",
            )
        )
        await db.commit()
    return JSONResponse({"state": state_nonce})


async def _send_internal_share_notification(
    db: AsyncSession,
    *,
    request: Request,
    meeting: Meeting,
    grant: MeetingShareGrant,
    recipient_user_id: UUID | None,
    inviter_user_id: UUID,
) -> str:
    if grant.audience_type != "user" or recipient_user_id is None:
        return "not_attempted"
    recipient_email = await db.scalar(
        select(ExternalIdentity.email)
        .where(
            ExternalIdentity.user_id == recipient_user_id,
            ExternalIdentity.email.is_not(None),
            ExternalIdentity.is_active.is_(True),
            ExternalIdentity.is_verified.is_(True),
        )
        .order_by(ExternalIdentity.created_at.asc())
    )
    if not recipient_email:
        return "not_available"
    inviter = await db.get(UserIdentity, inviter_user_id)
    public_base_url = request.app.state.settings.public_base_url
    if public_base_url is None:
        return "not_available"
    try:
        await email_delivery.send_meeting_invitation(
            settings=request.app.state.settings,
            recipient_email=recipient_email,
            acceptance_url=(f"{str(public_base_url).rstrip('/')}/meetings/{meeting.id}"),
            delivery_key=str(grant.id),
            content_scope=grant.content_scope,
            inviter_name=inviter.display_name if inviter is not None else None,
            meeting_title=meeting.title,
            occurred_at=meeting.started_at or meeting.created_at,
            duration_seconds=meeting.duration_seconds,
            expires_at=grant.expires_at,
        )
    except email_delivery.EmailLoginDeliveryError as exc:
        return "outcome_unknown" if exc.outcome_unknown else "failed"
    return "sent"


async def get_public_share_db_session(
    request: Request,
    workspace_id: Annotated[UUID, Query()],
):
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        yield None
        return
    async with sessionmaker() as session:
        session.info["share_rate_limit_sessionmaker"] = sessionmaker
        await apply_tenant_context(
            session,
            TenantDatabaseContext(
                organization_id=UUID(int=0),
                workspace_id=workspace_id,
                user_id=UUID(int=0),
                context_kind="request",
            ),
        )
        yield session


async def _verified_invitation_address_hashes(
    request: Request,
    *,
    recipient_scope: TenantScope,
) -> set[str]:
    """Read verified identities under the recipient's own validated RLS context."""
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        raise ProblemDetail(
            status=503,
            code="auth_context_unavailable",
            title="Authentication context unavailable",
        )
    async with sessionmaker() as session:
        await apply_tenant_context(
            session,
            TenantDatabaseContext(
                organization_id=recipient_scope.organization_id,
                workspace_id=recipient_scope.workspace_id,
                user_id=recipient_scope.user_id,
                device_id=recipient_scope.device_id,
                auth_session_id=recipient_scope.auth_session_id,
                context_kind="request",
            ),
        )
        emails = (
            await session.scalars(
                select(ExternalIdentity.email).where(
                    ExternalIdentity.user_id == recipient_scope.user_id,
                    ExternalIdentity.is_active.is_(True),
                    ExternalIdentity.is_verified.is_(True),
                    ExternalIdentity.email.is_not(None),
                )
            )
        ).all()
    return {
        digest
        for email in emails
        if email
        for digest in invitation_address_hashes(normalize_invitation_address(email))
    }


async def _recipient_share_access_proof(
    request: Request,
    *,
    recipient_scope: TenantScope,
    owner_workspace_id: UUID,
) -> ShareRecipientAccessProof:
    """Validate the recipient identity and membership in the owner's workspace."""
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        raise ProblemDetail(
            status=503,
            code="auth_context_unavailable",
            title="Authentication context unavailable",
        )
    return await recipient_share_access_proof(
        sessionmaker,
        recipient_scope=recipient_scope,
        owner_workspace_id=owner_workspace_id,
    )


PublicShareDbDependency = Depends(get_public_share_db_session)
StorageDependency = Depends(get_request_storage)
CabinetSearchQuery = Query(default=None, max_length=120)
CabinetStatusQuery = Query(default=None)
CabinetAccessQuery = Query(default=None)
ShareRecipientsMeetingIdQuery = Query(default=None)
CabinetSortQuery = Query(default="updated_desc")
CabinetLimitQuery = Query(default=50, ge=1, le=100)


def _mark_share_secret_response(response: Response) -> None:
    response.headers.update(
        {
            "Cache-Control": "private, no-store",
            "Pragma": "no-cache",
            "Referrer-Policy": "no-referrer",
            "X-Robots-Tag": "noindex, nofollow, noarchive",
        }
    )


PLAYBACK_BINARY_SCHEMA = {"type": "string", "format": "binary"}
PLAYBACK_COMMON_HEADERS = {
    "Accept-Ranges": {
        "description": "Supported byte range unit. Always `bytes`.",
        "schema": {"type": "string"},
    },
    "Content-Disposition": {
        "description": "Safe inline playback filename.",
        "schema": {"type": "string"},
    },
    "Content-Length": {
        "description": "Number of bytes in this response body.",
        "schema": {"type": "integer"},
    },
}
PLAYBACK_PROBLEM_CONTENT = {
    "application/problem+json": {"schema": {"$ref": "#/components/schemas/Problem"}}
}
PLAYBACK_RESPONSES = {
    200: {
        "description": "Complete canonical review M4A.",
        "content": {"audio/mp4": {"schema": PLAYBACK_BINARY_SCHEMA}},
        "headers": PLAYBACK_COMMON_HEADERS,
    },
    206: {
        "description": "Requested byte range from the canonical review M4A.",
        "content": {"audio/mp4": {"schema": PLAYBACK_BINARY_SCHEMA}},
        "headers": {
            **PLAYBACK_COMMON_HEADERS,
            "Content-Range": {
                "description": "Returned byte interval and complete object length.",
                "schema": {"type": "string"},
            },
        },
    },
    404: {"description": "Meeting not found.", "content": PLAYBACK_PROBLEM_CONTENT},
    409: {"description": "Playback is not available.", "content": PLAYBACK_PROBLEM_CONTENT},
    416: {
        "description": "Requested byte range is malformed or unsatisfiable.",
        "content": PLAYBACK_PROBLEM_CONTENT,
    },
    503: {
        "description": "Canonical storage is temporarily unavailable.",
        "content": PLAYBACK_PROBLEM_CONTENT,
    },
}


def _is_hx_request(request: Request) -> bool:
    return request.headers.get("HX-Request", "").lower() == "true"


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
    storage: object = StorageDependency,
    db: AsyncSession | None = DbDependency,
) -> MeetingListResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    return await list_cabinet_meetings(
        db,
        workspace_id=tenant_scope.workspace_id,
        viewer_user_id=principal.user_id,
        storage=storage,
        q=q,
        status=status,
        access=access,
        sort=sort,
        limit=limit,
    )


@router.post(
    "/cabinet/media-uploads",
    response_model=ManualMediaUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="createCabinetManualMediaUpload",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
    openapi_extra=MANUAL_MEDIA_UPLOAD_OPENAPI_EXTRA,
)
async def create_cabinet_manual_media_upload_route(
    request: Request,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
    storage: object = StorageDependency,
) -> ManualMediaUploadResponse:
    if not principal.auth_via_session:
        raise ProblemDetail(
            status=401,
            code="auth_session_required_for_manual_upload",
            title="Sign in required for media upload",
        )
    upload = await read_manual_media_upload_body(
        request,
        max_file_bytes=request.app.state.settings.max_upload_part_bytes,
        spool_memory_bytes=request.app.state.settings.max_upload_spool_memory_bytes,
    )
    result = await accept_manual_media_upload(
        settings=request.app.state.settings,
        tenant_scope=tenant_scope,
        db=db,
        storage=storage,
        file=upload.file,
        filename=upload.filename,
        content_type=upload.content_type,
        duration_seconds=upload.duration_seconds,
        title=upload.title,
        local_recording_id=upload.local_recording_id,
        temporal_client=getattr(request.app.state, "temporal_client", None),
        archive_audio=upload.archive_audio,
    )
    await commit_if_available(db)
    return ManualMediaUploadResponse(
        meeting=await content_safe_meeting_response(db, result.meeting, result.calendar_context),
        upload_session=session_response(result.upload_session),
        object_count=result.object_count,
        workflow_started=result.processing.workflow_started,
        mediascribe_job_created=result.processing.mediascribe_job_created,
    )


@router.get(
    "/cabinet/meetings/{meeting_id}",
    response_model=MeetingReviewResponse,
    operation_id="getCabinetMeetingReview",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def get_cabinet_meeting_review_route(
    request: Request,
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = DbDependency,
) -> MeetingReviewResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    response = await get_cabinet_meeting_review(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
        storage=storage,
        external_invitations_enabled=request.app.state.settings.share_external_invitations_enabled,
        invitation_encryption_key=(
            request.app.state.settings.credential_encryption_key_file.read_bytes().strip()
            if request.app.state.settings.credential_encryption_key_file is not None
            else None
        ),
    )
    if response is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    if response.access is not None and not response.access.can_view_full_meeting:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return response


@router.get(
    "/cabinet/meetings/{meeting_id}/shared-summary",
    response_model=PublicShareSummaryResponse,
    operation_id="getSharedMeetingSummary",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def get_shared_meeting_summary_route(
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> PublicShareSummaryResponse:
    if db is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    meeting, decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    items = []
    outcome_set = await current_outcome_set(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting.id,
        processing_result_id=None,
    )
    if outcome_set is not None:
        items = (
            await db.scalars(
                select(MeetingOutcomeItem)
                .where(
                    MeetingOutcomeItem.workspace_id == tenant_scope.workspace_id,
                    MeetingOutcomeItem.outcome_set_id == outcome_set.id,
                    MeetingOutcomeItem.state == "available",
                )
                .order_by(MeetingOutcomeItem.category, MeetingOutcomeItem.sequence)
            )
        ).all()
    if not decision.can_view:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return PublicShareSummaryResponse.model_validate(
        narrow_summary_projection(
            meeting_label=meeting.title or "Встреча",
            occurred_at=meeting.started_at or meeting.created_at,
            duration_seconds=meeting.duration_seconds,
            summary_sections=[
                {"category": item.category, "text": item.text or ""} for item in items
            ],
        )
    )


@router.get(
    "/cabinet/meetings/{meeting_id}/access",
    response_model=MeetingAccessResponse,
    operation_id="getMeetingAccessState",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def get_meeting_access_state_route(
    request: Request,
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> MeetingAccessResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    result = await latest_processing_result(
        db, workspace_id=tenant_scope.workspace_id, meeting_id=meeting_id
    )
    return MeetingAccessResponse(
        meeting_id=meeting.id,
        access=decision.to_schema(),
        share=await share_panel_state(
            db,
            meeting,
            decision,
            external_invitations_enabled=request.app.state.settings.share_external_invitations_enabled,
            invitation_encryption_key=(
                request.app.state.settings.credential_encryption_key_file.read_bytes().strip()
                if request.app.state.settings.credential_encryption_key_file is not None
                else None
            ),
        ),
        artifacts=await artifact_egress_states(db, meeting=meeting, access=decision, result=result),
        deletion_truth_copy=DELETION_TRUTH_COPY,
    )


@router.post(
    "/cabinet/meetings/{meeting_id}/deletion-requests",
    response_model=DeletionRequestResponse,
    status_code=202,
    operation_id="createMeetingDeletionRequest",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def create_meeting_deletion_request_route(
    request: Request,
    meeting_id: UUID,
    payload: CreateDeletionRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = DbDependency,
) -> DeletionRequestResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    _ensure_lifecycle_manager(decision)
    response = await request_meeting_deletion(
        db,
        meeting=meeting,
        actor_user_id=principal.user_id,
        device_id=device.device_id,
        confirmation_boundary=payload.confirmation_boundary,
        local_buffer_expiry_days=request.app.state.settings.retention_local_buffer_expiry_days,
        reason_code=payload.reason_code,
        storage=storage,
        temporal_client=getattr(request.app.state, "temporal_client", None),
    )
    await db.commit()
    if _is_hx_request(request):
        return cabinet_html_response(
            "",
            status_code=202,
            hx_request=True,
        )
    return response


@router.get(
    "/cabinet/meetings/{meeting_id}/deletion-report",
    response_model=DeletionVerificationReport,
    operation_id="getMeetingDeletionReport",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def get_meeting_deletion_report_route(
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> DeletionVerificationReport:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting = await _authorized_lifecycle_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    return await deletion_report_response(db, meeting=meeting)


@router.get(
    "/cabinet/meetings/{meeting_id}/lifecycle",
    response_model=DeletionLifecycleState,
    operation_id="getMeetingLifecycleState",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def get_meeting_lifecycle_state_route(
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> DeletionLifecycleState:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting = await _authorized_lifecycle_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    return lifecycle_state(await lifecycle_for_meeting(meeting=meeting))


@router.post(
    "/cabinet/meetings/{meeting_id}/deletion-retry",
    response_model=DeletionRequestResponse,
    status_code=202,
    operation_id="retryMeetingDeletion",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def retry_meeting_deletion_route(
    request: Request,
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = DbDependency,
) -> DeletionRequestResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting = await _authorized_lifecycle_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    response = await retry_meeting_deletion(
        db,
        meeting=meeting,
        storage=storage,
        temporal_client=getattr(request.app.state, "temporal_client", None),
    )
    await db.commit()
    return response


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
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    _meeting, decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    if not decision.can_share:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return await activity_response(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )


@router.get(
    "/cabinet/summary-templates",
    response_model=SummaryTemplateListResponse,
    operation_id="listSummaryTemplates",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def list_summary_templates_route(
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> SummaryTemplateListResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    personal = (
        await db.scalars(
            select(SummaryTemplate)
            .where(
                SummaryTemplate.workspace_id == tenant_scope.workspace_id,
                SummaryTemplate.owner_user_id == principal.user_id,
                SummaryTemplate.status == "active",
            )
            .order_by(SummaryTemplate.updated_at.desc())
            .limit(100)
        )
    ).all()
    workspace = await db.scalar(select(Workspace).where(Workspace.id == tenant_scope.workspace_id))
    membership = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == tenant_scope.workspace_id,
            WorkspaceMembership.user_id == principal.user_id,
            WorkspaceMembership.status == "active",
        )
    )
    default_template_key = "graf-auto-v1"
    if workspace is not None:
        definition = built_in_template_for_version(
            workspace.default_summary_template_key,
            workspace.default_summary_template_version,
        )
        if workspace.default_summary_template_id is None and definition is not None:
            default_template_key = definition.key
        elif workspace.default_summary_template_id is not None:
            personal_default = next(
                (
                    template
                    for template in personal
                    if template.id == workspace.default_summary_template_id
                    and template.template_key == workspace.default_summary_template_key
                    and template.version == workspace.default_summary_template_version
                ),
                None,
            )
            if personal_default is not None:
                default_template_key = personal_default.template_key
    built_ins = [_built_in_template_view(definition) for definition in BUILT_IN_TEMPLATES]
    return SummaryTemplateListResponse(
        default_template_key=default_template_key,
        can_manage_default=membership is not None and membership.role == "owner",
        recommended=built_ins[:4],
        personal=[_personal_template_view(template) for template in personal],
    )


@router.put(
    "/cabinet/summary-templates/default",
    response_model=SummaryTemplateView,
    operation_id="updateDefaultSummaryTemplate",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def update_default_summary_template_route(
    payload: UpdateDefaultSummaryTemplateRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> SummaryTemplateView:
    if db is None:
        raise ProblemDetail(
            status=503,
            code="cabinet_store_unavailable",
            title="Cabinet store unavailable",
        )
    membership = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == tenant_scope.workspace_id,
            WorkspaceMembership.user_id == principal.user_id,
            WorkspaceMembership.status == "active",
        )
    )
    if membership is None or membership.role != "owner":
        raise ProblemDetail(
            status=403,
            code="summary_default_forbidden",
            title="Default summary format can only be changed by the workspace owner",
        )
    workspace = await db.scalar(
        select(Workspace).where(Workspace.id == tenant_scope.workspace_id).with_for_update()
    )
    if workspace is None:
        raise ProblemDetail(status=404, code="workspace_not_found", title="Workspace not found")
    if payload.template_id is not None:
        template = await db.scalar(
            select(SummaryTemplate).where(
                SummaryTemplate.id == payload.template_id,
                SummaryTemplate.workspace_id == tenant_scope.workspace_id,
                SummaryTemplate.owner_user_id == principal.user_id,
                SummaryTemplate.template_key == payload.template_key,
                SummaryTemplate.version == payload.template_version,
                SummaryTemplate.status == "active",
            )
        )
        if template is None:
            raise ProblemDetail(
                status=404,
                code="summary_template_not_found",
                title="Template not found",
            )
        selected = _personal_template_view(template)
    else:
        definition = BUILT_IN_BY_KEY.get(payload.template_key)
        if definition is None or definition.version != payload.template_version:
            raise ProblemDetail(
                status=404,
                code="summary_template_not_found",
                title="Template not found",
            )
        selected = _built_in_template_view(definition)
    workspace.default_summary_template_key = selected.template_key
    workspace.default_summary_template_id = selected.template_id
    workspace.default_summary_template_version = selected.version
    await db.commit()
    return selected


async def _ensure_personal_template_capacity(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    owner_user_id: UUID,
) -> None:
    # Serialize create/duplicate checks per workspace so the 100-template cap
    # remains true under concurrent requests.
    workspace = await db.scalar(
        select(Workspace.id).where(Workspace.id == workspace_id).with_for_update()
    )
    if workspace is None:
        raise ProblemDetail(status=404, code="workspace_not_found", title="Workspace not found")
    active_count = len(
        (
            await db.scalars(
                select(SummaryTemplate.id).where(
                    SummaryTemplate.workspace_id == workspace_id,
                    SummaryTemplate.owner_user_id == owner_user_id,
                    SummaryTemplate.status == "active",
                )
            )
        ).all()
    )
    if active_count >= 100:
        raise ProblemDetail(
            status=409, code="summary_template_limit", title="Template limit reached"
        )


@router.post(
    "/cabinet/summary-templates",
    response_model=SummaryTemplateView,
    status_code=201,
    operation_id="createSummaryTemplate",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def create_summary_template_route(
    payload: CreateSummaryTemplateRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> SummaryTemplateView:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    await _ensure_personal_template_capacity(
        db,
        workspace_id=tenant_scope.workspace_id,
        owner_user_id=principal.user_id,
    )
    template = SummaryTemplate(
        workspace_id=tenant_scope.workspace_id,
        owner_user_id=principal.user_id,
        template_key=f"personal-{uuid4()}",
        kind="personal",
        name=payload.name,
        purpose=payload.purpose,
        sections_json=list(payload.sections),
        output_language=payload.output_language,
        detail_level=payload.detail_level,
        version=1,
        status="active",
    )
    db.add(template)
    await db.commit()
    return _personal_template_view(template)


@router.patch(
    "/cabinet/summary-templates/{template_id}",
    response_model=SummaryTemplateView,
    operation_id="updateSummaryTemplate",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def update_summary_template_route(
    template_id: UUID,
    payload: UpdateSummaryTemplateRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> SummaryTemplateView:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    current = await _owned_personal_template(
        db,
        workspace_id=tenant_scope.workspace_id,
        owner_user_id=principal.user_id,
        template_id=template_id,
    )
    if current.version != payload.expected_version or current.status != "active":
        raise ProblemDetail(status=409, code="summary_template_conflict", title="Template changed")
    current.status = "archived"
    revised = SummaryTemplate(
        workspace_id=current.workspace_id,
        owner_user_id=current.owner_user_id,
        template_key=current.template_key,
        kind="personal",
        name=payload.name,
        purpose=payload.purpose,
        sections_json=list(payload.sections),
        output_language=payload.output_language,
        detail_level=payload.detail_level,
        version=current.version + 1,
        status="active",
    )
    db.add(revised)
    await db.flush()
    default_workspace = await _workspace_defaulting_to_template(
        db,
        workspace_id=tenant_scope.workspace_id,
        template_id=current.id,
    )
    if default_workspace is not None:
        default_workspace.default_summary_template_key = revised.template_key
        default_workspace.default_summary_template_id = revised.id
        default_workspace.default_summary_template_version = revised.version
    await db.commit()
    return _personal_template_view(revised)


@router.post(
    "/cabinet/summary-templates/{template_id}/duplicate",
    response_model=SummaryTemplateView,
    status_code=201,
    operation_id="duplicateSummaryTemplate",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def duplicate_summary_template_route(
    template_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> SummaryTemplateView:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    source = await _owned_personal_template(
        db,
        workspace_id=tenant_scope.workspace_id,
        owner_user_id=principal.user_id,
        template_id=template_id,
    )
    await _ensure_personal_template_capacity(
        db,
        workspace_id=tenant_scope.workspace_id,
        owner_user_id=principal.user_id,
    )
    duplicate = SummaryTemplate(
        workspace_id=source.workspace_id,
        owner_user_id=source.owner_user_id,
        template_key=f"personal-{uuid4()}",
        kind="personal",
        name=f"{source.name} — копия"[:80],
        purpose=source.purpose,
        sections_json=list(source.sections_json),
        output_language=source.output_language,
        detail_level=source.detail_level,
        version=1,
        status="active",
    )
    db.add(duplicate)
    await db.commit()
    return _personal_template_view(duplicate)


@router.post(
    "/cabinet/summary-templates/{template_id}/archive",
    response_model=SummaryTemplateView,
    operation_id="archiveSummaryTemplate",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def archive_summary_template_route(
    template_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> SummaryTemplateView:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    template = await _owned_personal_template(
        db,
        workspace_id=tenant_scope.workspace_id,
        owner_user_id=principal.user_id,
        template_id=template_id,
    )
    template.status = "archived"
    default_workspace = await _workspace_defaulting_to_template(
        db,
        workspace_id=tenant_scope.workspace_id,
        template_id=template.id,
    )
    if default_workspace is not None:
        _reset_default_summary_template(default_workspace)
    await db.commit()
    return _personal_template_view(template)


@router.delete(
    "/cabinet/summary-templates/{template_id}",
    status_code=204,
    operation_id="deleteSummaryTemplate",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def delete_summary_template_route(
    template_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    template = await _owned_personal_template(
        db,
        workspace_id=tenant_scope.workspace_id,
        owner_user_id=principal.user_id,
        template_id=template_id,
    )
    template.status = "deleted"
    default_workspace = await _workspace_defaulting_to_template(
        db,
        workspace_id=tenant_scope.workspace_id,
        template_id=template.id,
    )
    if default_workspace is not None:
        _reset_default_summary_template(default_workspace)
    await db.commit()
    return Response(status_code=204)


@router.post(
    "/cabinet/meetings/{meeting_id}/summary-candidates",
    response_model=SummaryCandidateResponse,
    status_code=202,
    operation_id="createSummaryCandidate",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def create_summary_candidate_route(
    request: Request,
    meeting_id: UUID,
    payload: CreateSummaryCandidateRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> SummaryCandidateResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    if meeting.created_by_user_id != principal.user_id or decision.state != "owner":
        raise ProblemDetail(
            status=403,
            code="summary_generation_forbidden",
            title="Summary generation is not available",
        )
    settings = request.app.state.settings
    if not settings.outcome_generation_enabled:
        raise ProblemDetail(
            status=503,
            code="summary_generation_unavailable",
            title="Summary generation is temporarily unavailable",
        )
    try:
        attempt = await create_summary_candidate(
            db,
            workspace_id=tenant_scope.workspace_id,
            meeting_id=meeting_id,
            requested_by_user_id=principal.user_id,
            template_key=payload.template_key,
            template_id=payload.template_id,
            template_version=payload.template_version,
            expected_current_outcome_set_id=payload.expected_current_outcome_set_id,
            request_intent=payload.request_intent,
            request_intent_id=payload.request_intent_id,
        )
    except OutcomeGenerationTerminalError as exc:
        _raise_summary_problem(exc)
    dispatch_intent = await ensure_dispatch_intent(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting=meeting,
        candidate_id=attempt.candidate_id,
        idempotency_key=attempt.idempotency_key or f"candidate:{attempt.candidate_id}",
        source_fingerprint=attempt.source_fingerprint,
        payload={
            "candidate_id": str(attempt.candidate_id),
            "source_result_id": str(attempt.source_result_id),
            "template_key": attempt.template_key,
            "template_version": attempt.template_version,
        },
    )
    terminal_dispatch_outcome = {
        "candidate": "completed",
        "accepted": "completed",
        "failed": "failed",
        "rejected": "cancelled",
        "cancelled": "cancelled",
        "stale": "cancelled",
        "expired": "cancelled",
    }.get(attempt.status)
    if terminal_dispatch_outcome is not None:
        dispatch_intent = (
            await finalize_dispatch_for_candidate(
                db,
                workspace_id=tenant_scope.workspace_id,
                candidate_id=attempt.candidate_id,
                outcome=terminal_dispatch_outcome,
                failure_code=attempt.failure_code,
            )
            or dispatch_intent
        )
    await db.commit()
    if dispatch_intent.state not in {"created", "retryable_failed"} or attempt.status in {
        "candidate",
        "accepted",
        "rejected",
        "failed",
        "cancelled",
        "stale",
        "expired",
    }:
        return await _summary_candidate_response_async(db, attempt, meeting.current_outcome_set_id)
    temporal_client = getattr(request.app.state, "outcome_temporal_client", None)
    if temporal_client is None:
        try:
            temporal_client = await connect_temporal_client(settings, outcome_tracing=True)
            request.app.state.outcome_temporal_client = temporal_client
        except Exception:
            temporal_client = None
    await reconcile_dispatch_intent(
        db,
        intent=dispatch_intent,
        settings=settings,
        temporal_client=temporal_client,
    )
    await db.refresh(attempt)
    if (
        dispatch_intent.state == "retryable_failed"
        and attempt.status == "queued"
        and attempt.failure_source == "temporal_dispatch"
    ):
        raise ProblemDetail(
            status=503,
            code="summary_generation_unavailable",
            title="Summary generation is temporarily unavailable",
        )
    return await _summary_candidate_response_async(db, attempt, meeting.current_outcome_set_id)


@router.get(
    "/cabinet/meetings/{meeting_id}/summary-candidates",
    response_model=SummaryCandidateListResponse,
    operation_id="listSummaryCandidates",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def list_summary_candidates_route(
    meeting_id: UUID,
    response: Response,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> SummaryCandidateListResponse:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Pragma"] = "no-cache"
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    if meeting.created_by_user_id != principal.user_id or decision.state != "owner":
        raise ProblemDetail(
            status=404, code="summary_candidate_not_found", title="Summary candidate not found"
        )
    meeting = await lock_meeting_fence(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
    )
    if meeting is None or meeting_is_deleted_or_deleting(meeting):
        raise ProblemDetail(
            status=409,
            code="summary_candidate_unavailable",
            title="Summary candidate is not ready",
        )
    latest_revision = await db.scalar(
        select(MediaRevision)
        .where(
            MediaRevision.workspace_id == tenant_scope.workspace_id,
            MediaRevision.meeting_id == meeting_id,
            MediaRevision.status == "accepted",
            MediaRevision.immutable.is_(True),
        )
        .order_by(MediaRevision.revision_number.desc(), MediaRevision.updated_at.desc())
    )
    latest_result = (
        await processing_store.latest_processing_result(
            db,
            workspace_id=tenant_scope.workspace_id,
            meeting_id=meeting_id,
            media_revision_id=latest_revision.id,
        )
        if latest_revision is not None
        else None
    )
    if latest_result is None:
        return SummaryCandidateListResponse(candidates=[])
    candidate_query = select(MeetingOutcomeGenerationAttempt).where(
        MeetingOutcomeGenerationAttempt.workspace_id == tenant_scope.workspace_id,
        MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
        MeetingOutcomeGenerationAttempt.processing_result_id == latest_result.id,
        # Legacy deterministic/blocked/cancelled attempts predate the
        # candidate lifecycle and intentionally have no candidate_id.
        # They remain durable provenance, but are not owner-review
        # candidates and must never be projected through this API.
        MeetingOutcomeGenerationAttempt.candidate_id.is_not(None),
        # Only the current accepted outcome is reviewable. Older accepted
        # attempts remain audit lineage but are superseded after a later
        # candidate is atomically published.
        or_(
            MeetingOutcomeGenerationAttempt.status != "accepted",
            MeetingOutcomeGenerationAttempt.outcome_set_id == meeting.current_outcome_set_id,
        ),
    )
    # Keep active work visible even when older history is crowded by terminal
    # attempts. The bounded recent history remains the normal path; this small
    # union is the server-authoritative reload/new-device recovery path.
    active_attempts = (
        await db.scalars(
            candidate_query.where(
                MeetingOutcomeGenerationAttempt.status.in_(
                    ("queued", "generating", "blocked_dependency")
                )
            )
        )
    ).all()
    recent_attempts = (
        await db.scalars(
            candidate_query.order_by(MeetingOutcomeGenerationAttempt.created_at.desc()).limit(8)
        )
    ).all()
    current_accepted_attempt = await db.scalar(
        candidate_query.where(
            MeetingOutcomeGenerationAttempt.status == "accepted",
            MeetingOutcomeGenerationAttempt.outcome_set_id == meeting.current_outcome_set_id,
        )
        .order_by(MeetingOutcomeGenerationAttempt.created_at.desc())
        .limit(1)
    )
    active_by_id = {attempt.id: attempt for attempt in active_attempts}
    recent_by_id = {attempt.id: attempt for attempt in recent_attempts}
    if current_accepted_attempt is not None:
        recent_by_id[current_accepted_attempt.id] = current_accepted_attempt
    attempts = sorted(active_by_id.values(), key=lambda attempt: attempt.created_at, reverse=True)
    attempts.extend(
        attempt
        for attempt in sorted(recent_by_id.values(), key=lambda item: item.created_at, reverse=True)
        if attempt.id not in active_by_id
    )
    attempts = attempts[:8]
    template_names = await _summary_candidate_template_names(db, attempts)
    source_revision_label = (
        f"Расшифровка · ревизия {latest_revision.revision_number}, "
        f"результат {latest_result.result_version}"
        if latest_revision is not None
        else f"Расшифровка · результат {latest_result.result_version}"
    )
    return SummaryCandidateListResponse(
        candidates=[
            _summary_candidate_response(
                attempt,
                meeting.current_outcome_set_id,
                template_name=template_names.get(attempt.template_id),
                source_revision_label=source_revision_label,
            )
            for attempt in attempts
        ]
    )


@router.get(
    "/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}/preview",
    response_model=SummaryCandidatePreviewResponse,
    operation_id="previewSummaryCandidate",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def preview_summary_candidate_route(
    meeting_id: UUID,
    candidate_id: UUID,
    response: Response,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> SummaryCandidatePreviewResponse:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Pragma"] = "no-cache"
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    if meeting.created_by_user_id != principal.user_id or decision.state != "owner":
        raise ProblemDetail(
            status=404, code="summary_candidate_not_found", title="Summary candidate not found"
        )
    meeting = await lock_meeting_fence(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
    )
    if meeting is None or meeting_is_deleted_or_deleting(meeting):
        raise ProblemDetail(
            status=409,
            code="summary_candidate_unavailable",
            title="Summary candidate is not ready",
        )
    attempt = await db.scalar(
        select(MeetingOutcomeGenerationAttempt).where(
            MeetingOutcomeGenerationAttempt.workspace_id == tenant_scope.workspace_id,
            MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
            MeetingOutcomeGenerationAttempt.candidate_id == candidate_id,
        )
    )
    if (
        attempt is None
        or attempt.outcome_set_id is None
        or attempt.status not in {"candidate", "accepted"}
    ):
        raise ProblemDetail(
            status=409, code="summary_candidate_unavailable", title="Summary candidate is not ready"
        )
    if is_expired(attempt.expires_at):
        raise ProblemDetail(
            status=409, code="summary_candidate_expired", title="Summary candidate has expired"
        )
    if not await _summary_candidate_source_is_current(db, attempt):
        raise ProblemDetail(
            status=409,
            code="summary_source_revision_stale",
            title="Summary candidate source revision is stale",
        )
    if attempt.status == "accepted" and attempt.outcome_set_id != meeting.current_outcome_set_id:
        raise ProblemDetail(
            status=409, code="summary_candidate_unavailable", title="Summary candidate is not ready"
        )
    outcome_set = await db.scalar(
        select(MeetingOutcomeSet).where(
            MeetingOutcomeSet.workspace_id == tenant_scope.workspace_id,
            MeetingOutcomeSet.meeting_id == meeting_id,
            MeetingOutcomeSet.id == attempt.outcome_set_id,
        )
    )
    if outcome_set is None or outcome_set.lifecycle_state != "active":
        raise ProblemDetail(
            status=409, code="summary_candidate_unavailable", title="Summary candidate is not ready"
        )
    preview_categories = {
        "summary",
        "key_points",
        "decisions",
        "action_items",
        "followups",
        "risks",
        "questions",
        "evidence",
    }
    items = (
        await db.scalars(
            select(MeetingOutcomeItem)
            .where(
                MeetingOutcomeItem.workspace_id == tenant_scope.workspace_id,
                MeetingOutcomeItem.meeting_id == meeting_id,
                MeetingOutcomeItem.outcome_set_id == attempt.outcome_set_id,
                MeetingOutcomeItem.state == "available",
                MeetingOutcomeItem.category.in_(preview_categories),
            )
            .order_by(MeetingOutcomeItem.category, MeetingOutcomeItem.sequence)
            .limit(200)
        )
    ).all()
    segments_by_id = await _summary_candidate_segments_by_id(db, attempt)
    return SummaryCandidatePreviewResponse(
        candidate_id=candidate_id,
        outcome_set_id=attempt.outcome_set_id,
        template_key=attempt.template_key,
        items=[
            _summary_candidate_preview_item(item, segments_by_id)
            for item in items
            if item.category in preview_categories
        ],
    )


@router.get(
    "/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}",
    response_model=SummaryCandidateResponse,
    operation_id="getSummaryCandidate",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def get_summary_candidate_route(
    meeting_id: UUID,
    candidate_id: UUID,
    response: Response,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> SummaryCandidateResponse:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Pragma"] = "no-cache"
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    if meeting.created_by_user_id != principal.user_id or decision.state != "owner":
        raise ProblemDetail(
            status=404, code="summary_candidate_not_found", title="Summary candidate not found"
        )
    meeting = await lock_meeting_fence(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
    )
    if meeting is None or meeting_is_deleted_or_deleting(meeting):
        raise ProblemDetail(
            status=409,
            code="summary_candidate_unavailable",
            title="Summary candidate is not ready",
        )
    attempt = await db.scalar(
        select(MeetingOutcomeGenerationAttempt).where(
            MeetingOutcomeGenerationAttempt.workspace_id == tenant_scope.workspace_id,
            MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
            MeetingOutcomeGenerationAttempt.candidate_id == candidate_id,
        )
    )
    if attempt is None:
        raise ProblemDetail(
            status=404, code="summary_candidate_not_found", title="Summary candidate not found"
        )
    if not await _summary_candidate_source_is_current(db, attempt):
        raise ProblemDetail(
            status=409,
            code="summary_source_revision_stale",
            title="Summary candidate source revision is stale",
        )
    if attempt.status == "accepted" and attempt.outcome_set_id != meeting.current_outcome_set_id:
        raise ProblemDetail(
            status=409,
            code="summary_candidate_unavailable",
            title="Summary candidate is not ready",
        )
    if attempt.outcome_set_id is not None:
        outcome_set = await db.scalar(
            select(MeetingOutcomeSet).where(
                MeetingOutcomeSet.workspace_id == tenant_scope.workspace_id,
                MeetingOutcomeSet.meeting_id == meeting_id,
                MeetingOutcomeSet.id == attempt.outcome_set_id,
            )
        )
        if outcome_set is None or outcome_set.lifecycle_state != "active":
            raise ProblemDetail(
                status=409,
                code="summary_candidate_unavailable",
                title="Summary candidate is not ready",
            )
    return await _summary_candidate_response_async(db, attempt, meeting.current_outcome_set_id)


@router.post(
    "/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}/accept",
    response_model=SummaryCandidateResponse,
    operation_id="acceptSummaryCandidate",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def accept_summary_candidate_route(
    meeting_id: UUID,
    candidate_id: UUID,
    payload: ResolveSummaryCandidateRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> SummaryCandidateResponse:
    return await _resolve_summary_candidate_route(
        meeting_id=meeting_id,
        candidate_id=candidate_id,
        accept=True,
        payload=payload,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
    )


@router.post(
    "/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}/reject",
    response_model=SummaryCandidateResponse,
    operation_id="rejectSummaryCandidate",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def reject_summary_candidate_route(
    meeting_id: UUID,
    candidate_id: UUID,
    payload: ResolveSummaryCandidateRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> SummaryCandidateResponse:
    return await _resolve_summary_candidate_route(
        meeting_id=meeting_id,
        candidate_id=candidate_id,
        accept=False,
        payload=payload,
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
    )


async def _resolve_summary_candidate_route(
    *,
    meeting_id: UUID,
    candidate_id: UUID,
    accept: bool,
    payload: ResolveSummaryCandidateRequest,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
    db: AsyncSession | None,
) -> SummaryCandidateResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    if meeting.created_by_user_id != principal.user_id or decision.state != "owner":
        raise ProblemDetail(
            status=403, code="summary_resolution_forbidden", title="Summary action is not available"
        )
    try:
        await resolve_summary_candidate(
            db,
            workspace_id=tenant_scope.workspace_id,
            meeting_id=meeting_id,
            candidate_id=candidate_id,
            requested_by_user_id=principal.user_id,
            accept=accept,
            expected_current_outcome_set_id=payload.expected_current_outcome_set_id,
        )
    except OutcomeGenerationTerminalError as exc:
        # A stale candidate is closed inside the service before the bounded
        # 409 is raised. Commit that dismissal so server-authoritative recovery
        # does not resurrect the same candidate after a reload.
        if str(exc) in {
            "summary_transcript_changed",
            "summary_candidate_expired",
            "summary_source_revision_stale",
        }:
            await db.commit()
        _raise_summary_problem(exc)
    await db.commit()
    attempt = await db.scalar(
        select(MeetingOutcomeGenerationAttempt).where(
            MeetingOutcomeGenerationAttempt.workspace_id == tenant_scope.workspace_id,
            MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
            MeetingOutcomeGenerationAttempt.candidate_id == candidate_id,
        )
    )
    if attempt is None:
        raise ProblemDetail(
            status=404,
            code="summary_candidate_not_found",
            title="Summary candidate not found",
        )
    return await _summary_candidate_response_async(db, attempt, meeting.current_outcome_set_id)


@router.post(
    "/cabinet/meetings/{meeting_id}/shares",
    response_model=ShareGrantResponse,
    status_code=201,
    operation_id="createMeetingShareGrant",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def create_meeting_share_grant_route(
    request: Request,
    meeting_id: UUID,
    payload: CreateShareGrantRequest,
    response: Response,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    db: AsyncSession | None = DbDependency,
) -> ShareGrantResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, _decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    settings = request.app.state.settings
    broader_audience_enabled = {
        "workspace": settings.share_workspace_audience_enabled,
        "team": settings.share_team_audience_enabled,
        "link": (
            settings.share_public_links_enabled and settings.share_public_links_abuse_gate_approved
        ),
    }.get(payload.audience_type, True)
    grant, raw_token = await create_scoped_share_grant(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting=meeting,
        actor_user_id=principal.user_id,
        device_id=device.device_id,
        audience_type=payload.audience_type,
        audience_id=payload.audience_id,
        content_scope=payload.content_scope,
        can_download=payload.can_download,
        can_export=payload.can_export,
        expires_at=payload.expires_at,
        broader_audience_enabled=broader_audience_enabled,
    )
    await db.commit()
    notification_status = await _send_internal_share_notification(
        db,
        request=request,
        meeting=meeting,
        grant=grant,
        recipient_user_id=payload.audience_id,
        inviter_user_id=principal.user_id,
    )
    grant.metadata_json = {
        **(grant.metadata_json or {}),
        "internal_notification_status": notification_status,
    }
    await db.commit()
    _mark_share_secret_response(response)
    return ShareGrantResponse(
        grant=grant_view(grant, display_name="Authenticated user"),
        share_url=(
            f"/api/v1/cabinet/public-shares/{raw_token}?workspace_id={tenant_scope.workspace_id}"
            if payload.audience_type == "link"
            else (
                f"/meetings/{meeting_id}"
                if payload.audience_type == "workspace"
                else (f"/api/v1/cabinet/share/{raw_token}?workspace_id={tenant_scope.workspace_id}")
            )
        ),
        notification_status=notification_status,
    )


async def _search_meeting_share_recipients(
    *,
    meeting_id: UUID | None,
    query: str,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
    device: DeviceContext,
    db: AsyncSession | None,
) -> ShareRecipientListResponse:
    if db is None:
        raise ProblemDetail(
            status=503,
            code="cabinet_store_unavailable",
            title="Cabinet store unavailable",
        )
    if meeting_id is None:
        # Keep the legacy workspace-only endpoint inert instead of allowing it
        # to become an identity enumeration primitive.
        return ShareRecipientListResponse(items=[])
    _meeting, decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    if not decision.can_share:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    rows = await search_share_recipients(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
        device_id=device.device_id,
        query=query,
    )
    return ShareRecipientListResponse(
        items=[
            ShareRecipientView(
                user_id=row.user_id,
                display_label=row.display_label,
                source=row.source,
                recipient_type=row.recipient_type,
                freshness=row.freshness,
            )
            for row in rows
        ]
    )


@router.get(
    "/cabinet/share-recipients",
    response_model=ShareRecipientListResponse,
    operation_id="searchMeetingShareRecipients",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def search_legacy_share_recipients_route(
    query: str = Query(min_length=0, max_length=80),
    meeting_id: UUID | None = ShareRecipientsMeetingIdQuery,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    db: AsyncSession | None = DbDependency,
) -> ShareRecipientListResponse:
    return await _search_meeting_share_recipients(
        meeting_id=meeting_id,
        query=query,
        tenant_scope=tenant_scope,
        principal=principal,
        device=device,
        db=db,
    )


@router.get(
    "/cabinet/meetings/{meeting_id}/share-recipients",
    response_model=ShareRecipientListResponse,
    operation_id="searchMeetingShareRecipientsForMeeting",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def search_meeting_share_recipients_route(
    meeting_id: UUID,
    query: str = Query(min_length=0, max_length=80),
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    db: AsyncSession | None = DbDependency,
) -> ShareRecipientListResponse:
    return await _search_meeting_share_recipients(
        meeting_id=meeting_id,
        query=query,
        tenant_scope=tenant_scope,
        principal=principal,
        device=device,
        db=db,
    )


@router.post(
    "/cabinet/meetings/{meeting_id}/shares/{grant_id}/rotate",
    response_model=ShareGrantResponse,
    operation_id="rotateMeetingShareLink",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def rotate_meeting_share_link_route(
    meeting_id: UUID,
    grant_id: UUID,
    response: Response,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    db: AsyncSession | None = DbDependency,
) -> ShareGrantResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, _ = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    grant, raw_token = await rotate_share_link(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting=meeting,
        actor_user_id=principal.user_id,
        device_id=device.device_id,
        grant_id=grant_id,
    )
    await db.commit()
    _mark_share_secret_response(response)
    return ShareGrantResponse(
        grant=grant_view(grant, display_name="Ссылка"),
        share_url=(
            (f"/api/v1/cabinet/public-shares/{raw_token}?workspace_id={tenant_scope.workspace_id}")
            if grant.audience_type == "link"
            else (f"/api/v1/cabinet/share/{raw_token}?workspace_id={tenant_scope.workspace_id}")
        ),
        notification_status="not_attempted",
    )


@router.post(
    "/cabinet/meetings/{meeting_id}/share-invitations",
    response_model=MeetingShareInvitationResponse,
    status_code=202,
    operation_id="createMeetingShareInvitation",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def create_meeting_share_invitation_route(
    request: Request,
    meeting_id: UUID,
    payload: CreateMeetingShareInvitationRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    db: AsyncSession | None = DbDependency,
) -> MeetingShareInvitationResponse:
    settings = request.app.state.settings
    if not settings.share_external_invitations_enabled:
        raise ProblemDetail(
            status=403,
            code="share_invitations_disabled",
            title="External invitations are disabled",
            detail="Choose a member of the current workspace instead.",
        )
    if db is None or settings.credential_encryption_key_file is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, _ = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    invitation = await create_share_invitation(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting=meeting,
        actor_user_id=principal.user_id,
        device_id=device.device_id,
        address=payload.address,
        content_scope=payload.content_scope,
        can_download=payload.can_download,
        can_export=payload.can_export,
        encryption_key=settings.credential_encryption_key_file.read_bytes().strip(),
        ttl_seconds=settings.share_invitation_ttl_seconds,
    )
    should_start_delivery = invitation.status == "pending"
    # Commit the invitation before starting Temporal. A worker uses its own
    # transaction and must never race an uncommitted invitation row.
    await db.commit()
    if not should_start_delivery:
        return MeetingShareInvitationResponse(
            invitation_id=invitation.id,
            status=invitation.status,
            expires_at=invitation.expires_at,
        )
    try:
        temporal_client = getattr(request.app.state, "temporal_client", None)
        if temporal_client is None:
            temporal_client = await connect_temporal_client(settings)
        await start_invitation_delivery_workflow(
            temporal_client=temporal_client,
            settings=settings,
            invitation_id=invitation.id,
            workspace_id=tenant_scope.workspace_id,
        )
    except Exception as exc:
        invitation.status = "outcome_unknown"
        invitation.failure_code = "delivery_workflow_start_unknown"
        await db.commit()
        raise ProblemDetail(
            status=503,
            code="postal_delivery_outcome_unknown",
            title="Delivery outcome is unknown",
            detail="The invitation was saved, but its delivery workflow did not start. Check the invitation status before retrying.",
        ) from exc
    return MeetingShareInvitationResponse(
        invitation_id=invitation.id,
        status=invitation.status,
        expires_at=invitation.expires_at,
    )


@router.delete(
    "/cabinet/meetings/{meeting_id}/share-invitations/{invitation_id}",
    status_code=204,
    operation_id="revokeMeetingShareInvitation",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def revoke_meeting_share_invitation_route(
    request: Request,
    meeting_id: UUID,
    invitation_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    db: AsyncSession | None = DbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, _ = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    await revoke_share_invitation(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting=meeting,
        actor_user_id=principal.user_id,
        device_id=device.device_id,
        invitation_id=invitation_id,
    )
    await db.commit()
    temporal_client = getattr(request.app.state, "temporal_client", None)
    if temporal_client is not None:
        await cancel_invitation_delivery_workflow(
            temporal_client=temporal_client,
            invitation_id=invitation_id,
        )
    return Response(status_code=204)


@router.delete(
    "/cabinet/meetings/{meeting_id}/shares/{grant_id}",
    status_code=204,
    operation_id="revokeMeetingShareGrant",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
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
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
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
    request: Request,
    share_token: str,
    workspace_id: Annotated[UUID, Query()],
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    recipient_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = PublicShareDbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    recipient_proof = await _recipient_share_access_proof(
        request,
        recipient_scope=recipient_scope,
        owner_workspace_id=workspace_id,
    )
    meeting = await resolve_share_token(
        db,
        workspace_id=workspace_id,
        viewer_user_id=principal.user_id,
        device_id=device.device_id,
        share_token=share_token,
        recipient_proof=recipient_proof,
    )
    if meeting is None:
        raise ProblemDetail(status=404, code="share_not_found", title="Share not found")
    decision = await decide_meeting_access(
        db,
        meeting,
        workspace_id=workspace_id,
        viewer_user_id=principal.user_id,
        recipient_proof=recipient_proof,
    )
    if not decision.can_view_full_meeting:
        items = []
        outcome_set = await current_outcome_set(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting.id,
            processing_result_id=None,
        )
        if outcome_set is not None:
            items = (
                await db.scalars(
                    select(MeetingOutcomeItem)
                    .where(
                        MeetingOutcomeItem.workspace_id == workspace_id,
                        MeetingOutcomeItem.outcome_set_id == outcome_set.id,
                        MeetingOutcomeItem.state == "available",
                    )
                    .order_by(MeetingOutcomeItem.category, MeetingOutcomeItem.sequence)
                )
            ).all()
        projection = narrow_summary_projection(
            meeting_label=meeting.title or "Встреча",
            occurred_at=meeting.started_at or meeting.created_at,
            duration_seconds=meeting.duration_seconds,
            summary_sections=[
                {"category": item.category, "text": item.text or ""} for item in items
            ],
        )
        await db.commit()
        if "text/html" in request.headers.get("accept", "").lower():
            response = cabinet_html_response(
                render_shared_meeting_summary_page(
                    meeting_title=str(projection["meeting_label"]),
                    occurred_at=projection["occurred_at"],
                    duration_seconds=int(projection["duration_seconds"]),
                    summary_sections=projection["summary_sections"],
                    authenticated=True,
                )
            )
            _mark_share_secret_response(response)
            return response
        response = JSONResponse(
            PublicShareSummaryResponse.model_validate(projection).model_dump(mode="json")
        )
        _mark_share_secret_response(response)
        return response
    await db.commit()
    if recipient_proof.workspace_membership_is_active:
        return RedirectResponse(url=f"/meetings/{meeting.id}", status_code=302)
    return RedirectResponse(
        url=(f"/shared-meetings/{meeting.id}?workspace_id={workspace_id}"),
        status_code=302,
    )


@router.get(
    "/cabinet/public-shares/{share_token}",
    response_model=PublicShareSummaryResponse,
    operation_id="resolvePublicMeetingShare",
)
async def resolve_public_meeting_share_route(
    request: Request,
    share_token: str,
    workspace_id: Annotated[UUID, Query()],
    db: AsyncSession | None = PublicShareDbDependency,
) -> Response | PublicShareSummaryResponse:
    settings = request.app.state.settings
    if (
        not settings.share_public_links_enabled
        or not settings.share_public_links_abuse_gate_approved
        or db is None
    ):
        raise ProblemDetail(status=404, code="share_not_found", title="Share not found")
    grant = await db.scalar(
        select(MeetingShareGrant).where(
            MeetingShareGrant.workspace_id == workspace_id,
            MeetingShareGrant.audience_type == "link",
            MeetingShareGrant.share_token_hash == hash_share_token(share_token),
            MeetingShareGrant.status == "active",
            MeetingShareGrant.content_scope == "summary_only",
            (
                MeetingShareGrant.expires_at.is_(None)
                | (MeetingShareGrant.expires_at > datetime.now(UTC))
            ),
        )
    )
    if grant is None:
        raise ProblemDetail(status=404, code="share_not_found", title="Share not found")
    try:
        meeting = await lock_shareable_meeting(
            db, workspace_id=workspace_id, meeting_id=grant.meeting_id
        )
    except ProblemDetail:
        raise ProblemDetail(status=404, code="share_not_found", title="Share not found") from None
    grant = await db.scalar(
        select(MeetingShareGrant)
        .where(
            MeetingShareGrant.id == grant.id,
            MeetingShareGrant.workspace_id == workspace_id,
            MeetingShareGrant.audience_type == "link",
            MeetingShareGrant.share_token_hash == hash_share_token(share_token),
            MeetingShareGrant.status == "active",
            MeetingShareGrant.content_scope == "summary_only",
            (
                MeetingShareGrant.expires_at.is_(None)
                | (MeetingShareGrant.expires_at > datetime.now(UTC))
            ),
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if grant is None:
        raise ProblemDetail(status=404, code="share_not_found", title="Share not found")
    items = []
    outcome_set = await current_outcome_set(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting.id,
        processing_result_id=None,
    )
    if outcome_set is not None:
        items = (
            await db.scalars(
                select(MeetingOutcomeItem)
                .where(
                    MeetingOutcomeItem.workspace_id == workspace_id,
                    MeetingOutcomeItem.outcome_set_id == outcome_set.id,
                    MeetingOutcomeItem.state == "available",
                )
                .order_by(MeetingOutcomeItem.category, MeetingOutcomeItem.sequence)
            )
        ).all()
    projection = narrow_summary_projection(
        meeting_label=meeting.title or "Встреча",
        occurred_at=meeting.started_at or meeting.created_at,
        duration_seconds=meeting.duration_seconds,
        summary_sections=[{"category": item.category, "text": item.text or ""} for item in items],
    )
    grant.last_used_at = datetime.now(UTC)
    await db.commit()
    if "text/html" in request.headers.get("accept", "").lower():
        response = cabinet_html_response(
            render_shared_meeting_summary_page(
                meeting_title=str(projection["meeting_label"]),
                occurred_at=projection["occurred_at"],
                duration_seconds=int(projection["duration_seconds"]),
                summary_sections=projection["summary_sections"],
                authenticated=False,
            )
        )
        _mark_share_secret_response(response)
        return response
    return PublicShareSummaryResponse.model_validate(projection)


@router.post(
    "/cabinet/share-invitations/{share_token}/accept",
    response_model=ShareGrantResponse,
    operation_id="acceptMeetingShareInvitation",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def accept_meeting_share_invitation_route(
    request: Request,
    share_token: str,
    response: Response,
    workspace_id: Annotated[UUID, Query()],
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    recipient_scope: TenantScope = TenantDependency,
    db: AsyncSession | None = PublicShareDbDependency,
) -> Response | ShareGrantResponse:
    settings = request.app.state.settings
    if db is None or settings.credential_encryption_key_file is None:
        raise ProblemDetail(status=404, code="invitation_not_found", title="Invitation not found")
    verified_address_hashes = await _verified_invitation_address_hashes(
        request,
        recipient_scope=recipient_scope,
    )
    recipient_proof = await _recipient_share_access_proof(
        request,
        recipient_scope=recipient_scope,
        owner_workspace_id=workspace_id,
    )
    accepted = await accept_share_invitation(
        db,
        workspace_id=workspace_id,
        user_id=principal.user_id,
        device_id=device.device_id,
        raw_token=share_token,
        verified_address_hashes=verified_address_hashes,
        encryption_key=settings.credential_encryption_key_file.read_bytes().strip(),
        recipient_user_active=recipient_proof.user_is_active,
    )
    if accepted is None:
        raise ProblemDetail(status=404, code="invitation_not_found", title="Invitation not found")
    grant, grant_raw_token = accepted
    if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
        meeting = await db.get(Meeting, grant.meeting_id)
        if meeting is None:
            raise ProblemDetail(
                status=404, code="invitation_not_found", title="Invitation not found"
            )
        if grant.content_scope == "full_meeting" and grant.can_download and grant.can_export:
            await db.commit()
            return RedirectResponse(
                url=(f"/shared-meetings/{meeting.id}?workspace_id={workspace_id}"),
                status_code=303,
            )
        outcome_set = await current_outcome_set(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting.id,
            processing_result_id=None,
        )
        items = []
        if outcome_set is not None:
            items = (
                await db.scalars(
                    select(MeetingOutcomeItem)
                    .where(
                        MeetingOutcomeItem.workspace_id == workspace_id,
                        MeetingOutcomeItem.outcome_set_id == outcome_set.id,
                        MeetingOutcomeItem.state == "available",
                    )
                    .order_by(MeetingOutcomeItem.category, MeetingOutcomeItem.sequence)
                )
            ).all()
        projection = narrow_summary_projection(
            meeting_label=meeting.title or "Встреча",
            occurred_at=meeting.started_at or meeting.created_at,
            duration_seconds=meeting.duration_seconds,
            summary_sections=[
                {"category": item.category, "text": item.text or ""} for item in items
            ],
        )
        await db.commit()
        html_response = cabinet_html_response(
            render_shared_meeting_summary_page(
                meeting_title=str(projection["meeting_label"]),
                occurred_at=projection["occurred_at"],
                duration_seconds=int(projection["duration_seconds"]),
                summary_sections=projection["summary_sections"],
                authenticated=True,
            )
        )
        _mark_share_secret_response(html_response)
        return html_response
    await db.commit()
    _mark_share_secret_response(response)
    response = ShareGrantResponse(
        grant=grant_view(grant, display_name="Authenticated user"),
        share_url=(f"/api/v1/cabinet/share/{grant_raw_token}?workspace_id={workspace_id}"),
    )
    return response


@router.get(
    "/cabinet/meetings/{meeting_id}/playback",
    operation_id="playCabinetMeetingAudio",
    dependencies=[PrincipalDependency, DeviceDependency],
    response_class=StreamingResponse,
    responses=PLAYBACK_RESPONSES,
)
async def play_cabinet_meeting_audio_route(
    meeting_id: UUID,
    range_header: Annotated[
        str | None,
        Header(
            alias="Range",
            description="Optional single RFC 9110 byte range, for example `bytes=0-1023`.",
        ),
    ] = None,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = DbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    if not decision.can_view_full_meeting:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    playback = await playback_artifact(
        db,
        storage=storage,
        meeting=meeting,
        access=decision,
        actor_user_id=principal.user_id,
        device_id=device.device_id,
        range_header=range_header,
    )
    await db.commit()
    return StreamingResponse(
        playback.body,
        media_type=playback.media_type,
        status_code=playback.status_code,
        headers=playback.headers,
    )


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
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    if not decision.can_view_full_meeting and artifact_class != "summary":
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    result = await latest_processing_result(
        db, workspace_id=tenant_scope.workspace_id, meeting_id=meeting_id
    )
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
    headers = {
        "Content-Disposition": f'attachment; filename="{download.filename}"',
        "Content-Length": str(download.byte_length),
    }
    if not isinstance(download.body, bytes):
        return StreamingResponse(
            download.body,
            media_type=download.media_type,
            headers=headers,
        )
    return Response(
        content=download.body,
        media_type=download.media_type,
        headers=headers,
    )


@router.get(
    "/cabinet/shared-meetings/{meeting_id}/playback",
    operation_id="playSharedMeetingAudio",
    dependencies=[PrincipalDependency, DeviceDependency],
    response_class=StreamingResponse,
    responses=PLAYBACK_RESPONSES,
)
async def play_shared_meeting_audio_route(
    request: Request,
    meeting_id: UUID,
    workspace_id: Annotated[UUID, Query()],
    range_header: Annotated[
        str | None,
        Header(
            alias="Range",
            description="Optional single RFC 9110 byte range, for example `bytes=0-1023`.",
        ),
    ] = None,
    recipient_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = PublicShareDbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, decision, recipient_proof = await _authorized_shared_meeting(
        request,
        db,
        owner_workspace_id=workspace_id,
        meeting_id=meeting_id,
        principal=principal,
        recipient_scope=recipient_scope,
    )
    playback = await playback_artifact(
        db,
        storage=storage,
        meeting=meeting,
        access=decision,
        actor_user_id=principal.user_id,
        device_id=device.device_id,
        range_header=range_header,
        recipient_proof=recipient_proof,
    )
    await db.commit()
    return StreamingResponse(
        playback.body,
        media_type=playback.media_type,
        status_code=playback.status_code,
        headers=playback.headers,
    )


@router.get(
    "/cabinet/shared-meetings/{meeting_id}/downloads/{artifact_class}",
    operation_id="downloadSharedMeetingArtifact",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def download_shared_meeting_artifact_route(
    request: Request,
    meeting_id: UUID,
    artifact_class: ArtifactClass,
    workspace_id: Annotated[UUID, Query()],
    recipient_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = PublicShareDbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, decision, recipient_proof = await _authorized_shared_meeting(
        request,
        db,
        owner_workspace_id=workspace_id,
        meeting_id=meeting_id,
        principal=principal,
        recipient_scope=recipient_scope,
    )
    result = await latest_processing_result(db, workspace_id=workspace_id, meeting_id=meeting_id)
    download = await download_artifact(
        db,
        storage=storage,
        meeting=meeting,
        access=decision,
        artifact_class=artifact_class,
        result=result,
        actor_user_id=principal.user_id,
        device_id=device.device_id,
        recipient_proof=recipient_proof,
    )
    await db.commit()
    headers = {
        "Content-Disposition": f'attachment; filename="{download.filename}"',
        "Content-Length": str(download.byte_length),
    }
    if not isinstance(download.body, bytes):
        return StreamingResponse(
            download.body,
            media_type=download.media_type,
            headers=headers,
        )
    return Response(
        content=download.body,
        media_type=download.media_type,
        headers=headers,
    )


@router.get(
    "/cabinet/shared-meetings/{meeting_id}/content-exports",
    response_model=ContentExportCapabilityResponse,
    operation_id="getSharedMeetingContentExportCapabilities",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def get_shared_meeting_content_export_capabilities_route(
    request: Request,
    meeting_id: UUID,
    workspace_id: Annotated[UUID, Query()],
    recipient_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = PublicShareDbDependency,
) -> ContentExportCapabilityResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, decision, _recipient_proof = await _authorized_shared_meeting(
        request,
        db,
        owner_workspace_id=workspace_id,
        meeting_id=meeting_id,
        principal=principal,
        recipient_scope=recipient_scope,
    )
    result = await latest_processing_result(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
    )
    return await content_export_capabilities(db, meeting=meeting, access=decision, result=result)


@router.post(
    "/cabinet/shared-meetings/{meeting_id}/content-exports",
    operation_id="createSharedMeetingContentExport",
    response_class=Response,
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def create_shared_meeting_content_export_route(
    request: Request,
    meeting_id: UUID,
    workspace_id: Annotated[UUID, Query()],
    payload: ContentExportSelectionRequest,
    recipient_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    db: AsyncSession | None = PublicShareDbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, decision, recipient_proof = await _authorized_shared_meeting(
        request,
        db,
        owner_workspace_id=workspace_id,
        meeting_id=meeting_id,
        principal=principal,
        recipient_scope=recipient_scope,
    )
    result = await latest_processing_result(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
    )
    generated = await create_content_export(
        db,
        meeting=meeting,
        access=decision,
        result=result,
        selection=ExportSelection(
            content_scope=payload.content_scope,
            format=payload.format,
            processing_result_id=payload.processing_result_id,
            outcome_set_id=payload.outcome_set_id,
            include_speaker_labels=payload.include_speaker_labels,
            include_timestamps=payload.include_timestamps,
            include_evidence=payload.include_evidence,
        ),
        actor_user_id=principal.user_id,
        device_id=device.device_id,
        recipient_proof=recipient_proof,
    )
    await db.commit()
    return Response(
        content=generated.body,
        media_type=generated.media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{generated.filename}"; '
                f"filename*=UTF-8''{generated.filename}"
            ),
            "Content-Length": str(generated.byte_length),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
            "Pragma": "no-cache",
        },
    )


@router.get(
    "/cabinet/meetings/{meeting_id}/content-exports",
    response_model=ContentExportCapabilityResponse,
    operation_id="getMeetingContentExportCapabilities",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def get_meeting_content_export_capabilities_route(
    meeting_id: UUID,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = DbDependency,
) -> ContentExportCapabilityResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, decision = await _authorized_content_export_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    result = await latest_processing_result(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
    )
    return await content_export_capabilities(db, meeting=meeting, access=decision, result=result)


@router.post(
    "/cabinet/meetings/{meeting_id}/content-exports",
    operation_id="createMeetingContentExport",
    response_class=Response,
    responses={
        200: {
            "description": "Revision-pinned content export",
            "content": {
                media_type: {"schema": {"type": "string", "format": "binary"}}
                for media_type in dict.fromkeys(
                    value.partition(";")[0] for value in MEDIA_TYPES.values()
                )
            },
        }
    },
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def create_meeting_content_export_route(
    meeting_id: UUID,
    payload: ContentExportSelectionRequest,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    db: AsyncSession | None = DbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, decision = await _authorized_content_export_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    if (
        decision.state != "deleted"
        and not decision.can_view_full_meeting
        and payload.content_scope != "summary"
    ):
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    result = await latest_processing_result(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
    )
    generated = await create_content_export(
        db,
        meeting=meeting,
        access=decision,
        result=result,
        selection=ExportSelection(
            content_scope=payload.content_scope,
            format=payload.format,
            processing_result_id=payload.processing_result_id,
            outcome_set_id=payload.outcome_set_id,
            include_speaker_labels=payload.include_speaker_labels,
            include_timestamps=payload.include_timestamps,
            include_evidence=payload.include_evidence,
        ),
        actor_user_id=principal.user_id,
        device_id=device.device_id,
    )
    await db.commit()
    filename = generated.filename
    headers = {
        "Content-Disposition": (
            f"attachment; filename=\"{filename}\"; filename*=UTF-8''{filename}"
        ),
        "Content-Length": str(generated.byte_length),
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store",
        "Pragma": "no-cache",
    }
    return Response(content=generated.body, media_type=generated.media_type, headers=headers)


@router.post(
    "/cabinet/meetings/{meeting_id}/exports",
    response_model=ExportPackageResponse,
    status_code=202,
    operation_id="createMeetingExportPackage",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
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
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    meeting, decision = await _authorized_meeting(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
    )
    if not decision.can_view_full_meeting and any(
        artifact != "summary" for artifact in payload.artifact_classes
    ):
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    result = await latest_processing_result(
        db, workspace_id=tenant_scope.workspace_id, meeting_id=meeting_id
    )
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
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
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


@router.post(
    "/internal/retention/run",
    response_model=RetentionRunResponse,
    status_code=202,
    operation_id="runRetentionScan",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def run_retention_scan_route(
    request: Request,
    payload: RetentionRunRequest | None = None,
    tenant_scope: TenantScope = TenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = DbDependency,
) -> RetentionRunResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    await load_admin_workspace_context(db, tenant_scope=tenant_scope, principal=principal)
    retention_payload = payload or RetentionRunRequest()
    response = await run_retention_scan(
        db,
        settings=request.app.state.settings,
        workspace_id=tenant_scope.workspace_id,
        limit=retention_payload.limit,
        dry_run=retention_payload.dry_run,
        storage=storage,
        temporal_client=getattr(request.app.state, "temporal_client", None),
    )
    await db.commit()
    return response


@router.get(
    "/desktop/local-purge-tasks",
    response_model=LocalPurgeTaskList,
    operation_id="listDesktopLocalPurgeTasks",
    dependencies=[PrincipalDependency, DeviceDependency],
)
async def list_desktop_local_purge_tasks_route(
    tenant_scope: TenantScope = TenantDependency,
    device: DeviceContext = DeviceDependency,
    db: AsyncSession | None = DbDependency,
) -> LocalPurgeTaskList:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    tasks = await list_local_purge_tasks(
        db,
        workspace_id=tenant_scope.workspace_id,
        device_id=device.device_id,
    )
    return LocalPurgeTaskList(tasks=tasks)


@router.post(
    "/desktop/local-purge-tasks/{task_id}/ack",
    response_model=LocalPurgeTask,
    operation_id="acknowledgeDesktopLocalPurgeTask",
    dependencies=[PrincipalDependency, DeviceDependency, WebCSRFDependency],
)
async def acknowledge_desktop_local_purge_task_route(
    task_id: UUID,
    payload: LocalPurgeAckRequest,
    tenant_scope: TenantScope = TenantDependency,
    device: DeviceContext = DeviceDependency,
    db: AsyncSession | None = DbDependency,
) -> LocalPurgeTask:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    task = await acknowledge_local_purge_task(
        db,
        workspace_id=tenant_scope.workspace_id,
        device_id=device.device_id,
        task_id=task_id,
        payload=payload,
    )
    await db.commit()
    return task


def _built_in_template_view(definition) -> SummaryTemplateView:
    return SummaryTemplateView(
        template_id=None,
        template_key=definition.key,
        kind="builtin",
        name=definition.name,
        purpose=definition.purpose,
        sections=list(definition.sections),
        output_language="ru",
        detail_level="standard",
        version=definition.version,
        status="active",
        can_edit=False,
        can_duplicate=True,
    )


def _personal_template_view(template: SummaryTemplate) -> SummaryTemplateView:
    return SummaryTemplateView(
        template_id=template.id,
        template_key=template.template_key,
        kind="personal",
        name=template.name,
        purpose=template.purpose,
        sections=list(template.sections_json),
        output_language=template.output_language,
        detail_level=template.detail_level,
        version=template.version,
        status=template.status,
        can_edit=template.status == "active",
        can_duplicate=template.status != "deleted",
    )


async def _owned_personal_template(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    owner_user_id: UUID,
    template_id: UUID,
) -> SummaryTemplate:
    template = await db.scalar(
        select(SummaryTemplate)
        .where(
            SummaryTemplate.id == template_id,
            SummaryTemplate.workspace_id == workspace_id,
            SummaryTemplate.owner_user_id == owner_user_id,
            SummaryTemplate.kind == "personal",
        )
        .with_for_update()
    )
    if template is None:
        raise ProblemDetail(
            status=404, code="summary_template_not_found", title="Template not found"
        )
    return template


async def _workspace_defaulting_to_template(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    template_id: UUID,
) -> Workspace | None:
    return await db.scalar(
        select(Workspace)
        .where(
            Workspace.id == workspace_id,
            Workspace.default_summary_template_id == template_id,
        )
        .with_for_update()
    )


def _reset_default_summary_template(workspace: Workspace) -> None:
    workspace.default_summary_template_key = "graf-auto-v1"
    workspace.default_summary_template_id = None
    workspace.default_summary_template_version = 1


def _summary_candidate_response(
    attempt: MeetingOutcomeGenerationAttempt,
    current_outcome_set_id: UUID | None,
    *,
    template_name: str | None = None,
    source_revision_label: str | None = None,
    preview: list[SummaryCandidatePreviewItem] | None = None,
) -> SummaryCandidateResponse:
    if attempt.candidate_id is None:
        raise ProblemDetail(
            status=500,
            code="summary_candidate_state_invalid",
            title="Summary candidate is invalid",
        )
    state = {
        "queued": "generating",
        "generating": "generating",
        "blocked_dependency": "blocked",
        "candidate": "ready",
        "accepted": "accepted",
        "rejected": "closed",
        "failed": "failed",
        "cancelled": "closed",
        "stale": "stale",
        "expired": "expired",
    }.get(attempt.status, "failed")
    reason_code, retryable, next_action = _summary_candidate_projection(attempt)
    template_definition = BUILT_IN_BY_KEY.get(attempt.template_key or "")
    expiry = normalize_db_timestamp(attempt.expires_at)
    if (
        state in {"generating", "ready", "blocked"}
        and expiry is not None
        and expiry <= datetime.now(UTC)
    ):
        state = "expired"
    if state == "expired":
        reason_code, retryable, next_action = "temporary_unavailable", True, "retry"
    return SummaryCandidateResponse(
        candidate_id=attempt.candidate_id,
        state=state,
        current_outcome_set_id=current_outcome_set_id,
        poll_url=(
            f"/api/v1/cabinet/meetings/{attempt.meeting_id}/summary-candidates/"
            f"{attempt.candidate_id}"
        ),
        outcome_set_id=attempt.outcome_set_id,
        template_key=attempt.template_key,
        template_name=(
            template_definition.name
            if template_definition is not None
            else (template_name or "Личный формат" if attempt.template_id is not None else None)
        ),
        template_id=attempt.template_id,
        template_version=attempt.template_version,
        reason_code=reason_code,
        retryable=retryable,
        next_action=next_action,
        format_name=attempt.display_format_name,
        expires_at=attempt.expires_at,
        preview=preview or [],
        provenance=SummaryCandidateProvenance(
            source_result_id=attempt.source_result_id,
            media_revision_id=attempt.media_revision_id,
            source_revision_label=source_revision_label,
            template_id=attempt.template_id,
            source_result_hash=attempt.source_result_hash,
            template_key=attempt.template_key,
            template_version=attempt.template_version,
            generator_version=attempt.generator_version,
        ),
    )


async def _summary_candidate_template_name(
    db: AsyncSession,
    attempt: MeetingOutcomeGenerationAttempt,
) -> str | None:
    if attempt.template_id is None:
        return None
    return await db.scalar(
        select(SummaryTemplate.name).where(
            SummaryTemplate.id == attempt.template_id,
            SummaryTemplate.workspace_id == attempt.workspace_id,
        )
    )


async def _summary_candidate_template_names(
    db: AsyncSession,
    attempts: list[MeetingOutcomeGenerationAttempt],
) -> dict[UUID, str]:
    template_ids = {attempt.template_id for attempt in attempts if attempt.template_id is not None}
    if not template_ids:
        return {}
    rows = await db.execute(
        select(SummaryTemplate.id, SummaryTemplate.name).where(
            SummaryTemplate.id.in_(template_ids),
            SummaryTemplate.workspace_id == attempts[0].workspace_id,
        )
    )
    return {template_id: name for template_id, name in rows.all()}


def _summary_candidate_projection(
    attempt: MeetingOutcomeGenerationAttempt,
) -> tuple[SummaryCandidateReasonCode | None, bool, SummaryCandidateNextAction | None]:
    """Map internal failure truth to a small, stable cabinet action contract."""
    if attempt.status in {"queued", "generating", "blocked_dependency"}:
        if attempt.failure_code in {
            "summary_generation_unavailable",
            "summary_dispatch_unavailable",
        }:
            return "temporary_unavailable", True, "retry"
        return "generating", False, "wait"
    if attempt.status == "expired":
        return "temporary_unavailable", True, "retry"
    if attempt.status in {"candidate", "accepted"}:
        return None, False, "review" if attempt.status == "candidate" else None
    if attempt.status == "rejected":
        return "dismissed", False, "new_candidate"
    if attempt.status == "cancelled":
        return "cancelled", False, "open_meeting"
    code = attempt.failure_code
    projection = {
        "summary_response_invalid": ("result_invalid", False, "new_candidate"),
        "litellm_invalid_json": ("result_invalid", False, "new_candidate"),
        "litellm_invalid_response": ("result_invalid", False, "new_candidate"),
        "litellm_invalid_structured_output": ("result_invalid", False, "new_candidate"),
        "litellm_request_rejected": ("result_invalid", False, "new_candidate"),
        "summary_transcript_unavailable": ("transcript_unavailable", False, "refresh"),
        "summary_source_unavailable": ("source_unavailable", False, "refresh"),
        "summary_source_revision_unavailable": ("source_unavailable", False, "refresh"),
        "summary_transcript_changed": ("source_changed", False, "refresh"),
        "outcome_transcript_changed": ("source_changed", False, "refresh"),
        "summary_source_result_stale": ("source_changed", False, "refresh"),
        "summary_source_revision_stale": ("source_changed", False, "refresh"),
        "summary_template_unavailable": ("template_unavailable", False, "choose_format"),
        "summary_template_snapshot_invalid": ("template_unavailable", False, "choose_format"),
        "summary_revision_conflict": ("revision_changed", False, "refresh"),
        "summary_generation_in_progress": ("generation_in_progress", False, "refresh_status"),
        "summary_prompt_invalid": ("prompt_invalid", False, "choose_format"),
        "summary_prompt_snapshot_corrupt": ("prompt_invalid", False, "choose_format"),
        "summary_prompt_not_selected": ("prompt_invalid", False, "choose_format"),
        "summary_prompt_not_pinned": ("prompt_invalid", False, "choose_format"),
        "summary_prompt_snapshot_invalid": ("prompt_invalid", False, "choose_format"),
        "summary_prompt_resolution_conflict": ("revision_changed", False, "refresh"),
        "generation_call_not_completed": ("content_unavailable", False, "refresh_status"),
        "generation_call_content_incomplete": ("content_unavailable", False, "refresh_status"),
        "generation_call_content_hash_mismatch": ("content_unavailable", False, "refresh_status"),
        "summary_generation_projection_missing": (
            "content_unavailable",
            False,
            "refresh_status",
        ),
        "summary_provider_outcome_ambiguous": (
            "provider_outcome_unknown",
            False,
            "refresh_status",
        ),
        "summary_provider_attempt_not_retryable": (
            "provider_outcome_unknown",
            False,
            "refresh_status",
        ),
        "litellm_outcome_ambiguous": (
            "provider_outcome_unknown",
            False,
            "refresh_status",
        ),
        "outcome_transcript_oversize": ("input_too_large", False, "open_meeting"),
        "outcome_transcript_chunk_oversize": ("input_too_large", False, "open_meeting"),
        "outcome_transcript_chunk_serialized_oversize": (
            "input_too_large",
            False,
            "open_meeting",
        ),
        "meeting_deleting": ("meeting_deleting", False, "open_meeting"),
        "meeting_deleted": ("meeting_deleted", False, "open_meetings"),
        "summary_generation_retries_exhausted": (
            "temporary_unavailable",
            True,
            "retry",
        ),
        "summary_dispatch_retries_exhausted": (
            "temporary_unavailable",
            True,
            "retry",
        ),
        "langfuse_prompt_unavailable": (
            "prompt_unavailable",
            True,
            "retry",
        ),
        "prompt_snapshot_export_unavailable": (
            "prompt_unavailable",
            True,
            "retry",
        ),
        "litellm_endpoint_unavailable": (
            "provider_unavailable",
            True,
            "retry",
        ),
        "litellm_unavailable": (
            "provider_unavailable",
            True,
            "retry",
        ),
        "litellm_retryable_response": (
            "provider_unavailable",
            True,
            "retry",
        ),
        "litellm_authentication_failed": ("provider_unavailable", False, "refresh"),
        "litellm_credential_unavailable": ("provider_unavailable", False, "refresh"),
        "litellm_not_configured": ("provider_unavailable", False, "refresh"),
    }
    return projection.get(code or "", ("generation_failed", False, "refresh"))


async def _summary_candidate_response_async(
    db: AsyncSession,
    attempt: MeetingOutcomeGenerationAttempt,
    current_outcome_set_id: UUID | None,
) -> SummaryCandidateResponse:
    source_revision_label = None
    source_result: ProcessingResult | None = None
    if attempt.source_result_id is not None:
        source_result = await db.scalar(
            select(ProcessingResult).where(
                ProcessingResult.workspace_id == attempt.workspace_id,
                ProcessingResult.meeting_id == attempt.meeting_id,
                ProcessingResult.id == attempt.source_result_id,
            )
        )
        if source_result is not None:
            if source_result.media_revision_id is not None:
                revision = await db.get(MediaRevision, source_result.media_revision_id)
                if revision is not None:
                    source_revision_label = (
                        f"Расшифровка · ревизия {revision.revision_number}, "
                        f"результат {source_result.result_version}"
                    )
            if source_revision_label is None:
                source_revision_label = f"Расшифровка · результат {source_result.result_version}"
    preview: list[SummaryCandidatePreviewItem] = []
    preview_allowed = not is_expired(attempt.expires_at) and (
        attempt.status == "candidate"
        or (attempt.status == "accepted" and attempt.outcome_set_id == current_outcome_set_id)
    )
    if attempt.outcome_set_id is not None and preview_allowed:
        outcome_set = await db.scalar(
            select(MeetingOutcomeSet).where(
                MeetingOutcomeSet.workspace_id == attempt.workspace_id,
                MeetingOutcomeSet.meeting_id == attempt.meeting_id,
                MeetingOutcomeSet.id == attempt.outcome_set_id,
                MeetingOutcomeSet.lifecycle_state == "active",
            )
        )
        if outcome_set is None:
            return _summary_candidate_response(
                attempt,
                current_outcome_set_id,
                source_revision_label=source_revision_label,
            )
        items = (
            await db.scalars(
                select(MeetingOutcomeItem)
                .where(
                    MeetingOutcomeItem.workspace_id == attempt.workspace_id,
                    MeetingOutcomeItem.meeting_id == attempt.meeting_id,
                    MeetingOutcomeItem.outcome_set_id == attempt.outcome_set_id,
                    MeetingOutcomeItem.state == "available",
                )
                .order_by(MeetingOutcomeItem.category, MeetingOutcomeItem.sequence)
                .limit(24)
            )
        ).all()
        segments_by_id = await _summary_candidate_segments_by_id(db, attempt)
        preview = [_summary_candidate_preview_item(item, segments_by_id) for item in items]
    return _summary_candidate_response(
        attempt,
        current_outcome_set_id,
        source_revision_label=source_revision_label,
        preview=preview,
    )


async def _summary_candidate_segments_by_id(
    db: AsyncSession,
    attempt: MeetingOutcomeGenerationAttempt,
) -> dict[str, OutcomeTranscriptSegment]:
    if attempt.source_result_id is None:
        return {}
    result = await db.scalar(
        select(ProcessingResult).where(
            ProcessingResult.workspace_id == attempt.workspace_id,
            ProcessingResult.meeting_id == attempt.meeting_id,
            ProcessingResult.id == attempt.source_result_id,
        )
    )
    if result is None:
        return {}
    canonical_segments = await load_outcome_transcript_segments(db, result=result)
    segments_by_id = {
        str(segment.segment_id): segment for segment in canonical_segments
    }
    # Keep old source references readable only when one ASR row maps to one
    # canonical provider turn. Ambiguous overlap is intentionally not guessed.
    transcript_rows = (
        await db.scalars(
            select(TranscriptSegment)
            .where(
                TranscriptSegment.workspace_id == result.workspace_id,
                TranscriptSegment.meeting_id == result.meeting_id,
                TranscriptSegment.processing_result_id == result.id,
            )
            .order_by(TranscriptSegment.sequence, TranscriptSegment.start_seconds)
        )
    ).all()
    for row in transcript_rows:
        candidates = [
            segment
            for segment in canonical_segments
            if segment.source_role == row.source_role
            and min(row.end_seconds, segment.end_seconds)
            > max(row.start_seconds, segment.start_seconds)
        ]
        if len(candidates) == 1:
            segments_by_id[str(row.id)] = candidates[0]
    return segments_by_id


def _summary_candidate_preview_item(
    item: MeetingOutcomeItem,
    segments_by_id: dict[str, OutcomeTranscriptSegment],
) -> SummaryCandidatePreviewItem:
    source_refs = []
    seen_segment_ids: set[str] = set()
    for ref in item.source_refs_json if isinstance(item.source_refs_json, list) else []:
        if not isinstance(ref, dict):
            continue
        segment_id = str(ref.get("transcript_segment_id") or "")
        segment = segments_by_id.get(segment_id)
        if segment is None:
            continue
        canonical_segment_id = str(segment.segment_id)
        if canonical_segment_id in seen_segment_ids:
            continue
        seen_segment_ids.add(canonical_segment_id)
        source_refs.append(
            {
                "transcript_segment_id": segment.segment_id,
                "sequence": segment.sequence,
                "start_seconds": float(segment.start_seconds),
                "end_seconds": float(segment.end_seconds),
                "speaker_label": segment.speaker_label,
                "source_role": segment.source_role,
                "evidence_kind": "segment",
                "seekable": True,
            }
        )
        if len(source_refs) == 8:
            break
    return SummaryCandidatePreviewItem(
        category=item.category,
        sequence=item.sequence,
        text=item.text or "",
        owner_text=item.owner_text or "",
        due_date_text=item.due_date_text or "",
        truth_label=item.truth_label or "",
        source_refs=source_refs,
    )


async def _summary_candidate_source_is_current(
    db: AsyncSession,
    attempt: MeetingOutcomeGenerationAttempt,
) -> bool:
    latest_revision = await db.scalar(
        select(MediaRevision)
        .where(
            MediaRevision.workspace_id == attempt.workspace_id,
            MediaRevision.meeting_id == attempt.meeting_id,
            MediaRevision.status == "accepted",
            MediaRevision.immutable.is_(True),
        )
        .order_by(MediaRevision.revision_number.desc(), MediaRevision.updated_at.desc())
    )
    latest_result = (
        await processing_store.latest_processing_result(
            db,
            workspace_id=attempt.workspace_id,
            meeting_id=attempt.meeting_id,
            media_revision_id=latest_revision.id,
        )
        if latest_revision is not None
        else None
    )
    speaker_attribution_current = await candidate_speaker_attribution_is_current(db, attempt)
    return (
        latest_result is not None
        and attempt.processing_result_id == latest_result.id
        and attempt.media_revision_id
        == (latest_revision.id if latest_revision is not None else None)
        and result_source_hash_is_attested(latest_result)
        and attempt.source_result_hash == latest_result.source_result_hash
        and speaker_attribution_current
    )


def _raise_summary_problem(exc: OutcomeGenerationTerminalError) -> None:
    code = str(exc)
    status_code = 409
    if code in {"meeting_not_found", "summary_candidate_unavailable"}:
        status_code = 404
    elif code.endswith("forbidden"):
        status_code = 403
    raise ProblemDetail(
        status=status_code,
        code=code,
        title="Summary request could not be completed",
    )


async def _authorized_meeting(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    viewer_user_id: UUID,
    recipient_proof: ShareRecipientAccessProof | None = None,
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
        recipient_proof=recipient_proof,
    )
    if not decision.can_view:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return meeting, decision


async def _authorized_shared_meeting(
    request: Request,
    db: AsyncSession,
    *,
    owner_workspace_id: UUID,
    meeting_id: UUID,
    principal: AuthenticatedPrincipal,
    recipient_scope: TenantScope,
):
    recipient_proof = await _recipient_share_access_proof(
        request,
        recipient_scope=recipient_scope,
        owner_workspace_id=owner_workspace_id,
    )
    meeting, decision = await _authorized_meeting(
        db,
        workspace_id=owner_workspace_id,
        meeting_id=meeting_id,
        viewer_user_id=principal.user_id,
        recipient_proof=recipient_proof,
    )
    if not decision.can_view_full_meeting:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return meeting, decision, recipient_proof


async def _authorized_content_export_meeting(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    viewer_user_id: UUID,
    recipient_proof: ShareRecipientAccessProof | None = None,
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
        recipient_proof=recipient_proof,
    )
    if decision.state == "deleted":
        await _authorized_lifecycle_meeting(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            viewer_user_id=viewer_user_id,
        )
        return meeting, decision
    if not decision.can_view:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return meeting, decision


async def _authorized_lifecycle_meeting(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    viewer_user_id: UUID,
) -> Meeting:
    meeting = await db.scalar(
        select(Meeting).where(
            Meeting.workspace_id == workspace_id,
            Meeting.id == meeting_id,
        )
    )
    if meeting is None:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    membership = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == viewer_user_id,
            WorkspaceMembership.status == "active",
        )
    )
    role = membership.role if membership is not None else None
    if meeting.created_by_user_id != viewer_user_id and role not in {"owner", "admin"}:
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return meeting


def _ensure_lifecycle_manager(decision) -> None:
    if decision.state != "owner" and decision.role not in {"owner", "admin"}:
        raise ProblemDetail(
            status=403, code="deletion_forbidden", title="Deletion is not available"
        )
