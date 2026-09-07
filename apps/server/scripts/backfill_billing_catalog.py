#!/usr/bin/env python3
"""Operator batch migration; emit counts only, never financial snapshots or credentials."""

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import create_async_engine

from twobrain_rec_server.billing.catalog_migration import backfill_subscription_pins
from twobrain_rec_server.db.models.billing import WorkspaceSubscription
from twobrain_rec_server.db.session import create_sessionmaker
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    maintenance_context_settings,
)


async def run(args: argparse.Namespace) -> dict[str, int]:
    engine = create_async_engine(
        Path(args.database_url_file).read_text().strip(), echo=False, pool_size=1, max_overflow=0
    )
    sessions = create_sessionmaker(engine)
    totals = {"processed": 0, "pinned": 0, "review_required": 0, "not_applicable": 0}
    context = maintenance_context_settings(
        MaintenanceTenantContext(
            operation_name="migration_verification",
            actor_id="billing_catalog_operator",
            reason_category="billing_catalog_migration",
            feature_area="billing",
        )
    )
    try:
        async with sessions() as db:
            db.sync_session.info["tenant_context"] = context
            if not await db.scalar(
                text("select session_user='twobrain_rec_maintenance' and rec_maintenance_allowed()")
            ):
                raise ValueError("Требуется отдельная роль обслуживания БД")
            if args.execute:
                for _ in range(args.max_batches):
                    counts = await backfill_subscription_pins(db, limit=args.batch_size)
                    await db.commit()
                    for key, value in counts.items():
                        totals[key] += value
                    if not counts["processed"]:
                        break
            totals["lag"] = await db.scalar(
                select(func.count())
                .select_from(WorkspaceSubscription)
                .where(
                    or_(
                        WorkspaceSubscription.pin_checked_application_version.is_distinct_from(
                            WorkspaceSubscription.application_version
                        ),
                        WorkspaceSubscription.pin_state == "pending",
                    )
                )
            )
            totals["unresolved"] = await db.scalar(
                select(func.count())
                .select_from(WorkspaceSubscription)
                .where(WorkspaceSubscription.pin_state == "legacy_pinned")
            )
            return totals
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url-file", required=True)
    parser.add_argument(
        "--execute", action="store_true", help="Без флага выводятся только счётчики"
    )
    parser.add_argument(
        "--batch-size", type=int, default=100, choices=range(1, 501), metavar="1..500"
    )
    parser.add_argument(
        "--max-batches", type=int, default=100, choices=range(1, 10001), metavar="1..10000"
    )
    try:
        print(json.dumps(asyncio.run(run(parser.parse_args())), sort_keys=True))
    except Exception:
        # Database exceptions can include bound snapshots or connection details.
        parser.exit(
            1,
            "Миграция не завершена; проверьте роль БД и журнал состояния без публикации секретов.\n",
        )


if __name__ == "__main__":
    main()
