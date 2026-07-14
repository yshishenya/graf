from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any

from fastapi import Request
from jinja2 import Environment
from markupsafe import Markup
from starlette.responses import HTMLResponse

from twobrain_rec_server.templates import (
    html_response,
    package_path,
    render_template_from,
    template_environment,
)

CABINET_STATIC_URL = "/static/cabinet"

TRUSTED_HTML_SOURCES = frozenset(
    {
        "auth.shell",
        "cabinet.shell",
        "meeting_list.delete_dialog",
        "meeting_list.manual_upload",
        "meeting_list.region",
        "meeting_list.rows",
        "meeting_list.upcoming_recurring",
        "meeting_detail.access_chip",
        "meeting_detail.access_summary",
        "meeting_detail.activity",
        "meeting_detail.artifacts",
        "meeting_detail.calendar_context",
        "meeting_detail.calendar_context_chooser",
        "meeting_detail.content",
        "meeting_detail.delete_confirmation",
        "meeting_detail.empty_transcript",
        "meeting_detail.governance",
        "meeting_detail.outcomes",
        "meeting_detail.playback",
        "meeting_detail.revision_status",
        "meeting_detail.share_panel",
        "meeting_detail.speaker_lanes",
        "meeting_detail.top_actions",
        "meeting_detail.transcript",
        "deletion_report.activity",
        "deletion_report.band",
        "deletion_report.content",
        "deletion_report.local_purge",
    }
)


def cabinet_template_dir() -> str:
    return package_path("twobrain_rec_server.cabinet", "templates")


def cabinet_static_dir() -> str:
    return package_path("twobrain_rec_server.cabinet", "static", "cabinet")


@lru_cache(maxsize=32)
def cabinet_static_asset_url(filename: str) -> str:
    path = Path(cabinet_static_dir(), filename)
    version = sha256(path.read_bytes()).hexdigest()[:12]
    return f"{CABINET_STATIC_URL}/{filename}?v={version}"


def get_cabinet_templates() -> Environment:
    return template_environment(cabinet_template_dir())


def render_template(template_name: str, **context: Any) -> str:
    return render_template_from(
        get_cabinet_templates(),
        template_name,
        cabinet_static_asset_url=cabinet_static_asset_url,
        cabinet_static_url=CABINET_STATIC_URL,
        **context,
    )


def trusted_component_html(html: str, *, source: str) -> Markup:
    if source not in TRUSTED_HTML_SOURCES:
        raise ValueError(f"Unreviewed cabinet trusted HTML source: {source}")
    return Markup(html)


def render_icon(name: str, *, label: str | None = None) -> str:
    template = get_cabinet_templates().get_template("cabinet/components/icons.html")
    return str(template.module.icon(name, label))


def cabinet_template_response(
    request: Request,
    template_name: str,
    *,
    status_code: int = 200,
    hx_request: bool = False,
    **context: Any,
) -> HTMLResponse:
    html = render_template(template_name, request=request, **context)
    return cabinet_html_response(html, status_code=status_code, hx_request=hx_request)


def cabinet_html_response(
    html: str,
    *,
    status_code: int = 200,
    hx_request: bool = False,
) -> HTMLResponse:
    response = html_response(html, status_code=status_code)
    if hx_request:
        response.headers["Vary"] = "HX-Request"
    return response
