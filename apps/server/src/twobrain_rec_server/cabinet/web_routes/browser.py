from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.cabinet import (
    PublicShareDbDependency,
    _recipient_share_access_proof,
)
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.sessions import hash_token, issue_auth_session
from twobrain_rec_server.auth.workspace_onboarding import (
    ensure_personal_workspace,
)
from twobrain_rec_server.cabinet.access import (
    accept_share_invitation,
    consume_share_invitation_continuation,
    create_share_invitation_continuation,
    decide_meeting_access,
    finalize_share_invitation_continuation,
    hash_share_token,
    invitation_address_hashes,
    narrow_summary_projection,
    normalize_invitation_address,
    share_invitation_preview,
    share_invitation_recipient_address,
)
from twobrain_rec_server.cabinet.queries import (
    get_account_profile_view,
    get_cabinet_meeting_review,
    get_calendar_settings_surface,
    list_cabinet_meetings,
    list_shared_with_me_meetings,
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
from twobrain_rec_server.cabinet.templates import (
    cabinet_html_response,
)
from twobrain_rec_server.cabinet.web_routes.auth_email_flow import (
    _ensure_email_registration_user,
    _record_email_login_audit,
    _resolve_email_browser_device,
    _resolve_email_login_user,
    _set_browser_auth_cookie,
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
    AuthSessionDeviceBinding,
    ExternalIdentity,
    Meeting,
    MeetingOutcomeItem,
    MeetingShareInvitation,
)
from twobrain_rec_server.db.tenant_context import (
    TenantDatabaseContext,
    apply_tenant_context,
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
        render_meeting_unavailable_page(csrf_token=csrf_token),
        status_code=404,
    )


async def _render_shared_summary_for_grant(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> str:
    meeting = await session.get(Meeting, meeting_id)
    if meeting is None or meeting.workspace_id != workspace_id:
        raise ProblemDetail(status=404, code="invitation_not_found", title="Invitation not found")
    items = (
        (
            await session.scalars(
                select(MeetingOutcomeItem)
                .where(
                    MeetingOutcomeItem.workspace_id == workspace_id,
                    MeetingOutcomeItem.outcome_set_id == meeting.current_outcome_set_id,
                    MeetingOutcomeItem.state == "available",
                )
                .order_by(MeetingOutcomeItem.category, MeetingOutcomeItem.sequence)
            )
        ).all()
        if meeting.current_outcome_set_id is not None
        else []
    )
    projection = narrow_summary_projection(
        meeting_label=meeting.title or "Встреча",
        occurred_at=meeting.started_at or meeting.created_at,
        duration_seconds=meeting.duration_seconds,
        summary_sections=[{"category": item.category, "text": item.text or ""} for item in items],
    )
    return render_shared_meeting_summary_page(
        meeting_title=str(projection["meeting_label"]),
        occurred_at=projection["occurred_at"],
        duration_seconds=int(projection["duration_seconds"]),
        summary_sections=projection["summary_sections"],
        authenticated=True,
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
        accepted = await accept_share_invitation(
            session,
            workspace_id=workspace_id,
            user_id=principal.user_id,
            device_id=recipient_scope.device_id,
            raw_token=raw_token,
            verified_address_hashes=verified_address_hashes,
            encryption_key=key_file.read_bytes().strip(),
            recipient_user_active=True,
        )
        if accepted is None:
            retry_path = f"/share-invitations/continue?workspace_id={workspace_id}&state={state}"
            return RedirectResponse(
                url=f"/login?{urlencode({'next': retry_path, 'error': 'share_recipient_mismatch'})}",
                status_code=303,
            )
        grant, _grant_token = accepted
        if not await finalize_share_invitation_continuation(
            session,
            workspace_id=workspace_id,
            nonce=state,
        ):
            raise ProblemDetail(
                status=404, code="invitation_not_found", title="Invitation not found"
            )
        shared_url = (
            _shared_meeting_url(workspace_id=workspace_id, meeting_id=grant.meeting_id)
            if grant.content_scope == "full_meeting" and grant.can_download and grant.can_export
            else None
        )
        summary_html = (
            None
            if shared_url is not None
            else await _render_shared_summary_for_grant(
                session,
                workspace_id=workspace_id,
                meeting_id=grant.meeting_id,
            )
        )
        await session.commit()
    response = (
        RedirectResponse(url=shared_url, status_code=303)
        if shared_url is not None
        else cabinet_html_response(summary_html or "")
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
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    key_file = request.app.state.settings.credential_encryption_key_file
    cookie_token = request.cookies.get(MAGIC_LINK_CSRF_COOKIE_NAME)
    if (
        sessionmaker is None
        or key_file is None
        or cookie_token is None
        or not secrets.compare_digest(cookie_token, magic_csrf)
    ):
        raise ProblemDetail(status=404, code="invitation_not_found", title="Invitation not found")

    encryption_key = key_file.read_bytes().strip()
    account_created = False
    invitation_id: UUID | None = None
    issued_token: str | None = None
    issued_expires_at: datetime | None = None
    user_id: UUID | None = None
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
        raw_token = await consume_share_invitation_continuation(
            session,
            workspace_id=workspace_id,
            nonce=state,
            encryption_key=encryption_key,
        )
        if raw_token is None:
            raise ProblemDetail(
                status=404, code="invitation_not_found", title="Invitation not found"
            )
        recipient_email = await share_invitation_recipient_address(
            session,
            workspace_id=workspace_id,
            raw_token=raw_token,
            encryption_key=encryption_key,
        )
        if recipient_email is None:
            raise ProblemDetail(
                status=404, code="invitation_not_found", title="Invitation not found"
            )
        invitation_id = await session.scalar(
            select(MeetingShareInvitation.id).where(
                MeetingShareInvitation.workspace_id == workspace_id,
                MeetingShareInvitation.token_hash == hash_share_token(raw_token),
                MeetingShareInvitation.status.in_(("pending", "sending", "sent")),
            )
        )
        workspace, user = await _resolve_email_login_user(
            session,
            workspace_id=workspace_id,
            email=recipient_email,
            internal_workspace_id=request.app.state.settings.web_login_workspace_id,
        )
        if workspace is None:
            raise ProblemDetail(
                status=404, code="invitation_not_found", title="Invitation not found"
            )
        account_created = user is None
        if account_created:
            existing_identity_id = await session.scalar(
                select(ExternalIdentity.id).where(
                    func.lower(ExternalIdentity.email) == recipient_email,
                    ExternalIdentity.is_verified.is_(True),
                    ExternalIdentity.is_active.is_(True),
                )
            )
            account_created = existing_identity_id is None
            user, account_created = await _ensure_email_registration_user(
                session,
                workspace=workspace,
                email=recipient_email,
                now=datetime.now(UTC),
            )
        personal_workspace = await ensure_personal_workspace(
            session,
            organization_id=workspace.organization_id,
            user_id=user.id,
        )
        now = datetime.now(UTC)
        device = await _resolve_email_browser_device(
            session,
            workspace=personal_workspace,
            user=user,
            now=now,
        )
        issued = await issue_auth_session(
            session,
            user_id=user.id,
            workspace_id=personal_workspace.id,
            device_id=device.id,
            provider="email_magic_link",
            ttl_seconds=request.app.state.settings.auth_session_ttl_seconds,
            claims_fingerprint=hash_token(f"magic:{recipient_email}:{workspace_id}"),
            now=now,
        )
        session.add(
            AuthSessionDeviceBinding(
                auth_session_id=issued.id,
                registered_device_id=device.id,
                device_state="trusted",
                last_heartbeat_at=now,
            )
        )
        await session.flush()
        await apply_tenant_context(
            session,
            TenantDatabaseContext(
                organization_id=workspace.organization_id,
                workspace_id=personal_workspace.id,
                user_id=user.id,
                device_id=device.id,
                auth_session_id=issued.id,
                context_kind="request",
            ),
        )
        await _record_email_login_audit(
            session,
            request=request,
            workspace_id=personal_workspace.id,
            user_id=user.id,
            metadata={
                "flow": "share_magic_link",
                "account_created": account_created,
            },
        )
        await session.flush()
        await apply_tenant_context(
            session,
            TenantDatabaseContext(
                organization_id=workspace.organization_id,
                workspace_id=workspace_id,
                user_id=user.id,
                device_id=device.id,
                auth_session_id=issued.id,
                context_kind="request",
            ),
        )
        accepted = await accept_share_invitation(
            session,
            workspace_id=workspace_id,
            user_id=user.id,
            device_id=device.id,
            raw_token=raw_token,
            verified_address_hashes=invitation_address_hashes(recipient_email),
            encryption_key=encryption_key,
            recipient_user_active=True,
        )
        if accepted is None or invitation_id is None:
            raise ProblemDetail(
                status=404, code="invitation_not_found", title="Invitation not found"
            )
        grant, _grant_token = accepted
        accepted_invitation = await session.scalar(
            select(MeetingShareInvitation)
            .where(
                MeetingShareInvitation.id == invitation_id,
                MeetingShareInvitation.workspace_id == workspace_id,
                MeetingShareInvitation.status == "accepted",
            )
            .with_for_update()
        )
        if accepted_invitation is None:
            raise ProblemDetail(
                status=404, code="invitation_not_found", title="Invitation not found"
            )
        if account_created:
            accepted_invitation.account_created_email_status = "pending"
            accepted_invitation.account_created_email_failure_code = None
        if not await finalize_share_invitation_continuation(
            session,
            workspace_id=workspace_id,
            nonce=state,
        ):
            raise ProblemDetail(
                status=404, code="invitation_not_found", title="Invitation not found"
            )
        shared_url = (
            _shared_meeting_url(workspace_id=workspace_id, meeting_id=grant.meeting_id)
            if grant.content_scope == "full_meeting" and grant.can_download and grant.can_export
            else None
        )
        summary_html = (
            None
            if shared_url is not None
            else await _render_shared_summary_for_grant(
                session,
                workspace_id=workspace_id,
                meeting_id=grant.meeting_id,
            )
        )
        await session.commit()
        issued_token = issued.token
        issued_expires_at = issued.expires_at
        user_id = user.id

    response = (
        RedirectResponse(url=shared_url, status_code=303)
        if shared_url is not None
        else cabinet_html_response(summary_html or "")
    )
    if issued_token is not None and issued_expires_at is not None:
        _set_browser_auth_cookie(
            request,
            response,
            token=issued_token,
            expires_at=issued_expires_at,
        )
    response.delete_cookie(MAGIC_LINK_CSRF_COOKIE_NAME, path="/")
    response.headers.update(
        {
            "Cache-Control": "private, no-store",
            "Pragma": "no-cache",
            "Referrer-Policy": "no-referrer",
            "X-Robots-Tag": "noindex, nofollow, noarchive",
        }
    )
    if account_created and invitation_id is not None and user_id is not None:
        await _dispatch_account_created_email(
            request,
            sessionmaker=sessionmaker,
            invitation_id=invitation_id,
            workspace_id=workspace_id,
            organization_id=workspace.organization_id,
            user_id=user_id,
        )
    return response


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
            meeting_occurred_at=preview.occurred_at if preview else None,
            meeting_duration_seconds=preview.duration_seconds if preview else None,
            invitation_expires_at=preview.expires_at if preview else None,
            content_scope=preview.content_scope if preview else "summary_only",
            authenticated=principal is not None,
            post_login_next_path=post_login_next_path,
            magic_action=(
                f"/share-invitations/continue/magic?workspace_id={workspace_id}"
                if continuation_nonce is not None
                else None
            ),
            magic_state=continuation_nonce,
            magic_csrf_token=magic_csrf_token,
            auto_accept=preview is not None
            and continuation_nonce is not None
            and principal is None,
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
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
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
    if response is None or response.access is None or not response.access.can_share:
        return _meeting_unavailable_response(
            request,
            csrf_token=_csrf_token_for_principal(request, principal),
        )
    return cabinet_html_response(render_meeting_share_fragment(response), hx_request=True)
