from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from hashlib import sha256
from typing import Any
from zoneinfo import ZoneInfo

import recurring_ical_events
from icalendar import Calendar, Event

from twobrain_rec_server.calendar.providers import CalendarProviderError

RAW_EXTRA_MARKERS = ("raw", "payload", "token", "secret", "authorization")


@dataclass(frozen=True, slots=True)
class NormalizedCalendarEvent:
    provider_family: str
    provider_calendar_id: str | None
    provider_event_id: str | None
    ical_uid: str | None
    source_version: str | None
    source_status: str
    starts_at: datetime
    ends_at: datetime
    duration_seconds: int
    timezone: str | None
    original_start: datetime | None
    all_day: bool
    floating_time: bool
    title: str | None
    description: str | None
    location: str | None
    title_state: str
    transparency: str | None
    privacy_class: str
    participants: list[dict[str, Any]] = field(default_factory=list)
    conference_links: list[dict[str, Any]] = field(default_factory=list)
    attachments_metadata: list[dict[str, Any]] = field(default_factory=list)
    provider_extras: dict[str, Any] = field(default_factory=dict)
    limitation_states: dict[str, str] = field(default_factory=dict)
    recurrence_rule: dict[str, Any] | None = None
    recurrence_exceptions: list[dict[str, Any]] = field(default_factory=list)
    recurring_series_id: str | None = None
    recurrence_instance_id: str | None = None
    source_created_at: datetime | None = None
    source_updated_at: datetime | None = None

    @property
    def participant_count(self) -> int:
        return len(self.participants)

    @property
    def meeting_link_present(self) -> bool:
        return bool(self.conference_links)


def normalize_calendar_event(event: dict[str, Any]) -> NormalizedCalendarEvent:
    starts_at = _coerce_datetime(event["starts_at"])
    ends_at = _coerce_datetime(event.get("ends_at") or _default_end(starts_at, event))
    if ends_at.astimezone(UTC) <= starts_at.astimezone(UTC):
        ends_at = starts_at + timedelta(minutes=1)
    raw_title = event.get("title")
    title_state = _title_state(raw_title, event)
    privacy_class = str(event.get("privacy_class", "unknown"))
    participants = normalize_calendar_participants(event.get("participants") or [])
    conference_links = [dict(link) for link in event.get("conference_links") or []]
    return NormalizedCalendarEvent(
        provider_family=str(event["provider_family"]),
        provider_calendar_id=event.get("provider_calendar_id"),
        provider_event_id=event.get("provider_event_id"),
        ical_uid=event.get("ical_uid"),
        source_version=event.get("source_version"),
        source_status=str(event.get("source_status", "unknown")),
        starts_at=starts_at,
        ends_at=ends_at,
        duration_seconds=max(
            60, int((ends_at.astimezone(UTC) - starts_at.astimezone(UTC)).total_seconds())
        ),
        timezone=event.get("timezone"),
        original_start=_optional_datetime(event.get("original_start")),
        all_day=bool(event.get("all_day", False)),
        floating_time=bool(event.get("floating_time", False)),
        title=_text(raw_title),
        description=_text(event.get("description")),
        location=_text(event.get("location")),
        title_state=title_state,
        transparency=event.get("transparency"),
        privacy_class=privacy_class,
        participants=participants,
        conference_links=conference_links,
        attachments_metadata=[dict(item) for item in event.get("attachments_metadata") or []],
        provider_extras=_safe_provider_extras(event.get("provider_extras") or {}),
        limitation_states=dict(event.get("limitation_states") or {}),
        recurrence_rule=event.get("recurrence_rule"),
        recurrence_exceptions=list(event.get("recurrence_exceptions") or []),
        recurring_series_id=event.get("recurring_series_id"),
        recurrence_instance_id=event.get("recurrence_instance_id"),
        source_created_at=_optional_datetime(event.get("source_created_at")),
        source_updated_at=_optional_datetime(event.get("source_updated_at")),
    )


