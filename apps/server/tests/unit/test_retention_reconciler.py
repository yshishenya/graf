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

    async def fake_scan(_db, *, settings, workspace_id, limit, storage, dry_run):
        assert dry_run is True
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

    async def fake_scan(_db, *, settings, workspace_id, limit, storage, dry_run):
        assert dry_run is True
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


def test_retention_scheduler_is_opt_in_by_default() -> None:
    from twobrain_rec_server.config import Settings

    settings = Settings()
    assert settings.retention_scheduler_enabled is False
    assert settings.retention_scheduler_dry_run_only is True


@pytest.mark.asyncio
async def test_retention_once_uses_destructive_mode_only_after_second_key(monkeypatch):
    workspace_id = uuid4()
    sessions = _FakeSessions([workspace_id])
    context = MaintenanceTenantContext(
        operation_name="retention_scan",
        actor_id="graf-maintenance",
        reason_category="retention_policy",
        feature_area="deletion",
    )
    observed: list[bool] = []

    async def apply_context(_db, _context):
        return None

    async def fake_scan(_db, *, settings, workspace_id, limit, storage, dry_run):
        observed.append(dry_run)
        return SimpleNamespace(evaluated=1, created_requests=0, skipped=0, blocked=0)

    monkeypatch.setattr(maintenance_worker, "apply_tenant_context", apply_context)
    monkeypatch.setattr(maintenance_worker, "run_retention_scan", fake_scan)

    await maintenance_worker.run_retention_once(
        settings=SimpleNamespace(
            retention_scheduler_enabled=True,
            retention_scheduler_dry_run_only=False,
        ),
        sessions=sessions,
        context=context,
        storage=object(),
    )

    assert observed == [False]


@pytest.mark.asyncio
async def test_retention_once_drains_saturated_batches_until_backlog_is_empty(monkeypatch):
    workspace_id = uuid4()
    sessions = _FakeSessions([workspace_id])
    context = MaintenanceTenantContext(
        operation_name="retention_scan",
        actor_id="graf-maintenance",
        reason_category="retention_policy",
        feature_area="deletion",
    )
    batches = [
        SimpleNamespace(evaluated=100, created_requests=100, skipped=0, blocked=0),
        SimpleNamespace(evaluated=100, created_requests=100, skipped=0, blocked=0),
        SimpleNamespace(evaluated=37, created_requests=37, skipped=0, blocked=0),
    ]
    calls: list[int] = []

    async def apply_context(_db, _context):
        return None

    async def fake_scan(_db, *, settings, workspace_id, limit, storage, dry_run):
        assert dry_run is False
        assert limit == maintenance_worker.RETENTION_SCAN_BATCH_LIMIT
        calls.append(limit)
        return batches[len(calls) - 1]

    monkeypatch.setattr(maintenance_worker, "apply_tenant_context", apply_context)
    monkeypatch.setattr(maintenance_worker, "run_retention_scan", fake_scan)

    await maintenance_worker.run_retention_once(
        settings=SimpleNamespace(
            retention_scheduler_enabled=True,
            retention_scheduler_dry_run_only=False,
        ),
        sessions=sessions,
        context=context,
        storage=object(),
    )

    # The daily pass must clear every expired meeting, not only the first 100.
    assert len(calls) == 3
    assert sessions.instances[1].commits == 3


@pytest.mark.asyncio
async def test_retention_once_keeps_a_dry_run_to_a_single_batch(monkeypatch):
    workspace_id = uuid4()
    sessions = _FakeSessions([workspace_id])
    context = MaintenanceTenantContext(
        operation_name="retention_scan",
        actor_id="graf-maintenance",
        reason_category="retention_policy",
        feature_area="deletion",
    )
    calls: list[int] = []

    async def apply_context(_db, _context):
        return None

    async def fake_scan(_db, *, settings, workspace_id, limit, storage, dry_run):
        assert dry_run is True
        calls.append(limit)
        return SimpleNamespace(evaluated=100, created_requests=100, skipped=0, blocked=0)

    monkeypatch.setattr(maintenance_worker, "apply_tenant_context", apply_context)
    monkeypatch.setattr(maintenance_worker, "run_retention_scan", fake_scan)

    await maintenance_worker.run_retention_once(
        settings=SimpleNamespace(
            retention_scheduler_enabled=True,
            retention_scheduler_dry_run_only=True,
        ),
        sessions=sessions,
        context=context,
        storage=object(),
    )

    # A dry run deletes nothing, so rescanning would only repeat the same rows.
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_retention_once_stops_at_the_batch_cap_and_logs_backlog(monkeypatch):
    workspace_id = uuid4()
    sessions = _FakeSessions([workspace_id])
    context = MaintenanceTenantContext(
        operation_name="retention_scan",
        actor_id="graf-maintenance",
        reason_category="retention_policy",
        feature_area="deletion",
    )
    warnings: list[str] = []

    async def apply_context(_db, _context):
        return None

    async def fake_scan(_db, *, settings, workspace_id, limit, storage, dry_run):
        return SimpleNamespace(evaluated=100, created_requests=100, skipped=0, blocked=0)

    monkeypatch.setattr(maintenance_worker, "apply_tenant_context", apply_context)
    monkeypatch.setattr(maintenance_worker, "run_retention_scan", fake_scan)
    monkeypatch.setattr(
        maintenance_worker.logger,
        "warning",
        lambda message, *args: warnings.append(message % args if args else message),
    )

    await maintenance_worker.run_retention_once(
        settings=SimpleNamespace(
            retention_scheduler_enabled=True,
            retention_scheduler_dry_run_only=False,
        ),
        sessions=sessions,
        context=context,
        storage=object(),
    )

    assert sessions.instances[1].commits == maintenance_worker.RETENTION_SCAN_MAX_BATCHES
    assert any("batch cap reached" in message for message in warnings)


@pytest.mark.asyncio
async def test_disabled_retention_reconciler_never_opens_storage() -> None:
    # The disabled path must return before create_engine/get_storage; a missing
    # engine here would fail the test with an unrelated error.
    await maintenance_worker.run_retention_reconciler(
        SimpleNamespace(retention_scheduler_enabled=False)
    )


def test_bootstrap_accepts_both_0113_and_0114_maintenance_helper_bodies() -> None:
    """A stand at 0113 must still pass the bootstrap safety check after 0114."""

    from importlib import import_module

    from scripts import bootstrap_runtime_database_roles as bootstrap

    previous = import_module(
        "twobrain_rec_server.db.migrations.versions.0113_fair_use_operator_history"
    )
    current = import_module(
        "twobrain_rec_server.db.migrations.versions.0116_retention_scan_maintenance"
    )
    legacy_body = previous.CONTEXT_HELPERS["rec_maintenance_allowed()"][1]

    assert current.maintenance_allowed_body(current.PREVIOUS_OPERATIONS) == legacy_body
    assert "retention_scan" in current.maintenance_allowed_body()
    assert "retention_scan" not in legacy_body
    # The package is importable and exposes the function the bootstrap uses.
    assert callable(bootstrap._restrict_fair_use_history)
