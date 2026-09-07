"""Synthetic audio: one-time activation, Range, revocation and source pinning."""

from dataclasses import replace
from http.cookies import SimpleCookie
from uuid import UUID

import pytest

from tests.fixtures.cabinet_access import _add_retained_playback_m4a
from tests.fixtures.processing import create_finalized_meeting
from tests.integration import test_system_admin_security as security
from tests.integration.test_system_admin_content import context_for
from twobrain_rec_server.db.session import create_system_admin_database
from twobrain_rec_server.system_admin.audit import create_case_context
from twobrain_rec_server.system_admin.media import audio_response, issue_media_ticket

system_database = security.system_database
pytestmark = pytest.mark.strict_rls


@pytest.mark.asyncio
async def test_audio_range_single_activation_and_revocation(system_database, client):
    db = system_database
    finalized = create_finalized_meeting(client, "system-audio-range")
    meeting = UUID(finalized["meeting"]["meeting_id"])
    body = b"synthetic-audio-range" * 300000
    await _add_retained_playback_m4a(client, meeting, body)
    engine, sessions = create_system_admin_database(database_url=db["url"])
    context = replace(context_for(db, meeting), permission="audio.listen")
    try:
        case = await create_case_context(sessions, context, reason="Synthetic audio investigation")
        context = replace(context, case_context_id=case)
        with pytest.raises(PermissionError):
            await issue_media_ticket(sessions, context)
        await db["owner"].execute("""insert into system_control.permission_grants
            (id,principal_id,assignment_id,assignment_version,permission,target_type,target_id,starts_at,expires_at,granted_by,reason)
            values(gen_random_uuid(),$1,$2,1,'audio.listen','meeting',$3,now(),now()+interval '1 hour',$1,'Synthetic grant')""",
            db["actor"],db["assignment"],meeting)
        with pytest.raises(PermissionError):
            await issue_media_ticket(sessions, replace(context,permission="audio.download"))
        ticket = await issue_media_ticket(sessions, context)
        assert "storage_object_key" not in ticket
        response = await audio_response(sessions, context, token=ticket["ticket"], cookies={},
            storage=client.app_state["storage"], range_header="bytes=5-30")
        assert response.status_code == 206
        assert response.headers["content-range"] == f"bytes 5-30/{len(body)}"
        assert b"".join([chunk async for chunk in response.body_iterator]) == body[5:31]
        event = await db["owner"].fetchrow("""select e.actor_user_id,a.principal_id from meeting_egress_audit_events e
            join system_control.audit_events a on a.id=e.id where e.meeting_id=$1""",meeting)
        assert event["actor_user_id"] is None and event["principal_id"] == db["actor"]
        cookie = SimpleCookie(response.headers["set-cookie"])
        cookies = {key: morsel.value for key, morsel in cookie.items()}
        with pytest.raises(PermissionError):
            await audio_response(sessions, context, token=ticket["ticket"], cookies={},
                storage=client.app_state["storage"], range_header="bytes=50-80")
        again = await audio_response(sessions, context, token=ticket["ticket"], cookies=cookies,
            storage=client.app_state["storage"], range_header="bytes=50-80")
        assert b"".join([chunk async for chunk in again.body_iterator]) == body[50:81]
        stream = await audio_response(sessions, context, token=ticket["ticket"], cookies=cookies,
            storage=client.app_state["storage"], range_header=None)
        iterator = stream.body_iterator
        assert await anext(iterator)
        await db["owner"].execute("update system_control.sessions set revoked_at=now()")
        with pytest.raises(RuntimeError, match="stream interrupted"):
            await anext(iterator)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_audio_source_change_and_deletion_close_ticket(system_database, client):
    db = system_database
    finalized = create_finalized_meeting(client, "system-audio-source")
    meeting = UUID(finalized["meeting"]["meeting_id"])
    await _add_retained_playback_m4a(client, meeting, b"synthetic-audio-source")
    engine, sessions = create_system_admin_database(database_url=db["url"])
    context = replace(context_for(db, meeting), permission="audio.download")
    try:
        await db["owner"].execute("update system_control.role_assignments set role='superadmin'")
        case = await create_case_context(sessions, context, reason="Synthetic source validation")
        context = replace(context, case_context_id=case)
        ticket = await issue_media_ticket(sessions, context)
        await db["owner"].execute("update track_artifacts set storage_object_key='synthetic/replaced' where meeting_id=$1 and track_role='playback'", meeting)
        with pytest.raises(PermissionError):
            await audio_response(sessions, context, token=ticket["ticket"], cookies={},
                storage=client.app_state["storage"], range_header=None)
        await db["owner"].execute("update meetings set deletion_state='requested' where id=$1", meeting)
        with pytest.raises(PermissionError):
            await issue_media_ticket(sessions, context)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_audio_http_cookie_range_and_download(system_database, client, monkeypatch):
    import httpx

    from twobrain_rec_server.system_admin.app import create_app
    from twobrain_rec_server.system_admin.auth import hash_token

    db = system_database
    finalized = create_finalized_meeting(client, "system-audio-http")
    meeting = UUID(finalized["meeting"]["meeting_id"])
    body = b"synthetic-http-audio"
    await _add_retained_playback_m4a(client, meeting, body)
    await db["owner"].execute("update system_control.role_assignments set role='superadmin'")
    token = "synthetic-http-session-" * 3
    await db["owner"].execute("update system_control.sessions set token_hash=$1", hash_token(token))
    monkeypatch.setenv("SYSTEM_ADMIN_ENABLED", "true")
    monkeypatch.setenv("SYSTEM_ADMIN_PUBLIC_ORIGIN", "https://admin.example.invalid")
    app = create_app()
    engine, sessions = create_system_admin_database(database_url=db["url"])
    app.state.system_sessions = sessions
    app.state.media_storage = client.app_state["storage"]
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://admin.example.invalid") as browser:
            browser.cookies.set("__Host-graf_system_session", token)
            prefix = "/api/system-admin/v1"
            csrf = (await browser.get(f"{prefix}/auth/csrf")).json()["csrf_token"]
            browser.headers.update({"Origin":"https://admin.example.invalid","X-CSRF-Token":csrf})
            case = (await browser.post(f"{prefix}/meetings/{meeting}/case", json={"reason":"Synthetic audio check"})).json()
            issued = await browser.post(f"{prefix}/meetings/{meeting}/media-ticket",
                json={"purpose":"download","case_context_id":case["case_context_id"]})
            assert issued.status_code == 200, issued.text
            media_path = f"{prefix}/media/{issued.json()['ticket']}"
            response = await browser.get(media_path, headers={"Range":"bytes=0-8"})
            assert response.status_code == 206 and response.content == body[:9]
            assert response.headers["content-disposition"].startswith("attachment;")
            assert response.headers["cache-control"] == "no-store"
            assert "httponly" in response.headers["set-cookie"].lower()
            import asyncio
            app.state.media_stream_slots = asyncio.Semaphore(0)
            busy = await browser.get(media_path, headers={"Range":"bytes=9-"})
            assert busy.status_code == 429 and busy.headers["retry-after"] == "5"
            app.state.media_stream_slots = asyncio.Semaphore(4)
            repeated = await browser.get(media_path, headers={"Range":"bytes=9-"})
            assert repeated.status_code == 206 and repeated.content == body[9:]
            assert app.state.media_stream_slots._value == 4
            assert (await browser.get(media_path, headers={"Range":"bytes=99999-"})).status_code == 416
            await db["owner"].execute("update system_control.sessions set revoked_at=now()")
            assert (await browser.get(media_path)).status_code == 401
    finally:
        await engine.dispose()
