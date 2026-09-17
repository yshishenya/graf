"""Run untrusted recurrence expansion in a disposable, bounded process."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict
from datetime import date, datetime

from twobrain_rec_server.calendar.normalize import (
    NormalizedCalendarEvent,
    normalize_icalendar_events,
)
from twobrain_rec_server.calendar.providers import CalendarEventPage, CalendarProviderError

PARSE_TIMEOUT_SECONDS = 15
MAX_CONTENT_BYTES = 32 * 1024 * 1024
_DATE_FIELDS = ("starts_at", "ends_at", "original_start", "source_created_at", "source_updated_at")


async def expand_caldav_resources(resources, *, provider_family, calendar_id, time_min, time_max):
    data = json.dumps(
        {
            "resources": resources,
            "provider_family": provider_family,
            "calendar_id": calendar_id,
            "time_min": time_min,
            "time_max": time_max,
        },
        default=_date_text,
    ).encode()
    if len(data) > MAX_CONTENT_BYTES:
        raise CalendarProviderError("invalid_payload")
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        __name__,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(data), PARSE_TIMEOUT_SECONDS)
        if process.returncode != 0 or len(output) > MAX_CONTENT_BYTES:
            raise CalendarProviderError("invalid_payload")
        result = json.loads(output)
        return CalendarEventPage(
            events=tuple(
                NormalizedCalendarEvent(
                    **{
                        key: datetime.fromisoformat(value)
                        if key in _DATE_FIELDS and value
                        else value
                        for key, value in event.items()
                    }
                )
                for event in result["events"]
            ),
            deleted_ical_uids=tuple(result["deleted_uids"]),
        )
    except TimeoutError as exc:
        raise CalendarProviderError("invalid_payload") from exc
    finally:
        if process.returncode is None:
            process.kill()
        await process.wait()


def _date_text(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError("unsupported calendar value")


def main():
    # Linux production: bound computation and memory as well as parent wall time.
    # A thread timeout cannot stop dateutil expanding an old SECONDLY rule.
    if sys.platform == "linux":
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
    data = sys.stdin.buffer.read(MAX_CONTENT_BYTES + 1)
    if len(data) > MAX_CONTENT_BYTES:
        raise ValueError("calendar resource too large")
    request = json.loads(data)
    events, deleted_uids = [], []
    for raw in request["resources"]:
        normalized, removed = normalize_icalendar_events(
            raw,
            provider_family=request["provider_family"],
            provider_calendar_id=request["calendar_id"],
            time_min=datetime.fromisoformat(request["time_min"]) if request["time_min"] else None,
            time_max=datetime.fromisoformat(request["time_max"]) if request["time_max"] else None,
        )
        events.extend(asdict(event) for event in normalized)
        deleted_uids.extend(removed)
    output = json.dumps(
        {"events": events, "deleted_uids": deleted_uids}, default=_date_text
    ).encode()
    if len(output) > MAX_CONTENT_BYTES:
        raise ValueError("calendar result too large")
    sys.stdout.buffer.write(output)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never echo private provider payloads or parser exceptions.
        sys.exit(1)
