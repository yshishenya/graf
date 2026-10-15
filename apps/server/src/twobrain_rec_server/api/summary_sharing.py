"""F286 owner commands and deliberate anonymous opt-out, with normal auth/CSRF."""

import re
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.ingest import get_request_db_session
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.auth.dependencies import (
    get_optional_principal,
    get_principal,
    get_tenant_scope,
    require_web_csrf,
)
from twobrain_rec_server.cabinet import summary_sharing as sharing
from twobrain_rec_server.cabinet.access import hash_share_token
from twobrain_rec_server.db.models.summary_sharing import SummaryEmailSuppression

router = APIRouter(prefix="/api/v1/cabinet", tags=["summary-sharing"])
Tenant = Depends(get_tenant_scope)
Db = Depends(get_request_db_session)
Csrf = Depends(require_web_csrf)
Principal = Depends(get_principal)
OptionalPrincipal = Depends(get_optional_principal)


class LinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    template_key: str = Field(min_length=1, max_length=64)
    expires_in_days: Literal[7, 30, 90] = 30


class LinkChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grant_id: UUID
    expected_version: int = Field(ge=1)
    template_key: str | None = Field(default=None, min_length=1, max_length=64)
    expires_in_days: Literal[7, 30, 90] = 30


class BatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    template_key: str = Field(min_length=1, max_length=64)
    recipients: list[str] = Field(min_length=1, max_length=250)
    idempotency_key: str = Field(min_length=1, max_length=128)


def db_required(db):
    if db is None:
        sharing.fail("summary_sharing_unavailable", 503)
    return db


def owner_args(scope, meeting_id):
    return {
        "workspace_id": scope.workspace_id,
        "meeting_id": meeting_id,
        "actor_user_id": scope.user_id,
    }


def private_response(content, status=200):
    from fastapi.encoders import jsonable_encoder
    from fastapi.responses import JSONResponse

    return JSONResponse(
        jsonable_encoder(content),
        status_code=status,
        headers={
            "Cache-Control": "private, no-store",
            "Referrer-Policy": "no-referrer",
            "X-Robots-Tag": "noindex, nofollow",
        },
    )


@router.get("/meetings/{meeting_id}/summary-sharing/preview")
async def preview(
    request: Request,
    meeting_id: UUID,
    template_key: str = Query(min_length=1, max_length=64),
    scope: TenantScope = Tenant,
    db: AsyncSession | None = Db,
):
    db = db_required(db)
    meeting = await sharing.owner_meeting(db, **owner_args(scope, meeting_id))
    _outcome, projection = await sharing.preview_summary(
        db, meeting=meeting, template_key=template_key
    )
    return private_response({"template_key": template_key, "projection": projection})


@router.get("/meetings/{meeting_id}/summary-sharing/link")
async def get_link(
    request: Request, meeting_id: UUID, scope: TenantScope = Tenant, db: AsyncSession | None = Db
):
    db = db_required(db)
    await sharing.owner_meeting(db, **owner_args(scope, meeting_id))
    grant = await sharing.current_link(db, workspace_id=scope.workspace_id, meeting_id=meeting_id)
    return private_response(
        await sharing.link_view(db, grant=grant, settings=request.app.state.settings)
    )


@router.post("/meetings/{meeting_id}/summary-sharing/link", dependencies=[Csrf])
async def create_link(
    request: Request,
    meeting_id: UUID,
    payload: LinkRequest,
    scope: TenantScope = Tenant,
    db: AsyncSession | None = Db,
):
    db = db_required(db)
    view = await sharing.create_link(
        db,
        settings=request.app.state.settings,
        **owner_args(scope, meeting_id),
        device_id=scope.device_id,
        template_key=payload.template_key,
        expires_in_days=payload.expires_in_days,
    )
    await db.commit()
    return private_response(view)


@router.post("/meetings/{meeting_id}/summary-sharing/link/{operation}", dependencies=[Csrf])
async def change_link(
    request: Request,
    meeting_id: UUID,
    operation: Literal["update", "rotate", "expiry"],
    payload: LinkChangeRequest,
    scope: TenantScope = Tenant,
    db: AsyncSession | None = Db,
):
    db = db_required(db)
    view = await sharing.change_link(
        db,
        settings=request.app.state.settings,
        **owner_args(scope, meeting_id),
        device_id=scope.device_id,
        operation=operation,
        **payload.model_dump(),
    )
    await db.commit()
    return private_response(view)


