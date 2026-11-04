import asyncio
from urllib.parse import parse_qs, urlsplit

import pytest
from starlette.requests import Request

from twobrain_rec_server.api.problems import ProblemDetail, problem_exception_handler


def _request(
    path: str,
    *,
    accept: str | None = "text/html",
    method: str = "GET",
) -> Request:
    headers = [(b"host", b"rec.2brain.pro")]
    if accept is not None:
        headers.append((b"accept", accept.encode()))
    return Request(
        {
            "type": "http",
            "method": method,
            "scheme": "https",
            "server": ("rec.2brain.pro", 443),
            "path": path.split("?", 1)[0],
            "raw_path": path.encode(),
            "query_string": path.partition("?")[2].encode(),
            "headers": headers,
        }
    )


@pytest.mark.parametrize(
    "path",
    (
        "/settings",
        "/settings/account",
        "/desktop/settings",
        "/desktop/settings/account",
        "/account",
        "/desktop/account",
        "/account/fair-use",
        "/desktop/account/fair-use",
        "/billing",
        "/billing/checkout",
        "/referrals",
    ),
)
def test_html_cabinet_auth_failures_redirect_to_login(path: str) -> None:
    response = asyncio.run(
        problem_exception_handler(
            _request(path),
            ProblemDetail(
                status=401,
                code="legacy_header_auth_disabled",
                title="Legacy header authentication is disabled",
            ),
        )
    )

    assert response.status_code == 303
    location = response.headers["location"]
    query = parse_qs(urlsplit(location).query)
    assert urlsplit(location).path == "/login"
    assert query["next"] == [path]
    assert query["error"] == ["legacy_header_auth_disabled"]


def test_html_cabinet_auth_failure_preserves_safe_return_query() -> None:
    response = asyncio.run(
        problem_exception_handler(
            _request("/billing/checkout?result=pending"),
            ProblemDetail(status=401, code="auth_session_expired", title="Session expired"),
        )
    )

    query = parse_qs(urlsplit(response.headers["location"]).query)
    assert query["next"] == ["/billing/checkout?result=pending"]


def test_html_cabinet_auth_failure_defaults_to_login_without_accept_header() -> None:
    response = asyncio.run(
        problem_exception_handler(
            _request("/settings", accept=None),
            ProblemDetail(status=401, code="auth_required", title="Auth required"),
        )
    )

    assert response.status_code == 303
    assert parse_qs(urlsplit(response.headers["location"]).query)["next"] == ["/settings"]


def test_non_html_api_auth_failure_stays_problem_json() -> None:
    response = asyncio.run(
        problem_exception_handler(
            _request("/api/v1/billing", accept="application/json"),
            ProblemDetail(status=401, code="legacy_header_auth_disabled", title="Auth required"),
        )
    )

    assert response.status_code == 401
    assert response.media_type == "application/problem+json"


def test_settings_mutation_auth_failure_stays_problem_json() -> None:
    response = asyncio.run(
        problem_exception_handler(
            _request("/settings/account/profile", accept="*/*", method="POST"),
            ProblemDetail(status=403, code="csrf_invalid", title="CSRF validation failed"),
        )
    )

    assert response.status_code == 403
    assert response.media_type == "application/problem+json"


def test_meetings_auth_failure_contract_is_unchanged() -> None:
    response = asyncio.run(
        problem_exception_handler(
            _request("/meetings", accept="*/*"),
            ProblemDetail(status=401, code="auth_session_expired", title="Session expired"),
        )
    )

    assert response.status_code == 401
    assert response.media_type == "application/problem+json"


@pytest.mark.parametrize("method", ["GET", "HEAD"])
@pytest.mark.parametrize("accept", ["text/html", "*/*", None])
def test_addressed_shared_reader_auth_failure_opens_login(method, accept) -> None:
    path = "/shared-meetings/20000000-0000-0000-0000-000000000001?workspace_id=20000000-0000-0000-0000-000000000002"
    response = asyncio.run(problem_exception_handler(
        _request(path, method=method, accept=accept),
        ProblemDetail(status=401, code="auth_session_expired", title="Session expired"),
    ))
    assert response.status_code == 303
    target = urlsplit(response.headers["location"])
    assert target.path == "/login"
    assert parse_qs(target.query)["next"] == [path]


@pytest.mark.parametrize("path,method,accept", [
    ("/shared-meetings/id", "POST", "text/html"),
    ("/shared-meetings/id", "PATCH", "text/html"),
    ("/shared-meetings/id", "DELETE", "text/html"),
    ("/shared-meetings/id", "GET", "application/json"),
    ("/api/v1/cabinet/shared-meetings/id/playback", "GET", "text/html"),
    ("/shared-meetings-evil/id", "GET", "text/html"),
])
def test_shared_reader_auth_handoff_does_not_change_api_or_mutation(path, method, accept) -> None:
    response = asyncio.run(problem_exception_handler(
        _request(path, method=method, accept=accept),
        ProblemDetail(status=401, code="auth_required", title="Auth required"),
    ))
    assert response.status_code == 401
    assert response.media_type == "application/problem+json"
