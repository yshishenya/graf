from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.cabinet import (
    PublicShareDbDependency,
    ShareOperationDbDependency,
    _recipient_share_access_proof,
)
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.cabinet.access import (
    consume_share_invitation_continuation,
    create_share_invitation_continuation,
    decide_meeting_access,
    hash_share_token,
    invitation_address_hashes,
    narrow_summary_projection,
    normalize_invitation_address,
    share_invitation_preview,
)
from twobrain_rec_server.cabinet.queries import (
    get_account_profile_view,
    get_cabinet_meeting_review,
    get_calendar_settings_surface,
    list_cabinet_meetings,
    list_shared_with_me_meetings,
    shared_meeting_display_metadata,
)
from twobrain_rec_server.cabinet.rendering import (
    render_meeting_detail_fragment,
    render_meeting_detail_page,
    render_meeting_list_fragment,
    render_meeting_list_page,
    render_meeting_unavailable_page,
    render_share_invitation_accept_page,
    render_shared_meeting_summary_page,
    render_shared_with_me_page,
)
from twobrain_rec_server.cabinet.review_policy_rendering import render_meeting_share_fragment
from twobrain_rec_server.cabinet.summary_sharing import load_shared_summary_projection
from twobrain_rec_server.cabinet.templates import (
    cabinet_html_response,
)
from twobrain_rec_server.cabinet.web_routes.support import (
    CabinetAccessFilter,
    CabinetLimitQuery,
    CabinetSearchQuery,
    CabinetSortQuery,
    CabinetStatusFilter,
    OptionalPrincipalDependency,
    PrincipalDependency,
    StorageDependency,
    WebDbDependency,
    WebTenantDependency,
    _csrf_token_for_principal,
    _is_hx_request,
    _normalize_web_meeting_status_filter,
    _request_path_with_query,
)
from twobrain_rec_server.db.models import (
    ExternalIdentity,
    Meeting,
    MeetingOutcomeItem,
    MeetingShareGrant,
    MeetingShareInvitation,
)
from twobrain_rec_server.db.tenant_context import (
    TenantDatabaseContext,
    apply_tenant_context,
)
from twobrain_rec_server.outcomes.service import (
    load_egress_default_outcome,
    load_meeting_default_slot,
    load_pinned_egress_outcome,
)
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
)
from twobrain_rec_server.workflows.temporal_client import (
    connect_temporal_client,
    start_account_created_email_workflow,
)

router = APIRouter(tags=["cabinet-web"])
MAGIC_LINK_CSRF_COOKIE_NAME = "graf_share_magic_csrf"
MAGIC_LINK_CSRF_TTL_SECONDS = 15 * 60
logger = logging.getLogger(__name__)


def _shared_meeting_url(*, workspace_id: UUID, meeting_id: UUID) -> str:
    return f"/shared-meetings/{meeting_id}?{urlencode({'workspace_id': str(workspace_id)})}"


def _meeting_unavailable_response(
    request: Request,
    *,
    csrf_token: str | None,
) -> HTMLResponse:
    if _is_hx_request(request):
        raise ProblemDetail(status=404, code="meeting_not_found", title="Meeting not found")
    return cabinet_html_response(
        render_meeting_unavailable_page(
            csrf_token=csrf_token,
            embedded=request.headers.get("X-GRAF-Client") == "desktop",
        ),
        status_code=404,
    )


