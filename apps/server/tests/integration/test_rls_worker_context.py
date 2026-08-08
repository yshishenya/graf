from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from tests.fakes.fake_temporal import FakeTemporalClient
from tests.integration.test_playback_normalization_backfill import _seed_legacy_revision
from twobrain_rec_server.db.models import PlaybackBackfillRun
from twobrain_rec_server.normalization import pickup


def test_reconciler_is_a_no_op_while_automatic_dispatch_gate_is_closed(
    client,
    monkeypatch,
) -> None:
    maintenance_calls: list[str] = []

    async def observe_context(_db, context):
        maintenance_calls.append(context.operation_name)

    monkeypatch.setattr(pickup, "apply_tenant_context", observe_context)
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.settings.playback_normalization_automatic_dispatch_enabled = False

    result = asyncio.run(
        pickup.reconcile_normalization_jobs(
            sessionmaker=client.app_state["media_sessionmaker"],
            settings=client.app.state.settings,
            storage=client.app_state["storage"],
            temporal_client=FakeTemporalClient(),
        )
    )

    assert result == pickup.NormalizationReconcileResult()
    assert maintenance_calls == []


def test_reconciler_switches_from_two_narrow_maintenance_operations_to_exact_worker_scope(
    client,
    monkeypatch,
) -> None:
    now = datetime(2026, 7, 14, 12, 30, tzinfo=UTC)
    maintenance_calls: list[str] = []
    worker_calls: list[tuple[str, str, str, str]] = []
    original_apply_context = pickup.apply_tenant_context
    original_apply_scope = pickup.apply_tenant_scope

    async def observe_context(db, context):
        maintenance_calls.append(context.operation_name)
        await original_apply_context(db, context)

    async def observe_scope(db, scope, *, context_kind="request"):
        worker_calls.append(
            (
                str(scope.organization_id),
                str(scope.workspace_id),
                str(scope.user_id),
                str(scope.device_id),
            )
        )
        await original_apply_scope(db, scope, context_kind=context_kind)

    monkeypatch.setattr(pickup, "apply_tenant_context", observe_context)
    monkeypatch.setattr(pickup, "apply_tenant_scope", observe_scope)
    client.app.state.settings.playback_normalization_enabled = True

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            seed = await _seed_legacy_revision(db, ordinal=4000, created_at=now)
        result = await pickup.reconcile_normalization_jobs(
            sessionmaker=client.app_state["media_sessionmaker"],
            settings=client.app.state.settings,
            storage=client.app_state["storage"],
            temporal_client=FakeTemporalClient(),
            now=now,
            actor_id="rls-worker-test",
        )
        return seed, result

    seed, result = asyncio.run(exercise())
    assert maintenance_calls[0] == "playback_normalization_inventory"
    assert maintenance_calls[1:] == ["playback_normalization_dispatch"] * 3
    assert worker_calls
    assert all(call == worker_calls[0] for call in worker_calls)
    assert result.workspaces_enumerated == 1
    assert result.inventory_evaluated == 1
    assert result.dispatched == 1
    assert seed.media_revision_id is not None


def test_worker_retries_a_safe_blocked_inventory_without_operator_action(
    client,
    monkeypatch,
) -> None:
    now = datetime(2026, 7, 14, 12, 45, tzinfo=UTC)
    original_inventory = pickup.inventory_playback_backfill_page

    async def fail_inventory_once(*_args, **_kwargs):
        raise RuntimeError("synthetic database interruption")

    client.app.state.settings.playback_normalization_enabled = True

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            await _seed_legacy_revision(db, ordinal=4100, created_at=now)
        monkeypatch.setattr(pickup, "inventory_playback_backfill_page", fail_inventory_once)
        first = await pickup.reconcile_normalization_jobs(
            sessionmaker=client.app_state["media_sessionmaker"],
            settings=client.app.state.settings,
            storage=client.app_state["storage"],
            temporal_client=FakeTemporalClient(),
            now=now,
            actor_id="blocked-inventory-test",
        )
        async with client.app_state["sessionmaker"]() as db:
            blocked = await db.scalar(select(PlaybackBackfillRun))
            assert blocked is not None
            blocked_state = (blocked.state, blocked.safe_block_reason)

        monkeypatch.setattr(pickup, "inventory_playback_backfill_page", original_inventory)
        second = await pickup.reconcile_normalization_jobs(
            sessionmaker=client.app_state["media_sessionmaker"],
            settings=client.app.state.settings,
            storage=client.app_state["storage"],
            temporal_client=FakeTemporalClient(),
            now=now + timedelta(minutes=1),
            actor_id="blocked-inventory-test",
        )
        async with client.app_state["sessionmaker"]() as db:
            recovered = await db.scalar(select(PlaybackBackfillRun))
            assert recovered is not None
            recovered_state = (recovered.state, recovered.safe_block_reason)
        return first, second, blocked_state, recovered_state

    first, second, blocked_state, recovered_state = asyncio.run(exercise())
    assert first.inventory_blocked == 1
    assert first.dispatched == 0
    assert blocked_state == ("blocked", "database_unavailable")
    assert second.inventory_blocked == 0
    assert second.inventory_evaluated == 1
    assert second.dispatched == 1
    assert recovered_state == ("dispatching", None)
