from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.admin.audit import read_admin_audit_journal
from twobrain_rec_server.admin.files import (
    admin_meeting_access,
    get_admin_file_detail,
    list_admin_files,
    load_workspace_meeting,
    record_admin_review_access,
)
from twobrain_rec_server.admin.invitations import (
    create_workspace_invitation,
    revoke_workspace_invitation,
)
from twobrain_rec_server.admin.metrics import get_admin_metrics
from twobrain_rec_server.admin.queries import (
    get_admin_overview_payload,
    load_admin_workspace_context,
)
from twobrain_rec_server.admin.templates import admin_template_response
from twobrain_rec_server.admin.usage import get_usage_summary
from twobrain_rec_server.admin.users import (
    get_workspace_user_detail,
    list_workspace_users,
    update_workspace_membership,
)
from twobrain_rec_server.admin.view_models import (
    build_audit_view,
    build_balance_view,
    build_file_detail_view,
    build_files_view,
    build_metrics_view,
    build_overview_view,
    build_user_detail_view,
    build_users_view,
)
from twobrain_rec_server.api.ingest import get_request_storage
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import ArtifactClass
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, DeviceContext, TenantScope
from twobrain_rec_server.auth.dependencies import (
    get_device_context,
    get_principal,
    get_web_owner_tenant_scope,
    require_web_csrf,
)
from twobrain_rec_server.cabinet.egress import create_export_package
from twobrain_rec_server.cabinet.queries import latest_processing_result
from twobrain_rec_server.db.tenant_context import apply_tenant_scope
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY
from twobrain_rec_server.deletion.service import request_meeting_deletion
from twobrain_rec_server.domain.statuses import DeletionReasonCode, DeletionRequestSource

router = APIRouter(tags=["admin-web"])

WebTenantDependency = Depends(get_web_owner_tenant_scope)
PrincipalDependency = Depends(get_principal)
DeviceDependency = Depends(get_device_context)
WebCSRFDependency = Depends(require_web_csrf)
StorageDependency = Depends(get_request_storage)
AdminSearchQuery = Query(default=None, max_length=120)
AdminStatusQuery = Query(default=None, max_length=64)
AdminDateQuery = Query(default=None)
AdminIntQuery = Query(default=None, ge=0)
AdminArtifactClassesForm = Form(default=[])
AdminDeletionReasonForm = Form(DeletionReasonCode.USER_REQUEST)