async def _render_shared_summary_for_grant(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    viewer_user_id: UUID | None = None,
    grant: MeetingShareGrant | None = None,
    embedded: bool = False,
) -> str:
    meeting = await session.get(Meeting, meeting_id)
    if meeting is None or meeting.workspace_id != workspace_id:
        raise ProblemDetail(status=404, code="invitation_not_found", title="Invitation not found")
    if grant is None and viewer_user_id is not None:
        grant = await session.scalar(
            select(MeetingShareGrant).where(
                MeetingShareGrant.workspace_id == workspace_id,
                MeetingShareGrant.meeting_id == meeting_id,
                MeetingShareGrant.grantee_user_id == viewer_user_id,
                MeetingShareGrant.audience_type == "user",
                MeetingShareGrant.status == "active",
            )
        )
    saved = await load_shared_summary_projection(session, workspace_id=workspace_id, meeting=meeting, grant=grant)
    if saved is not None:
        return render_shared_meeting_summary_page(meeting_title=saved["meeting_label"],
            occurred_at=datetime.fromisoformat(str(saved["occurred_at"])), duration_seconds=saved["duration_seconds"],
            summary_sections=saved["summary_sections"], protocol=saved["protocol"], authenticated=True, embedded=embedded)
    metadata = grant.metadata_json if grant is not None and isinstance(grant.metadata_json, dict) else {}
    pin = metadata.get("summary_revision")
    outcome = None
    if isinstance(pin, dict):
        try:
            pinned_id = UUID(str(pin.get("outcome_set_id")))
        except (TypeError, ValueError):
            pinned_id = None
        template_key = pin.get("template_key")
        if isinstance(template_key, str) and pinned_id is not None:
            outcome = await load_pinned_egress_outcome(
                session,
                meeting=meeting,
                template_key=template_key,
                outcome_set_id=pinned_id,
            )
    else:
        slot = await load_meeting_default_slot(
            session,
            workspace_id=workspace_id,
            meeting_id=meeting.id,
        )
        outcome = await load_egress_default_outcome(session, meeting=meeting, slot=slot)
    items = (
        (
            await session.scalars(
                select(MeetingOutcomeItem)
                .where(
                    MeetingOutcomeItem.workspace_id == workspace_id,
                    MeetingOutcomeItem.outcome_set_id == outcome.id,
                    MeetingOutcomeItem.state == "available",
                )
                .order_by(MeetingOutcomeItem.category, MeetingOutcomeItem.sequence)
            )
        ).all()
        if outcome is not None
        else []
    )
    projection = narrow_summary_projection(
        meeting_label=meeting.title or "Встреча",
        occurred_at=meeting.started_at or meeting.created_at,
        duration_seconds=meeting.duration_seconds,
        summary_sections=[{"category": item.category, "text": item.text or ""} for item in items],
        protocol=outcome.protocol_json if outcome is not None else None,
    )
    display_title, display_time, uploaded = await shared_meeting_display_metadata(session, meeting=meeting)
    return render_shared_meeting_summary_page(
        meeting_title=display_title,
        occurred_at=display_time,
        time_is_upload=uploaded,
        duration_seconds=int(projection["duration_seconds"]),
        summary_sections=projection["summary_sections"],
        protocol=projection.get("protocol"),
        generator_version=outcome.generator_version if outcome is not None else None,
        authenticated=True,
        embedded=embedded,
    )


@router.get("/share-invitations/continue", response_class=HTMLResponse, include_in_schema=False)
async def share_invitation_continuation(
    request: Request,
    workspace_id: Annotated[UUID, Query()],
    state: str = Query(min_length=16, max_length=128),
    principal: AuthenticatedPrincipal = PrincipalDependency,
    recipient_scope: TenantScope = WebTenantDependency,
) -> Response:
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    key_file = request.app.state.settings.credential_encryption_key_file
    if sessionmaker is None or key_file is None:
        raise ProblemDetail(status=404, code="invitation_not_found", title="Invitation not found")
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
        verified_emails = (
            await session.scalars(
                select(ExternalIdentity.email).where(
                    ExternalIdentity.user_id == principal.user_id,
                    ExternalIdentity.is_active.is_(True),
                    ExternalIdentity.is_verified.is_(True),
                    ExternalIdentity.email.is_not(None),
                )
            )
        ).all()
    verified_address_hashes = {
        digest
        for email in verified_emails
        if email
        for digest in invitation_address_hashes(normalize_invitation_address(email))
    }
    async with sessionmaker() as session:
        session.info["share_rate_limit_sessionmaker"] = sessionmaker
        await apply_tenant_context(
            session,
            TenantDatabaseContext(
                organization_id=principal.organization_id,
                workspace_id=workspace_id,
                user_id=principal.user_id,
                device_id=recipient_scope.device_id,
                auth_session_id=principal.session_id,
                context_kind="request",
            ),
        )
        raw_token = await consume_share_invitation_continuation(
            session,
            workspace_id=workspace_id,
            nonce=state,
            encryption_key=key_file.read_bytes().strip(),
        )
        if raw_token is None:
            raise ProblemDetail(
                status=404, code="invitation_not_found", title="Invitation not found"
            )
        invitation = await session.scalar(select(MeetingShareInvitation).where(
            MeetingShareInvitation.workspace_id == workspace_id,
            MeetingShareInvitation.token_hash == hash_share_token(raw_token)))
        if invitation is None or invitation.normalized_address_hash not in verified_address_hashes:
            retry_path = f"/share-invitations/continue?workspace_id={workspace_id}&state={state}"
            return RedirectResponse(url=f"/login?{urlencode({'next': retry_path, 'error': 'share_recipient_mismatch'})}", status_code=303)
        preview = await share_invitation_preview(session, workspace_id=workspace_id, raw_token=raw_token)
        if preview is None:
            raise ProblemDetail(status=404, code="invitation_not_found", title="Invitation not found")
        # Signing in verifies the mailbox; the explicit CSRF-protected accept
        # form separately records consent. A scanner/GET cannot create a grant.
        summary_html = render_share_invitation_accept_page(share_token=raw_token,
            workspace_id=str(workspace_id), csrf_token=_csrf_token_for_principal(request, principal),
            meeting_title=preview.meeting_title, meeting_occurred_at=preview.display_occurred_at,
            meeting_time_is_upload=preview.display_time_is_upload,
            meeting_duration_seconds=preview.duration_seconds, invitation_expires_at=preview.expires_at,
            content_scope=preview.content_scope, authenticated=True, auto_accept=False)
    response = cabinet_html_response(summary_html)
    response.headers.update(
        {
            "Cache-Control": "private, no-store",
            "Pragma": "no-cache",
            "Referrer-Policy": "no-referrer",
            "X-Robots-Tag": "noindex, nofollow, noarchive",
        }
    )
    return response


