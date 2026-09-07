from __future__ import annotations

import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from html import unescape
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import WORKSPACE_ID
from tests.fixtures.cabinet import create_outcome_ready_meeting
from tests.fixtures.cabinet_access import (
    SHARED_USER_ID,
    add_workspace_user,
    auth_headers_for,
    grant_meeting_to_user,
)
from tests.fixtures.meeting_protocol import seed_accepted_protocol
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.cabinet.web_routes import auth_email_flow, browser
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    ExternalIdentity,
    Meeting,
    MeetingShareGrant,
    ProcessingResult,
    TranscriptSegment,
)


@pytest.mark.parametrize("scenario", [
    "valid", "missing_segment", "unreferenced_segment", "candidate", "source_mismatch", "deleted", "tampered", "foreign",
])
def test_export_source_link_reauthorizes_and_never_uses_another_revision(client, scenario):
    meeting_id = create_outcome_ready_meeting(client, "protocol-source-link")

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            outcome, segments = await seed_accepted_protocol(db, meeting_id)
            segment_id = segments[0].segment_id
            if scenario == "missing_segment":
                segment_id = uuid4()
            elif scenario == "unreferenced_segment":
                segment_id = segments[-1].segment_id
                assert segment_id != segments[0].segment_id
            elif scenario == "candidate":
                outcome.revision_state = "candidate"
                outcome.accepted_at = None
            elif scenario == "source_mismatch":
                outcome.source_result_hash = "another-revision"
            elif scenario == "deleted":
                meeting = await db.get(Meeting, meeting_id)
                meeting.deleted_at = datetime.now(UTC)
            elif scenario == "tampered":
                outcome.content_hash = "f" * 64
            await db.commit()
            return outcome.id, segment_id

    outcome_id, segment_id = asyncio.run(seed())
    headers = auth_headers()
    if scenario == "foreign":
        headers["X-Workspace-Id"] = str(uuid4())
    response = client.get(
        f"/cabinet/meetings/{meeting_id}/sources/{outcome_id}/{segment_id}?workspace_id={WORKSPACE_ID}", headers=headers,
    )
    if scenario == "valid":
        assert response.status_code == 200
        assert f'data-initial-source-segment="{segment_id}"' in response.text
        assert "data-transcript-turn" in response.text
    else:
        assert response.status_code in {403, 404, 409}
        assert "data-initial-source-segment" not in response.text
        assert "data-transcript-turn" not in response.text


@pytest.mark.parametrize("scope", ["full_meeting", "summary_only", "revoked"])
def test_protocol_source_link_requires_current_full_grant(client, scope):
    meeting_id = create_outcome_ready_meeting(client, "protocol-source-grant")
    add_workspace_user(client)

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            outcome, segments = await seed_accepted_protocol(db, meeting_id)
            return outcome.id, segments[0].segment_id

    outcome_id, segment_id = asyncio.run(seed())
    granted = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/shares", headers=auth_headers(),
        json={"grantee_user_id": str(SHARED_USER_ID), "content_scope": "summary_only" if scope == "summary_only" else "full_meeting"},
    )
    assert granted.status_code == 201
    if scope == "revoked":
        revoked = client.delete(
            f"/api/v1/cabinet/meetings/{meeting_id}/shares/{granted.json()['grant']['grant_id']}",
            headers=auth_headers(),
        )
        assert revoked.status_code == 204
    response = client.get(
        f"/cabinet/meetings/{meeting_id}/sources/{outcome_id}/{segment_id}?workspace_id={WORKSPACE_ID}",
        headers=auth_headers_for(),
    )
    assert response.status_code == (200 if scope == "full_meeting" else 404)
    assert ("data-initial-source-segment" in response.text) == (scope == "full_meeting")