async def get_admin_web_db_session(
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


WebDbDependency = Depends(get_admin_web_db_session)


@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin_overview_page(
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    if db is None:
        return admin_template_response(
            request,
            "admin/access_denied.html",
            status_code=503,
            page_title="Администрирование",
            reason="Админка временно недоступна",
        )
    try:
        context = await load_admin_workspace_context(
            db, tenant_scope=tenant_scope, principal=principal
        )
    except ProblemDetail:
        return admin_template_response(
            request,
            "admin/access_denied.html",
            status_code=403,
            page_title="Нет доступа",
            reason="Админка доступна только владельцам и администраторам рабочей области.",
        )
    overview = await get_admin_overview_payload(db, context=context)
    view = build_overview_view(
        workspace_name=context.workspace_name,
        actor_role=context.actor_role,
        overview=overview,
    )
    return admin_template_response(
        request,
        "admin/overview.html",
        view=view,
        page_title=view.page_title,
        principal=principal,
    )


@router.get("/admin/users", response_class=HTMLResponse, include_in_schema=False)
async def admin_users_page(
    request: Request,
    search: str | None = AdminSearchQuery,
    role: str | None = Query(default=None, pattern="^(owner|admin|member)$"),
    status: str | None = AdminStatusQuery,
    invitation_status: str | None = AdminStatusQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    loaded = await _load_web_admin_context(
        request, tenant_scope=tenant_scope, principal=principal, db=db
    )
    if isinstance(loaded, HTMLResponse):
        return loaded
    context, session = loaded
    users = await list_workspace_users(
        session,
        context=context,
        search=search,
        role=role,
        status=status,
        invitation_status=invitation_status,
    )
    view = build_users_view(
        workspace_name=context.workspace_name, actor_role=context.actor_role, users=users
    )
    return admin_template_response(
        request,
        "admin/users.html",
        view=view,
        page_title=view.page_title,
        principal=principal,
    )


@router.get("/admin/users/{user_id}", response_class=HTMLResponse, include_in_schema=False)
async def admin_user_detail_page(
    request: Request,
    user_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    loaded = await _load_web_admin_context(
        request, tenant_scope=tenant_scope, principal=principal, db=db
    )
    if isinstance(loaded, HTMLResponse):
        return loaded
    context, session = loaded
    try:
        user = await get_workspace_user_detail(session, context=context, user_id=user_id)
    except ProblemDetail:
        return admin_template_response(
            request,
            "admin/access_denied.html",
            status_code=404,
            page_title="Пользователь не найден",
            reason="Пользователь не найден в этой рабочей области.",
        )
    view = build_user_detail_view(
        workspace_name=context.workspace_name, actor_role=context.actor_role, user=user
    )
    return admin_template_response(
        request,
        "admin/user_detail.html",
        view=view,
        page_title=view.page_title,
        principal=principal,
    )


@router.get("/admin/files", response_class=HTMLResponse, include_in_schema=False)
async def admin_files_page(
    request: Request,
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
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    loaded = await _load_web_admin_context(
        request, tenant_scope=tenant_scope, principal=principal, db=db
    )
    if isinstance(loaded, HTMLResponse):
        return loaded
    context, session = loaded
    files = await list_admin_files(
        session,
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
    )
    view = build_files_view(
        workspace_name=context.workspace_name, actor_role=context.actor_role, files=files
    )
    return admin_template_response(
        request,
        "admin/files.html",
        view=view,
        page_title=view.page_title,
        principal=principal,
    )


@router.get("/admin/files/{meeting_id}", response_class=HTMLResponse, include_in_schema=False)
async def admin_file_detail_page(
    request: Request,
    meeting_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    loaded = await _load_web_admin_context(
        request, tenant_scope=tenant_scope, principal=principal, db=db
    )
    if isinstance(loaded, HTMLResponse):
        return loaded
    context, session = loaded
    try:
        file = await get_admin_file_detail(session, context=context, meeting_id=meeting_id)
    except ProblemDetail:
        return admin_template_response(
            request,
            "admin/access_denied.html",
            status_code=404,
            page_title="Файл не найден",
            reason="Файл не найден в этой рабочей области.",
        )
    view = build_file_detail_view(
        workspace_name=context.workspace_name, actor_role=context.actor_role, file=file
    )
    return admin_template_response(
        request,
        "admin/file_detail.html",
        view=view,
        page_title=view.page_title,
        principal=principal,
    )


@router.get("/admin/balance", response_class=HTMLResponse, include_in_schema=False)
async def admin_balance_page(
    request: Request,
    date_from: date | None = AdminDateQuery,
    date_to: date | None = AdminDateQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    loaded = await _load_web_admin_context(
        request, tenant_scope=tenant_scope, principal=principal, db=db
    )
    if isinstance(loaded, HTMLResponse):
        return loaded
    context, session = loaded
    usage = await get_usage_summary(session, context=context, date_from=date_from, date_to=date_to)
    view = build_balance_view(
        workspace_name=context.workspace_name, actor_role=context.actor_role, usage=usage
    )
    return admin_template_response(
        request,
        "admin/balance.html",
        view=view,
        page_title=view.page_title,
        principal=principal,
    )


@router.get("/admin/metrics", response_class=HTMLResponse, include_in_schema=False)
async def admin_metrics_page(
    request: Request,
    family: str | None = Query(
        default=None, pattern="^(adoption|usage|funnel|reliability|governance)$"
    ),
    date_from: date | None = AdminDateQuery,
    date_to: date | None = AdminDateQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    loaded = await _load_web_admin_context(
        request, tenant_scope=tenant_scope, principal=principal, db=db
    )
    if isinstance(loaded, HTMLResponse):
        return loaded
    context, session = loaded
    metrics = await get_admin_metrics(
        session, context=context, family=family, date_from=date_from, date_to=date_to
    )
    view = build_metrics_view(
        workspace_name=context.workspace_name,
        actor_role=context.actor_role,
        metrics=metrics,
        filters={
            "family": family,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
        },
    )
    return admin_template_response(
        request,
        "admin/metrics.html",
        view=view,
        page_title=view.page_title,
        principal=principal,
    )


@router.get("/admin/audit", response_class=HTMLResponse, include_in_schema=False)
async def admin_audit_page(
    request: Request,
    date_from: date | None = AdminDateQuery,
    date_to: date | None = AdminDateQuery,
    user_id: UUID | None = None,
    action: str | None = Query(default=None, max_length=120),
    object_kind: str | None = Query(default=None, max_length=64),
    object_id: str | None = Query(default=None, max_length=160),
    outcome: str | None = Query(default=None, max_length=32),
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    loaded = await _load_web_admin_context(
        request, tenant_scope=tenant_scope, principal=principal, db=db
    )
    if isinstance(loaded, HTMLResponse):
        return loaded
    context, session = loaded
    audit = await read_admin_audit_journal(
        session,
        context=context,
        date_from=date_from,
        date_to=date_to,
        user_id=user_id,
        action=action,
        object_kind=object_kind,
        object_id=object_id,
        outcome=outcome,
    )
    view = build_audit_view(
        workspace_name=context.workspace_name, actor_role=context.actor_role, audit=audit
    )
    return admin_template_response(
        request,
        "admin/audit.html",
        view=view,
        page_title=view.page_title,
        principal=principal,
    )


@router.post("/admin/invitations", include_in_schema=False, dependencies=[WebCSRFDependency])
async def admin_create_invitation_form(
    request: Request,
    target_contact: str = Form(...),
    invited_role: str = Form("member"),
    target_provider: str | None = Form(None),
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    loaded = await _load_web_admin_context(
        request, tenant_scope=tenant_scope, principal=principal, db=db
    )
    if isinstance(loaded, HTMLResponse):
        return loaded
    context, session = loaded
    await create_workspace_invitation(
        session,
        context=context,
        target_contact=target_contact,
        target_provider=_blank_to_none(target_provider),
        invited_role=invited_role,
    )
    await session.commit()
    return RedirectResponse("/admin/users", status_code=303)


@router.post(
    "/admin/invitations/{invitation_id}/revoke",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def admin_revoke_invitation_form(
    request: Request,
    invitation_id: UUID,
    reason_code: str | None = Form(None),
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    loaded = await _load_web_admin_context(
        request, tenant_scope=tenant_scope, principal=principal, db=db
    )
    if isinstance(loaded, HTMLResponse):
        return loaded
    context, session = loaded
    await revoke_workspace_invitation(
        session,
        context=context,
        invitation_id=invitation_id,
        reason_code=_blank_to_none(reason_code),
    )
    await session.commit()
    return RedirectResponse("/admin/users", status_code=303)


@router.post(
    "/admin/users/{user_id}/membership", include_in_schema=False, dependencies=[WebCSRFDependency]
)
async def admin_update_membership_form(
    request: Request,
    user_id: UUID,
    role: str | None = Form(None),
    status: str | None = Form(None),
    reason_code: str | None = Form(None),
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    loaded = await _load_web_admin_context(
        request, tenant_scope=tenant_scope, principal=principal, db=db
    )
    if isinstance(loaded, HTMLResponse):
        return loaded
    context, session = loaded
    await update_workspace_membership(
        session,
        context=context,
        target_user_id=user_id,
        requested_role=_blank_to_none(role),
        requested_status=_blank_to_none(status),
        reason_code=_blank_to_none(reason_code),
    )
    await session.commit()
    return RedirectResponse(f"/admin/users/{user_id}", status_code=303)


@router.post(
    "/admin/files/{meeting_id}/review-access",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def admin_review_access_form(
    request: Request,
    meeting_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    loaded = await _load_web_admin_context(
        request, tenant_scope=tenant_scope, principal=principal, db=db
    )
    if isinstance(loaded, HTMLResponse):
        return loaded
    context, session = loaded
    response = await record_admin_review_access(session, context=context, meeting_id=meeting_id)
    await session.commit()
    return RedirectResponse(str(response["review_path"]), status_code=303)


@router.post(
    "/admin/files/{meeting_id}/exports", include_in_schema=False, dependencies=[WebCSRFDependency]
)
async def admin_export_file_form(
    request: Request,
    meeting_id: UUID,
    artifact_classes: list[str] = AdminArtifactClassesForm,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    loaded = await _load_web_admin_context(
        request, tenant_scope=tenant_scope, principal=principal, db=db
    )
    if isinstance(loaded, HTMLResponse):
        return loaded
    context, session = loaded
    meeting = await load_workspace_meeting(session, context.workspace_id, meeting_id)
    result = await latest_processing_result(
        session, workspace_id=context.workspace_id, meeting_id=meeting_id
    )
    requested = _artifact_classes_from_form(artifact_classes)
    await create_export_package(
        session,
        meeting=meeting,
        access=admin_meeting_access(context),
        requested_artifacts=requested,
        result=result,
        actor_user_id=principal.user_id,
        device_id=device.device_id,
    )
    await session.commit()
    return RedirectResponse(f"/admin/files/{meeting_id}", status_code=303)


@router.post(
    "/admin/files/{meeting_id}/deletion-requests",
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def admin_delete_file_form(
    request: Request,
    meeting_id: UUID,
    confirm: str | None = Form(None),
    reason_code: DeletionReasonCode = AdminDeletionReasonForm,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    device: DeviceContext = DeviceDependency,
    storage: object = StorageDependency,
    db: AsyncSession | None = WebDbDependency,
) -> Response:
    loaded = await _load_web_admin_context(
        request, tenant_scope=tenant_scope, principal=principal, db=db
    )
    if isinstance(loaded, HTMLResponse):
        return loaded
    if confirm != "true":
        return admin_template_response(
            request,
            "admin/access_denied.html",
            status_code=422,
            page_title="Подтвердите удаление",
            reason="Для удаления встречи нужно поставить галочку подтверждения.",
            principal=principal,
        )
    context, session = loaded
    meeting = await load_workspace_meeting(session, context.workspace_id, meeting_id)
    await request_meeting_deletion(
        session,
        meeting=meeting,
        actor_user_id=principal.user_id,
        device_id=device.device_id,
        confirmation_boundary=BOUNDED_DELETE_COPY,
        request_source=DeletionRequestSource.ADMIN,
        reason_code=reason_code,
        storage=storage,
    )
    await session.commit()
    return RedirectResponse(f"/admin/files/{meeting_id}", status_code=303)


async def _load_web_admin_context(
    request: Request,
    *,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
    db: AsyncSession | None,
) -> tuple[object, AsyncSession] | HTMLResponse:
    if db is None:
        return admin_template_response(
            request,
            "admin/access_denied.html",
            status_code=503,
            page_title="Администрирование",
            reason="Админка временно недоступна",
        )
    try:
        context = await load_admin_workspace_context(
            db, tenant_scope=tenant_scope, principal=principal
        )
    except ProblemDetail:
        return admin_template_response(
            request,
            "admin/access_denied.html",
            status_code=403,
            page_title="Нет доступа",
            reason="Админка доступна только владельцам и администраторам рабочей области.",
        )
    return context, db


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _artifact_classes_from_form(values: list[str]) -> list[ArtifactClass]:
    allowed = {"audio", "transcript", "summary"}
    requested = [value for value in values if value in allowed]
    if not requested:
        requested = ["audio", "transcript", "summary"]
    return requested  # type: ignore[return-value]
