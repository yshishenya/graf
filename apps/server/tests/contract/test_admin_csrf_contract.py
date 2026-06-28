from __future__ import annotations

from fastapi.routing import APIRoute

from twobrain_rec_server.admin.web import router as admin_web_router
from twobrain_rec_server.api.admin import router as admin_api_router


def test_unsafe_admin_api_routes_require_web_csrf_dependency() -> None:
    assert _unsafe_routes_missing_csrf(admin_api_router.routes) == []


def test_unsafe_admin_web_routes_require_web_csrf_dependency() -> None:
    assert _unsafe_routes_missing_csrf(admin_web_router.routes) == []


def _unsafe_routes_missing_csrf(routes: list[object]) -> list[str]:
    missing: list[str] = []
    for route in routes:
        if not isinstance(route, APIRoute):
            continue
        if not (route.methods or set()) & {"POST", "PUT", "PATCH", "DELETE"}:
            continue
        dependency_names = {
            getattr(dependency.call, "__name__", "")
            for dependency in route.dependant.dependencies
            if dependency.call is not None
        }
        if "require_web_csrf" not in dependency_names:
            missing.append(f"{sorted(route.methods or set())} {route.path}")
    return missing
