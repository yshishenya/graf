from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from twobrain_rec_server.config import Settings
from twobrain_rec_server.public.templates import DEFAULT_PUBLIC_BASE_URL, public_template_response

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
async def public_landing_page(request: Request) -> HTMLResponse:
    autorecord_apps = landing_autorecord_apps()
    row_split = (len(autorecord_apps) + 1) // 2
    return public_template_response(
        request,
        "public/landing.html",
        page_title="GRAF — запись встреч и готовые итоги",
        analytics_path="/",
        start_url="/login?next=/meetings",
        download_url="/download",
        autorecord_app_count=len(autorecord_apps),
        autorecord_app_rows=(autorecord_apps[:row_split], autorecord_apps[row_split:]),
        autorecord_apps=autorecord_apps,
    )


@router.get("/download", response_class=HTMLResponse, include_in_schema=False)
async def public_download_page(request: Request) -> HTMLResponse:
    return public_template_response(
        request,
        "public/download.html",
        page_title="Скачать GRAF для macOS",
        analytics_path="/download",
        start_url="/login?next=/meetings",
    )


@router.get("/privacy", response_class=HTMLResponse, include_in_schema=False)
async def public_privacy_page(request: Request) -> HTMLResponse:
    return public_template_response(
        request,
        "public/privacy.html",
        page_title="Политика обработки персональных данных GRAF",
    )


@router.get("/cookies", response_class=HTMLResponse, include_in_schema=False)
async def public_cookies_page(request: Request) -> HTMLResponse:
    return public_template_response(
        request,
        "public/cookies.html",
        page_title="Политика cookies GRAF",
    )


@router.get("/terms", response_class=HTMLResponse, include_in_schema=False)
async def public_terms_page(request: Request) -> HTMLResponse:
    return public_template_response(
        request,
        "public/terms.html",
        page_title="Условия использования GRAF",
    )


@router.get("/offer", response_class=HTMLResponse, include_in_schema=False)
async def public_offer_page(request: Request) -> HTMLResponse:
    return public_template_response(
        request,
        "public/offer.html",
        page_title="Условия оплаты и возврата GRAF",
    )


@router.get("/analytics-consent", response_class=HTMLResponse, include_in_schema=False)
async def public_analytics_consent_page(request: Request) -> HTMLResponse:
    return public_template_response(
        request,
        "public/analytics_consent.html",
        page_title="Согласие на аналитику GRAF",
    )


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
    locations = ("/", "/download", "/privacy", "/cookies", "/terms", "/analytics-consent")
    urls = "".join(f"<url><loc>{base_url}{path}</loc></url>" for path in locations)
    return Response(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',
        media_type="application/xml",
    )
