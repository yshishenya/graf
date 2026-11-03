"""F292: real public-reader boundaries, legacy compatibility and audience transitions."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import WORKSPACE_ID
from tests.fixtures.cabinet import SAFE_TRANSCRIPT_TEXT
from tests.fixtures.cabinet_access import (
    SHARED_USER_ID,
    add_retained_playback_m4a,
    add_workspace_user,
)
from tests.integration.test_summary_sharing import prepare
from twobrain_rec_server.db.models import MeetingShareGrant, ProcessingResult


def publish(client, meeting, template, scope="full_meeting"):
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting}/summary-sharing/link",
        headers=auth_headers(),
        json={"template_key": template, "content_scope": scope},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    return data, data["share_url"].split("https://graf.example.test")[-1]


def test_full_reader_and_explicit_scope_preserve_legacy(client, tmp_path):
    meeting, template = prepare(client, tmp_path)
    link, path = publish(client, meeting, template, "summary_only")
    again, _ = publish(client, meeting, template)
    assert again == link  # Copy cannot silently widen a previously published document.
    assert "transcript" not in client.get(path).json()
    changed = client.post(
        f"/api/v1/cabinet/meetings/{meeting}/summary-sharing/link/scope",
        headers=auth_headers(),
        json={
            "grant_id": link["grant_id"],
            "expected_version": link["version"],
            "template_key": template,
            "content_scope": "full_meeting",
        },
    )
    assert changed.status_code == 200, changed.text
    response = client.get(path)
    assert response.status_code == 200, response.text
    assert SAFE_TRANSCRIPT_TEXT in str(response.json()["transcript"])
    assert set(response.json()) == {
        "meeting_label",
        "occurred_at",
        "duration_seconds",
        "summary_sections",
        "protocol",
        "transcript",
        "media_version",
        "playback_available",
    }
    html = client.get(path, headers={"Accept": "text/html"})
    assert "data-public-sharing" in html.text and "data-public-transcript" in html.text
    assert "data-public-welcome" in html.text and "Начать пользоваться GRAF" in html.text
    assert html.headers["referrer-policy"] == "no-referrer"
    assert html.headers["cache-control"] == "private, no-store"
    stale = client.post(
        f"/api/v1/cabinet/meetings/{meeting}/summary-sharing/link/scope",
        headers=auth_headers(),
        json={
            "grant_id": link["grant_id"],
            "expected_version": link["version"],
            "content_scope": "summary_only",
            "template_key": template,
        },
    )
    assert stale.status_code == 409


def test_public_playback_ranges_revoke_and_media_fence(client, tmp_path):
    meeting, template = prepare(client, tmp_path)
    body = b"x" * (4 * 1024 * 1024 + 17)
    add_retained_playback_m4a(client, UUID(str(meeting)), body)
    link, path = publish(client, meeting, template)
    version = client.get(path).json()["media_version"]
    audio = path.replace("?", "/playback?") + "&media_version=" + version
    response = client.get(audio)
    assert response.status_code == 200, response.text[:100]
    assert response.content == body
    partial = client.get(audio, headers={"Range": "bytes=3-19"})
    assert partial.status_code == 206 and partial.content == body[3:20]
    assert partial.headers["content-range"] == f"bytes 3-19/{len(body)}"
    assert client.get(audio, headers={"Range": f"bytes={len(body)}-"}).status_code == 416
    assert client.get(audio.replace(version, "0" * 24)).status_code == 409
    revoked = client.request(
        "DELETE",
        f"/api/v1/cabinet/meetings/{meeting}/summary-sharing/link",
        headers=auth_headers(),
        json={"grant_id": link["grant_id"], "expected_version": link["version"]},
    )
    assert revoked.status_code == 200
    assert client.get(audio, headers={"Range": "bytes=0-3"}).status_code == 404
    assert client.get(path).status_code == 404


def test_audience_transitions_preserve_addressed_grants(client, tmp_path):
    meeting, template = prepare(client, tmp_path)
    add_workspace_user(client)
    client.app.state.settings.share_workspace_audience_enabled = True
    addressed = client.post(
        f"/api/v1/cabinet/meetings/{meeting}/shares",
        headers=auth_headers(),
        json={
            "audience_type": "user",
            "audience_id": str(SHARED_USER_ID),
            "content_scope": "full_meeting",
            "can_download": False,
            "can_export": False,
        },
    )
    assert addressed.status_code == 201, addressed.text
    url = f"/api/v1/cabinet/meetings/{meeting}/sharing/general-access"
    state = client.get(url, headers=auth_headers()).json()
    for audience in ("workspace", "link", "invite_only"):
        response = client.post(
            url,
            headers=auth_headers(),
            json={
                "audience": audience,
                "content_scope": "full_meeting",
                "template_key": template,
                "expected_fingerprint": state["fingerprint"],
            },
        )
        assert response.status_code == 200, response.text
        state = response.json()
        if audience == "workspace":
            stale = state["fingerprint"]
        assert state["audience"] == audience
    conflict = client.post(
        url,
        headers=auth_headers(),
        json={"audience": "workspace", "expected_fingerprint": stale, "template_key": template},
    )
    assert conflict.status_code == 409

    async def check():
        async with client.app_state["sessionmaker"]() as db:
            grants = (
                await db.scalars(
                    select(MeetingShareGrant).where(
                        MeetingShareGrant.meeting_id == UUID(str(meeting)),
                        MeetingShareGrant.status == "active",
                    )
                )
            ).all()
            assert len(grants) == 1 and grants[0].audience_type == "user"

    asyncio.run(check())


def test_login_continuation_never_copies_share_secret_into_login_url(client, tmp_path):
    meeting, template = prepare(client, tmp_path)
    _, path = publish(client, meeting, template)
    response = client.get(
        path.replace("?", "/continue?") + "&action=sign-in", follow_redirects=False
    )
    assert response.status_code == 303
    token = path.split("/public-shares/")[1].split("?")[0]
    assert token not in response.headers["location"]
    assert response.headers["location"].startswith("/login?next=")
    assert client.get(response.headers["location"]).status_code == 200
    assert "httponly" in response.headers["set-cookie"].lower()
    resumed = client.get("/shared-meeting/continue", follow_redirects=False)
    assert resumed.status_code == 303 and resumed.headers["location"] == path


def test_rotation_expiry_narrowing_and_legacy_writer_cannot_bypass_version(client, tmp_path):
    meeting, template = prepare(client, tmp_path)
    add_retained_playback_m4a(client, UUID(str(meeting)), b"audio")
    link, path = publish(client, meeting, template)
    version = client.get(path).json()["media_version"]
    audio = path.replace("?", "/playback?") + "&media_version=" + version
    base = f"/api/v1/cabinet/meetings/{meeting}"
    assert (
        client.post(base + f"/shares/{link['grant_id']}/rotate", headers=auth_headers()).status_code
        == 409
    )
    assert (
        client.delete(base + f"/shares/{link['grant_id']}", headers=auth_headers()).status_code
        == 409
    )
    rotated = client.post(
        base + "/summary-sharing/link/rotate",
        headers=auth_headers(),
        json={"grant_id": link["grant_id"], "expected_version": link["version"]},
    ).json()
    assert client.get(path).status_code == 404 and client.get(audio).status_code == 404
    current = rotated["share_url"].split("https://graf.example.test")[-1]
    narrowed = client.post(
        base + "/summary-sharing/link/scope",
        headers=auth_headers(),
        json={
            "grant_id": rotated["grant_id"],
            "expected_version": rotated["version"],
            "content_scope": "summary_only",
            "template_key": template,
        },
    )
    assert narrowed.status_code == 200, narrowed.text
    assert "transcript" not in client.get(current).json()
    assert (
        client.get(current.replace("?", "/playback?") + "&media_version=" + version).status_code
        == 404
    )

    async def expire():
        async with client.app_state["sessionmaker"]() as db:
            grant = await db.get(MeetingShareGrant, UUID(link["grant_id"]))
            grant.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()

    asyncio.run(expire())
    assert client.get(current).status_code == 404


def test_public_current_result_fence_and_anonymous_audit(client, tmp_path):
    from uuid import uuid4

    from twobrain_rec_server.db.models import Meeting, MeetingEgressAuditEvent

    meeting, template = prepare(client, tmp_path)
    add_retained_playback_m4a(client, UUID(str(meeting)), b"audio")
    link, path = publish(client, meeting, template)
    version = client.get(path).json()["media_version"]
    audio = path.replace("?", "/playback?") + "&media_version=" + version
    assert client.get(audio).status_code == 200

    async def replace():
        async with client.app_state["sessionmaker"]() as db:
            events = (
                await db.scalars(
                    select(MeetingEgressAuditEvent).where(
                        MeetingEgressAuditEvent.meeting_id == UUID(str(meeting)),
                        MeetingEgressAuditEvent.event_type == "playback_requested",
                    )
                )
            ).all()
            assert events and events[-1].actor_user_id is None and events[-1].device_id is None
            assert events[-1].metadata_json["share_grant_id"] == link["grant_id"]
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == UUID(str(meeting)))
            )
            result.status = "failed"
            await db.commit()

    asyncio.run(replace())
    assert client.get(path).json()["transcript"] == []
    assert client.get(audio).status_code == 409
    foreign = path.replace(str(WORKSPACE_ID), str(uuid4()))
    assert client.get(foreign).status_code == 404

    async def delete():
        async with client.app_state["sessionmaker"]() as db:
            row = await db.get(Meeting, UUID(str(meeting)))
            row.deletion_state = "requested"
            await db.commit()

    asyncio.run(delete())
    assert client.get(path).status_code == 404


def test_continuation_tamper_expiry_and_invalid_context_are_safe(client, tmp_path):
    from cryptography.fernet import Fernet

    from twobrain_rec_server.cabinet.public_sharing import CONTINUATION_COOKIE

    meeting, template = prepare(client, tmp_path)
    _, path = publish(client, meeting, template)
    route = path.replace("?", "/continue?")
    assert (
        client.get(route + "&tab=outcomes&position_ms=10", follow_redirects=False).status_code
        == 422
    )
    response = client.get(
        route + "&tab=recording&position_ms=14000&media_version=" + "a" * 24, follow_redirects=False
    )
    assert response.status_code == 303
    resumed = client.get("/shared-meeting/continue", follow_redirects=False)
    assert (
        resumed.headers["location"]
        == path + "&media_version=" + "a" * 24 + "#recording?position_ms=14000"
    )
    key = client.app.state.settings.credential_encryption_key_file.read_bytes()
    for candidate in [
        Fernet(key)
        .encrypt_at_time(path.encode(), int(datetime.now(UTC).timestamp()) - 601)
        .decode(),
        Fernet(key).encrypt(b"https://evil.example.test/").decode(),
        "tampered",
    ]:
        client.cookies.set(CONTINUATION_COOKIE, candidate)
        assert (
            client.get("/shared-meeting/continue", follow_redirects=False).headers["location"]
            == "/meetings"
        )


def test_public_stream_is_bounded_and_closes_on_size_mismatch():
    import pytest

    from twobrain_rec_server.cabinet.egress import ReviewAudioBuildError, _bounded_public_stream

    class Body:
        def __init__(self, chunks):
            self.chunks = chunks
            self.closed = False

        def __iter__(self):
            return iter(self.chunks)

        def close(self):
            self.closed = True

    body = Body([b"x" * 65536] * 80)
    chunks = list(_bounded_public_stream(body, expected_length=65536 * 80))
    assert (
        max(map(len, chunks)) <= 4 * 1024 * 1024
        and sum(map(len, chunks)) > 4 * 1024 * 1024
        and body.closed
    )
    for chunks, expected in [
        ([b"a"], 2),
        ([b"abc"], 2),
        ([b"x" * (4 * 1024 * 1024 + 1)], 4 * 1024 * 1024 + 1),
    ]:
        body = Body(chunks)
        with pytest.raises(ReviewAudioBuildError):
            list(_bounded_public_stream(body, expected_length=expected))
        assert body.closed


def test_full_link_without_summary_and_summary_html_never_embeds_recording(client, tmp_path):
    from tests.fixtures.cabinet import create_ready_meeting

    meeting, template = prepare(client, tmp_path)
    fresh = create_ready_meeting(client, "f292-without-summary")
    _, path = publish(client, fresh, template)
    response = client.get(path)
    assert response.status_code == 200, response.text
    assert response.json()["summary_sections"] == []
    assert SAFE_TRANSCRIPT_TEXT in str(response.json()["transcript"])
    _, summary = publish(client, meeting, template, "summary_only")
    html = client.get(summary, headers={"Accept": "text/html"})
    assert html.status_code == 200, html.text
    assert "data-public-welcome" in html.text
    assert "data-public-transcript" not in html.text and "<audio" not in html.text
    assert SAFE_TRANSCRIPT_TEXT not in html.text


def test_personal_roles_and_scope_do_not_require_download_permission(client, tmp_path):
    from tests.fixtures.cabinet_access import auth_headers_for

    meeting, template = prepare(client, tmp_path)
    add_workspace_user(client)
    base = f"/api/v1/cabinet/meetings/{meeting}"
    response = client.post(
        base + "/shares",
        headers=auth_headers(),
        json={
            "audience_type": "user",
            "audience_id": str(SHARED_USER_ID),
            "content_scope": "summary_only",
        },
    )
    grant = response.json()["grant"]["grant_id"]
    version = response.json()["grant"]["version"]
    for role, scope in [
        ("editor", "full_meeting"),
        ("commenter", "full_meeting"),
        ("viewer", "full_meeting"),
        ("summary", "summary_only"),
    ]:
        changed = client.patch(
            base + f"/shares/{grant}/permissions",
            headers=auth_headers(),
            json={
                "expected_version": version,
                "content_scope": scope,
                "can_comment": role in ("editor", "commenter"),
                "can_edit": role == "editor",
            },
        )
        assert changed.status_code == 200, changed.text
        assert changed.json()["content_scope"] == scope
        stale = client.patch(base + f"/shares/{grant}/permissions", headers=auth_headers(),
            json={"expected_version":version,"can_comment":False,"can_edit":False})
        assert stale.status_code == 409
        stale_revoke = client.delete(base + f"/shares/{grant}?expected_version={version}", headers=auth_headers())
        assert stale_revoke.status_code == 409
        version = changed.json()["version"]
    denied = client.patch(
        base + f"/shares/{grant}/permissions",
        headers=auth_headers_for(user_id=SHARED_USER_ID),
        json={"content_scope": "full_meeting", "can_comment": True, "can_edit": True},
    )
    assert denied.status_code in (403, 404)


def test_legacy_visibility_and_disabled_audiences_are_truthful(client, tmp_path):
    from twobrain_rec_server.db.models import Meeting

    meeting, template = prepare(client, tmp_path)
    base = f"/api/v1/cabinet/meetings/{meeting}"

    async def visible():
        async with client.app_state["sessionmaker"]() as db:
            row = await db.get(Meeting, UUID(str(meeting)))
            row.visibility = "team"
            await db.commit()

    asyncio.run(visible())
    state = client.get(base + "/sharing/general-access", headers=auth_headers()).json()
    assert state["audience"] == "workspace" and state["content_scope"] == "full_meeting"
    assert state["capabilities"]["workspace"] is False
    assert (
        client.post(
            base + "/summary-sharing/link", headers=auth_headers(), json={"template_key": template}
        ).status_code
        == 409
    )
    changed = client.post(
        base + "/sharing/general-access",
        headers=auth_headers(),
        json={
            "audience": "invite_only",
            "expected_fingerprint": state["fingerprint"],
        },
    )
    assert changed.status_code == 200 and changed.json()["audience"] == "invite_only"
    assert changed.json()["fingerprint"] != state["fingerprint"]
    blocked = client.post(
        base + "/sharing/general-access",
        headers=auth_headers(),
        json={
            "audience": "workspace",
            "expected_fingerprint": changed.json()["fingerprint"],
        },
    )
    assert blocked.status_code == 403
    assert (
        client.get(base + "/sharing/general-access", headers=auth_headers()).json()["audience"]
        == "invite_only"
    )


def test_external_full_view_without_file_permissions_opens_recording(client, tmp_path):
    from tests.fakes.auth_contexts import DEVICE_ID, USER_ID
    from tests.integration.test_recording_share_public_link import _independent_invitation_login
    from twobrain_rec_server.cabinet.access import create_share_invitation, open_invitation_delivery
    from twobrain_rec_server.db.models import Meeting

    meeting_id, _template = prepare(client, tmp_path)
    key = client.app.state.settings.credential_encryption_key_file.read_bytes()
    address = "reader-f292@example.test"

    async def invite():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, UUID(str(meeting_id)))
            invitation = await create_share_invitation(
                db,
                workspace_id=WORKSPACE_ID,
                meeting=meeting,
                actor_user_id=USER_ID,
                device_id=DEVICE_ID,
                address=address,
                content_scope="full_meeting",
                can_download=False,
                can_export=False,
                encryption_key=key,
                ttl_seconds=3600,
            )
            _, token = open_invitation_delivery(invitation.encrypted_delivery_address, key=key)
            await db.commit()
            return token

    response = _independent_invitation_login(
        client, recipient_email=address, raw_token=asyncio.run(invite())
    )
    assert response.status_code == 303, response.text
    assert (
        response.headers["location"] == f"/shared-meetings/{meeting_id}?workspace_id={WORKSPACE_ID}"
    )
    page = client.get(response.headers["location"], headers={"Accept": "text/html"})
    assert page.status_code == 200 and SAFE_TRANSCRIPT_TEXT in page.text
    assert f"/shared-meetings/{meeting_id}/downloads/audio" not in page.text
    denied = client.get(
        f"/api/v1/cabinet/shared-meetings/{meeting_id}/downloads/audio",
        params={"workspace_id": str(WORKSPACE_ID)},
    )
    assert denied.status_code in (403, 409)
