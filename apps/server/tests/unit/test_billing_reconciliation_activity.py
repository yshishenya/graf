from __future__ import annotations

import asyncio
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from twobrain_rec_server.billing.database import (
    BillingMaintenanceDatabaseError,
    require_billing_maintenance_database,
)
from twobrain_rec_server.workflows import worker


def observation_environment(**overrides):
    from temporalio.testing import ActivityEnvironment

    env = ActivityEnvironment()
    env.info = replace(env.info, namespace="synthetic", workflow_type="BillingReconciliationWorkflow",
                       workflow_id="billing-reconciliation/10000000-0000-4000-8000-000000000001/v1",
                       workflow_run_id="20000000-0000-4000-8000-000000000001",
                       activity_id="1", activity_type="run_billing_reconciliation_activity")
    env.info = replace(env.info, **overrides)
    return env


def test_observation_uses_actual_execution_identity_and_not_payload():
    from twobrain_rec_server.billing.reconciliation_observation import (
        current_reconciliation_attempt,
    )

    assert current_reconciliation_attempt() is None
    first = observation_environment(attempt=7).run(current_reconciliation_attempt)
    second = observation_environment(attempt=7, workflow_run_id="30000000-0000-4000-8000-000000000001").run(current_reconciliation_attempt)
    assert first.namespace == "synthetic" and first.activity_id == "1" and first.attempt == 7
    assert str(first.workflow_run_id) == "20000000-0000-4000-8000-000000000001"
    assert first != second


@pytest.mark.parametrize("field,value", [
    ("namespace", ""), ("namespace", "я" * 128), ("namespace", "bad\x00value"),
    ("workflow_id", "private-payload"), ("workflow_run_id", "bucket-not-run"),
    ("workflow_type", "OtherWorkflow"), ("activity_type", "OtherActivity"),
    ("activity_id", ""), ("activity_id", "я" * 128),
    ("attempt", 0), ("attempt", -1), ("attempt", 2147483648), ("attempt", True),
])
def test_observation_rejects_invalid_actual_identity_without_fabrication(field, value):
    from twobrain_rec_server.billing.reconciliation_observation import (
        current_reconciliation_attempt,
    )

    assert observation_environment(**{field: value}).run(current_reconciliation_attempt) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["success", "failure", "cancel", "invalid_payload"])
async def test_observation_preserves_activity_outcome_and_never_repeats_financial_work(monkeypatch, outcome):
    from twobrain_rec_server.billing import reconciliation_observation as observation

    events = []
    error = RuntimeError("synthetic-private-original-error")

    async def financial(payload):
        events.append("financial")
        if outcome == "failure":
            raise error
        if outcome == "cancel":
            raise asyncio.CancelledError
        return {"run_id": payload["run_id"], "processed": 4}

    async def persist(attempt, event_kind):
        events.append(event_kind)
        assert attempt.attempt == 2
        raise RuntimeError("synthetic-private-SQL-URL-email")

    monkeypatch.setattr(observation, "_persist_observation", persist)
    if outcome != "invalid_payload":
        monkeypatch.setattr(worker, "_run_billing_reconciliation_activity", financial)
    env = observation_environment(attempt=2)
    payload = {"run_id": "10000000-0000-4000-8000-000000000001"}
    if outcome == "failure":
        with pytest.raises(RuntimeError) as exc:
            await env.run(worker.run_billing_reconciliation_activity, payload)
        assert exc.value is error
    elif outcome == "cancel":
        with pytest.raises(asyncio.CancelledError):
            await env.run(worker.run_billing_reconciliation_activity, payload)
    elif outcome == "invalid_payload":
        from temporalio.exceptions import ApplicationError
        with pytest.raises(ApplicationError) as exc:
            await env.run(worker.run_billing_reconciliation_activity, {"private": "invalid"})
        assert exc.value.non_retryable
    else:
        assert await env.run(worker.run_billing_reconciliation_activity, payload) == {"run_id": payload["run_id"], "processed": 4}
    terminal = {"success": "succeeded", "failure": "failed", "cancel": "canceled", "invalid_payload": "failed"}[outcome]
    assert events == ["started", *([] if outcome == "invalid_payload" else ["financial"]), terminal]


@pytest.mark.asyncio
async def test_observation_failure_has_only_fixed_log_code_and_external_cancel_survives(monkeypatch, caplog):
    from twobrain_rec_server.billing import reconciliation_observation as observation

    # Alembic disables existing loggers when another test prepares its database.
    monkeypatch.setattr(observation.logger, "disabled", False)
    caplog.set_level("WARNING", logger=observation.logger.name)
    attempt = observation_environment().run(observation.current_reconciliation_attempt)
    monkeypatch.setattr(observation, "_persist_observation", AsyncMock(side_effect=RuntimeError("private-SQL-URL-contact")))
    assert await observation.record_reconciliation_observation(attempt, "started") is False
    assert caplog.records and all(r.getMessage() == "billing_observation_unavailable" and not r.exc_info for r in caplog.records)
    monkeypatch.setattr(observation, "_persist_observation", AsyncMock(side_effect=asyncio.CancelledError))
    with pytest.raises(asyncio.CancelledError):
        await observation.record_reconciliation_observation(attempt, "started")


