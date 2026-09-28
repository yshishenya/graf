"""Owner-scoped projections; provider occurrences and immutable recording links stay intact."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import String, and_, case, cast, func, or_, select, tuple_

from twobrain_rec_server.calendar.service import SELECTABLE_CALENDAR_VISIBILITIES
from twobrain_rec_server.db.models import CalendarEventSnapshot as Event
from twobrain_rec_server.db.models import CalendarSource, ExternalCalendar


def series_key(event, owner_id) -> str | None:
    if not event.recurring_series_id:
        return None
    identity = "::".join(
        map(
            str,
            (
                event.workspace_id,
                owner_id,
                event.calendar_source_id,
                event.external_calendar_id,
                event.recurring_series_id,
            ),
        )
    )
    return "v2-" + hashlib.sha256(identity.encode()).hexdigest()


def series_key_expression(owner_id):
    identity = func.concat(
        cast(Event.workspace_id, String),
        "::",
        str(owner_id),
        "::",
        cast(Event.calendar_source_id, String),
        "::",
        cast(Event.external_calendar_id, String),
        "::",
        Event.recurring_series_id,
    )
    return func.concat("v2-", func.encode(func.sha256(func.convert_to(identity, "UTF8")), "hex"))


def representative(events, now):
    valid = [
        e
        for e in events
        if e.source_status != "cancelled" and e.source_deleted_at is None and e.ends_at > now
    ]
    current = [e for e in valid if e.starts_at <= now]
    return (
        min(current, key=lambda e: (-e.starts_at.timestamp(), str(e.id)))
        if current
        else min(valid, key=lambda e: (e.starts_at, str(e.id)), default=None)
    )


def authorized_events(scope, *, include_cancelled=False):
    query = (
        select(Event)
        .join(ExternalCalendar, Event.external_calendar_id == ExternalCalendar.id)
        .join(CalendarSource, Event.calendar_source_id == CalendarSource.id)
        .where(
            Event.workspace_id == scope.workspace_id,
            ExternalCalendar.workspace_id == scope.workspace_id,
            ExternalCalendar.calendar_source_id == CalendarSource.id,
            ExternalCalendar.selected.is_(True),
            ExternalCalendar.visibility.in_(SELECTABLE_CALENDAR_VISIBILITIES),
            CalendarSource.workspace_id == scope.workspace_id,
            CalendarSource.owner_user_id == scope.user_id,
            CalendarSource.connection_state == "active",
            CalendarSource.disconnected_at.is_(None),
        )
    )

    if not include_cancelled:
        query = query.where(Event.source_deleted_at.is_(None), Event.source_status != "cancelled")
    return query


def filtered_events(scope, preference, *, include_cancelled=False, history=False):
    query = authorized_events(scope, include_cancelled=include_cancelled)
    if preference is None or not preference.include_all_day_events:
        query = query.where(Event.all_day.is_(False))
    private = or_(
        Event.safe_to_show_in_list.is_(False),
        Event.privacy_class.in_(["free_busy", "free_busy_only"]),
    )
    # Historical dates remain useful after provider cancellation removes join metadata.
    if history:
        return (
            query
            if preference and preference.include_private_free_busy_prompt_candidates
            else query.where(~private)
        )
    count = func.coalesce(
        Event.conference_summary_json["participant_count"].as_string(),
        Event.provider_extras_json["participant_count"].as_string(),
        "0",
    )
    # Compare digits without casting arbitrary provider metadata to an integer.
    participants = and_(count.op("~")("^[0-9]+$"), count.op("~")("[1-9]"))
    link = or_(
        Event.conference_summary_json["meeting_link_present"].as_string().in_(["true", "1"]),
        func.nullif(func.trim(Event.location), "").is_not(None),
        Event.provider_extras_json["location_present"].as_string().in_(["true", "1"]),
    )
    eligible = or_(participants, link)
    if (
        preference
        and preference.include_events_without_participants
        and preference.include_events_without_link_or_location
    ):
        eligible = True
    if preference and preference.include_private_free_busy_prompt_candidates:
        return query.where(or_(private, eligible))
    return query.where(~private, eligible)


async def overview_events(db, scope, preference, *, now=None, limit=4, after=None):
    now = now or datetime.now(UTC)
    current = Event.starts_at <= now
    # Ranking and eligibility precede LIMIT, so one frequent series cannot consume the page.
    partition = (
        Event.calendar_source_id,
        Event.external_calendar_id,
        func.coalesce(func.nullif(Event.recurring_series_id, ""), cast(Event.id, String)),
    )
    ranked = (
        filtered_events(scope, preference)
        .with_only_columns(
            Event.id.label("id"),
            func.row_number()
            .over(
                partition_by=partition,
                order_by=(
                    case((current, 0), else_=1),
                    case((current, Event.starts_at)).desc(),
                    Event.starts_at.asc(),
                    Event.id.asc(),
                ),
            )
            .label("rank"),
        )
        .where(Event.ends_at > now, Event.starts_at <= now + timedelta(days=30))
        .subquery()
    )
    query = select(Event).join(ranked, Event.id == ranked.c.id).where(ranked.c.rank == 1)
    if after:
        query = query.where(
            tuple_(Event.starts_at, Event.id)
            > tuple_(datetime.fromisoformat(after[0]), UUID(after[1]))
        )
    rows = list(await db.scalars(query.order_by(Event.starts_at, Event.id).limit(limit + 1)))
    return rows[:limit], len(rows) > limit


def encode_cursor(context, last, secret, *, now=None):
    payload = {
        "v": 1,
        "context": context,
        "last": last,
        "exp": int(time.time() if now is None else now) + 3600,
    }
    cipher = Fernet(
        base64.urlsafe_b64encode(hashlib.sha256(("calendar-cursor:" + secret).encode()).digest())
    )
    raw = cipher.encrypt(json.dumps(payload, separators=(",", ":")).encode()).decode()
    sig = hmac.new(secret.encode(), ("calendar-series:" + raw).encode(), hashlib.sha256).hexdigest()
    return raw + "." + sig


def decode_cursor(cursor, context, secret, *, now=None):
    try:
        if len(cursor) > 2048 or not cursor.isascii():
            raise ValueError()
        raw, sig = cursor.split(".")
        expected = hmac.new(
            secret.encode(), ("calendar-series:" + raw).encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError()
        cipher = Fernet(
            base64.urlsafe_b64encode(
                hashlib.sha256(("calendar-cursor:" + secret).encode()).digest()
            )
        )
        payload = json.loads(cipher.decrypt(raw.encode()))
        if (
            payload["v"] != 1
            or payload["context"] != context
            or payload["exp"] <= int(time.time() if now is None else now)
        ):
            raise ValueError()
        start, event_id = payload["last"]
        if datetime.fromisoformat(start).tzinfo is None:
            raise ValueError()
        UUID(event_id)
        return start, event_id
    except (ValueError, KeyError, TypeError, UnicodeError, InvalidToken) as error:
        raise ValueError("invalid_calendar_cursor") from error


async def series_occurrences(db, scope, preference, key, start, end, *, limit=20, after=None):
    query = filtered_events(scope, preference, include_cancelled=True, history=True).where(
        Event.recurring_series_id.is_not(None),
        series_key_expression(scope.user_id) == key,
        Event.starts_at >= start,
        Event.starts_at < end,
    )
    if after:
        query = query.where(
            tuple_(Event.starts_at, Event.id)
            > tuple_(datetime.fromisoformat(after[0]), UUID(after[1]))
        )
    rows = list(await db.scalars(query.order_by(Event.starts_at, Event.id).limit(limit + 1)))
    return rows[:limit], len(rows) > limit
