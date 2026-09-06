from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import PERSONAL_WORKSPACE_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.cabinet_access import (
    add_workspace_user,
    auth_headers_for,
    set_meeting_visibility,
)
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.db.models import Meeting


def _info(client, meeting_id):
    response = client.get(f"/api/v1/cabinet/meetings/{meeting_id}", headers=auth_headers())
    assert response.status_code == 200
    return response.json()["meeting"]


def _rename(
    client, meeting_id, title, version, *, desktop=False, headers=None, accept="application/json"
):
    return client.post(
        f"{'/desktop' if desktop else ''}/meetings/{meeting_id}/title",
        headers={**(headers or auth_headers()), "Accept": accept},
        data={"title": title, "expected_version": version},
        follow_redirects=False,
    )


@pytest.mark.parametrize("desktop", [False, True])
def test_rename_persists_and_preserves_identity_and_escaped_rendering(client, desktop):
    seed = seed_cabinet_meetings(client)
    before = _info(client, seed.ready_id)
    title = "План <b>работ</b> & «команда» 😀"
    result = _rename(
        client, seed.ready_id, f"  {title}  ", before["title_version"], desktop=desktop
    )
    assert result.status_code == 200, result.text
    assert result.json()["title"] == title
    after = _info(client, seed.ready_id)
    assert after["title"] == title
    assert after["title_version"] != before["title_version"]
    assert after["started_at"] == before["started_at"]
    assert after["status"] == before["status"]
    html = client.get(
        f"{'/desktop' if desktop else ''}/meetings/{seed.ready_id}", headers=auth_headers()
    ).text
    assert "&lt;b&gt;" in html and "<b>работ</b>" not in html
    assert "data-meeting-title-form" in html
    assert 'data-hx-history="false"' in html
    listed = client.get("/api/v1/cabinet/meetings", headers=auth_headers()).json()
    assert (
        next(x for x in listed["items"] if x["meeting_id"] == str(seed.ready_id))["title"] == title
    )


@pytest.mark.parametrize(
    "title,code",
    [
        ("   ", "meeting_title_empty"),
        ("я" * 501, "meeting_title_too_long"),
        ("https://example.com", "unsafe_meeting_title"),
        ("a\nb", "unsafe_meeting_title"),
        ("a\u0085b", "unsafe_meeting_title"),
        ("/private/document", "unsafe_meeting_title"),
        ("C:\\private\\file", "unsafe_meeting_title"),
    ],
)
def test_invalid_name_is_rejected_without_echo(client, title, code):
    seed = seed_cabinet_meetings(client)
    before = _info(client, seed.ready_id)
    result = _rename(client, seed.ready_id, title, before["title_version"])
    assert result.status_code == 422
    assert result.json()["code"] == code
    assert title not in result.text
    assert _info(client, seed.ready_id)["title"] == before["title"]


def test_unicode_limit_conflict_and_lost_response_retry(client):
    seed = seed_cabinet_meetings(client)
    version = _info(client, seed.ready_id)["title_version"]
    title = "😀" * 500
    first = _rename(client, seed.ready_id, title, version)
    assert first.status_code == 200
    repeat = _rename(client, seed.ready_id, title, version)
    assert repeat.json() == first.json()
    conflict = _rename(client, seed.ready_id, "Второе имя", version)
    assert conflict.status_code == 409
    assert conflict.json()["title"] == title
    assert conflict.json()["title_version"] == first.json()["title_version"]
    assert (
        _rename(client, seed.ready_id, "Второе имя", conflict.json()["title_version"]).status_code
        == 200
    )


@pytest.mark.parametrize("role", ["member", "admin"])
def test_shared_viewers_and_other_workspace_cannot_rename(client, role):
    seed = seed_cabinet_meetings(client)
    add_workspace_user(client, role=role)
    set_meeting_visibility(client, seed.ready_id, "team_visible")
    before = _info(client, seed.ready_id)
    for headers in (
        auth_headers_for(),
        {**auth_headers(), "X-Workspace-Id": str(PERSONAL_WORKSPACE_ID)},
    ):
        result = _rename(
            client, seed.ready_id, "Чужое имя", before["title_version"], headers=headers
        )
        assert result.status_code in {403, 404}
        assert before["title"] not in result.text
    html = client.get(f"/meetings/{seed.ready_id}", headers=auth_headers_for()).text
    assert "data-meeting-title-form" not in html
    assert _info(client, seed.ready_id)["title"] == before["title"]


