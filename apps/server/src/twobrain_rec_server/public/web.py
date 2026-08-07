from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from twobrain_rec_server.public.templates import public_template_response

router = APIRouter(tags=["public-web"])


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def public_landing_page(request: Request) -> HTMLResponse:
    return public_template_response(
        request,
        "public/landing.html",
        page_title="GRAF — запись встреч и готовые итоги",
        analytics_path="/",
        start_url="/login?next=/meetings",
        download_url="/download",
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
