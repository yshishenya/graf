from __future__ import annotations

import asyncio
import json
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.tenant_context import TenantDatabaseContext, apply_tenant_context
from twobrain_rec_server.public.analytics import (
    PUBLIC_ANALYTICS_CAPTURE_ENDPOINT,
    PUBLIC_ANALYTICS_RELAY_MAX_BYTES,
    PublicAnalyticsConsentRequired,
    PublicAnalyticsEventRejected,
    deliver_public_analytics_event,
    normalize_public_analytics_event,
)
from twobrain_rec_server.public.offers import build_public_offer_view
from twobrain_rec_server.public.templates import (
    DEFAULT_PUBLIC_BASE_URL,
    public_template_response,
    record_public_page_response,
)

router = APIRouter(tags=["public-web"])
LANDING_AUTORECORD_PRIORITY = (
    "Zoom",
    "Yandex Telemost",
    "VK Calls",
    "VK Teams",
    "MTS Link",
    "Kontur Talk",
    "TrueConf",
    "SaluteJazz",
    "Microsoft Teams new",
    "Telegram for macOS / Telegram Lite",
    "WhatsApp",
    "FaceTime",
    "Webex",
    "Discord",
    "Slack calls",
)
MEETING_TARGET_REGISTRY = (
    Path(__file__).resolve().parents[1]
    / "db"
    / "migrations"
    / "data"
    / "0030_meeting_target_registry.json"
)
PUBLIC_WEB_CONTEXT_ID = UUID(int=0)


async def get_public_web_db_session(request: Request):
    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        yield None
        return
    async with sessionmaker() as session:
        # Billing catalog is global, but PostgreSQL still requires the ordinary
        # request RLS context before reading it.
        # A zero UUID cannot match any tenant-owned row if this dependency is
        # ever extended with another query.
        try:
            await apply_tenant_context(
                session,
                TenantDatabaseContext(
                    organization_id=PUBLIC_WEB_CONTEXT_ID,
                    workspace_id=PUBLIC_WEB_CONTEXT_ID,
                    user_id=PUBLIC_WEB_CONTEXT_ID,
                ),
            )
        except Exception:
            # Keep public pages renderable when the catalog database is down;
            # the offer builder will then fail closed without paid claims.
            yield None
            return
        yield session


PublicWebDbDependency = Depends(get_public_web_db_session)


@lru_cache(maxsize=1)
def landing_autorecord_apps() -> tuple[str, ...]:
    registry = json.loads(MEETING_TARGET_REGISTRY.read_text(encoding="utf-8"))
    priority = {name: index for index, name in enumerate(LANDING_AUTORECORD_PRIORITY)}
    return tuple(
        sorted(
            (
                target["displayName"]
                for target in registry["targets"]
                if target["platform"] == "macos" and target["mode"] == "prompt_enabled"
            ),
            key=lambda name: (priority.get(name, len(priority)), name.casefold()),
        )
    )


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def public_landing_page(
    request: Request,
    db: AsyncSession | None = PublicWebDbDependency,
) -> HTMLResponse:
    settings = getattr(request.app.state, "settings", Settings())
    public_offer = await build_public_offer_view(db, settings)
    autorecord_apps = landing_autorecord_apps()
    row_split = (len(autorecord_apps) + 1) // 2
    return await public_page_response(
        request,
        "public/landing.html",
        db=db,
        page_title="ГРАФ — запись и расшифровка звонков в любом приложении",
        analytics_path="/",
        start_url="/login?next=/meetings",
        download_url="/download",
        social_title="ГРАФ — запись звонков в любом приложении",
        social_description="Запишите разговор без бота и получите расшифровку по спикерам, итоги и следующие действия.",
        public_offer=public_offer,
        autorecord_app_count=len(autorecord_apps),
        autorecord_app_rows=(autorecord_apps[:row_split], autorecord_apps[row_split:]),
        autorecord_apps=autorecord_apps,
    )


@router.get("/download", response_class=HTMLResponse, include_in_schema=False)
async def public_download_page(
    request: Request,
    db: AsyncSession | None = PublicWebDbDependency,
) -> HTMLResponse:
    return await public_page_response(
        request,
        "public/download.html",
        db=db,
        page_title="Скачать ГРАФ для macOS",
        analytics_path="/download",
        start_url="/login?next=/meetings",
    )


@router.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
async def public_privacy_page(
    request: Request,
    db: AsyncSession | None = PublicWebDbDependency,
) -> HTMLResponse:
    return await public_page_response(
        request,
        "public/privacy.html",
        db=db,
        page_title="Политика обработки персональных данных ГРАФ",
    )


@router.get("/cookies", response_class=HTMLResponse, include_in_schema=False)
async def public_cookies_page(
    request: Request,
    db: AsyncSession | None = PublicWebDbDependency,
) -> HTMLResponse:
    return await public_page_response(
        request,
        "public/cookies.html",
        db=db,
        page_title="Политика cookies ГРАФ",
    )


