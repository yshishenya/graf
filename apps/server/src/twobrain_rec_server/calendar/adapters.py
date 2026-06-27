from __future__ import annotations

from typing import Any

from twobrain_rec_server.calendar.conference_links import extract_conference_link_candidates
from twobrain_rec_server.calendar.normalize import (
    NormalizedCalendarEvent,
    normalize_calendar_event,
    normalize_icalendar_event,
)


class ProviderMappingAdapter:
    def __init__(
        self,
        provider_family: str,
        adapter_family: str,
        *,
        timeout_seconds: float = 10.0,
        max_pages: int = 100,
    ) -> None:
        self.provider_family = provider_family
        self.adapter_family = adapter_family
        self.timeout_seconds = timeout_seconds
        self.max_pages = max_pages

    def map_event(self, event: dict) -> NormalizedCalendarEvent:
        if "icalendar" in event:
            return normalize_icalendar_event(
                str(event["icalendar"]),
                provider_family=self.provider_family,
                provider_calendar_id=event.get("provider_calendar_id"),
            )
        if self.adapter_family == "google_calendar" and "start" in event:
            return normalize_calendar_event(_google_event(event, self.provider_family))
        if self.adapter_family == "microsoft_graph" and "start" in event:
            return normalize_calendar_event(_graph_event(event, self.provider_family))
        if self.adapter_family == "exchange_ews" and "Start" in event:
            return normalize_calendar_event(_ews_event(event, self.provider_family))
        if self.adapter_family == "bitrix24" and "DATE_FROM" in event:
            return normalize_calendar_event(_bitrix_event(event, self.provider_family))
        return normalize_calendar_event(event | {"provider_family": self.provider_family})


ADAPTER_FAMILIES = {
    "caldav_yandex": "caldav",
    "caldav_mail_ru": "caldav",
    "custom_caldav": "caldav",
    "custom_caldav_vk_workspace": "caldav",
    "caldav_mailion_myoffice": "caldav",
    "caldav_r7_office": "caldav",
    "caldav_communigate_pro": "caldav",
    "caldav_rupost": "caldav",
    "caldav_nextcloud_sogo": "caldav",
    "google_calendar": "google_calendar",
    "microsoft_graph": "microsoft_graph",
    "exchange_ews": "exchange_ews",
    "bitrix24": "bitrix24",
}


def adapter_for_provider(provider_family: str) -> ProviderMappingAdapter:
    return ProviderMappingAdapter(provider_family, ADAPTER_FAMILIES.get(provider_family, "caldav"))


def _google_event(event: dict[str, Any], provider_family: str) -> dict[str, Any]:
    private = str(event.get("visibility", "")).lower() == "private"
    attendees = [] if private else [_google_organizer(event), *[_google_attendee(item) for item in event.get("attendees") or []]]
    entry_points = (event.get("conferenceData") or {}).get("entryPoints") or []
    links = [entry.get("uri") for entry in entry_points if entry.get("uri")]
    return {
        "provider_family": provider_family,
        "provider_calendar_id": event.get("calendarId") or event.get("provider_calendar_id"),
        "provider_event_id": event.get("id"),
        "ical_uid": event.get("iCalUID"),
        "source_version": event.get("etag"),
        "source_status": event.get("status", "unknown"),
        "source_created_at": event.get("created"),
        "source_updated_at": event.get("updated"),
        "starts_at": _google_time(event["start"]),
        "ends_at": _google_time(event.get("end") or event["start"]),
        "timezone": (event.get("start") or {}).get("timeZone"),
        "all_day": "date" in (event.get("start") or {}),
        "title": None if private else event.get("summary"),
        "title_state": "private_redacted" if private else ("available" if event.get("summary") else "unknown"),
        "description": None if private else event.get("description"),
        "description_state": "private_redacted" if private else ("available" if event.get("description") else "unknown"),
        "location": None if private else event.get("location"),
        "transparency": event.get("transparency"),
        "privacy_class": "private" if private else "public",
        "participants": [participant for participant in attendees if participant],
        "conference_links": _link_dicts("google_conference", *links),
        "attachments_metadata": event.get("attachments") or [],
        "provider_extras": {
            "native_resource": "google_event",
            "color_id": event.get("colorId"),
            "event_type": event.get("eventType"),
        },
        "limitation_states": {"participants": "private_redacted"} if private else {},
        "recurrence_rule": {"rules": event["recurrence"]} if event.get("recurrence") else None,
        "recurring_series_id": event.get("recurringEventId"),
        "recurrence_instance_id": _google_time(event["originalStartTime"]) if event.get("originalStartTime") else None,
        "original_start": _google_time(event["originalStartTime"]) if event.get("originalStartTime") else None,
    }


