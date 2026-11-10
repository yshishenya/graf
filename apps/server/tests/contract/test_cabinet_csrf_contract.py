from uuid import uuid4

import pytest
from fastapi.routing import APIRoute

from twobrain_rec_server.api.cabinet import router as cabinet_api_router
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.summary_sharing import router as summary_sharing_router
from twobrain_rec_server.api.support_incidents import router as support_incidents_router
from twobrain_rec_server.auth.csrf import issue_csrf_token, require_csrf_token, verify_csrf_token
from twobrain_rec_server.auth.dependencies import get_tenant_scope, require_web_csrf


def test_csrf_token_is_bound_to_session_and_secret() -> None:
    session_id = uuid4()
    token = issue_csrf_token(session_id=session_id, secret="server-secret")

    assert verify_csrf_token(token, session_id=session_id, secret="server-secret")
    assert not verify_csrf_token(token, session_id=uuid4(), secret="server-secret")
    assert not verify_csrf_token(token, session_id=session_id, secret="other-secret")


def test_csrf_missing_or_stale_token_fails_closed() -> None:
    session_id = uuid4()

    with pytest.raises(ProblemDetail) as missing:
        require_csrf_token(None, session_id=session_id, secret="server-secret")
    assert missing.value.status == 403
    assert missing.value.code == "csrf_token_missing"

    with pytest.raises(ProblemDetail) as invalid:
        require_csrf_token("stale", session_id=session_id, secret="server-secret")
    assert invalid.value.status == 403
    assert invalid.value.code == "csrf_token_invalid"


def test_unsafe_cabinet_api_routes_require_web_csrf_dependency() -> None:
    missing = []
    for route in cabinet_api_router.routes:
        if not isinstance(route, APIRoute):
            continue
        if not (route.methods & {"POST", "PUT", "PATCH", "DELETE"}):
            continue
        dependency_names = {getattr(dependency.call, "__name__", "") for dependency in route.dependant.dependencies}
        if "require_web_csrf" not in dependency_names:
            missing.append(f"{','.join(sorted(route.methods))} {route.path}")

    assert missing == []


def test_support_incident_mutations_require_web_csrf_dependency() -> None:
    missing = []
    for route in support_incidents_router.routes:
        if not isinstance(route, APIRoute):
            continue
        if not (route.methods & {"POST", "PUT", "PATCH", "DELETE"}):
            continue
        dependency_names = {getattr(dependency.call, "__name__", "") for dependency in route.dependant.dependencies}
        if "require_web_csrf" not in dependency_names:
            missing.append(f"{','.join(sorted(route.methods))} {route.path}")

    assert missing == []


def test_general_access_routes_require_tenant_and_protect_writes_with_csrf() -> None:
    routes = {
        method: route
        for route in summary_sharing_router.routes
        if isinstance(route, APIRoute)
        and route.path == "/api/v1/cabinet/meetings/{meeting_id}/sharing/general-access"
        for method in route.methods
    }
    assert set(routes) == {"GET", "POST"}
    for route in routes.values():
        assert get_tenant_scope in {dependency.call for dependency in route.dependant.dependencies}
    assert require_web_csrf in {
        dependency.call for dependency in routes["POST"].dependant.dependencies
    }
