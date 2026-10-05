"""Maintenance-role loops for durable lifecycle reconciliation."""

from __future__ import annotations

import asyncio
import logging

from twobrain_rec_server.billing.database import (
    BillingMaintenanceDatabaseError,
    verify_billing_maintenance_database,
)
from twobrain_rec_server.cabinet.summary_autosend import (
    list_autosend_readiness_candidates,
    reconcile_meeting_autosend,
)
from twobrain_rec_server.calendar.worker import run_calendar_sync_reconciler
from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context
from twobrain_rec_server.workflows.billing_reconciliation_workflow import (
    BILLING_RECONCILIATION_ACTIVITY_NAME,
    BillingReconciliationWorkflow,
    billing_reconciliation_task_queue,
)
from twobrain_rec_server.workflows.summary_delivery import reconcile_summary_delivery_once
from twobrain_rec_server.workflows.temporal_client import connect_temporal_client
from twobrain_rec_server.workflows.worker import (
    run_account_closure_reconciler,
    run_billing_notification_reconciler,
    run_billing_reconciliation_activity,
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
    await verify_billing_maintenance_database(settings)
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


def _create_billing_reconciliation_worker(settings: Settings, client):
    from temporalio import activity
    from temporalio.worker import Worker

    @activity.defn(name=BILLING_RECONCILIATION_ACTIVITY_NAME)
    async def reconcile(payload: dict[str, str]) -> dict[str, int | str]:
        return await run_billing_reconciliation_activity(payload)

    return Worker(
        client,
        task_queue=billing_reconciliation_task_queue(settings),
        workflows=[BillingReconciliationWorkflow],
        activities=[reconcile],
        identity="graf-maintenance:billing-reconciliation",
    )


async def _run_billing_reconciliation_worker(worker) -> None:
    await worker.run()
    raise RuntimeError("billing reconciliation poller stopped")


async def _run_temporal_maintenance(settings) -> None:
    """Temporal outages must not stop independent calendar maintenance."""
    while True:
        client = None
        tasks = []
        try:
            client = await connect_temporal_client(settings, identity="graf-maintenance")
            await verify_billing_maintenance_database(settings)
            billing_worker = _create_billing_reconciliation_worker(settings, client)
            tasks = [asyncio.create_task(_run_billing_reconciliation_worker(billing_worker))]
            tasks.extend(
                asyncio.create_task(reconcile(settings, client))
                for reconcile in (
                    run_account_closure_reconciler,
                    run_billing_renewal_reconciler,
                    run_billing_reconciliation_reconciler,
                    run_deletion_purge_reconciler,
                    run_processing_start_reconciler,
                    run_summary_sharing_reconciler,
                )
            )
            if settings.outcome_generation_enabled:
                tasks.append(asyncio.create_task(run_dispatch_reconciler(settings, client)))
            await asyncio.gather(*tasks)
        except BillingMaintenanceDatabaseError:
            raise
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


async def run_summary_sharing_reconciler(settings, temporal_client) -> None:
    """Bounded readiness scan and durable delivery recovery on the existing poller."""
    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    context = MaintenanceTenantContext(
        operation_name="summary_delivery_reconciliation", actor_id="graf-maintenance",
        reason_category="summary_readiness_recovery", feature_area="sharing",
    )
    try:
        while True:
            try:
                async with sessionmaker() as db:
                    await apply_tenant_context(db, context)
                    targets = await list_autosend_readiness_candidates(db, limit=25)
                    await db.commit()
                for workspace_id, meeting_id in targets:
                    async with sessionmaker() as db:
                        await apply_tenant_context(db, context)
                        await reconcile_meeting_autosend(
                            db, settings=settings, workspace_id=workspace_id,
                            meeting_id=meeting_id,
                        )
                        await db.commit()
                await reconcile_summary_delivery_once(
                    sessionmaker, settings=settings, temporal_client=temporal_client, limit=50,
                )
            except Exception as error:
                logger.error("summary sharing recovery failed; error_type=%s", type(error).__name__)
            await asyncio.sleep(5)
    finally:
        await engine.dispose()


def main() -> None:
    asyncio.run(run_maintenance_worker())


if __name__ == "__main__":
    main()
