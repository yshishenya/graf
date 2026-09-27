"""Five GB included, explicit five GB packages and future-price consent."""

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import insert

revision = "0101_storage_packages"
down_revision = "0100_billing_purchases"
branch_labels = None
depends_on = None
OFFER_VERSION = "personal-2026-09-27"
STORAGE_BYTES = 5000000000
PROCESSING_MODE = "unlimited"
CURRENCY = "RUB"
APPROVED_ROWS = (
    {"cycle": "month", "amount_minor": 100000},
    {"cycle": "year", "amount_minor": 1000000},
)


def upgrade() -> None:
    op.add_column("workspace_subscriptions", sa.Column("storage_price_consents", sa.JSON()))
    for table, name in (
        ("billing_storage_price_versions", "storage_price_capacity"),
        ("billing_storage_entitlement_grants", "storage_grant_capacity"),
    ):
        op.drop_constraint(op.f(f"ck_{table}_{name}"), table, type_="check")
        op.create_check_constraint(
            op.f(f"ck_{table}_{name}"),
            table,
            "capacity_bytes BETWEEN 5000000000 AND 500000000000 "
            "AND capacity_bytes % 5000000000 = 0",
        )
    _seed_catalog()


def _seed_catalog() -> None:
    connection = op.get_bind()
    metadata = sa.MetaData()
    storage = sa.Table("billing_storage_price_versions", metadata, autoload_with=connection)
    plans = sa.Table("billing_plan_versions", metadata, autoload_with=connection)
    # Only sale availability changes. Historical amounts, IDs and grants remain intact.
    connection.execute(
        storage.update().where(storage.c.version < 2).values(enabled_for_checkout=False)
    )
    rows = []
    for count in range(1, 100):
        for cycle, price in (("month", 25000), ("year", 250000)):
            rows.append(
                {
                    "id": uuid5(NAMESPACE_URL, f"graf:storage:packages:v2:{count}:{cycle}"),
                    "version": 2,
                    "capacity_bytes": (count + 1) * 5000000000,
                    "cycle": cycle,
                    "amount_minor": count * price,
                    "currency": "RUB",
                    "enabled_for_checkout": True,
                    "effective_from": datetime(2026, 9, 27, tzinfo=UTC),
                    "policy_snapshot": {
                        "offer_version": "personal-2026-09-27",
                        "capacity_kind": "total",
                        "package_count": count,
                        "package_bytes": 5000000000,
                        "package_amount_minor": price,
                    },
                }
            )
    connection.execute(insert(storage).on_conflict_do_nothing(index_elements=["id"]), rows)
    version = (
        connection.scalar(
            sa.select(sa.func.max(plans.c.version)).where(plans.c.plan_code == "personal")
        )
        or 0
    )
    connection.execute(
        plans.update()
        .where(plans.c.plan_code == "personal", plans.c.storage_bytes != STORAGE_BYTES)
        .values(enabled_for_checkout=False)
    )
    for offset, (cycle, amount) in enumerate((("month", 100000), ("year", 1000000)), 1):
        if connection.scalar(
            sa.select(plans.c.id).where(
                plans.c.id == uuid5(NAMESPACE_URL, f"graf:personal:packages:2026-09-27:{cycle}")
            )
        ):
            continue
        connection.execute(
            plans.insert().values(
                id=uuid5(NAMESPACE_URL, f"graf:personal:packages:2026-09-27:{cycle}"),
                plan_code="personal",
                version=version + offset,
                cycle=cycle,
                amount_minor=amount,
                currency="RUB",
                storage_bytes=5000000000,
                processing_mode="unlimited",
                enabled_for_checkout=True,
                policy_snapshot={"offer_version": "personal-2026-09-27"},
            )
        )


def downgrade() -> None:
    raise RuntimeError(
        "Financial catalogue versions and accepted prices must be preserved. "
        "Disable checkout and roll back application code after payment reconciliation; "
        "do not delete financial history."
    )
