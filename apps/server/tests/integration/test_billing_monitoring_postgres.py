"""Synthetic CLI/forced-RLS/transaction proofs on the existing disposable cluster."""
import asyncio
import json
import os
import signal
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import event, insert, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from tests.integration.test_billing_registry import registry_database, settings  # noqa: F401
from twobrain_rec_server.billing import monitoring
from twobrain_rec_server.billing.registry import canonical_hash
from twobrain_rec_server.cli import billing_monitoring as cli
from twobrain_rec_server.db.models import (
    BillingInvoice,
    BillingNotificationDelivery,
    BillingOperation,
    BillingRegistryGap,
    BillingRegistryImport,
    BillingWebhookEvent,
    Organization,
    UserIdentity,
    Workspace,
)
from twobrain_rec_server.db.session import create_sessionmaker
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    apply_tenant_context_to_connection,
)

pytestmark = pytest.mark.strict_rls
DAY = date(2026, 10, 31)
ARGS = cli.build_parser().parse_args(["--date", str(DAY)])
TABLES = (BillingOperation, BillingInvoice, BillingWebhookEvent, BillingNotificationDelivery,
          BillingRegistryImport, BillingRegistryGap)


@pytest.fixture
def database(registry_database):  # noqa: F811 — imported pytest fixture
    async def setup():
        engine = create_async_engine(registry_database)
        try:
            async with engine.begin() as conn:
                names = ",".join(model.__tablename__ for model in TABLES)
                for role in ("twobrain_rec_app", "twobrain_rec_maintenance", "registry_worker"):
                    await conn.execute(text(f"GRANT SELECT,INSERT,UPDATE,DELETE ON {names} TO {role}"))
                for model in TABLES:
                    flags = (await conn.execute(text(
                        "select relrowsecurity, relforcerowsecurity from pg_class where relname=:table"
                    ), {"table": model.__tablename__})).one()
                    assert flags == (True, True)
        finally:
            await engine.dispose()
    asyncio.run(setup())
    return registry_database


def invoke(url, role="twobrain_rec_maintenance"):
    return asyncio.run(cli.run(ARGS, settings=settings(url, role)))


def process(url, role="twobrain_rec_maintenance"):
    env = {**os.environ, "TWOBRAIN_DATABASE_URL": settings(url, role).database_url,
           "TWOBRAIN_BILLING_YOOKASSA_SHOP_ID": "123",
           "TWOBRAIN_BILLING_YOOKASSA_ENVIRONMENT": "test"}
    result = subprocess.run([sys.executable, "-m", cli.__name__, "--date", str(DAY)],
                            env=env, capture_output=True, text=True, timeout=20)
    assert result.stderr == ""
    return json.loads(result.stdout), result.returncode


async def fingerprint(url):
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            return [(await conn.execute(text(
                f"select coalesce(jsonb_agg(to_jsonb(t) order by id)::text, '[]') from {model.__tablename__} t"
            ))).scalar_one() for model in TABLES]
    finally:
        await engine.dispose()


async def seed(url):
    engine = create_async_engine(url)
    user, workspace, organization = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC) - timedelta(seconds=120)
    try:
        async with create_sessionmaker(engine)() as db:
            db.add(Organization(id=organization, slug=f"test-{organization}", name="Synthetic"))
            await db.flush()
            db.add(UserIdentity(id=user, organization_id=organization, external_subject=str(user)))
            await db.flush()
            db.add(Workspace(id=workspace, organization_id=organization, slug=f"test-{workspace}",
                             name="Synthetic", kind="personal", owner_user_id=user))
            await db.flush()
            operation = BillingOperation(workspace_id=workspace, kind="renewal", state="unknown",
                                         idempotency_key="private-operation", provider_id="private-provider",
                                         request_snapshot={"secret": "private-snapshot"}, created_at=now)
            db.add(operation)
            await db.flush()
            db.add(BillingInvoice(workspace_id=workspace, operation_id=operation.id,
                                 safe_number="private-invoice", amount_minor=987654321,
                                 receipt_contact_snapshot="private-contact", status="succeeded", created_at=now))
            db.add(BillingOperation(workspace_id=workspace, kind="resume_renewal", state="succeeded",
                                    idempotency_key="private-no-money", created_at=now))
            db.add(BillingOperation(workspace_id=workspace, kind="private-kind", state="private-state",
                                    idempotency_key="private-future", created_at=now + timedelta(days=1)))
            db.add(BillingOperation(workspace_id=workspace, kind="renewal", state="method_required",
                                    idempotency_key="private-compatibility", created_at=now))
            for index, state in enumerate(monitoring.WEBHOOK_STATES):
                db.add(BillingWebhookEvent(workspace_id=workspace, provider_event_id=f"private-event-{index}",
                                          event_type="private-event", object_id="private-object",
                                          occurred_at=datetime(1970, 1, 1, tzinfo=UTC), payload_hash="f" * 64,
                                          state=state, received_at=now + timedelta(seconds=index * 10)))
            for index, state in enumerate(monitoring.DELIVERY_STATES):
                db.add(BillingNotificationDelivery(workspace_id=workspace, recipient_id=user,
                                                  event_id=f"private-notification-{index}", channel="email",
                                                  template_key="private-template", state=state, attempts=index,
                                                  last_error_code="postal_outcome_unknown",
                                                  safe_payload={"private": "private-payload"}, created_at=now))
            await db.commit()
    finally:
        await engine.dispose()