@router.delete("/meetings/{meeting_id}/summary-sharing/link", dependencies=[Csrf])
async def revoke_link(
    request: Request,
    meeting_id: UUID,
    payload: LinkChangeRequest,
    scope: TenantScope = Tenant,
    db: AsyncSession | None = Db,
):
    db = db_required(db)
    view = await sharing.change_link(
        db,
        settings=request.app.state.settings,
        **owner_args(scope, meeting_id),
        device_id=scope.device_id,
        operation="revoke",
        **payload.model_dump(),
    )
    await db.commit()
    return private_response(view)


@router.post("/meetings/{meeting_id}/summary-sharing/batches", dependencies=[Csrf])
async def create_batch(
    request: Request,
    meeting_id: UUID,
    payload: BatchRequest,
    scope: TenantScope = Tenant,
    db: AsyncSession | None = Db,
):
    db = db_required(db)
    batch = await sharing.create_batch(
        db,
        settings=request.app.state.settings,
        **owner_args(scope, meeting_id),
        device_id=scope.device_id,
        **payload.model_dump(),
    )
    view = await sharing.batch_view(db, batch, settings=request.app.state.settings)
    await db.commit()
    return private_response(view)


@router.get("/meetings/{meeting_id}/summary-sharing/batches/{batch_id}")
async def get_batch(
    request: Request,
    meeting_id: UUID,
    batch_id: UUID,
    scope: TenantScope = Tenant,
    db: AsyncSession | None = Db,
):
    db = db_required(db)
    batch = await sharing.get_batch(db, **owner_args(scope, meeting_id), batch_id=batch_id)
    return private_response(
        await sharing.batch_view(db, batch, settings=request.app.state.settings)
    )


@router.post(
    "/meetings/{meeting_id}/summary-sharing/batches/{batch_id}/cancel", dependencies=[Csrf]
)
async def cancel_batch(
    request: Request,
    meeting_id: UUID,
    batch_id: UUID,
    scope: TenantScope = Tenant,
    db: AsyncSession | None = Db,
):
    db = db_required(db)
    batch = await sharing.get_batch(db, **owner_args(scope, meeting_id), batch_id=batch_id)
    await sharing.cancel_batch(db, batch=batch)
    view = await sharing.batch_view(db, batch, settings=request.app.state.settings)
    await db.commit()
    return private_response(view)


@router.post(
    "/meetings/{meeting_id}/summary-sharing/batches/{batch_id}/recipients/{recipient_id}/retry",
    dependencies=[Csrf],
)
async def retry_recipient(
    request: Request,
    meeting_id: UUID,
    batch_id: UUID,
    recipient_id: UUID,
    scope: TenantScope = Tenant,
    db: AsyncSession | None = Db,
):
    db = db_required(db)
    batch = await sharing.get_batch(db, **owner_args(scope, meeting_id), batch_id=batch_id)
    await sharing.retry_recipient(
        db, batch=batch, recipient_id=recipient_id, settings=request.app.state.settings
    )
    view = await sharing.batch_view(db, batch, settings=request.app.state.settings)
    await db.commit()
    return private_response(view)


@router.get(
    "/meetings/{meeting_id}/summary-sharing/form",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def sharing_form(
    request: Request,
    meeting_id: UUID,
    template_key: str = Query(default="meeting_minutes", max_length=64),
    batch_id: UUID | None = None,
    scope: TenantScope = Tenant,
    db: AsyncSession | None = Db,
    principal=Principal,
):
    from twobrain_rec_server.cabinet.rendering import render_summary_sharing_form
    from twobrain_rec_server.cabinet.web_routes.support import _csrf_token_for_principal

    db = db_required(db)
    await sharing.owner_meeting(db, **owner_args(scope, meeting_id))
    link = await sharing.link_view(
        db,
        grant=await sharing.current_link(
            db, workspace_id=scope.workspace_id, meeting_id=meeting_id
        ),
        settings=request.app.state.settings,
    )
    batch = (
        await sharing.get_batch(db, **owner_args(scope, meeting_id), batch_id=batch_id)
        if batch_id
        else None
    )
    body = render_summary_sharing_form(
        meeting_id=str(meeting_id),
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=scope),
        template_key=template_key,
        share_workspace_id=str(scope.workspace_id),
        link=link,
        batch=await sharing.batch_view(db, batch, settings=request.app.state.settings)
        if batch
        else None,
    )
    return HTMLResponse(
        body,
        headers={
            "Cache-Control": "private, no-store",
            "Referrer-Policy": "no-referrer",
            "X-Robots-Tag": "noindex, nofollow",
        },
    )


