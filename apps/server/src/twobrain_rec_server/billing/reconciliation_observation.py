"""Bounded metadata observations, independent of financial transactions."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import create_async_engine

from twobrain_rec_server.billing.database import require_billing_maintenance_database
from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.models.billing import BillingReconciliationObservation
from twobrain_rec_server.db.session import create_sessionmaker
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    maintenance_context_settings,
)
from twobrain_rec_server.workflows.billing_reconciliation_workflow import (
    BILLING_RECONCILIATION_ACTIVITY_NAME,
    BILLING_RECONCILIATION_WORKFLOW_ID_PATTERN,
)

logger = logging.getLogger(__name__)
OBSERVATION_TIMEOUT_SECONDS = 2
EVENT_KINDS = frozenset({"started", "succeeded", "failed", "canceled"})


@dataclass(frozen=True)
class ReconciliationAttempt:
    namespace: str
    workflow_id: str
    workflow_run_id: UUID
    activity_id: str
    attempt: int

    def __post_init__(self):
        for value, limit in ((self.namespace, 255), (self.workflow_id, 128), (self.activity_id, 255)):
            if not isinstance(value, str) or "\x00" in value or not 1 <= len(value.encode("utf-8")) <= limit:
                raise ValueError("invalid reconciliation identity")
        if (not BILLING_RECONCILIATION_WORKFLOW_ID_PATTERN.fullmatch(self.workflow_id)
                or not isinstance(self.workflow_run_id, UUID)
                or type(self.attempt) is not int or not 1 <= self.attempt <= 2147483647):
            raise ValueError("invalid reconciliation identity")


def current_reconciliation_attempt() -> ReconciliationAttempt | None:
    from temporalio import activity

    try:
        info = activity.info()
        if (info.workflow_type != "BillingReconciliationWorkflow"
                or info.activity_type != BILLING_RECONCILIATION_ACTIVITY_NAME):
            return None
        return ReconciliationAttempt(info.namespace, info.workflow_id, UUID(info.workflow_run_id),
                                     info.activity_id, info.attempt)
    except (RuntimeError, ValueError, TypeError, AttributeError):
        return None


async def record_reconciliation_observation(attempt: ReconciliationAttempt | None, event_kind: str) -> bool:
    try:
        if attempt is None or event_kind not in EVENT_KINDS:
            raise ValueError("unavailable reconciliation observation")
        await _persist_observation(attempt, event_kind)
        return True
    except Exception:
        # Never expose identity, payload, SQL, connection URL or failure text.
        logger.warning("billing_observation_unavailable")
        return False


async def _persist_observation(attempt: ReconciliationAttempt, event_kind: str) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + OBSERVATION_TIMEOUT_SECONDS
    terminate_at_deadline = None
    try:
        async with asyncio.timeout_at(deadline):
            settings = get_settings()
            engine = create_async_engine(settings.database_url, hide_parameters=True, connect_args={
                "timeout": OBSERVATION_TIMEOUT_SECONDS,
                "server_settings": {"statement_timeout": "1000", "lock_timeout": "500"},
            })
            db = None
            connection = None
            driver = None

            @event.listens_for(engine.sync_engine, "do_connect")
            def capture_driver(dialect, _record, args, params):
                nonlocal driver, terminate_at_deadline
                # Capture before dialect initialization and Session.after_begin
                # can issue SQL. Their cancellation may otherwise wait for the
                # adapter's shielded graceful close before returning here.
                adapted = dialect.loaded_dbapi.connect(*args, **params)
                driver = adapted.driver_connection
                terminate_at_deadline = loop.call_at(deadline, driver.terminate)
                return adapted

            try:
                db = create_sessionmaker(engine)()
                db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                    operation_name="billing_reconciliation", actor_id="billing-observation",
                    reason_category="billing_maintenance_observation", feature_area="billing",
                ))
                connection = await db.connection()
                await require_billing_maintenance_database(db)
                await db.execute(insert(BillingReconciliationObservation).values(
                    **asdict(attempt), event_kind=event_kind,
                ).on_conflict_do_nothing())
                await db.commit()
            except BaseException as error:
                if driver is not None and (isinstance(error, asyncio.CancelledError) or loop.time() >= deadline):
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
                    async with asyncio.timeout_at(deadline):
                        await engine.dispose()
    finally:
        if terminate_at_deadline is not None:
            terminate_at_deadline.cancel()
