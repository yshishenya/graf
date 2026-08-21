from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.catalog import (
    CatalogNotApproved,
    PlanCatalogSnapshot,
    validate_plan_version,
)
from twobrain_rec_server.billing.launch_gates import (
    BillingLaunchBlocked,
    require_current_billing_launch_gates,
)
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import BillingPlanVersion

PUBLIC_MONTHLY_AMOUNT_MINOR = 100_000
PUBLIC_ANNUAL_AMOUNT_MINOR = 1_000_000
PUBLIC_TRIAL_DAYS = 7
# This revision is the one published by the current /offer legal page. A
# catalog row with exact prices but another revision must not enable public
# sale claims for this release.
PUBLIC_APPROVED_OFFER_VERSION = "personal-2026-08-21"


@dataclass(frozen=True, slots=True)
class PublicOfferView:
    catalog_ready: bool = False
    sale_ready: bool = False
    monthly_amount_minor: int | None = None
    annual_amount_minor: int | None = None
    monthly_label: str | None = None
    annual_label: str | None = None
    annual_saving_minor: int | None = None
    annual_saving_label: str | None = None
    annual_monthly_equivalent_label: str | None = None
    offer_version: str | None = None
    trial_days: int = PUBLIC_TRIAL_DAYS


def unavailable_public_offer() -> PublicOfferView:
    return PublicOfferView()


def _rubles_label(amount_minor: int) -> str:
    return f"{amount_minor // 100:,}".replace(",", " ") + " ₽"


async def build_public_offer_view(
    db: AsyncSession | None,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> PublicOfferView:
    """Return public pricing only from the same approved catalog used by checkout."""

    if db is None:
        return unavailable_public_offer()
    current = (now or datetime.now(UTC)).astimezone(UTC)
    try:
        rows = list(
            await db.scalars(
                select(BillingPlanVersion)
                .where(
                    BillingPlanVersion.plan_code == "personal",
                    BillingPlanVersion.cycle.in_(("month", "year")),
                )
                .order_by(BillingPlanVersion.cycle, BillingPlanVersion.version.desc())
            )
        )
    except (OSError, SQLAlchemyError):
        # Public pages remain available if the catalog database is unavailable.
        # Paid copy must fail closed instead of advertising an unverified sale.
        return unavailable_public_offer()
    approved_by_cycle: dict[str, PlanCatalogSnapshot] = {}
    for row in rows:
        if row.cycle in approved_by_cycle:
            continue
        try:
            approved_by_cycle[row.cycle] = validate_plan_version(row, now=current)
        except (CatalogNotApproved, ValueError):
            # A future, expired, disabled or malformed newest version must
            # not hide an older version that is currently effective. This is
            # the same first-valid-row selection used by checkout.
            continue
    month = approved_by_cycle.get("month")
    year = approved_by_cycle.get("year")
    if month is None or year is None:
        return unavailable_public_offer()
    if not _matching_public_catalog(month, year):
        return unavailable_public_offer()

    saving_minor = PUBLIC_MONTHLY_AMOUNT_MINOR * 12 - PUBLIC_ANNUAL_AMOUNT_MINOR
    sale_ready = False
    if (
        settings.billing_checkout_enabled
        and not settings.billing_emergency_stop
        and settings.billing_yookassa_shop_id
    ):
        try:
            await require_current_billing_launch_gates(
                db,
                environment=settings.billing_yookassa_environment,
                shop_id=settings.billing_yookassa_shop_id,
                deployment_sha=settings.langfuse_release,
                now=current,
            )
        except (BillingLaunchBlocked, OSError, SQLAlchemyError, ValueError):
            pass
        else:
            sale_ready = True
    return PublicOfferView(
        catalog_ready=True,
        sale_ready=sale_ready,
        monthly_amount_minor=PUBLIC_MONTHLY_AMOUNT_MINOR,
        annual_amount_minor=PUBLIC_ANNUAL_AMOUNT_MINOR,
        monthly_label=_rubles_label(PUBLIC_MONTHLY_AMOUNT_MINOR),
        annual_label=_rubles_label(PUBLIC_ANNUAL_AMOUNT_MINOR),
        annual_saving_minor=saving_minor,
        annual_saving_label=_rubles_label(saving_minor),
        annual_monthly_equivalent_label=_rubles_label(PUBLIC_ANNUAL_AMOUNT_MINOR // 12),
        offer_version=month.offer_version,
    )


def _matching_public_catalog(month: PlanCatalogSnapshot, year: PlanCatalogSnapshot) -> bool:
    return bool(
        month.amount_minor == PUBLIC_MONTHLY_AMOUNT_MINOR
        and year.amount_minor == PUBLIC_ANNUAL_AMOUNT_MINOR
        and month.currency == year.currency == "RUB"
        and month.storage_bytes == year.storage_bytes
        and month.processing_mode == year.processing_mode == "unlimited"
        and month.offer_version == year.offer_version
        and month.offer_version == PUBLIC_APPROVED_OFFER_VERSION
    )
