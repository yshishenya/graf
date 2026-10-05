import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from twobrain_rec_server.workflows import maintenance_worker as worker


@pytest.mark.asyncio
@pytest.mark.parametrize("connect_succeeds", [False, True])
async def test_calendar_runs_during_temporal_outage_and_all_tasks_stop(
    monkeypatch, connect_succeeds
):
    calendar_started = asyncio.Event()
    calendar_stopped = asyncio.Event()
    connection_waiting = asyncio.Event()
    connection_cancelled = asyncio.Event()
    allow_connection = asyncio.Event()
    dependent_started = asyncio.Event()
    dependent_stopped = asyncio.Event()
    client = SimpleNamespace(close=AsyncMock())
    attempts = 0

    async def connect(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ConnectionError("synthetic unavailable")
        connection_waiting.set()
        try:
            await allow_connection.wait()
        except asyncio.CancelledError:
            connection_cancelled.set()
            raise
        return client

    async def calendar(settings):
        calendar_started.set()
        try:
            await asyncio.Event().wait()
        finally:
            calendar_stopped.set()

    async def dependent(*args):
        dependent_started.set()
        try:
            await asyncio.Event().wait()
        finally:
            dependent_stopped.set()

    async def independent(*args):
        await asyncio.Event().wait()

    monkeypatch.setattr(
        worker, "get_settings", lambda: SimpleNamespace(outcome_generation_enabled=True)
    )
    monkeypatch.setattr(worker, "connect_temporal_client", connect)
    monkeypatch.setattr(worker, "verify_billing_maintenance_database", AsyncMock())
    monkeypatch.setattr(
        worker, "_create_billing_reconciliation_worker",
        lambda *_args: SimpleNamespace(run=dependent),
    )
    monkeypatch.setattr(worker, "TEMPORAL_RETRY_SECONDS", 0, raising=False)
    monkeypatch.setattr(worker, "run_calendar_sync_reconciler", calendar)
    monkeypatch.setattr(worker, "run_billing_notification_reconciler", independent)
    for name in (
        "run_account_closure_reconciler",
        "run_billing_renewal_reconciler",
        "run_billing_reconciliation_reconciler",
        "run_deletion_purge_reconciler",
        "run_processing_start_reconciler",
        "run_dispatch_reconciler",
        "run_summary_sharing_reconciler",
    ):
        monkeypatch.setattr(worker, name, dependent)
    task = asyncio.create_task(worker.run_maintenance_worker())
    try:
        await asyncio.wait_for(calendar_started.wait(), timeout=0.3)
        await asyncio.wait_for(connection_waiting.wait(), timeout=0.3)
        assert not dependent_started.is_set()
        assert not task.done()
        if connect_succeeds:
            allow_connection.set()
            await asyncio.wait_for(dependent_started.wait(), timeout=0.3)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    assert calendar_stopped.is_set()
    if connect_succeeds:
        assert dependent_stopped.is_set()
        client.close.assert_awaited_once()
    else:
        assert connection_cancelled.is_set()
        client.close.assert_not_called()


@pytest.mark.parametrize("compose_name", ["docker-compose.yml", "docker-compose.dev.yml"])
def test_maintenance_container_does_not_wait_for_temporal_health(compose_name):
    from pathlib import Path

    import yaml

    class ComposeLoader(yaml.SafeLoader):
        pass

    ComposeLoader.add_constructor("!override", ComposeLoader.construct_sequence)
    path = Path(__file__).resolve().parents[4] / "infra" / compose_name
    services = yaml.load(path.read_text(), Loader=ComposeLoader)["services"]
    dependencies = services["rec-maintenance"]["depends_on"]
    assert "rec-temporal" not in dependencies
    assert dependencies["rec-postgres"]["condition"] == "service_healthy"
    assert dependencies["rec-minio"]["condition"] == "service_healthy"
    assert any(
        dependencies[name]["condition"] == "service_completed_successfully"
        for name in ("rec-migrate", "rec-db-runtime-bootstrap")
        if name in dependencies
    )


@pytest.mark.asyncio
async def test_billing_poller_keeps_existing_registration_across_reconnect(monkeypatch):
    from temporalio import activity

    from twobrain_rec_server.config import Settings
    from twobrain_rec_server.workflows.billing_reconciliation_workflow import (
        BILLING_RECONCILIATION_ACTIVITY_NAME,
        BillingReconciliationWorkflow,
        billing_reconciliation_task_queue,
    )

    registrations = []

    def registered_worker(client, **kwargs):
        registrations.append({"client": client, **kwargs})
        return SimpleNamespace(run=AsyncMock())

    monkeypatch.setattr("temporalio.worker.Worker", registered_worker)
    execute = AsyncMock(return_value={"webhook_processed": 1})
    monkeypatch.setattr(worker, "run_billing_reconciliation_activity", execute)
    settings = Settings(temporal_task_queue="graf-processing")
    clients = [object(), object()]
    for client in clients:
        worker._create_billing_reconciliation_worker(settings, client)
    assert len(registrations) == 2
    first_activity, second_activity = [r["activities"][0] for r in registrations]
    assert first_activity is not second_activity
    for index, registration in enumerate(registrations):
        assert registration["client"] is clients[index]
        assert registration["task_queue"] == billing_reconciliation_task_queue(settings)
        assert registration["workflows"] == [BillingReconciliationWorkflow]
        assert registration["identity"] == "graf-maintenance:billing-reconciliation"
        definition = activity._Definition.must_from_callable(registration["activities"][0])
        assert definition.name == BILLING_RECONCILIATION_ACTIVITY_NAME
        assert await registration["activities"][0]({"run_id": "probe"}) == {
            "webhook_processed": 1,
        }
    assert execute.await_count == 2


@pytest.mark.asyncio
async def test_wrong_database_role_stops_before_any_poller_or_reconciler(monkeypatch):
    from twobrain_rec_server.billing.database import BillingMaintenanceDatabaseError

    settings = SimpleNamespace(outcome_generation_enabled=False)
    monkeypatch.setattr(worker, "get_settings", lambda: settings)
    verify = AsyncMock(side_effect=BillingMaintenanceDatabaseError("maintenance database role"))
    connect = AsyncMock()
    calendar = AsyncMock()
    notification = AsyncMock()
    monkeypatch.setattr(worker, "verify_billing_maintenance_database", verify)
    monkeypatch.setattr(worker, "connect_temporal_client", connect)
    monkeypatch.setattr(worker, "run_calendar_sync_reconciler", calendar)
    monkeypatch.setattr(worker, "run_billing_notification_reconciler", notification)
    with pytest.raises(BillingMaintenanceDatabaseError):
        await worker.run_maintenance_worker()
    verify.assert_awaited_once_with(settings)
    connect.assert_not_awaited()
    calendar.assert_not_awaited()
    notification.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("poller_returns", [False, True])
async def test_billing_poller_reconnect_waits_for_old_tasks_and_closes_clients(
    monkeypatch, poller_returns,
):
    settings = SimpleNamespace(outcome_generation_enabled=False)
    active_pollers = 0
    max_pollers = 0
    active_loops = 0
    first_loops_started = asyncio.Event()
    second_poller_started = asyncio.Event()
    shutdown = []
    clients = []
    workers_created = 0

    async def connect(*_args, **_kwargs):
        async def close():
            assert active_pollers == 0
            assert active_loops == 0
            shutdown.append(len(clients))

        client = SimpleNamespace(close=AsyncMock(side_effect=close))
        clients.append(client)
        return client

    async def independent(*_args):
        await asyncio.Event().wait()

    async def dependent(*_args):
        nonlocal active_loops
        active_loops += 1
        if active_loops == 6:
            first_loops_started.set()
        try:
            await asyncio.Event().wait()
        finally:
            active_loops -= 1

    def poller_factory(*_args):
        nonlocal workers_created
        workers_created += 1
        generation = workers_created

        async def run():
            nonlocal active_pollers, max_pollers
            active_pollers += 1
            max_pollers = max(max_pollers, active_pollers)
            try:
                if generation == 1:
                    await first_loops_started.wait()
                    if poller_returns:
                        return
                    raise ConnectionError("synthetic poller disconnect")
                second_poller_started.set()
                await asyncio.Event().wait()
            finally:
                active_pollers -= 1

        return SimpleNamespace(run=run)

    monkeypatch.setattr(worker, "get_settings", lambda: settings)
    verify = AsyncMock()
    monkeypatch.setattr(worker, "verify_billing_maintenance_database", verify)
    monkeypatch.setattr(worker, "connect_temporal_client", connect)
    monkeypatch.setattr(worker, "_create_billing_reconciliation_worker", poller_factory)
    monkeypatch.setattr(worker, "TEMPORAL_RETRY_SECONDS", 0)
    monkeypatch.setattr(worker, "run_calendar_sync_reconciler", independent)
    monkeypatch.setattr(worker, "run_billing_notification_reconciler", independent)
    for name in (
        "run_account_closure_reconciler", "run_billing_renewal_reconciler",
        "run_billing_reconciliation_reconciler", "run_deletion_purge_reconciler",
        "run_processing_start_reconciler",
        "run_summary_sharing_reconciler",
    ):
        monkeypatch.setattr(worker, name, dependent)
    task = asyncio.create_task(worker.run_maintenance_worker())
    try:
        await asyncio.wait_for(second_poller_started.wait(), timeout=2)
        assert max_pollers == 1
        assert shutdown == [1]
        assert verify.await_count == 3  # Startup and each connection, before its poller.
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    assert active_pollers == active_loops == 0
    assert workers_created == 2
    assert shutdown == [1, 2]
    for client in clients:
        client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_reconnect_role_mismatch_closes_client_before_poller(monkeypatch):
    from twobrain_rec_server.billing.database import BillingMaintenanceDatabaseError

    client = SimpleNamespace(close=AsyncMock())
    settings = SimpleNamespace(outcome_generation_enabled=False)
    verify = AsyncMock(side_effect=BillingMaintenanceDatabaseError("maintenance database role"))
    create_poller = AsyncMock()
    monkeypatch.setattr(worker, "verify_billing_maintenance_database", verify)
    monkeypatch.setattr(worker, "connect_temporal_client", AsyncMock(return_value=client))
    monkeypatch.setattr(worker, "_create_billing_reconciliation_worker", create_poller)
    with pytest.raises(BillingMaintenanceDatabaseError):
        await worker._run_temporal_maintenance(settings)
    create_poller.assert_not_called()
    client.close.assert_awaited_once()
