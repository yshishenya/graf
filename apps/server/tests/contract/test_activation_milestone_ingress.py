"""Trusted admission on disposable PostgreSQL; never enable a real provider."""

import asyncio
import os
from contextlib import nullcontext
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import USER_ID, principal
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import ProductActivationMilestone, UserIdentity
from twobrain_rec_server.product_analytics import ingest, legal_basis_gate
from twobrain_rec_server.product_analytics.activation_fence import ActivationHold, activation_fence
from twobrain_rec_server.product_analytics.identity import build_safe_identity
from twobrain_rec_server.product_analytics.ingest import ProductAnalyticsIngestService
from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
    BASIS_WITHDRAWAL_STATE_FILE_ENV,
)


def payload(name="first_recording_completed", user_id=USER_ID):
    return {
        "event_name": name,
        "stable_pseudonymous_user_id": build_safe_identity(
            user_source_id=str(user_id)
        ).stable_pseudonymous_user_id,
        "properties": {},
    }


@pytest.fixture
def isolated_admission(monkeypatch, tmp_path):
    # Replace only the still-blocked operating receipts in this test process.
    # The real resolver stays fail-closed pending T110/T113 recovery verification.
    monkeypatch.setattr(ingest, "activation_milestone_write_blockers", lambda settings: ())
    directory = (tmp_path / "operator").resolve()
    directory.mkdir(mode=0o700)
    path = directory / "state.json"
    lock = directory / "activation.lock"
    lock.write_bytes(b"synthetic permanent inode")
    lock.chmod(0o600)
    monkeypatch.setenv("GRAF_PRODUCT_ACTIVATION_STATE_FILE", str(path))
    monkeypatch.setenv("GRAF_PRODUCT_ACTIVATION_OWNER_UID", str(os.geteuid()))
    # Only this Mac test opener bypasses read-only mount validation. Actual
    # flock/UID/inode checks remain; production must keep readonly=True.
    monkeypatch.setattr(ingest, "activation_fence", lambda path, *, owner_uid:
                        activation_fence(path, owner_uid=owner_uid, readonly=False), raising=False)
    monkeypatch.setattr(
        ingest, "resolve_provider_delivery_gate", lambda *a, **kw: SimpleNamespace(allowed=True)
    )
    monkeypatch.setattr(
        ingest.YandexOfflineConversionExporter, "transfer_decision",
        lambda *a, **kw: SimpleNamespace(allowed=True),
    )

    def forbidden(*a, **kw):
        raise AssertionError("admission must never enter provider transport")

    monkeypatch.setattr(
        "twobrain_rec_server.product_analytics.posthog_client.PostHogClientWrapper.capture_event",
        forbidden,
    )
    monkeypatch.setattr(
        "twobrain_rec_server.product_analytics.router.ParallelMeasurementRouter.dispatch", forbidden
    )
    return path


def run(url, scenario):
    async def execute():
        engine = create_async_engine(url, poolclass=NullPool)
        try:
            await scenario(async_sessionmaker(engine, expire_on_commit=False), engine)
        finally:
            await engine.dispose()

    asyncio.run(execute())


