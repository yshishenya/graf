"""Authenticated quiet inbox, with a complete HTML fallback."""
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import exists, or_, select, tuple_

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.cabinet.templates import cabinet_html_response, render_template
from twobrain_rec_server.cabinet.web_routes.support import (
    PrincipalDependency,
    WebCSRFDependency,
    WebDbDependency,
    WebTenantDependency,
    _csrf_token_for_principal,
)
from twobrain_rec_server.db.models import Meeting
from twobrain_rec_server.db.models.notifications import ServerNotification as Notice
from twobrain_rec_server.notifications.inbox import (
    acknowledge_revision,
    authorized_card,
    decode_cursor,
    encode_cursor,
)

router = APIRouter(tags=['cabinet-web'])
Filter = Literal['important', 'history']


async def notification_snapshot_db(request: Request, tenant_scope: TenantScope = WebTenantDependency):
    from twobrain_rec_server.db.tenant_context import apply_tenant_scope
    factory = getattr(request.app.state, "db_sessionmaker", None)
    if factory is None:
        yield None
        return
    async with factory() as db:
        await db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
        await apply_tenant_scope(db, tenant_scope)
        yield db

SnapshotDb = Depends(notification_snapshot_db)


async def inbox_page(request, db, scope, principal, filter, cursor, limit):
    if db is None:
        raise ProblemDetail(status=503, code='cabinet_store_unavailable', title='Cabinet store unavailable')
    now = datetime.now(UTC)
    binding = f'{principal.user_id}:{principal.session_id}:{scope.workspace_id}:{filter}:updated-v1'
    secret = request.app.state.settings.web_csrf_secret
    visible_meeting = exists(select(Meeting.id).where(
        Meeting.id == Notice.meeting_id, Meeting.workspace_id == scope.workspace_id,
        Meeting.created_by_user_id == principal.user_id, Meeting.deleted_at.is_(None),
        or_(Meeting.deletion_state.is_(None), Meeting.deletion_state == 'none')))
    base = [Notice.recipient_id == principal.user_id,
            or_(Notice.expires_at.is_(None), Notice.expires_at > now),
            or_((Notice.family == 'result') & visible_meeting, Notice.family == 'share')]
    # The dot covers every accessible current action, independently of pagination.
    dot = bool(await db.scalar(select(exists(select(Notice.id).where(*base,
        Notice.family == 'result', Notice.requires_action.is_(True),
        Notice.resolved_at.is_(None), Notice.revision > Notice.read_revision)))))
    query = select(Notice).where(*base)
    if filter == 'important':
        query = query.where(Notice.requires_action.is_(True), Notice.resolved_at.is_(None))
    try:
        marker = decode_cursor(cursor, binding=binding, secret=secret, now=now) if cursor else None
    except ValueError as exc:
        raise ProblemDetail(status=422, code='notification_cursor_invalid', title='Refresh the inbox') from exc
    items = []
    last = marker
    # Fetch bounded batches, walking past revoked shares without exposing their titles.
    while len(items) <= limit:
        batch_query = query.where(tuple_(Notice.updated_at, Notice.id) < last) if last else query
        rows = list(await db.scalars(batch_query.order_by(Notice.updated_at.desc(), Notice.id.desc()).limit(limit+1)))
        if not rows:
            break
        for row in rows:
            card = await authorized_card(db, row, tenant_scope=scope, sessionmaker=request.app.state.db_sessionmaker)
            last = (row.updated_at, row.id)
            if card:
                items.append((card, last))
                if len(items) > limit:
                    break
        if len(rows) < limit+1:
            break
    next_cursor = encode_cursor(items[limit-1][1], binding=binding, secret=secret, now=now) if len(items)>limit else None
    return dict(items=[card for card, _ in items[:limit]], next_cursor=next_cursor,
                has_unseen_action_required=dot, generated_at=now.isoformat())


@router.get('/api/v1/notifications')
async def notifications_api(request: Request, filter: Filter = 'important',
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency, db=SnapshotDb):
    data = await inbox_page(request, db, tenant_scope, principal, filter, cursor, limit)
    return JSONResponse(data, headers={'Cache-Control':'no-store'})


@router.get('/notifications', response_class=HTMLResponse)
@router.get('/desktop/notifications', response_class=HTMLResponse)
async def notifications_html(request: Request, filter: Filter = 'important',
    cursor: Annotated[str | None, Query(max_length=2048)] = None,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency, db=SnapshotDb):
    data = await inbox_page(request, db, tenant_scope, principal, filter, cursor, 30)
    embedded = request.url.path.startswith('/desktop/')
    html = render_template('cabinet/pages/notification_history.html',
        **data, filter=filter, embedded=embedded, csrf_token=_csrf_token_for_principal(request, principal))
    return cabinet_html_response(html)


@router.post('/api/v1/notifications/{notification_id}/read', dependencies=[WebCSRFDependency])
async def notification_read(request: Request, notification_id: UUID,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency, db=WebDbDependency):
    if db is None:
        raise ProblemDetail(status=503, code='cabinet_store_unavailable', title='Cabinet store unavailable')
    row = await db.scalar(select(Notice).where(Notice.id==notification_id,
        Notice.recipient_id==principal.user_id).with_for_update())
    if row is None or (row.expires_at and row.expires_at <= datetime.now(UTC)) or not await authorized_card(
        db,row,tenant_scope=tenant_scope,sessionmaker=request.app.state.db_sessionmaker):
        raise ProblemDetail(status=404, code='notification_unavailable', title='Notification unavailable')
    form = await request.form()
    try:
        acknowledge_revision(row, int(form.get('revision', '')))
    except (TypeError,ValueError) as exc:
        raise ProblemDetail(status=422, code='notification_revision_invalid', title='Refresh the inbox') from exc
    await db.commit()
    if request.headers.get('accept') == 'application/json':
        return JSONResponse({'read_revision':row.read_revision},headers={'Cache-Control':'no-store'})
    return RedirectResponse('/desktop/notifications' if form.get('embedded') == '1' else '/notifications',status_code=303)
