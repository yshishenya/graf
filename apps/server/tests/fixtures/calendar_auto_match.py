from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from tests.fixtures.calendar import calendar_event_fixture, participant_fixture

# Test-fixture limits mirror the feature design boundary. Production code must
# own and enforce its own limits.
FIXTURE_MAX_SOURCES = 4
FIXTURE_MAX_EVENTS = 50
FIXTURE_MAX_VISIBLE_CANDIDATES = 10
FIXTURE_MAX_ROSTER_ITEMS = 100

FIXTURE_RECORDING_STARTED_AT = datetime(2026, 7, 13, 9, 0, tzinfo=UTC)
FIXTURE_EVALUATED_AT = FIXTURE_RECORDING_STARTED_AT + timedelta(seconds=2)

_SYNTHETIC_OWNER_IDENTITY = "owner@example.test"
_SYNTHETIC_WORKSPACE_ID = "workspace-098"


def calendar_auto_match_source_fixture(
    *,
    source_id: str = "source-primary",
    external_calendar_id: str = "calendar-primary",
    provider_family: str = "caldav_yandex",
    owner_identity: str = _SYNTHETIC_OWNER_IDENTITY,
    sync_state: str = "synced",
    last_successful_sync_at: datetime | None = None,
    last_sync_finished_at: datetime | None = None,
    last_safe_error_code: str | None = None,
) -> dict[str, Any]:
    """Build one selected source without credentials or provider payloads."""
    _require_test_identity(owner_identity)
    successful_at = last_successful_sync_at or FIXTURE_EVALUATED_AT - timedelta(minutes=5)
    return {
        "id": source_id,
        "workspace_id": _SYNTHETIC_WORKSPACE_ID,
        "owner_identity": owner_identity,
        "provider_family": provider_family,
        "connection_state": "active",
        "sync_state": sync_state,
        "sync_horizon_start": FIXTURE_EVALUATED_AT - timedelta(days=1),
        "sync_horizon_end": FIXTURE_EVALUATED_AT + timedelta(days=365),
        "last_successful_sync_at": successful_at,
        "last_sync_finished_at": last_sync_finished_at or successful_at,
        "last_safe_error_code": last_safe_error_code,
        "selected_calendar_count": 1,
        "external_calendar_id": external_calendar_id,
        "selected": True,
    }


def calendar_auto_match_event_fixture(
    *,
    source: dict[str, Any] | None = None,
    provider_event_id: str = "event-clear",
    starts_at: datetime = FIXTURE_RECORDING_STARTED_AT - timedelta(minutes=5),
    ends_at: datetime = FIXTURE_RECORDING_STARTED_AT + timedelta(minutes=55),
    title: str | None = "Synthetic Planning Sync",
    source_status: str = "confirmed",
    privacy_class: str = "public",
    all_day: bool = False,
    participants: Sequence[dict[str, Any]] | None = None,
    conference_link_hash: str | None = "sha256:auto-match-fixture",
    recurring_series_id: str | None = None,
    recurrence_instance_id: str | None = None,
) -> dict[str, Any]:
    """Build one sanitized event snapshot input for deterministic matching tests."""
    selected_source = source or calendar_auto_match_source_fixture()
    _require_test_identity(str(selected_source["owner_identity"]))
    if title is not None and not title.startswith("Synthetic "):
        raise ValueError("fixture event titles must be explicitly synthetic")
    roster = list(participants) if participants is not None else _synthetic_roster()
    if len(roster) > FIXTURE_MAX_ROSTER_ITEMS:
        raise ValueError(f"fixture roster exceeds {FIXTURE_MAX_ROSTER_ITEMS} items")
    for participant in roster:
        email = participant.get("email")
        if email is not None:
            _require_test_identity(email)
        display_name = participant.get("display_name")
        if display_name is not None and not display_name.startswith("Synthetic "):
            raise ValueError("fixture participant names must be explicitly synthetic")

    conference_links = []
    if conference_link_hash is not None:
        if not conference_link_hash.startswith("sha256:") or "://" in conference_link_hash:
            raise ValueError("fixture conference evidence must be a SHA-256 marker")
        conference_links.append(
            {
                "provider_family": "generic",
                "source_field": "location",
                "url_hash": conference_link_hash,
                "redacted_url_preview": "meet.example.test/...",
                "contains_passcode": False,
                "sensitivity_class": "meeting_link",
            }
        )

    event = calendar_event_fixture(
        selected_source["provider_family"],
        provider_account_id=selected_source["id"],
        provider_calendar_id=selected_source["external_calendar_id"],
        provider_event_id=provider_event_id,
        ical_uid=f"{provider_event_id}@example.test",
        starts_at=starts_at,
        ends_at=ends_at,
        duration_seconds=max(0, int((ends_at - starts_at).total_seconds())),
        title=title,
        title_state="available" if title is not None else "policy_hidden",
        description=None,
        description_state="unavailable",
        location=None,
        source_status=source_status,
        privacy_class=privacy_class,
        all_day=all_day,
        participants=roster,
        conference_links=conference_links,
        attachments_metadata=[],
        provider_extras={"raw_payload_retained": False},
        recurring_series_id=recurring_series_id,
        recurrence_instance_id=recurrence_instance_id,
        source_created_at=FIXTURE_EVALUATED_AT - timedelta(days=7),
        source_updated_at=FIXTURE_EVALUATED_AT - timedelta(minutes=5),
    )
    event.update(
        {
            "workspace_id": selected_source["workspace_id"],
            "calendar_source_id": selected_source["id"],
            "external_calendar_id": selected_source["external_calendar_id"],
            "safe_to_show_in_list": title is not None and privacy_class == "public",
            "safe_to_use_as_title": title is not None and privacy_class == "public",
        }
    )
    _assert_sanitized_event(event)
    return event


