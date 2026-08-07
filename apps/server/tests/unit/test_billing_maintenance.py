import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

from twobrain_rec_server.billing.maintenance import reconcile_billing_maintenance


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def __iter__(self):
        return iter(self._values)


class _FakeDb:
    def __init__(self):
        self.calls = []

    async def scalars(self, query):
        self.calls.append(query)
        # Maintenance queries are intentionally tested at the contract seam;
        # the SQL expression itself is owned by the integration/RLS suite.
        return _ScalarResult([])

    async def scalar(self, query):
        self.calls.append(query)
        return 0

    async def flush(self):
        return None


def test_billing_maintenance_returns_only_safe_counters(monkeypatch) -> None:
    async def no_promos(_db, *, now):
        return 2

    async def no_credits(_db, *, now):
        return 3

    async def no_reservations(_db, *, workspace_id, now):
        return 4

    monkeypatch.setattr("twobrain_rec_server.billing.maintenance.expire_promo_reservations", no_promos)
    monkeypatch.setattr("twobrain_rec_server.billing.maintenance.mature_pending_credits", no_credits)
    monkeypatch.setattr("twobrain_rec_server.billing.maintenance.release_expired_storage_reservations", no_reservations)
    result = asyncio.run(
        reconcile_billing_maintenance(
            _FakeDb(), now=datetime(2026, 8, 7, tzinfo=UTC)
        )
    )
    assert result == {
        "expired_promos": 2,
        "matured_credits": 3,
        "released_storage_reservations": 0,
        "stuck_operations": 0,
        "storage_projections_checked": 0,
        "storage_addons_checked": 0,
        "pending_notifications": 0,
    }


def test_billing_maintenance_classifies_stuck_operation_and_projects_addon(monkeypatch) -> None:
    workspace_id = UUID("11111111-1111-4111-8111-111111111111")
    operation = SimpleNamespace(
        state="provider_pending",
        updated_at=None,
        workspace_id=workspace_id,
        kind="initial_checkout",
    )

    class RowsDb(_FakeDb):
        def __init__(self):
            super().__init__()
            self.rows = [[operation], [workspace_id], []]
            self.scalar_rows = [SimpleNamespace(capacity_bytes=20_000_000_000), 5]
            self.added = []

        async def scalars(self, query):
            self.calls.append(query)
            return _ScalarResult(self.rows.pop(0))

        async def scalar(self, query):
            self.calls.append(query)
            return self.scalar_rows.pop(0)

        def add(self, value):
            self.added.append(value)

    async def no_promos(_db, *, now):
        return 0

    async def no_credits(_db, *, now):
        return 0

    async def release(_db, *, workspace_id, now):
        return 2

    async def project(_db, *, workspace_id, capacity_bytes):
        return SimpleNamespace(used_bytes=0, capacity_bytes=capacity_bytes)

    monkeypatch.setattr("twobrain_rec_server.billing.maintenance.expire_promo_reservations", no_promos)
    monkeypatch.setattr("twobrain_rec_server.billing.maintenance.mature_pending_credits", no_credits)
    monkeypatch.setattr("twobrain_rec_server.billing.maintenance.release_expired_storage_reservations", release)
    monkeypatch.setattr("twobrain_rec_server.billing.maintenance.project_active_playback_storage", project)
    db = RowsDb()
    result = asyncio.run(reconcile_billing_maintenance(db, now=datetime(2026, 8, 7, tzinfo=UTC)))
    assert operation.state == "unknown"
    assert result["stuck_operations"] == 1
    assert result["released_storage_reservations"] == 2
    assert result["storage_projections_checked"] == 1
    assert result["storage_addons_checked"] == 1
    assert result["pending_notifications"] == 5
    assert len(db.added) == 1
