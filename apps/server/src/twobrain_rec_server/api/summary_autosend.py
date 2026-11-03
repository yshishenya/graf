"""Verified owner APIs for explicit summary automation."""

from html import escape
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.ingest import get_request_db_session
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.dependencies import (
    get_principal,
    get_web_owner_tenant_scope,
    require_web_csrf,
)
from twobrain_rec_server.cabinet.summary_autosend import (
    auto_state,
    disable_rule,
    preferences_view,
    save_rule,
    update_preferences,
)
from twobrain_rec_server.cabinet.templates import cabinet_static_asset_url
from twobrain_rec_server.cabinet.web_routes.support import _csrf_token_for_principal

router = APIRouter(prefix="/api/v1/cabinet", tags=["summary-auto-send"])
Owner = Annotated[TenantScope, Depends(get_web_owner_tenant_scope)]
Database = Annotated[AsyncSession | None, Depends(get_request_db_session)]
Principal = Annotated[AuthenticatedPrincipal, Depends(get_principal)]


class PreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0)
    ask_enabled: bool | None = None
    paused: bool | None = None


class AutoSendUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope: Literal["meeting", "series"]
    enabled: bool
    template_key: str = Field(min_length=1, max_length=64)
    recipient_user_ids: list[UUID] = Field(default_factory=list, max_length=50)
    expected_version: int = Field(ge=0)


class RuleDisable(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0)


def _database(db):
    if db is None:
        raise ProblemDetail(
            status=503, code="cabinet_store_unavailable", title="Настройки временно недоступны"
        )
    return db


def _private_json(value):
    return JSONResponse(
        content=jsonable_encoder(value),
        headers={
            "Cache-Control": "private, no-store",
            "Referrer-Policy": "no-referrer",
            "X-Robots-Tag": "noindex",
        },
    )


@router.get("/summary-sharing/preferences")
async def read_preferences(scope: Owner, db: Database):
    return _private_json(
        await preferences_view(
            _database(db), workspace_id=scope.workspace_id, owner_user_id=scope.user_id
        )
    )


@router.patch("/summary-sharing/preferences", dependencies=[Depends(require_web_csrf)])
async def patch_preferences(payload: PreferencesUpdate, scope: Owner, db: Database):
    db = _database(db)
    if payload.ask_enabled is None and payload.paused is None:
        raise ProblemDetail(status=422, code="empty_preferences_update", title="Выберите настройку")
    await update_preferences(
        db,
        workspace_id=scope.workspace_id,
        owner_user_id=scope.user_id,
        expected_version=payload.expected_version,
        ask_enabled=payload.ask_enabled,
        paused=payload.paused,
    )
    result = await preferences_view(
        db, workspace_id=scope.workspace_id, owner_user_id=scope.user_id
    )
    await db.commit()
    return _private_json(result)


@router.get("/meetings/{meeting_id}/summary-sharing/auto-send")
async def read_auto_send(meeting_id: UUID, request: Request, scope: Owner, db: Database):
    result = await auto_state(
        _database(db),
        settings=request.app.state.settings,
        workspace_id=scope.workspace_id,
        meeting_id=meeting_id,
        owner_user_id=scope.user_id,
    )
    await db.commit()
    return _private_json(result)


@router.post(
    "/meetings/{meeting_id}/summary-sharing/auto-send", dependencies=[Depends(require_web_csrf)]
)
async def write_auto_send(
    meeting_id: UUID, payload: AutoSendUpdate, request: Request, scope: Owner, db: Database
):
    result = await save_rule(
        _database(db),
        settings=request.app.state.settings,
        workspace_id=scope.workspace_id,
        meeting_id=meeting_id,
        owner_user_id=scope.user_id,
        scope=payload.scope,
        enabled=payload.enabled,
        template_key=payload.template_key,
        recipient_user_ids=payload.recipient_user_ids,
        expected_version=payload.expected_version,
    )
    await db.commit()
    return _private_json(result)


@router.post(
    "/summary-sharing/preferences/rules/{rule_id}/disable", dependencies=[Depends(require_web_csrf)]
)
async def disable_auto_send_rule(rule_id: UUID, payload: RuleDisable, scope: Owner, db: Database):
    result = await disable_rule(
        _database(db),
        workspace_id=scope.workspace_id,
        owner_user_id=scope.user_id,
        rule_id=rule_id,
        expected_version=payload.expected_version,
    )
    await db.commit()
    return _private_json(result)