async def _mark_account_created_email_dispatch_failure(
    *,
    sessionmaker,
    invitation_id: UUID,
    workspace_id: UUID,
    status: str,
    failure_code: str,
) -> None:
    async with sessionmaker() as session:
        await apply_tenant_context(
            session,
            TenantDatabaseContext(
                organization_id=UUID(int=0),
                workspace_id=workspace_id,
                user_id=UUID(int=0),
                context_kind="worker",
            ),
        )
        invitation = await session.get(MeetingShareInvitation, invitation_id)
        if invitation is not None and invitation.account_created_email_status == "pending":
            invitation.account_created_email_status = status
            invitation.account_created_email_failure_code = failure_code
            await session.commit()


async def _dispatch_account_created_email(
    request: Request,
    *,
    sessionmaker,
    invitation_id: UUID,
    workspace_id: UUID,
    organization_id: UUID,
    user_id: UUID,
) -> None:
    settings = request.app.state.settings
    try:
        if not settings.email_login_delivery_enabled:
            await _mark_account_created_email_dispatch_failure(
                sessionmaker=sessionmaker,
                invitation_id=invitation_id,
                workspace_id=workspace_id,
                status="failed",
                failure_code="postal_delivery_disabled",
            )
            return
        temporal_client = getattr(request.app.state, "temporal_client", None)
        if temporal_client is None:
            temporal_client = await connect_temporal_client(settings)
        await start_account_created_email_workflow(
            temporal_client=temporal_client,
            settings=settings,
            invitation_id=invitation_id,
            workspace_id=workspace_id,
            organization_id=organization_id,
            user_id=user_id,
        )
    except Exception:
        try:
            await _mark_account_created_email_dispatch_failure(
                sessionmaker=sessionmaker,
                invitation_id=invitation_id,
                workspace_id=workspace_id,
                status="outcome_unknown",
                failure_code="account_created_email_workflow_start_unknown",
            )
        except Exception:
            # Access is already committed; notification bookkeeping must not
            # turn a successful invitation acceptance into an HTTP 500.
            logger.exception("account-created invitation notification bookkeeping failed")


