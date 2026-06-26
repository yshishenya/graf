from uuid import uuid4

import pytest
from fastapi.routing import APIRoute

from twobrain_rec_server.api.cabinet import router as cabinet_api_router
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.csrf import issue_csrf_token, require_csrf_token, verify_csrf_token


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
