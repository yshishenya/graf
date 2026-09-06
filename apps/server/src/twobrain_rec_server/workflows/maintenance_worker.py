"""Maintenance-role loops for durable lifecycle reconciliation."""

from __future__ import annotations

import asyncio
import logging

from twobrain_rec_server.calendar.worker import run_calendar_sync_reconciler
from twobrain_rec_server.config import get_settings
from twobrain_rec_server.system_admin.worker import run_system_operation_reconciler
from twobrain_rec_server.workflows.temporal_client import connect_temporal_client
from twobrain_rec_server.workflows.worker import (
    run_account_closure_reconciler,
    run_billing_notification_reconciler,
    run_billing_reconciliation_reconciler,
    run_billing_renewal_reconciler,
    run_deletion_purge_reconciler,
    run_dispatch_reconciler,
    run_processing_start_reconciler,
)

logger = logging.getLogger(__name__)
TEMPORAL_RETRY_SECONDS = 5


async def run_maintenance_worker() -> None:
    settings = get_settings()
    tasks = [
        asyncio.create_task(run_calendar_sync_reconciler(settings)),
        asyncio.create_task(run_billing_notification_reconciler(settings)),
        asyncio.create_task(_run_temporal_maintenance(settings)),
    ]
    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def _run_temporal_maintenance(settings) -> None:
    """Temporal outages must not stop independent calendar maintenance."""
    while True:
        client = None
        tasks = []
        try:
            client = await connect_temporal_client(settings, identity="graf-maintenance")
            tasks = [
                asyncio.create_task(reconcile(settings, client))
                for reconcile in (
                    run_system_operation_reconciler,
                    run_account_closure_reconciler,
                    run_billing_renewal_reconciler,
                    run_billing_reconciliation_reconciler,
                    run_deletion_purge_reconciler,
                    run_processing_start_reconciler,
                )
            ]
            if settings.outcome_generation_enabled:
                tasks.append(asyncio.create_task(run_dispatch_reconciler(settings, client)))
            await asyncio.gather(*tasks)
        except Exception as error:
            logger.error("Temporal maintenance unavailable; error_type=%s", type(error).__name__)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            close = getattr(client, "close", None)
            if close is not None:
                try:
                    result = close()
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as error:
                    logger.error(
                        "Temporal client close failed; error_type=%s", type(error).__name__
                    )
        await asyncio.sleep(TEMPORAL_RETRY_SECONDS)


def main() -> None:
    asyncio.run(run_maintenance_worker())


if __name__ == "__main__":
    main()
