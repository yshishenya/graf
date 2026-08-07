import asyncio
from datetime import UTC, datetime

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
    assert result == {"expired_promos": 2, "matured_credits": 3, "released_storage_reservations": 0}