def normalize_icalendar_events(
    icalendar_text: str,
    *,
    provider_family: str,
    provider_calendar_id: str | None = None,
    time_min: datetime | None = None,
    time_max: datetime | None = None,
) -> tuple[tuple[NormalizedCalendarEvent, ...], tuple[str, ...]]:
    """Expand complete resources in the same bounded window as provider sync."""
    try:
        calendar = Calendar.from_ical(icalendar_text)
        components = calendar.walk("VEVENT")
        recurring_uids = {
            str(event.get("UID"))
            for event in components
            if any(key in event for key in ("RRULE", "RDATE", "RECURRENCE-ID"))
        }
        deleted_uids = {
            str(event["UID"])
            for event in components
            if str(event.get("STATUS", "")).upper() == "CANCELLED" and "RECURRENCE-ID" not in event
        }
        calendar.subcomponents = [
            component
            for component in calendar.subcomponents
            if component.name != "VEVENT" or str(component.get("UID")) not in deleted_uids
        ]
        calendar_timezone = _text(calendar.get("X-WR-TIMEZONE"))
        for event in calendar.walk("VEVENT"):
            if not event.get("UID"):
                raise ValueError("missing event identity")
            if (
                "DTSTART" not in event
                and "RECURRENCE-ID" in event
                and str(event.get("STATUS", "")).upper() == "CANCELLED"
            ):
                event.add(
                    "DTSTART",
                    event.decoded("RECURRENCE-ID"),
                    parameters=event["RECURRENCE-ID"].params,
                )
            _component_time(event, "DTSTART", calendar_timezone)
        if recurring_uids - deleted_uids and (time_min is None or time_max is None):
            raise ValueError("recurrence requires a bounded window")
        instances = (
            recurring_ical_events.of(calendar, keep_recurrence_attributes=True).between(
                time_min, time_max
            )
            if time_min is not None and time_max is not None
            else calendar.walk("VEVENT")
        )
        events = tuple(
            _normalize_ical_component(
                event,
                provider_family=provider_family,
                provider_calendar_id=provider_calendar_id,
                recurring=str(event.get("UID")) in recurring_uids,
                calendar_timezone=calendar_timezone,
            )
            for event in instances
        )
        return events, tuple(sorted(deleted_uids))
    except CalendarProviderError:
        raise
    except Exception as exc:
        # The provider body can contain private text; only expose a stable code.
        raise CalendarProviderError("invalid_payload") from exc


def normalize_icalendar_event(
    icalendar_text: str,
    *,
    provider_family: str,
    provider_calendar_id: str | None = None,
) -> NormalizedCalendarEvent:
    """Normalize one component; provider reads use the bounded resource function."""
    try:
        calendar = Calendar.from_ical(icalendar_text)
        event = calendar.walk("VEVENT")[0]
        return _normalize_ical_component(
            event,
            provider_family=provider_family,
            provider_calendar_id=provider_calendar_id,
            recurring=any(key in event for key in ("RRULE", "RDATE", "RECURRENCE-ID")),
            calendar_timezone=_text(calendar.get("X-WR-TIMEZONE")),
        )
    except CalendarProviderError:
        raise
    except Exception as exc:
        raise CalendarProviderError("invalid_payload") from exc


def _component_time(event: Event, field: str, calendar_timezone: str | None):
    value = event.decoded(field)
    if isinstance(value, datetime) and value.tzinfo is None:
        # Floating local time is not UTC. The calendar must declare its zone.
        timezone = event[field].params.get("TZID") or calendar_timezone
        if not timezone:
            raise CalendarProviderError("invalid_payload")
        value = value.replace(tzinfo=ZoneInfo(str(timezone)))
    return value


def _ical_identity(value: date | datetime) -> str:
    return (
        value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        if isinstance(value, datetime)
        else value.strftime("%Y%m%d")
    )


def _properties(event: Event, key: str) -> list:
    value = event.get(key)
    return [] if value is None else value if isinstance(value, list) else [value]