def clear_match_fixture() -> dict[str, Any]:
    source = calendar_auto_match_source_fixture()
    event = calendar_auto_match_event_fixture(source=source)
    return _scenario_fixture(
        sources=[source],
        events=[event],
        context_state="matched_auto",
        reason_code="single_fresh_candidate",
        candidate_count=1,
        visible_candidate_count=0,
    )


def overlap_match_fixture() -> dict[str, Any]:
    source = calendar_auto_match_source_fixture()
    events = [
        calendar_auto_match_event_fixture(
            source=source,
            provider_event_id="event-overlap-a",
            starts_at=FIXTURE_RECORDING_STARTED_AT - timedelta(minutes=15),
            ends_at=FIXTURE_RECORDING_STARTED_AT + timedelta(minutes=30),
            title="Synthetic Design Review",
            conference_link_hash="sha256:overlap-a",
        ),
        calendar_auto_match_event_fixture(
            source=source,
            provider_event_id="event-overlap-b",
            starts_at=FIXTURE_RECORDING_STARTED_AT - timedelta(minutes=5),
            ends_at=FIXTURE_RECORDING_STARTED_AT + timedelta(minutes=45),
            title="Synthetic Delivery Sync",
            conference_link_hash="sha256:overlap-b",
        ),
    ]
    return _scenario_fixture(
        sources=[source],
        events=events,
        context_state="ambiguous",
        reason_code="multiple_time_candidates",
        candidate_count=2,
        visible_candidate_count=2,
    )


def private_free_busy_match_fixture(
    *, privacy_class: Literal["private", "free_busy_only"] = "private"
) -> dict[str, Any]:
    if privacy_class not in {"private", "free_busy_only"}:
        raise ValueError("privacy_class must be private or free_busy_only")
    source = calendar_auto_match_source_fixture()
    event = calendar_auto_match_event_fixture(
        source=source,
        provider_event_id=f"event-{privacy_class}",
        title=None,
        privacy_class=privacy_class,
        participants=[],
        conference_link_hash=None,
    )
    event["title_state"] = "free_busy_only" if privacy_class == "free_busy_only" else "private_redacted"
    event["limitation_states"] = {
        "title": event["title_state"],
        "participants": "private_redacted",
        "conference_links": "private_redacted",
    }
    _assert_sanitized_event(event)
    return _scenario_fixture(
        sources=[source],
        events=[event],
        context_state="skipped_private",
        reason_code="private_or_free_busy_event",
        candidate_count=0,
        visible_candidate_count=0,
    )


