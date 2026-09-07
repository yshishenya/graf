"""F252 synthetic UI using production templates, assets and time middleware.

uv run uvicorn tests.fixtures.user_time_ui_harness:app --host 127.0.0.1 --port 8872
"""

from datetime import UTC, datetime, timedelta

from starlette.responses import JSONResponse, RedirectResponse

from tests.fixtures import calendar_visual_ui_harness as calendar_harness
from tests.fixtures.cabinet_audit_ui_harness import app
from twobrain_rec_server.cabinet.user_time import (
    apply_user_time_preference,
    user_time_middleware,
    valid_timezone_choice,
)


async def _synthetic_user_time(request, call_next):
    async def render(_):
        # Synthetic local-only session. Actual authentication/persistence is covered in integration tests.
        preferred = request.cookies.get("synthetic_timezone")
        apply_user_time_preference(
            user_id="00000000-0000-4000-8000-000000000252",
            session_id="00000000-0000-4000-8000-000000000253",
            timezone=preferred,
        )
        if request.method == "POST" and request.url.path == "/settings/account/preferences":
            form = await request.form()
            zone = str(form.get("timezone") or "")
            if not valid_timezone_choice(zone):
                return JSONResponse({"title": "Выберите часовой пояс из списка"}, status_code=422)
            response = RedirectResponse("/settings/account?preferences=saved", status_code=303)
            response.set_cookie("synthetic_timezone", zone, httponly=True, samesite="lax")
            return response
        return await call_next(request)

    return await user_time_middleware(request, render)


app.middleware("http")(_synthetic_user_time)
_original_item = calendar_harness._ready_item


def _time_item(index=0):
    item = _original_item(index)
    item.started_at = datetime(2026, 9, 5, 21, 30, tzinfo=UTC) - timedelta(hours=index)
    item.ended_at = item.started_at + timedelta(seconds=item.duration_seconds)
    item.updated_at = item.started_at
    return item


calendar_harness._ready_item = _time_item