def _graph_event(event: dict[str, Any], provider_family: str) -> dict[str, Any]:
    private = str(event.get("sensitivity", "")).lower() in {"private", "confidential"}
    attendees = [] if private else [_graph_organizer(event), *[_graph_attendee(item) for item in event.get("attendees") or []]]
    join_url = (event.get("onlineMeeting") or {}).get("joinUrl")
    return {
        "provider_family": provider_family,
        "provider_calendar_id": event.get("calendarId") or event.get("calendar_id"),
        "provider_event_id": event.get("id"),
        "ical_uid": event.get("iCalUId") or event.get("iCalUID"),
        "source_version": event.get("changeKey"),
        "source_status": "cancelled" if event.get("isCancelled") else "confirmed",
        "source_created_at": event.get("createdDateTime"),
        "source_updated_at": event.get("lastModifiedDateTime"),
        "starts_at": _graph_time(event["start"]),
        "ends_at": _graph_time(event.get("end") or event["start"]),
        "timezone": (event.get("start") or {}).get("timeZone"),
        "title": None if private else event.get("subject"),
        "title_state": "private_redacted" if private else ("available" if event.get("subject") else "unknown"),
        "description": None if private else (event.get("bodyPreview") or (event.get("body") or {}).get("content")),
        "description_state": "private_redacted" if private else (
            "available" if event.get("bodyPreview") or (event.get("body") or {}).get("content") else "unknown"
        ),
        "location": None if private else (event.get("location") or {}).get("displayName"),
        "transparency": event.get("showAs"),
        "privacy_class": "private" if private else "public",
        "participants": [participant for participant in attendees if participant],
        "conference_links": _link_dicts("graph_online_meeting", join_url, event.get("onlineMeetingUrl")),
        "attachments_metadata": event.get("attachments") or [],
        "provider_extras": {
            "native_resource": "microsoft_graph_event",
            "categories": event.get("categories") or [],
            "importance": event.get("importance"),
        },
        "limitation_states": {"participants": "private_redacted"} if private else {},
        "recurrence_rule": event.get("recurrence"),
        "recurring_series_id": event.get("seriesMasterId"),
    }


def _ews_event(event: dict[str, Any], provider_family: str) -> dict[str, Any]:
    private = str(event.get("Sensitivity", "")).lower() in {"private", "confidential"}
    item_id = event.get("ItemId") or {}
    attendees = [] if private else [_ews_organizer(event), *[_ews_attendee(item, "required_attendee") for item in event.get("RequiredAttendees") or []]]
    attendees.extend([] if private else [_ews_attendee(item, "optional_attendee") for item in event.get("OptionalAttendees") or []])
    attendees.extend([] if private else [_ews_attendee(item, "resource") for item in event.get("Resources") or []])
    return {
        "provider_family": provider_family,
        "provider_calendar_id": event.get("CalendarId") or event.get("calendar_id"),
        "provider_event_id": item_id.get("Id") if isinstance(item_id, dict) else event.get("ItemId"),
        "ical_uid": event.get("UID") or event.get("ICalUid"),
        "source_version": item_id.get("ChangeKey") if isinstance(item_id, dict) else event.get("ChangeKey"),
        "source_status": "cancelled" if event.get("IsCancelled") else "confirmed",
        "source_created_at": event.get("DateTimeCreated"),
        "source_updated_at": event.get("LastModifiedTime"),
        "starts_at": event["Start"],
        "ends_at": event.get("End") or event["Start"],
        "timezone": event.get("TimeZone"),
        "title": None if private else event.get("Subject"),
        "title_state": "private_redacted" if private else ("available" if event.get("Subject") else "unknown"),
        "description": None if private else _ews_body_text(event.get("Body")),
        "description_state": "private_redacted" if private else ("available" if event.get("Body") else "unknown"),
        "location": None if private else event.get("Location"),
        "transparency": event.get("LegacyFreeBusyStatus"),
        "privacy_class": "private" if private else "public",
        "participants": [participant for participant in attendees if participant],
        "conference_links": _link_dicts("ews_location", event.get("Location"), event.get("JoinUrl")),
        "attachments_metadata": event.get("Attachments") or [],
        "provider_extras": {"native_resource": "exchange_ews_event", "categories": event.get("Categories") or []},
        "limitation_states": {"participants": "private_redacted"} if private else {},
        "recurring_series_id": event.get("RecurringMasterId"),
        "recurrence_instance_id": event.get("OccurrenceId"),
        "original_start": event.get("OriginalStart"),
    }


