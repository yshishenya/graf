"""Internal operator import/status. Dry-run by default, metadata-only output."""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from datetime import date
from pathlib import Path

from asyncpg import PostgresError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from twobrain_rec_server.billing.database import (
    BillingMaintenanceDatabaseError,
    require_billing_maintenance_database,
)
from twobrain_rec_server.billing.registry import RegistryInputError, read_registry_files
from twobrain_rec_server.billing.registry_store import persist_registry, registry_status
from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    maintenance_context_settings,
)


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's normal message can contain CSV paths or operator-supplied text.
        self.exit(2, json.dumps({"result_code": "invalid_arguments"}) + "\n")


def build_parser():
    parser = SafeParser(description="Внутренняя проверка реестров; финансовая сверка отдельно")
    commands = parser.add_subparsers(dest="command", required=True, parser_class=SafeParser)
    status = commands.add_parser("status")
    status.add_argument("--date", required=True, type=date.fromisoformat)
    command = commands.add_parser("import")
    command.add_argument("--date", required=True, type=date.fromisoformat)
    for kind in ("payments", "refunds"):
        command.add_argument(f"--{kind}", action="append", type=Path, default=[])
    command.add_argument("--expect-empty", choices=("payments", "refunds"), action="append", default=[])
    command.add_argument("--owner", required=True)
    command.add_argument("--operator", required=True)
    command.add_argument("--replace")
    command.add_argument("--reason", choices=("initial_import", "corrected_export", "missing_parts_recovered", "revalidated_export"), default="initial_import")
    command.add_argument("--execute", action="store_true")
    return parser


async def run(args, *, settings=None):
    settings = settings or get_settings()
    scope = {"environment": settings.billing_yookassa_environment,
             "shop_id": settings.billing_yookassa_shop_id, "report_date": args.date}
    if not scope["shop_id"] or not re.fullmatch(r"[0-9]{1,32}", scope["shop_id"]):
        return {"result_code": "invalid_scope"}, 2
    if args.command == "import" and (
        any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value) for value in (args.owner, args.operator))
        or (args.replace is not None and (not re.fullmatch(r"[a-f0-9]{64}", args.replace) or args.reason == "initial_import"))
    ):
        return {"result_code": "invalid_arguments"}, 2
    engine = None
    try:
        engine = create_engine(settings)
        async with create_sessionmaker(engine)() as db:
            db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                operation_name="billing_reconciliation", feature_area="billing",
                actor_id=args.operator if args.command == "import" else "registry-status",
                reason_category="registry_import" if args.command == "import" else "registry_status"))
            async with db.begin():
                if args.command == "status" or not args.execute:
                    await db.execute(text("SET TRANSACTION READ ONLY"))
                await require_billing_maintenance_database(db)
                if args.command == "status":
                    return await registry_status(db, **scope), 0
                bundle, error_code = None, None
                expected_empty = frozenset(args.expect_empty)
                try:
                    bundle = read_registry_files({"payments": args.payments, "refunds": args.refunds},
                                                 **scope, expected_empty=expected_empty)
                except RegistryInputError as exc:
                    error_code = str(exc)
                if not args.execute:
                    return {"dry_run": True, "files_complete": bundle.files_complete if bundle else False,
                            "input_digest": bundle.input_digest if bundle else None,
                            "result_code": error_code or "validated", "financial_status": "not_checked"}, 1 if error_code else 0
                return await persist_registry(db, **scope, bundle=bundle, expected_empty=expected_empty,
                                              error_code=error_code, owner=args.owner, operator=args.operator,
                                              replace_digest=args.replace, reason=args.reason)
    except BillingMaintenanceDatabaseError:
        return {"result_code": "database_identity_rejected"}, 1
    except (SQLAlchemyError, PostgresError, OSError):
        # No driver traceback: it can include connection URLs and SQL values.
        return {"result_code": "database_unavailable"}, 1
    finally:
        if engine is not None:
            await engine.dispose()


def main():
    result, code = asyncio.run(run(build_parser().parse_args()))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
