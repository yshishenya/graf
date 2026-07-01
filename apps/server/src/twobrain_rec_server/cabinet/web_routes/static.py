from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from twobrain_rec_server.cabinet.templates import (
    cabinet_static_dir,
)

router = APIRouter(tags=["cabinet-web"])


@router.get("/favicon.ico", include_in_schema=False)
async def browser_favicon() -> FileResponse:
    return FileResponse(
        f"{cabinet_static_dir()}/favicon.ico",
        media_type="image/x-icon",
    )


@router.get("/apple-touch-icon.png", include_in_schema=False)
@router.get("/apple-touch-icon-precomposed.png", include_in_schema=False)
async def browser_apple_touch_icon() -> FileResponse:
    return FileResponse(
        f"{cabinet_static_dir()}/apple-touch-icon.png",
        media_type="image/png",
    )
