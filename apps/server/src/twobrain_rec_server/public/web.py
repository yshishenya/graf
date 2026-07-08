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
        page_title="GRAF - встречи записываются сами",
        analytics_path="/",
        start_url="/login?next=/meetings",
        download_url="/download",
    )


@router.get("/download", response_class=HTMLResponse, include_in_schema=False)
async def public_download_page(request: Request) -> HTMLResponse:
    return public_template_response(
        request,
        "public/download.html",
        page_title="Скачать GRAF",
        analytics_path="/download",
        start_url="/login?next=/meetings",
    )
