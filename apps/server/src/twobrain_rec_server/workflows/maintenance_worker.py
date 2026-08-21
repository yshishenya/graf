"""Maintenance-role loops for durable lifecycle reconciliation."""

from __future__ import annotations

import asyncio
import logging

from twobrain_rec_server.calendar.worker import run_calendar_sync_reconciler
from twobrain_rec_server.config import get_settings
from twobrain_rec_server.workflows.temporal_client import connect_temporal_client
from twobrain_rec_server.workflows.worker import (
    run_account_closure_reconciler,
    run_billing_notification_reconciler,
    run_billing_reconciliation_reconciler,
    run_billing_renewal_reconciler,
    run_deletion_purge_reconciler,
    run_dispatch_reconciler,
    run_legacy_processing_lineage_reconciler,
)

logger = logging.getLogger(__name__)


async def run_maintenance_worker() -> None:
    settings = get_settings()
    temporal_client = await connect_temporal_client(settings, identity="graf-maintenance")
    tasks = [
        asyncio.create_task(run_account_closure_reconciler(settings, temporal_client)),
        asyncio.create_task(run_billing_renewal_reconciler(settings, temporal_client)),
        asyncio.create_task(run_billing_reconciliation_reconciler(settings, temporal_client)),
        asyncio.create_task(run_billing_notification_reconciler(settings)),
        asyncio.create_task(run_deletion_purge_reconciler(settings, temporal_client)),
        asyncio.create_task(run_legacy_processing_lineage_reconciler(settings)),
        asyncio.create_task(run_calendar_sync_reconciler(settings)),
    ]
    if settings.outcome_generation_enabled:
        tasks.append(asyncio.create_task(run_dispatch_reconciler(settings, temporal_client)))
    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        close = getattr(temporal_client, "close", None)
        if close is not None:
            result = close()
            if asyncio.iscoroutine(result):
                await result


def main() -> None:
    asyncio.run(run_maintenance_worker())


if __name__ == "__main__":
    main()
