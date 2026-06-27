from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from hashlib import sha256
from typing import Any

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
    title_state: str
    privacy_class: str
    participants: list[dict[str, Any]] = field(default_factory=list)
    conference_links: list[dict[str, Any]] = field(default_factory=list)
    provider_extras: dict[str, Any] = field(default_factory=dict)
    limitation_states: dict[str, str] = field(default_factory=dict)
    recurrence_rule: dict[str, Any] | None = None
    recurrence_exceptions: list[dict[str, Any]] = field(default_factory=list)
    recurring_series_id: str | None = None
    recurrence_instance_id: str | None = None

    @property
    def participant_count(self) -> int:
        return len(self.participants)

    @property
    def meeting_link_present(self) -> bool:
        return bool(self.conference_links)


def normalize_calendar_event(event: dict[str, Any]) -> NormalizedCalendarEvent:
    starts_at = _coerce_datetime(event["starts_at"])
    ends_at = _coerce_datetime(event.get("ends_at") or _default_end(starts_at, event))
    if ends_at <= starts_at:
        ends_at = starts_at + timedelta(minutes=1)
    title = event.get("title")
    title_state = str(event.get("title_state") or _title_state(title, event))
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
        duration_seconds=max(60, int((ends_at - starts_at).total_seconds())),
        timezone=event.get("timezone"),
        original_start=_optional_datetime(event.get("original_start")),
        all_day=bool(event.get("all_day", False)),
        floating_time=bool(event.get("floating_time", False)),
        title=title if title_state == "available" else None,
        title_state=title_state,
        privacy_class=str(event.get("privacy_class", "unknown")),
        participants=participants,
        conference_links=conference_links,
        provider_extras=_safe_provider_extras(event.get("provider_extras") or {}),
        limitation_states=dict(event.get("limitation_states") or {}),
        recurrence_rule=event.get("recurrence_rule"),
        recurrence_exceptions=list(event.get("recurrence_exceptions") or []),
        recurring_series_id=event.get("recurring_series_id"),
        recurrence_instance_id=event.get("recurrence_instance_id"),
    )


def normalize_icalendar_event(
    icalendar_text: str,
    *,
    provider_family: str,
    provider_calendar_id: str | None = None,
) -> NormalizedCalendarEvent:
    fields = _parse_vevent_fields(icalendar_text)
    privacy_class = "private" if fields.get("CLASS", "").lower() in {"private", "confidential"} else "public"
    source_status = fields.get("STATUS", "unknown").lower()
    starts_at = _parse_ical_datetime(fields["DTSTART"])
    event = {
        "provider_family": provider_family,
        "provider_calendar_id": provider_calendar_id,
        "provider_event_id": fields.get("UID"),
        "ical_uid": fields.get("UID"),
        "source_version": fields.get("SEQUENCE"),
        "source_status": source_status,
        "starts_at": starts_at,
        "ends_at": _parse_ical_datetime(fields["DTEND"]) if fields.get("DTEND") else None,
        "all_day": len(fields["DTSTART"]) == 8,
        "floating_time": fields["DTSTART"].endswith("Z") is False and "T" in fields["DTSTART"],
        "timezone": "UTC" if fields["DTSTART"].endswith("Z") else None,
        "title": fields.get("SUMMARY") if privacy_class == "public" else None,
        "title_state": "available" if fields.get("SUMMARY") and privacy_class == "public" else "private_redacted",
        "description_state": "available" if fields.get("DESCRIPTION") and privacy_class == "public" else "private_redacted",
        "location": fields.get("LOCATION"),
        "privacy_class": privacy_class,
        "conference_links": [] if source_status == "cancelled" else [
            {
                "provider_family": link.provider_family,
                "source_field": "icalendar",
                "url_hash": link.url_hash,
                "redacted_url_preview": link.redacted_url_preview,
                "contains_passcode": link.contains_passcode,
                "sensitivity_class": "meeting_link",
            }
            for link in _extract_ical_links(fields)
        ],
        "provider_extras": {"icalendar_source": "VEVENT"},
        "limitation_states": {},
        "recurrence_rule": {"rrule": fields["RRULE"]} if fields.get("RRULE") else None,
    }
    return normalize_calendar_event(event)


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=UTC)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    raise TypeError("calendar event datetime is required")


def _parse_ical_datetime(value: str) -> datetime:
    if len(value) == 8:
        return datetime.combine(datetime.strptime(value, "%Y%m%d").date(), time.min, tzinfo=UTC)
    if value.endswith("Z"):
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=UTC)


def _optional_datetime(value: Any) -> datetime | None:
    return None if value is None else _coerce_datetime(value)


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
    if privacy in {"private", "confidential"}:
        return "private_redacted"
    return "unknown"


def normalize_calendar_participants(participants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None]] = set()
    for participant in participants:
        item = _normalize_participant(participant)
        key = (item["participant_kind"], (item.get("email") or item.get("display_name") or "").lower() or None)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(item)
    return normalized


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
        "display_name": participant.get("display_name"),
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


def _parse_vevent_fields(icalendar_text: str) -> dict[str, str]:
    unfolded: list[str] = []
    for raw_line in icalendar_text.splitlines():
        if raw_line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += raw_line.strip()
        else:
            unfolded.append(raw_line.strip())
    fields: dict[str, str] = {}
    in_event = False
    for line in unfolded:
        if line == "BEGIN:VEVENT":
            in_event = True
            continue
        if line == "END:VEVENT":
            break
        if not in_event or ":" not in line:
            continue
        name, value = line.split(":", 1)
        fields[name.split(";", 1)[0].upper()] = value
    return fields


def _extract_ical_links(fields: dict[str, str]):
    from twobrain_rec_server.calendar.conference_links import extract_conference_link_candidates

    return extract_conference_link_candidates(fields.get("LOCATION"), fields.get("DESCRIPTION"), fields.get("URL"))