@router.get(
    "/summary-sharing/preferences/form", response_class=HTMLResponse, include_in_schema=False
)
async def preferences_form(request: Request, scope: Owner, principal: Principal, db: Database):
    values = await preferences_view(
        _database(db), workspace_id=scope.workspace_id, owner_user_id=scope.user_id
    )
    csrf = escape(
        _csrf_token_for_principal(request, principal, tenant_scope=scope) or "", quote=True
    )
    stylesheet = escape(cabinet_static_asset_url("cabinet.css"), quote=True)
    fields = f'<input type="hidden" name="csrf_token" value="{csrf}">'
    rules = ""
    for rule in values["rules"]:
        if rule["enabled"]:
            label = "Эта встреча" if rule["scope"] == "meeting" else "Серия встреч"
            rules += (
                f'<form method="post" action="/api/v1/cabinet/summary-sharing/preferences/rules/{rule["id"]}/disable/form">'
                f'{fields}<input type="hidden" name="expected_version" value="{rule["version"]}">'
                f"<p>{label}: выбранный формат, {len(rule['recipient_user_ids'])} получателей.</p>"
                '<button class="button quiet" type="submit">Отключить правило</button></form>'
            )
    body = (
        f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>Отправка участникам — GRAF</title><link rel="stylesheet" href="{stylesheet}"></head>'
        '<body><main class="cabinet-main" id="cabinet-main"><div class="settings-page__content">'
        "<h1>Отправка участникам</h1><p>Итоги отправляются автоматически только по явно включённым правилам.</p>"
        '<form method="post" action="/api/v1/cabinet/summary-sharing/preferences/form">'
        f'{fields}<input type="hidden" name="expected_version" value="{values["version"]}">'
        f'<p><label><input type="checkbox" name="ask_enabled" value="true" {"checked" if values["ask_enabled"] else ""}> Предлагать отправить итоги</label></p>'
        f'<p><label><input type="checkbox" name="paused" value="true" {"checked" if values["paused"] else ""}> Приостановить автоотправку</label></p>'
        "<p>Возобновление действует на будущие встречи. Старые отменённые отправки не возобновятся.</p>"
        '<button class="button primary" type="submit">Сохранить</button></form>'
        f"<h2>Включённые правила</h2>{rules or '<p>Нет включённых правил.</p>'}"
        '<p><a href="/settings/summaries">Вернуться к настройкам итогов</a></p></div></main></body></html>'
    )
    return HTMLResponse(
        body,
        headers={
            "Cache-Control": "private, no-store",
            "X-Robots-Tag": "noindex",
            "Referrer-Policy": "no-referrer",
        },
    )


def _form_version(form):
    value = str(form.get("expected_version", ""))
    if not value.isdecimal() or len(value) > 10:
        raise ProblemDetail(status=422, code="invalid_settings_version", title="Обновите настройки")
    return int(value)


@router.post(
    "/summary-sharing/preferences/form",
    dependencies=[Depends(require_web_csrf)],
    include_in_schema=False,
)
async def save_preferences_form(request: Request, scope: Owner, db: Database):
    form = await request.form()
    try:
        await update_preferences(
            _database(db),
            workspace_id=scope.workspace_id,
            owner_user_id=scope.user_id,
            expected_version=_form_version(form),
            ask_enabled=form.get("ask_enabled") == "true",
            paused=form.get("paused") == "true",
        )
        await db.commit()
    except ProblemDetail as problem:
        if db is not None:
            await db.rollback()
        return _settings_form_error(problem)
    return RedirectResponse("/api/v1/cabinet/summary-sharing/preferences/form", status_code=303)


@router.post(
    "/summary-sharing/preferences/rules/{rule_id}/disable/form",
    dependencies=[Depends(require_web_csrf)],
    include_in_schema=False,
)
async def disable_rule_form(rule_id: UUID, request: Request, scope: Owner, db: Database):
    form = await request.form()
    try:
        await disable_rule(
            _database(db),
            workspace_id=scope.workspace_id,
            owner_user_id=scope.user_id,
            rule_id=rule_id,
            expected_version=_form_version(form),
        )
        await db.commit()
    except ProblemDetail as problem:
        if db is not None:
            await db.rollback()
        return _settings_form_error(problem)
    return RedirectResponse("/api/v1/cabinet/summary-sharing/preferences/form", status_code=303)


def _settings_form_error(problem):
    message = (
        "Настройки уже изменились. Откройте их снова и повторите действие."
        if problem.status == 409
        else "Не удалось сохранить настройку. Откройте настройки и повторите действие."
    )
    return HTMLResponse(
        '<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Настройки отправки — GRAF</title></head><body><main><h1>Настройка не сохранена</h1>"
        f'<p>{escape(message)}</p><a href="/api/v1/cabinet/summary-sharing/preferences/form">Вернуться к настройкам</a></main></body></html>',
        status_code=problem.status,
        headers={
            "Cache-Control": "private, no-store",
            "Referrer-Policy": "no-referrer",
            "X-Robots-Tag": "noindex",
        },
    )
