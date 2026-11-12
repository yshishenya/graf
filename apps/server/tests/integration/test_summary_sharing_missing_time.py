"""F292/T038: required transport date and truthful saved-summary HTML metadata."""

import asyncio
import re
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.cabinet_access import SHARED_USER_ID, add_workspace_user, auth_headers_for
from tests.integration.test_meeting_sharing_parity import publish
from tests.integration.test_summary_sharing import prepare
from twobrain_rec_server.cabinet.access import create_share_invitation, open_invitation_delivery
from twobrain_rec_server.db.models import (
    ExternalIdentity,
    MediaRevision,
    Meeting,
    MeetingShareGrant,
)
from twobrain_rec_server.workflows.summary_delivery import deliver_summary_batch

CREATED = datetime(2026, 7, 10, 13, 25, tzinfo=UTC)
STARTED = CREATED - timedelta(hours=1)


def set_metadata(client, meeting_id, source):
    async def update():
        async with client.app.state.db_sessionmaker() as db:
            meeting = await db.get(Meeting, meeting_id)
            meeting.started_at = STARTED if source == "known" else None
            meeting.created_at = CREATED
            meeting.title, meeting.title_source = "Published synthetic meeting", "user_confirmed"
            revision = await db.scalar(
                select(MediaRevision)
                .where(MediaRevision.meeting_id == meeting_id)
                .order_by(MediaRevision.revision_number.desc())
                .limit(1)
            )
            assert revision is not None
            if source == "manual":
                revision.source_kind = "manual_upload"
            await db.commit()

    asyncio.run(update())


def test_new_summary_and_owner_preview_with_unknown_recording_time(client, tmp_path):
    meeting, template = prepare(client, tmp_path)
    set_metadata(client, meeting, "unknown")
    base = f"/api/v1/cabinet/meetings/{meeting}/summary-sharing"
    preview = client.get(
        base + "/preview", params={"template_key": template}, headers=auth_headers()
    )
    assert preview.status_code == 200, preview.text
    assert datetime.fromisoformat(preview.json()["projection"]["occurred_at"]) == CREATED
    link, path = publish(client, meeting, template, "summary_only")
    projection = client.get(path).json()
    assert {**projection, "occurred_at": datetime.fromisoformat(projection["occurred_at"])} == {
        **link["summary"]["projection"],
        "occurred_at": CREATED,
    }
    assert datetime.fromisoformat(projection["occurred_at"]) == CREATED
    assert not {"transcript", "speakers", "media_version", "playback_available"} & projection.keys()
    html = client.get(path, headers={"Accept": "text/html"})
    assert html.status_code == 200
    assert "data-user-datetime" not in html.text
    assert (
        client.get(path.replace("?", "/playback?", 1) + "&media_version=" + "0" * 24).status_code
        == 404
    )


@pytest.mark.parametrize("days", [7, 30, 90])
def test_expired_full_to_summary_without_recording_time(client, tmp_path, days):
    meeting, template = prepare(client, tmp_path)
    set_metadata(client, meeting, "unknown")
    link, path = publish(client, meeting, template)

    async def expire():
        async with client.app.state.db_sessionmaker() as db:
            grant = await db.get(MeetingShareGrant, UUID(link["grant_id"]))
            grant.expires_at = datetime.now(UTC) - timedelta(days=1)
            await db.commit()

    asyncio.run(expire())
    assert client.get(path).status_code == 404
    base = f"/api/v1/cabinet/meetings/{meeting}/sharing/general-access"
    before = client.get(base, headers=auth_headers()).json()
    now = datetime.now(UTC)
    resumed = client.post(
        base,
        headers=auth_headers(),
        json={
            "audience": "link",
            "content_scope": "summary_only",
            "template_key": template,
            "expected_fingerprint": before["fingerprint"],
            "expires_in_days": days,
        },
    )
    assert resumed.status_code == 200, resumed.text
    current = resumed.json()
    assert current["content_scope"] == "summary_only"
    assert current["link"]["share_url"] == link["share_url"]
    assert (
        now + timedelta(days=days)
        <= datetime.fromisoformat(current["link"]["expires_at"])
        <= datetime.now(UTC) + timedelta(days=days)
    )
    projection = client.get(path).json()
    assert {**projection, "occurred_at": datetime.fromisoformat(projection["occurred_at"])} == {
        **current["link"]["summary"]["projection"],
        "occurred_at": CREATED,
    }
    assert datetime.fromisoformat(projection["occurred_at"]) == CREATED
    assert not {"transcript", "speakers", "media_version", "playback_available"} & projection.keys()
    assert "data-user-datetime" not in client.get(path, headers={"Accept": "text/html"}).text
    assert (
        client.get(path.replace("?", "/playback?", 1) + "&media_version=" + "0" * 24).status_code
        == 404
    )


