from uuid import UUID

import pytest

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import WORKSPACE_ID
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.cabinet_access import SHARED_USER_ID, add_workspace_user, auth_headers_for


@pytest.mark.parametrize("embedded", [False, True])
@pytest.mark.parametrize("scope", ["full_meeting", "summary_only", "unavailable"])
def test_shared_detail_surface_hint_never_changes_access(client, embedded, scope) -> None:
    seeds = seed_cabinet_meetings(client)
    add_workspace_user(client)
    if scope != "unavailable":
        created = client.post(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
            headers=auth_headers(),
            json={
                "audience_type": "user",
                "audience_id": str(SHARED_USER_ID),
                "content_scope": scope,
                "can_download": False,
            },
        )
        assert created.status_code == 201
    headers = auth_headers_for()
    if embedded:
        headers["X-GRAF-Client"] = "desktop"
    response = client.get(
        f"/shared-meetings/{seeds.ready_id}?workspace_id={WORKSPACE_ID}", headers=headers
    )
    assert response.status_code == (404 if scope == "unavailable" else 200)
    list_path = "/desktop/meetings" if embedded else "/meetings"
    assert f'href="{list_path}"' in response.text
    if scope == "summary_only":
        assert "Вам открыли только итоги" in response.text
        assert "data-playback-player" not in response.text
    elif scope == "full_meeting":
        assert 'id="detail-panel-recording"' in response.text
        assert 'id="detail-panel-outcomes"' in response.text
    else:
        assert "Встреча больше недоступна" in response.text
    download = client.get(
        f"/api/v1/cabinet/shared-meetings/{seeds.ready_id}/downloads/audio",
        params={"workspace_id": str(WORKSPACE_ID)}, headers=headers,
    )
    assert download.status_code == (409 if scope == "full_meeting" else 404)


def test_recipient_sees_active_share_in_separate_browser_and_desktop_lists(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_workspace_user(client)
    created = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers(),
        json={
            "audience_type": "user",
            "audience_id": str(SHARED_USER_ID),
            "content_scope": "full_meeting",
            "can_download": True,
            "can_export": True,
        },
    )
    assert created.status_code == 201

    for path in ("/shared-with-me", "/desktop/shared-with-me"):
        response = client.get(path, headers=auth_headers_for())

        assert response.status_code == 200
        assert "Поделились со мной" in response.text
        assert str(seeds.ready_id) in response.text
        assert "/shared-meetings/" in response.text
        assert "Загрузить запись" not in response.text


def test_unrelated_recipient_gets_neutral_empty_shared_with_me_list(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_workspace_user(client)
    other_user_id = UUID("30000000-0000-0000-0000-000000000424")
    other_device_id = UUID("40000000-0000-0000-0000-000000000424")
    add_workspace_user(client, user_id=other_user_id, device_id=other_device_id)
    created = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers(),
        json={
            "audience_type": "user",
            "audience_id": str(other_user_id),
            "content_scope": "full_meeting",
            "can_download": True,
            "can_export": True,
        },
    )
    assert created.status_code == 201

    response = client.get("/shared-with-me", headers=auth_headers_for())

    assert response.status_code == 200
    assert "Пока нет встреч, которыми с вами поделились" in response.text


def test_revoked_share_disappears_from_recipient_list(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_workspace_user(client)
    created = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers(),
        json={
            "audience_type": "user",
            "audience_id": str(SHARED_USER_ID),
            "content_scope": "full_meeting",
        },
    )
    assert created.status_code == 201
    grant_id = created.json()["grant"]["grant_id"]

    assert client.get("/shared-with-me", headers=auth_headers_for()).status_code == 200
    revoked = client.delete(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares/{grant_id}",
        headers=auth_headers(),
    )
    assert revoked.status_code == 204

    response = client.get("/shared-with-me", headers=auth_headers_for())

    assert response.status_code == 200
    assert str(seeds.ready_id) not in response.text
    assert "Пока нет встреч, которыми с вами поделились" in response.text