def test_empty_then_populated_cli_restart_privacy_and_no_writes(database):
    empty, code = process(database)
    assert code == 0 and empty["coverage"] == "partial"
    families = empty["families"]
    assert len(families) == 11
    assert families["payment_state"]["values"]["operations"]["count"] == 0
    assert families["storage"]["values"] is None
    assert families["ingress_and_duplicates"]["reason_code"] == "uninstrumented"
    assert families["registry"]["reason_code"] == "unverified"
    asyncio.run(seed(database))
    before = asyncio.run(fingerprint(database))
    for _ in range(2):
        result, code = process(database)
        assert code == 0
        serialized = json.dumps(result)
        assert "private-" not in serialized and "987654321" not in serialized
        assert "1970" not in serialized and "postal_outcome_unknown" not in serialized
        assert "provider_id" not in serialized and "shop_id" not in serialized
        families = result["families"]
        assert families["payment_state"]["scope"] == "database_inventory"
        operations = families["operation_uncertainty"]["values"]
        assert operations["count"] == 4 and operations["invalid_time_count"] == 1
        assert operations["oldest_age_seconds"] is None
        assert any(row["kind"] == "resume_renewal" and row["state"] == "succeeded" for row in operations["groups"])
        assert families["webhook_queue"]["values"]["queue"]["count"] == 2
        age = families["webhook_queue"]["values"]["queue"]["oldest_age_seconds"]
        assert 120 <= age < 150
        assert families["webhook_queue"]["values"]["transport_lag_seconds"] is None
        assert families["notifications"]["values"]["queue"]["count"] == 2
        assert families["notifications"]["values"]["failed"]["count"] == 1
        assert families["notifications"]["values"]["stored_attempts"] == 10
        assert datetime.fromisoformat(result["finished_at"]) >= datetime.fromisoformat(result["as_of"])
    assert asyncio.run(fingerprint(database)) == before


def test_real_identity_and_readonly_before_first_hook(database, monkeypatch):
    for role in ("twobrain_rec_app", "registry_worker", "twobrain_rec"):
        result, code = process(database, role)
        assert code == 1 and result == cli.failure("database_identity_rejected")
    actual = cli.create_async_engine
    observed = []
    before_dialect = []

    def instrument(*args, **kwargs):
        engine = actual(*args, **kwargs)

        @event.listens_for(engine.sync_engine, "do_connect")
        def startup(dialect, record, args, kwargs):
            connection = dialect.connect(*args, **kwargs)
            cursor = connection.cursor()
            cursor.execute("select current_setting('transaction_isolation'), current_setting('transaction_read_only'), current_setting('statement_timeout'), current_setting('lock_timeout')")
            before_dialect.append(cursor.fetchone())
            cursor.close()
            connection.rollback()
            return connection

        @event.listens_for(engine.sync_engine, "before_cursor_execute")
        def check(conn, cursor, statement, parameters, context, executemany):
            if not observed:
                cursor.execute("select current_setting('transaction_isolation'), current_setting('transaction_read_only'), current_setting('statement_timeout'), current_setting('lock_timeout')")
                observed.append(cursor.fetchone())
        return engine
    monkeypatch.setattr(cli, "create_async_engine", instrument)
    assert invoke(database)[1] == 0
    assert observed == [("repeatable read", "on", "5s", "2s")]
    assert before_dialect == observed