@router.post(
    "/meetings/{meeting_id}/summary-sharing/form", dependencies=[Csrf], include_in_schema=False
)
async def sharing_form_action(
    request: Request,
    meeting_id: UUID,
    scope: TenantScope = Tenant,
    db: AsyncSession | None = Db,
    principal=Principal,
):
    db = db_required(db)
    form = await request.form()
    template = str(form.get("template_key", "meeting_minutes"))
    action = form.get("action")
    batch_id = None
    try:
        if action == "link":
            payload = LinkRequest(
                template_key=template, expires_in_days=form.get("expires_in_days", 30)
            )
            await sharing.create_link(
                db,
                settings=request.app.state.settings,
                **owner_args(scope, meeting_id),
                device_id=scope.device_id,
                **payload.model_dump(),
            )
        elif action == "send":
            addresses = [
                value.strip()
                for value in re.split(r"[,;\s]+", str(form.get("recipients", "")))
                if value.strip()
            ]
            payload = BatchRequest(
                template_key=template,
                recipients=addresses,
                idempotency_key=str(form.get("idempotency_key") or uuid4()),
            )
            batch = await sharing.create_batch(
                db,
                settings=request.app.state.settings,
                **owner_args(scope, meeting_id),
                device_id=scope.device_id,
                **payload.model_dump(),
            )
            batch_id = batch.id
        elif action in ("update", "rotate", "expiry", "revoke"):
            payload = LinkChangeRequest(
                grant_id=form.get("grant_id"),
                expected_version=form.get("expected_version"),
                template_key=template,
                expires_in_days=form.get("expires_in_days", 30),
            )
            await sharing.change_link(
                db,
                settings=request.app.state.settings,
                **owner_args(scope, meeting_id),
                device_id=scope.device_id,
                operation=action,
                **payload.model_dump(),
            )
        elif action in ("cancel", "retry"):
            batch_id = UUID(str(form.get("batch_id")))
            batch = await sharing.get_batch(db, **owner_args(scope, meeting_id), batch_id=batch_id)
            if action == "cancel":
                await sharing.cancel_batch(db, batch=batch)
            else:
                await sharing.retry_recipient(
                    db,
                    batch=batch,
                    recipient_id=UUID(str(form.get("recipient_id"))),
                    settings=request.app.state.settings,
                )
        else:
            sharing.fail("invalid_share_operation", 422)
    except (ValidationError, ValueError):
        await db.rollback()
        from twobrain_rec_server.cabinet.rendering import render_summary_sharing_form
        from twobrain_rec_server.cabinet.web_routes.support import _csrf_token_for_principal

        return HTMLResponse(
            render_summary_sharing_form(
                meeting_id=str(meeting_id),
                csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=scope),
                template_key=template,
                share_workspace_id=str(scope.workspace_id),
                error="Проверьте адреса получателей и параметры ссылки.",
                idempotency_key=str(form.get("idempotency_key") or uuid4()),
            ),
            status_code=422,
            headers={
                "Cache-Control": "private, no-store",
                "Referrer-Policy": "no-referrer",
                "X-Robots-Tag": "noindex, nofollow",
            },
        )
    except sharing.ProblemDetail as exc:
        if exc.status not in (409, 422, 503):
            raise
        await db.rollback()
        from twobrain_rec_server.cabinet.rendering import render_summary_sharing_form
        from twobrain_rec_server.cabinet.web_routes.support import _csrf_token_for_principal

        error = (
            "Проверьте адреса получателей."
            if exc.status == 422
            else "Состояние изменилось. Обновите страницу и проверьте отправку."
            if exc.status == 409
            else "Отправка сейчас недоступна. Попробуйте позже."
        )
        return HTMLResponse(
            render_summary_sharing_form(
                meeting_id=str(meeting_id),
                csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=scope),
                template_key=template,
                share_workspace_id=str(scope.workspace_id),
                error=error,
                idempotency_key=str(form.get("idempotency_key") or uuid4()),
            ),
            status_code=exc.status,
            headers={
                "Cache-Control": "private, no-store",
                "Referrer-Policy": "no-referrer",
                "X-Robots-Tag": "noindex, nofollow",
            },
        )
    await db.commit()
    from urllib.parse import urlencode

    query = urlencode(
        {
            "template_key": template,
            "workspace_id": str(scope.workspace_id),
            **({"batch_id": str(batch_id)} if batch_id else {}),
        }
    )
    return RedirectResponse(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-sharing/form?{query}", status_code=303
    )


