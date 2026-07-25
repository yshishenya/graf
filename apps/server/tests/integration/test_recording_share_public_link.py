import asyncio
import re
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from cryptography.fernet import Fernet
from sqlalchemy import select

import twobrain_rec_server.cabinet.web_routes.browser as browser_routes
from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.cabinet import SAFE_TRANSCRIPT_TEXT, seed_cabinet_meetings
from tests.fixtures.cabinet_access import (
    SHARED_USER_ID,
    add_retained_playback_m4a,
    add_workspace_user,
    auth_headers_for,
    set_artifact_policy,
)
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.cabinet.access import (
    create_share_invitation,
    open_invitation_delivery,
    revoke_share_grant,
    revoke_share_invitation,
)
from twobrain_rec_server.db.models import (
    ExternalIdentity,
    Meeting,
    MeetingShareGrant,
    MeetingShareInvitation,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)


def test_summary_only_user_cannot_open_full_meeting_routes(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_workspace_user(client)

    share = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers(),
        json={
            "audience_type": "user",
            "audience_id": str(SHARED_USER_ID),
            "content_scope": "summary_only",
            "can_download": False,
            "can_export": False,
        },
    )

    assert share.status_code == 201
    html_summary = client.get(
        share.json()["share_url"],
        headers={**auth_headers_for(), "Accept": "text/html"},
    )
    assert html_summary.status_code == 200
    assert html_summary.headers["cache-control"] == "private, no-store"
    assert "Итоги встречи" in html_summary.text
    assert "audio" not in html_summary.text.lower()
    set_artifact_policy(client, seeds.ready_id, summary_download="allowed")
    assert client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}", headers=auth_headers_for()
    ).status_code == 404
    summary = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shared-summary",
        headers=auth_headers_for(),
    )
    assert summary.status_code == 200
    assert set(summary.json()) == {
        "meeting_label",
        "occurred_at",
        "duration_seconds",
        "summary_sections",
    }
    access = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/access",
        headers=auth_headers_for(),
    )
    assert access.status_code == 200
    scoped_access = access.json()["access"]
    assert scoped_access["state"] == "shared"
    assert scoped_access["content_scope"] == "summary_only"
    assert scoped_access["can_view"] is True
    assert scoped_access["can_view_full_meeting"] is False
    assert scoped_access["can_share"] is False
    assert scoped_access["can_download"] is False
    assert scoped_access["can_export"] is False
    assert client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/activity",
        headers=auth_headers_for(),
    ).status_code == 404
    embedded = client.get(
        f"/desktop/meetings/{seeds.ready_id}",
        headers=auth_headers_for(),
        follow_redirects=False,
    )
    assert embedded.status_code == 302
    assert embedded.headers["location"].endswith(f"/{seeds.ready_id}/shared-summary")
    assert client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/summary",
        headers=auth_headers_for(),
    ).status_code == 409


def test_summary_only_recipient_cannot_upgrade_own_share_grant(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_workspace_user(client)
    created = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers(),
        json={
            "audience_type": "user",
            "audience_id": str(SHARED_USER_ID),
            "content_scope": "summary_only",
        },
    )
    assert created.status_code == 201

    escalated = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers_for(),
        json={
            "audience_type": "user",
            "audience_id": str(SHARED_USER_ID),
            "content_scope": "full_meeting",
            "can_download": True,
            "can_export": True,
        },
    )
    access = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/access",
        headers=auth_headers_for(),
    )

    assert escalated.status_code == 404
    assert access.status_code == 200
    assert access.json()["access"]["content_scope"] == "summary_only"
    assert access.json()["access"]["can_download"] is False
    assert access.json()["access"]["can_export"] is False