def test_set_role_and_wrong_context_denied_and_mutation_rejected(database, monkeypatch):
    actual = cli.collect_billing_report

    async def injected(db, **kwargs):
        if mode == "set_role":
            await db.execute(text("SET ROLE twobrain_rec_maintenance"))
        elif mode == "wrong_context":
            await db.execute(text("select set_config('app.maintenance_operation', 'operator_diagnostics', true)"))
        else:
            await db.execute(text("delete from billing_operations"))
        return await actual(db, **kwargs)
    monkeypatch.setattr(cli, "collect_billing_report", injected)
    for mode in ("set_role", "wrong_context", "mutation"):
        role = "registry_worker" if mode == "set_role" else "twobrain_rec_maintenance"
        result, code = invoke(database, role)
        assert code == 1
        assert result == cli.failure("report_unavailable" if mode == "mutation" else "database_identity_rejected")


def test_schema_error_and_query_timeout_are_whole_safe_failures(database, monkeypatch):
    async def query(db, **kwargs):
        await db.execute(text("select pg_sleep(10)" if mode == "timeout" else "select private_missing_column from billing_operations"))
    monkeypatch.setattr(cli, "collect_billing_report", query)
    for mode in ("schema", "timeout"):  # noqa: B007 — query callback captures mode
        result, code = invoke(database)
        assert code == 1 and result == cli.failure("report_unavailable")


def test_total_deadline_includes_connect_and_safe_scope(database, monkeypatch):
    # Use an actual TCP acceptor that never finishes PostgreSQL authentication.
    async def stalled_server():
        connections = []
        async def stall(reader, writer):
            connections.append(writer)
            await reader.read()
        server = await asyncio.start_server(stall, "127.0.0.1", 0)
        url = make_url(settings(database).database_url).set(port=server.sockets[0].getsockname()[1])
        try:
            configured = settings(database).model_copy(update={"database_url": url.render_as_string(hide_password=False)})
            return await cli.run(ARGS, settings=configured)
        finally:
            server.close()
            for writer in connections:
                writer.close()
                await writer.wait_closed()
            await asyncio.wait_for(server.wait_closed(), 1)
    # The real connection is stalled; shorten only the enclosing deadline for this test.
    monkeypatch.setattr(cli, "REPORT_TIMEOUT_SECONDS", 0.2)
    assert asyncio.run(stalled_server()) == (cli.failure("report_timeout"), 1)
    assert asyncio.run(cli.run(ARGS, settings=settings(database).model_copy(
        update={"billing_yookassa_shop_id": None}))) == (cli.failure("invalid_scope"), 2)


def test_output_limit_is_whole_failure(database, monkeypatch):
    monkeypatch.setattr(cli, "MAX_OUTPUT_BYTES", 100)
    assert invoke(database) == (cli.failure("report_limit_exceeded"), 1)


def test_repeatable_snapshot_after_registry_lock_and_lock_timeout(database, monkeypatch):
    async def scenario(timeout):
        writer = create_async_engine(settings(database).database_url)
        entered = asyncio.Event()
        actual = monitoring.registry_status
        key = canonical_hash(["test", "123", DAY.isoformat()])

        async def waiting(db, **kwargs):
            entered.set()
            return await actual(db, **kwargs)
        monkeypatch.setattr(monitoring, "registry_status", waiting)
        try:
            async with writer.begin() as conn:
                await apply_tenant_context_to_connection(conn, MaintenanceTenantContext(
                    operation_name="billing_reconciliation", actor_id="synthetic-operator",
                    reason_category="registry_import", feature_area="billing",
                ))
                await conn.execute(text("select pg_advisory_xact_lock(hashtextextended(:scope,0))"), {"scope": key})
                task = asyncio.create_task(cli.run(ARGS, settings=settings(database)))
                await asyncio.wait_for(entered.wait(), 5)
                if timeout:
                    result = await task
                    assert result == (cli.failure("report_unavailable"), 1)
                    return
                receipt = (await conn.execute(insert(BillingRegistryImport).values(
                    environment="test", shop_id="123", report_date=DAY, profile="synthetic",
                    config_fingerprint="a" * 64, input_digest="c" * 64, parts=[], expected_empty=[],
                    accepted=True, files_complete=True, result_code="accepted_complete",
                    operator="synthetic-operator", reason_code="initial_import",
                ).returning(BillingRegistryImport.id))).scalar_one()
                now = datetime.now(UTC)
                await conn.execute(insert(BillingRegistryGap).values(
                    environment="test", shop_id="123", report_date=DAY, kind="payments",
                    part_index=1, reason="missing_part", generation=1, owner="synthetic-owner",
                    detected_receipt_id=receipt, detected_at=now, checked_at=now,
                    deadline_at=now + timedelta(hours=24),
                ))
                # Prove the reader is really waiting, rather than scheduling a coincidental order.
                for _ in range(100):
                    waits = (await conn.execute(text("select count(*) from pg_locks where locktype='advisory' and not granted"))).scalar_one()
                    if waits:
                        break
                    await asyncio.sleep(0.01)
                assert waits > 0 and not task.done()
            old, code = await task
            assert code == 0
            new, code = await asyncio.to_thread(process, database)
            assert code == 0
            old_registry = old["families"]["registry"]["values"]
            new_registry = new["families"]["registry"]["values"]
            assert old_registry["latest_accepted"] is None and old_registry["detected_count"] == 0
            assert old_registry["detected_gaps"] == []
            assert new_registry["latest_accepted"]["files_complete"] is True
            assert new_registry["detected_count"] == len(new_registry["detected_gaps"]) == 1
        finally:
            monkeypatch.setattr(monitoring, "registry_status", actual)
            await writer.dispose()
    asyncio.run(seed(database))
    asyncio.run(scenario(False))
    asyncio.run(scenario(True))


