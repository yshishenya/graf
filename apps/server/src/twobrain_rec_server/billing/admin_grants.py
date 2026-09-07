"""Non-monetary access assignments and deterministic commercial precedence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.catalog import (
    CAPABILITY_BOOLEANS,
    EXPORT_FORMATS,
    validate_capabilities,
)
from twobrain_rec_server.db.models.billing import (
    BillingAccessAdjustment,
    BillingAccessRevocation,
    BillingPlanVersion,
)
from twobrain_rec_server.db.models.identity import Workspace

BOOLEAN_FEATURES = CAPABILITY_BOOLEANS - {"processing_unlimited"}
QUOTA_UNITS = {"processing_seconds": "seconds", "storage_bytes": "bytes"}


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("access time must be timezone-aware")
    return value.astimezone(UTC)


def _timezone(value: str) -> ZoneInfo:
    try:
        return ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
        raise ValueError("invalid billing timezone") from exc


def add_calendar_days(moment: datetime, *, days: int, timezone: str) -> datetime:
    if type(days) is not int or not 1 <= days <= 3650:
        raise ValueError("gift duration must be between 1 and 3650 calendar days")
    # Calendar arithmetic preserves the local wall time across DST. A nonexistent
    # spring-forward time normalizes forward when converted to UTC and back.
    return (_utc(moment).astimezone(_timezone(timezone)) + timedelta(days=days)).astimezone(UTC)


def _source(
    source_kind: str, source_ref: str, reason: str, admin_operation_id: UUID | None
) -> None:
    if source_kind not in ("admin", "promotion", "migration") or (source_kind == "admin") != (
        admin_operation_id is not None
    ):
        raise ValueError("access source is invalid")
    if (
        not isinstance(source_ref, str)
        or re.fullmatch(r"[A-Za-z0-9:_-]{1,160}", source_ref) is None
    ):
        raise ValueError("access source reference is invalid")
    if not isinstance(reason, str) or not 10 <= len(reason.strip()) <= 500:
        raise ValueError("access reason must contain 10 to 500 characters")


async def create_adjustment(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    kind: str,
    starts_at: datetime,
    ends_at: datetime,
    source_kind: str,
    source_ref: str,
    reason: str,
    subject_user_id: UUID | None = None,
    feature_key: str | None = None,
    value: int | bool | None = None,
    unit: str | None = None,
    plan_version_id: UUID | None = None,
    plan_mode: str | None = None,
    timezone: str = "UTC",
    admin_operation_id: UUID | None = None,
    adjustment_id: UUID | None = None,
) -> BillingAccessAdjustment:
    """Caller commits the claimed system command and this immutable source together."""
    _source(source_kind, source_ref, reason, admin_operation_id)
    starts, ends = _utc(starts_at), _utc(ends_at)
    _timezone(timezone)
    if ends <= starts:
        raise ValueError("access interval is empty")
    if kind == "plan_interval":
        if (
            plan_version_id is None
            or plan_mode not in ("append", "overlay")
            or any(item is not None for item in (feature_key, value, unit))
        ):
            raise ValueError("plan interval requires an explicit version and placement")
    else:
        if plan_version_id is not None or plan_mode is not None:
            raise ValueError("feature assignment cannot select a plan")
        if kind in ("allow", "deny"):
            if (
                feature_key not in BOOLEAN_FEATURES
                or type(value) is not bool
                or value != (kind == "allow")
                or unit != "boolean"
            ):
                raise ValueError("boolean assignment is invalid")
        elif kind in ("extra_quota", "exact_limit"):
            minimum = 1 if kind == "extra_quota" or feature_key == "storage_bytes" else 0
            if (
                feature_key not in QUOTA_UNITS
                or unit != QUOTA_UNITS[feature_key]
                or type(value) is not int
                or not minimum <= value <= 9_000_000_000_000_000
            ):
                raise ValueError("quota assignment is invalid")
        else:
            raise ValueError("unknown access assignment")
    values = dict(
        workspace_id=workspace_id,
        subject_user_id=subject_user_id,
        kind=kind,
        feature_key=feature_key,
        value=value,
        unit=unit,
        plan_version_id=plan_version_id,
        plan_mode=plan_mode,
        starts_at=starts,
        ends_at=ends,
        timezone=timezone,
        source_kind=source_kind,
        source_ref=source_ref,
        admin_operation_id=admin_operation_id,
        reason=reason.strip(),
    )
    # Same lock is used by the database overlap guard and revocations.
    if (
        await db.scalar(select(Workspace.id).where(Workspace.id == workspace_id).with_for_update())
        is None
    ):
        raise ValueError("access workspace unavailable")
    existing = await db.scalar(
        select(BillingAccessAdjustment).where(
            BillingAccessAdjustment.source_kind == source_kind,
            BillingAccessAdjustment.source_ref == source_ref,
        )
    )
    if existing is not None:
        if any(getattr(existing, key) != val for key, val in values.items()) or (
            adjustment_id is not None and existing.id != adjustment_id
        ):
            raise ValueError("access idempotency conflict")
        return existing
    row = BillingAccessAdjustment(id=adjustment_id or uuid4(), **values)
    db.add(row)
    await db.flush()
    return row


async def revoke_adjustment(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    adjustment_id: UUID,
    source_kind: str,
    source_ref: str,
    reason: str,
    admin_operation_id: UUID | None = None,
    revocation_id: UUID | None = None,
) -> BillingAccessRevocation:
    _source(source_kind, source_ref, reason, admin_operation_id)
    await db.scalar(select(Workspace.id).where(Workspace.id == workspace_id).with_for_update())
    original = await db.scalar(
        select(BillingAccessAdjustment).where(
            BillingAccessAdjustment.id == adjustment_id,
            BillingAccessAdjustment.workspace_id == workspace_id,
        )
    )
    if original is None:
        raise ValueError("access source unavailable")
    values = dict(
        workspace_id=workspace_id,
        adjustment_id=adjustment_id,
        source_kind=source_kind,
        source_ref=source_ref,
        admin_operation_id=admin_operation_id,
        reason=reason.strip(),
    )
    existing = await db.scalar(
        select(BillingAccessRevocation).where(
            or_(
                BillingAccessRevocation.adjustment_id == adjustment_id,
                (BillingAccessRevocation.source_kind == source_kind)
                & (BillingAccessRevocation.source_ref == source_ref),
            )
        )
    )
    if existing is not None:
        if any(getattr(existing, key) != val for key, val in values.items()) or (
            revocation_id is not None and existing.id != revocation_id
        ):
            raise ValueError("access revocation idempotency conflict")
        return existing
    row = BillingAccessRevocation(id=revocation_id or uuid4(), **values)
    db.add(row)
    await db.flush()
    return row


@dataclass(frozen=True, slots=True)
class ExtraQuota:
    id: UUID
    feature_key: str
    value: int
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AccessResolution:
    capabilities: dict[str, object]
    applied_ids: tuple[UUID, ...]
    extra_quotas: tuple[ExtraQuota, ...]
    plan_version_id: UUID | None
    plan_ends_at: datetime | None
    denied_features: frozenset[str]


async def resolve_adjustments(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    subject_user_id: UUID | None,
    base_capabilities: dict[str, object],
    now: datetime,
    hard_denies: frozenset[str] = frozenset(),
) -> AccessResolution:
    """Commercial permissions never cancel a mandatory product/workspace deny.

    Processing extras stay separate from the base ceiling so reservation allocation
    can debit each source once. Stored consumption is never modified by this read.
    """
    capabilities = validate_capabilities(base_capabilities)
    if not hard_denies <= BOOLEAN_FEATURES | {"processing_seconds"}:
        raise ValueError("unsupported mandatory access restriction")
    current = _utc(now)
    rows = list(
        await db.scalars(
            select(BillingAccessAdjustment)
            .where(
                BillingAccessAdjustment.workspace_id == workspace_id,
                or_(
                    BillingAccessAdjustment.subject_user_id.is_(None),
                    BillingAccessAdjustment.subject_user_id == subject_user_id,
                ),
                BillingAccessAdjustment.starts_at <= current,
                BillingAccessAdjustment.ends_at > current,
                ~exists(
                    select(1).where(
                        BillingAccessRevocation.adjustment_id == BillingAccessAdjustment.id
                    )
                ),
            )
            .order_by(BillingAccessAdjustment.ends_at, BillingAccessAdjustment.id)
            .limit(501)
        )
    )
    # ponytail: bounded evaluator; consolidate overlapping sources before raising the 500-source ceiling.
    if len(rows) > 500:
        raise ValueError("too many simultaneous access sources")
    plans = [row for row in rows if row.kind == "plan_interval"]
    if len(plans) > 1:
        raise ValueError("ambiguous overlapping plan intervals")
    if plans:
        plan = await db.get(BillingPlanVersion, plans[0].plan_version_id)
        if (
            plan is None
            or plan.status not in ("published", "retired")
            or plan.capability_schema_version != 1
        ):
            raise ValueError("assigned plan unavailable")
        capabilities = validate_capabilities(plan.capabilities)
    exact = set()
    denied = set(hard_denies)
    extras = []
    for row in rows:
        if row.kind == "exact_limit":
            if row.feature_key in exact:
                raise ValueError("ambiguous exact access limit")
            exact.add(row.feature_key)
            capabilities[row.feature_key] = row.value
            if row.feature_key == "processing_seconds":
                capabilities["processing_unlimited"] = False
        elif row.kind == "allow":
            capabilities[row.feature_key] = True
            if row.feature_key == "content_export" and not capabilities["export_formats"]:
                capabilities["export_formats"] = sorted(EXPORT_FORMATS)
        elif row.kind == "deny":
            denied.add(row.feature_key)
        elif row.kind == "extra_quota":
            extras.append(ExtraQuota(row.id, row.feature_key, row.value, row.ends_at))
    capabilities["storage_bytes"] += sum(
        source.value for source in extras if source.feature_key == "storage_bytes"
    )
    for key in denied:
        if key == "processing_seconds":
            capabilities[key] = 0
            capabilities["processing_unlimited"] = False
            extras = [source for source in extras if source.feature_key != key]
        else:
            capabilities[key] = False
    if not capabilities["content_export"]:
        capabilities["export_formats"] = []
    return AccessResolution(
        validate_capabilities(capabilities),
        tuple(row.id for row in rows),
        tuple(extras),
        plans[0].plan_version_id if plans else None,
        plans[0].ends_at if plans else None,
        frozenset(denied),
    )
