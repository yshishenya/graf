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
from twobrain_rec_server.product_analytics.acquisition import record_visit_attribution_safely
from twobrain_rec_server.public.analytics import (
    apply_public_visit_attribution_cookie,
    build_public_analytics_context,
    read_public_visit_attribution,
    record_public_page_visit,
)
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


def public_static_asset_url(filename: str) -> str:
    path = Path(public_static_dir(), filename)
    stat = path.stat()
    return _public_static_asset_url(
        filename,
        path,
        (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns),
    )


@lru_cache(maxsize=32)
def _public_static_asset_url(
    filename: str, path: Path, identity: tuple[int, int, int, int, int]
) -> str:
    version = sha256(path.read_bytes()).hexdigest()[:12]
    return f"{PUBLIC_STATIC_URL}/{filename}?v={version}"


class VersionedPublicStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: dict[str, Any]):
        response = await super().get_response(path, scope)
        version = parse_qs(scope.get("query_string", b"").decode("ascii", "ignore")).get(
            "v", [None]
        )[0]
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


def public_analytics_page_context(
    request: Request,
    analytics_path: str,
) -> dict[str, Any]:
    """Build the consent-based measurement context of one public route (FR-027).

    A route outside :data:`PUBLIC_ANALYTICS_SURFACES` gets a disabled context, so
    the caller may use this builder for a page it also serves in another role.
    """
    settings = getattr(request.app.state, "settings", Settings())
    return build_public_analytics_context(
        settings,
        analytics_path,
        request.query_params,
        referrer=request.headers.get("referer"),
    )


async def record_public_page_response(
    request: Request,
    response: HTMLResponse,
    *,
    db: Any = None,
) -> HTMLResponse:
    """Keep the visit of an already rendered public page and count it (FR-009).

    The three rules of :func:`public_page_response` hold here too: the page is
    already rendered, so the campaign cookie and the anonymous count can never
    withhold or break the response.
    """
    attribution = read_public_visit_attribution(request)
    apply_public_visit_attribution_cookie(response, request, attribution=attribution)
    # Level 2 keeps one opaque, campaign-bearing visit record. The write is
    # best-effort and never delays or breaks the already-rendered public page.
    if attribution.get("attribution_status") in {"saved", "current"}:
        # Public page rendering owns the request transaction. Keep the durable
        # visit write inside it so auth can resolve the exact reference, but do
        # not commit here and unexpectedly close the caller's transaction.
        settings = getattr(getattr(request, "app", None), "state", None)
        settings = getattr(settings, "settings", None)
        await record_visit_attribution_safely(
            db,
            attribution,
            commit=False,
            settings=settings,
        )
    # Level 1 carries no personal data and is required on every public page; this
    # switch exists so an operator can stop that one counter when its basis falls
    # away (FR-048) without touching the optional levels, which are off by default.
    settings = getattr(request.app.state, "settings", None)
    braked = settings is not None and not settings.product_analytics_anonymous_aggregate_enabled
    if not braked:
        await record_public_page_visit(db, request, attribution=attribution)
    return response


def public_template_response(
    request: Request,
    template_name: str,
    *,
    status_code: int = 200,
    **context: Any,
) -> HTMLResponse:
    analytics_path = str(context.pop("analytics_path", request.url.path))
    context.setdefault("public_analytics", public_analytics_page_context(request, analytics_path))
    settings = getattr(request.app.state, "settings", Settings())
    public_base_url = str(settings.public_base_url or DEFAULT_PUBLIC_BASE_URL).rstrip("/")
    canonical_url = f"{public_base_url}{analytics_path}"
    context.setdefault("canonical_url", canonical_url)
    context.setdefault("social_title", context.get("page_title", "ГРАФ"))
    context.setdefault(
        "social_description",
        "ГРАФ записывает встречи и превращает разговор в расшифровку, решения и следующие действия.",
    )
    response = html_response(
        render_template(template_name, request=request, **context),
        status_code=status_code,
    )
    response.headers.update(PUBLIC_HTML_HEADERS)
    return response
