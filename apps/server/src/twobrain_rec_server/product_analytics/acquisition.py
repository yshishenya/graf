"""Level 2 attribution: the campaign of a visit and the campaign of a client.

Level 2 works on the basis of the contract with a registered customer
(152-ФЗ п. 5 ч. 1 ст. 6), so it may keep a pseudonym and the campaign the
customer came from. Unlike the level 1 anonymous aggregate, this module is
allowed to use the pseudonyms of
:mod:`twobrain_rec_server.product_analytics.identity` — they belong to level 2
precisely because the person stays determinable for the operator.

Two entities live here (data-model.md, level 2):

* **visit attribution** — campaign labels read from the page address, valid for
  a bounded window of at most 90 days and unusable afterwards;
* **client acquisition attribute** — the campaign copied onto the customer
  record at registration, with the rule that produced it and the reliability of
  the link.

Rules kept here: the window never exceeds 90 days; the "last non-direct source
in the 90-day window" rule is the only attribution rule; an unknown campaign is
``unknown`` and never ``direct`` (FR-018, FR-024); the reference of a visit is
opaque and is not a tracking identifier (FR-014).
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models.product_analytics import (
    ClientAcquisitionAttribute as ClientAcquisitionAttributeRow,
)
from twobrain_rec_server.db.models.product_analytics import (
    PublicVisitAttribution as PublicVisitAttributionRow,
)
from twobrain_rec_server.product_analytics.anonymous_aggregate import (
    PUBLIC_PAGE_SURFACES,
    sanitize_anonymous_aggregate_label,
)
from twobrain_rec_server.product_analytics.forbidden_fields import (
    assert_safe_client_acquisition_attribute,
    assert_safe_visit_attribution,
)
from twobrain_rec_server.product_analytics.identity import stable_pseudonym
from twobrain_rec_server.product_analytics.legal_basis_gate import (
    ATTRIBUTION_PROFILES_LEVEL,
    legal_basis_write_allowed,
)

logger = logging.getLogger(__name__)

ATTRIBUTION_RULE_LAST_NON_DIRECT_90D = "last_non_direct_90d"
ATTRIBUTION_RULES = (ATTRIBUTION_RULE_LAST_NON_DIRECT_90D,)
ATTRIBUTION_WINDOW_DAYS = 90
ATTRIBUTION_CONFIDENCE_LEVELS = ("linked", "weak", "unknown")
ATTRIBUTION_REF_PREFIX = "graf_visit_"
# The browser keeps only a small, session-scoped history of opaque visit
# references.  The bound is part of the server contract as well: auth must never
# turn a caller-controlled collection into an unbounded database lookup.
MAX_VISIT_ATTRIBUTION_REFS = 8
# Durable visit rows are a handoff cache, not a request log. Keep the default
# admission high enough for ordinary paid traffic while bounding an attacker
# that sends a fresh campaign label on every request. The values are runtime
# configurable so the operator can size them from the capacity baseline.
PUBLIC_VISIT_ATTRIBUTION_ADMISSION_LIMIT = 10_000
PUBLIC_VISIT_ATTRIBUTION_ADMISSION_WINDOW_SECONDS = 3_600
PUBLIC_VISIT_ATTRIBUTION_ADMISSION_LOCK_KEY = "graf:public_visit_attribution:admission"
CAMPAIGN_FIELDS = ("source", "medium", "campaign", "content", "term")
# The unique constraint of ``client_acquisition_attributes``: one acquisition
# attribute per account, which is what makes registration idempotent.
CLIENT_ACQUISITION_UNIQUE_CONSTRAINT = "uq_client_acquisition_account"
# Statuses of the visit record handed over by ``read_public_visit_attribution``
# (``public/analytics.py``). Campaign labels exist only for ``saved`` and
# ``current``; a missing or damaged record means "campaign unknown" and never
# "direct" (FR-018, FR-024, FR-059).
KNOWN_VISIT_ATTRIBUTION_STATUSES = ("saved", "current")
# The documented public default of the module. A registration that has no visit
# record at all still needs a landing page — the column is not nullable and
# "no public page was ever seen" is not a public route — so the download page is
# used: it is the published page of the product the visitor came for, not an
# invented visit. Labels stay empty and the confidence stays ``unknown``, so the
# row never reads as a direct entry (FR-018, FR-024).
DEFAULT_PUBLIC_LANDING_PATH = "/download"

# "Прямой заход" is a property of the referrer, not of the campaign: a visit
# without labels is either explicitly direct or simply unknown, and the two are
# never the same value (FR-018, FR-024).
DIRECT_REFERRER_CATEGORY = "direct"
ATTRIBUTION_SOURCE_CAMPAIGN = "campaign"
ATTRIBUTION_SOURCE_DIRECT = DIRECT_REFERRER_CATEGORY
ATTRIBUTION_SOURCE_UNKNOWN = "unknown"


def attribution_window_days() -> int:
    return ATTRIBUTION_WINDOW_DAYS


def resolve_attribution_confidence(
    *,
    campaign_known: bool,
    linked_automatically: bool = False,
    fallback_recovered: bool = False,
) -> str:
    """Return the reliability of the campaign link.

    ``linked`` — the attribute moved to the account at registration or login;
    ``weak`` — recovered through the download-page fallback or across devices;
    ``unknown`` — the campaign is unknown, which is never the same as direct.
    """
    if not campaign_known:
        return "unknown"
    if linked_automatically and not fallback_recovered:
        return "linked"
    return "weak"


def is_within_attribution_window(
    moment: datetime,
    *,
    now: datetime | None = None,
    window_days: int = ATTRIBUTION_WINDOW_DAYS,
) -> bool:
    """Return whether a visit timestamp is live, not stale or from the future."""
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    else:
        reference = reference.astimezone(UTC)
    observed = moment
    observed = (
        observed.replace(tzinfo=UTC) if observed.tzinfo is None else observed.astimezone(UTC)
    )
    # Durable rows expire at ``first_seen_at + window_days``.  Keep this strict
    # lower bound in sync with ``VisitAttribution.is_expired`` at the exact
    # boundary, and reject forged future timestamps as well.
    return reference - timedelta(days=window_days) < observed <= reference


def classify_attribution_source(
    *,
    campaign_known: bool,
    referrer_category: str | None = None,
) -> str:
    """Say what a visit without campaign labels actually is.

    ``campaign`` — the campaign is known and is the recorded source;
    ``direct`` — the visitor arrived without a referrer at all;
    ``unknown`` — nobody knows where the visitor came from.

    A visit is ``direct`` only when the referrer itself is direct. An unknown
    campaign is never reported as a direct entry (FR-018, FR-024).
    """
    if campaign_known:
        return ATTRIBUTION_SOURCE_CAMPAIGN
    if str(referrer_category or "").strip().lower() == DIRECT_REFERRER_CATEGORY:
        return ATTRIBUTION_SOURCE_DIRECT
    return ATTRIBUTION_SOURCE_UNKNOWN


def resolve_last_non_direct_source(
    visits: Iterable[VisitAttribution],
    *,
    now: datetime | None = None,
    window_days: int = ATTRIBUTION_WINDOW_DAYS,
) -> VisitAttribution | None:
    """Pick the last non-direct source inside the attribution window (FR-017).

    This is the single attribution rule of the feature: the same function backs
    the campaign copied onto the customer record and the campaign reported for
    Yandex.Metrica, so both breakdowns agree (SC-008). Visits without campaign
    labels (direct or unknown) are never chosen, an expired visit is never
    reused, and the newest eligible visit wins.
    """
    reference = now or datetime.now(UTC)
    eligible = [
        visit
        for visit in visits
        if visit.campaign_known()
        and is_within_attribution_window(
            visit.first_seen_at, now=reference, window_days=window_days
        )
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda visit: (visit.first_seen_at, visit.attribution_ref))


@dataclass(frozen=True, slots=True)
class VisitAttribution:
    """One visit's campaign labels with a bounded lifetime."""

    attribution_ref: str
    landing_path: str
    first_seen_at: datetime
    expires_at: datetime
    source: str | None = None
    medium: str | None = None
    campaign: str | None = None
    content: str | None = None
    term: str | None = None
    yclid: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return the stored shape, which is also the allowlisted entity shape."""
        return {
            "attribution_ref": self.attribution_ref,
            "source": self.source,
            "medium": self.medium,
            "campaign": self.campaign,
            "content": self.content,
            "term": self.term,
            "yclid": self.yclid,
            "landing_path": self.landing_path,
            "first_seen_at": self.first_seen_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }

    def is_expired(self, *, now: datetime | None = None) -> bool:
        return (now or datetime.now(UTC)) >= self.expires_at

    def campaign_known(self) -> bool:
        """Return whether this visit carries any non-empty campaign signal.

        ``yclid`` is a first-class Yandex campaign identifier.  A visit that
        has only that click id is still attributable and must survive the
        last-non-direct selection used by registration and login.
        """
        return any(getattr(self, field) for field in (*CAMPAIGN_FIELDS, "yclid"))


@dataclass(frozen=True, slots=True)
class ClientAcquisitionAttribute:
    """The campaign recorded on the customer record at registration."""

    account_id: UUID
    account_pseudonym: str
    landing_path: str
    attribution_rule: str
    attribution_confidence: str
    captured_at: datetime
    source: str | None = None
    medium: str | None = None
    campaign: str | None = None
    content: str | None = None
    term: str | None = None
    yclid: str | None = None
    # The bridge the campaign arrived through (FR-022). It is an opaque
    # identifier issued by the product, never an identifier of a person, and it
    # is kept under the same retention term as the campaign it belongs to.
    graf_attribution_id: str | None = None

    def as_storage_dict(self) -> dict[str, Any]:
        """The row as stored in the product database (not an analytics payload)."""
        return {
            "account_id": str(self.account_id),
            "source": self.source,
            "medium": self.medium,
            "campaign": self.campaign,
            "content": self.content,
            "term": self.term,
            "yclid": self.yclid,
            "graf_attribution_id": self.graf_attribution_id,
            "landing_path": self.landing_path,
            "attribution_rule": self.attribution_rule,
            "attribution_confidence": self.attribution_confidence,
            "captured_at": self.captured_at.isoformat(),
        }

    def as_analytics_dict(self) -> dict[str, Any]:
        """The allowlisted view: a pseudonym, never the raw account identifier."""
        return {
            "account_pseudonym": self.account_pseudonym,
            "source": self.source,
            "medium": self.medium,
            "campaign": self.campaign,
            "content": self.content,
            "term": self.term,
            "yclid_present": self.yclid is not None,
            "graf_attribution_id": self.graf_attribution_id,
            "landing_path": self.landing_path,
            "attribution_rule": self.attribution_rule,
            "attribution_confidence": self.attribution_confidence,
            "captured_at": self.captured_at.isoformat(),
        }


def build_visit_attribution(
    *,
    landing_path: str,
    source: Any = None,
    medium: Any = None,
    campaign: Any = None,
    content: Any = None,
    term: Any = None,
    yclid: Any = None,
    first_seen_at: datetime | None = None,
    ttl_days: int = ATTRIBUTION_WINDOW_DAYS,
    attribution_ref: str | None = None,
) -> VisitAttribution:
    """Build the visit attribution of one visit.

    Labels pass the same sanitizer as the level 1 aggregate, so a label that
    looks like an email address, a phone number, a token or a name never
    reaches storage. The window is capped at 90 days and an over-long window is
    refused instead of being silently shortened.
    """
    if landing_path not in PUBLIC_PAGE_SURFACES:
        raise ValueError("visit attribution covers public pages only")
    if attribution_ref is not None and _safe_visit_attribution_ref(attribution_ref) is None:
        raise ValueError("visit attribution reference must be opaque")
    if not 1 <= int(ttl_days) <= ATTRIBUTION_WINDOW_DAYS:
        raise ValueError("visit attribution window must be between 1 and 90 days")
    start = first_seen_at or datetime.now(UTC)
    start = start.replace(tzinfo=UTC) if start.tzinfo is None else start.astimezone(UTC)
    current_time = datetime.now(UTC)
    if start > current_time:
        raise ValueError("visit attribution cannot start in the future")
    attribution = VisitAttribution(
        attribution_ref=attribution_ref or f"{ATTRIBUTION_REF_PREFIX}{uuid4().hex}",
        landing_path=landing_path,
        first_seen_at=start,
        expires_at=start + timedelta(days=int(ttl_days)),
        source=sanitize_anonymous_aggregate_label(_lowered(source)),
        medium=sanitize_anonymous_aggregate_label(_lowered(medium)),
        campaign=sanitize_anonymous_aggregate_label(campaign),
        content=sanitize_anonymous_aggregate_label(content),
        term=sanitize_anonymous_aggregate_label(term),
        yclid=_safe_yclid(yclid),
    )
    assert_safe_visit_attribution(attribution.as_dict())
    return attribution


def build_visit_attribution_from_attribution(
    attribution: Mapping[str, Any] | None,
    *,
    landing_path: str,
    yclid: Any = None,
    first_seen_at: datetime | None = None,
    ttl_days: int = ATTRIBUTION_WINDOW_DAYS,
    attribution_ref: str | None = None,
) -> VisitAttribution:
    """Build the visit attribution from the normalized public attribution mapping."""
    values = attribution or {}
    return build_visit_attribution(
        landing_path=landing_path,
        source=values.get("utm_source"),
        medium=values.get("utm_medium"),
        campaign=values.get("utm_campaign"),
        content=values.get("utm_content"),
        term=values.get("utm_term"),
        yclid=yclid,
        first_seen_at=first_seen_at,
        ttl_days=ttl_days,
        attribution_ref=attribution_ref,
    )


def ensure_visit_attribution_reference(
    attribution: Mapping[str, Any] | None,
    *,
    now: datetime | None = None,
) -> dict[str, str | None]:
    """Attach one opaque reference to a campaign-bearing visit mapping.

    The reference is a server-issued lookup key, not a browser identity.  It is
    created only for a campaign-bearing public visit and is carried in the
    existing session cookie so authentication can look up exactly that visit.
    A mapping without campaign labels stays untouched and therefore cannot
    create a durable anonymous history row.
    """

    values = dict(attribution or {})
    campaign_values = (
        values.get("utm_source"),
        values.get("utm_medium"),
        values.get("utm_campaign"),
        values.get("utm_content"),
        values.get("utm_term"),
        values.get("yclid"),
    )
    if not any(value for value in campaign_values):
        return values
    existing = _safe_visit_attribution_ref(values.get("attribution_ref"))
    if existing is None:
        reference = build_visit_attribution_from_attribution(
            values,
            landing_path=_public_landing_path(values.get("landing_path")),
            yclid=values.get("yclid"),
            first_seen_at=_attribution_moment(values.get("first_seen_at")) or now,
        ).attribution_ref
        values["attribution_ref"] = reference
    else:
        values["attribution_ref"] = existing
    return values


def _visit_attribution_from_row(row: PublicVisitAttributionRow) -> VisitAttribution:
    """Copy only the allowlisted scalar columns out of a database row."""

    return VisitAttribution(
        attribution_ref=row.attribution_ref,
        source=row.source,
        medium=row.medium,
        campaign=row.campaign,
        content=row.content,
        term=row.term,
        yclid=row.yclid,
        landing_path=row.landing_path,
        first_seen_at=row.first_seen_at,
        expires_at=row.expires_at,
    )


async def load_visit_attributions_by_refs(
    session: AsyncSession | None,
    attribution_refs: Iterable[Any],
    *,
    now: datetime | None = None,
) -> tuple[VisitAttribution, ...]:
    """Load only exact, caller-supplied visit references inside the live window.

    The browser normally carries one current reference. This batch primitive is
    also available to a future handoff that explicitly carries several opaque
    references; it never discovers a global latest anonymous row.
    """
    references = tuple(
        dict.fromkeys(
            reference
            for value in attribution_refs
            if (reference := _safe_visit_attribution_ref(value)) is not None
        )
    )[:MAX_VISIT_ATTRIBUTION_REFS]
    if session is None or not references:
        return ()
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    statement = (
        select(PublicVisitAttributionRow)
        .where(
            PublicVisitAttributionRow.attribution_ref.in_(references),
            PublicVisitAttributionRow.first_seen_at <= moment,
            PublicVisitAttributionRow.expires_at > moment,
        )
        .limit(len(references))
    )
    try:
        result = await session.execute(statement)
        rows = result.scalars().all()
    except Exception as exc:  # noqa: BLE001 - attribution must never break auth
        logger.warning(
            "visit attribution history lookup was not available: error=%s",
            exc.__class__.__name__,
        )
        with contextlib.suppress(Exception):
            await session.rollback()
        return ()
    return tuple(_visit_attribution_from_row(row) for row in rows)


async def load_visit_attribution_by_ref(
    session: AsyncSession | None,
    attribution_ref: Any,
    *,
    now: datetime | None = None,
) -> VisitAttribution | None:
    """Load one non-expired visit by its exact opaque reference.

    This is intentionally the only durable lookup used at authentication time:
    there is no "latest visit" query and no way to cross-link two visitors.  A
    missing database or a stale reference is an ordinary attribution gap and
    never breaks sign-in.
    """

    reference = _safe_visit_attribution_ref(attribution_ref)
    if session is None or reference is None:
        return None
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    statement = (
        select(PublicVisitAttributionRow)
        .where(
            PublicVisitAttributionRow.attribution_ref == reference,
            PublicVisitAttributionRow.first_seen_at <= moment,
            PublicVisitAttributionRow.expires_at > moment,
        )
        .limit(1)
    )
    try:
        result = await session.execute(statement)
        row = result.scalar_one_or_none()
    except Exception as exc:  # noqa: BLE001 - attribution must never break auth
        logger.warning(
            "visit attribution lookup was not available: error=%s",
            exc.__class__.__name__,
        )
        with contextlib.suppress(Exception):
            await session.rollback()
        return None
    return _visit_attribution_from_row(row) if row is not None else None


def _positive_setting(settings: Any | None, name: str, default: int) -> int:
    value = getattr(settings, name, default)
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return default


def _session_dialect_name(session: AsyncSession) -> str | None:
    get_bind = getattr(session, "get_bind", None)
    if not callable(get_bind):
        # Small in-process test doubles do not expose a SQLAlchemy bind. The
        # real application database is PostgreSQL; keeping this fallback makes
        # the best-effort writer tests independent of a database implementation.
        return None
    return getattr(get_bind().dialect, "name", None)


async def _admit_visit_attribution_references(
    session: AsyncSession,
    references: Iterable[str],
    *,
    settings: Any | None = None,
) -> tuple[str, ...]:
    """Return references allowed to create or reuse durable rows.

    PostgreSQL's transaction advisory lock serializes the check and the later
    insert across every API process. The lock key is a constant; caller labels
    and references cannot create independent quota buckets. The public response
    remains independent because callers treat an empty result as a measurement
    gap, not as a page error.
    """

    ordered = tuple(dict.fromkeys(references))
    if not ordered or _session_dialect_name(session) != "postgresql":
        return ordered

    await session.execute(
        text("select pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
        {"lock_key": PUBLIC_VISIT_ATTRIBUTION_ADMISSION_LOCK_KEY},
    )
    existing = set(
        (
            await session.scalars(
                select(PublicVisitAttributionRow.attribution_ref).where(
                    PublicVisitAttributionRow.attribution_ref.in_(ordered)
                )
            )
        ).all()
    )
    candidates = [reference for reference in ordered if reference not in existing]
    if not candidates:
        return ordered

    window_seconds = _positive_setting(
        settings,
        "product_analytics_visit_attribution_admission_window_seconds",
        PUBLIC_VISIT_ATTRIBUTION_ADMISSION_WINDOW_SECONDS,
    )
    limit = _positive_setting(
        settings,
        "product_analytics_visit_attribution_admission_limit",
        PUBLIC_VISIT_ATTRIBUTION_ADMISSION_LIMIT,
    )
    window_start = datetime.now(UTC) - timedelta(seconds=window_seconds)
    created = await session.scalar(
        select(func.count(PublicVisitAttributionRow.id)).where(
            PublicVisitAttributionRow.created_at >= window_start
        )
    )
    remaining = max(0, limit - int(created or 0))
    admitted_new = set(candidates[:remaining])
    return tuple(
        reference
        for reference in ordered
        if reference in existing or reference in admitted_new
    )


async def record_visit_attributions_safely(
    session: AsyncSession | None,
    attributions: Iterable[Mapping[str, Any]],
    *,
    now: datetime | None = None,
    commit: bool = True,
    settings: Any | None = None,
    environ: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Persist several exact visit snapshots atomically and idempotently."""
    if not legal_basis_write_allowed(
        ATTRIBUTION_PROFILES_LEVEL,
        settings=settings,
        environ=environ,
    ):
        return ()
    values = [ensure_visit_attribution_reference(item, now=now) for item in attributions]
    visits: list[VisitAttribution] = []
    for item in values:
        reference = _safe_visit_attribution_ref(item.get("attribution_ref"))
        if reference is None:
            continue
        visits.append(
            build_visit_attribution_from_attribution(
                item,
                landing_path=_public_landing_path(item.get("landing_path")),
                yclid=item.get("yclid"),
                first_seen_at=_attribution_moment(item.get("first_seen_at")) or now,
                attribution_ref=reference,
            )
        )
    if session is None or not visits:
        return ()
    try:
        admitted_refs = await _admit_visit_attribution_references(
            session,
            (visit.attribution_ref for visit in visits),
            settings=settings,
        )
        if not admitted_refs:
            return ()
        admitted = set(admitted_refs)
        table = PublicVisitAttributionRow.__table__
        statement = (
            postgresql_insert(table)
            .values(
                [
                    {
                        "id": uuid4(),
                        "attribution_ref": visit.attribution_ref,
                        "source": visit.source,
                        "medium": visit.medium,
                        "campaign": visit.campaign,
                        "content": visit.content,
                        "term": visit.term,
                        "yclid": visit.yclid,
                        "landing_path": visit.landing_path,
                        "first_seen_at": visit.first_seen_at,
                        "expires_at": visit.expires_at,
                    }
                    for visit in visits
                    if visit.attribution_ref in admitted
                ]
            )
            .on_conflict_do_nothing(index_elements=[table.c.attribution_ref])
        )
        await session.execute(statement)
        if commit:
            await session.commit()
        return admitted_refs
    except Exception as exc:  # noqa: BLE001 - measurement must never break a page
        logger.warning(
            "visit attribution history was not recorded: error=%s",
            exc.__class__.__name__,
        )
        with contextlib.suppress(Exception):
            await session.rollback()
        return ()