def test_registry_projection_scope_and_bounded_preflight(database, monkeypatch):
    async def seed_registry(count, shop="123"):
        engine = create_async_engine(settings(database).database_url)
        now = datetime.now(UTC) - timedelta(hours=1)
        try:
            async with engine.begin() as conn:
                await apply_tenant_context_to_connection(conn, MaintenanceTenantContext(
                    operation_name="billing_reconciliation", actor_id="synthetic-operator",
                    reason_category="registry_import", feature_area="billing",
                ))
                receipt = (await conn.execute(insert(BillingRegistryImport).values(
                    environment="test", shop_id=shop, report_date=DAY, profile="private-profile",
                    config_fingerprint="a" * 64, input_digest=f"{count:064x}", parts=[], expected_empty=[],
                    accepted=True, files_complete=False, result_code="accepted_incomplete",
                    operator="private-operator", reason_code="initial_import", created_at=now,
                ).returning(BillingRegistryImport.id))).scalar_one()
                for index in range(count):
                    await conn.execute(insert(BillingRegistryGap).values(
                        environment="test", shop_id=shop, report_date=DAY, kind="payments",
                        part_index=index % 65, reason="missing_part" if count == 1 else f"private-reason-{index // 65}",
                        generation=1, owner="private-owner",
                        detected_receipt_id=receipt, detected_at=now, checked_at=now,
                        deadline_at=now + timedelta(hours=24),
                    ))
        finally:
            await engine.dispose()
    asyncio.run(seed_registry(1))
    asyncio.run(seed_registry(1, "999"))
    before = asyncio.run(fingerprint(database))
    result, code = process(database)
    assert code == 0
    registry = result["families"]["registry"]
    assert registry["scope"] == "proven_current_shop"
    assert registry["values"]["detected_count"] == 1
    assert registry["values"]["financial_status"] == "not_checked"
    assert registry["values"]["latest_accepted"]["files_complete"] is False
    gap = registry["values"]["detected_gaps"][0]
    assert gap["owner"] == "owner_unverified"
    assert datetime.fromisoformat(gap["deadline_at"]) > datetime.fromisoformat(result["as_of"])
    assert "private-" not in json.dumps(result)
    assert asyncio.run(fingerprint(database)) == before
    class EarlierClock:
        @staticmethod
        def now(tz):
            return datetime.now(tz) - timedelta(hours=2)
    with monkeypatch.context() as clock:
        clock.setattr(cli, "datetime", EarlierClock)
        future, code = invoke(database)
    assert code == 0
    future_registry = future["families"]["registry"]
    assert future_registry["reason_code"] == "invalid_time"
    assert future_registry["values"]["invalid_time_count"] > 0
    assert future_registry["values"]["latest_accepted"]["created_at"] is None
    asyncio.run(seed_registry(500))
    assert process(database) == (cli.failure("report_limit_exceeded"), 1)


def test_recognized_compatibility_states_stay_partial(database):
    asyncio.run(seed(database))
    async def remove_unknown():
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                await conn.execute(text("update billing_operations set kind='renewal', state='succeeded', created_at=now() - interval '1 hour' where kind='private-kind'"))
        finally:
            await engine.dispose()
    asyncio.run(remove_unknown())
    result, code = invoke(database)
    assert code == 0
    assert result["families"]["operation_uncertainty"]["reason_code"] == "read_compatibility_state"


