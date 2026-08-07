"""One-shot, restart-safe billing maintenance projection.

The scheduler owns cadence; this function owns only bounded, idempotent DB
maintenance. It never creates a payment, changes provider authority, or sends
customer content.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.promotions import expire_promo_reservations
from twobrain_rec_server.billing.referral_rewards import mature_pending_credits
from twobrain_rec_server.billing.storage import release_expired_storage_reservations
from twobrain_rec_server.db.models import WorkspaceSubscription


async def reconcile_billing_maintenance(
    db: AsyncSession,
    *,
    now: datetime | None = None,
    workspace_id: UUID | None = None,
) -> dict[str, int]:
    """Run one bounded maintenance pass and return counters only."""
    current = (now or datetime.now(UTC)).astimezone(UTC)
    expired_promos = await expire_promo_reservations(db, now=current)
    matured_credits = await mature_pending_credits(db, now=current)
    query = select(WorkspaceSubscription.workspace_id)
    if workspace_id is not None:
        query = query.where(WorkspaceSubscription.workspace_id == workspace_id)
    released_reservations = 0
    for current_workspace_id in await db.scalars(query):
        released_reservations += await release_expired_storage_reservations(
            db,
            workspace_id=current_workspace_id,
            now=current,
        )
    await db.flush()
    return {
        "expired_promos": expired_promos,
        "matured_credits": matured_credits,
        "released_storage_reservations": released_reservations,
    }