def test_view_only_full_meeting_grant_cannot_download_or_export(client) -> None:
    from uuid import UUID

    seeds = seed_cabinet_meetings(client)
    user_id = UUID("30000000-0000-0000-0000-000000000121")
    device_id = UUID("40000000-0000-0000-0000-000000000121")
    add_workspace_user(client, user_id=user_id, device_id=device_id)
    viewer_headers = auth_headers_for(user_id=user_id, device_id=device_id)
    set_artifact_policy(
        client,
        seeds.ready_id,
        transcript_download="allowed",
        summary_download="allowed",
        package_export="allowed",
    )
    share = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers(),
        json={
            "audience_type": "user",
            "audience_id": str(user_id),
            "content_scope": "full_meeting",
            "can_download": False,
            "can_export": False,
        },
    )
    assert share.status_code == 201

    assert client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/transcript",
        headers=viewer_headers,
    ).status_code == 409
    capabilities = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/content-exports",
        headers=viewer_headers,
    )
    assert capabilities.status_code == 200
    assert capabilities.json()["transcript"]["state"] == "denied"
    processing_result_id = capabilities.json()["processing_result_id"]
    assert processing_result_id is not None
    export = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/content-exports",
        headers=viewer_headers,
        json={
            "content_scope": "transcript",
            "format": "txt",
            "processing_result_id": processing_result_id,
            "include_speaker_labels": True,
            "include_timestamps": True,
            "include_evidence": True,
        },
    )
    assert export.status_code == 409


def test_public_summary_link_rotation_and_revocation_invalidate_old_tokens(client) -> None:
    seeds = seed_cabinet_meetings(client)
    settings = client.app.state.settings
    previous = settings.share_public_links_enabled
    previous_abuse_gate = settings.share_public_links_abuse_gate_approved
    settings.share_public_links_enabled = True
    settings.share_public_links_abuse_gate_approved = True
    try:
        created = client.post(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
            headers=auth_headers(),
            json={
                "audience_type": "link",
                "content_scope": "summary_only",
                "can_download": False,
                "can_export": False,
                "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            },
        )
        assert created.status_code == 201
        old_url = created.json()["share_url"]
        assert client.get(old_url).status_code == 200
        html = client.get(old_url, headers={"Accept": "text/html"})
        assert html.status_code == 200
        assert html.headers["cache-control"] == "private, no-store"
        assert "Итоги встречи" in html.text

        grant_id = created.json()["grant"]["grant_id"]
        rotated = client.post(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares/{grant_id}/rotate",
            headers=auth_headers(),
        )
        assert rotated.status_code == 200
        new_url = rotated.json()["share_url"]
        assert client.get(old_url).status_code == 404
        assert client.get(new_url).status_code == 200

        revoked = client.delete(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares/{grant_id}",
            headers=auth_headers(),
        )
        assert revoked.status_code == 204
        assert client.get(new_url).status_code == 404
    finally:
        settings.share_public_links_enabled = previous
        settings.share_public_links_abuse_gate_approved = previous_abuse_gate


def test_revoked_user_grant_can_be_recreated_and_revoked_again(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_workspace_user(client)
    payload = {
        "audience_type": "user",
        "audience_id": str(SHARED_USER_ID),
        "content_scope": "full_meeting",
        "can_download": False,
        "can_export": False,
    }

    first = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers(),
        json=payload,
    )
    assert first.status_code == 201
    first_grant_id = first.json()["grant"]["grant_id"]
    assert client.delete(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares/{first_grant_id}",
        headers=auth_headers(),
    ).status_code == 204

    second = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers(),
        json=payload,
    )
    assert second.status_code == 201
    second_grant_id = second.json()["grant"]["grant_id"]
    assert second_grant_id != first_grant_id
    assert client.delete(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares/{second_grant_id}",
        headers=auth_headers(),
    ).status_code == 204


def test_revoked_public_link_can_be_recreated(client) -> None:
    seeds = seed_cabinet_meetings(client)
    settings = client.app.state.settings
    previous = settings.share_public_links_enabled
    previous_abuse_gate = settings.share_public_links_abuse_gate_approved
    settings.share_public_links_enabled = True
    settings.share_public_links_abuse_gate_approved = True
    payload = {
        "audience_type": "link",
        "content_scope": "summary_only",
        "can_download": False,
        "can_export": False,
        "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
    }
    try:
        first = client.post(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
            headers=auth_headers(),
            json=payload,
        )
        assert first.status_code == 201
        assert client.delete(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares/"
            f"{first.json()['grant']['grant_id']}",
            headers=auth_headers(),
        ).status_code == 204

        second = client.post(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
            headers=auth_headers(),
            json=payload,
        )
        assert second.status_code == 201
        assert second.json()["grant"]["grant_id"] != first.json()["grant"]["grant_id"]
        assert client.get(second.json()["share_url"]).status_code == 200
    finally:
        settings.share_public_links_enabled = previous
        settings.share_public_links_abuse_gate_approved = previous_abuse_gate