async def record_visit_attribution_safely(
    session: AsyncSession | None,
    attribution: Mapping[str, Any] | None,
    *,
    now: datetime | None = None,
    commit: bool = True,
    settings: Any | None = None,
    environ: Mapping[str, str] | None = None,
) -> str | None:
    """Persist one campaign-bearing visit without affecting public page delivery."""

    if not legal_basis_write_allowed(
        ATTRIBUTION_PROFILES_LEVEL,
        settings=settings,
        environ=environ,
    ):
        return None
    values = ensure_visit_attribution_reference(attribution, now=now)
    reference = _safe_visit_attribution_ref(values.get("attribution_ref"))
    if session is None or reference is None:
        return None
    landing_path = _public_landing_path(values.get("landing_path"))
    first_seen_at = _attribution_moment(values.get("first_seen_at")) or (now or datetime.now(UTC))
    visit = build_visit_attribution_from_attribution(
        values,
        landing_path=landing_path,
        yclid=values.get("yclid"),
        first_seen_at=first_seen_at,
        attribution_ref=reference,
    )
    try:
        admitted_refs = await _admit_visit_attribution_references(
            session,
            (visit.attribution_ref,),
            settings=settings,
        )
        if reference not in admitted_refs:
            return None
        table = PublicVisitAttributionRow.__table__
        statement = (
            postgresql_insert(table)
            .values(
                id=uuid4(),
                attribution_ref=visit.attribution_ref,
                source=visit.source,
                medium=visit.medium,
                campaign=visit.campaign,
                content=visit.content,
                term=visit.term,
                yclid=visit.yclid,
                landing_path=visit.landing_path,
                first_seen_at=visit.first_seen_at,
                expires_at=visit.expires_at,
            )
            .on_conflict_do_nothing(index_elements=[table.c.attribution_ref])
        )
        await session.execute(statement)
        if commit:
            await session.commit()
        return visit.attribution_ref
    except Exception as exc:  # noqa: BLE001 - measurement must never break a page
        logger.warning(
            "visit attribution was not recorded: error=%s",
            exc.__class__.__name__,
        )
        with contextlib.suppress(Exception):
            await session.rollback()
        return None


