from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.contract.test_dev_maintenance_database_role import dev_compose, dev_role_helper
from twobrain_rec_server.billing.database import (
    BillingMaintenanceDatabaseError,
    verify_billing_maintenance_database,
)
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context


def test_actual_dev_maintenance_login_passes_guard_and_other_maintenance_contexts(
    postgres_isolated_cluster_database_url, monkeypatch,
):
    owner = make_url(postgres_isolated_cluster_database_url)
    services = dev_compose()["services"]
    configured = make_url(services["rec-maintenance"]["environment"]["TWOBRAIN_DATABASE_URL"])
    monkeypatch.setenv("TWOBRAIN_ENV", "development")
    monkeypatch.setenv("TWOBRAIN_DB_HOST", owner.host)
    monkeypatch.setenv("TWOBRAIN_DB_PORT", str(owner.port))
    monkeypatch.setenv("TWOBRAIN_DB_NAME", owner.database)
    monkeypatch.setenv("TWOBRAIN_DB_OWNER_PASSWORD", owner.password)
    for name in ("APP", "MAINTENANCE", "MEDIA"):
        value = (services.get("rec-db-runtime-bootstrap", {}).get("environment", {})
                 .get(f"TWOBRAIN_DB_{name}_PASSWORD", "synthetic-dev-password"))
        monkeypatch.setenv(f"TWOBRAIN_DB_{name}_PASSWORD", value)

    async def proof():
        if "rec-db-runtime-bootstrap" in services:
            await dev_role_helper(monkeypatch).bootstrap_development_roles()
            await dev_role_helper(monkeypatch).bootstrap_development_roles()
        password = owner.password if configured.username == owner.username else configured.password
        url = owner.set(username=configured.username, password=password).render_as_string(hide_password=False)
        settings = Settings(env="development", database_url=url,
                            billing_checkout_enabled=False, billing_provider_observation_enabled=False)
        await verify_billing_maintenance_database(settings)
        engine = create_async_engine(url)
        try:
            async with async_sessionmaker(engine)() as db:
                row = (await db.execute(text("SELECT session_user, current_user, rolsuper, rolbypassrls, current_setting('row_security') AS rls FROM pg_roles WHERE rolname=current_user"))).mappings().one()
                assert row["session_user"] == row["current_user"] == "twobrain_rec_maintenance"
                assert row["rolsuper"] is False and row["rolbypassrls"] is False and row["rls"] == "on"
                await db.rollback()
                for operation, table in (
                    ("calendar_sync_reconciliation", "calendar_sources"),
                    ("billing_notification_reconciliation", "billing_invoices"),
                    ("deletion_purge_reconciliation", "meeting_deletion_requests"),
                    ("outcome_dispatch_reconciliation", "meetings"),
                    ("processing_recovery_reconciliation", "processing_workflows"),
                ):
                    await apply_tenant_context(db, MaintenanceTenantContext(
                        operation_name=operation, actor_id="dev-role-proof",
                        reason_category="synthetic-validation", feature_area="development",
                    ))
                    assert await db.scalar(text("SELECT rec_maintenance_allowed()")) is True
                    assert await db.scalar(text(f"SELECT count(*) FROM {table}")) is not None
                    await db.rollback()
        finally:
            await engine.dispose()

    asyncio.run(proof())


def test_actual_previous_dev_superuser_login_is_rejected(postgres_isolated_cluster_database_url):
    settings = Settings(env="development", database_url=postgres_isolated_cluster_database_url,
                        billing_checkout_enabled=False, billing_provider_observation_enabled=False)
    with pytest.raises(BillingMaintenanceDatabaseError, match="maintenance database role"):
        asyncio.run(verify_billing_maintenance_database(settings))