def test_expired_and_revoked_invitations_can_be_recreated(client) -> None:
    seeds = seed_cabinet_meetings(client)

    async def exercise_cycles() -> tuple[MeetingShareInvitation, ...]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, seeds.ready_id)
            assert meeting is not None
            key = Fernet.generate_key()
            first_expired = await create_share_invitation(
                db,
                workspace_id=WORKSPACE_ID,
                meeting=meeting,
                actor_user_id=USER_ID,
                device_id=DEVICE_ID,
                address="invitee@example.com",
                content_scope="summary_only",
                can_download=False,
                can_export=False,
                encryption_key=key,
                ttl_seconds=1,
            )
            first_expired.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()
            replacement = await create_share_invitation(
                db,
                workspace_id=WORKSPACE_ID,
                meeting=meeting,
                actor_user_id=USER_ID,
                device_id=DEVICE_ID,
                address="invitee@example.com",
                content_scope="summary_only",
                can_download=False,
                can_export=False,
                encryption_key=key,
                ttl_seconds=3600,
            )
            await db.commit()
            await revoke_share_invitation(
                db,
                workspace_id=WORKSPACE_ID,
                meeting=meeting,
                actor_user_id=USER_ID,
                device_id=DEVICE_ID,
                invitation_id=replacement.id,
            )
            await db.commit()
            after_revoke = await create_share_invitation(
                db,
                workspace_id=WORKSPACE_ID,
                meeting=meeting,
                actor_user_id=USER_ID,
                device_id=DEVICE_ID,
                address="invitee@example.com",
                content_scope="summary_only",
                can_download=False,
                can_export=False,
                encryption_key=key,
                ttl_seconds=3600,
            )
            await db.commit()
            outcome_unknown = await create_share_invitation(
                db,
                workspace_id=WORKSPACE_ID,
                meeting=meeting,
                actor_user_id=USER_ID,
                device_id=DEVICE_ID,
                address="unknown@example.com",
                content_scope="summary_only",
                can_download=False,
                can_export=False,
                encryption_key=key,
                ttl_seconds=3600,
            )
            outcome_unknown.status = "outcome_unknown"
            outcome_unknown.failure_code = "postal_delivery_outcome_unknown"
            await db.commit()
            await revoke_share_invitation(
                db,
                workspace_id=WORKSPACE_ID,
                meeting=meeting,
                actor_user_id=USER_ID,
                device_id=DEVICE_ID,
                invitation_id=outcome_unknown.id,
            )
            await db.commit()
            return first_expired, replacement, after_revoke, outcome_unknown

    first_expired, replacement, after_revoke, outcome_unknown = asyncio.run(exercise_cycles())
    assert first_expired.status == "expired"
    assert first_expired.encrypted_delivery_address == ""
    assert replacement.status == "revoked"
    assert replacement.encrypted_delivery_address == ""
    assert len({first_expired.id, replacement.id, after_revoke.id}) == 3
    assert after_revoke.status == "pending"
    assert outcome_unknown.status == "revoked"