@router.post(
    "/share-invitations/continue/magic",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def share_invitation_magic_link(
    request: Request,
    workspace_id: Annotated[UUID, Query()],
    state: Annotated[str, Form(min_length=16, max_length=128)],
    magic_csrf: Annotated[str, Form(min_length=16, max_length=128)],
) -> Response:
    # Invitation possession proves neither an independent login nor mailbox
    # ownership: old and new invitation bearers can never issue an auth session.
    raise ProblemDetail(status=401, code="independent_login_required", title="Sign in to accept this invitation")


@router.get(
    "/share-invitations/{share_token}", response_class=HTMLResponse, include_in_schema=False
)
async def share_invitation_accept_page(
    request: Request,
    share_token: str,
    workspace_id: Annotated[UUID, Query()],
    principal: AuthenticatedPrincipal | None = OptionalPrincipalDependency,
) -> Response:
    preview = None
    continuation_nonce = None
    magic_csrf_token = None
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is not None:
        async with sessionmaker() as session:
            await apply_tenant_context(
                session,
                TenantDatabaseContext(
                    organization_id=UUID(int=0),
                    workspace_id=workspace_id,
                    user_id=UUID(int=0),
                    context_kind="request",
                ),
            )
            accepted_invitation = await session.scalar(select(MeetingShareInvitation).where(
                MeetingShareInvitation.workspace_id == workspace_id,
                MeetingShareInvitation.token_hash == hash_share_token(share_token),
                MeetingShareInvitation.published_summary_id.is_not(None),
                MeetingShareInvitation.status == "accepted",
                MeetingShareInvitation.read_expires_at > datetime.now(UTC)))
            if accepted_invitation is not None:
                from twobrain_rec_server.db.models.summary_sharing import SummaryRecipientDelivery
                delivery_id = await session.scalar(select(SummaryRecipientDelivery.id).where(
                    SummaryRecipientDelivery.workspace_id == workspace_id,
                    SummaryRecipientDelivery.invitation_id == accepted_invitation.id))
                if delivery_id:
                    # The reader independently checks the actual signed-in mailbox;
                    # the old invitation bearer carries no authentication power.
                    return RedirectResponse(f"/api/v1/cabinet/summary-sharing/received/{delivery_id}?workspace_id={workspace_id}", status_code=303,
                        headers={"Cache-Control": "private, no-store", "Referrer-Policy": "no-referrer", "X-Robots-Tag": "noindex, nofollow"})
            preview = await share_invitation_preview(
                session,
                workspace_id=workspace_id,
                raw_token=share_token,
            )
            key_file = request.app.state.settings.credential_encryption_key_file
            if preview is not None and key_file is not None:
                continuation_nonce = await create_share_invitation_continuation(
                    session,
                    workspace_id=workspace_id,
                    raw_token=share_token,
                    encryption_key=key_file.read_bytes().strip(),
                )
            await session.commit()
    if preview is not None and principal is not None and continuation_nonce is not None:
        return RedirectResponse(
            url=(
                f"/share-invitations/continue?workspace_id={workspace_id}"
                f"&state={continuation_nonce}"
            ),
            status_code=303,
        )
    if preview is not None and continuation_nonce is not None and principal is None:
        magic_csrf_token = request.cookies.get(
            MAGIC_LINK_CSRF_COOKIE_NAME
        ) or secrets.token_urlsafe(32)
    post_login_next_path = "/meetings"
    if continuation_nonce is not None:
        post_login_next_path = (
            f"/share-invitations/continue?workspace_id={workspace_id}&state={continuation_nonce}"
        )
    response = cabinet_html_response(
        render_share_invitation_accept_page(
            share_token=share_token,
            workspace_id=str(workspace_id),
            csrf_token=(
                _csrf_token_for_principal(request, principal) if principal is not None else None
            ),
            meeting_title=preview.meeting_title if preview else None,
            meeting_occurred_at=preview.display_occurred_at if preview else None,
            meeting_time_is_upload=preview.display_time_is_upload if preview else False,
            meeting_duration_seconds=preview.duration_seconds if preview else None,
            invitation_expires_at=preview.expires_at if preview else None,
            content_scope=preview.content_scope if preview else "summary_only",
            authenticated=principal is not None,
            post_login_next_path=post_login_next_path,
            magic_action=None,
            magic_state=continuation_nonce,
            magic_csrf_token=magic_csrf_token,
            auto_accept=False,
        )
    )
    if magic_csrf_token is not None:
        response.set_cookie(
            key=MAGIC_LINK_CSRF_COOKIE_NAME,
            value=magic_csrf_token,
            max_age=MAGIC_LINK_CSRF_TTL_SECONDS,
            path="/",
            secure=request.url.scheme == "https",
            httponly=False,
            samesite="lax",
        )
    response.headers.update(
        {
            "Cache-Control": "private, no-store",
            "Pragma": "no-cache",
            "Referrer-Policy": "no-referrer",
            "X-Robots-Tag": "noindex, nofollow, noarchive",
        }
    )
    return response


@router.get("/meetings", response_class=HTMLResponse, include_in_schema=False)
async def meeting_list_page(
    request: Request,
    q: str | None = CabinetSearchQuery,
    status: CabinetStatusFilter = None,
    access: CabinetAccessFilter = None,
    sort: str = CabinetSortQuery,
    limit: int = CabinetLimitQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    response = await list_cabinet_meetings(
        db,
        workspace_id=tenant_scope.workspace_id,
        viewer_user_id=principal.user_id,
        storage=storage,
        q=q,
        status=status,
        group_status_filter=True,
        visible_title_search=True,
        access=access,
        sort=sort,
        unknown_sort_fallback="started_desc",
        normalize_response_sort=True,
        limit=limit,
    )

    raw_status = request.query_params.get("status")
    canonical_status = _normalize_web_meeting_status_filter(raw_status)
    status_was_normalized = (
        isinstance(raw_status, str) and raw_status != "" and canonical_status != raw_status
    )
    sort_was_normalized = sort != response.filters.sort
    needs_url_normalization = sort_was_normalized or status_was_normalized
    canonical_path = (
        _request_path_with_query(
            request,
            sort_override=response.filters.sort if sort_was_normalized else None,
            status_override=status if status_was_normalized else None,
        )
        if needs_url_normalization
        else _request_path_with_query(request)
    )
    if needs_url_normalization and not _is_hx_request(request):
        return RedirectResponse(url=canonical_path, status_code=303)
    if _is_hx_request(request):
        result = cabinet_html_response(
            render_meeting_list_fragment(response, poll_url=canonical_path),
            hx_request=True,
        )
        if needs_url_normalization:
            result.headers["HX-Replace-Url"] = canonical_path
        return result
    profile = await get_account_profile_view(db, tenant_scope)
    calendar_surface = await get_calendar_settings_surface(
        db,
        tenant_scope,
        settings=request.app.state.settings,
    )
    return cabinet_html_response(
        render_meeting_list_page(
            response,
            calendar_surface=calendar_surface,
            display_timezone=profile.timezone,
            csrf_token=_csrf_token_for_principal(request, principal),
            poll_url=canonical_path,
            profile=profile,
            product_analytics_provider=build_request_browser_provider_context(
                request,
                "recording_list",
                principal=principal,
                tenant_scope=tenant_scope,
            ),
        )
    )


@router.get("/shared-with-me", response_class=HTMLResponse, include_in_schema=False)
async def shared_with_me_list_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
) -> HTMLResponse:
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    items = await list_shared_with_me_meetings(
        sessionmaker,
        recipient_scope=tenant_scope,
    )
    async with sessionmaker() as profile_db:
        profile = await get_account_profile_view(profile_db, tenant_scope)
    return cabinet_html_response(
        render_shared_with_me_page(
            items,
            csrf_token=_csrf_token_for_principal(request, principal),
            profile=profile,
            product_analytics_provider=build_request_browser_provider_context(
                request,
                "recording_list",
                principal=principal,
                tenant_scope=tenant_scope,
            ),
        )
    )


@router.get("/meetings/{meeting_id}", response_class=HTMLResponse, include_in_schema=False)
async def meeting_detail_page(
    request: Request,
    meeting_id: str,
    source_result_id: Annotated[UUID | None, Query()] = None,
    calendar_context_action: str | None = Query(default=None, pattern="^change$"),
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    try:
        parsed_meeting_id = UUID(meeting_id)
    except ValueError:
        return _meeting_unavailable_response(
            request,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    response = await get_cabinet_meeting_review(
        db,
        workspace_id=tenant_scope.workspace_id,
        meeting_id=parsed_meeting_id,
        viewer_user_id=principal.user_id,
        selected_summary_template_key=request.query_params.get("summary_format"),
        source_result_id=source_result_id,
        storage=storage,
        include_calendar_correction_candidates=calendar_context_action == "change",
        external_invitations_enabled=request.app.state.settings.share_external_invitations_enabled,
        invitation_encryption_key=(
            request.app.state.settings.credential_encryption_key_file.read_bytes().strip()
            if request.app.state.settings.credential_encryption_key_file is not None
            else None
        ),
    )
    if response is None:
        return _meeting_unavailable_response(
            request,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    if response.access is not None and not response.access.can_view_full_meeting:
        shared_summary = cabinet_html_response(
            await _render_shared_summary_for_grant(
                db,
                workspace_id=tenant_scope.workspace_id,
                meeting_id=parsed_meeting_id,
                viewer_user_id=principal.user_id,
            )
        )
        shared_summary.headers.update(
            {
                "Cache-Control": "private, no-store",
                "Pragma": "no-cache",
                "Referrer-Policy": "no-referrer",
                "X-Robots-Tag": "noindex, nofollow, noarchive",
            }
        )
        return shared_summary
    if _is_hx_request(request):
        return cabinet_html_response(
            render_meeting_detail_fragment(
                response,
                csrf_token=_csrf_token_for_principal(request, principal),
                poll_url=_request_path_with_query(request),
            ),
            hx_request=True,
        )
    return cabinet_html_response(
        render_meeting_detail_page(
            response,
            csrf_token=_csrf_token_for_principal(request, principal),
            poll_url=_request_path_with_query(request),
            profile=await get_account_profile_view(db, tenant_scope),
            product_analytics_provider=build_request_browser_provider_context(
                request,
                "meeting_result_detail",
                principal=principal,
                tenant_scope=tenant_scope,
            ),
        )
    )


@router.get("/shared-meetings/{meeting_id}", response_class=HTMLResponse, include_in_schema=False)
async def shared_meeting_detail_page(
    request: Request,
    meeting_id: str,
    workspace_id: Annotated[UUID, Query()],
    recipient_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = PublicShareDbDependency,
) -> Response:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    try:
        parsed_meeting_id = UUID(meeting_id)
    except ValueError:
        return _meeting_unavailable_response(
            request,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    recipient_proof = await _recipient_share_access_proof(
        request,
        recipient_scope=recipient_scope,
        owner_workspace_id=workspace_id,
    )
    meeting = await db.scalar(
        select(Meeting).where(
            Meeting.workspace_id == workspace_id,
            Meeting.id == parsed_meeting_id,
        )
    )
    access = (
        await decide_meeting_access(
            db,
            meeting,
            workspace_id=workspace_id,
            viewer_user_id=principal.user_id,
            recipient_proof=recipient_proof,
        )
        if meeting is not None
        else None
    )
    if access is None or not access.can_view:
        return _meeting_unavailable_response(
            request,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    if not access.can_view_full_meeting:
        response = cabinet_html_response(
            await _render_shared_summary_for_grant(
                db,
                workspace_id=workspace_id,
                meeting_id=parsed_meeting_id,
                viewer_user_id=principal.user_id,
                embedded=request.headers.get("X-GRAF-Client") == "desktop",
            )
        )
        response.headers.update(
            {
                "Cache-Control": "private, no-store",
                "Pragma": "no-cache",
                "Referrer-Policy": "no-referrer",
                "X-Robots-Tag": "noindex, nofollow, noarchive",
            }
        )
        return response
    review = await get_cabinet_meeting_review(
        db,
        workspace_id=workspace_id,
        meeting_id=parsed_meeting_id,
        viewer_user_id=principal.user_id,
        storage=storage,
        recipient_proof=recipient_proof,
    )
    if review is None or review.access is None or not review.access.can_view:
        return _meeting_unavailable_response(
            request,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    response = cabinet_html_response(
        render_meeting_detail_page(
            review,
            csrf_token=_csrf_token_for_principal(request, principal),
            poll_url=_request_path_with_query(request),
            product_analytics_provider=None,
            shared_workspace_id=workspace_id,
            embedded=request.headers.get("X-GRAF-Client") == "desktop",
        )
    )
    response.headers.update(
        {
            "Cache-Control": "private, no-store",
            "Pragma": "no-cache",
            "Referrer-Policy": "no-referrer",
            "X-Robots-Tag": "noindex, nofollow, noarchive",
        }
    )
    return response


@router.get(
    "/meetings/{meeting_id}/share",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def meeting_share_fragment(
    request: Request,
    meeting_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = ShareOperationDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    response = await get_cabinet_meeting_review(
        db,
        workspace_id=db.info.get("share_owner_workspace", tenant_scope.workspace_id),
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
    if response is None or response.access is None or not response.access.can_share:
        return _meeting_unavailable_response(
            request,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    return cabinet_html_response(render_meeting_share_fragment(response, share_workspace_id=db.info.get("share_owner_workspace")), hx_request=True)
