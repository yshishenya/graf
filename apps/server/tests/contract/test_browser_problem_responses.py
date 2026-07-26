from __future__ import annotations

import pytest


@pytest.mark.parametrize("accept", [None, "*/*", "text/html"])
def test_browser_invitation_replay_is_html_for_browser_accepts(client, accept: str | None) -> None:
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

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "private, no-store"
    assert "Приглашение недоступно" in response.text
    assert "Ссылка уже использована, отозвана или срок её действия истёк." in response.text
    for secret in (
        "synthetic-continuation-state",
        "synthetic-magic-csrf-token",
        "synthetic-share-token",
        "meeting-secret",
    ):
        assert secret not in response.text


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

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "invitation_not_found"
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
    assert "detail" not in response.text


def test_explicit_html_navigation_uses_existing_login_flow(client) -> None:
    response = client.get(
        "/meetings",
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login?")
    assert "next=%2Fmeetings" in response.headers["location"]
