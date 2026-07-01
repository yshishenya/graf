from __future__ import annotations

from fastapi import APIRouter

from twobrain_rec_server.cabinet.web_routes import (
    auth,
    browser,
    calendar,
    deletion,
    desktop,
    static,
)

router = APIRouter(tags=["cabinet-web"])
router.include_router(static.router)
router.include_router(auth.router)
router.include_router(browser.router)
router.include_router(calendar.router)
router.include_router(deletion.router)
router.include_router(desktop.router)
