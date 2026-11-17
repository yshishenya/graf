from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext
from twobrain_rec_server.workflows import maintenance_worker


class _Scalars:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _FakeDb:
    def __init__(self, workspace_ids):
        self.workspace_ids = workspace_ids
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def scalars(self, _query):
        return _Scalars(self.workspace_ids)

    async def commit(self):
        self.commits += 1


class _FakeSessions:
    def __init__(self, workspace_ids):
        self.workspace_ids = workspace_ids
        self.instances: list[_FakeDb] = []

    def __call__(self):
        db = _FakeDb(self.workspace_ids)
        self.instances.append(db)
        return db


@pytest.mark.asyncio
async def test_retention_once_runs_each_workspace_and_isolates_failure(monkeypatch):
    first, second = uuid4(), uuid4()
    sessions = _FakeSessions([first, second])
    context = MaintenanceTenantContext(
        operation_name="retention_scan",
        actor_id="graf-maintenance",
        reason_category="retention_policy",
        feature_area="deletion",
    )
    calls = []

    async def apply_context(_db, _context):
        return None

    async def fake_scan(_db, *, settings, workspace_id, limit, storage):
        calls.append((workspace_id, limit, storage))
        if workspace_id == second:
            raise RuntimeError("workspace failed")
        return SimpleNamespace(evaluated=1, created_requests=0, skipped=1, blocked=0)

    monkeypatch.setattr(maintenance_worker, "apply_tenant_context", apply_context)
    monkeypatch.setattr(maintenance_worker, "run_retention_scan", fake_scan)

    await maintenance_worker.run_retention_once(
        settings=SimpleNamespace(retention_scheduler_enabled=True),
        sessions=sessions,
        context=context,
        storage=object(),
    )

    assert calls == [(first, 100, calls[0][2]), (second, 100, calls[1][2])]
    # The first workspace committed; the failing one did not abort the loop.
    assert len(sessions.instances) == 3
    assert sessions.instances[1].commits == 1
    assert sessions.instances[2].commits == 0


@pytest.mark.asyncio
async def test_retention_reconciler_disabled_returns_without_starting_dependencies(monkeypatch):
    def unexpected(*_args, **_kwargs):
        raise AssertionError("disabled scheduler must not create an engine")

    monkeypatch.setattr(maintenance_worker, "create_engine", unexpected)

    await maintenance_worker.run_retention_reconciler(
        SimpleNamespace(retention_scheduler_enabled=False)
    )


@pytest.mark.asyncio
async def test_retention_once_uses_isolated_session_per_workspace(monkeypatch):
    workspace_id = uuid4()
    sessions = _FakeSessions([workspace_id])
    context = MaintenanceTenantContext(
        operation_name="retention_scan",
        actor_id="graf-maintenance",
        reason_category="retention_policy",
        feature_area="deletion",
    )

    async def apply_context(_db, _context):
        return None

    async def fake_scan(_db, *, settings, workspace_id, limit, storage):
        return SimpleNamespace(evaluated=0, created_requests=0, skipped=0, blocked=0)

    monkeypatch.setattr(maintenance_worker, "apply_tenant_context", apply_context)
    monkeypatch.setattr(maintenance_worker, "run_retention_scan", fake_scan)

    await maintenance_worker.run_retention_once(
        settings=SimpleNamespace(retention_scheduler_enabled=True),
        sessions=sessions,
        context=context,
        storage=object(),
    )

    assert len(sessions.instances) == 2
    assert sessions.instances[0] is not sessions.instances[1]
    assert sessions.instances[1].commits == 1