@pytest.mark.parametrize("phase", ["commit", "close"])
@pytest.mark.parametrize("fail_commit", [False, True])
@pytest.mark.parametrize("cancel_twice", [False, True])
def test_fence_covers_transaction_and_close_even_after_repeated_cancellation(
    postgres_seeded_database_url, isolated_admission, phase, fail_commit, cancel_twice,
):
    path = isolated_admission

    def exclusive_available():
        try:
            with activation_fence(path, owner_uid=os.geteuid(), exclusive=True, timeout=0):
                return True
        except ActivationHold as exc:
            assert str(exc) == "activation_lock_busy"
            return False

    async def scenario(sessions, engine):
        entered, release = asyncio.Event(), asyncio.Event()
        closed = False
        acquired_before_factory = []

        class PausedSession(AsyncSession):
            async def commit(self):
                if phase == "commit":
                    entered.set()
                    await release.wait()
                if fail_commit:
                    raise RuntimeError("synthetic commit failure")
                await super().commit()

            async def close(self):
                nonlocal closed
                if phase == "close":
                    entered.set()
                    await release.wait()
                await super().close()
                closed = True

        def factory():
            acquired_before_factory.append(not exclusive_available())
            return PausedSession(engine, expire_on_commit=False)

        request = asyncio.create_task(ProductAnalyticsIngestService(
            Settings(product_analytics_enabled=True, product_analytics_validation_mode="local_only")
        ).ingest_authenticated(payload(), principal=principal(), sessionmaker=factory, source_kind="desktop"))
        cancelled = False
        try:
            await asyncio.wait_for(entered.wait(), timeout=3)
            assert acquired_before_factory == [True]
            assert not exclusive_available()
            if cancel_twice:
                assert request.cancel("first cancellation")
                cancelled = True
                await asyncio.sleep(0)
                assert request.cancel("second cancellation")
                await asyncio.sleep(0)
                assert not request.done()
                assert not closed and not exclusive_available()
        finally:
            release.set()
            if cancelled:
                with pytest.raises(asyncio.CancelledError, match="first cancellation"):
                    await asyncio.wait_for(request, timeout=3)
            else:
                result = await asyncio.wait_for(request, timeout=3)
                assert result.status == ("database_unavailable" if fail_commit else "accepted")
        assert closed and exclusive_available()
        async with sessions() as db:
            assert await db.scalar(select(func.count()).select_from(ProductActivationMilestone)) == (
                0 if fail_commit else 1
            )

    run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("failure", [
    "state_missing", "uid_missing", "uid_invalid", "uid_wrong", "lock_missing", "lock_busy", "mount_writable",
])
def test_fence_refuses_before_creating_database_session(isolated_admission, monkeypatch, failure):
    path = isolated_admission
    if failure in {"state_missing", "uid_missing"}:
        monkeypatch.delenv("GRAF_PRODUCT_ACTIVATION_" + ("STATE_FILE" if failure == "state_missing" else "OWNER_UID"))
    elif failure == "uid_invalid":
        monkeypatch.setenv("GRAF_PRODUCT_ACTIVATION_OWNER_UID", "unknown")
    elif failure == "uid_wrong":
        monkeypatch.setenv("GRAF_PRODUCT_ACTIVATION_OWNER_UID", str(os.geteuid() + 1))
    elif failure == "lock_missing":
        (path.parent / "activation.lock").unlink()
    elif failure == "mount_writable":
        monkeypatch.setattr(ingest, "activation_fence", activation_fence)

    calls = []

    def forbidden_session():
        calls.append(True)
        raise AssertionError("database must not be entered")

    with (activation_fence(path, owner_uid=os.geteuid(), exclusive=True, timeout=0)
          if failure == "lock_busy" else nullcontext()):
        result = asyncio.run(ProductAnalyticsIngestService(Settings(
            product_analytics_enabled=True, product_analytics_validation_mode="local_only",
        )).ingest_authenticated(
            payload(), principal=principal(), sessionmaker=forbidden_session, source_kind="desktop",
        ))
    assert result.status == "admission_blocked" and not result.accepted
    assert calls == []


def test_concurrent_ingress_owns_commit_and_keeps_original_decision(
    postgres_seeded_database_url, isolated_admission
):
    async def scenario(sessions, engine):
        async def accept():
            return await ProductAnalyticsIngestService(
                Settings(product_analytics_enabled=True)
            ).ingest_authenticated(
                payload(), principal=principal(), sessionmaker=sessions, source_kind="desktop"
            )

        results = await asyncio.gather(*(accept() for _ in range(5)))
        assert sum(item.status == "accepted" for item in results) == 1
        assert all(item.accepted and not item.provider_results for item in results)
        assert len({item.event.occurred_at for item in results}) == 1
        async with sessions() as db:
            rows = (await db.scalars(select(ProductActivationMilestone))).all()
            assert len(rows) == 1
            assert rows[0].account_id == USER_ID
            assert rows[0].posthog_state == "pending"
            # This event is not in the Yandex offline conversion catalog.
            assert rows[0].yandex_state == "not_requested"

    run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("change", ["basis", "purpose", "local_flags", "local_mode"])
