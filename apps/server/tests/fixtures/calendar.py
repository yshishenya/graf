from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

BASE_START = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)

PROVIDER_CASES = (
    "caldav_yandex",
    "caldav_mail_ru",
    "google_calendar",
    "microsoft_graph",
    "exchange_ews",
    "bitrix24",
    "custom_caldav_vk_workspace",
    "caldav_mailion_myoffice",
    "caldav_r7_office",
    "caldav_communigate_pro",
    "caldav_rupost",
    "caldav_nextcloud_sogo",
)


def calendar_event_fixture(provider_family: str = "caldav_yandex", **overrides: Any) -> dict[str, Any]:
    start = overrides.pop("starts_at", BASE_START)
    event: dict[str, Any] = {
        "provider_family": provider_family,
        "provider_account_id": f"{provider_family}-account",
        "provider_calendar_id": f"{provider_family}-calendar",
        "provider_event_id": f"{provider_family}-event",
        "ical_uid": f"{provider_family}-uid@example.test",
        "source_version": "etag-1",
        "source_status": "confirmed",
        "starts_at": start,
        "ends_at": start + timedelta(hours=1),
        "timezone": "UTC",
        "all_day": False,
        "floating_time": False,
        "title": "Synthetic Planning Sync",
        "title_state": "available",
        "description_state": "available",
        "location": "Synthetic Room",
        "privacy_class": "public",
        "participants": [
            participant_fixture("organizer", email="organizer@example.test", response_status="organizer"),
            participant_fixture("required_attendee", email="attendee@example.test", response_status="accepted"),
        ],
        "conference_links": [
            {
                "provider_family": "generic",
                "source_field": "location",
                "url_hash": "sha256:calendar-link",
                "redacted_url_preview": "meet.example.test/...",
                "contains_passcode": False,
                "sensitivity_class": "meeting_link",
            }
        ],
        "provider_extras": {"raw_payload_retained": False},
        "limitation_states": {},
    }
    event.update(overrides)
    return event


def participant_fixture(
    participant_kind: str,
    *,
    email: str | None = "person@example.test",
    response_status: str = "needs_action",
    workspace_relation: str = "external",
    recipient_candidate_class: str | None = None,
) -> dict[str, Any]:
    return {
        "participant_kind": participant_kind,
        "response_status": response_status,
        "email": email,
        "email_hash": "sha256:synthetic-email" if email else None,
        "display_name": "Synthetic Person" if email else None,
        "workspace_relation": workspace_relation,
        "recipient_candidate_class": recipient_candidate_class or workspace_relation,
    }


def provider_fixture_matrix() -> list[dict[str, Any]]:
    return [calendar_event_fixture(provider) for provider in PROVIDER_CASES]


def private_free_busy_event_fixture(provider_family: str = "caldav_yandex") -> dict[str, Any]:
    return calendar_event_fixture(
        provider_family,
        source_status="free_busy_only",
        title=None,
        title_state="free_busy_only",
        description_state="private_redacted",
        location=None,
        privacy_class="free_busy_only",
        participants=[],
        conference_links=[],
        limitation_states={
            "title": "free_busy_only",
            "participants": "private_redacted",
            "conference_links": "private_redacted",
        },
    )


def attendee_heavy_event_fixture(count: int = 25) -> dict[str, Any]:
    participants = [
        participant_fixture(
            "required_attendee",
            email=f"attendee-{index}@example.test",
            response_status="needs_action",
            workspace_relation="external",
        )
        for index in range(count)
    ]
    return calendar_event_fixture("google_calendar", participants=participants)


def recurrence_exception_fixture(provider_family: str = "exchange_ews") -> dict[str, Any]:
    return calendar_event_fixture(
        provider_family,
        recurring_series_id="series-1",
        recurrence_instance_id="series-1-20260701T090000Z",
        original_start=BASE_START - timedelta(days=1),
        recurrence_rule={"freq": "weekly", "count": 4},
        recurrence_exceptions=[{"original_start": (BASE_START - timedelta(days=1)).isoformat(), "state": "moved"}],
    )


def clone_calendar_event(event: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    cloned = deepcopy(event)
    cloned.update(overrides)
    return cloned
