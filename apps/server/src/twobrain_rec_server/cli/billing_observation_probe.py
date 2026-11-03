"""Fixed internal read-only source command; no global application settings."""
import asyncio
import json
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine

from twobrain_rec_server.billing.observation_alerts import closed, uuid
from twobrain_rec_server.billing.observation_probe import collect_probe
from twobrain_rec_server.db.session import create_sessionmaker
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    maintenance_context_settings,
)


async def run(config):
    closed(config, {"source_profile", "source_generation", "database_url"})
    uuid(config["source_profile"])
    uuid(config["source_generation"])
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 15
    timer = driver = engine = db = connection = None
    try:
        async with asyncio.timeout_at(deadline):
            engine = create_async_engine(config["database_url"], hide_parameters=True,
                execution_options={"isolation_level": "REPEATABLE READ", "postgresql_readonly": True},
                connect_args={"timeout": 15, "server_settings": {"statement_timeout": "5000", "lock_timeout": "2000",
                    "default_transaction_read_only": "on", "default_transaction_isolation": "repeatable read"}})

            @event.listens_for(engine.sync_engine, "do_connect")
            def capture(dialect, _record, args, params):
                nonlocal timer, driver
                adapted = dialect.loaded_dbapi.connect(*args, **params)
                driver = adapted.driver_connection
                timer = loop.call_at(deadline, driver.terminate)
                return adapted

            db = create_sessionmaker(engine)()
            db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                operation_name="billing_reconciliation", actor_id="billing-observation",
                reason_category="operator_diagnostics", feature_area="billing"))
            connection = await db.connection()
            return await collect_probe(db, source_profile=config["source_profile"], source_generation=config["source_generation"])
    except BaseException:
        if driver is not None:
            driver.terminate()
        raise
    finally:
        try:
            if db is not None:
                try:
                    async with asyncio.timeout_at(deadline):
                        await db.close()
                except BaseException:
                    if driver is not None:
                        driver.terminate()
                    if connection is not None and not connection.closed:
                        await connection.invalidate()
                    await db.invalidate()
                    raise
        finally:
            try:
                if engine is not None:
                    async with asyncio.timeout_at(deadline):
                        await engine.dispose()
            finally:
                if timer is not None:
                    timer.cancel()


def main():
    from twobrain_rec_server.cli.billing_observation_alerts import read_protected

    try:
        config = read_protected(Path("/run/secrets/billing-observation-source.json"))
        result = asyncio.run(run(config))
        code = 0
    except (Exception, KeyboardInterrupt):
        result, code = {"schema_version": 1, "result_code": "observation_unavailable"}, 1
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