def test_withdrawal_while_waiting_for_account_lock_is_rechecked_before_insert(
    postgres_seeded_database_url, isolated_admission, monkeypatch, change
):
    async def scenario(sessions, engine):
        withdrawn = False
        entered = asyncio.Event()
        pid = None
        original_context = ingest.apply_tenant_context

        async def context(db, value):
            nonlocal pid
            await original_context(db, value)
            pid = await db.scalar(text("select pg_backend_pid()"))
            entered.set()

        monkeypatch.setattr(ingest, "apply_tenant_context", context)
        monkeypatch.setattr(ingest, "activation_milestone_write_blockers", lambda s: (
            ("legal_basis_withdrawn",) if withdrawn and change == "basis" else ()
        ))
        monkeypatch.setattr(
            ingest.YandexOfflineConversionExporter, "transfer_decision",
            lambda *a, **kw: SimpleNamespace(allowed=not withdrawn),
        )
        async with sessions() as blocker:
            await blocker.scalar(select(UserIdentity.id).where(
                UserIdentity.id == USER_ID
            ).with_for_update())
            settings = Settings(
                product_analytics_enabled=True,
                product_analytics_validation_mode="local_only" if change.startswith("local_") else "disabled",
            )
            waiting = asyncio.create_task(ProductAnalyticsIngestService(settings).ingest_authenticated(
                payload("desktop_account_connected"), principal=principal(),
                sessionmaker=sessions, source_kind="server",
            ))
            await asyncio.wait_for(entered.wait(), timeout=3)
            # Observe a real PostgreSQL lock wait, not a patched admission call.
            for _ in range(100):
                state = await blocker.scalar(text(
                    "select wait_event_type from pg_stat_activity where pid=:pid"
                ), {"pid": pid})
                if state == "Lock":
                    break
                await asyncio.sleep(0.01)
            else:
                waiting.cancel()
                await asyncio.gather(waiting, return_exceptions=True)
                raise AssertionError("admission did not wait for the account lock")
            withdrawn = True
            if change == "local_flags":
                settings.product_analytics_yandex_offline_enabled = True
            elif change == "local_mode":
                settings.product_analytics_validation_mode = "live_safe"
            released_at = datetime.now(UTC)
            await blocker.rollback()
            result = await asyncio.wait_for(waiting, timeout=3)
        async with sessions() as db:
            rows = (await db.scalars(select(ProductActivationMilestone))).all()
        if change == "purpose":
            assert result.accepted and len(rows) == 1
            assert rows[0].posthog_state == "pending"
            assert rows[0].yandex_state == "not_requested"
            assert rows[0].accepted_at >= released_at
        else:
            assert not result.accepted and result.status == "admission_blocked"
            assert rows == []

    run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("local_only", [False, True])