def test_external_invitation_accepts_from_another_workspace_and_resolves_share(client, tmp_path) -> None:
    from uuid import UUID

    seeds = seed_cabinet_meetings(client)
    recipient_user_id = UUID("30000000-0000-0000-0000-000000000221")
    recipient_workspace_id = UUID("20000000-0000-0000-0000-000000000221")
    recipient_device_id = UUID("40000000-0000-0000-0000-000000000221")
    recipient_email = "external-invitee@example.com"
    key = Fernet.generate_key()
    key_path = tmp_path / "share.key"
    key_path.write_bytes(key)
    client.app.state.settings.credential_encryption_key_file = key_path

    async def seed_invitation() -> str:
        async with client.app_state["sessionmaker"]() as db:
            db.add_all(
                [
                    UserIdentity(
                        id=recipient_user_id,
                        organization_id=ORG_ID,
                        external_subject=str(recipient_user_id),
                        display_name="External Invitee",
                        status="active",
                    ),
                    Workspace(
                        id=recipient_workspace_id,
                        organization_id=ORG_ID,
                        slug="external-invitee-workspace",
                        name="External Invitee Workspace",
                        kind="corporate",
                    ),
                ]
            )
            await db.flush()
            db.add_all(
                [
                    WorkspaceMembership(
                        workspace_id=recipient_workspace_id,
                        user_id=recipient_user_id,
                        role="owner",
                        status="active",
                    ),
                    RegisteredDevice(
                        id=recipient_device_id,
                        workspace_id=recipient_workspace_id,
                        user_id=recipient_user_id,
                        device_public_id="external-invitee-device",
                        status="active",
                    ),
                    ExternalIdentity(
                        user_id=recipient_user_id,
                        provider="test",
                        provider_subject="external-invitee-subject",
                        email=recipient_email,
                        is_verified=True,
                    ),
                ]
            )
            meeting = await db.get(Meeting, seeds.ready_id)
            assert meeting is not None
            invitation = await create_share_invitation(
                db,
                workspace_id=WORKSPACE_ID,
                meeting=meeting,
                actor_user_id=USER_ID,
                device_id=DEVICE_ID,
                address=recipient_email,
                content_scope="summary_only",
                can_download=False,
                can_export=False,
                encryption_key=key,
                ttl_seconds=3600,
            )
            _, raw_token = open_invitation_delivery(
                invitation.encrypted_delivery_address,
                key=key,
            )
            await db.commit()
            return raw_token

    raw_token = asyncio.run(seed_invitation())
    anonymous_preview = client.get(
        f"/share-invitations/{raw_token}?workspace_id={WORKSPACE_ID}",
        headers={"Accept": "text/html"},
    )
    assert anonymous_preview.status_code == 200
    assert "Итоги встречи доступны" in anonymous_preview.text
    assert raw_token not in anonymous_preview.text
    assert "Открыть итоги" in anonymous_preview.text
    state_match = re.search(r'name="state" value="([A-Za-z0-9_-]+)"', anonymous_preview.text)
    assert state_match is not None
    recipient_headers = auth_headers_for(
        user_id=recipient_user_id,
        device_id=recipient_device_id,
        workspace_id=recipient_workspace_id,
    )
    wrong_account = client.get(
        f"/share-invitations/continue?workspace_id={WORKSPACE_ID}&state={state_match.group(1)}",
        headers=auth_headers(),
        follow_redirects=False,
    )
    assert wrong_account.status_code == 303
    assert "share_recipient_mismatch" in wrong_account.headers["location"]
    assert state_match.group(1) in wrong_account.headers["location"]
    continued = client.get(
        f"/share-invitations/continue?workspace_id={WORKSPACE_ID}&state={state_match.group(1)}",
        headers=recipient_headers,
    )
    assert continued.status_code == 200
    assert raw_token not in continued.text
    assert "Итоги встречи" in continued.text
    assert (
        client.get(
            f"/share-invitations/continue?workspace_id={WORKSPACE_ID}&state={state_match.group(1)}",
            headers=recipient_headers,
        ).status_code
        == 404
    )

    async def seed_second_invitation() -> str:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, seeds.ready_id)
            assert meeting is not None
            invitation = await create_share_invitation(
                db,
                workspace_id=WORKSPACE_ID,
                meeting=meeting,
                actor_user_id=USER_ID,
                device_id=DEVICE_ID,
                address=recipient_email,
                content_scope="summary_only",
                can_download=False,
                can_export=False,
                encryption_key=key,
                ttl_seconds=3600,
            )
            _, token = open_invitation_delivery(
                invitation.encrypted_delivery_address,
                key=key,
            )
            await db.commit()
            return token

    direct_raw_token = asyncio.run(seed_second_invitation())
    direct_redirect = client.get(
        f"/share-invitations/{direct_raw_token}?workspace_id={WORKSPACE_ID}",
        headers=recipient_headers,
        follow_redirects=False,
    )
    assert direct_redirect.status_code == 303
    assert direct_raw_token not in direct_redirect.headers["location"]
    direct_summary = client.get(direct_redirect.headers["location"], headers=recipient_headers)
    assert direct_summary.status_code == 200
    assert "Итоги встречи" in direct_summary.text

    api_raw_token = asyncio.run(seed_second_invitation())
    accepted = client.post(
        f"/api/v1/cabinet/share-invitations/{api_raw_token}/accept",
        params={"workspace_id": str(WORKSPACE_ID)},
        headers=recipient_headers,
    )
    assert accepted.status_code == 200
    assert raw_token not in accepted.json()["share_url"]
    resolved = client.get(accepted.json()["share_url"], headers=recipient_headers)
    assert resolved.status_code == 200
    assert set(resolved.json()) == {
        "meeting_label",
        "occurred_at",
        "duration_seconds",
        "summary_sections",
    }
    replay = client.post(
        f"/api/v1/cabinet/share-invitations/{api_raw_token}/accept",
        params={"workspace_id": str(WORKSPACE_ID)},
        headers=recipient_headers,
    )
    assert replay.status_code == 200
    assert replay.json()["share_url"] == accepted.json()["share_url"]

    form_raw_token = asyncio.run(seed_second_invitation())
    form_acceptance = client.post(
        f"/api/v1/cabinet/share-invitations/{form_raw_token}/accept",
        params={"workspace_id": str(WORKSPACE_ID)},
        headers={
            **recipient_headers,
            "Accept": "text/html",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={},
        follow_redirects=False,
    )
    assert form_acceptance.status_code == 200
    assert "location" not in form_acceptance.headers
    assert form_raw_token not in form_acceptance.text
    assert "Итоги встречи" in form_acceptance.text

    async def owner_membership() -> WorkspaceMembership | None:
        async with client.app_state["sessionmaker"]() as db:
            return await db.get(WorkspaceMembership, (WORKSPACE_ID, recipient_user_id))

    assert asyncio.run(owner_membership()) is None


def test_external_invitation_email_auth_creates_account_and_opens_summary(client, tmp_path) -> None:
    seeds = seed_cabinet_meetings(client)
    recipient_email = "new-invitee@example.com"
    key = Fernet.generate_key()
    key_path = tmp_path / "share.key"
    key_path.write_bytes(key)
    client.app.state.settings.credential_encryption_key_file = key_path

    async def seed_invitation() -> str:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, seeds.ready_id)
            assert meeting is not None
            invitation = await create_share_invitation(
                db,
                workspace_id=WORKSPACE_ID,
                meeting=meeting,
                actor_user_id=USER_ID,
                device_id=DEVICE_ID,
                address=recipient_email,
                content_scope="summary_only",
                can_download=False,
                can_export=False,
                encryption_key=key,
                ttl_seconds=3600,
            )
            _, token = open_invitation_delivery(
                invitation.encrypted_delivery_address,
                key=key,
            )
            await db.commit()
            return token

    raw_token = asyncio.run(seed_invitation())
    preview = client.get(
        f"/share-invitations/{raw_token}?workspace_id={WORKSPACE_ID}",
        headers={"Accept": "text/html"},
    )
    assert preview.status_code == 200
    state_match = re.search(r'name="state" value="([A-Za-z0-9_-]+)"', preview.text)
    assert state_match is not None
    state = state_match.group(1)
    magic_csrf_match = re.search(r'name="magic_csrf" value="([^\"]+)"', preview.text)
    assert magic_csrf_match is not None
    assert "Открыть итоги" in preview.text
    assert "Войти и открыть итоги" not in preview.text

    rejected_csrf = client.post(
        "/share-invitations/continue/magic",
        params={"workspace_id": str(WORKSPACE_ID)},
        data={"state": state, "magic_csrf": "x" * 32},
        follow_redirects=False,
    )
    assert rejected_csrf.status_code == 404

    magic = client.post(
        "/share-invitations/continue/magic",
        params={"workspace_id": str(WORKSPACE_ID)},
        data={"state": state, "magic_csrf": magic_csrf_match.group(1)},
        follow_redirects=False,
    )
    assert magic.status_code == 200
    assert "Итоги встречи" in magic.text
    assert raw_token not in magic.text
    session_cookie = magic.cookies.get(AUTH_SESSION_COOKIE_NAME)
    assert session_cookie
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, session_cookie)

    replay = client.post(
        "/share-invitations/continue/magic",
        params={"workspace_id": str(WORKSPACE_ID)},
        data={"state": state, "magic_csrf": magic_csrf_match.group(1)},
        follow_redirects=False,
    )
    assert replay.status_code == 404

    async def read_bootstrap_result() -> tuple[ExternalIdentity, WorkspaceMembership, MeetingShareGrant, MeetingShareInvitation]:
        async with client.app_state["sessionmaker"]() as db:
            identity = await db.scalar(
                select(ExternalIdentity).where(ExternalIdentity.email == recipient_email)
            )
            assert identity is not None
            assert identity.is_verified is True
            personal_membership = await db.scalar(
                select(WorkspaceMembership).where(
                    WorkspaceMembership.user_id == identity.user_id,
                    WorkspaceMembership.status == "active",
                )
            )
            assert personal_membership is not None
            owner_membership = await db.get(WorkspaceMembership, (WORKSPACE_ID, identity.user_id))
            assert owner_membership is None
            grant = await db.scalar(
                select(MeetingShareGrant).where(
                    MeetingShareGrant.workspace_id == WORKSPACE_ID,
                    MeetingShareGrant.meeting_id == seeds.ready_id,
                    MeetingShareGrant.audience_id == identity.user_id,
                    MeetingShareGrant.status == "active",
                )
            )
            assert grant is not None
            invitation = await db.scalar(
                select(MeetingShareInvitation).where(
                    MeetingShareInvitation.workspace_id == WORKSPACE_ID,
                    MeetingShareInvitation.meeting_id == seeds.ready_id,
                    MeetingShareInvitation.status == "accepted",
                )
            )
            assert invitation is not None
            return identity, personal_membership, grant, invitation

    identity, personal_membership, grant, invitation = asyncio.run(read_bootstrap_result())
    assert personal_membership.workspace_id != WORKSPACE_ID
    assert grant.content_scope == "summary_only"
    assert grant.can_download is False
    assert grant.can_export is False
    assert invitation.account_created_email_status == "failed"
    assert invitation.account_created_email_failure_code == "postal_delivery_disabled"


