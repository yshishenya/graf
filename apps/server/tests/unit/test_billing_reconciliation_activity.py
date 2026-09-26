from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import UUID

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
    monkeypatch.setattr(worker, "reconcile_billing_maintenance", maintenance)
    monkeypatch.setattr(worker, "reconcile_pending_webhook_events", webhooks)
    monkeypatch.setattr(worker, "reconcile_pending_initial_checkout_operations", initial)

    result = asyncio.run(
        worker.run_billing_reconciliation_activity(
            {"run_id": str(UUID("10000000-0000-4000-8000-000000000001"))}
        )
    )

    assert events == ["context", "maintenance", "commit", "webhooks", "initial", "commit", "dispose"]
    assert result == {
        "run_id": "10000000-0000-4000-8000-000000000001",
        "maintenance": 1,
        "webhook_reconciled": 1,
        "initial_checkout_processed": 1,
    }
