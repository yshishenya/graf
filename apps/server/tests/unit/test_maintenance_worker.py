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
    monkeypatch.setattr(worker, "TEMPORAL_RETRY_SECONDS", 0, raising=False)
    monkeypatch.setattr(worker, "run_calendar_sync_reconciler", calendar)
    monkeypatch.setattr(worker, "run_billing_notification_reconciler", independent)
    for name in (
        "run_system_operation_reconciler",
        "run_account_closure_reconciler",
        "run_billing_renewal_reconciler",
        "run_billing_reconciliation_reconciler",
        "run_deletion_purge_reconciler",
        "run_processing_start_reconciler",
        "run_dispatch_reconciler",
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
