from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Form, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.ingest import get_request_storage
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.csrf import issue_csrf_token
from twobrain_rec_server.auth.dependencies import (
    DESKTOP_CALENDAR_AUTH_COOKIE_PATH,
    get_principal,
    get_web_owner_tenant_scope,
    require_web_csrf,
)
from twobrain_rec_server.cabinet.access import decide_meeting_access
from twobrain_rec_server.db.models import (
    Meeting,
    WorkspaceMembership,
)
from twobrain_rec_server.db.tenant_context import (
    apply_tenant_scope,
)

WebTenantDependency = Depends(get_web_owner_tenant_scope)
PrincipalDependency = Depends(get_principal)
WebCSRFDependency = Depends(require_web_csrf)
StorageDependency = Depends(get_request_storage)
CabinetSearchQuery = Query(default=None, max_length=120)
CabinetStatusQuery = Query(default=None)
CabinetAccessQuery = Query(default=None)
CabinetSortQuery = Query(default="updated_desc")
CabinetLimitQuery = Query(default=50, ge=1, le=100)
CalendarConnectResultQuery = Query(default=None, max_length=48, alias="connect_result")
CalendarPolicyLimitedQuery = Query(default=None, max_length=48, alias="policy_limited")
CalendarSelectionResultQuery = Query(default=None, max_length=48, alias="selection_result")
CalendarPreferencesResultQuery = Query(default=None, max_length=48, alias="preferences_result")
CalendarSyncResultQuery = Query(default=None, max_length=48, alias="sync_result")
CalendarDisconnectResultQuery = Query(default=None, max_length=48, alias="disconnect_result")
CalendarProviderResultQuery = Query(default=None, max_length=48, alias="result")
CalendarProviderFamilyQuery = Query(default=None, max_length=80, alias="provider_family")

CalendarAccountLabelForm = Form(default=None, max_length=160)
CalendarCalDAVURLForm = Form(default=None, max_length=1000)
CalendarUsernameForm = Form(default=None, max_length=240)
CalendarCredentialForm = Form(default=None, max_length=2000)

def _is_hx_request(request: Request) -> bool:
    return request.headers.get("HX-Request", "").lower() == "true"


def _request_path_with_query(request: Request) -> str:
    query = request.url.query
    return f"{request.url.path}?{query}" if query else request.url.path


async def get_web_request_db_session(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
):
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        yield None
        return
    async with sessionmaker() as session:
        await apply_tenant_scope(session, tenant_scope)
        yield session


WebDbDependency = Depends(get_web_request_db_session)


async def get_web_login_db_session(request: Request):
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        yield None
        return
    async with sessionmaker() as session:
        yield session


LoginDbDependency = Depends(get_web_login_db_session)

def _csrf_token_for_principal(
    request: Request,
    principal: AuthenticatedPrincipal,
    *,
    tenant_scope: TenantScope | None = None,
) -> str | None:
    csrf_subject_id = principal.session_id
    if not principal.auth_via_session:
        if tenant_scope is None or not request.url.path.startswith(DESKTOP_CALENDAR_AUTH_COOKIE_PATH):
            return None
        csrf_subject_id = tenant_scope.device_id
    if csrf_subject_id is None:
        return None
    secret = getattr(request.app.state, "web_csrf_secret", None)
    if not secret:
        raise ProblemDetail(
            status=503,
            code="csrf_secret_unavailable",
            title="CSRF protection unavailable",
        )
    return issue_csrf_token(session_id=csrf_subject_id, secret=str(secret))

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


def _ensure_lifecycle_manager(decision) -> None:
    if decision.state != "owner" and decision.role not in {"owner", "admin"}:
        raise ProblemDetail(status=403, code="deletion_forbidden", title="Deletion is not available")


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
