"""Seed the approved personal plan catalog rows.

The public landing, the cabinet checkout and the renewal planner all read the
approved prices from ``billing_plan_versions``. Until this migration the rows
existed only as a manual step on a single production host, so any rebuilt,
restored or freshly provisioned environment silently lost the public price
block and could not start a payment at all.

The insert is idempotent and never overwrites an operator-managed row.
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "0093_billing_catalog_seed"
down_revision: str = "0092_recording_origin_cancel"
branch_labels: str | None = None
depends_on: str | None = None

# The published offer revision. A catalog row with other prices or another
# revision must not enable public sale claims, so this value is written
# verbatim and guarded by a test against the application constant.
OFFER_VERSION = "personal-2026-08-21"
STORAGE_BYTES = 2_000_000_000
PROCESSING_MODE = "unlimited"
CURRENCY = "RUB"

APPROVED_ROWS = (
    {"version": 1, "cycle": "month", "amount_minor": 100_000},
    {"version": 2, "cycle": "year", "amount_minor": 1_000_000},
)

_INSERT = sa.text(
    """
    insert into billing_plan_versions (
        id, plan_code, version, cycle, amount_minor, currency,
        storage_bytes, processing_mode, enabled_for_checkout,
        policy_snapshot, effective_from, effective_until
    ) values (
        :id, :plan_code, :version, :cycle, :amount_minor, :currency,
        :storage_bytes, :processing_mode, true,
        :policy_snapshot, null, null
    )
    on conflict (plan_code, version) do nothing
    """
).bindparams(sa.bindparam("policy_snapshot", type_=sa.JSON()))


def _delete_seeded_rows() -> None:
    """Remove only rows that still carry exactly the seeded values."""

    for row in APPROVED_ROWS:
        op.execute(
            sa.text(
                """
                delete from billing_plan_versions
                where plan_code = 'personal'
                  and version = :version
                  and cycle = :cycle
                  and amount_minor = :amount_minor
                  and currency = :currency
                  and storage_bytes = :storage_bytes
                  and processing_mode = :processing_mode
                  and policy_snapshot ->> 'offer_version' = :offer_version
                """
            ).bindparams(
                version=row["version"],
                cycle=row["cycle"],
                amount_minor=row["amount_minor"],
                currency=CURRENCY,
                storage_bytes=STORAGE_BYTES,
                processing_mode=PROCESSING_MODE,
                offer_version=OFFER_VERSION,
            )
        )


def upgrade() -> None:
    for row in APPROVED_ROWS:
        op.execute(
            _INSERT.bindparams(
                id=uuid.uuid4(),
                plan_code="personal",
                version=row["version"],
                cycle=row["cycle"],
                amount_minor=row["amount_minor"],
                currency=CURRENCY,
                storage_bytes=STORAGE_BYTES,
                processing_mode=PROCESSING_MODE,
                policy_snapshot={"offer_version": OFFER_VERSION},
            )
        )


def downgrade() -> None:
    _delete_seeded_rows()