def test_html_fallback_success_and_validation_preserve_draft(client):
    seed = seed_cabinet_meetings(client)
    version = _info(client, seed.ready_id)["title_version"]
    bad = _rename(client, seed.ready_id, "x" * 501, version, accept="text/html")
    assert bad.status_code == 422
    assert "x" * 501 in bad.text and "не больше 500" in bad.text
    good = _rename(client, seed.ready_id, "Новое имя", version, accept="text/html")
    assert good.status_code == 303
    assert good.headers["location"] == f"/meetings/{seed.ready_id}"


def test_stale_ingest_snapshot_cannot_restore_old_title(client):
    from twobrain_rec_server.ingest.store import load_meeting_record, persist_meeting

    seed = seed_cabinet_meetings(client)

    async def snapshot():
        async with client.app_state["sessionmaker"]() as db:
            return await load_meeting_record(db, meeting_id=seed.ready_id)

    stale = client.portal.call(snapshot)
    before = _info(client, seed.ready_id)
    saved = _rename(client, seed.ready_id, "Ручное название", before["title_version"]).json()

    async def store():
        async with client.app_state["sessionmaker"]() as db:
            await persist_meeting(db, stale)

    client.portal.call(store)
    after = _info(client, seed.ready_id)
    assert after["title"] == saved["title"]
    assert after["title_version"] == saved["title_version"]


@pytest.mark.parametrize("legacy", [False, True])
def test_ingest_retry_after_rename_keeps_identity_guards(client, legacy):
    payload = {
        "local_recording_id": "rename-retry",
        "title": "Исходное имя",
        "title_source": "app_context",
        "duration_seconds": 10,
    }
    created = client.post("/api/v1/meetings", headers=auth_headers(), json=payload)
    assert created.status_code == 200, created.text
    mid = UUID(created.json()["meeting_id"])
    if legacy:

        async def clear_fingerprint():
            async with client.app_state["sessionmaker"]() as db:
                m = await db.get(Meeting, mid)
                m.create_request_fingerprint_sha256 = None
                await db.commit()

        client.portal.call(clear_fingerprint)
    assert (
        _rename(client, mid, "Ручное имя", _info(client, mid)["title_version"]).status_code == 200
    )
    assert client.post("/api/v1/meetings", headers=auth_headers(), json=payload).status_code == 200
    assert (
        client.post(
            "/api/v1/meetings", headers=auth_headers(), json={**payload, "duration_seconds": 11}
        ).status_code
        == 409
    )
    assert _info(client, mid)["title"] == "Ручное имя"


@pytest.mark.parametrize("first", ["calendar", "deletion", "rename"])
def test_concurrent_writers_use_the_same_postgres_row_lock(client, first):
    from twobrain_rec_server.cabinet.meeting_titles import save_meeting_title
    from twobrain_rec_server.calendar.matching import _apply_calendar_title
    from twobrain_rec_server.processing.fences import lock_meeting_fence

    seed = seed_cabinet_meetings(client)
    version = _info(client, seed.ready_id)["title_version"]

    async def race():
        async with client.app_state["sessionmaker"]() as a, client.app_state["sessionmaker"]() as b:
            locked = await lock_meeting_fence(
                a, workspace_id=WORKSPACE_ID, meeting_id=seed.ready_id
            )
            if first == "calendar":
                locked.title = "Календарь"
                locked.title_source = "calendar"
                locked.title_updated_at = datetime.now(UTC)
            elif first == "deletion":
                locked.deletion_state = "requested"
            else:
                await save_meeting_title(
                    a,
                    workspace_id=WORKSPACE_ID,
                    meeting_id=seed.ready_id,
                    user_id=USER_ID,
                    title="Ручное имя",
                    expected_version=version,
                )

            async def second_writer():
                if first != "rename":
                    return await save_meeting_title(
                        b,
                        workspace_id=WORKSPACE_ID,
                        meeting_id=seed.ready_id,
                        user_id=USER_ID,
                        title="Ручное имя",
                        expected_version=version,
                    )
                m = await lock_meeting_fence(b, workspace_id=WORKSPACE_ID, meeting_id=seed.ready_id)
                applied = await _apply_calendar_title(
                    b,
                    meeting=m,
                    attempt=SimpleNamespace(
                        attempt_state="matched_auto", matched_title="Поздний календарь"
                    ),
                    updated_at=datetime.now(UTC),
                )
                assert not applied
                assert m.title == "Ручное имя"
                return m

            pending = asyncio.create_task(second_writer())
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(asyncio.shield(pending), 0.15)
            await a.commit()
            if first != "rename":
                with pytest.raises(ProblemDetail) as caught:
                    await pending
                assert caught.value.code == (
                    "meeting_title_conflict" if first == "calendar" else "meeting_deletion_active"
                )
            else:
                await pending
                await b.commit()

    client.portal.call(race)


