"""Synthetic, process-local UI harness; persistence is covered by PostgreSQL tests.

Run: uvicorn tests.fixtures.meeting_rename_ui_harness:app --host 127.0.0.1 --port 8873
Open /meetings. /test/{mode} selects normal, error, lost, delayed, forbidden, deleted.
"""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from tests.fixtures.calendar_visual_ui_harness import (
    _meeting_response,
    _profile,
    _theme_review,
    synthetic_silence,
)
from tests.fixtures.calendar_visual_ui_harness import (
    app as calendar_app,
)
from twobrain_rec_server.cabinet.rendering import (
    render_meeting_detail_page,
    render_meeting_list_page,
)

app = FastAPI()
state = {"title": "Синтетическая встреча", "version": 1, "mode": "normal"}
app.mount(
    "/static/cabinet",
    next(
        route.app
        for route in calendar_app.routes
        if getattr(route, "path", "") == "/static/cabinet"
    ),
)
app.get("/synthetic/theme.wav")(synthetic_silence)


@app.get("/test/{mode}")
async def select_mode(mode: str):
    state["mode"] = mode
    return RedirectResponse("/meetings/00000000-0000-4000-8000-000000000240")


@app.get("/meetings")
@app.get("/desktop/meetings")
async def listing(request: Request):
    response = _meeting_response("populated")
    response.items[0].title = state["title"]
    return HTMLResponse(
        render_meeting_list_page(
            response, embedded=request.url.path.startswith("/desktop/"), profile=_profile(request)
        )
    )


@app.get("/meetings/{meeting_id}")
@app.get("/desktop/meetings/{meeting_id}")
async def detail(request: Request, meeting_id: str):
    review = _theme_review()
    review.meeting.title = state["title"]
    review.meeting.title_version = str(state["version"])
    html = render_meeting_detail_page(
        review,
        embedded=request.url.path.startswith("/desktop/"),
        csrf_token="synthetic-csrf",
        profile=_profile(request),
    )
    if request.query_params.get("refresh") == "delayed":
        html = html.replace(
            "</main>",
            """<button hx-get="?refresh=delayed" hx-target="#cabinet-main" hx-select="#cabinet-main">Тест фонового обновления</button><button onmousedown="event.preventDefault()" onclick="document.querySelector('[data-meeting-title-input]').dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', isComposing: true, bubbles: true, cancelable: true}))">Тест IME</button></main>""",
        )
        if request.headers.get("hx-request"):
            await asyncio.sleep(3)
    return HTMLResponse(html)


@app.post("/meetings/{meeting_id}/title")
@app.post("/desktop/meetings/{meeting_id}/title")
async def rename(request: Request, meeting_id: str):
    form = await request.form()
    mode = state["mode"]
    if mode == "error":
        return JSONResponse({"code": "server_error"}, status_code=500)
    if mode in {"forbidden", "deleted"}:
        return JSONResponse({"code": "meeting_not_found"}, status_code=404)
    if form["expected_version"] != str(state["version"]):
        return JSONResponse(
            {
                "code": "meeting_title_conflict",
                "title": state["title"],
                "title_version": str(state["version"]),
                "message": "Название уже изменено. Enter — сохранить своё, Esc — оставить текущее",
            },
            status_code=409,
        )
    state["title"] = str(form["title"]).strip()
    state["version"] += 1
    if mode in {"lost", "delayed"}:
        await asyncio.sleep(17 if mode == "lost" else 3)
    if "application/json" not in request.headers.get("accept", ""):
        return RedirectResponse(request.url.path.removesuffix("/title"), status_code=303)
    return JSONResponse(
        {"meeting_id": meeting_id, "title": state["title"], "title_version": str(state["version"])}
    )
