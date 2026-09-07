"""Presentation-only time context. Never use it for storage or business deadlines."""

from __future__ import annotations

import re
from contextvars import ContextVar
from datetime import UTC, date, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from babel import Locale
from babel.core import get_global
from babel.dates import get_timezone_location
from markupsafe import Markup, escape
from starlette.requests import Request

_display_timezone: ContextVar[str] = ContextVar("display_timezone", default="UTC")
_device_timezone: ContextVar[str] = ContextVar("device_timezone", default="UTC")
_viewer_time: ContextVar[dict[str, str] | None] = ContextVar("viewer_time", default=None)
_reload_allowed: ContextVar[bool] = ContextVar("time_reload_allowed", default=False)
TIMEZONE_COOKIE = "graf_timezone"
# Explicit read-only pages: never replay callbacks, payment returns or action GETs.
_READ_ONLY_PAGE = re.compile(
    r"^/(?:desktop/)?(?:meetings(?:/[0-9a-fA-F-]{36})?|shared-with-me|"
    r"shared-meetings/[0-9a-fA-F-]{36}|settings(?:/(?:account|calendar|recording|"
    r"summaries|workspace|notifications|integrations/calendar))?|account(?:/(?:profile|security|"
    r"notifications|fair-use|referrals))?|referrals|"
    r"billing(?:/(?:plans|discounts|usage|subscription|payment-method|storage|history)|"
    r"/(?:invoices|checkout/status)/[A-Za-z0-9-]+)?|"
    r"admin(?:/(?:users|files)(?:/[0-9a-fA-F-]{36})?|/(?:balance|metrics|"
    r"meeting-detection|audit))?)$"
)


def validated_timezone(value: str | None) -> str:
    if not value or len(value) > 100 or (value != "UTC" and "/" not in value):
        return "UTC"
    try:
        return ZoneInfo(value).key
    except (ValueError, ZoneInfoNotFoundError):
        return "UTC"


def display_timezone_name() -> str:
    return _display_timezone.get()


def valid_timezone_choice(value: str | None) -> bool:
    return bool(value and len(value) <= 64 and validated_timezone(value) == value)


def apply_user_time_preference(*, user_id: object, session_id: object, timezone: str | None) -> None:
    """Called only after authenticating the viewer, before queries and rendering."""
    preferred = validated_timezone(timezone) if timezone else ""
    _viewer_time.set({"user": str(user_id), "session": str(session_id or ""), "preferred": preferred})
    _display_timezone.set(preferred or _device_timezone.get())


def viewer_time_context() -> dict[str, str]:
    return _viewer_time.get() or {"user": "", "session": "", "preferred": ""}


@lru_cache(maxsize=1)
def _timezone_names() -> dict[str, str]:
    locale = Locale("ru")
    aliases = get_global("zone_aliases")
    # CLDR city translations can still be keyed by an older IANA alias.
    cities = {aliases.get(zone, zone): data["city"] for zone, data in locale.time_zones.items()
              if "city" in data}
    names = {"UTC": "Всемирное координированное время"}
    for zone, territory in get_global("zone_territories").items():
        if territory == "ZZ" or not valid_timezone_choice(zone):
            continue
        city = cities.get(zone) or get_timezone_location(ZoneInfo(zone), locale=locale, return_city=True)
        country = locale.territories.get(territory, territory)
        names[zone] = f"{city}, {country}"
    return names


def timezone_label(zone: str, at: datetime | None = None) -> str:
    zone = validated_timezone(zone)
    instant = at or datetime.now(UTC)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    offset = instant.astimezone(ZoneInfo(zone)).utcoffset()
    minutes = int(offset.total_seconds() / 60) if offset else 0
    sign = "+" if minutes >= 0 else "−"
    hours, minute = divmod(abs(minutes), 60)
    canonical = get_global("zone_aliases").get(zone, zone)
    name = _timezone_names().get(zone) or _timezone_names().get(canonical, zone.replace("_", " "))
    return f"UTC{sign}{hours:02d}:{minute:02d} — {name}"


def timezone_options(selected: str | None = None) -> list[dict[str, str]]:
    zones = set(_timezone_names())
    selected = selected or display_timezone_name()
    if valid_timezone_choice(selected):
        zones.add(selected)
    now = datetime.now(UTC)
    return [{"value": zone, "label": timezone_label(zone, now)} for zone in sorted(
        zones, key=lambda zone: (now.astimezone(ZoneInfo(zone)).utcoffset(), timezone_label(zone, now))
    )]


def time_reload_allowed() -> bool:
    return _reload_allowed.get()


def local_datetime(value: datetime) -> datetime:
    instant = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return instant.astimezone(ZoneInfo(display_timezone_name()))


def format_user_datetime(
    value: datetime | date | str | None,
    *,
    date_only: bool = False,
    time_only: bool = False,
    show_zone: bool = False,
) -> str:
    if value is None or value == "":
        return "Без даты"
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value) if len(value) == 10 else datetime.fromisoformat(value)
        except ValueError:
            return "Без даты"
    if not isinstance(value, datetime):
        return value.strftime("%d.%m.%Y")
    localized = local_datetime(value)
    pattern = "%d.%m.%Y" if date_only else "%H:%M" if time_only else "%d.%m.%Y, %H:%M"
    label = localized.strftime(pattern)
    zone = display_timezone_name()
    if show_zone or zone == "UTC":
        offset = localized.strftime("%z")
        suffix = "UTC" if offset == "+0000" else f"UTC{offset[:3]}:{offset[3:]}"
        return f"{label} ({suffix})"
    return label


def user_time_element(value: datetime | str | None, *, show_zone: bool = False) -> Markup:
    """Semantic, progressively enhanced timestamps, including first visits to share pages."""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            value = None
    if value is None:
        return Markup("Без даты")
    instant = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return Markup('<time datetime="{}" data-user-datetime data-show-zone="{}">{}</time>').format(
        escape(instant.isoformat()), "true" if show_zone else "false",
        escape(format_user_datetime(instant, show_zone=show_zone)),
    )


async def user_time_middleware(request: Request, call_next):
    token = _display_timezone.set(validated_timezone(request.cookies.get(TIMEZONE_COOKIE)))
    device_token = _device_timezone.set(_display_timezone.get())
    viewer_token = _viewer_time.set(None)
    reload_token = _reload_allowed.set(
        request.method == "GET"
        and not request.headers.get("HX-Request")
        and bool(_READ_ONLY_PAGE.fullmatch(request.url.path))
    )
    try:
        return await call_next(request)
    finally:
        _viewer_time.reset(viewer_token)
        _device_timezone.reset(device_token)
        _reload_allowed.reset(reload_token)
        _display_timezone.reset(token)