def build_client_acquisition_attribute(
    *,
    account_id: UUID,
    landing_path: str,
    source: Any = None,
    medium: Any = None,
    campaign: Any = None,
    content: Any = None,
    term: Any = None,
    yclid: Any = None,
    graf_attribution_id: Any = None,
    captured_at: datetime | None = None,
    attribution_rule: str = ATTRIBUTION_RULE_LAST_NON_DIRECT_90D,
    attribution_confidence: str | None = None,
    linked_automatically: bool = False,
    fallback_recovered: bool = False,
) -> ClientAcquisitionAttribute:
    """Build the acquisition attribute of a customer record."""
    if landing_path not in PUBLIC_PAGE_SURFACES:
        raise ValueError("client acquisition attribute covers public pages only")
    if attribution_rule not in ATTRIBUTION_RULES:
        raise ValueError("unsupported attribution rule")
    values = {
        "source": sanitize_anonymous_aggregate_label(_lowered(source)),
        "medium": sanitize_anonymous_aggregate_label(_lowered(medium)),
        "campaign": sanitize_anonymous_aggregate_label(campaign),
        "content": sanitize_anonymous_aggregate_label(content),
        "term": sanitize_anonymous_aggregate_label(term),
    }
    campaign_known = any(values.values())
    confidence = attribution_confidence or resolve_attribution_confidence(
        campaign_known=campaign_known,
        linked_automatically=linked_automatically,
        fallback_recovered=fallback_recovered,
    )
    if confidence not in ATTRIBUTION_CONFIDENCE_LEVELS:
        raise ValueError("unsupported attribution confidence level")
    attribute = ClientAcquisitionAttribute(
        account_id=account_id,
        account_pseudonym=stable_pseudonym("account", str(account_id)),
        landing_path=landing_path,
        attribution_rule=attribution_rule,
        attribution_confidence=confidence,
        captured_at=captured_at or datetime.now(UTC),
        yclid=_safe_yclid(yclid),
        # The bridge is kept only when it has the shape this module checks and
        # only next to a campaign that really arrived: an identifier without a
        # campaign would be a link to nothing (FR-022, FR-024).
        graf_attribution_id=_safe_attribution_bridge_id(graf_attribution_id) if campaign_known else None,
        **values,
    )
    assert_safe_client_acquisition_attribute(attribute.as_analytics_dict())
    return attribute