@pytest.fixture
def protocol_source(client):
    meeting_id = create_outcome_ready_meeting(client, "source-link-continuation")

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            outcome, segments = await seed_accepted_protocol(
                db, meeting_id, text="Синтетический протокол для перехода к источнику.",
            )
            meeting = await db.get(Meeting, meeting_id)
            meeting.visibility = "owner_only"
            await db.commit()
            segment_id = segments[0].segment_id
            return SimpleNamespace(
                meeting_id=meeting_id,
                outcome_id=outcome.id,
                segment_id=segment_id,
                result_id=outcome.processing_result_id,
                summary_text=outcome.protocol_json["executive_summary"][0]["text"],
                transcript_text=segments[0].text,
                url=(f"/cabinet/meetings/{meeting_id}/sources/{outcome.id}/{segment_id}"
                     f"?workspace_id={WORKSPACE_ID}"),
            )

    return asyncio.run(seed())


def _assert_source_content_withheld(response, source):
    assert "data-initial-source-segment" not in response.text
    assert "data-transcript-turn" not in response.text
    assert source.summary_text not in unescape(response.text)
    assert source.transcript_text not in unescape(response.text)


@pytest.mark.parametrize("session", ["missing", "invalid"])
def test_source_link_redirects_to_login_with_exact_destination(client, protocol_source, session):
    client.cookies.clear()
    if session == "invalid":
        client.cookies.set(AUTH_SESSION_COOKIE_NAME, "synthetic-invalid-source-session")
    response = client.get(
        protocol_source.url, headers={"Accept": "text/html"}, follow_redirects=False,
    )
    _assert_source_content_withheld(response, protocol_source)
    assert response.status_code == 303
    destination = urlsplit(response.headers["location"])
    assert destination.path == "/login" and not destination.netloc
    assert parse_qs(destination.query)["next"] == [protocol_source.url]


@pytest.mark.parametrize("revoke_during_login", [False, True])
def test_email_login_resumes_exact_source_and_rechecks_access(
    client, protocol_source, revoke_during_login
):
    add_workspace_user(client)
    grant_meeting_to_user(client, protocol_source.meeting_id)
    email = "source-recipient@example.test"

    async def seed_identity():
        async with client.app_state["sessionmaker"]() as db:
            db.add(ExternalIdentity(
                user_id=SHARED_USER_ID, provider="email", provider_subject=email,
                provider_username=email, email=email, is_verified=True,
            ))
            await db.commit()

    asyncio.run(seed_identity())
    client.cookies.clear()
    login = client.get("/login", params={"next": protocol_source.url})
    assert login.status_code == 200
    assert f'name="next" value="{protocol_source.url}"' in unescape(login.text)
    _assert_source_content_withheld(login, protocol_source)
    started = client.post(
        "/login/email/start", data={"email": email, "next": protocol_source.url},
    )
    assert started.status_code == 200
    state = re.search(r'name="state" value="([^"]+)"', started.text)
    code = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", started.text)
    assert state is not None and code is not None
    _assert_source_content_withheld(started, protocol_source)
    cookie_name = auth_email_flow._email_auth_browser_cookie_name(
        state_nonce=state.group(1), secure=True,
    )
    nonce = started.cookies.get(cookie_name)
    assert nonce
    # TestClient uses HTTP; carry the genuine synthetic Secure-cookie value
    # without its transport flag, as in the existing browser-login tests.
    client.cookies.set(cookie_name, nonce, domain="testserver.local", path="/")
    if revoke_during_login:
        asyncio.run(_revoke_source_grant(client, protocol_source.meeting_id))
    verified = client.post(
        "/login/email/verify",
        data={"email": email, "code": code.group(1), "state": state.group(1), "next": protocol_source.url},
        follow_redirects=False,
    )
    assert verified.status_code == 303
    assert verified.headers["location"] == protocol_source.url
    token = verified.cookies.get(AUTH_SESSION_COOKIE_NAME)
    assert token
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, token, domain="testserver.local", path="/")
    resumed = client.get(
        verified.headers["location"], headers={"Accept": "text/html"}, follow_redirects=False,
    )
    assert resumed.status_code == (404 if revoke_during_login else 200)
    if revoke_during_login:
        _assert_source_content_withheld(resumed, protocol_source)
    else:
        assert f'data-initial-source-segment="{protocol_source.segment_id}"' in resumed.text
        assert protocol_source.transcript_text in unescape(resumed.text)
        assert protocol_source.summary_text in unescape(resumed.text)
        assert resumed.headers["cache-control"] == "private, no-store"


