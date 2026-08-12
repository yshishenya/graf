from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from fastapi import Request
from jinja2 import Environment
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles

from twobrain_rec_server.cabinet.templates import CABINET_STATIC_URL, cabinet_static_asset_url
from twobrain_rec_server.config import Settings
from twobrain_rec_server.public.analytics import build_public_analytics_context
from twobrain_rec_server.templates import (
    html_response,
    package_path,
    render_template_from,
    template_environment,
)

PUBLIC_STATIC_URL = "/static/public"
DEFAULT_PUBLIC_BASE_URL = "https://rec.2brain.pro"
PUBLIC_HTML_HEADERS = {
    "Cache-Control": "private, no-store",
    "Content-Security-Policy": "frame-ancestors 'none'; base-uri 'self'; object-src 'none'",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


def public_template_dir() -> str:
    return package_path("twobrain_rec_server.public", "templates")


def public_static_dir() -> str:
    return package_path("twobrain_rec_server.public", "static", "public")


@lru_cache(maxsize=32)
def public_static_asset_url(filename: str) -> str:
    path = Path(public_static_dir(), filename)
    version = sha256(path.read_bytes()).hexdigest()[:12]
    return f"{PUBLIC_STATIC_URL}/{filename}?v={version}"


class VersionedPublicStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: dict[str, Any]):
        response = await super().get_response(path, scope)
        version = parse_qs(scope.get("query_string", b"").decode("ascii", "ignore")).get("v", [None])[0]
        try:
            expected = public_static_asset_url(path).rsplit("?v=", 1)[1]
        except (FileNotFoundError, IndexError):
            expected = None
        response.headers["Cache-Control"] = (
            "public, max-age=31536000, immutable"
            if response.status_code < 400 and version == expected
            else "no-cache"
        )
        return response


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
    public_base_url = str(settings.public_base_url or DEFAULT_PUBLIC_BASE_URL).rstrip("/")
    canonical_url = f"{public_base_url}{analytics_path}"
    context.setdefault("canonical_url", canonical_url)
    context.setdefault("social_title", context.get("page_title", "GRAF"))
    context.setdefault("social_description", "GRAF записывает встречи и превращает разговор в расшифровку, решения и следующие действия.")
    response = html_response(
        render_template(template_name, request=request, **context),
        status_code=status_code,
    )
    response.headers.update(PUBLIC_HTML_HEADERS)
    return response
