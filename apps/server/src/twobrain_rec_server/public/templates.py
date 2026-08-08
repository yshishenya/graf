from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any

from fastapi import Request
from jinja2 import Environment
from starlette.responses import HTMLResponse

from twobrain_rec_server.cabinet.templates import CABINET_STATIC_URL, cabinet_static_asset_url
from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.browser_context import build_browser_provider_context
from twobrain_rec_server.public.analytics import build_public_analytics_context
from twobrain_rec_server.templates import (
    html_response,
    package_path,
    render_template_from,
    template_environment,
)

PUBLIC_STATIC_URL = "/static/public"


def public_template_dir() -> str:
    return package_path("twobrain_rec_server.public", "templates")


def public_static_dir() -> str:
    return package_path("twobrain_rec_server.public", "static", "public")


@lru_cache(maxsize=32)
def public_static_asset_url(filename: str) -> str:
    path = Path(public_static_dir(), filename)
    version = sha256(path.read_bytes()).hexdigest()[:12]
    return f"{PUBLIC_STATIC_URL}/{filename}?v={version}"


def get_public_templates() -> Environment:
    return template_environment(public_template_dir())


def render_template(template_name: str, **context: Any) -> str:
    return render_template_from(
        get_public_templates(),
        template_name,
        cabinet_static_asset_url=cabinet_static_asset_url,
        cabinet_static_url=CABINET_STATIC_URL,
        public_static_asset_url=public_static_asset_url,
        public_static_url=PUBLIC_STATIC_URL,
        **context,
    )


def public_template_response(
    request: Request,
    template_name: str,
    *,
    status_code: int = 200,
    **context: Any,
) -> HTMLResponse:
    settings = getattr(request.app.state, "settings", Settings())
    analytics_path = str(context.pop("analytics_path", request.url.path))
    context.setdefault(
        "public_analytics",
        build_public_analytics_context(
            settings,
            analytics_path,
            request.query_params,
            referrer=request.headers.get("referer"),
        ),
    )
    public_page_class = {
        "/": "public_landing",
        "/download": "public_download",
        "/privacy": "legal",
        "/cookies": "legal",
        "/terms": "legal",
        "/analytics-consent": "legal",
    }.get(analytics_path, "future_browser_page")
    context.setdefault("product_analytics_provider", build_browser_provider_context(settings, public_page_class))
    return html_response(
        render_template(template_name, request=request, **context),
        status_code=status_code,
    )