@pytest.mark.asyncio
@pytest.mark.parametrize("blocked", ["connect", "guard", "insert", "commit", "close", "dispose"])
async def test_observation_deadline_includes_cleanup_and_leaves_no_background_task(monkeypatch, blocked):
    from twobrain_rec_server.billing import reconciliation_observation as observation

    events = []
    connectors = []

    def listens_for(_engine, name):
        assert name == "do_connect"
        return lambda callback: connectors.append(callback)

    async def step(name):
        events.append(name)
        if name == blocked:
            await asyncio.sleep(10)

    class Driver:
        def terminate(self):
            events.append("terminate")

    class Connection:
        closed = False

        async def get_raw_connection(self):
            return SimpleNamespace(driver_connection=Driver())

        async def invalidate(self):
            events.append("connection_invalidate")

    class Db:
        sync_session = SimpleNamespace(info={})

        async def connection(self):
            await step("connect")
            dialect = SimpleNamespace(loaded_dbapi=SimpleNamespace(
                connect=lambda: SimpleNamespace(driver_connection=Driver()),
            ))
            connectors[0](dialect, None, (), {})
            return Connection()

        async def execute(self, _):
            await step("insert")

        async def commit(self):
            await step("commit")

        async def close(self):
            await step("close")

        async def invalidate(self):
            events.append("session_invalidate")

    class Engine:
        sync_engine = object()

        async def dispose(self):
            await step("dispose")

    async def guard(_db):
        await step("guard")

    monkeypatch.setattr(observation, "get_settings", lambda: SimpleNamespace(database_url="synthetic"))
    monkeypatch.setattr(observation, "event", SimpleNamespace(listens_for=listens_for))
    monkeypatch.setattr(observation, "create_async_engine", lambda *a, **kw: Engine())
    monkeypatch.setattr(observation, "create_sessionmaker", lambda _: Db)
    monkeypatch.setattr(observation, "require_billing_maintenance_database", guard)
    monkeypatch.setattr(observation, "OBSERVATION_TIMEOUT_SECONDS", 0.03)
    before = asyncio.all_tasks()
    began = asyncio.get_running_loop().time()
    attempt = observation_environment().run(observation.current_reconciliation_attempt)
    assert await observation.record_reconciliation_observation(attempt, "started") is False
    assert asyncio.get_running_loop().time() - began < 0.3
    await asyncio.sleep(0)
    assert asyncio.all_tasks() == before
    if blocked in {"guard", "insert", "commit", "close"}:
        assert "terminate" in events
    if "session_invalidate" in events:
        assert events.index("connection_invalidate") < events.index("session_invalidate")


@pytest.mark.asyncio
@pytest.mark.parametrize("failed_stage", ["context", "guard", "maintenance", "commit1", "webhooks", "initial", "commit2", "exit", "dispose"])
async def test_observation_preserves_original_errors_before_between_and_after_financial_commits(monkeypatch, failed_stage):
    from twobrain_rec_server.billing import reconciliation_observation as observation

    events = []
    error = RuntimeError("private-original-financial-error")

    async def step(name):
        events.append(name)
        if name == failed_stage:
            raise error
        return {"count": 1}

    class Db:
        commits = 0

        async def commit(self):
            self.commits += 1
            await step(f"commit{self.commits}")

    class SessionContext:
        async def __aenter__(self):
            return Db()

        async def __aexit__(self, *args):
            await step("exit")

    class Engine:
        async def dispose(self):
            await step("dispose")

    async def persist(attempt, kind):
        events.append(kind)

    monkeypatch.setattr(observation, "_persist_observation", persist)
    monkeypatch.setattr(worker, "get_settings", lambda: SimpleNamespace())
    monkeypatch.setattr(worker, "create_engine", lambda _: Engine())
    monkeypatch.setattr(worker, "create_sessionmaker", lambda _: SessionContext)
    monkeypatch.setattr(worker, "apply_tenant_context", lambda *a: step("context"))
    monkeypatch.setattr(worker, "require_billing_maintenance_database", lambda *a: step("guard"))
    monkeypatch.setattr(worker, "reconcile_billing_maintenance", lambda *a: step("maintenance"))
    monkeypatch.setattr(worker, "reconcile_pending_webhook_events", lambda *a: step("webhooks"))
    monkeypatch.setattr(worker, "reconcile_pending_initial_checkout_operations", lambda *a, **k: step("initial"))
    with pytest.raises(RuntimeError) as exc:
        await observation_environment().run(worker.run_billing_reconciliation_activity, {
            "run_id": "10000000-0000-4000-8000-000000000001"})
    assert exc.value is error
    assert events[0] == "started" and events[-1] == "failed"
    assert "succeeded" not in events
    for name in ("maintenance", "webhooks", "initial", "commit1", "commit2", "dispose"):
        assert events.count(name) <= 1


