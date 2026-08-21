from __future__ import annotations

import asyncio
import re

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.cabinet_access import (
    add_workspace_user,
    auth_headers_for,
    set_meeting_visibility,
)
from tests.integration.test_cabinet_csrf import (
    OWNER_REVIEW_TEST_TOKEN,
    _seed_owner_review_session,
)
from twobrain_rec_server.auth.csrf import issue_csrf_token
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    MeetingSpeakerName,
    ProcessingAuditEvent,
)
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY


def test_owner_can_set_reload_and_clear_meeting_speaker_name(client) -> None:
    meeting_id = seed_cabinet_meetings(client).ready_id
    stable_key = _renameable_speaker_keys(client, meeting_id, auth_headers())[0]
    path = f"/meetings/{meeting_id}/speakers/{stable_key}"

    saved = client.post(
        path,
        headers=auth_headers(),
        data={"display_name": "  Мария  "},
        follow_redirects=False,
    )

    assert saved.status_code == 303
    assert saved.headers["location"] == f"/meetings/{meeting_id}"
    browser = client.get(f"/meetings/{meeting_id}", headers=auth_headers())
    embedded = client.get(f"/desktop/meetings/{meeting_id}", headers=auth_headers())
    assert 'value="Мария"' in browser.text
    assert f'data-speaker-key="{stable_key}"' in browser.text
    assert 'value="Мария"' in embedded.text

    row, audits = asyncio.run(_speaker_name_state(client, meeting_id))
    assert row is not None
    assert row.speaker_key == stable_key
    assert row.display_name == "Мария"
    assert audits[-1].event_type == "speaker_display_name_set"
    assert audits[-1].metadata_json == {"speaker_key": stable_key}
    assert "Мария" not in str(audits[-1].metadata_json)

    asyncio.run(_swap_provider_speaker_labels(client, meeting_id))
    reordered = client.get(f"/meetings/{meeting_id}", headers=auth_headers())
    assert _renameable_keys_from_html(reordered.text)[1] == stable_key
    assert 'value="Мария"' in reordered.text

    legacy = client.post(
        f"/meetings/{meeting_id}/speakers/speaker_00",
        headers=auth_headers(),
        data={"display_name": "Другое имя"},
        follow_redirects=False,
    )
    assert legacy.status_code == 404
    row, _audits = asyncio.run(_speaker_name_state(client, meeting_id))
    assert row is not None
    assert row.speaker_key == stable_key
    assert row.display_name == "Мария"

    cleared = client.post(
        path,
        headers=auth_headers(),
        data={"display_name": ""},
        follow_redirects=False,
    )
    assert cleared.status_code == 303
    row, audits = asyncio.run(_speaker_name_state(client, meeting_id))
    assert row is None
    assert audits[-1].event_type == "speaker_display_name_cleared"


def test_viewer_cannot_rename_and_invalid_names_fail_closed(client) -> None:
    meeting_id = seed_cabinet_meetings(client).ready_id
    set_meeting_visibility(client, meeting_id, "team")
    add_workspace_user(client)
    stable_key = _renameable_speaker_keys(client, meeting_id, auth_headers())[0]
    path = f"/meetings/{meeting_id}/speakers/{stable_key}"

    viewer_page = client.get(f"/meetings/{meeting_id}", headers=auth_headers_for())
    denied = client.post(
        path,
        headers=auth_headers_for(),
        data={"display_name": "Viewer rename"},
        follow_redirects=False,
    )
    invalid = client.post(
        path,
        headers=auth_headers(),
        data={"display_name": "<script>"},
        follow_redirects=False,
    )

    assert viewer_page.status_code == 200
    assert "data-speaker-name-form" not in viewer_page.text
    assert denied.status_code == 404
    assert invalid.status_code == 422
    row, _audits = asyncio.run(_speaker_name_state(client, meeting_id))
    assert row is None


def test_workspace_admin_can_rename_team_visible_speaker(client) -> None:
    meeting_id = seed_cabinet_meetings(client).ready_id
    set_meeting_visibility(client, meeting_id, "team")
    add_workspace_user(client, role="admin")
    stable_key = _renameable_speaker_keys(client, meeting_id, auth_headers_for())[0]

    saved = client.post(
        f"/meetings/{meeting_id}/speakers/{stable_key}",
        headers=auth_headers_for(),
        data={"display_name": "Администратор"},
        follow_redirects=False,
    )
    page = client.get(f"/meetings/{meeting_id}", headers=auth_headers_for())

    assert saved.status_code == 303
    assert "data-speaker-name-form" in page.text
    assert 'value="Администратор"' in page.text


