from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from typing import Any

from fastapi import Request
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup
from starlette.responses import HTMLResponse

CABINET_STATIC_URL = "/static/cabinet"

TRUSTED_HTML_SOURCES = frozenset(
    {
        "auth.shell",
        "cabinet.shell",
        "meeting_list.delete_dialog",
        "meeting_list.region",
        "meeting_list.rows",
        "meeting_detail.access_chip",
        "meeting_detail.access_summary",
        "meeting_detail.activity",
        "meeting_detail.artifacts",
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


def _cabinet_package_root() -> Any:
    return files("twobrain_rec_server.cabinet")


def cabinet_template_dir() -> str:
    return str(_cabinet_package_root().joinpath("templates"))


def cabinet_static_dir() -> str:
    return str(_cabinet_package_root().joinpath("static", "cabinet"))


@lru_cache(maxsize=1)
def get_cabinet_templates() -> Environment:
    return Environment(
        loader=FileSystemLoader(cabinet_template_dir()),
        autoescape=select_autoescape(("html", "xml"), default_for_string=True),
        undefined=StrictUndefined,
    )


def render_template(template_name: str, **context: Any) -> str:
    template = get_cabinet_templates().get_template(template_name)
    return template.render(cabinet_static_url=CABINET_STATIC_URL, **context)


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
    response = HTMLResponse(html, status_code=status_code)
    if hx_request:
        response.headers["Vary"] = "HX-Request"
    return response
