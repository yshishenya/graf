from __future__ import annotations

from typing import Annotated
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.workspace_onboarding import (
    list_active_workspaces,
    list_workspace_join_offers,
)
from twobrain_rec_server.cabinet.access import (
    accept_share_invitation,
    consume_share_invitation_continuation,
    create_share_invitation_continuation,
    finalize_share_invitation_continuation,
    invitation_address_hashes,
    narrow_summary_projection,
    normalize_invitation_address,
    share_invitation_preview,
)
from twobrain_rec_server.cabinet.queries import (
    get_cabinet_meeting_review,
    get_provider_link_start_options,
    list_cabinet_meetings,
)
from twobrain_rec_server.cabinet.rendering import (
    render_meeting_detail_fragment,
    render_meeting_detail_page,
    render_meeting_list_fragment,
    render_meeting_list_page,
    render_meeting_unavailable_page,
    render_settings_page,
    render_share_invitation_accept_page,
    render_shared_meeting_summary_page,
)
from twobrain_rec_server.cabinet.review_policy_rendering import render_meeting_share_fragment
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
from twobrain_rec_server.db.models import ExternalIdentity, Meeting, MeetingOutcomeItem
from twobrain_rec_server.db.tenant_context import TenantDatabaseContext, apply_tenant_context
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
)

router = APIRouter(tags=["cabinet-web"])


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
            raise ProblemDetail(status=404, code="invitation_not_found", title="Invitation not found")
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
            retry_path = (
                f"/share-invitations/continue?workspace_id={workspace_id}"
                f"&state={state}"
            )
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
            raise ProblemDetail(status=404, code="invitation_not_found", title="Invitation not found")
        meeting = await session.get(Meeting, grant.meeting_id)
        if meeting is None:
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
            summary_sections=[
                {"category": item.category, "text": item.text or ""} for item in items
            ],
        )
        await session.commit()
    response = cabinet_html_response(
        render_shared_meeting_summary_page(
            meeting_title=str(projection["meeting_label"]),
            occurred_at=projection["occurred_at"],
            duration_seconds=int(projection["duration_seconds"]),
            summary_sections=projection["summary_sections"],
            authenticated=True,
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


@router.get("/share-invitations/{share_token}", response_class=HTMLResponse, include_in_schema=False)
async def share_invitation_accept_page(
    request: Request,
    share_token: str,
    workspace_id: Annotated[UUID, Query()],
    principal: AuthenticatedPrincipal | None = OptionalPrincipalDependency,
) -> Response:
    preview = None
    continuation_nonce = None
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
    post_login_next_path = "/meetings"
    if continuation_nonce is not None:
        post_login_next_path = (
            f"/share-invitations/continue?workspace_id={workspace_id}"
            f"&state={continuation_nonce}"
        )
    response = cabinet_html_response(
        render_share_invitation_accept_page(
            share_token=share_token,
            workspace_id=str(workspace_id),
            csrf_token=(
                _csrf_token_for_principal(request, principal)
                if principal is not None
                else None
            ),
            meeting_title=preview.meeting_title if preview else None,
            meeting_occurred_at=preview.occurred_at if preview else None,
            meeting_duration_seconds=preview.duration_seconds if preview else None,
            invitation_expires_at=preview.expires_at if preview else None,
            authenticated=principal is not None,
            post_login_next_path=post_login_next_path,
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
        isinstance(raw_status, str)
        and raw_status != ""
        and canonical_status != raw_status
    )
    sort_was_normalized = sort != response.filters.sort
    needs_url_normalization = sort_was_normalized or status_was_normalized
    canonical_path = _request_path_with_query(
        request,
        sort_override=response.filters.sort if sort_was_normalized else None,
        status_override=status if status_was_normalized else None,
    ) if needs_url_normalization else _request_path_with_query(request)
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
    return cabinet_html_response(
        render_meeting_list_page(
            response,
            csrf_token=_csrf_token_for_principal(request, principal),
            poll_url=canonical_path,
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
        return RedirectResponse(
            url=f"/api/v1/cabinet/meetings/{parsed_meeting_id}/shared-summary",
            status_code=302,
        )
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
            product_analytics_provider=build_request_browser_provider_context(
                request,
                "meeting_result_detail",
                principal=principal,
                tenant_scope=tenant_scope,
            ),
        )
    )


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
        raise ProblemDetail(status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable")
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


@router.get("/settings", response_class=HTMLResponse, include_in_schema=False)
async def settings_page(
    request: Request,
    workspace_offer: str | None = Query(default=None, max_length=24),
    space_switch: str | None = Query(default=None, max_length=24),
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Cabinet store unavailable"
        )
    offers = await list_workspace_join_offers(
        db,
        organization_id=principal.organization_id,
        current_workspace_id=tenant_scope.workspace_id,
        user_id=principal.user_id,
    )
    provider_link_options = await get_provider_link_start_options(db, tenant_scope)
    spaces = await list_active_workspaces(
        db,
        organization_id=principal.organization_id,
        current_workspace_id=tenant_scope.workspace_id,
        user_id=principal.user_id,
    )
    await db.commit()
    return cabinet_html_response(
        render_settings_page(
            csrf_token=_csrf_token_for_principal(request, principal),
            provider_link_options=provider_link_options,
            workspace_spaces=spaces,
            workspace_join_offers=offers,
            workspace_offer_result=workspace_offer,
            workspace_switch_result=space_switch,
            product_analytics_provider=build_request_browser_provider_context(
                request,
                "settings",
                principal=principal,
                tenant_scope=tenant_scope,
            ),
        )
    )
