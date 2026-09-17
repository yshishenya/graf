"""F243 synthetic account surface, reusing the calendar harness unchanged."""

from fastapi import Request
from fastapi.responses import HTMLResponse

from tests.fixtures.calendar_visual_ui_harness import app
from twobrain_rec_server.cabinet.rendering import render_settings_page
from twobrain_rec_server.cabinet.view_models import AccountProfileView, AccountSettingsSurface


@app.get("/settings", response_class=HTMLResponse)
@app.get("/desktop/settings", response_class=HTMLResponse)
@app.get("/settings/account", response_class=HTMLResponse)
@app.get("/desktop/settings/account", response_class=HTMLResponse)
async def account(request: Request) -> HTMLResponse:
    profile = AccountProfileView(
        display_name="Синтетический пользователь",
        locale="en-US",
        theme=request.query_params.get("theme", "system"),
    )
    return HTMLResponse(
        render_settings_page(
            category="account" if request.url.path.endswith("/account") else "overview",
            embedded=request.url.path.startswith("/desktop/"),
            csrf_token="synthetic-csrf",
            profile=profile,
            account_surface=AccountSettingsSurface(profile=profile),
        )
    )