def test_external_full_invitation_opens_recording_package_and_rechecks_revoke(client, tmp_path) -> None:
    seeds = seed_cabinet_meetings(client)
    audio_body = add_retained_playback_m4a(client, seeds.ready_id, b"shared-recording-m4a")
    set_artifact_policy(
        client,
        seeds.ready_id,
        audio_download="allowed",
        transcript_download="allowed",
        summary_download="allowed",
        package_export="allowed",
    )
    recipient_email = "recording-invitee@example.com"
    key = Fernet.generate_key()
    key_path = tmp_path / "full-share.key"
    key_path.write_bytes(key)
    client.app.state.settings.credential_encryption_key_file = key_path

    async def seed_invitation() -> str:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, seeds.ready_id)
            assert meeting is not None
            invitation = await create_share_invitation(
                db,
                workspace_id=WORKSPACE_ID,
                meeting=meeting,
                actor_user_id=USER_ID,
                device_id=DEVICE_ID,
                address=recipient_email,
                content_scope="full_meeting",
                can_download=True,
                can_export=True,
                encryption_key=key,
                ttl_seconds=3600,
            )
            _, token = open_invitation_delivery(
                invitation.encrypted_delivery_address,
                key=key,
            )
            await db.commit()
            return token

    raw_token = asyncio.run(seed_invitation())
    preview = client.get(
        f"/share-invitations/{raw_token}?workspace_id={WORKSPACE_ID}",
        headers={"Accept": "text/html"},
    )
    assert preview.status_code == 200
    assert "Запись встречи доступна" in preview.text
    assert "Открыть запись" in preview.text
    assert "Открыть итоги" not in preview.text
    state = re.search(r'name="state" value="([A-Za-z0-9_-]+)"', preview.text)
    magic_csrf = re.search(r'name="magic_csrf" value="([^\"]+)"', preview.text)
    assert state is not None and magic_csrf is not None

    magic = client.post(
        "/share-invitations/continue/magic",
        params={"workspace_id": str(WORKSPACE_ID)},
        data={"state": state.group(1), "magic_csrf": magic_csrf.group(1)},
        follow_redirects=False,
    )
    assert magic.status_code == 303
    shared_url = magic.headers["location"]
    assert shared_url == f"/shared-meetings/{seeds.ready_id}?workspace_id={WORKSPACE_ID}"
    session_cookie = magic.cookies.get(AUTH_SESSION_COOKIE_NAME)
    assert session_cookie
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, session_cookie)

    page = client.get(shared_url, headers={"Accept": "text/html"})
    assert page.status_code == 200
    assert "Итоги" in page.text
    assert "Расшифровка" in page.text
    assert SAFE_TRANSCRIPT_TEXT in page.text
    assert f"/api/v1/cabinet/shared-meetings/{seeds.ready_id}/playback" in page.text
    assert f"/api/v1/cabinet/shared-meetings/{seeds.ready_id}/downloads/audio" in page.text
    assert f"/api/v1/cabinet/shared-meetings/{seeds.ready_id}/content-exports" in page.text
    assert 'data-media-revision-id=""' in page.text
    assert "Сведения о встрече" not in page.text

    playback = client.get(
        f"/api/v1/cabinet/shared-meetings/{seeds.ready_id}/playback",
        params={"workspace_id": str(WORKSPACE_ID)},
    )
    assert playback.status_code == 200
    assert playback.content == audio_body

    download = client.get(
        f"/api/v1/cabinet/shared-meetings/{seeds.ready_id}/downloads/audio",
        params={"workspace_id": str(WORKSPACE_ID)},
    )
    assert download.status_code == 200
    assert download.content == audio_body
    assert "attachment" in download.headers["content-disposition"]

    capabilities = client.get(
        f"/api/v1/cabinet/shared-meetings/{seeds.ready_id}/content-exports",
        params={"workspace_id": str(WORKSPACE_ID)},
    )
    assert capabilities.status_code == 200
    assert capabilities.json()["transcript"]["state"] == "available"

    async def revoke_grant() -> None:
        async with client.app_state["sessionmaker"]() as db:
            identity = await db.scalar(
                select(ExternalIdentity).where(ExternalIdentity.email == recipient_email)
            )
            assert identity is not None
            grant = await db.scalar(
                select(MeetingShareGrant).where(
                    MeetingShareGrant.workspace_id == WORKSPACE_ID,
                    MeetingShareGrant.meeting_id == seeds.ready_id,
                    MeetingShareGrant.audience_id == identity.user_id,
                    MeetingShareGrant.status == "active",
                )
            )
            meeting = await db.get(Meeting, seeds.ready_id)
            assert grant is not None and meeting is not None
            await revoke_share_grant(
                db,
                workspace_id=WORKSPACE_ID,
                meeting=meeting,
                actor_user_id=USER_ID,
                device_id=DEVICE_ID,
                grant_id=grant.id,
            )
            await db.commit()

    asyncio.run(revoke_grant())
    assert client.get(shared_url, headers={"Accept": "text/html"}).status_code == 404
    assert (
        client.get(
            f"/api/v1/cabinet/shared-meetings/{seeds.ready_id}/downloads/audio",
            params={"workspace_id": str(WORKSPACE_ID)},
        ).status_code
        == 404
    )