@router.api_route(
    "/summary-sharing/opt-out/{token}", methods=["GET", "POST"], include_in_schema=False
)
async def opt_out(request: Request, token: str, workspace_id: UUID):
    from twobrain_rec_server.db.tenant_context import TenantDatabaseContext, apply_tenant_context

    factory = getattr(request.app.state, "db_sessionmaker", None)
    if factory is None or len(token) > 128:
        sharing.fail("share_not_found", 404)
    async with factory() as db:
        await apply_tenant_context(
            db,
            TenantDatabaseContext(
                organization_id=UUID(int=0),
                workspace_id=workspace_id,
                user_id=UUID(int=0),
                context_kind="request",
            ),
        )
        row = await db.scalar(
            select(SummaryEmailSuppression)
            .where(
                SummaryEmailSuppression.workspace_id == workspace_id,
                SummaryEmailSuppression.token_hash == hash_share_token(token),
            )
            .with_for_update()
        )
        if row is None:
            sharing.fail("share_not_found", 404)
        if request.method == "POST":
            # Explicit POST is intentional; bearer capability affects email preference only.
            row.opted_out_at = row.opted_out_at or datetime.now(UTC)
            await db.commit()
            body = "<h1>Автоматические письма отключены</h1><p>Доступ к итогам сохранён.</p>"
        else:
            body = '<h1>Отключить автоматические письма?</h1><p>Это касается итогов от этого отправителя. Доступ к документам сохранится.</p><form method="post"><button type="submit">Отключить</button></form>'
    return HTMLResponse(
        '<!doctype html><html lang="ru"><meta name="viewport" content="width=device-width, initial-scale=1"><title>GRAF</title><body>'
        + body
        + "</body></html>",
        headers={
            "Cache-Control": "private, no-store",
            "Referrer-Policy": "no-referrer",
            "X-Robots-Tag": "noindex, nofollow",
        },
    )


@router.get("/summary-sharing/received/{recipient_id}", include_in_schema=False)
async def received_summary(
    request: Request, recipient_id: UUID, workspace_id: UUID, principal=OptionalPrincipal
):
    from urllib.parse import urlencode

    from twobrain_rec_server.api.cabinet import (
        _recipient_share_access_proof,
        _verified_invitation_address_hashes,
    )
    from twobrain_rec_server.auth.dependencies import get_web_owner_tenant_scope
    from twobrain_rec_server.cabinet.access import lock_shareable_meeting
    from twobrain_rec_server.cabinet.rendering import render_shared_meeting_summary_page
    from twobrain_rec_server.db.models.summary_sharing import (
        PublishedMeetingSummary,
        SummaryDeliveryBatch,
        SummaryRecipientDelivery,
    )
    from twobrain_rec_server.db.tenant_context import TenantDatabaseContext, apply_tenant_context

    if principal is None:
        return RedirectResponse(
            "/login?"
            + urlencode(
                {
                    "next": str(request.url.path)
                    + "?"
                    + urlencode({"workspace_id": str(workspace_id)})
                }
            ),
            status_code=303,
        )
    scope = await get_web_owner_tenant_scope(
        request,
        principal=principal,
        x_workspace_id=request.headers.get("X-Workspace-Id"),
        x_device_id=request.headers.get("X-Device-Id"),
        desktop_calendar_auth_cookie=None,
    )
    verified = await _verified_invitation_address_hashes(request, recipient_scope=scope)
    proof = await _recipient_share_access_proof(
        request, recipient_scope=scope, owner_workspace_id=workspace_id
    )
    factory = getattr(request.app.state, "db_sessionmaker", None)
    if factory is None:
        sharing.fail("share_not_found", 404)
    async with factory() as db:
        await apply_tenant_context(
            db,
            TenantDatabaseContext(
                organization_id=UUID(int=0),
                workspace_id=workspace_id,
                user_id=principal.user_id,
                context_kind="request",
            ),
        )
        row = await db.scalar(
            select(SummaryRecipientDelivery).where(
                SummaryRecipientDelivery.id == recipient_id,
                SummaryRecipientDelivery.workspace_id == workspace_id,
                SummaryRecipientDelivery.state.in_(("sending", "accepted", "unknown")),
            )
        )
        if (
            row is None
            or row.normalized_address_hash not in verified
            or not proof.user_is_active
            or row.read_expires_at is None
            or row.read_expires_at <= datetime.now(UTC)
        ):
            sharing.fail("share_not_found", 404)
        batch = await db.get(SummaryDeliveryBatch, row.batch_id)
        meeting = await lock_shareable_meeting(
            db, workspace_id=workspace_id, meeting_id=batch.meeting_id
        )
        if row.invitation_id is not None:
            from twobrain_rec_server.db.models import MeetingShareInvitation

            invitation = await db.get(MeetingShareInvitation, row.invitation_id)
            if (
                invitation is None
                or invitation.status != "accepted"
                or invitation.resolved_user_id != principal.user_id
            ):
                sharing.fail("share_not_found", 404)
        elif row.user_id != principal.user_id:
            sharing.fail("share_not_found", 404)
        if row.invitation_id is None:
            from twobrain_rec_server.cabinet.access import decide_meeting_access

            decision = await decide_meeting_access(
                db,
                meeting,
                workspace_id=workspace_id,
                viewer_user_id=principal.user_id,
                recipient_proof=proof,
            )
            if not decision.can_view:
                sharing.fail("share_not_found", 404)
        else:
            from twobrain_rec_server.db.models import MeetingShareGrant

            grant = await db.scalar(
                select(MeetingShareGrant).where(
                    MeetingShareGrant.id == row.grant_id,
                    MeetingShareGrant.workspace_id == workspace_id,
                    MeetingShareGrant.meeting_id == meeting.id,
                    MeetingShareGrant.status == "active",
                    MeetingShareGrant.audience_id == principal.user_id,
                )
            )
            if grant is None:
                sharing.fail("share_not_found", 404)
        snapshot = await db.scalar(
            select(PublishedMeetingSummary).where(
                PublishedMeetingSummary.id == batch.published_summary_id,
                PublishedMeetingSummary.workspace_id == workspace_id,
                PublishedMeetingSummary.meeting_id == meeting.id,
            )
        )
        if snapshot is None or snapshot.schema_version != 1:
            sharing.fail("share_not_found", 404)
        projection = sharing.reader_projection(snapshot.projection_json)
    if "text/html" not in request.headers.get("accept", "").lower():
        return private_response(projection)
    return HTMLResponse(
        render_shared_meeting_summary_page(
            meeting_title=projection["meeting_label"],
            occurred_at=datetime.fromisoformat(str(projection["occurred_at"])),
            duration_seconds=projection["duration_seconds"],
            summary_sections=projection["summary_sections"],
            protocol=projection["protocol"],
            authenticated=True,
        ),
        headers={
            "Cache-Control": "private, no-store",
            "Referrer-Policy": "no-referrer",
            "X-Robots-Tag": "noindex, nofollow",
        },
    )