async def _revoke_source_grant(client, meeting_id):
    async with client.app_state["sessionmaker"]() as db:
        grant = await db.scalar(select(MeetingShareGrant).where(
            MeetingShareGrant.meeting_id == meeting_id,
            MeetingShareGrant.grantee_user_id == SHARED_USER_ID,
        ))
        assert grant is not None and grant.status == "active"
        grant.status = "revoked"
        grant.revoked_at = datetime.now(UTC)
        await db.commit()


@pytest.mark.parametrize("change", ["unchanged", "revoke", "delete", "source_hash", "source_replaced"])
def test_source_link_rechecks_after_final_render(client, monkeypatch, protocol_source, change):
    add_workspace_user(client)
    grant_meeting_to_user(client, protocol_source.meeting_id)
    original_render = browser.render_meeting_detail_page
    buffered_pages = []
    mutations = []

    async def change_after_render():
        if change == "revoke":
            await _revoke_source_grant(client, protocol_source.meeting_id)
        elif change != "unchanged":
            async with client.app_state["sessionmaker"]() as db:
                if change == "delete":
                    meeting = await db.get(Meeting, protocol_source.meeting_id)
                    meeting.deletion_state = "requested"
                    meeting.deletion_epoch += 1
                else:
                    result = await db.get(ProcessingResult, protocol_source.result_id)
                    if change == "source_hash":
                        result.source_result_hash = "changed-source-during-render"
                    else:
                        newer = ProcessingResult(
                            workspace_id=result.workspace_id, meeting_id=result.meeting_id,
                            media_revision_id=result.media_revision_id, mediascribe_job_id=result.mediascribe_job_id,
                            processing_workflow_id=result.processing_workflow_id,
                            result_version=result.result_version + 1, status="imported",
                            transcript_status=result.transcript_status, diarization_status=result.diarization_status,
                            segment_count=result.segment_count, diarization_segment_count=result.diarization_segment_count,
                            source_result_hash="replacement-source-during-render", imported_at=datetime.now(UTC),
                        )
                        db.add(newer)
                        await db.flush()
                        # Distinct canonical IDs even when the two revisions have
                        # the same wording/timestamps: never match by proximity.
                        for model in (TranscriptSegment, DiarizationSegment):
                            rows = (await db.scalars(select(model).where(
                                model.processing_result_id == result.id,
                            ))).all()
                            for row in rows:
                                values = {column.name: getattr(row, column.name) for column in model.__table__.c
                                          if column.name not in {"id", "created_at", "processing_result_id"}}
                                db.add(model(**values, processing_result_id=newer.id))
                await db.commit()
        mutations.append(change)

    def render_then_change(*args, **kwargs):
        page = original_render(*args, **kwargs)
        assert f'data-initial-source-segment="{protocol_source.segment_id}"' in page
        assert protocol_source.transcript_text in unescape(page)
        assert protocol_source.summary_text in unescape(page)
        buffered_pages.append(page)
        # The route's renderer is synchronous. Commit in an independent thread
        # and DB transaction before returning its HTML; no sleeps or mocked guard.
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(asyncio.run, change_after_render()).result(timeout=15)
        return page

    monkeypatch.setattr(browser, "render_meeting_detail_page", render_then_change)
    response = client.get(protocol_source.url, headers=auth_headers_for(), follow_redirects=False)
    assert len(buffered_pages) == 1 and mutations == [change]
    if change == "source_replaced":
        # A fresh request already refuses this destination. The buffered page
        # must honor the same source boundary instead of winning the render race.
        monkeypatch.setattr(browser, "render_meeting_detail_page", original_render)
        fresh_response = client.get(protocol_source.url, headers=auth_headers_for(), follow_redirects=False)
        assert fresh_response.status_code == 409
        _assert_source_content_withheld(fresh_response, protocol_source)
    if change == "unchanged":
        assert response.status_code == 200
        assert response.text == buffered_pages[0]
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["referrer-policy"] == "no-referrer"
    else:
        assert response.status_code in {404, 409}
        _assert_source_content_withheld(response, protocol_source)