def test_cookie_authenticated_speaker_rename_requires_session_csrf(client) -> None:
    meeting_id = seed_cabinet_meetings(client).ready_id
    stable_key = _renameable_speaker_keys(client, meeting_id, auth_headers())[0]
    session = client.portal.call(_seed_owner_review_session, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)
    path = f"/meetings/{meeting_id}/speakers/{stable_key}"

    missing = client.post(path, data={"display_name": "Мария"}, follow_redirects=False)
    accepted = client.post(
        path,
        headers={
            "X-CSRF-Token": issue_csrf_token(
                session_id=session.id,
                secret=str(client.app.state.web_csrf_secret),
            )
        },
        data={"display_name": "Мария"},
        follow_redirects=False,
    )

    assert missing.status_code == 403
    assert missing.json()["code"] == "csrf_token_missing"
    assert accepted.status_code == 303


def test_meeting_deletion_purges_speaker_name_override(client) -> None:
    meeting_id = seed_cabinet_meetings(client).ready_id
    stable_key = _renameable_speaker_keys(client, meeting_id, auth_headers())[0]
    saved = client.post(
        f"/meetings/{meeting_id}/speakers/{stable_key}",
        headers=auth_headers(),
        data={"display_name": "Мария"},
        follow_redirects=False,
    )
    deleted = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )
    row, _audits = asyncio.run(_speaker_name_state(client, meeting_id))

    assert saved.status_code == 303
    assert deleted.status_code == 202
    assert row is None


def test_unknown_provider_identity_cannot_be_renamed(client) -> None:
    meeting_id = seed_cabinet_meetings(client).ready_id
    asyncio.run(_set_first_provider_speaker_label(client, meeting_id, "UNKNOWN"))

    page = client.get(f"/meetings/{meeting_id}", headers=auth_headers())
    unknown_key = re.search(r'data-speaker-key="(unknown:[^"]+)"', page.text)

    assert page.status_code == 200
    assert "Спикер не определён" in page.text
    assert unknown_key is not None
    assert unknown_key.group(1) not in _renameable_keys_from_html(page.text)

    denied = client.post(
        f"/meetings/{meeting_id}/speakers/{unknown_key.group(1)}",
        headers=auth_headers(),
        data={"display_name": "Неизвестный"},
        follow_redirects=False,
    )
    assert denied.status_code == 404
    row, _audits = asyncio.run(_speaker_name_state(client, meeting_id))
    assert row is None


def _renameable_speaker_keys(client, meeting_id, headers: dict[str, str]) -> list[str]:
    page = client.get(f"/meetings/{meeting_id}", headers=headers)
    assert page.status_code == 200
    keys = _renameable_keys_from_html(page.text)
    assert keys
    return keys


def _renameable_keys_from_html(html: str) -> list[str]:
    return re.findall(
        r'<form[^>]+data-speaker-name-form[^>]+data-speaker-key="([^"]+)"',
        html,
    )


async def _set_first_provider_speaker_label(client, meeting_id, label: str) -> None:
    async with client.app_state["sessionmaker"]() as db:
        row = await db.scalar(
            select(DiarizationSegment)
            .where(DiarizationSegment.meeting_id == meeting_id)
            .order_by(DiarizationSegment.sequence)
        )
        assert row is not None
        row.speaker_label = label
        await db.commit()


async def _swap_provider_speaker_labels(client, meeting_id) -> None:
    async with client.app_state["sessionmaker"]() as db:
        rows = (
            await db.scalars(
                select(DiarizationSegment)
                .where(DiarizationSegment.meeting_id == meeting_id)
                .order_by(DiarizationSegment.sequence)
            )
        ).all()
        assert len(rows) == 2
        rows[0].speaker_label, rows[1].speaker_label = (
            rows[1].speaker_label,
            rows[0].speaker_label,
        )
        await db.commit()


async def _speaker_name_state(client, meeting_id):
    async with client.app_state["sessionmaker"]() as db:
        row = await db.scalar(
            select(MeetingSpeakerName).where(MeetingSpeakerName.meeting_id == meeting_id)
        )
        audits = (
            await db.scalars(
                select(ProcessingAuditEvent)
                .where(ProcessingAuditEvent.meeting_id == meeting_id)
                .where(ProcessingAuditEvent.event_type.like("speaker_display_name_%"))
                .order_by(ProcessingAuditEvent.created_at)
            )
        ).all()
        return row, audits