def test_summary_only_share_opens_summary_from_recipient_list(client) -> None:
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

    response = client.get("/shared-with-me", headers=auth_headers_for())
    assert response.status_code == 200
    assert f"/shared-meetings/{seeds.ready_id}" in response.text

    target = client.get(
        f"/shared-meetings/{seeds.ready_id}?workspace_id={WORKSPACE_ID}",
        headers=auth_headers_for(),
    )

    assert target.status_code == 200
    assert "Проектный синк" in target.text


@pytest.mark.parametrize("source", ["known", "manual", "unknown"])
def test_shared_and_invitation_dates_use_display_truth_without_changing_transport(client, source):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from tests.fakes.auth_contexts import USER_ID
    from twobrain_rec_server.cabinet.access import hash_share_token, share_invitation_preview
    from twobrain_rec_server.cabinet.rendering import render_share_invitation_accept_page
    from twobrain_rec_server.cabinet.user_time import _display_timezone
    from twobrain_rec_server.db.models import MediaRevision, Meeting, MeetingShareInvitation

    seeds = seed_cabinet_meetings(client)
    add_workspace_user(client)
    client.cookies.set("graf_timezone", "Asia/Yekaterinburg")
    instant = datetime(2026, 9, 5, 21, 30, tzinfo=UTC)
    receipt = datetime(2026, 9, 6, 21, 30, tzinfo=UTC)
    raw_token = "synthetic-f252-invitation-token"

    async def seed_preview():
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, seeds.ready_id)
            meeting.started_at = instant if source == "known" else None
            meeting.created_at = receipt
            meeting.recording_display_timezone_offset_minutes = -420
            meeting.title = "Meeting - 2026-09-05 21:30"
            meeting.title_source = "generic"
            revision = await db.scalar(select(MediaRevision).where(MediaRevision.meeting_id == meeting.id).order_by(MediaRevision.revision_number.desc()).limit(1))
            assert revision is not None
            if source == "manual":
                revision.source_kind = "manual_upload"
            db.add(MeetingShareInvitation(
                workspace_id=WORKSPACE_ID, meeting_id=meeting.id, invited_by_user_id=USER_ID,
                normalized_address_hash="synthetic-f252-hash", encrypted_delivery_address="synthetic-ciphertext",
                token_hash=hash_share_token(raw_token), status="pending", expires_at=datetime.now(UTC)+timedelta(days=2),
            ))
            await db.commit()
            preview = await share_invitation_preview(db, workspace_id=WORKSPACE_ID, raw_token=raw_token)
            assert preview is not None
            assert preview.occurred_at == (instant if source == "known" else receipt)
            assert preview.display_occurred_at == (None if source == "unknown" else instant if source == "known" else receipt)
            return preview
    preview = client.portal.call(seed_preview)
    token = _display_timezone.set("Asia/Yekaterinburg")
    try:
        invitation_html = render_share_invitation_accept_page(
            share_token=raw_token, workspace_id=str(WORKSPACE_ID), csrf_token=None,
            meeting_title=preview.meeting_title, meeting_occurred_at=preview.display_occurred_at,
            meeting_time_is_upload=preview.display_time_is_upload,
            meeting_duration_seconds=preview.duration_seconds, invitation_expires_at=preview.expires_at,
        )
    finally:
        _display_timezone.reset(token)
    created = client.post(f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares", headers=auth_headers(), json={"audience_type":"user", "audience_id":str(SHARED_USER_ID), "content_scope":"summary_only"})
    assert created.status_code == 201
    shared = client.get(f"/shared-meetings/{seeds.ready_id}?workspace_id={WORKSPACE_ID}", headers=auth_headers_for())
    assert shared.status_code == 200
    for html in (shared.text, invitation_html):
        assert "Meeting - 2026-09-05 21:30" not in html
        if source == "unknown":
            assert "Без даты" in html
            assert "07.09.2026, 02:30" not in html
            assert "Загружено" not in html
        else:
            assert ("06.09.2026, 02:30" if source == "known" else "07.09.2026, 02:30") in html
            assert "data-user-datetime" in html
            assert ("Загружено" in html) == (source == "manual")
