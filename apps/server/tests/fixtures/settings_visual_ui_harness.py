"""Synthetic settings preview; production templates, no database or external writes."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import Request
from fastapi.responses import HTMLResponse

from tests.fixtures.calendar_visual_ui_harness import app
from twobrain_rec_server.auth.workspace_onboarding import (
    WorkspaceAccessView,
    WorkspaceJoinOfferView,
)
from twobrain_rec_server.billing.catalog import plan_descriptor
from twobrain_rec_server.cabinet.rendering import (
    _page_shell,
    render_provider_link_settings_page,
    render_settings_page,
)
from twobrain_rec_server.cabinet.templates import render_template
from twobrain_rec_server.cabinet.user_time import apply_user_time_preference
from twobrain_rec_server.cabinet.view_models import (
    AccountDeviceView,
    AccountProfileView,
    AccountProviderView,
    AccountSessionView,
    AccountSettingsSurface,
    ProviderLinkSettingsSurface,
)


@app.middleware("http")
async def synthetic_settings_scope(request, call_next):
    apply_user_time_preference(user_id=UUID(int=1), workspace_id=UUID(int=4), session_id="synthetic", timezone="UTC")
    return await call_next(request)


@app.get("/settings", response_class=HTMLResponse)
@app.get("/desktop/settings", response_class=HTMLResponse)
@app.get("/settings/{category}", response_class=HTMLResponse)
@app.get("/desktop/settings/{category}", response_class=HTMLResponse)
def settings_preview(request: Request, category: str = "overview"):
    now = datetime.now(UTC)
    profile = AccountProfileView(
        "Александра — тестовый профиль",
        "alexandra@example.test",
        theme=request.query_params.get("theme", "dark"),
    )
    embedded = request.url.path.startswith("/desktop")
    if category == "upload-preview":
        return HTMLResponse(
            '<link rel="stylesheet" href="/static/cabinet/cabinet.css">'
            '<script defer src="/static/cabinet/cabinet.js"></script>'
            + render_template(
                "cabinet/fragments/manual_upload.html",
                embedded=embedded,
                upload_available=True,
                upload_endpoint="/synthetic-upload",
                detail_base_path="/meetings/",
                media_accept="audio/*",
            )
        )
    if category == "billing":
        free = request.query_params.get("plan") == "free"
        return HTMLResponse(
            _page_shell(
                "Тариф и оплата",
                embedded=embedded,
                active_nav="settings",
                settings_active="billing",
                profile=profile,
                csrf_token="synthetic-csrf",
                content_template="cabinet/pages/billing_overview_content.html",
                plan=plan_descriptor("free" if free else "personal"),
                plan_code="free" if free else "personal",
                billing_data_available=request.query_params.get("mode") != "unavailable",
                billing_owner=True,
                billing_role="owner",
                billing_enabled=request.query_params.get("payments") != "off",
                processing_used_label="0 мин 0 сек" if free else "2 ч 15 мин",
                free_processing_limit_label="300 минут",
                current_price_label="0 ₽" if free else "1 000 ₽",
                current_cycle_label="без оплаты" if free else "в месяц",
                storage_used_label="127,88 MB" if free else "200 MB",
                storage_capacity_label="250 MB" if free else "2 GB",
                trial_state="eligible" if free else "unavailable",
            )
        )
    if category == "provider-links":
        return HTMLResponse(
            render_provider_link_settings_page(
                ProviderLinkSettingsSurface(
                    link_state_id=UUID(int=7),
                    provider_label="VK",
                    status="callback_verified",
                    status_label="Провайдер подтверждён — подтвердите подключение в GRAF",
                    can_confirm=True,
                ),
                embedded=embedded,
                profile=profile,
                csrf_token="synthetic-csrf",
            )
        )
    surface = AccountSettingsSurface(
        profile=profile,
        providers=(AccountProviderView("email", "Email", "Подключен", True, now),),
        devices=(
            AccountDeviceView(UUID(int=1), "macOS", "2026.09.06.1", "Активно", now, True, False),
            AccountDeviceView(
                UUID(int=2),
                "MacBook Pro — рабочий компьютер",
                "2026.09.05.1",
                "Активно",
                now,
                False,
                True,
            ),
        ),
        sessions=(
            AccountSessionView(
                UUID(int=3), "Email", "Активна", now, now + timedelta(days=1), True, False
            ),
        ),
    )
    if request.query_params.get("mode") == "unavailable":
        surface = AccountSettingsSurface(unavailable=True)
    return HTMLResponse(
        render_settings_page(
            show_account_navigation=False,
            category=category,
            embedded=request.url.path.startswith("/desktop"),
            profile=profile,
            account_surface=surface,
            csrf_token="synthetic-csrf",
            workspace_spaces=(
                WorkspaceAccessView(UUID(int=4), "Личное пространство", "personal", "owner", True),
                WorkspaceAccessView(
                    UUID(int=5), "Команда исследований и развития", "organization", "member", False
                ),
            ),
            workspace_join_offers=(
                WorkspaceJoinOfferView(
                    UUID(int=6), "Тестовая команда", "member", now + timedelta(days=1)
                ),
            ),
            device_revoke_result=request.query_params.get("device_revoke"),
            profile_result=request.query_params.get("profile"),
            account_close_result=request.query_params.get("account_close"),
        )
    )


@app.get("/api/v1/cabinet/summary-templates")
def synthetic_summary_formats():
    return {
        "actor": str(UUID(int=1)), "workspace": str(UUID(int=4)),
        "can_manage_default": True, "default_template_key": "graf-auto-v1", "personal": [{
            "template_id": str(UUID(int=20)), "template_key": "synthetic", "version": 1,
            "name": "Планёрка команды", "purpose": "Решения и следующие шаги",
            "sections": ["summary", "action_items"], "output_language": "ru", "detail_level": "standard",
        }],
    }