def build_client_acquisition_attribute_from_visits(
    *,
    account_id: UUID,
    visits: Iterable[VisitAttribution],
    captured_at: datetime | None = None,
    now: datetime | None = None,
    linked_automatically: bool = False,
    fallback_recovered: bool = False,
) -> ClientAcquisitionAttribute:
    """Copy the campaign of the last non-direct visit onto the customer record.

    The rule is applied by :func:`resolve_last_non_direct_source` only; when no
    visit qualifies, the attribute keeps empty labels and the confidence
    ``unknown`` instead of inventing a source (FR-017, FR-018, FR-024).
    """
    reference = now or captured_at or datetime.now(UTC)
    selected = resolve_last_non_direct_source(visits, now=reference)
    return build_client_acquisition_attribute(
        account_id=account_id,
        landing_path=selected.landing_path if selected else DEFAULT_PUBLIC_LANDING_PATH,
        source=selected.source if selected else None,
        medium=selected.medium if selected else None,
        campaign=selected.campaign if selected else None,
        content=selected.content if selected else None,
        term=selected.term if selected else None,
        yclid=selected.yclid if selected else None,
        captured_at=reference,
        linked_automatically=linked_automatically,
        fallback_recovered=fallback_recovered,
    )


def build_client_acquisition_attribute_from_visit_attribution(
    *,
    account_id: UUID,
    attribution: Mapping[str, Any] | None,
    graf_attribution_id: Any = None,
    captured_at: datetime | None = None,
    now: datetime | None = None,
) -> ClientAcquisitionAttribute:
    """Copy the campaign of the visit onto the customer record at sign-in.

    This is the primary handoff of the feature (FR-015): the labels the browser
    kept for the visit — or the labels the desktop app forwarded from the
    handoff link — are read back by ``read_public_visit_attribution`` and become
    the acquisition attribute of the customer record, with no action from the
    visitor. The same builder serves the first registration and a later sign-in
    of an existing account, and the storage rule keeps the first one (FR-022).

    Three rules decide the result:

    * the record must still be usable — a status outside
      :data:`KNOWN_VISIT_ATTRIBUTION_STATUSES` means "campaign unknown", and an
      unknown campaign is never written as ``direct`` (FR-018, FR-024, FR-059);
    * a record outside the 90-day window is not reusable (FR-017);
    * the attribute is ``linked`` when the campaign is known, because it moved
      to the account automatically at sign-in; otherwise it is ``unknown``.

    An identifier of a Yandex click without campaign labels is still a known
    paid source: the labels stay empty, but the link is not ``unknown``.
    """
    values = attribution or {}
    reference = now or captured_at or datetime.now(UTC)
    status = str(values.get("attribution_status") or "missing").strip().lower()
    labels = {
        "source": values.get("utm_source"),
        "medium": values.get("utm_medium"),
        "campaign": values.get("utm_campaign"),
        "content": values.get("utm_content"),
        "term": values.get("utm_term"),
    }
    yclid = values.get("yclid")
    usable = status in KNOWN_VISIT_ATTRIBUTION_STATUSES and (
        any(_present(label) for label in labels.values()) or _present(yclid)
    )
    if usable and not is_within_attribution_window(
        _attribution_moment(values.get("first_seen_at")) or reference,
        now=reference,
    ):
        usable = False
    return build_client_acquisition_attribute(
        account_id=account_id,
        landing_path=_public_landing_path(values.get("landing_path")),
        source=labels["source"] if usable else None,
        medium=labels["medium"] if usable else None,
        campaign=labels["campaign"] if usable else None,
        content=labels["content"] if usable else None,
        term=labels["term"] if usable else None,
        yclid=yclid if usable else None,
        graf_attribution_id=graf_attribution_id if usable else None,
        captured_at=reference,
        attribution_confidence=resolve_attribution_confidence(
            campaign_known=usable, linked_automatically=True
        ),
    )


