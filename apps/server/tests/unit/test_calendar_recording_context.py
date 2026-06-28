from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from twobrain_rec_server.calendar.service import choose_recording_context


def test_recording_context_selects_single_current_event() -> None:
    now = datetime(2026, 7, 1, 9, 30, tzinfo=UTC)
    event = _event(starts_at=now - timedelta(minutes=30), ends_at=now + timedelta(minutes=30))

    selected, reason = choose_recording_context([event], recording_started_at=now)

    assert selected == event
    assert reason == "current_event"


def test_recording_context_uses_explicit_future_selection_only() -> None:
    now = datetime(2026, 7, 1, 9, 30, tzinfo=UTC)
    future = _event(starts_at=now + timedelta(minutes=10), ends_at=now + timedelta(hours=1))
    past = _event(starts_at=now - timedelta(hours=2), ends_at=now - timedelta(hours=1))

    selected, reason = choose_recording_context([future, past], recording_started_at=now, selected_event_id=future.id)
    past_selected, past_reason = choose_recording_context([future, past], recording_started_at=now, selected_event_id=past.id)

    assert selected == future
    assert reason == "selected_future_event"
    assert past_selected is None
    assert past_reason == "no_context"


def test_recording_context_allows_explicit_current_selection_without_looking_back() -> None:
    now = datetime(2026, 7, 1, 9, 30, tzinfo=UTC)
    current = _event(starts_at=now - timedelta(minutes=10), ends_at=now + timedelta(minutes=20))

    selected, reason = choose_recording_context([current], recording_started_at=now, selected_event_id=current.id)

    assert selected == current
    assert reason == "selected_current_event"


def test_recording_context_avoids_ambiguous_and_missing_matches() -> None:
    now = datetime(2026, 7, 1, 9, 30, tzinfo=UTC)
    events = [
        _event(starts_at=now - timedelta(minutes=10), ends_at=now + timedelta(minutes=30)),
        _event(starts_at=now - timedelta(minutes=5), ends_at=now + timedelta(minutes=25)),
    ]

    selected, reason = choose_recording_context(events, recording_started_at=now)
    none_selected, none_reason = choose_recording_context([], recording_started_at=now)

    assert selected is None
    assert reason == "ambiguous_current_events"
    assert none_selected is None
    assert none_reason == "no_context"


def test_recording_context_dedupes_same_meeting_link_before_ambiguity() -> None:
    now = datetime(2026, 7, 1, 9, 30, tzinfo=UTC)
    first = _event(
        starts_at=now - timedelta(minutes=10),
        ends_at=now + timedelta(minutes=30),
        provider_event_id="yandex-event",
        url_hash="same-link",
    )
    second = _event(
        starts_at=now - timedelta(minutes=10),
        ends_at=now + timedelta(minutes=30),
        provider_event_id="mail-ru-event",
        url_hash="same-link",
    )

    selected, reason = choose_recording_context([first, second], recording_started_at=now)

    assert selected == first
    assert reason == "current_event"


def test_recording_context_keeps_same_provider_id_from_different_sources_ambiguous() -> None:
    now = datetime(2026, 7, 1, 9, 30, tzinfo=UTC)
    first = _event(
        starts_at=now - timedelta(minutes=10),
        ends_at=now + timedelta(minutes=30),
        provider_event_id="same-event",
        calendar_source_id=uuid4(),
    )
    second = _event(
        starts_at=now - timedelta(minutes=5),
        ends_at=now + timedelta(minutes=25),
        provider_event_id="same-event",
        calendar_source_id=uuid4(),
    )

    selected, reason = choose_recording_context([first, second], recording_started_at=now)

    assert selected is None
    assert reason == "ambiguous_current_events"


def _event(
    *,
    starts_at: datetime,
    ends_at: datetime,
    provider_event_id: str | None = None,
    url_hash: str | None = None,
    calendar_source_id=None,
) -> SimpleNamespace:
    conference_summary_json = {"url_hash": url_hash} if url_hash else {}
    return SimpleNamespace(
        id=uuid4(),
        starts_at=starts_at,
        ends_at=ends_at,
        calendar_source_id=calendar_source_id,
        provider_event_id=provider_event_id,
        conference_summary_json=conference_summary_json,
    )
