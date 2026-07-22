import asyncio
from datetime import UTC, datetime, timedelta

from cryptography.fernet import Fernet

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.cabinet_access import (
    SHARED_USER_ID,
    add_workspace_user,
    auth_headers_for,
    set_artifact_policy,
)
from twobrain_rec_server.cabinet.access import (
    create_share_invitation,
    open_invitation_delivery,
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
    settings.share_public_links_enabled = True
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
    settings.share_public_links_enabled = True
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
                ttl_seconds=-1,
            )
            await db.commit()
            replacement = await create_share_invitation(
                db,
                workspace_id=WORKSPACE_ID,
                meeting=meeting,
                actor_user_id=USER_ID,
                device_id=DEVICE_ID,
                address="invitee@example.com",
                content_scope="full_meeting",
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
            return first_expired, replacement, after_revoke

    first_expired, replacement, after_revoke = asyncio.run(exercise_cycles())
    assert first_expired.status == "expired"
    assert first_expired.encrypted_delivery_address == ""
    assert replacement.status == "revoked"
    assert replacement.encrypted_delivery_address == ""
    assert len({first_expired.id, replacement.id, after_revoke.id}) == 3
    assert after_revoke.status == "pending"


def test_external_invitation_accepts_from_another_workspace_and_resolves_share(client) -> None:
    from uuid import UUID

    seeds = seed_cabinet_meetings(client)
    recipient_user_id = UUID("30000000-0000-0000-0000-000000000221")
    recipient_workspace_id = UUID("20000000-0000-0000-0000-000000000221")
    recipient_device_id = UUID("40000000-0000-0000-0000-000000000221")
    recipient_email = "external-invitee@example.com"

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
            db.add(
                MeetingShareGrant(
                    workspace_id=WORKSPACE_ID,
                    meeting_id=meeting.id,
                    grant_type="user",
                    grantee_user_id=recipient_user_id,
                    audience_type="user",
                    audience_id=recipient_user_id,
                    content_scope="full_meeting",
                    can_download=True,
                    can_export=True,
                    created_by_user_id=USER_ID,
                    status="active",
                    metadata_json={"source": "preexisting_test_grant"},
                )
            )
            key = Fernet.generate_key()
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
    recipient_headers = auth_headers_for(
        user_id=recipient_user_id,
        device_id=recipient_device_id,
        workspace_id=recipient_workspace_id,
    )
    accepted = client.post(
        f"/api/v1/cabinet/share-invitations/{raw_token}/accept",
        params={"workspace_id": str(WORKSPACE_ID)},
        headers=recipient_headers,
    )
    assert accepted.status_code == 200
    resolved = client.get(accepted.json()["share_url"], headers=recipient_headers)
    assert resolved.status_code == 200
    assert set(resolved.json()) == {
        "meeting_label",
        "occurred_at",
        "duration_seconds",
        "summary_sections",
    }


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
    )
    settings.share_workspace_audience_enabled = True
    settings.share_team_audience_enabled = True
    settings.share_public_links_enabled = True
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
        ) = previous


def test_public_link_resolution_does_not_depend_on_process_local_state(client) -> None:
    seeds = seed_cabinet_meetings(client)
    settings = client.app.state.settings
    previous = settings.share_public_links_enabled
    settings.share_public_links_enabled = True
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
