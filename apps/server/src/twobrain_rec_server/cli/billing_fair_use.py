"""Internal fair-use intake: explicit execution and metadata-only results."""
from __future__ import annotations

import asyncio
import json
import re
from datetime import UTC, datetime
from uuid import UUID

from asyncpg import PostgresError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from twobrain_rec_server.billing.database import BillingMaintenanceDatabaseError
from twobrain_rec_server.billing.fair_use import (
    create_operator_review,
    create_review,
    resolve_persisted_review,
)
from twobrain_rec_server.cli.billing_registry import SafeParser
from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    maintenance_context_settings,
)


def _operator_ref(value):
    if not re.fullmatch(r"op-[0-9a-f]{32}", value):
        raise ValueError("invalid operator reference")
    return value


def _evidence_ref(value):
    create_review(capability="server_processing", reason="resale", evidence_ref=value,
                  starts_at=datetime.now(UTC))
    return value


def parse_args(argv=None):
    parser = SafeParser(description="Внутреннее рассмотрение fair-use", allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True, parser_class=SafeParser)
    for name in ("create", "resolve"):
        command = commands.add_parser(name, allow_abbrev=False)
        command.add_argument("--workspace", type=UUID, required=True)
        command.add_argument("--evidence-ref", type=_evidence_ref, required=True)
        command.add_argument("--operator-ref", type=_operator_ref, required=True)
        command.add_argument("--evidence-reviewed", action="store_true", required=True)
        command.add_argument("--execute", action="store_true")
        if name == "create":
            command.add_argument("--subject", type=UUID, required=True)
            command.add_argument("--capability", choices=("server_processing", "storage"), required=True)
            command.add_argument("--reason", choices=("automated_bulk", "resale", "limit_circumvention", "security_abuse"), required=True)
        else:
            command.add_argument("--decision", choices=("cleared", "confirmed"), required=True)
            command.add_argument("--resolution-code", choices=("not_substantiated", "no_longer_applicable", "basis_confirmed"), required=True)
    args = parser.parse_args(argv)
    if args.command == "resolve" and ((args.decision == "confirmed") != (args.resolution_code == "basis_confirmed")):
        parser.error("invalid resolution")
    return args


async def run(args, *, settings=None):
    engine = None
    try:
        settings = settings or get_settings()
        engine = create_engine(settings)
        async with create_sessionmaker(engine)() as db:
            db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                operation_name="billing_reconciliation", feature_area="billing",
                actor_id="fair-use-operator", reason_category="fair_use_review",
            ))
            async with db.begin():
                if not args.execute:
                    await db.execute(text("SET TRANSACTION READ ONLY"))
                await db.execute(text("SET LOCAL statement_timeout = '5s'"))
                await db.execute(text("SET LOCAL lock_timeout = '1s'"))
                common = dict(workspace_id=args.workspace, evidence_ref=args.evidence_ref,
                              operator_ref=args.operator_ref, evidence_reviewed=args.evidence_reviewed,
                              execute=args.execute)
                if args.command == "create":
                    status, changed = await create_operator_review(
                        db, **common, subject_user_id=args.subject,
                        capability=args.capability, reason=args.reason,
                    )
                else:
                    status, changed = await resolve_persisted_review(
                        db, **common, decision=args.decision, resolution_code=args.resolution_code,
                    )
            # A return inside begin() could incorrectly classify a failed commit.
            return {"result_code": "validated" if not args.execute else "applied" if changed else "unchanged",
                    "dry_run": not args.execute, "status": status}, 0
    except BillingMaintenanceDatabaseError:
        return {"result_code": "database_identity_rejected"}, 1
    except (ValueError, OverflowError):
        return {"result_code": "review_rejected"}, 1
    except (SQLAlchemyError, PostgresError, OSError):
        return {"result_code": "database_unavailable"}, 1
    finally:
        if engine is not None:
            try:
                await engine.dispose()
            except (SQLAlchemyError, PostgresError, OSError):
                return {"result_code": "database_unavailable"}, 1


def main():
    result, code = asyncio.run(run(parse_args()))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
