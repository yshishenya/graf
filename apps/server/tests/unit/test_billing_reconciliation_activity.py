from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import UUID

import pytest

from twobrain_rec_server.billing.database import (
    BillingMaintenanceDatabaseError,
    require_billing_maintenance_database,
)
from twobrain_rec_server.workflows import worker


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

    monkeypatch.setattr(worker, "get_settings", lambda: SimpleNamespace())
    monkeypatch.setattr(worker, "create_engine", lambda _settings: Engine())
    monkeypatch.setattr(worker, "create_sessionmaker", lambda _engine: lambda: SessionContext())
    monkeypatch.setattr(worker, "apply_tenant_context", apply_tenant_context)
    monkeypatch.setattr(worker, "require_billing_maintenance_database", verify_identity)
    monkeypatch.setattr(worker, "reconcile_billing_maintenance", maintenance)
    monkeypatch.setattr(worker, "reconcile_pending_webhook_events", webhooks)
    monkeypatch.setattr(worker, "reconcile_pending_initial_checkout_operations", initial)

    result = asyncio.run(
        worker.run_billing_reconciliation_activity(
            {"run_id": str(UUID("10000000-0000-4000-8000-000000000001"))}
        )
    )

    assert events == [
        "context", "database_identity", "maintenance", "commit",
        "webhooks", "initial", "commit", "dispose",
    ]
    assert result == {
        "run_id": "10000000-0000-4000-8000-000000000001",
        "maintenance": 1,
        "webhook_reconciled": 1,
        "initial_checkout_processed": 1,
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
