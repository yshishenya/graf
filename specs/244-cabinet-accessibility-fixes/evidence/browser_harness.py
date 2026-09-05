"""Extend the existing synthetic harness only with a signed-out upload page."""

from fastapi import Request
from fastapi.responses import HTMLResponse

from tests.fixtures.calendar_visual_ui_harness import _meeting_response, _profile, app
from twobrain_rec_server.cabinet.rendering import render_meeting_list_page


@app.get("/f244-unavailable", response_class=HTMLResponse)
async def unavailable(request: Request) -> HTMLResponse:
    return HTMLResponse(
        render_meeting_list_page(
            _meeting_response(),
            embedded=request.query_params.get("embedded") == "true",
            csrf_token=None,
            profile=_profile(request),
        )
    )