@pytest.mark.parametrize("source", ["unknown", "known", "manual"])
def test_saved_summary_metadata_across_all_html_entry_points(client, tmp_path, source):
    meeting, template = prepare(client, tmp_path)
    set_metadata(client, meeting, source)
    add_workspace_user(client)
    link, public_path = publish(client, meeting, template, "summary_only")
    projection = link["summary"]["projection"]
    grant_response = client.post(
        f"/api/v1/cabinet/meetings/{meeting}/shares",
        headers=auth_headers(),
        json={
            "audience_type": "user",
            "audience_id": str(SHARED_USER_ID),
            "content_scope": "summary_only",
        },
    )
    assert grant_response.status_code == 201, grant_response.text
    grant_id = UUID(grant_response.json()["grant"]["grant_id"])
    grant_token = "synthetic-t038-recipient-grant-token"

    async def seed_recipient():
        from twobrain_rec_server.cabinet.access import hash_share_token

        async with client.app.state.db_sessionmaker() as db:
            grant = await db.get(MeetingShareGrant, grant_id)
            grant.published_summary_id = UUID(link["summary"]["published_summary_id"])
            grant.share_token_hash = hash_share_token(grant_token)
            db.add(
                ExternalIdentity(
                    user_id=SHARED_USER_ID,
                    provider="email",
                    provider_subject="reader-t038@example.test",
                    email="reader-t038@example.test",
                    is_verified=True,
                    is_active=True,
                )
            )
            row = await db.get(Meeting, meeting)
            invitation = await create_share_invitation(
                db,
                workspace_id=WORKSPACE_ID,
                meeting=row,
                actor_user_id=USER_ID,
                device_id=DEVICE_ID,
                address="reader-t038@example.test",
                content_scope="summary_only",
                can_download=False,
                can_export=False,
                encryption_key=client.app.state.settings.credential_encryption_key_file.read_bytes().strip(),
                ttl_seconds=3600,
            )
            invitation.published_summary_id = grant.published_summary_id
            invitation.read_expires_at = datetime.now(UTC) + timedelta(days=30)
            _, token = open_invitation_delivery(
                invitation.encrypted_delivery_address,
                key=client.app.state.settings.credential_encryption_key_file.read_bytes().strip(),
            )
            await db.commit()
            return token

    invitation_token = asyncio.run(seed_recipient())
    batch = client.post(
        f"/api/v1/cabinet/meetings/{meeting}/summary-sharing/batches",
        headers=auth_headers(),
        json={
            "template_key": template,
            "recipients": ["reader-t038@example.test"],
            "idempotency_key": "t038-saved",
        },
    )
    assert batch.status_code == 200, batch.text
    sender = AsyncMock()
    sender.send_summary_delivery.return_value = "synthetic-t038-message"
    asyncio.run(
        deliver_summary_batch(
            client.app.state.db_sessionmaker,
            settings=client.app.state.settings,
            workspace_id=WORKSPACE_ID,
            batch_id=UUID(batch.json()["batch_id"]),
            mail_client=sender,
        )
    )
    sender.send_summary_delivery.assert_awaited_once()
    delivery_path = sender.send_summary_delivery.call_args.kwargs["read_url"].replace(
        "https://graf.example.test", ""
    )
    assert "/summary-sharing/received/" in delivery_path

    async def rename_current():
        async with client.app.state.db_sessionmaker() as db:
            row = await db.get(Meeting, meeting)
            row.title = "Changed after publication"
            if source == "known":
                row.started_at = STARTED + timedelta(hours=5)
            await db.commit()

    asyncio.run(rename_current())
    headers = {**auth_headers_for(), "Accept": "text/html"}
    pages = [
        client.get(public_path, headers={"Accept": "text/html"}),
        client.get(
            f"/api/v1/cabinet/share/{grant_token}?workspace_id={WORKSPACE_ID}", headers=headers
        ),
        client.get(f"/shared-meetings/{meeting}?workspace_id={WORKSPACE_ID}", headers=headers),
        client.get(f"/meetings/{meeting}", headers=headers),
        client.get(delivery_path, headers=headers),
        client.post(
            f"/api/v1/cabinet/share-invitations/{invitation_token}/accept?workspace_id={WORKSPACE_ID}",
            headers=headers,
            data={"accept": "true"},
        ),
    ]
    expected = STARTED if source == "known" else CREATED
    for page in pages:
        assert page.status_code == 200, page.text
        assert "Published synthetic meeting" in page.text
        assert "Changed after publication" not in page.text
        assert "data-playback-player" not in page.text
        dates = re.findall(r'<time datetime="([^"]+)" data-user-datetime', page.text)
        if source == "unknown":
            assert not dates
        else:
            assert dates
            assert all(datetime.fromisoformat(value) == expected for value in dates)
        assert ("Загружено" in page.text) == (source == "manual")
    transport = client.get(public_path).json()
    assert {**transport, "occurred_at": datetime.fromisoformat(transport["occurred_at"])} == {
        **projection,
        "occurred_at": expected,
    }
    assert (
        client.get(delivery_path, headers=auth_headers_for()).json()
        == batch.json()["summary"]["projection"]
    )
