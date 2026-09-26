"""Level 1 anonymous page aggregate: counting visits without any identifier.

**This module MUST NOT import** ``twobrain_rec_server.product_analytics.identity``.
The pseudonyms built there (``graf_pseudo_user_<sha256(salt + raw_id)>``) are
pseudonymisation, not anonymisation: the salt is a constant in the code and the
raw identifier stays in the product database, so the person remains
determinable without additional information. Level 1 gets its legal basis
exactly from the absence of identifiers, therefore any reuse of ``identity.py``
— or of any other stable value — destroys that basis (research.md §1).

What that means for every value that reaches a bucket:

* only the dimensions listed in ``data-model.md`` are stored, and only in
  aggregate form, with a visit counter;
* no device address, session or visit identifier, user-agent string, device
  fingerprint, cookie value or pseudonym is accepted — the aggregate is checked
  by :mod:`twobrain_rec_server.product_analytics.forbidden_fields` before it is
  written;
* campaign labels come from the page address, so they are untrusted: they pass
  :func:`sanitize_anonymous_aggregate_label`, which bounds length, restricts the
  character set and drops values that look like contact details or a person's
  name;
* the device class is computed here and only the coarse category is stored; the
  user-agent string itself is never stored anywhere;
* buckets smaller than :data:`MINIMUM_AGGREGATE_BUCKET_SIZE` are not disclosed
  in reports (FR-057), so a lone visitor cannot be read out of a report.

Writing follows research.md §2 and §3: one synchronous PostgreSQL
``INSERT ... ON CONFLICT DO UPDATE`` by bucket key, no network call, no queue
and no dependency on the analytics stack, so the public page never waits for
analytics.

Internal, support, test and automated traffic is still counted, but it carries
its own ``traffic_class`` and reports read only the reported classes (FR-013).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models.product_analytics import (
    AnonymousPageAggregateBucket as AnonymousPageAggregateBucketRow,
)
from twobrain_rec_server.product_analytics.forbidden_fields import (
    assert_no_anonymous_aggregate_identifiers,
)
from twobrain_rec_server.product_analytics.legal_basis_gate import (
    ANONYMOUS_AGGREGATE_LEVEL,
    legal_basis_write_allowed,
)
from twobrain_rec_server.product_analytics.traffic_class import (
    DEFAULT_TRAFFIC_CLASS,
    REPORTED_TRAFFIC_CLASSES,
    is_reportable_traffic,
    normalize_traffic_class,
)

# Public routes of the marketing site. A path outside this list is never
# counted: the aggregate covers public pages only, and an unknown path is a
# programming error rather than a silent new dimension. The pages with a
# credential form are public too, so they are counted as pages like the others:
# what is counted is the visit, never a typed value (FR-027).
PUBLIC_PAGE_SURFACES = {
    "/": "public_landing",
    "/download": "public_download",
    "/privacy": "public_privacy",
    "/cookies": "public_cookies",
    "/terms": "public_terms",
    "/offer": "public_offer",
    "/analytics-consent": "public_analytics_consent",
    "/sign-up": "public_signup",
    "/login": "public_login",
}
PUBLIC_PAGE_PATHS = tuple(PUBLIC_PAGE_SURFACES)
ANONYMOUS_AGGREGATE_SURFACES = tuple(PUBLIC_PAGE_SURFACES.values())
# Steps of web registration (FR-020) are counted by the same anonymous counter
# as a visit, but they carry their own surface. The published page list does not
# change: a registration step is not a page of the site, so it can never be read
# as a page view, and the landing page of the step stays the public page the
# visit started from. The step catalog is closed, so a typo cannot create a new
# measurement dimension silently.
WEB_REGISTRATION_STEP_STARTED = "signup_step_viewed"
WEB_REGISTRATION_STEP_COMPLETED = "signup_completed"
WEB_REGISTRATION_STEP_FAILED = "signup_failed"
WEB_REGISTRATION_STEP_SURFACES = {
    WEB_REGISTRATION_STEP_STARTED: "public_signup_step_viewed",
    WEB_REGISTRATION_STEP_COMPLETED: "public_signup_completed",
    WEB_REGISTRATION_STEP_FAILED: "public_signup_failed",
}
WEB_REGISTRATION_STEPS = tuple(WEB_REGISTRATION_STEP_SURFACES)
# The delivery of the installer file (FR-019) is counted by the same anonymous
# counter, again with its own surface: opening the download page is a page view,
# while the number of files that really reached the browser is a different fact,
# and only the two together show a link that is clicked but does not work.
INSTALLER_DELIVERY_SURFACE = "public_installer_delivery"
DEVICE_CLASSES = ("desktop", "mobile", "tablet", "unknown")
REFERRER_CATEGORIES = ("direct", "organic", "paid", "referral", "unknown")
CAMPAIGN_LABEL_FIELDS = ("source", "medium", "campaign", "content", "term")
MAX_ANONYMOUS_AGGREGATE_LABEL_LENGTH = 96
# FR-057: a bucket smaller than this is not disclosed in reports.
MINIMUM_AGGREGATE_BUCKET_SIZE = 3
AGGREGATE_BUCKET_CONSTRAINT = "uq_anonymous_page_aggregate_bucket"

_SAFE_LABEL_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,95}$")
_LABEL_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
# A phone-shaped label either starts with ``+`` or separates its digit groups;
# a bare digit run of ten or more is dropped as well, so a phone written
# without separators is not stored as a campaign label.
_LABEL_PHONE_RE = re.compile(
    r"(?:\+\d[\d\s().-]{7,}\d)|(?:\d{1,4}[\s().-]\d[\d\s().-]{5,}\d)|(?:^\d{10,}$)"
)
_LABEL_SECRET_RE = re.compile(
    r"(access[_-]?token|refresh[_-]?token|id[_-]?token|api[_-]?key|secret|password|passcode|signed[_-]?url|signature)",
    re.IGNORECASE,
)
# A person's name: capitalized parts joined together ("IvanPetrov",
# "Ivan.Petrov", "Ivan_Petrov") or two lowercase alphabetic parts joined by a
# dot ("ivan.petrov"). Cyrillic labels never pass the character set, so a name
# written in Russian is dropped by the character rule.
_LABEL_NAME_RE = re.compile(
    r"^(?:[A-Z][a-z]{1,20})(?:[._-]?[A-Z][a-z]{1,20}){1,2}$|^[a-z]{3,15}\.[a-z]{3,15}$"
)
_UNSAFE_LABEL_MARKERS = ("://", "/", "\\", "?", "#", "@", " ")

logger = logging.getLogger(__name__)

_TABLET_MARKERS = ("ipad", "tablet", "kindle", "silk/", "playbook", "nexus 7", "nexus 10")
_MOBILE_MARKERS = (
    "mobile",
    "iphone",
    "ipod",
    "android",
    "windows phone",
    "blackberry",
    "opera mini",
)


def surface_for_public_path(path: str) -> str | None:
    """Return the surface of a public route, or ``None`` for a private one."""
    return PUBLIC_PAGE_SURFACES.get(_normalized_path(path))


def registration_step_surface(step: str) -> str:
    """Return the aggregate surface of one step of web registration (FR-020).

    An unknown step is refused rather than counted: the catalog is closed, so a
    misspelled step cannot turn into a new dimension of the funnel.
    """
    try:
        return WEB_REGISTRATION_STEP_SURFACES[step]
    except KeyError as exc:
        raise ValueError(f"unknown web registration step: {step}") from exc


def device_class_from_user_agent(user_agent: str | None) -> str:
    """Reduce a user-agent string to a coarse class; the string itself is dropped."""
    if not user_agent:
        return "unknown"
    lowered = user_agent.lower()
    if any(marker in lowered for marker in _TABLET_MARKERS):
        return "tablet"
    if "android" in lowered and "mobile" not in lowered:
        return "tablet"
    if any(marker in lowered for marker in _MOBILE_MARKERS):
        return "mobile"
    if any(marker in lowered for marker in ("macintosh", "mac os x", "windows", "linux", "x11", "cros")):
        return "desktop"
    return "unknown"


def sanitize_anonymous_aggregate_label(value: Any) -> str | None:
    """Return a safe campaign label, or ``None`` when the value must be dropped.

    The single source of truth for both layers: the public page context uses it
    to stop a hostile label (``?utm_campaign=<email>``) from being handed to the
    browser, and the aggregate uses it again before a value reaches a bucket.
    """
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped or len(stripped) > MAX_ANONYMOUS_AGGREGATE_LABEL_LENGTH:
        return None
    if any(marker in stripped for marker in _UNSAFE_LABEL_MARKERS):
        return None
    if _LABEL_EMAIL_RE.search(stripped) or _LABEL_PHONE_RE.search(stripped):
        return None
    if _LABEL_SECRET_RE.search(stripped) or _LABEL_NAME_RE.fullmatch(stripped):
        return None
    if not _SAFE_LABEL_RE.fullmatch(stripped):
        return None
    return stripped


def is_disclosed_bucket(
    visits: int,
    *,
    minimum_bucket_size: int = MINIMUM_AGGREGATE_BUCKET_SIZE,
) -> bool:
    """Return whether a bucket may appear in a report (FR-057)."""
    return visits >= minimum_bucket_size


@dataclass(frozen=True, slots=True)
class AnonymousAggregateBucket:
    """One aggregate bucket: dimensions plus a visit counter, nothing else."""

    bucket_date: date
    surface: str
    landing_path: str
    device_class: str
    referrer_category: str
    traffic_class: str = DEFAULT_TRAFFIC_CLASS
    bucket_hour: int | None = None
    source: str | None = None
    medium: str | None = None
    campaign: str | None = None
    content: str | None = None
    term: str | None = None
    visits: int = 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "bucket_date": self.bucket_date.isoformat(),
            "bucket_hour": self.bucket_hour,
            "surface": self.surface,
            "landing_path": self.landing_path,
            "source": self.source,
            "medium": self.medium,
            "campaign": self.campaign,
            "content": self.content,
            "term": self.term,
            "device_class": self.device_class,
            "referrer_category": self.referrer_category,
            "traffic_class": self.traffic_class,
            "visits": self.visits,
        }

    def as_row(self) -> dict[str, Any]:
        """Return the values of the stored row (shape of the database table)."""
        return {
            "id": uuid4(),
            "bucket_date": self.bucket_date,
            "bucket_hour": self.bucket_hour,
            "surface": self.surface,
            "landing_path": self.landing_path,
            "source": self.source,
            "medium": self.medium,
            "campaign": self.campaign,
            "content": self.content,
            "term": self.term,
            "device_class": self.device_class,
            "referrer_category": self.referrer_category,
            "traffic_class": self.traffic_class,
            "visits": self.visits,
        }

    def bucket_key(self) -> tuple[Any, ...]:
        return (
            self.bucket_date,
            self.bucket_hour,
            self.surface,
            self.landing_path,
            self.source,
            self.medium,
            self.campaign,
            self.content,
            self.term,
            self.device_class,
            self.referrer_category,
            self.traffic_class,
        )

    def is_reportable(self) -> bool:
        return is_reportable_traffic(self.traffic_class)


def build_anonymous_aggregate_bucket(
    *,
    path: str,
    occurred_at: datetime | None = None,
    bucket_hour: int | None = None,
    source: Any = None,
    medium: Any = None,
    campaign: Any = None,
    content: Any = None,
    term: Any = None,
    referrer_category: Any = None,
    device_class: Any = None,
    traffic_class: Any = None,
    visits: int = 1,
) -> AnonymousAggregateBucket:
    """Build one bucket from request-time values, dropping anything unsafe."""
    normalized_path = _normalized_path(path)
    surface = surface_for_public_path(normalized_path)
    if surface is None:
        raise ValueError("anonymous aggregate covers public pages only")
    moment = occurred_at or datetime.now(UTC)
    if bucket_hour is not None and not 0 <= int(bucket_hour) <= 23:
        raise ValueError("aggregate bucket hour must be between 0 and 23")
    if int(visits) < 1:
        raise ValueError("aggregate bucket visits must be positive")
    bucket = AnonymousAggregateBucket(
        bucket_date=moment.astimezone(UTC).date() if moment.tzinfo else moment.date(),
        bucket_hour=int(bucket_hour) if bucket_hour is not None else None,
        surface=surface,
        landing_path=normalized_path,
        # ``source`` and ``medium`` are lowercased exactly as the public
        # attribution normalizer does it, so a direct caller cannot lose a
        # legitimate label such as "Yandex_Direct".
        source=sanitize_anonymous_aggregate_label(_lowered(source)),
        medium=sanitize_anonymous_aggregate_label(_lowered(medium)),
        campaign=sanitize_anonymous_aggregate_label(campaign),
        content=sanitize_anonymous_aggregate_label(content),
        term=sanitize_anonymous_aggregate_label(term),
        device_class=_known_value(device_class, DEVICE_CLASSES, "unknown"),
        referrer_category=_known_value(referrer_category, REFERRER_CATEGORIES, "unknown"),
        traffic_class=normalize_traffic_class(traffic_class),
        visits=int(visits),
    )
    assert_no_anonymous_aggregate_identifiers(bucket.as_dict())
    return bucket


def build_anonymous_aggregate_bucket_from_attribution(
    attribution: Mapping[str, Any] | None,
    *,
    path: str,
    occurred_at: datetime | None = None,
    bucket_hour: int | None = None,
    device_class: Any = None,
    traffic_class: Any = None,
) -> AnonymousAggregateBucket:
    """Build a bucket from the normalized public campaign attribution mapping."""
    values = attribution or {}
    return build_anonymous_aggregate_bucket(
        path=path,
        occurred_at=occurred_at,
        bucket_hour=bucket_hour,
        source=values.get("utm_source"),
        medium=values.get("utm_medium"),
        campaign=values.get("utm_campaign"),
        content=values.get("utm_content"),
        term=values.get("utm_term"),
        referrer_category=values.get("referrer_category"),
        device_class=device_class,
        traffic_class=traffic_class,
    )


async def record_anonymous_aggregate_bucket(
    session: AsyncSession,
    bucket: AnonymousAggregateBucket,
    *,
    commit: bool = True,
    settings: Any | None = None,
    environ: Mapping[str, str] | None = None,
) -> int | None:
    """Insert or increment one bucket with a single statement and return its count.

    One ``INSERT ... ON CONFLICT DO UPDATE`` by bucket key: no network call, no
    queue and no background worker, so the public page never depends on the
    analytics stack. The counter is committed immediately by default, because a
    visit rolled back at the end of the request was never counted; pass
    ``commit=False`` only when the caller already owns the transaction.
    """
    if not legal_basis_write_allowed(
        ANONYMOUS_AGGREGATE_LEVEL,
        settings=settings,
        environ=environ,
    ):
        return None
    assert_no_anonymous_aggregate_identifiers(bucket.as_dict())
    table = AnonymousPageAggregateBucketRow.__table__
    statement = (
        postgresql_insert(table)
        .values(**bucket.as_row())
        .on_conflict_do_update(
            constraint=AGGREGATE_BUCKET_CONSTRAINT,
            set_={"visits": table.c.visits + bucket.visits, "updated_at": func.now()},
        )
        .returning(table.c.visits)
    )
    result = await session.execute(statement)
    visits = int(result.scalar_one())
    if commit:
        await session.commit()
    return visits


async def record_anonymous_aggregate_bucket_safely(
    session: AsyncSession | None,
    bucket: AnonymousAggregateBucket,
    *,
    commit: bool = True,
    settings: Any | None = None,
    environ: Mapping[str, str] | None = None,
) -> int | None:
    """Count one bucket without ever letting measurement break the page (FR-058).

    The write itself stays exactly one synchronous ``INSERT ... ON CONFLICT DO
    UPDATE`` with no network call, no queue and no provider access. This wrapper
    only adds the failure rule the public page needs: an unavailable database, a
    closed session or a rejected statement is logged and swallowed, so a visitor
    still gets the page while the missing count stays a measurement gap.

    ``None`` means "not counted"; the caller must not retry, retry would turn one
    broken write into a request-path loop.
    """
    if session is None:
        return None
    try:
        return await record_anonymous_aggregate_bucket(
            session,
            bucket,
            commit=commit,
            settings=settings,
            environ=environ,
        )
    except Exception as exc:  # noqa: BLE001 - measurement must never reach the visitor
        logger.warning(
            "anonymous aggregate bucket was not recorded: surface=%s error=%s",
            bucket.surface,
            exc.__class__.__name__,
        )
        return None


def reportable_aggregate_criteria(
    *,
    minimum_bucket_size: int = MINIMUM_AGGREGATE_BUCKET_SIZE,
) -> tuple[Any, ...]:
    """Return the SQL criteria every report over the aggregate must apply.

    Two rules are inseparable from a report (FR-013, FR-057): only reported
    traffic classes are read, and a bucket below the minimum size is not
    disclosed. Both live here so report code cannot apply one without the other.
    """
    table = AnonymousPageAggregateBucketRow.__table__
    return (
        table.c.traffic_class.in_(tuple(REPORTED_TRAFFIC_CLASSES)),
        table.c.visits >= int(minimum_bucket_size),
    )


def build_minimum_bucket_size_disclosure(*, suppressed_buckets: int = 0) -> dict[str, Any]:
    """Report caveat text for the minimum bucket size rule (FR-057)."""
    return {
        "minimum_bucket_size": MINIMUM_AGGREGATE_BUCKET_SIZE,
        "suppressed_buckets": int(suppressed_buckets),
        "caveat": (
            "Buckets with fewer visits than the minimum bucket size are not disclosed, "
            "so the reported totals are a lower bound."
        ),
    }


async def select_reportable_aggregate_buckets(
    session: AsyncSession,
    *,
    bucket_date_from: date | None = None,
    bucket_date_to: date | None = None,
    minimum_bucket_size: int = MINIMUM_AGGREGATE_BUCKET_SIZE,
    limit: int = 5000,
) -> list[dict[str, Any]]:
    """Read report rows: reported traffic classes only, disclosed buckets only."""
    table = AnonymousPageAggregateBucketRow.__table__
    statement = select(table).where(*reportable_aggregate_criteria(
        minimum_bucket_size=minimum_bucket_size
    ))
    if bucket_date_from is not None:
        statement = statement.where(table.c.bucket_date >= bucket_date_from)
    if bucket_date_to is not None:
        statement = statement.where(table.c.bucket_date <= bucket_date_to)
    statement = statement.order_by(table.c.bucket_date, table.c.surface).limit(int(limit))
    result = await session.execute(statement)
    rows = [
        {
            "bucket_date": row.bucket_date.isoformat(),
            "bucket_hour": row.bucket_hour,
            "surface": row.surface,
            "landing_path": row.landing_path,
            "source": row.source,
            "medium": row.medium,
            "campaign": row.campaign,
            "content": row.content,
            "term": row.term,
            "device_class": row.device_class,
            "referrer_category": row.referrer_category,
            "traffic_class": row.traffic_class,
            "visits": row.visits,
        }
        for row in result
    ]
    # Defence in depth: the rule is re-applied in Python, so a later change to
    # the statement cannot quietly disclose a small bucket.
    return [
        row
        for row in rows
        if is_disclosed_bucket(row["visits"], minimum_bucket_size=minimum_bucket_size)
    ]


async def sum_reportable_aggregate_visits(
    session: AsyncSession,
    *,
    surface: str | None = None,
    bucket_date_from: date | None = None,
    bucket_date_to: date | None = None,
    minimum_bucket_size: int = MINIMUM_AGGREGATE_BUCKET_SIZE,
) -> int:
    """Сумма визитов по раскрытым корзинам уровня 1 (FR-009, FR-012, FR-057).

    Это знаменатель доли согласия: он не зависит от согласия и потому считает
    всех посетителей, включая отказавшихся. Читаются только отчитываемые классы
    трафика и только раскрытые корзины, поэтому сумма является нижней границей, а
    не точным числом, и оговорка об этом выдается вместе с долей.
    """
    table = AnonymousPageAggregateBucketRow.__table__
    statement = select(func.coalesce(func.sum(table.c.visits), 0)).where(
        *reportable_aggregate_criteria(minimum_bucket_size=minimum_bucket_size)
    )
    if surface is not None:
        statement = statement.where(table.c.surface == surface)
    if bucket_date_from is not None:
        statement = statement.where(table.c.bucket_date >= bucket_date_from)
    if bucket_date_to is not None:
        statement = statement.where(table.c.bucket_date <= bucket_date_to)
    result = await session.execute(statement)
    return int(result.scalar_one() or 0)


async def sum_reportable_aggregate_visits_by_campaign(
    session: AsyncSession,
    *,
    surface: str,
    bucket_date_from: date | None = None,
    bucket_date_to: date | None = None,
    minimum_bucket_size: int = MINIMUM_AGGREGATE_BUCKET_SIZE,
) -> dict[str, int]:
    """Визиты по метке кампании для одного разреза уровня 1.

    Разрез называется вызывающим: например ``public_installer_delivery`` дает
    состоявшиеся скачивания по кампании, которые стоимость результата соединяет
    с расходом кабинета. Корзина без метки кампании в результат не попадает: ее
    нельзя сопоставить, и приписывать ее кампании было бы выдумкой.
    """
    table = AnonymousPageAggregateBucketRow.__table__
    statement = (
        select(table.c.campaign, func.coalesce(func.sum(table.c.visits), 0))
        .where(
            *reportable_aggregate_criteria(minimum_bucket_size=minimum_bucket_size),
            table.c.surface == surface,
            table.c.campaign.is_not(None),
        )
        .group_by(table.c.campaign)
    )
    if bucket_date_from is not None:
        statement = statement.where(table.c.bucket_date >= bucket_date_from)
    if bucket_date_to is not None:
        statement = statement.where(table.c.bucket_date <= bucket_date_to)
    result = await session.execute(statement)
    return {str(campaign): int(visits) for campaign, visits in result.all() if visits}


def _known_value(value: Any, allowed: tuple[str, ...], fallback: str) -> str:
    if isinstance(value, str):
        normalized = value.strip().lower().replace("-", "_")
        if normalized in allowed:
            return normalized
    return fallback


def _lowered(value: Any) -> Any:
    return value.lower() if isinstance(value, str) else value


def _normalized_path(path: Any) -> str:
    if not isinstance(path, str):
        return ""
    normalized = path.strip()
    if len(normalized) > 1:
        normalized = normalized.rstrip("/") or "/"
    return normalized