def test_both_http_shapes_share_one_durable_decision(client, isolated_admission, monkeypatch, local_only):
    settings = client.app.state.settings
    for key in (
        "product_analytics_enabled", "product_analytics_posthog_enabled",
        "product_analytics_posthog_desktop_direct_enabled", "product_analytics_direct_desktop_egress_enabled",
    ):
        monkeypatch.setattr(settings, key, key == "product_analytics_enabled" or not local_only)
    if local_only:
        monkeypatch.setattr(settings, "product_analytics_validation_mode", "local_only")

        def forbidden(*a, **kw):
            raise AssertionError("local_only must not resolve a provider")

        monkeypatch.setattr(ingest, "resolve_provider_delivery_gate", forbidden)
        monkeypatch.setattr(ingest.YandexOfflineConversionExporter, "from_settings", forbidden)
    value = payload()
    first = client.post("/api/v1/product-analytics/events", json=value, headers=auth_headers())
    second = client.post(
        "/api/v1/product-analytics/posthog-desktop-capture",
        json={"event": value["event_name"], "distinct_id": value["stable_pseudonymous_user_id"]},
        headers=auth_headers(),
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["status"] == "accepted"
    assert second.json()["status"] == "duplicate"
    assert first.json()["event"] == second.json()["event"]
    assert first.json()["provider_results"] == second.json()["provider_results"] == []
    if local_only:
        # A later provider mode must not replay the original local decision.
        monkeypatch.setattr(settings, "product_analytics_validation_mode", "provider_smoke")
        monkeypatch.setattr(ingest, "resolve_provider_delivery_gate", lambda *a, **kw: SimpleNamespace(allowed=True))
        third = client.post("/api/v1/product-analytics/events", json=value, headers=auth_headers())
        assert third.status_code == 200 and third.json()["status"] == "duplicate"

        async def check():
            async with client.app.state.db_sessionmaker() as db:
                rows = (await db.scalars(select(ProductActivationMilestone))).all()
                assert len(rows) == 1
                assert rows[0].posthog_state == rows[0].yandex_state == "not_requested"

        asyncio.run(check())


@pytest.mark.parametrize("proxy", [False, True])
@pytest.mark.parametrize("local_only", [False, True])
def test_http_rejects_missing_account_forged_account_and_unverified_triggers(
    client, isolated_admission, monkeypatch, proxy, local_only
):
    for key in (
        "product_analytics_enabled", "product_analytics_posthog_enabled",
        "product_analytics_posthog_desktop_direct_enabled", "product_analytics_direct_desktop_egress_enabled",
    ):
        monkeypatch.setattr(client.app.state.settings, key, key == "product_analytics_enabled" or not local_only)
    if local_only:
        monkeypatch.setattr(client.app.state.settings, "product_analytics_validation_mode", "local_only")
    path = "/api/v1/product-analytics/" + ("posthog-desktop-capture" if proxy else "events")

    def send(value, headers):
        body = value if not proxy else {
            "event": value["event_name"],
            "distinct_id": value["stable_pseudonymous_user_id"],
            "properties": value["properties"],
        }
        return client.post(path, json=body, headers=headers)

    assert send(payload(), {}).status_code == 403
    assert send(payload(user_id=uuid4()), auth_headers()).status_code == 403
    for name in (
        "desktop_first_opened", "desktop_account_connected", "first_result_viewed", "first_value_session_completed",
    ):
        response = send(payload(name), auth_headers())
        assert response.status_code == 403, response.text
    if proxy:
        valid = {"event": payload()["event_name"], "distinct_id": payload()["stable_pseudonymous_user_id"]}
        assert client.post(path, json={**valid, "telemetry_gate_state": "declined"}, headers=auth_headers()).status_code == 403
        assert client.post(path, json={**valid, "api_key_state": "client_key"}, headers=auth_headers()).status_code == 400

    async def count():
        async with client.app.state.db_sessionmaker() as db:
            return await db.scalar(select(func.count()).select_from(ProductActivationMilestone))

    assert asyncio.run(count()) == 0


def test_withdrawal_after_connection_and_commit_failure_leave_no_decision(
    postgres_seeded_database_url, isolated_admission, monkeypatch
):
    async def scenario(sessions, engine):
        service = ProductAnalyticsIngestService(Settings(product_analytics_enabled=True))
        checks = iter(((), ("legal_basis_withdrawn",)))
        monkeypatch.setattr(ingest, "activation_milestone_write_blockers", lambda s: next(checks))
        result = await service.ingest_authenticated(
            payload(), principal=principal(), sessionmaker=sessions, source_kind="desktop"
        )
        assert not result.accepted and result.status == "admission_blocked"
        monkeypatch.setattr(ingest, "activation_milestone_write_blockers", lambda s: ())

        class FailedCommit(AsyncSession):
            async def commit(self):
                raise RuntimeError("synthetic commit failure")

        result = await service.ingest_authenticated(
            payload(), principal=principal(),
            sessionmaker=async_sessionmaker(engine, class_=FailedCommit), source_kind="desktop",
        )
        assert not result.accepted and result.status == "database_unavailable"
        async with sessions() as db:
            assert await db.scalar(select(func.count()).select_from(ProductActivationMilestone)) == 0

    run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("local_only", [False, True])
def test_server_auth_uses_the_same_account_ledger(
    postgres_seeded_database_url, isolated_admission, monkeypatch, local_only
):
    from twobrain_rec_server.api.auth import record_account_connected_milestone

    if local_only:
        def forbidden(*a, **kw):
            raise AssertionError("local_only must not resolve a provider")

        monkeypatch.setattr(ingest, "resolve_provider_delivery_gate", forbidden)
        monkeypatch.setattr(ingest.YandexOfflineConversionExporter, "from_settings", forbidden)

    async def scenario(sessions, engine):
        user = principal()
        results = [await record_account_connected_milestone(
            settings=Settings(
                product_analytics_enabled=True,
                product_analytics_validation_mode="local_only" if local_only else "disabled",
            ), user_id=user.user_id,
            organization_id=user.organization_id, workspace_id=next(iter(user.workspace_ids)),
            sessionmaker=sessions, provider="synthetic", handoff=None,
        ) for _ in range(2)]
        assert [item.status for item in results] == ["accepted", "duplicate"]
        async with sessions() as db:
            row = await db.scalar(select(ProductActivationMilestone))
            assert row.source_kind == "server"
            assert row.posthog_state == row.yandex_state == ("not_requested" if local_only else "pending")

    run(postgres_seeded_database_url, scenario)


def test_auth_milestone_builder_failure_is_best_effort(monkeypatch):
    from twobrain_rec_server.api import auth

    def broken(**kwargs):
        raise ValueError("synthetic builder failure")

    monkeypatch.setattr(auth, "build_account_connected_product_analytics_payload", broken)
    user = principal()
    result = asyncio.run(auth.record_account_connected_milestone(
        settings=Settings(product_analytics_enabled=True), user_id=user.user_id,
        organization_id=user.organization_id, workspace_id=next(iter(user.workspace_ids)),
        sessionmaker=None, provider="synthetic", handoff=None,
    ))
    assert result is None


@pytest.mark.parametrize("record", [
    "", "basis_withdrawal level=attribution_profiles state=withdrawn withdrawn_at=broken",
    "basis_withdrawal level=attribution_profiles state=withdrawn withdrawn_at=2026-01-01 reason=owner_decision",
])
@pytest.mark.parametrize("mode", ["live_safe", "local_only"])
def test_runtime_gate_never_opens_on_missing_or_partial_recovery(tmp_path, monkeypatch, record, mode):
    path = tmp_path / "basis"
    monkeypatch.setenv(BASIS_WITHDRAWAL_STATE_FILE_ENV, str(path))
    settings = Settings(
        product_analytics_enabled=True, product_analytics_validation_mode=mode,
        product_analytics_legal_approved=True, product_analytics_disclosure_approved=True,
    )
    monkeypatch.setattr(
        legal_basis_gate, "build_analytics_operations_readiness", lambda s: SimpleNamespace(blockers=())
    )
    assert "basis_unavailable" in legal_basis_gate.activation_milestone_write_blockers(settings)
    path.write_text("legal_basis_state_version=1\n" + record)
    blockers = legal_basis_gate.activation_milestone_write_blockers(settings)
    assert "activation_recovery_unverified" in blockers
    if "broken" in record:
        assert "basis_unavailable" in blockers
    elif record:
        assert "legal_basis_withdrawn" in blockers
    if mode == "local_only":
        settings.product_analytics_yandex_offline_enabled = True
        assert "local_only_configuration_invalid" in legal_basis_gate.activation_milestone_write_blockers(settings)


def test_local_only_real_recovery_gate_keeps_both_http_and_server_auth_closed(client, monkeypatch):
    from twobrain_rec_server.api.auth import record_account_connected_milestone

    settings = client.app.state.settings
    monkeypatch.setattr(settings, "product_analytics_enabled", True)
    monkeypatch.setattr(settings, "product_analytics_validation_mode", "local_only")
    first = client.post("/api/v1/product-analytics/events", json=payload(), headers=auth_headers())
    second = client.post(
        "/api/v1/product-analytics/posthog-desktop-capture",
        json={"event": payload()["event_name"], "distinct_id": payload()["stable_pseudonymous_user_id"]},
        headers=auth_headers(),
    )
    assert first.status_code == second.status_code == 403
    assert first.json()["code"] == "product_analytics_admission_blocked"
    assert second.json()["code"] == "posthog_desktop_admission_blocked"

    async def check():
        user = principal()
        result = await record_account_connected_milestone(
            settings=settings, user_id=user.user_id, organization_id=user.organization_id,
            workspace_id=next(iter(user.workspace_ids)),
            sessionmaker=client.app.state.db_sessionmaker, provider="synthetic", handoff=None,
        )
        assert not result.accepted and result.status == "admission_blocked"
        async with client.app.state.db_sessionmaker() as db:
            assert await db.scalar(select(func.count()).select_from(ProductActivationMilestone)) == 0

    asyncio.run(check())