def test_sigint_and_cleanup_error_never_leak_or_succeed(database, monkeypatch):
    async def cancel_process():
        engine = create_async_engine(database)
        child = None
        try:
            async with engine.begin() as conn:
                key = canonical_hash(["test", "123", DAY.isoformat()])
                await conn.execute(text("select pg_advisory_xact_lock(hashtextextended(:scope,0))"), {"scope": key})
                env = {**os.environ, "TWOBRAIN_DATABASE_URL": settings(database).database_url,
                       "TWOBRAIN_BILLING_YOOKASSA_SHOP_ID": "123",
                       "TWOBRAIN_BILLING_YOOKASSA_ENVIRONMENT": "test"}
                child = subprocess.Popen([sys.executable, "-m", cli.__name__, "--date", str(DAY)],
                                         env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                for _ in range(500):
                    waiting = (await conn.execute(text("select count(*) from pg_locks where locktype='advisory' and not granted"))).scalar_one()
                    if waiting:
                        break
                    await asyncio.sleep(0.01)
                assert waiting > 0
                child.send_signal(signal.SIGINT)
                stdout, stderr = await asyncio.to_thread(child.communicate, timeout=5)
                assert child.returncode == 1 and stderr == ""
                assert json.loads(stdout) == cli.failure("report_cancelled")
        finally:
            if child is not None and child.poll() is None:
                child.kill()
                await asyncio.to_thread(child.communicate, timeout=5)
            await engine.dispose()
    asyncio.run(cancel_process())
    actual = cli.create_async_engine
    http_calls = []

    def no_http(*args, **kwargs):
        http_calls.append(True)
        raise AssertionError("unexpected HTTP")
    monkeypatch.setattr(httpx.Client, "request", no_http)
    monkeypatch.setattr(httpx.AsyncClient, "request", no_http)

    def cleanup_failure(*args, **kwargs):
        engine = actual(*args, **kwargs)
        dispose = engine.dispose

        async def fail():
            await dispose()
            raise RuntimeError("private-cleanup-url-and-row")
        # Keep the actual SQLAlchemy engine for sessions; replace the class method
        # only after retaining the bound original cleanup above.
        monkeypatch.setattr(type(engine), "dispose", lambda self: fail())
        return engine
    monkeypatch.setattr(cli, "create_async_engine", cleanup_failure)
    assert invoke(database) == (cli.failure("report_unavailable"), 1)
    assert http_calls == []


def test_expired_deadline_still_bounds_cleanup(database, monkeypatch):
    actual = cli.create_async_engine
    entered, pools = [], []

    async def collector(db, **kwargs):
        await asyncio.sleep(1)

    def blocked_cleanup(*args, **kwargs):
        engine = actual(*args, **kwargs)
        pools.append(engine.pool)

        async def dispose(self):
            entered.append(True)
            await asyncio.sleep(30)
        monkeypatch.setattr(type(engine), "dispose", dispose)
        return engine
    monkeypatch.setattr(cli, "collect_billing_report", collector)
    monkeypatch.setattr(cli, "create_async_engine", blocked_cleanup)
    monkeypatch.setattr(cli, "REPORT_TIMEOUT_SECONDS", 0.05)

    async def bounded():
        async with asyncio.timeout(1):
            return await cli.run(ARGS, settings=settings(database))
    assert asyncio.run(bounded()) == (cli.failure("report_timeout"), 1)
    assert entered == [True]
    assert pools[0].checkedout() == 0


def test_expired_deadline_bounds_session_close_and_disconnects(database, monkeypatch):
    actual_close = AsyncSession.close
    sessions, drivers, pools = [], [], []
    async def stalled_close(self):
        sessions.append(self)
        await asyncio.sleep(30)
    async def collector(db, **kwargs):
        connection = await db.connection()
        pools.append(connection.engine.pool)
        drivers.append((await connection.get_raw_connection()).driver_connection)
        await asyncio.sleep(30)
    monkeypatch.setattr(AsyncSession, "close", stalled_close)
    monkeypatch.setattr(cli, "collect_billing_report", collector)
    monkeypatch.setattr(cli, "REPORT_TIMEOUT_SECONDS", 0.2)
    async def bounded():
        try:
            async with asyncio.timeout(1):
                result = await cli.run(ARGS, settings=settings(database))
            assert result == (cli.failure("report_timeout"), 1)
            assert len(sessions) == len(drivers) == 1 and drivers[0].is_closed()
            assert pools[0].checkedout() == 0 and not sessions[0].in_transaction()
        finally:
            for db in sessions:
                await db.invalidate()
                await actual_close(db)
    asyncio.run(bounded())