@router.get("/terms", response_class=HTMLResponse, include_in_schema=False)
async def public_terms_page(
    request: Request,
    db: AsyncSession | None = PublicWebDbDependency,
) -> HTMLResponse:
    return await public_page_response(
        request,
        "public/terms.html",
        db=db,
        page_title="Условия использования ГРАФ",
    )


@router.get("/offer", response_class=HTMLResponse, include_in_schema=False)
async def public_offer_page(
    request: Request,
    db: AsyncSession | None = PublicWebDbDependency,
) -> HTMLResponse:
    settings = getattr(request.app.state, "settings", Settings())
    return await public_page_response(
        request,
        "public/offer.html",
        db=db,
        page_title="Условия оплаты и возврата ГРАФ",
        public_offer=await build_public_offer_view(db, settings),
    )


@router.get("/analytics-consent", response_class=HTMLResponse, include_in_schema=False)
async def public_analytics_consent_page(
    request: Request,
    db: AsyncSession | None = PublicWebDbDependency,
) -> HTMLResponse:
    return await public_page_response(
        request,
        "public/analytics_consent.html",
        db=db,
        page_title="Как ГРАФ использует аналитику",
    )


async def public_page_response(
    request: Request,
    template_name: str,
    *,
    db: AsyncSession | None = None,
    **context: Any,
) -> HTMLResponse:
    """Render one public page, count the visit and keep its campaign labels.

    Three rules meet here and none of them may break the other two (FR-009,
    FR-014, FR-058):

    * the page is rendered before anything is measured, so measurement can never
      block the response;
    * the visit is counted by one synchronous bucket write that does not raise
      and does not touch the analytics stack, so the page and the anonymous count
      survive an unreachable counter;
    * the campaign labels of the visit are stored in a session cookie, so they
      survive the move between public pages and are readable by the registration
      path through :func:`read_public_visit_attribution`.
    """
    response = public_template_response(request, template_name, **context)
    return await record_public_page_response(request, response, db=db)


@router.post(PUBLIC_ANALYTICS_CAPTURE_ENDPOINT, include_in_schema=False)
async def public_analytics_event(request: Request) -> JSONResponse:
    """Relay one consented public page event to PostHog (FR-004, FR-006, FR-058).

    The browser gate refuses to send after a refusal; this route repeats the same
    decision on the server, because a gate that lives only in the browser can be
    bypassed. The response never depends on the provider: an unreachable or
    unconfigured counter is reported in the body and the page is unaffected.
    """
    settings = getattr(request.app.state, "settings", Settings())
    if not settings.public_analytics_enabled:
        return JSONResponse(
            {"accepted": False, "reason": "public_measurement_disabled"},
            status_code=403,
        )
    if not _same_origin_request(request):
        return JSONResponse({"accepted": False, "reason": "cross_origin"}, status_code=403)
    body = await request.body()
    if len(body) > PUBLIC_ANALYTICS_RELAY_MAX_BYTES:
        return JSONResponse({"accepted": False, "reason": "payload_too_large"}, status_code=413)
    try:
        payload = json.loads(body or b"{}")
    except (TypeError, ValueError):
        return JSONResponse({"accepted": False, "reason": "invalid_json"}, status_code=400)
    try:
        event = normalize_public_analytics_event(payload)
    except PublicAnalyticsConsentRequired:
        return JSONResponse(
            {"accepted": False, "reason": "optional_consent_not_granted"},
            status_code=403,
        )
    except PublicAnalyticsEventRejected as exc:
        return JSONResponse({"accepted": False, "reason": str(exc)}, status_code=400)
    delivery = await asyncio.to_thread(deliver_public_analytics_event, settings, event)
    return JSONResponse({"accepted": True, "delivery": delivery}, status_code=202)


def _same_origin_request(request: Request) -> bool:
    """Refuse a relay call made by a page of another site."""
    origin = request.headers.get("origin")
    if not origin:
        return True
    origin_host = urlparse(origin).netloc.lower()
    if not origin_host:
        return False
    request_host = urlparse(str(request.base_url)).netloc.lower()
    return bool(request_host) and origin_host == request_host


def _public_base_url(request: Request) -> str:
    settings = getattr(request.app.state, "settings", Settings())
    return str(settings.public_base_url or DEFAULT_PUBLIC_BASE_URL).rstrip("/")


@router.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def public_robots(request: Request) -> PlainTextResponse:
    base_url = _public_base_url(request)
    return PlainTextResponse(f"User-agent: *\nAllow: /\nSitemap: {base_url}/sitemap.xml\n")


@router.get("/sitemap.xml", include_in_schema=False)
async def public_sitemap(request: Request) -> Response:
    base_url = _public_base_url(request)
    locations = ("/", "/download", "/privacy", "/cookies", "/terms", "/offer", "/analytics-consent")
    urls = "".join(f"<url><loc>{base_url}{path}</loc></url>" for path in locations)
    return Response(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',
        media_type="application/xml",
    )