def _bitrix_event(event: dict[str, Any], provider_family: str) -> dict[str, Any]:
    private = str(event.get("PRIVATE_EVENT", "")).upper() == "Y"
    attendees = [] if private else [_bitrix_organizer(event), *[_bitrix_attendee(item) for item in event.get("ATTENDEE_LIST") or []]]
    return {
        "provider_family": provider_family,
        "provider_calendar_id": str(event.get("OWNER_ID") or event.get("CALENDAR_ID") or ""),
        "provider_event_id": str(event.get("ID")),
        "ical_uid": event.get("DAV_XML_ID") or event.get("G_EVENT_ID") or str(event.get("ID")),
        "source_version": str(event.get("VERSION")) if event.get("VERSION") is not None else None,
        "source_status": "cancelled" if str(event.get("DELETED", "")).upper() == "Y" else "confirmed",
        "source_created_at": event.get("DATE_CREATE"),
        "source_updated_at": event.get("TIMESTAMP_X"),
        "starts_at": event["DATE_FROM"],
        "ends_at": event.get("DATE_TO") or event["DATE_FROM"],
        "timezone": event.get("TZ_FROM"),
        "title": None if private else event.get("NAME"),
        "title_state": "private_redacted" if private else ("available" if event.get("NAME") else "unknown"),
        "description": None if private else event.get("DESCRIPTION"),
        "description_state": "private_redacted" if private else ("available" if event.get("DESCRIPTION") else "unknown"),
        "location": None if private else event.get("LOCATION"),
        "transparency": event.get("ACCESSIBILITY"),
        "privacy_class": "private" if private else "public",
        "participants": [participant for participant in attendees if participant],
        "conference_links": _link_dicts("bitrix_location", event.get("LOCATION"), event.get("DESCRIPTION")),
        "provider_extras": {
            "native_resource": "bitrix24_event",
            "color": event.get("COLOR"),
            "reminders": event.get("REMIND") or [],
        },
        "limitation_states": {"participants": "private_redacted"} if private else {},
        "recurrence_rule": {"rrule": event["RRULE"]} if event.get("RRULE") else None,
        "recurrence_exceptions": [{"exdate": event["EXDATE"]}] if event.get("EXDATE") else [],
    }


def _google_time(value: dict[str, Any]) -> str:
    return str(value.get("dateTime") or value.get("date"))


def _graph_time(value: dict[str, Any]) -> str:
    return str(value.get("dateTime"))


def _ews_body_text(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("Text") or value.get("text")
    return str(value) if value else None


def _google_organizer(event: dict[str, Any]) -> dict[str, Any] | None:
    organizer = event.get("organizer") or {}
    email = organizer.get("email")
    if not email:
        return None
    return {
        "participant_kind": "organizer",
        "email": email,
        "display_name": organizer.get("displayName"),
        "response_status": "organizer",
    }


def _google_attendee(attendee: dict[str, Any]) -> dict[str, Any]:
    return {
        "participant_kind": "resource" if attendee.get("resource") else ("optional_attendee" if attendee.get("optional") else "required_attendee"),
        "email": attendee.get("email"),
        "display_name": attendee.get("displayName"),
        "response_status": _response_status(attendee.get("responseStatus")),
    }


def _graph_organizer(event: dict[str, Any]) -> dict[str, Any] | None:
    email = ((event.get("organizer") or {}).get("emailAddress") or {})
    if not email.get("address"):
        return None
    return {
        "participant_kind": "organizer",
        "email": email.get("address"),
        "display_name": email.get("name"),
        "response_status": "organizer",
    }


def _graph_attendee(attendee: dict[str, Any]) -> dict[str, Any]:
    email = attendee.get("emailAddress") or {}
    return {
        "participant_kind": "optional_attendee" if attendee.get("type") == "optional" else "required_attendee",
        "email": email.get("address"),
        "display_name": email.get("name"),
        "response_status": _response_status((attendee.get("status") or {}).get("response")),
    }


def _ews_organizer(event: dict[str, Any]) -> dict[str, Any] | None:
    mailbox = ((event.get("Organizer") or {}).get("Mailbox") or {})
    if not mailbox.get("EmailAddress"):
        return None
    return {
        "participant_kind": "organizer",
        "email": mailbox.get("EmailAddress"),
        "display_name": mailbox.get("Name"),
        "response_status": "organizer",
    }


def _ews_attendee(attendee: dict[str, Any], kind: str) -> dict[str, Any]:
    mailbox = attendee.get("Mailbox") or {}
    return {
        "participant_kind": kind,
        "email": mailbox.get("EmailAddress"),
        "display_name": mailbox.get("Name"),
        "response_status": _response_status(attendee.get("ResponseType")),
    }


def _bitrix_organizer(event: dict[str, Any]) -> dict[str, Any] | None:
    email = event.get("MEETING_HOST")
    return {"participant_kind": "organizer", "email": email, "response_status": "organizer"} if email else None


def _bitrix_attendee(attendee: dict[str, Any]) -> dict[str, Any]:
    return {
        "participant_kind": "required_attendee",
        "email": attendee.get("EMAIL"),
        "display_name": attendee.get("DISPLAY_NAME") or attendee.get("NAME"),
        "response_status": _response_status(attendee.get("STATUS")),
    }


def _response_status(value: Any) -> str:
    normalized = str(value or "unknown").lower()
    return {
        "accept": "accepted",
        "accepted": "accepted",
        "y": "accepted",
        "decline": "declined",
        "declined": "declined",
        "n": "declined",
        "tentativelyaccepted": "tentative",
        "tentative": "tentative",
        "needsaction": "needs_action",
        "needs_action": "needs_action",
        "q": "needs_action",
    }.get(normalized, normalized)


def _link_dicts(source_field: str, *texts: str | None) -> list[dict[str, Any]]:
    return [
        {
            "provider_family": link.provider_family,
            "source_field": source_field,
            "url_hash": link.url_hash,
            "redacted_url_preview": link.redacted_url_preview,
            "contains_passcode": link.contains_passcode,
            "sensitivity_class": "meeting_link",
        }
        for link in extract_conference_link_candidates(*texts)
    ]