def _normalize_ical_component(
    component: Event,
    *,
    provider_family: str,
    provider_calendar_id: str | None,
    recurring: bool,
    calendar_timezone: str | None,
) -> NormalizedCalendarEvent:
    from twobrain_rec_server.calendar.conference_links import conference_link_dicts

    starts_at = _component_time(component, "DTSTART", calendar_timezone)
    ends_at = (
        _component_time(component, "DTEND", calendar_timezone)
        if "DTEND" in component
        else starts_at + component.decoded("DURATION")
        if "DURATION" in component
        else None
    )
    original = (
        _component_time(component, "RECURRENCE-ID", calendar_timezone)
        if recurring and "RECURRENCE-ID" in component
        else starts_at
        if recurring
        else None
    )
    recurrence_id = _ical_identity(original) if original is not None else None
    uid = str(component["UID"])
    status = str(component.get("STATUS", "unknown")).lower()
    participants = []
    for key in ("ORGANIZER", "ATTENDEE"):
        for person in _properties(component, key):
            uri = str(person)
            params = person.params
            kind = (
                "organizer"
                if key == "ORGANIZER"
                else {"ROOM": "room", "RESOURCE": "resource", "GROUP": "group"}.get(
                    str(params.get("CUTYPE", "")),
                    "optional_attendee"
                    if params.get("ROLE") == "OPT-PARTICIPANT"
                    else "required_attendee",
                )
            )
            participants.append(
                {
                    "participant_kind": kind,
                    "email": uri[7:] if uri.lower().startswith("mailto:") else None,
                    "display_name": _text(params.get("CN")),
                    "response_status": str(params.get("PARTSTAT", "unknown"))
                    .lower()
                    .replace("needs-action", "needsAction"),
                    "provider_uri": uri,
                    "provider_details": {str(key): str(value) for key, value in params.items()},
                }
            )
    timezone = component["DTSTART"].params.get("TZID") or calendar_timezone
    if not timezone and isinstance(starts_at, datetime):
        timezone = str(starts_at.tzinfo)
    return normalize_calendar_event(
        {
            "provider_family": provider_family,
            "provider_calendar_id": provider_calendar_id,
            "provider_event_id": f"{uid}:{recurrence_id}" if recurrence_id else uid,
            "ical_uid": uid,
            "source_version": _text(component.get("SEQUENCE")),
            "source_status": status,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "all_day": not isinstance(starts_at, datetime),
            "floating_time": False,
            "timezone": _text(timezone),
            "title": _text(component.get("SUMMARY")),
            "description": _text(component.get("DESCRIPTION")),
            "location": _text(component.get("LOCATION")),
            "transparency": _text(component.get("TRANSP")),
            "privacy_class": str(component.get("CLASS", "public")).lower(),
            "participants": participants,
            "conference_links": []
            if status == "cancelled"
            else conference_link_dicts(
                *[
                    (key.lower(), _text(component.get(key)))
                    for key in ("URL", "DESCRIPTION", "LOCATION")
                ]
            ),
            "attachments_metadata": [
                {
                    "source_field": "ATTACH",
                    "url": str(attachment),
                    **{str(key).lower(): str(value) for key, value in attachment.params.items()},
                }
                for attachment in _properties(component, "ATTACH")
            ],
            "provider_extras": {"icalendar_source": "VEVENT"},
            "recurrence_rule": {
                **(
                    {"rrule": component["RRULE"].to_ical().decode()} if "RRULE" in component else {}
                ),
                **(
                    {"rdate": [item.to_ical().decode() for item in _properties(component, "RDATE")]}
                    if "RDATE" in component
                    else {}
                ),
            }
            if "RRULE" in component or "RDATE" in component
            else None,
            "recurrence_exceptions": [
                {"exdate": item.to_ical().decode()} for item in _properties(component, "EXDATE")
            ],
            "recurring_series_id": uid if recurring else None,
            "recurrence_instance_id": recurrence_id,
            "original_start": original,
            "source_created_at": component.decoded("CREATED") if "CREATED" in component else None,
            "source_updated_at": component.decoded("LAST-MODIFIED")
            if "LAST-MODIFIED" in component
            else None,
        }
    )


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=UTC)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    raise TypeError("calendar event datetime is required")


