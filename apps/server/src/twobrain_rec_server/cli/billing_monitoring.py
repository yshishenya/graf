"""Internal, bounded, read-only billing observation. No provider or mail calls."""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import create_async_engine

from twobrain_rec_server.billing.database import BillingMaintenanceDatabaseError
from twobrain_rec_server.billing.monitoring import ReportLimitError, collect_billing_report
from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.session import create_sessionmaker
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    maintenance_context_settings,
)

REPORT_TIMEOUT_SECONDS = 15
MAX_OUTPUT_BYTES = 64 * 1024


def failure(code):
    return {"schema_version": 1, "result_code": code}


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, json.dumps(failure("invalid_arguments")) + "\n")


def build_parser():
    parser = SafeParser(description="Внутренний отчёт по объявленным источникам биллинга")
    parser.add_argument("--date", required=True, type=_report_date)
    return parser


def _report_date(value):
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("invalid date")
    return date.fromisoformat(value)


def serialize(result):
    output = json.dumps(result, ensure_ascii=False, sort_keys=True)
    if len((output + "\n").encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise ReportLimitError
    return output


async def run(args, *, settings=None):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + REPORT_TIMEOUT_SECONDS
    terminate_at_deadline = None
    try:
        async with asyncio.timeout_at(deadline):
            settings = settings or get_settings()
            shop = settings.billing_yookassa_shop_id
            if (not shop or not re.fullmatch(r"[0-9]{1,32}", shop)
                    or settings.billing_yookassa_environment not in {"test", "production"}):
                return failure("invalid_scope"), 2
            scope = {"environment": settings.billing_yookassa_environment,
                     "shop_id": shop, "report_date": args.date}
            as_of = datetime.now(UTC)
            # Driver options apply before SQLAlchemy's first SELECT/tenant hook.
            engine = create_async_engine(settings.database_url, execution_options={
                "isolation_level": "REPEATABLE READ", "postgresql_readonly": True,
            }, connect_args={"server_settings": {
                "statement_timeout": "5000", "lock_timeout": "2000",
                "default_transaction_read_only": "on",
                "default_transaction_isolation": "repeatable read",
            }})
            db = create_sessionmaker(engine)()
            driver = None
            connection = None
            db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                operation_name="billing_reconciliation", actor_id="billing-observation",
                reason_category="operator_diagnostics", feature_area="billing",
            ))
            try:
                connection = await db.connection()
                driver = (await connection.get_raw_connection()).driver_connection
                # Socket termination is synchronous: a stalled rollback cannot
                # outlive the deadline. Disconnect rolls back this read-only txn.
                terminate_at_deadline = loop.call_at(deadline, driver.terminate)
                result = await collect_billing_report(db, scope=scope, as_of=as_of)
                result["finished_at"] = datetime.now(UTC).isoformat()
                serialize(result)
            except BaseException as error:
                if driver is not None and (isinstance(error, asyncio.CancelledError) or loop.time() >= deadline):
                    driver.terminate()
                raise
            finally:
                try:
                    # Close explicitly; Session.__aexit__ shields close(), which
                    # otherwise survives the collector's delivered cancellation.
                    async with asyncio.timeout_at(deadline):
                        await db.close()
                except BaseException:
                    if driver is not None:
                        driver.terminate()
                    # Drop the already terminated connection from SQLAlchemy's
                    # checkout as well. A failed close may already have detached
                    # the Session transaction, so retain the Connection itself.
                    if connection is not None and not connection.closed:
                        await connection.invalidate()
                    await db.invalidate()
                    raise
                finally:
                    async with asyncio.timeout_at(deadline):
                        await engine.dispose()
            return result, 0
    except BillingMaintenanceDatabaseError:
        return failure("database_identity_rejected"), 1
    except ReportLimitError:
        return failure("report_limit_exceeded"), 1
    except TimeoutError:
        return failure("report_timeout"), 1
    except asyncio.CancelledError:
        raise
    except Exception:
        # Settings/driver/schema errors may contain credentials, SQL and row data.
        return failure("report_unavailable"), 1
    finally:
        if terminate_at_deadline is not None:
            terminate_at_deadline.cancel()


def main():
    try:
        result, code = asyncio.run(run(build_parser().parse_args()))
    except KeyboardInterrupt:
        result, code = failure("report_cancelled"), 1
    print(serialize(result))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
