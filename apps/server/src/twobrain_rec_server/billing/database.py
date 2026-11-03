"""Database identity gate for the existing global payment reconciliation worker."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context


class BillingMaintenanceDatabaseError(RuntimeError):
    """Refuse an invisible or privileged payment reconciliation database."""


async def require_billing_maintenance_database(db: AsyncSession) -> None:
    """Check actual login/active identities and row protection, never a URL hint."""
    if db.get_bind().dialect.name != "postgresql":
        raise BillingMaintenanceDatabaseError(
            "payment reconciliation requires a protected maintenance database role"
        )
    row = (await db.execute(text(
        "select session_user, current_user, current_setting('row_security'), "
        "rolsuper, rolbypassrls, rec_maintenance_allowed(), "
        "current_setting('app.maintenance_operation', true) = 'billing_reconciliation', "
        "current_setting('app.maintenance_feature_area', true) = 'billing' "
        "from pg_roles where rolname = current_user"
    ))).one()
    if (
        row[0] != "twobrain_rec_maintenance"
        or row[1] != "twobrain_rec_maintenance"
        or row[2] != "on"
        or row[3] is not False
        or row[4] is not False
        or row[5] is not True
        or row[6] is not True
        or row[7] is not True
    ):
        raise BillingMaintenanceDatabaseError(
            "payment reconciliation requires a protected maintenance database role"
        )


async def verify_billing_maintenance_database(settings: Settings) -> None:
    """Refuse the poller before it can report a misleading empty success."""
    engine = create_engine(settings)
    try:
        async with create_sessionmaker(engine)() as db:
            await db.execute(text("SET TRANSACTION READ ONLY"))
            await apply_tenant_context(db, MaintenanceTenantContext(
                operation_name="billing_reconciliation",
                actor_id="graf-maintenance",
                reason_category="billing_worker_startup",
                feature_area="billing",
            ))
            await require_billing_maintenance_database(db)
    finally:
        await engine.dispose()