def test_account_created_notification_failure_cannot_break_committed_acceptance(monkeypatch) -> None:
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                settings=SimpleNamespace(email_login_delivery_enabled=True),
                temporal_client=object(),
            )
        )
    )

    async def fail_workflow_start(**_kwargs):
        raise RuntimeError("synthetic workflow outage")

    async def fail_status_update(**_kwargs):
        raise RuntimeError("synthetic status-store outage")

    monkeypatch.setattr(browser_routes, "start_account_created_email_workflow", fail_workflow_start)
    monkeypatch.setattr(
        browser_routes,
        "_mark_account_created_email_dispatch_failure",
        fail_status_update,
    )

    asyncio.run(
        browser_routes._dispatch_account_created_email(
            request,
            sessionmaker=object(),
            invitation_id=USER_ID,
            workspace_id=WORKSPACE_ID,
            organization_id=ORG_ID,
            user_id=USER_ID,
        )
    )


def test_enabled_broader_audiences_have_no_dead_share_paths(client) -> None:
    from uuid import UUID

    seeds = seed_cabinet_meetings(client)
    workspace_user_id = UUID("30000000-0000-0000-0000-000000000321")
    workspace_device_id = UUID("40000000-0000-0000-0000-000000000321")
    add_workspace_user(
        client,
        user_id=workspace_user_id,
        device_id=workspace_device_id,
    )
    settings = client.app.state.settings
    previous = (
        settings.share_workspace_audience_enabled,
        settings.share_team_audience_enabled,
        settings.share_public_links_enabled,
        settings.share_public_links_abuse_gate_approved,
    )
    settings.share_workspace_audience_enabled = True
    settings.share_team_audience_enabled = True
    settings.share_public_links_enabled = True
    settings.share_public_links_abuse_gate_approved = True
    try:
        workspace_share = client.post(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
            headers=auth_headers(),
            json={
                "audience_type": "workspace",
                "audience_id": str(WORKSPACE_ID),
                "content_scope": "summary_only",
                "can_download": False,
                "can_export": False,
            },
        )
        assert workspace_share.status_code == 201
        assert workspace_share.json()["share_url"] == f"/meetings/{seeds.ready_id}"
        assert client.get(
            workspace_share.json()["share_url"],
            headers=auth_headers_for(
                user_id=workspace_user_id,
                device_id=workspace_device_id,
            ),
        ).status_code == 200

        team_share = client.post(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
            headers=auth_headers(),
            json={
                "audience_type": "team",
                "audience_id": "50000000-0000-0000-0000-000000000321",
                "content_scope": "summary_only",
                "can_download": False,
                "can_export": False,
            },
        )
        assert team_share.status_code == 409
        assert team_share.json()["code"] == "share_team_audience_unavailable"

        full_public = client.post(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
            headers=auth_headers(),
            json={
                "audience_type": "link",
                "content_scope": "full_meeting",
                "can_download": False,
                "can_export": False,
                "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            },
        )
        assert full_public.status_code == 422
        assert full_public.json()["code"] == "public_share_scope_invalid"
    finally:
        (
            settings.share_workspace_audience_enabled,
            settings.share_team_audience_enabled,
            settings.share_public_links_enabled,
            settings.share_public_links_abuse_gate_approved,
        ) = previous


def test_public_link_resolution_does_not_depend_on_process_local_state(client) -> None:
    seeds = seed_cabinet_meetings(client)
    settings = client.app.state.settings
    previous = settings.share_public_links_enabled
    previous_abuse_gate = settings.share_public_links_abuse_gate_approved
    settings.share_public_links_enabled = True
    settings.share_public_links_abuse_gate_approved = True
    try:
        created = client.post(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
            headers=auth_headers(),
            json={
                "audience_type": "link",
                "content_scope": "summary_only",
                "can_download": False,
                "can_export": False,
                "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            },
        )
        assert created.status_code == 201
        share_url = created.json()["share_url"]

        assert client.get(share_url).status_code == 200
        assert client.get(share_url).status_code == 200
        assert client.get(share_url).status_code == 200
    finally:
        settings.share_public_links_enabled = previous
        settings.share_public_links_abuse_gate_approved = previous_abuse_gate
