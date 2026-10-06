from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import pytest


@pytest.mark.parametrize("accept", [None, "*/*", "text/html"])
def test_browser_invitation_replay_requires_independent_login(client, accept: str | None) -> None:
    headers = {} if accept is None else {"Accept": accept}

    response = client.post(
        "/share-invitations/continue/magic",
        params={"workspace_id": "20000000-0000-0000-0000-000000000001"},
        headers=headers,
        data={
            "state": "synthetic-continuation-state",
            "magic_csrf": "synthetic-magic-csrf-token",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    location = urlsplit(response.headers["location"])
    assert location.scheme == location.netloc == ""
    assert location.path == "/login"
    assert parse_qs(location.query) == {
        "next": ["/meetings"],
        "error": ["independent_login_required"],
    }
    assert "set-cookie" not in response.headers
    for secret in (
        "synthetic-continuation-state",
        "synthetic-magic-csrf-token",
        "synthetic-share-token",
        "meeting-secret",
    ):
        assert secret not in response.text
        assert secret not in response.headers["location"]


def test_explicit_json_invitation_errors_keep_problem_details(client) -> None:
    response = client.post(
        "/share-invitations/continue/magic",
        params={"workspace_id": "20000000-0000-0000-0000-000000000001"},
        headers={"Accept": "application/json"},
        data={
            "state": "synthetic-continuation-state",
            "magic_csrf": "synthetic-magic-csrf-token",
        },
        follow_redirects=False,
    )

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "independent_login_required"
    assert "set-cookie" not in response.headers
    assert "location" not in response.headers
    assert "synthetic-continuation-state" not in response.text
    assert "synthetic-magic-csrf-token" not in response.text
    assert "Приглашение недоступно" not in response.text


@pytest.mark.parametrize("accept", [None, "*/*", "text/html"])
def test_browser_invitation_validation_errors_are_html(client, accept: str | None) -> None:
    headers = {} if accept is None else {"Accept": accept}

    response = client.post(
        "/share-invitations/continue/magic",
        headers=headers,
        data={},
        follow_redirects=False,
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "private, no-store"
    assert "Приглашение недоступно" in response.text
    assert '"detail"' not in response.text


def test_explicit_html_navigation_uses_existing_login_flow(client) -> None:
    response = client.get(
        "/meetings",
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login?")
    assert "next=%2Fmeetings" in response.headers["location"]
