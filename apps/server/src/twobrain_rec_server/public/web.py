from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from twobrain_rec_server.public.templates import public_template_response

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
        page_title="Политика конфиденциальности GRAF",
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
        page_title="Условия публичного сайта GRAF",
    )


@router.get("/analytics-consent", response_class=HTMLResponse, include_in_schema=False)
async def public_analytics_consent_page(request: Request) -> HTMLResponse:
    return public_template_response(
        request,
        "public/analytics_consent.html",
        page_title="Согласие на аналитику GRAF",
    )