async def record_client_acquisition_attribute_safely(
    session: AsyncSession | None,
    attribute: ClientAcquisitionAttribute,
    *,
    commit: bool = False,
    settings: Any | None = None,
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Write the acquisition attribute of a customer record exactly once (FR-015).

    One ``INSERT ... ON CONFLICT (account_id) DO NOTHING``: the campaign that
    brought the customer is written at the first registration, a repeated
    registration neither overwrites it nor creates a second row, and the unique
    constraint ``uq_client_acquisition_account`` keeps one attribute per account.

    Measurement must never break registration (FR-058). The write runs inside its
    own savepoint, so a rejected statement leaves the account, the session and
    everything already written in the same transaction untouched, and the loss
    stays a measurement gap. ``False`` therefore means "not written": either the
    account already carries its campaign, or the write was refused.
    """
    if not legal_basis_write_allowed(
        ATTRIBUTION_PROFILES_LEVEL,
        settings=settings,
        environ=environ,
    ):
        return False
    if session is None:
        return False
    table = ClientAcquisitionAttributeRow.__table__
    statement = (
        postgresql_insert(table)
        .values(
            id=uuid4(),
            account_id=attribute.account_id,
            source=attribute.source,
            medium=attribute.medium,
            campaign=attribute.campaign,
            content=attribute.content,
            term=attribute.term,
            yclid=attribute.yclid,
            graf_attribution_id=attribute.graf_attribution_id,
            landing_path=attribute.landing_path,
            attribution_rule=attribute.attribution_rule,
            attribution_confidence=attribute.attribution_confidence,
            captured_at=attribute.captured_at,
        )
        .on_conflict_do_nothing(constraint=CLIENT_ACQUISITION_UNIQUE_CONSTRAINT)
        .returning(table.c.id)
    )
    try:
        async with session.begin_nested():
            result = await session.execute(statement)
            written = result.scalar_one_or_none() is not None
        if written and commit:
            await session.commit()
        return written
    except Exception as exc:  # noqa: BLE001 - measurement must never reach registration
        logger.warning(
            "client acquisition attribute was not recorded: confidence=%s error=%s",
            attribute.attribution_confidence,
            exc.__class__.__name__,
        )
        return False


def _safe_visit_attribution_ref(value: Any) -> str | None:
    """Accept only the opaque reference shape issued for durable visit rows."""
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate.startswith(ATTRIBUTION_REF_PREFIX):
        return None
    suffix = candidate[len(ATTRIBUTION_REF_PREFIX) :]
    if not 16 <= len(suffix) <= 64 or not all(
        character in "0123456789abcdef" for character in suffix.lower()
    ):
        return None
    return candidate


def _safe_attribution_bridge_id(value: Any) -> str | None:
    """Keep the bridge identifier only in the exact shape the product issues.

    The shape lives in one place — ``attribution.safe_attribution_bridge_id`` —
    and is read at call time, because that module reads this one: a second copy
    of the rule would drift, and a module-level import would close the cycle.
    """
    from twobrain_rec_server.product_analytics.attribution import (  # noqa: PLC0415
        safe_attribution_bridge_id,
    )

    return safe_attribution_bridge_id(value)


def _public_landing_path(value: Any) -> str:
    """Keep a public landing page, or fall back to the documented default."""
    if isinstance(value, str) and value in PUBLIC_PAGE_SURFACES:
        return value
    return DEFAULT_PUBLIC_LANDING_PATH


def _attribution_moment(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _present(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def sanitize_yclid(value: Any) -> str | None:
    """Keep a Yandex click identifier only when it has a sane shape (FR-016)."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not 8 <= len(stripped) <= 120:
        return None
    if not all(character.isalnum() or character in "_-" for character in stripped):
        return None
    return stripped


def _safe_yclid(value: Any) -> str | None:
    return sanitize_yclid(value)


def _lowered(value: Any) -> Any:
    return value.lower() if isinstance(value, str) else value