@router.get("/meetings/{meeting_id}/summary-sharing/batches")
async def batch_by_operation(
    request: Request,
    meeting_id: UUID,
    idempotency_key: str = Query(min_length=1, max_length=128),
    scope: TenantScope = Tenant,
    db: AsyncSession | None = Db,
):
    from twobrain_rec_server.db.models.summary_sharing import SummaryDeliveryBatch

    db = db_required(db)
    await sharing.owner_meeting(db, **owner_args(scope, meeting_id))
    batch = await db.scalar(
        select(SummaryDeliveryBatch).where(
            SummaryDeliveryBatch.workspace_id == scope.workspace_id,
            SummaryDeliveryBatch.meeting_id == meeting_id,
            SummaryDeliveryBatch.owner_user_id == scope.user_id,
            SummaryDeliveryBatch.idempotency_key == idempotency_key,
        )
    )
    if batch is None:
        sharing.fail("summary_batch_not_found", 404)
    return private_response(
        await sharing.batch_view(db, batch, settings=request.app.state.settings)
    )


@router.get("/meetings/{meeting_id}/summary-sharing/recipients")
async def recipient_candidates(
    request: Request,
    meeting_id: UUID,
    query: str = Query(default="", max_length=160),
    scope: TenantScope = Tenant,
    db: AsyncSession | None = Db,
):
    from twobrain_rec_server.cabinet.access import search_share_recipients
    from twobrain_rec_server.db.models import ExternalIdentity

    db = db_required(db)
    await sharing.owner_meeting(db, **owner_args(scope, meeting_id))
    people = await search_share_recipients(
        db,
        workspace_id=scope.workspace_id,
        viewer_user_id=scope.user_id,
        device_id=scope.device_id,
        query=query,
        meeting_id=meeting_id,
    )
    results = []
    for person in people:
        email = await db.scalar(
            select(ExternalIdentity.email)
            .where(
                ExternalIdentity.user_id == person.user_id,
                ExternalIdentity.is_verified.is_(True),
                ExternalIdentity.is_active.is_(True),
            )
            .order_by(ExternalIdentity.id)
            .limit(1)
        )
        if email:
            results.append(
                {
                    "user_id": str(person.user_id),
                    "display_label": person.display_label,
                    "email": email,
                    "source": person.source,
                    "recipient_type": person.recipient_type,
                }
            )
    return private_response({"recipients": results})