def _optional_datetime(value: Any) -> datetime | None:
    return None if value is None else _coerce_datetime(value)


def _text(value: Any) -> str | None:
    return None if value is None else str(value)


def _default_end(starts_at: datetime, event: dict[str, Any]) -> datetime:
    if event.get("all_day"):
        return starts_at + timedelta(days=1)
    duration_seconds = event.get("duration_seconds")
    if duration_seconds:
        return starts_at + timedelta(seconds=max(60, int(duration_seconds)))
    return starts_at + timedelta(hours=1)


def _title_state(title: str | None, event: dict[str, Any]) -> str:
    privacy = str(event.get("privacy_class", "")).lower()
    if title:
        return "available"
    if privacy == "free_busy_only":
        return "free_busy_only"
    return "unknown"


def normalize_calendar_participants(participants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: dict[tuple[str, str], dict[str, Any]] = {}
    for index, participant in enumerate(participants):
        item = _normalize_participant(participant)
        identity = item.get("email") or item.get("provider_uri") or item.get("display_name")
        key = (
            item["participant_kind"],
            str(identity).casefold() if identity else f"unnamed:{index}",
        )
        previous = normalized.get(key, {})
        details = previous.get("provider_details", {}) | item.get("provider_details", {})
        normalized[key] = previous | {
            field: value
            for field, value in item.items()
            if field not in previous or value is not None and value != "unknown"
        }
        if details:
            normalized[key]["provider_details"] = details
    return list(normalized.values())


def _normalize_participant(participant: dict[str, Any]) -> dict[str, Any]:
    email = participant.get("email")
    participant_kind = str(participant.get("participant_kind", "attendee"))
    response_status = str(participant.get("response_status", "unknown"))
    workspace_relation = str(participant.get("workspace_relation") or _workspace_relation(email))
    return {
        "participant_kind": participant_kind,
        "response_status": response_status,
        "email": email,
        "email_hash": participant.get("email_hash") or _email_hash(email),
        "display_name": _text(participant.get("display_name")),
        **(
            {"provider_uri": participant["provider_uri"]} if participant.get("provider_uri") else {}
        ),
        **(
            {"provider_details": dict(participant["provider_details"])}
            if participant.get("provider_details")
            else {}
        ),
        "workspace_relation": workspace_relation,
        "recipient_candidate_class": participant.get("recipient_candidate_class")
        or _recipient_candidate_class(participant_kind, response_status, email, workspace_relation),
    }


def _email_hash(email: str | None) -> str | None:
    return f"sha256:{sha256(email.lower().encode('utf-8')).hexdigest()}" if email else None


def _workspace_relation(email: str | None) -> str:
    if email is None:
        return "unknown"
    return "internal" if email.lower().endswith("@example.test") else "external"


def _recipient_candidate_class(
    participant_kind: str,
    response_status: str,
    email: str | None,
    workspace_relation: str,
) -> str:
    if participant_kind in {"resource", "room", "group"}:
        return participant_kind
    if not email:
        return "unavailable"
    if response_status == "declined":
        return "declined"
    if participant_kind == "organizer":
        return "organizer"
    if participant_kind == "optional_attendee":
        return "optional_attendee"
    if workspace_relation == "external":
        return "external_attendee"
    if workspace_relation == "internal":
        return "internal_attendee"
    return "required_attendee"


def _safe_provider_extras(extras: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in extras.items():
        lowered = key.lower()
        if any(marker in lowered for marker in RAW_EXTRA_MARKERS):
            continue
        safe[key] = value
    safe["raw_payload_retained"] = False
    return safe