@pytest.mark.parametrize("desktop", [False, True])
def test_cookie_rename_requires_session_bound_csrf(client, desktop):
    from tests.integration.test_cabinet_csrf import (
        OWNER_REVIEW_TEST_TOKEN,
        _seed_owner_review_session,
    )
    from twobrain_rec_server.auth.csrf import issue_csrf_token
    from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME

    seed = seed_cabinet_meetings(client)
    version = _info(client, seed.ready_id)["title_version"]
    session = client.portal.call(_seed_owner_review_session, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)
    path = f"{'/desktop' if desktop else ''}/meetings/{seed.ready_id}/title"
    body = {"title": "Название с проверкой сессии", "expected_version": version}
    for token in ("", "stale"):
        response = client.post(
            path, data={**body, "csrf_token": token}, headers={"Accept": "application/json"}
        )
        assert response.status_code == 403
    token = issue_csrf_token(session_id=session.id, secret=str(client.app.state.web_csrf_secret))
    response = client.post(
        path, data={**body, "csrf_token": token}, headers={"Accept": "application/json"}
    )
    assert response.status_code == 200, response.text


def test_title_version_prevents_aba_and_deletion_hides_html_draft(client):
    seed = seed_cabinet_meetings(client)
    original = _info(client, seed.ready_id)
    first = _rename(client, seed.ready_id, "Временное имя", original["title_version"]).json()
    restored = _rename(client, seed.ready_id, original["title"], first["title_version"]).json()
    assert restored["title_version"] != original["title_version"]
    assert (
        _rename(client, seed.ready_id, "Устаревшая правка", original["title_version"]).status_code
        == 409
    )

    async def deleting():
        async with client.app_state["sessionmaker"]() as db:
            m = await db.get(Meeting, seed.ready_id)
            m.deletion_state = "requested"
            await db.commit()

    client.portal.call(deleting)
    result = _rename(
        client, seed.ready_id, "Недоступный черновик", restored["title_version"], accept="text/html"
    )
    assert result.status_code == 409
    assert "Недоступный черновик" not in result.text
    assert "data-meeting-title-form" not in result.text


def test_export_preserves_full_user_title(client):
    from tests.fixtures.cabinet_access import set_artifact_policy

    seed = seed_cabinet_meetings(client)
    title = "я" * 500
    assert (
        _rename(
            client, seed.ready_id, title, _info(client, seed.ready_id)["title_version"]
        ).status_code
        == 200
    )
    set_artifact_policy(client, seed.ready_id, transcript_download="allowed")
    path = f"/api/v1/cabinet/meetings/{seed.ready_id}/content-exports"
    capability = client.get(path, headers=auth_headers()).json()
    response = client.post(
        path,
        headers=auth_headers(),
        json={
            "content_scope": "transcript",
            "format": "txt",
            "processing_result_id": capability["processing_result_id"],
            "outcome_set_id": None,
        },
    )
    assert response.status_code == 200, response.text
    assert title in response.text