@pytest.mark.asyncio
async def test_observation_repeated_external_cancel_interrupts_optional_cancel_record(monkeypatch):
    from twobrain_rec_server.billing import reconciliation_observation as observation

    work_started, recording_cancel = asyncio.Event(), asyncio.Event()

    async def financial(_payload):
        work_started.set()
        await asyncio.sleep(10)

    async def persist(attempt, kind):
        if kind == "canceled":
            recording_cancel.set()
            await asyncio.sleep(10)

    monkeypatch.setattr(worker, "_run_billing_reconciliation_activity", financial)
    monkeypatch.setattr(observation, "_persist_observation", persist)
    before = asyncio.all_tasks()
    task = asyncio.create_task(observation_environment().run(worker.run_billing_reconciliation_activity, {}))
    await work_started.wait()
    task.cancel()
    await recording_cancel.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert asyncio.all_tasks() == before


def test_billing_reconciliation_releases_maintenance_locks_before_webhooks(monkeypatch) -> None:
    events: list[str] = []

    class Db:
        async def commit(self) -> None:
            events.append("commit")

    db = Db()

    class SessionContext:
        async def __aenter__(self):
            return db

        async def __aexit__(self, *_args):
            return None

    class Engine:
        async def dispose(self) -> None:
            events.append("dispose")

    async def apply_tenant_context(_db, _context) -> None:
        events.append("context")

    async def verify_identity(_db):
        events.append("database_identity")

    async def maintenance(_db):
        events.append("maintenance")
        return {"maintenance": 1}

    async def webhooks(_db, _settings):
        events.append("webhooks")
        return {"reconciled": 1}

    async def initial(_db, _settings, **kwargs):
        events.append("initial")
        assert kwargs == {"commit_each_operation": True}
        return {"processed": 1}

    async def receipts(_db, _settings):
        events.append("receipts")
        return {"receipt_gets": 1}

    monkeypatch.setattr(worker, "get_settings", lambda: SimpleNamespace())
    monkeypatch.setattr(worker, "create_engine", lambda _settings: Engine())
    monkeypatch.setattr(worker, "create_sessionmaker", lambda _engine: lambda: SessionContext())
    monkeypatch.setattr(worker, "apply_tenant_context", apply_tenant_context)
    monkeypatch.setattr(worker, "require_billing_maintenance_database", verify_identity)
    monkeypatch.setattr(worker, "reconcile_billing_maintenance", maintenance)
    monkeypatch.setattr(worker, "reconcile_pending_webhook_events", webhooks)
    monkeypatch.setattr(worker, "reconcile_pending_initial_checkout_operations", initial)
    monkeypatch.setattr(worker, "reconcile_pending_receipts", receipts)

    result = asyncio.run(
        worker.run_billing_reconciliation_activity(
            {"run_id": str(UUID("10000000-0000-4000-8000-000000000001"))}
        )
    )

    assert events == [
        "context", "database_identity", "maintenance", "commit",
        "webhooks", "initial", "commit", "receipts", "dispose",
    ]
    assert result == {
        "run_id": "10000000-0000-4000-8000-000000000001",
        "maintenance": 1,
        "webhook_reconciled": 1,
        "initial_checkout_processed": 1,
        "receipt_gets": 1,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "position,value",
    [(0, "twobrain_rec_app"), (1, "twobrain_rec_app"), (2, "off"),
     (3, True), (4, True), (5, False), (6, False), (7, False), (5, None)],
)
async def test_reconciliation_identity_rejects_unsafe_role_or_context(position, value):
    row = ["twobrain_rec_maintenance", "twobrain_rec_maintenance", "on",
           False, False, True, True, True]
    row[position] = value

    class Db:
        def get_bind(self):
            return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

        async def execute(self, _statement):
            return SimpleNamespace(one=lambda: tuple(row))

    with pytest.raises(BillingMaintenanceDatabaseError, match="maintenance database role"):
        await require_billing_maintenance_database(Db())


@pytest.mark.asyncio
async def test_reconciliation_identity_accepts_only_protected_maintenance_database():
    class Db:
        def get_bind(self):
            return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

        async def execute(self, _statement):
            return SimpleNamespace(one=lambda: (
                "twobrain_rec_maintenance", "twobrain_rec_maintenance", "on",
                False, False, True, True, True,
            ))

    await require_billing_maintenance_database(Db())


@pytest.mark.asyncio
async def test_reconciliation_identity_rejects_non_postgresql_before_query():
    class Db:
        def get_bind(self):
            return SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))

        async def execute(self, _statement):
            raise AssertionError("a wrong database must fail before queries")

    with pytest.raises(BillingMaintenanceDatabaseError):
        await require_billing_maintenance_database(Db())
