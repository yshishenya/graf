from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from twobrain_rec_server.calendar.credentials import generate_credential_key
from twobrain_rec_server.calendar.owner_content import (
    OWNER_CONTENT_ENVELOPE_KEY,
    attach_owner_content,
    owner_event_content,
    owner_event_title,
    plaintext_owner_text,
    seal_owner_event_content,
)
from twobrain_rec_server.db.models import CalendarEventSnapshot


def content_fixture():
    return SimpleNamespace(
        title="Встреча owner@example.test " + "Д" * 800,
        description="Описание " * 900 + " https://zoom.us/j/123?pwd=synthetic-passcode",
        location="Код доступа: synthetic-code; кабинет 5",
        participants=[{"display_name": "Имя " * 200, "email": "owner@example.test"}],
        attachments_metadata=[
            {"title": "Материал", "fileUrl": "https://example.test/file?token=synthetic"}
        ],
        provider_extras={"provider_note": "https://example.test/private"},
        conference_links=[{"open_url": "https://example.test/meeting?pwd=synthetic"}],
    )


def test_owner_content_roundtrip_preserves_long_private_fields_without_orm_mutation():
    original = content_fixture()
    key = generate_credential_key()
    sealed = seal_owner_event_content(original, key)
    assert original.title not in sealed
    now = datetime.now(UTC)
    event = CalendarEventSnapshot(
        id=uuid4(),
        title=original.title,
        description=None,
        location=None,
        starts_at=now,
        ends_at=now + timedelta(hours=1),
        privacy_class="private",
        provider_extras_json={OWNER_CONTENT_ENVELOPE_KEY: sealed},
    )
    before = {
        name: getattr(event, name)
        for name in ("title", "description", "location", "provider_extras_json")
    }
    attach_owner_content([event], key)
    content = owner_event_content(event)
    assert content["title"] == original.title
    assert content["description"] == original.description
    assert content["location"] == original.location
    assert content["participants"] == original.participants
    assert content["attachments"] == original.attachments_metadata
    assert content["provider_extras"] == original.provider_extras
    assert content["conference_links"] == original.conference_links
    assert owner_event_title(event) == original.title
    assert before == {name: getattr(event, name) for name in before}
    assert "_owner_calendar_content" not in inspect(event).mapper.attrs


def test_wrong_or_absent_key_never_exposes_encrypted_content():
    event = SimpleNamespace(
        title=None,
        description=None,
        location=None,
        provider_extras_json={
            OWNER_CONTENT_ENVELOPE_KEY: seal_owner_event_content(
                content_fixture(), generate_credential_key()
            )
        },
    )
    assert owner_event_content(event, generate_credential_key())["description"] is None
    assert owner_event_title(event) is None


@pytest.mark.parametrize(
    "text",
    [
        "https://example.test/path",
        "www.example.test/path",
        "Код доступа: synthetic",
        "Код встречи 12345",
        "Access code: synthetic",
        "Password: synthetic",
        "passcode=synthetic",
        "Пароль 12345",
    ],
)
def test_sensitive_text_has_no_plaintext_projection(text):
    assert plaintext_owner_text(text) is None


def test_ordinary_text_and_email_are_lossless():
    text = "  Встреча owner@example.test " + "Я" * 1200
    assert plaintext_owner_text(text) == text


def test_owner_api_private_title_available_and_user_setting_still_hides_title():
    from twobrain_rec_server.api.calendar import _event_summary

    original = content_fixture()
    key = generate_credential_key()
    now = datetime.now(UTC)
    event = CalendarEventSnapshot(
        id=uuid4(),
        title=None,
        description=None,
        location=None,
        starts_at=now,
        ends_at=now + timedelta(hours=1),
        privacy_class="private",
        all_day=True,
        safe_to_show_in_list=False,
        provider_extras_json={OWNER_CONTENT_ENVELOPE_KEY: seal_owner_event_content(original, key)},
    )
    summary = _event_summary(event, credential_encryption_key=key)
    assert summary.all_day is True
    assert summary.title == original.title
    assert summary.title_state == "available"
    assert summary.description == original.description
    assert summary.location == original.location
    assert summary.participants == original.participants
    assert summary.attachments == original.attachments_metadata
    assert summary.conference_links == original.conference_links
    assert summary.provider_extras == original.provider_extras
    hidden = _event_summary(event, show_title=False, credential_encryption_key=key)
    assert hidden.title is None
    assert hidden.title_state == "policy_hidden"


def test_missing_title_is_not_reported_as_graf_redaction():
    from twobrain_rec_server.api.calendar import _event_summary

    now = datetime.now(UTC)
    event = CalendarEventSnapshot(
        id=uuid4(),
        title=None,
        description=None,
        location=None,
        starts_at=now,
        ends_at=now + timedelta(hours=1),
        provider_extras_json={"title_state": "unknown"},
        privacy_class="private",
    )
    summary = _event_summary(event)
    assert summary.title is None
    assert summary.title_state == "available"


def test_owner_private_title_does_not_grant_shared_recording_context():
    from twobrain_rec_server.calendar.matching import is_safe_calendar_context_candidate

    original = content_fixture()
    key = generate_credential_key()
    now = datetime.now(UTC)
    event = CalendarEventSnapshot(
        id=uuid4(),
        title=original.title,
        starts_at=now,
        ends_at=now + timedelta(hours=1),
        privacy_class="private",
        safe_to_show_in_list=True,
        safe_to_use_as_title=True,
        provider_extras_json={OWNER_CONTENT_ENVELOPE_KEY: seal_owner_event_content(original, key)},
    )
    attach_owner_content([event], key)
    assert owner_event_title(event) == original.title
    assert not is_safe_calendar_context_candidate(event, participant_count=1)


@pytest.mark.asyncio
@pytest.mark.parametrize("key", [None, b"", b"invalid-key"])
async def test_snapshot_refuses_missing_or_invalid_key_before_any_database_action(key):
    from unittest.mock import AsyncMock

    from twobrain_rec_server.calendar.sync import upsert_event_snapshot

    db = AsyncMock()
    with pytest.raises(ValueError):
        await upsert_event_snapshot(db, None, None, None, None, credential_encryption_key=key)
    db.scalar.assert_not_called()
    db.add.assert_not_called()
    db.flush.assert_not_called()


def test_owner_all_day_date_is_not_shifted_by_display_timezone():
    from datetime import UTC, datetime

    from twobrain_rec_server.cabinet.rendering import _home_upcoming_time_label
    start = datetime(2026, 9, 6, tzinfo=UTC)
    assert _home_upcoming_time_label(start, "America/Los_Angeles", all_day=True) == "06.09.2026, весь день"
    assert _home_upcoming_time_label(start, "Asia/Yekaterinburg", all_day=True) == "06.09.2026, весь день"