def stale_latest_failed_match_fixture(
    *, freshness_class: Literal["stale", "latest_sync_failed"] = "stale"
) -> dict[str, Any]:
    if freshness_class not in {"stale", "latest_sync_failed"}:
        raise ValueError("freshness_class must be stale or latest_sync_failed")
    if freshness_class == "stale":
        successful_at = FIXTURE_EVALUATED_AT - timedelta(hours=24, seconds=1)
        source = calendar_auto_match_source_fixture(last_successful_sync_at=successful_at)
    else:
        successful_at = FIXTURE_EVALUATED_AT - timedelta(hours=2)
        source = calendar_auto_match_source_fixture(
            sync_state="failed",
            last_successful_sync_at=successful_at,
            last_sync_finished_at=FIXTURE_EVALUATED_AT - timedelta(minutes=1),
            last_safe_error_code="provider_unavailable",
        )
    event = calendar_auto_match_event_fixture(source=source)
    return _scenario_fixture(
        sources=[source],
        events=[event],
        context_state="skipped_stale_calendar",
        reason_code=freshness_class,
        candidate_count=0,
        visible_candidate_count=0,
    )


def recurring_match_fixture() -> dict[str, Any]:
    source = calendar_auto_match_source_fixture(provider_family="exchange_ews")
    series_id = "synthetic-weekly-series@example.test"
    events = [
        calendar_auto_match_event_fixture(
            source=source,
            provider_event_id="event-recurring-previous",
            starts_at=FIXTURE_RECORDING_STARTED_AT - timedelta(days=7),
            ends_at=FIXTURE_RECORDING_STARTED_AT - timedelta(days=7) + timedelta(hours=1),
            title="Synthetic Weekly Planning",
            recurring_series_id=series_id,
            recurrence_instance_id="synthetic-weekly-20260706T090000Z",
            conference_link_hash="sha256:recurring-series",
        ),
        calendar_auto_match_event_fixture(
            source=source,
            provider_event_id="event-recurring-current",
            title="Synthetic Weekly Planning",
            recurring_series_id=series_id,
            recurrence_instance_id="synthetic-weekly-20260713T090000Z",
            conference_link_hash="sha256:recurring-series",
        ),
    ]
    return _scenario_fixture(
        sources=[source],
        events=events,
        context_state="matched_auto",
        reason_code="single_fresh_candidate",
        candidate_count=1,
        visible_candidate_count=0,
    )


def _scenario_fixture(
    *,
    sources: Sequence[dict[str, Any]],
    events: Sequence[dict[str, Any]],
    context_state: str,
    reason_code: str,
    candidate_count: int,
    visible_candidate_count: int,
) -> dict[str, Any]:
    if len(sources) > FIXTURE_MAX_SOURCES:
        raise ValueError(f"fixture scenario exceeds {FIXTURE_MAX_SOURCES} sources")
    if len(events) > FIXTURE_MAX_EVENTS:
        raise ValueError(f"fixture scenario exceeds {FIXTURE_MAX_EVENTS} events")
    if visible_candidate_count > FIXTURE_MAX_VISIBLE_CANDIDATES:
        raise ValueError(
            f"fixture scenario exceeds {FIXTURE_MAX_VISIBLE_CANDIDATES} visible candidates"
        )
    return {
        "workspace_id": _SYNTHETIC_WORKSPACE_ID,
        "owner_identity": _SYNTHETIC_OWNER_IDENTITY,
        "recording_started_at": FIXTURE_RECORDING_STARTED_AT,
        "evaluated_at": FIXTURE_EVALUATED_AT,
        "sources": list(sources),
        "events": list(events),
        "expected": {
            "context_state": context_state,
            "reason_code": reason_code,
            "candidate_count": candidate_count,
            "visible_candidate_count": visible_candidate_count,
        },
    }


def _synthetic_roster() -> list[dict[str, Any]]:
    return [
        participant_fixture(
            "organizer",
            email="organizer@example.test",
            response_status="organizer",
            workspace_relation="owner",
        ),
        participant_fixture(
            "required_attendee",
            email="attendee@example.test",
            response_status="accepted",
        ),
    ]


def _require_test_identity(identity: str) -> None:
    domain = identity.rpartition("@")[2]
    if not domain.endswith(".test"):
        raise ValueError("fixture identities must use a .test domain")


def _assert_sanitized_event(event: dict[str, Any]) -> None:
    if event.get("description") is not None:
        raise ValueError("calendar auto-match fixtures cannot contain event descriptions")
    if event.get("attachments_metadata"):
        raise ValueError("calendar auto-match fixtures cannot contain attachment data")
    for link in event.get("conference_links", []):
        if "url" in link or link.get("contains_passcode"):
            raise ValueError("calendar auto-match fixtures cannot contain raw links or passcodes")
