from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.billing.fair_use import appeal_persisted_review
from twobrain_rec_server.billing.trial import merged_user_lineage
from twobrain_rec_server.cabinet.rendering_shared import _page_shell
from twobrain_rec_server.cabinet.templates import cabinet_html_response
from twobrain_rec_server.cabinet.web_routes.support import (
    PrincipalDependency,
    WebCSRFDependency,
    WebDbDependency,
    WebTenantDependency,
    _csrf_token_for_principal,
)
from twobrain_rec_server.db.models import FairUseReviewRecord, Workspace
from twobrain_rec_server.product_analytics.browser_context import (
    build_request_browser_provider_context,
)

router = APIRouter(tags=["cabinet-web"])
MOSCOW = ZoneInfo("Europe/Moscow")
FairUseResultQuery = Query(default=None, max_length=24, alias="result")

_REASON_LABELS = {
    "automated_bulk": "автоматизированная массовая обработка",
    "resale": "перепродажа или предоставление сервиса третьим лицам",
    "limit_circumvention": "обход технических ограничений",
    "security_abuse": "подозрение на злоупотребление безопасностью",
}
_CAPABILITY_LABELS = {
    "server_processing": "обработка встреч",
    "storage": "хранилище",
    "exports": "экспорт данных",
}
_STATE_LABELS = {
    "notice": "Уведомление",
    "restricted": "Ограничение на проверке",
    "appealed": "Апелляция отправлена",
    "cleared": "Ограничение снято",
    "confirmed": "Ограничение подтверждено",
}


def _date_label(value: datetime) -> str:
    return value.astimezone(MOSCOW).strftime("%d.%m.%Y, %H:%M")


def _review_view(row: FairUseReviewRecord, *, now: datetime, can_appeal: bool) -> dict[str, object]:
    review_by = row.review_by.astimezone(UTC)
    return {
        "id": str(row.id),
        "capability": _CAPABILITY_LABELS.get(row.capability, "одна из функций продукта"),
        "reason_label": _REASON_LABELS.get(row.reason_code, "доказуемая неперсональная эксплуатация"),
        "state_label": _STATE_LABELS.get(row.state, "Статус уточняется"),
        "review_by_label": _date_label(review_by),
        "review_overdue": review_by <= now,
        "support_reference": f"FU-{row.id.hex[:12].upper()}",
        "can_appeal": can_appeal and row.state in {"notice", "restricted"},
        "appealed": row.state == "appealed",
    }


async def _render_fair_use_page(
    request: Request,
    *,
    embedded: bool,
    tenant_scope: TenantScope,
    principal: AuthenticatedPrincipal,
    db: AsyncSession | None,
    result: str | None = None,
) -> HTMLResponse:
    reviews: list[dict[str, object]] = []
    unavailable = db is None
    if db is not None:
        lineage = merged_user_lineage(principal.user_id)
        lineage_user_ids = set(await db.scalars(select(lineage.c.user_id)))
        lineage_user_ids.add(principal.user_id)
        rows = await db.scalars(
            select(FairUseReviewRecord)
            .where(
                or_(
                    FairUseReviewRecord.subject_user_id.in_(lineage_user_ids),
                    exists(
                        select(1).where(
                            Workspace.id == FairUseReviewRecord.workspace_id,
                            Workspace.owner_user_id == principal.user_id,
                            Workspace.kind.in_(("personal", "linked")),
                        )
                    ),
                ),
            )
            .order_by(FairUseReviewRecord.review_by.desc(), FairUseReviewRecord.created_at.desc())
        )
        now = datetime.now(UTC)
        reviews = [
            _review_view(row, now=now, can_appeal=row.subject_user_id in lineage_user_ids)
            for row in rows
        ]
        await db.commit()
    html = _page_shell(
        "Проверка добросовестного использования",
        embedded=embedded,
        csrf_token=_csrf_token_for_principal(request, principal, tenant_scope=tenant_scope),
        product_analytics_provider=build_request_browser_provider_context(
            request,
            "fair_use",
            principal=principal,
            tenant_scope=tenant_scope,
            device_class="desktop_webview" if embedded else "browser",
        ),
        active_nav="settings",
        settings_active="account",
        content_template="cabinet/pages/fair_use_content.html",
        reviews=reviews,
        unavailable=unavailable,
        fair_use_result={
            "appealed": "Апелляция отправлена. Мы сохранили только технический статус обращения.",
            "already_appealed": "Апелляция уже отправлена и находится на проверке.",
            "unavailable": "Проверка сейчас недоступна. Попробуйте позже.",
        }.get(result),
        support_email=request.app.state.settings.billing_support_email,
        appeal_base_path="/desktop/account/fair-use" if embedded else "/account/fair-use",
        back_href="/desktop/meetings" if embedded else "/meetings",
    )
    return cabinet_html_response(html)


@router.get("/account/fair-use", response_class=HTMLResponse, include_in_schema=False)
@router.get("/desktop/account/fair-use", response_class=HTMLResponse, include_in_schema=False)
async def fair_use_page(
    request: Request,
    result: str | None = FairUseResultQuery,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> HTMLResponse:
    return await _render_fair_use_page(
        request,
        embedded=request.url.path.startswith("/desktop/"),
        tenant_scope=tenant_scope,
        principal=principal,
        db=db,
        result=result,
    )


@router.post(
    "/account/fair-use/{review_id}/appeal",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
@router.post(
    "/desktop/account/fair-use/{review_id}/appeal",
    response_class=HTMLResponse,
    include_in_schema=False,
    dependencies=[WebCSRFDependency],
)
async def fair_use_appeal(
    review_id: str,
    request: Request,
    tenant_scope: TenantScope = WebTenantDependency,
    principal: AuthenticatedPrincipal = PrincipalDependency,
    db: AsyncSession | None = WebDbDependency,
) -> RedirectResponse:
    if db is None:
        result = "unavailable"
    else:
        try:
            parsed_review_id = UUID(review_id)
        except ValueError:
            parsed_review_id = None
        appealed_at = datetime.now(UTC)
        existing = (
            await appeal_persisted_review(
                db,
                review_id=parsed_review_id,
                subject_user_id=principal.user_id,
                at=appealed_at,
            )
            if parsed_review_id is not None
            else None
        )
        if existing is None or existing.state in {"cleared", "confirmed"}:
            result = "unavailable"
        else:
            result = "appealed" if existing.appealed_at == appealed_at else "already_appealed"
            await db.commit()
    base = "/desktop/account/fair-use" if request.url.path.startswith("/desktop/") else "/account/fair-use"
    return RedirectResponse(f"{base}?result={result}", status_code=303)
