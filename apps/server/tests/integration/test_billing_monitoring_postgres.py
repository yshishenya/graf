"""Synthetic CLI/forced-RLS/transaction proofs on the existing disposable cluster."""
import asyncio
import json
import os
import signal
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    String,
    column,
    delete,
    event,
    insert,
    text,
    values,
)
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from tests.integration.test_billing_registry import registry_database, settings  # noqa: F401
from twobrain_rec_server.billing import monitoring
from twobrain_rec_server.billing.database import BillingMaintenanceDatabaseError
from twobrain_rec_server.billing.registry import canonical_hash
from twobrain_rec_server.cli import billing_monitoring as cli
from twobrain_rec_server.db.models import (
    BillingAuditEvent,
    BillingEntitlementGrant,
    BillingInvoice,
    BillingNotificationDelivery,
    BillingOperation,
    BillingRegistryGap,
    BillingRegistryImport,
    BillingStorageEntitlementGrant,
    BillingWebhookEvent,
    FairUseReviewRecord,
    MediaRevision,
    Meeting,
    MeetingDeletionRequest,
    ObservedProviderRefund,
    Organization,
    PlaybackNormalizationJob,
    RegisteredDevice,
    StorageReservation,
    TimeCreditLedgerEntry,
    TrackArtifact,
    UploadSession,
    UserIdentity,
    Workspace,
    WorkspaceSubscription,
)
from twobrain_rec_server.db.session import create_sessionmaker
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    apply_tenant_context_to_connection,
    maintenance_context_settings,
)

pytestmark = pytest.mark.strict_rls
DAY = date(2026, 10, 31)
ARGS = cli.build_parser().parse_args(["--date", str(DAY)])
TABLES = (BillingAuditEvent, BillingOperation, BillingInvoice, BillingWebhookEvent, BillingNotificationDelivery,
          BillingRegistryImport, BillingRegistryGap, TimeCreditLedgerEntry, ObservedProviderRefund, FairUseReviewRecord,
          MeetingDeletionRequest)
STORAGE_TABLES = (Workspace, WorkspaceSubscription, StorageReservation, BillingEntitlementGrant,
                  BillingStorageEntitlementGrant, TrackArtifact, UploadSession, MediaRevision, Meeting, PlaybackNormalizationJob)


def test_observation_source_probe_partial_counts_roles_and_no_writes(database, caplog):
    from twobrain_rec_server.cli.billing_observation_probe import run

    profile, generation = str(uuid4()), str(uuid4())

    def config(role="twobrain_rec_maintenance"):
        return {"source_profile": profile, "source_generation": generation,
                "database_url": settings(database, role).database_url}

    async def probe():
        empty = await run(config())
        assert empty == {"schema_version": 2, "source_profile": profile, "source_generation": generation,
                         "as_of": empty["as_of"], "coverage": "partial", "event_count": 0,
                         "failed_event_count": 0, "conflicting_attempt_count": 0, "last_event_at": None,
                         "receipt_canceled_count": 0, "receipt_overdue_confirmed_count": 0,
                         "receipt_overdue_unknown_count": 0}
        engine = create_async_engine(database)
        try:
            workflow = f"billing-reconciliation/{uuid4()}/v1"
            run_id = str(uuid4())
            statement = text("""INSERT INTO billing_reconciliation_observations
                (namespace,workflow_id,workflow_run_id,activity_id,attempt,event_kind,observed_at)
                VALUES ('private-source-namespace',:workflow,:run,'private-source-activity',:attempt,:kind,:at)""")
            old = datetime.now(UTC) - timedelta(days=30)
            async with engine.begin() as conn:
                for attempt, kinds in ((1, ("started", "succeeded")), (2, ("started", "failed")),
                                       (3, ("succeeded", "failed")), (4, ("started",))):
                    for kind in kinds:
                        await conn.execute(statement, {"workflow": workflow, "run": run_id,
                                                       "attempt": attempt, "kind": kind, "at": old})
            async def fingerprint():
                async with engine.connect() as conn:
                    return (await conn.execute(text("SELECT row_to_json(t)::text FROM billing_reconciliation_observations t "
                                                    "ORDER BY namespace,workflow_id,workflow_run_id,activity_id,attempt,event_kind"))).scalars().all()
            before = await fingerprint()
            for _ in range(2):
                result = await run(config())
                assert result["event_count"] == 7 and result["failed_event_count"] == 2
                assert result["conflicting_attempt_count"] == 1 and result["coverage"] == "partial"
                assert datetime.fromisoformat(result["last_event_at"]) == old
                assert "private-source" not in json.dumps(result) and len(json.dumps(result).encode()) < 16384
            assert await fingerprint() == before
            for role in ("twobrain_rec_app", "registry_worker", "twobrain_rec"):
                with pytest.raises((BillingMaintenanceDatabaseError, DBAPIError)):
                    await run(config(role))
            # A new process imports only the source command and gets no application settings.
            env = {k: v for k, v in os.environ.items() if not k.startswith("TWOBRAIN_")}
            env["SYNTHETIC_SOURCE_CONFIG"] = json.dumps(config())
            script = ("import asyncio,json,os; from twobrain_rec_server.cli.billing_observation_probe import run; "
                      "print(json.dumps(asyncio.run(run(json.loads(os.environ['SYNTHETIC_SOURCE_CONFIG'])))))")
            child = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True, timeout=20)
            assert child.returncode == 0 and child.stderr == ""
            assert json.loads(child.stdout)["event_count"] == 7
            assert "private-source" not in child.stdout and "postgresql" not in child.stdout
            assert await fingerprint() == before
        finally:
            await engine.dispose()

    asyncio.run(probe())
    assert "private-source" not in caplog.text and "postgresql" not in caplog.text


def test_observation_source_refuses_hidden_nonempty_receipt_history(database):
    from twobrain_rec_server.billing.observation_alerts import ObservationError
    from twobrain_rec_server.billing.observation_probe import collect_probe

    async def scenario():
        engine = create_async_engine(database)
        reader = create_async_engine(settings(database).database_url)
        try:
            async with engine.begin() as conn:
                await conn.execute(text("""
                    INSERT INTO billing_receipt_observation_deltas
                      (canceled_delta, overdue_confirmed_delta, overdue_unknown_delta) VALUES (1, 0, 0)
                """))
                await conn.execute(text("""
                    ALTER POLICY receipt_observation_read ON billing_receipt_observation_deltas USING (false)
                """))
            async with create_sessionmaker(reader)() as db:
                db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                    operation_name="billing_reconciliation", actor_id="synthetic", reason_category="synthetic",
                    feature_area="billing"))
                with pytest.raises(ObservationError):
                    await collect_probe(db, source_profile=str(uuid4()), source_generation=str(uuid4()))
        finally:
            await reader.dispose()
            await engine.dispose()

    asyncio.run(scenario())


def test_observation_source_rr_detects_old_late_commit_and_read_only_before_hooks(database):
    from twobrain_rec_server.billing.observation_probe import collect_probe
    from twobrain_rec_server.cli.billing_observation_probe import run

    profile, generation = str(uuid4()), str(uuid4())

    async def probe():
        writer = create_async_engine(database)
        reader = create_async_engine(settings(database).database_url, execution_options={
            "isolation_level": "REPEATABLE READ", "postgresql_readonly": True,
        })
        try:
            async with writer.begin() as late:
                await late.execute(text("""INSERT INTO billing_reconciliation_observations
                    (namespace,workflow_id,workflow_run_id,activity_id,attempt,event_kind,observed_at)
                    VALUES ('private-late',:workflow,:run,'private-late',1,'failed',:at)"""),
                    {"workflow": f"billing-reconciliation/{uuid4()}/v1", "run": str(uuid4()),
                     "at": datetime.now(UTC) - timedelta(days=30)})
                await late.execute(text("""
                    INSERT INTO billing_receipt_observation_deltas
                      (canceled_delta, overdue_confirmed_delta, overdue_unknown_delta)
                    VALUES (1, 0, 2)
                """))
                # This gets a later identity but commits first. Both must be included.
                async with writer.begin() as early:
                    await early.execute(text("""
                        INSERT INTO billing_receipt_observation_deltas
                          (canceled_delta, overdue_confirmed_delta, overdue_unknown_delta)
                        VALUES (0, 3, 0)
                    """))
                async with create_sessionmaker(reader)() as db:
                    db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                        operation_name="billing_reconciliation", actor_id="synthetic", reason_category="synthetic",
                        feature_area="billing"))
                    first = await collect_probe(db, source_profile=profile, source_generation=generation)
                    assert first["event_count"] == 0
                    assert [first[key] for key in ("receipt_canceled_count", "receipt_overdue_confirmed_count",
                                                   "receipt_overdue_unknown_count")] == [0, 3, 0]
                    await late.commit()
                    same = await collect_probe(db, source_profile=profile, source_generation=generation)
                    assert same["event_count"] == 0 and same["last_event_at"] is None
                    assert [same[key] for key in ("receipt_canceled_count", "receipt_overdue_confirmed_count",
                                                  "receipt_overdue_unknown_count")] == [0, 3, 0]
            observed = []

            def before_sql(conn, _cursor, _statement, _parameters, _context, _many):
                row = conn.connection.cursor()
                try:
                    row.execute("SELECT current_setting('transaction_read_only'),current_setting('transaction_isolation')")
                    observed.append(row.fetchone())
                finally:
                    row.close()

            # Includes tenant-context hooks of the actual source CLI.
            event.listen(__import__('sqlalchemy').engine.Engine, "before_cursor_execute", before_sql)
            try:
                result = await run({"source_profile": profile, "source_generation": generation,
                                    "database_url": settings(database).database_url})
            finally:
                event.remove(__import__('sqlalchemy').engine.Engine, "before_cursor_execute", before_sql)
            assert result["event_count"] == result["failed_event_count"] == 1
            assert result["conflicting_attempt_count"] == 0
            assert [result[key] for key in ("receipt_canceled_count", "receipt_overdue_confirmed_count",
                                            "receipt_overdue_unknown_count")] == [1, 3, 2]
            assert datetime.fromisoformat(result["last_event_at"]) < datetime.fromisoformat(result["as_of"]) - timedelta(days=29)
            assert observed and all(tuple(row) == ("on", "repeatable read") for row in observed)
        finally:
            await reader.dispose()
            await writer.dispose()

    asyncio.run(probe())


def test_observation_source_early_sql_timeout_cancel_and_no_backend_tail(database, monkeypatch):
    import time

    from twobrain_rec_server.cli import billing_observation_probe as source_cli

    original_factory = source_cli.create_async_engine
    application = f"synthetic-source-{uuid4()}"

    def factory(*args, **kwargs):
        kwargs["connect_args"]["server_settings"]["application_name"] = application
        engine = original_factory(*args, **kwargs)

        @event.listens_for(engine.sync_engine, "begin")
        def slow_setup(conn):
            assert conn.exec_driver_sql("SHOW transaction_read_only").scalar_one() == "on"
            assert conn.exec_driver_sql("SHOW transaction_isolation").scalar_one() == "repeatable read"
            conn.exec_driver_sql("SELECT pg_sleep(30)")

        return engine

    monkeypatch.setattr(source_cli, "create_async_engine", factory)

    async def probe():
        config = {"source_profile": str(uuid4()), "source_generation": str(uuid4()),
                  "database_url": settings(database).database_url}
        started = time.monotonic()
        with pytest.raises((DBAPIError, TimeoutError)):
            await source_cli.run(config)
        assert 4 < time.monotonic() - started < 8
        task = asyncio.create_task(source_cli.run(config))
        await asyncio.sleep(0.2)
        task.cancel()
        started = time.monotonic()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert time.monotonic() - started < 2
        admin = original_factory(database)
        try:
            async with admin.connect() as conn:
                count = (await conn.execute(text("SELECT count(*) FROM pg_stat_activity WHERE application_name=:name"),
                                            {"name": application})).scalar_one()
                assert count == 0
        finally:
            await admin.dispose()

    asyncio.run(probe())


@pytest.mark.parametrize("invalid", ["set_role", "context", "schema", "force_rls", "nonfinite"])
def test_observation_source_negative_boundary_is_whole_safe_unavailable(database, monkeypatch, capsys, invalid):
    from twobrain_rec_server.billing import observation_probe
    from twobrain_rec_server.cli import billing_observation_alerts as alerts_cli
    from twobrain_rec_server.cli import billing_observation_probe as source_cli

    role = "registry_worker" if invalid == "set_role" else "twobrain_rec_maintenance"
    config = {"source_profile": str(uuid4()), "source_generation": str(uuid4()),
              "database_url": settings(database, role).database_url}
    original_factory = source_cli.create_async_engine

    def factory(*args, **kwargs):
        engine = original_factory(*args, **kwargs)
        if invalid == "set_role":
            @event.listens_for(engine.sync_engine, "begin")
            def impersonate(conn):
                conn.exec_driver_sql("SET LOCAL ROLE twobrain_rec_maintenance")
        if invalid == "context":
            @event.listens_for(engine.sync_engine, "before_cursor_execute")
            def wrong_context(conn, _cursor, statement, _parameters, _context, _many):
                if "from pg_roles where rolname" in statement:
                    cursor = conn.connection.cursor()
                    try:
                        cursor.execute("SELECT set_config('app.maintenance_feature_area','synthetic_wrong',true)")
                    finally:
                        cursor.close()
        return engine

    async def alter(statement):
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                await conn.execute(text(statement))
        finally:
            await engine.dispose()

    revert = None
    if invalid == "schema":
        asyncio.run(alter("ALTER TABLE billing_reconciliation_observations RENAME COLUMN observed_at TO synthetic_missing"))
        revert = "ALTER TABLE billing_reconciliation_observations RENAME COLUMN synthetic_missing TO observed_at"
    elif invalid == "force_rls":
        asyncio.run(alter("ALTER TABLE billing_reconciliation_observations NO FORCE ROW LEVEL SECURITY"))
        revert = "ALTER TABLE billing_reconciliation_observations FORCE ROW LEVEL SECURITY"
    elif invalid == "nonfinite":
        # Keep the migrated finite-time CHECK intact; test a broken SQL projection.
        real_text = observation_probe.text
        monkeypatch.setattr(observation_probe, "text", lambda sql: real_text(sql.replace(
            "max(observed_at) AS last_event_at", "'infinity'::timestamptz AS last_event_at")))
    monkeypatch.setattr(source_cli, "create_async_engine", factory)
    monkeypatch.setattr(alerts_cli, "read_protected", lambda _path: config)
    try:
        with pytest.raises(SystemExit) as exited:
            source_cli.main()
        assert exited.value.code == 1
        output = capsys.readouterr()
        assert json.loads(output.out) == {"schema_version": 1, "result_code": "observation_unavailable"}
        assert output.err == "" and "postgresql" not in output.out and "synthetic_wrong" not in output.out
    finally:
        if revert is not None:
            asyncio.run(alter(revert))


@pytest.mark.parametrize("stage", ["before", "during"])
def test_observation_source_database_outage_does_not_leave_a_backend(database, monkeypatch, stage):
    import socket
    import time

    from twobrain_rec_server.cli import billing_observation_probe as source_cli

    config = {"source_profile": str(uuid4()), "source_generation": str(uuid4()),
              "database_url": settings(database).database_url}
    original_factory, original_probe = source_cli.create_async_engine, source_cli.collect_probe
    application = f"synthetic-outage-{uuid4()}"

    def factory(*args, **kwargs):
        kwargs["connect_args"]["server_settings"]["application_name"] = application
        return original_factory(*args, **kwargs)

    monkeypatch.setattr(source_cli, "create_async_engine", factory)

    async def scenario():
        admin = original_factory(database)
        try:
            if stage == "before":
                with socket.socket() as unavailable:
                    unavailable.bind(("127.0.0.1", 0))
                    port = unavailable.getsockname()[1]
                    config["database_url"] = make_url(config["database_url"]).set(port=port).render_as_string(hide_password=False)
                    started = time.monotonic()
                    with pytest.raises(OSError):
                        await source_cli.run(config)
                    assert time.monotonic() - started < 18
            else:
                async def disconnected(db, **kwargs):
                    async with admin.begin() as conn:
                        assert (await conn.execute(text(
                            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE application_name=:name"
                        ), {"name": application})).scalar_one() is True
                    return await original_probe(db, **kwargs)

                monkeypatch.setattr(source_cli, "collect_probe", disconnected)
                with pytest.raises(DBAPIError):
                    await source_cli.run(config)
            async with admin.connect() as conn:
                assert (await conn.execute(text("SELECT count(*) FROM pg_stat_activity WHERE application_name=:name"),
                                          {"name": application})).scalar_one() == 0
        finally:
            await admin.dispose()
    asyncio.run(scenario())


@pytest.mark.parametrize("stage", ["connect", "close"])
def test_observation_source_total_budget_includes_connect_and_close(database, monkeypatch, stage):
    import time
    from contextlib import suppress

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from twobrain_rec_server.cli import billing_observation_probe as source_cli

    original_factory = source_cli.create_async_engine
    application = f"synthetic-budget-{uuid4()}"
    reached = []

    def factory(*args, **kwargs):
        kwargs["connect_args"]["server_settings"]["application_name"] = application
        return original_factory(*args, **kwargs)

    class SlowClose(AsyncSession):
        async def close(self):
            reached.append(True)
            await asyncio.sleep(30)
            await super().close()

    monkeypatch.setattr(source_cli, "create_async_engine", factory)
    if stage == "close":
        monkeypatch.setattr(source_cli, "create_sessionmaker", lambda engine: async_sessionmaker(engine, class_=SlowClose))

    async def scenario():
        config = {"source_profile": str(uuid4()), "source_generation": str(uuid4()),
                  "database_url": settings(database).database_url}
        server, writers = None, []
        if stage == "connect":
            def silent(_reader, writer):
                writers.append(writer)
            server = await asyncio.start_server(silent, "127.0.0.1", 0)
            config["database_url"] = make_url(config["database_url"]).set(
                port=server.sockets[0].getsockname()[1]).render_as_string(hide_password=False)
        started = time.monotonic()
        try:
            with pytest.raises(TimeoutError):
                await source_cli.run(config)
            assert 14 < time.monotonic() - started < 18
            assert bool(reached) == (stage == "close")
            admin = original_factory(database)
            try:
                async with admin.connect() as conn:
                    assert (await conn.execute(text("SELECT count(*) FROM pg_stat_activity WHERE application_name=:name"),
                                              {"name": application})).scalar_one() == 0
            finally:
                await admin.dispose()
        finally:
            if server is not None:
                server.close()
            for writer in writers:
                # The silent TCP fixture never completes PostgreSQL/SSL negotiation.
                writer.transport.abort()
                with suppress(OSError, TimeoutError):
                    await asyncio.wait_for(writer.wait_closed(), 1)
            if server is not None:
                await server.wait_closed()
    asyncio.run(scenario())


def test_reconciliation_journal_empty_cli_is_declared_partial(database):
    result, code = process(database)
    assert code == 0
    assert result["families"]["reconciliation_attempts"] == {
        "source": "billing_reconciliation_observations", "scope": "database_inventory",
        "kind": "current_state", "coverage": "partial", "reason_code": "history_incomplete",
        "values": {"attempt_count": 0, "groups": [], "observed_retry_attempt_count": 0, "missing_start_count": 0},
    }


def reconciliation_attempt(**overrides):
    from twobrain_rec_server.billing.reconciliation_observation import ReconciliationAttempt

    return ReconciliationAttempt(**{
        "namespace": "private-namespace", "workflow_id": f"billing-reconciliation/{uuid4()}/v1",
        "workflow_run_id": uuid4(), "activity_id": "private-activity", "attempt": 1, **overrides,
    })


def test_reconciliation_journal_persists_deduplicates_conflicts_and_snapshot(database, monkeypatch):
    from dataclasses import replace

    from twobrain_rec_server.billing import reconciliation_observation as observation

    monkeypatch.setattr(observation, "get_settings", lambda: settings(database))

    async def probe():
        engine = create_async_engine(database)
        first = reconciliation_attempt()
        failed = replace(first, workflow_run_id=uuid4())
        unknown = replace(first, attempt=3)
        canceled = replace(first, activity_id="private-canceled", attempt=5)
        conflict = replace(first, activity_id="private-conflict", attempt=2)
        try:
            for attempt, kinds in ((first, ("started", "succeeded")), (failed, ("started", "failed")),
                                   (unknown, ("started",)), (canceled, ("canceled",)),
                                   (conflict, ("succeeded", "failed"))):
                for kind in kinds:
                    assert await observation.record_reconciliation_observation(attempt, kind)
            async with engine.connect() as conn:
                before = (await conn.execute(text("SELECT row_to_json(t)::text FROM billing_reconciliation_observations t ORDER BY namespace,workflow_id,workflow_run_id,activity_id,attempt,event_kind"))).scalars().all()
            assert all(await asyncio.gather(*(observation.record_reconciliation_observation(first, "succeeded") for _ in range(4))))
            async with engine.connect() as conn:
                assert (await conn.execute(text("SELECT row_to_json(t)::text FROM billing_reconciliation_observations t ORDER BY namespace,workflow_id,workflow_run_id,activity_id,attempt,event_kind"))).scalars().all() == before
                # A separate transaction rolls back without erasing observation.
                await conn.execute(text("SELECT pg_advisory_xact_lock(109109)"))
                assert await observation.record_reconciliation_observation(unknown, "started")
                await conn.rollback()
            reader = create_async_engine(settings(database).database_url, execution_options={
                "isolation_level": "REPEATABLE READ", "postgresql_readonly": True,
            })
            try:
                async with create_sessionmaker(reader)() as db:
                    db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                        operation_name="billing_reconciliation", actor_id="synthetic", reason_category="synthetic", feature_area="billing"))
                    old = await monitoring._reconciliation_attempts(db)
                    assert old["values"] == {"attempt_count": 5, "groups": [
                        {"outcome": outcome, "count": 1} for outcome in ("canceled", "conflict", "failed", "succeeded", "unknown")],
                        "observed_retry_attempt_count": 3, "missing_start_count": 2}
                    assert old["coverage"] == "partial" and old["reason_code"] == "conflicting_observations"
                    assert await observation.record_reconciliation_observation(unknown, "succeeded")
                    assert await monitoring._reconciliation_attempts(db) == old
                async with create_sessionmaker(reader)() as db:
                    db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                        operation_name="billing_reconciliation", actor_id="synthetic", reason_category="synthetic", feature_area="billing"))
                    new = await monitoring._reconciliation_attempts(db)
                    assert new["values"]["attempt_count"] == 5
                    assert new["values"]["groups"][-1] == {"outcome": "succeeded", "count": 2}
            finally:
                await reader.dispose()
        finally:
            await engine.dispose()
    asyncio.run(probe())
    baseline = asyncio.run(fingerprint(database))
    one, code = process(database)
    two, other_code = process(database, day=date(2020, 1, 1))
    assert code == other_code == 0
    assert one["families"]["reconciliation_attempts"] == two["families"]["reconciliation_attempts"]
    assert one["families"]["addon_and_time_credit"]["values"]["job_attempts"] is None
    assert "private-" not in json.dumps(one)
    assert asyncio.run(fingerprint(database)) == baseline


def test_reconciliation_journal_roles_constraints_and_immutable_history(database, monkeypatch):
    from dataclasses import asdict

    from sqlalchemy.exc import DBAPIError

    from twobrain_rec_server.billing import reconciliation_observation as observation
    from twobrain_rec_server.db.models import BillingReconciliationObservation
    from twobrain_rec_server.db.rls_validation import RLS_COVERED_TABLES

    monkeypatch.setattr(observation, "get_settings", lambda: settings(database))
    attempt = reconciliation_attempt()
    table = BillingReconciliationObservation.__table__
    assert table.name in RLS_COVERED_TABLES

    async def probe():
        assert await observation.record_reconciliation_observation(attempt, "started")
        admin = create_async_engine(database)
        try:
            async with admin.begin() as conn:
                assert (await conn.execute(text("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE relname='billing_reconciliation_observations'"))).one() == (True, True)
                assert (await conn.execute(text("SELECT has_table_privilege('twobrain_rec_maintenance','billing_reconciliation_observations','SELECT,INSERT'),has_table_privilege('twobrain_rec_maintenance','billing_reconciliation_observations','UPDATE'),has_table_privilege('twobrain_rec_maintenance','billing_reconciliation_observations','DELETE')"))).one() == (True, False, False)
                # Deliberately broad test-only grants prove the exact RLS boundary.
                await conn.execute(text("GRANT SELECT,INSERT,UPDATE,DELETE ON billing_reconciliation_observations TO twobrain_rec_app,registry_worker,twobrain_rec_maintenance"))
            for role, context, operation, area, set_role in [
                ("twobrain_rec_app", "maintenance", "billing_reconciliation", "billing", False),
                ("registry_worker", "maintenance", "billing_reconciliation", "billing", False),
                ("registry_worker", "maintenance", "billing_reconciliation", "billing", True),
                ("twobrain_rec_maintenance", "request", "billing_reconciliation", "billing", False),
                ("twobrain_rec_maintenance", "worker", "billing_reconciliation", "billing", False),
                ("twobrain_rec_maintenance", "maintenance", "operator_diagnostics", "billing", False),
                ("twobrain_rec_maintenance", "maintenance", "billing_reconciliation", "wrong", False),
            ]:
                engine = create_async_engine(settings(database, role).database_url)
                try:
                    async with engine.begin() as conn:
                        if set_role:
                            await conn.execute(text("SET ROLE twobrain_rec_maintenance"))
                        for key, value in {"app.context_kind": context, "app.maintenance_operation": operation,
                                           "app.maintenance_feature_area": area, "app.maintenance_actor": "synthetic", "app.maintenance_reason": "synthetic"}.items():
                            await conn.execute(text("SELECT set_config(:key,:value,true)"), {"key": key, "value": value})
                        assert (await conn.execute(table.select())).all() == []
                        with pytest.raises(DBAPIError):
                            await conn.execute(insert(table).values(**asdict(attempt), event_kind="failed"))
                finally:
                    await engine.dispose()
            invalid = [{"namespace": ""}, {"namespace": "я" * 128}, {"workflow_id": "private-invalid"},
                       {"workflow_run_id": None}, {"activity_id": ""}, {"activity_id": "я" * 128},
                       {"attempt": 0}, {"event_kind": "private-outcome"}, {"event_kind": None},
                       {"observed_at": None}, {"observed_at": text("'infinity'::timestamptz")}]
            for override in invalid:
                async with admin.connect() as conn:
                    with pytest.raises(DBAPIError):
                        await conn.execute(insert(table).values(**{**asdict(attempt), "event_kind": "failed", **override}))
            for sql in ("UPDATE billing_reconciliation_observations SET observed_at=clock_timestamp()", "DELETE FROM billing_reconciliation_observations"):
                async with admin.connect() as conn:
                    with pytest.raises(DBAPIError, match="history is immutable"):
                        await conn.execute(text(sql))
            for role in ("twobrain_rec", "twobrain_rec_app", "registry_worker"):
                monkeypatch.setattr(observation, "get_settings", lambda role=role: settings(database, role))
                assert not await observation.record_reconciliation_observation(attempt, "succeeded")
        finally:
            await admin.dispose()
    asyncio.run(probe())


def test_reconciliation_journal_faults_deadline_and_whole_cli_schema_failure(database, monkeypatch, caplog):
    from twobrain_rec_server.billing import reconciliation_observation as observation

    monkeypatch.setattr(observation, "get_settings", lambda: settings(database))
    attempt = reconciliation_attempt()

    async def faults():
        engine = create_async_engine(database)
        try:
            for body in ("PERFORM pg_sleep(10)", "RAISE EXCEPTION 'private-disk-url-contact' USING ERRCODE='53100'"):
                async with engine.begin() as conn:
                    await conn.execute(text(f"CREATE FUNCTION synthetic_observation_fault() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN {body}; RETURN NEW; END $$"))
                    await conn.execute(text("CREATE TRIGGER synthetic_observation_fault BEFORE INSERT ON billing_reconciliation_observations FOR EACH ROW EXECUTE FUNCTION synthetic_observation_fault()"))
                try:
                    began = asyncio.get_running_loop().time()
                    assert not await observation.record_reconciliation_observation(attempt, "started")
                    assert asyncio.get_running_loop().time() - began < 2.3
                finally:
                    async with engine.begin() as conn:
                        await conn.execute(text("DROP TRIGGER synthetic_observation_fault ON billing_reconciliation_observations"))
                        await conn.execute(text("DROP FUNCTION synthetic_observation_fault()"))
            async with engine.connect() as lock:
                await lock.execute(text("LOCK TABLE billing_reconciliation_observations IN ACCESS EXCLUSIVE MODE"))
                began = asyncio.get_running_loop().time()
                assert not await observation.record_reconciliation_observation(attempt, "started")
                assert asyncio.get_running_loop().time() - began < 2.3
                await lock.rollback()
            assert await observation.record_reconciliation_observation(attempt, "started")
            async with engine.connect() as conn:
                assert (await conn.execute(text("SELECT count(*) FROM billing_reconciliation_observations"))).scalar_one() == 1
        finally:
            await engine.dispose()
    asyncio.run(faults())
    assert "private-disk" not in caplog.text and "postgresql" not in caplog.text

    async def rename(old, new):
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                await conn.execute(text(f"ALTER TABLE {old} RENAME TO {new}"))
        finally:
            await engine.dispose()
    asyncio.run(rename("billing_reconciliation_observations", "synthetic_missing_observations"))
    try:
        assert process(database) == ({"schema_version": 1, "result_code": "report_unavailable"}, 1)
        assert not asyncio.run(observation.record_reconciliation_observation(attempt, "succeeded"))
    finally:
        asyncio.run(rename("synthetic_missing_observations", "billing_reconciliation_observations"))


@pytest.mark.parametrize("stage", ["dialect", "tenant"])
@pytest.mark.parametrize("cancellation", ["deadline", "external", "repeated"])
def test_early_sql_cancellation_has_no_graceful_close_tail(database, monkeypatch, stage, cancellation):
    import asyncpg

    from twobrain_rec_server.billing import reconciliation_observation as observation

    monkeypatch.setattr(observation, "get_settings", lambda: settings(database))
    monkeypatch.setattr(observation, "OBSERVATION_TIMEOUT_SECONDS", 0.15)
    original_engine = observation.create_async_engine
    original_close = asyncpg.Connection.close
    engines, drivers, reached = [], [], []
    entered = None
    def factory(*args, **kwargs):
        engine = original_engine(*args, **kwargs)
        engines.append(engine)
        if stage == "dialect":
            original_initialize = engine.sync_engine.dialect.initialize
            def initialize(connection):
                reached.append("dialect")
                entered.set()
                connection.exec_driver_sql("SELECT pg_sleep(10)")
                original_initialize(connection)
            monkeypatch.setattr(engine.sync_engine.dialect, "initialize", initialize)
        else:
            @event.listens_for(engine.sync_engine, "before_cursor_execute")
            def before(connection, cursor, statement, params, context, executemany):
                if "set_config" in statement and not reached:
                    reached.append("tenant")
                    entered.set()
                    connection.exec_driver_sql("SELECT pg_sleep(10)")
        return engine
    async def slow_transport_close(self, *, timeout=None):
        # Model transport close waiting for the peer until native close timeout.
        # Actual synchronous terminate must release it, rather than another task.
        drivers.append(self)
        async with asyncio.timeout(timeout):
            while not self.is_closed():
                await asyncio.sleep(0.005)
        await original_close(self, timeout=timeout)
    monkeypatch.setattr(observation, "create_async_engine", factory)
    monkeypatch.setattr(asyncpg.Connection, "close", slow_transport_close)
    async def probe():
        nonlocal entered
        entered = asyncio.Event()
        before = asyncio.all_tasks()
        started = asyncio.get_running_loop().time()
        task = asyncio.create_task(observation.record_reconciliation_observation(reconciliation_attempt(), "started"))
        if cancellation == "deadline":
            assert not await task
        else:
            await entered.wait()
            await asyncio.sleep(0.01)
            task.cancel()
            if cancellation == "repeated":
                await asyncio.sleep(0.01)
                task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        elapsed = asyncio.get_running_loop().time() - started
        assert reached == [stage]
        assert elapsed < 0.5, f"early SQL exceeded total observation budget: {elapsed:.3f}s"
        await asyncio.sleep(0.02)
        assert asyncio.all_tasks() == before
        assert all(d.is_closed() for d in drivers)
        assert all(e.sync_engine.pool.checkedout() == 0 for e in engines)
    asyncio.run(probe())


def test_reconciliation_journal_migration_roundtrip_backup_restore_and_nonempty_refusal(database, monkeypatch, tmp_path):
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy.exc import DBAPIError

    from twobrain_rec_server.billing import reconciliation_observation as observation
    from twobrain_rec_server.config import get_settings

    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "src/twobrain_rec_server/db/migrations"))
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", database)
    get_settings.cache_clear()
    dump = tmp_path / "synthetic-observations.dump"
    parsed = make_url(database)
    restored_name = f"test_observation_restore_{uuid4().hex}"
    candidates = subprocess.check_output(["docker", "ps", "--filter", "name=graf-postgres-test-bootstrap-", "--format", "{{.Names}}"], text=True).split()
    container = next(name for name in candidates if subprocess.check_output(
        ["docker", "port", name, "5432/tcp"], text=True).strip() == f"127.0.0.1:{parsed.port}")

    def docker(*args, **kwargs):
        result = subprocess.run(["docker", "exec", container, *args], capture_output=True, timeout=30, **kwargs)
        assert result.returncode == 0, "synthetic restore command must succeed"
        return result

    created = False
    try:
        command.downgrade(config, "0108_public_consent")
        command.upgrade(config, "head")
        monkeypatch.setattr(observation, "get_settings", lambda: settings(database))
        assert asyncio.run(observation.record_reconciliation_observation(reconciliation_attempt(), "failed"))
        with pytest.raises(DBAPIError, match="reconciliation observations exist"):
            command.downgrade(config, "0108_public_consent")
        expected = process(database)[0]["families"]["reconciliation_attempts"]
        dump.write_bytes(docker("pg_dump", "-U", "twobrain_rec", "-d", parsed.database, "--format=custom").stdout)
        docker("createdb", "-U", "twobrain_rec", restored_name)
        created = True
        # The dump is synthetic and temporary; restoring preserves schema/RLS/grants/triggers.
        result = subprocess.run(["docker", "exec", "-i", container, "pg_restore", "-U", "twobrain_rec", "-d", restored_name],
                                input=dump.read_bytes(), capture_output=True, timeout=30)
        assert result.returncode == 0, "synthetic pg_restore must succeed"
        restored = parsed.set(database=restored_name).render_as_string(hide_password=False)
        result, code = process(restored)
        assert code == 0 and result["families"]["reconciliation_attempts"] == expected

        async def flags():
            engine = create_async_engine(restored)
            try:
                async with engine.connect() as conn:
                    assert (await conn.execute(text("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE relname='billing_reconciliation_observations'"))).one() == (True, True)
                    with pytest.raises(DBAPIError, match="history is immutable"):
                        await conn.execute(text("DELETE FROM billing_reconciliation_observations"))
            finally:
                await engine.dispose()
        asyncio.run(flags())
    finally:
        get_settings.cache_clear()
        dump.unlink(missing_ok=True)
        if created:
            docker("dropdb", "-U", "twobrain_rec", "--force", restored_name)


def test_reconciliation_journal_actual_activity_commit_unknown_and_privileged_guard(database, monkeypatch, caplog):
    from tests.unit.test_billing_reconciliation_activity import observation_environment
    from twobrain_rec_server.billing import reconciliation_observation as observation
    from twobrain_rec_server.workflows import worker

    monkeypatch.setattr(observation, "get_settings", lambda: settings(database))
    calls = []

    async def financial(payload):
        calls.append(payload)
        return {"processed": 3}

    monkeypatch.setattr(worker, "_run_billing_reconciliation_activity", financial)

    async def probe():
        env = observation_environment(attempt=7)
        payload = {"run_id": str(uuid4())}
        assert await env.run(worker.run_billing_reconciliation_activity, payload) == {"processed": 3}
        assert calls == [payload]
        engine = create_async_engine(database)
        try:
            async with engine.connect() as conn:
                rows = (await conn.execute(text("SELECT namespace,workflow_run_id::text,attempt,event_kind FROM billing_reconciliation_observations ORDER BY event_kind"))).all()
                assert rows == [("synthetic", env.info.workflow_run_id, 7, kind) for kind in ("started", "succeeded")]
                assert all(row[1] != payload["run_id"] for row in rows)
            base_factory = observation.create_sessionmaker

            def uncertain_factory(engine):
                factory = base_factory(engine)
                def create():
                    db = factory()
                    commit = db.commit
                    async def uncertain_commit():
                        await commit()
                        raise OSError("private-commit-reply-lost")
                    db.commit = uncertain_commit
                    return db
                return create

            with monkeypatch.context() as patch:
                patch.setattr(observation, "create_sessionmaker", uncertain_factory)
                assert not await observation.record_reconciliation_observation(reconciliation_attempt(), "failed")
            async with engine.connect() as conn:
                assert (await conn.execute(text("SELECT count(*) FROM billing_reconciliation_observations"))).scalar_one() == 3

            # The guard rejects the actual privileged login even with correct context.
            async with engine.begin() as conn:
                await conn.execute(text("ALTER ROLE twobrain_rec_maintenance BYPASSRLS"))
            try:
                assert not await observation.record_reconciliation_observation(reconciliation_attempt(), "started")
            finally:
                async with engine.begin() as conn:
                    await conn.execute(text("ALTER ROLE twobrain_rec_maintenance NOBYPASSRLS"))

            real_create = observation.create_async_engine
            def rls_off_engine(url, **kwargs):
                kwargs["connect_args"]["server_settings"]["row_security"] = "off"
                return real_create(url, **kwargs)
            with monkeypatch.context() as patch:
                patch.setattr(observation, "create_async_engine", rls_off_engine)
                assert not await observation.record_reconciliation_observation(reconciliation_attempt(), "started")
            async with engine.connect() as conn:
                assert (await conn.execute(text("SELECT count(*) FROM billing_reconciliation_observations"))).scalar_one() == 3
        finally:
            await engine.dispose()
    asyncio.run(probe())
    assert "private-commit" not in caplog.text and "postgresql" not in caplog.text


@pytest.fixture
def database(registry_database):  # noqa: F811 — imported pytest fixture
    async def setup():
        engine = create_async_engine(registry_database)
        try:
            async with engine.begin() as conn:
                names = ",".join(model.__tablename__ for model in TABLES)
                for role in ("twobrain_rec_app", "twobrain_rec_maintenance", "registry_worker"):
                    await conn.execute(text(f"GRANT SELECT,INSERT,UPDATE,DELETE ON {names} TO {role}"))
                # Roles are created by registry_database after migrations; grant
                # the same two privileges as0109, without any history mutation.
                await conn.execute(text("GRANT SELECT,INSERT ON billing_reconciliation_observations TO twobrain_rec_maintenance"))
                await conn.execute(text("GRANT SELECT ON billing_receipt_observation_deltas TO twobrain_rec_maintenance"))
                for model in (*TABLES, *STORAGE_TABLES):
                    flags = (await conn.execute(text(
                        "select relrowsecurity, relforcerowsecurity from pg_class where relname=:table"
                    ), {"table": model.__tablename__})).one()
                    assert flags == (True, True)
                # The migrated fair-use policy contains an owner_scope subquery.
                # Runtime bootstrap already grants this SELECT; keep its RLS intact.
                await conn.execute(text("GRANT SELECT ON workspaces TO twobrain_rec_maintenance"))
                storage_names = ",".join(model.__tablename__ for model in STORAGE_TABLES)
                await conn.execute(text(f"GRANT SELECT ON {storage_names} TO twobrain_rec_maintenance"))
        finally:
            await engine.dispose()
    asyncio.run(setup())
    return registry_database


def invoke(url, role="twobrain_rec_maintenance"):
    return asyncio.run(cli.run(ARGS, settings=settings(url, role)))


def process(url, role="twobrain_rec_maintenance", *, day=DAY):
    env = {**os.environ, "TWOBRAIN_DATABASE_URL": settings(url, role).database_url,
           "TWOBRAIN_BILLING_YOOKASSA_SHOP_ID": "123",
           "TWOBRAIN_BILLING_YOOKASSA_ENVIRONMENT": "test"}
    result = subprocess.run([sys.executable, "-m", cli.__name__, "--date", str(day)],
                            env=env, capture_output=True, text=True, timeout=20)
    assert result.stderr == ""
    return json.loads(result.stdout), result.returncode


async def fingerprint(url):
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            return [(await conn.execute(text(
                f"select coalesce(jsonb_agg(to_jsonb(t) order by "
                f"{'workspace_id' if model is WorkspaceSubscription else 'id'})::text, '[]') from {model.__tablename__} t"
            ))).scalar_one() for model in (*TABLES, *STORAGE_TABLES)]
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
            return workspace
    finally:
        await engine.dispose()


def test_empty_then_populated_cli_restart_privacy_and_no_writes(database):
    empty, code = process(database)
    assert code == 0 and empty["coverage"] == "partial"
    families = empty["families"]
    assert len(families) == 12
    assert families["payment_state"]["values"]["operations"]["count"] == 0
    assert families["storage"]["values"]["workspace_count"] == 0
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


def test_free_projection_boundaries_pairs_priorities_and_restart(database, monkeypatch):
    workspace = asyncio.run(seed(database))
    audit = BillingAuditEvent.__table__
    start = datetime(2026, 10, 30, 21, tzinfo=UTC)
    end = start + timedelta(days=1)
    as_of = start + timedelta(hours=12)
    microsecond = timedelta(microseconds=1)
    rows = [
        {"created_at": start - microsecond},
        {"created_at": start, "outcome": "blocked", "reason_code": "workspace_scope_invalid"},
        {"created_at": start + timedelta(seconds=1), "reason_code": "renewal_not_confirmed"},
        {"created_at": as_of - microsecond},
        {"created_at": start + timedelta(seconds=2), "outcome": "blocked"},
        {"created_at": start + timedelta(seconds=3), "reason_code": None},
        {"created_at": start + timedelta(seconds=4), "target_kind": "private-target"},
        {"created_at": start + timedelta(seconds=5), "outcome": "private-outcome", "reason_code": "private-reason"},
        {"created_at": as_of}, {"created_at": as_of + microsecond},
        {"created_at": end - microsecond}, {"created_at": end},
        {"created_at": None},
        {"created_at": None, "action": "renewal.private-other-action"},
    ]

    async def change(statement):
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                await conn.execute(statement)
        finally:
            await engine.dispose()

    asyncio.run(change(insert(audit).values([{
        "workspace_id": workspace, "action": "renewal.cutoff_projected_free",
        "target_kind": "workspace_subscription", "outcome": "projected", "reason_code": "unknown_pending",
        "target_ref": "private-target-ref", "metadata_json": {"secret": "private-audit-json"}, **row,
    } for row in rows])))
    before = asyncio.run(fingerprint(database))
    clock = [as_of]

    class Clock:
        @staticmethod
        def now(tz):
            return clock[0]

    actual_engine = cli.create_async_engine
    sql = []

    def instrument(*args, **kwargs):
        engine = actual_engine(*args, **kwargs)

        @event.listens_for(engine.sync_engine, "before_cursor_execute")
        def record(conn, cursor, statement, parameters, context, executemany):
            if "billing_audit_events" in statement:
                sql.append(statement)
        return engine

    def no_http(*args, **kwargs):
        raise AssertionError("unexpected HTTP")

    with monkeypatch.context() as scoped:
        scoped.setattr(cli, "datetime", Clock)
        scoped.setattr(cli, "create_async_engine", instrument)
        scoped.setattr(httpx.Client, "request", no_http)
        scoped.setattr(httpx.AsyncClient, "request", no_http)

        def observe(reason, count, coverage="partial"):
            result, code = invoke(database)
            assert code == 0
            family = result["families"]["free_projection"]
            assert family["source"] == "billing_audit_events" and family["kind"] == "event_window"
            assert family["scope"] == "database_inventory" and family["coverage"] == coverage
            assert family["reason_code"] == reason
            assert family["values"]["count"] == count == sum(g["count"] for g in family["values"]["groups"])
            assert "private-" not in json.dumps(result)
            return family

        family = observe("unrecognized", 7)
        assert family["values"]["undated_count"] == 1
        assert family["values"]["undated_count_scope"] == "database_inventory"
        assert family["values"]["at_or_after_as_of_count"] == 3
        assert {(g["outcome"], g["reason_code"], g["count"]) for g in family["values"]["groups"]} == {
            ("blocked", "workspace_scope_invalid", 1), ("projected", "unknown_pending", 1),
            ("projected", "renewal_not_confirmed", 1), ("unrecognized", "unrecognized", 4),
        }
        assert family["window"] == {"timezone": "Europe/Moscow", "start": start.isoformat(),
                                    "end": end.isoformat(), "observed_until": as_of.isoformat(),
                                    "calendar_day_elapsed": False}
        assert asyncio.run(fingerprint(database)) == before
        for _ in range(2):
            restarted, code = process(database)
            assert code == 0 and restarted["families"]["free_projection"]["values"]["count"] == 10
            assert "private-" not in json.dumps(restarted)
        assert asyncio.run(fingerprint(database)) == before
        for statement in sql:
            assert all(name not in statement for name in ("metadata_json", "target_ref", "workspace_id", "actor_user_id"))
        assert len(sql) == 2

        asyncio.run(change(delete(audit).where(
            audit.c.created_at >= start + timedelta(seconds=2), audit.c.created_at <= start + timedelta(seconds=5))))
        observe("undated_time", 3)
        asyncio.run(change(delete(audit).where(audit.c.created_at.is_(None))))
        observe("at_or_after_as_of", 3)
        asyncio.run(change(delete(audit).where(audit.c.created_at >= as_of, audit.c.created_at < end)))
        observe("window_open", 3)
        clock[0] = start
        at_start = observe("at_or_after_as_of", 0)
        assert at_start["values"]["at_or_after_as_of_count"] == 3
        clock[0] = end
        closed = observe("observed", 3, "complete_declared_source")
        assert closed["window"]["calendar_day_elapsed"] is True
        assert closed["window"]["observed_until"] == end.isoformat()
        asyncio.run(change(delete(audit)))
        observe("empty", 0, "complete_declared_source")
        clock[0] = as_of
        observe("window_open", 0)


def test_free_projection_unavailable_and_schema_failure_are_safe(database):
    for day, reason in ((date.min, "calendar_boundary_unrepresentable"),
                        (date.max, "calendar_boundary_unrepresentable"),
                        (date.today() + timedelta(days=3), "window_not_started")):
        result, code = process(database, day=day)
        assert code == 0 and result["coverage"] == "partial"
        assert result["families"]["free_projection"]["reason_code"] == reason
        assert result["families"]["free_projection"]["values"] is None
        assert result["families"]["payment_state"]["values"]["operations"]["count"] == 0

    async def rename(source, target):
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                await conn.execute(text(f"alter table billing_audit_events rename column {source} to {target}"))
        finally:
            await engine.dispose()

    asyncio.run(rename("reason_code", "synthetic_missing_reason"))
    try:
        assert process(database) == (cli.failure("report_unavailable"), 1)
    finally:
        asyncio.run(rename("synthetic_missing_reason", "reason_code"))


def test_free_projection_late_commit_changes_new_snapshot_only(database):
    workspace = asyncio.run(seed(database))

    async def scenario():
        writer = create_async_engine(database)
        reader = create_async_engine(settings(database).database_url, execution_options={
            "isolation_level": "REPEATABLE READ", "postgresql_readonly": True,
        })
        factory = create_sessionmaker(reader)
        try:
            async with writer.connect() as conn:
                started = (await conn.execute(text("select transaction_timestamp()"))).scalar_one()
                day = started.astimezone(ZoneInfo("Europe/Moscow")).date()
                # A closed calendar day is a synthetic boundary; no system clock change.
                as_of = datetime.combine(day + timedelta(days=1), datetime.min.time(),
                                         ZoneInfo("Europe/Moscow")).astimezone(UTC) + timedelta(hours=1)
                scope = {"environment": "test", "shop_id": "123", "report_date": day}
                async with factory() as db:
                    db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                        operation_name="billing_reconciliation", actor_id="synthetic-operator",
                        reason_category="operator_diagnostics", feature_area="billing",
                    ))
                    old = await monitoring.collect_billing_report(db, scope=scope, as_of=as_of)
                    assert old["families"]["free_projection"]["values"]["count"] == 0
                    recorded = (await conn.execute(insert(BillingAuditEvent).values(
                        workspace_id=workspace, action="renewal.cutoff_projected_free",
                        target_kind="workspace_subscription", outcome="projected", reason_code="unknown_pending",
                    ).returning(BillingAuditEvent.created_at))).scalar_one()
                    assert recorded == started  # PostgreSQL default now(), not Python's wall clock.
                    await conn.commit()
                    committed_after = (await conn.execute(text("select clock_timestamp()"))).scalar_one()
                    assert committed_after > recorded
                    unchanged = await monitoring.collect_billing_report(db, scope=scope, as_of=as_of)
                    assert unchanged["families"]["free_projection"] == old["families"]["free_projection"]
                async with factory() as db:
                    db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                        operation_name="billing_reconciliation", actor_id="synthetic-operator",
                        reason_category="operator_diagnostics", feature_area="billing",
                    ))
                    new = await monitoring.collect_billing_report(db, scope=scope, as_of=as_of)
                    family = new["families"]["free_projection"]
                    assert family["values"]["count"] == 1 and family["reason_code"] == "observed"
                    assert family["window"]["calendar_day_elapsed"] is True
            restarted, code = await asyncio.to_thread(process, database, day=day)
            assert code == 0 and restarted["families"]["free_projection"]["values"]["count"] == 1
        finally:
            await writer.dispose()
            await reader.dispose()

    asyncio.run(scenario())


def test_credit_ledger_boundaries_states_priorities_and_privacy(database, monkeypatch):
    workspace = asyncio.run(seed(database))
    now = datetime(2026, 11, 1, tzinfo=UTC)
    us = timedelta(microseconds=1)
    day = timedelta(days=1)
    table = TimeCreditLedgerEntry.__table__
    schedules = [
        ("pending", now - timedelta(seconds=120.9), now + us),
        ("available", now, now + day),
        ("pending", now + us, now + 2 * us),
        ("available", now + day, now + 2 * day),
        ("pending", now - 2 * day, now - us),
        ("available", now - day, now),
        ("pending", now, now),
        ("available", now, now - us),
        ("pending", now - us, now + us),
        *[(state, now, now) for state in ("applied", "expired", "rejected", "reversed", "matured", "private-state")],
    ]

    async def change(statement):
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                await conn.execute(statement)
        finally:
            await engine.dispose()

    asyncio.run(change(insert(table).values([{
        "id": uuid4(), "workspace_id": workspace, "source_ref": f"private-credit-{index}",
        "days": -987654321 if state == "reversed" else 987654321,
        "capacity_snapshot_bytes": 987654321, "state": state, "maturity_at": maturity,
        "expires_at": expiry, "applied_start": now - day, "applied_end": now + day,
    } for index, (state, maturity, expiry) in enumerate(schedules)])))
    before = asyncio.run(fingerprint(database))
    actual_engine = cli.create_async_engine
    sql = []

    def instrument(*args, **kwargs):
        engine = actual_engine(*args, **kwargs)

        @event.listens_for(engine.sync_engine, "before_cursor_execute")
        def record(conn, cursor, statement, parameters, context, executemany):
            if "time_credit_ledger_entries" in statement:
                sql.append(statement)
        return engine

    class Clock:
        @staticmethod
        def now(tz):
            return now

    def no_http(*args, **kwargs):
        raise AssertionError("unexpected HTTP")

    with monkeypatch.context() as scoped:
        scoped.setattr(cli, "datetime", Clock)
        scoped.setattr(cli, "create_async_engine", instrument)
        scoped.setattr(httpx.Client, "request", no_http)
        scoped.setattr(httpx.AsyncClient, "request", no_http)
        result, code = invoke(database)
        assert code == 0 and result["as_of"] == now.isoformat()
        family = result["families"]["addon_and_time_credit"]
        assert family["source"] == "time_credit_ledger_entries"
        assert family["scope"] == "database_inventory" and family["kind"] == "current_state"
        assert family["coverage"] == "partial" and family["reason_code"] == "unrecognized"
        values = family["values"]
        assert values["count"] == 15 == sum(group["count"] for group in values["groups"])
        assert values["groups"] == [{"state": state, "count": count} for state, count in (
            ("applied", 1), ("available", 4), ("expired", 1), ("pending", 5),
            ("rejected", 1), ("reversed", 1), ("unrecognized", 2),
        )]
        pending = values["pending_or_available"]
        assert pending == {"count": 9, "invalid_schedule_count": 2, "expiry_reached_count": 2,
                           "maturity_reached_unexpired_count": 3, "waiting_count": 2,
                           "oldest_maturity_reached_age_seconds": 120}
        assert pending["count"] == sum(pending[key] for key in (
            "invalid_schedule_count", "expiry_reached_count", "maturity_reached_unexpired_count", "waiting_count"))
        for key in ("addon_jobs", "job_attempts", "job_errors", "job_retries"):
            assert values[key] is None
        assert len(sql) == 1
        for private in ("days", "source_ref", ".id", "workspace_id", "referral_attribution_id",
                        "capacity_snapshot_bytes", "applied_start", "applied_end", "reversal_of_id"):
            assert private not in sql[0]
        assert "private-" not in json.dumps(result) and "987654321" not in json.dumps(result)
        assert asyncio.run(fingerprint(database)) == before
        for report_day in (DAY, date(1999, 1, 1)):
            restarted, code = process(database, day=report_day)
            assert code == 0
            assert restarted["families"]["addon_and_time_credit"]["values"]["groups"] == values["groups"]
            assert "private-" not in json.dumps(restarted) and "987654321" not in json.dumps(restarted)
        assert asyncio.run(fingerprint(database)) == before
        asyncio.run(change(delete(table).where(table.c.state.in_(("matured", "private-state")))))
        assert invoke(database)[0]["families"]["addon_and_time_credit"]["reason_code"] == "invalid_schedule"
        asyncio.run(change(delete(table).where(table.c.state.in_(("pending", "available")),
                                              table.c.expires_at <= table.c.maturity_at)))
        valid = invoke(database)[0]["families"]["addon_and_time_credit"]
        assert valid["coverage"] == "partial" and valid["reason_code"] == "jobs_uninstrumented"
        assert valid["values"]["pending_or_available"]["count"] == 7


def test_credit_ledger_empty_notnull_and_schema_failure(database):
    result, code = process(database)
    assert code == 0
    family = result["families"]["addon_and_time_credit"]
    assert family["source"] == "time_credit_ledger_entries"
    assert family["coverage"] == "partial" and family["reason_code"] == "jobs_uninstrumented"
    values = family["values"]
    assert values["count"] == 0 and values["groups"] == []
    assert values["pending_or_available"] == {
        "count": 0, "invalid_schedule_count": 0, "expiry_reached_count": 0,
        "maturity_reached_unexpired_count": 0, "waiting_count": 0,
        "oldest_maturity_reached_age_seconds": None,
    }
    workspace = asyncio.run(seed(database))

    async def schema():
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                for column in ("state", "maturity_at", "expires_at"):
                    row = {"workspace_id": workspace, "source_ref": "private-null", "days": 7,
                           "state": "pending", "maturity_at": datetime(2026, 11, 1, tzinfo=UTC),
                           "expires_at": datetime(2027, 11, 1, tzinfo=UTC), column: None}
                    with pytest.raises(IntegrityError):
                        async with conn.begin_nested():
                            await conn.execute(insert(TimeCreditLedgerEntry).values(**row))
                await conn.execute(text("alter table time_credit_ledger_entries rename column maturity_at to synthetic_missing_maturity"))
            try:
                assert await asyncio.to_thread(process, database) == (cli.failure("report_unavailable"), 1)
            finally:
                async with engine.begin() as conn:
                    await conn.execute(text("alter table time_credit_ledger_entries rename column synthetic_missing_maturity to maturity_at"))
        finally:
            await engine.dispose()
    asyncio.run(schema())
    assert process(database)[0]["families"]["addon_and_time_credit"]["values"]["count"] == 0


def test_credit_ledger_repeatable_snapshot_and_new_process(database):
    workspace = asyncio.run(seed(database))
    as_of = datetime(2026, 11, 1, tzinfo=UTC)

    async def scenario():
        writer = create_async_engine(database)
        reader = create_async_engine(settings(database).database_url, execution_options={
            "isolation_level": "REPEATABLE READ", "postgresql_readonly": True,
        })
        factory = create_sessionmaker(reader)
        scope = {"environment": "test", "shop_id": "123", "report_date": DAY}

        def session():
            db = factory()
            db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                operation_name="billing_reconciliation", actor_id="synthetic-operator",
                reason_category="operator_diagnostics", feature_area="billing",
            ))
            return db
        try:
            async with session() as db:
                old = await monitoring.collect_billing_report(db, scope=scope, as_of=as_of)
                assert old["families"]["addon_and_time_credit"]["values"]["count"] == 0
                async with writer.begin() as conn:
                    await conn.execute(insert(TimeCreditLedgerEntry).values(
                        workspace_id=workspace, source_ref="private-new-credit", days=7, state="pending",
                        maturity_at=as_of, expires_at=as_of + timedelta(days=365),
                    ))
                unchanged = await monitoring.collect_billing_report(db, scope=scope, as_of=as_of)
                assert unchanged["families"]["addon_and_time_credit"] == old["families"]["addon_and_time_credit"]
            async with session() as db:
                new = await monitoring.collect_billing_report(db, scope=scope, as_of=as_of)
                pending = new["families"]["addon_and_time_credit"]["values"]["pending_or_available"]
                assert pending["count"] == pending["maturity_reached_unexpired_count"] == 1
                assert pending["oldest_maturity_reached_age_seconds"] == 0
        finally:
            await reader.dispose()
            await writer.dispose()
    asyncio.run(scenario())
    restarted, code = process(database)
    assert code == 0 and restarted["families"]["addon_and_time_credit"]["values"]["count"] == 1


def test_refund_inventory_empty_notnull_and_schema_failure(database):
    result, code = process(database)
    assert code == 0
    family = result["families"]["refunds_and_receipts"]
    assert family["source"] == "observed_provider_refunds,billing_invoices.plan_snapshot.receipt_observations"
    assert family["scope"] == "database_inventory" and family["kind"] == "current_state"
    assert family["coverage"] == "partial" and family["reason_code"] == "reconciliation_uninstrumented"
    assert family["values"]["count"] == 0 and family["values"]["groups"] == []
    assert family["values"]["reconciliation_gaps"] is None
    assert family["values"]["receipts"]["values"]["invoice_count"] == 0
    workspace = asyncio.run(seed(database))

    async def schema():
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                invoice = (await conn.execute(text("select id from billing_invoices"))).scalar_one()
                for column in ("status", "source"):
                    row = {"workspace_id": workspace, "invoice_id": invoice, "shop_environment": "test",
                           "provider_refund_id": "private-null", "amount_minor": 1, "currency": "RUB",
                           "status": "succeeded", "source": "provider_observation", column: None}
                    with pytest.raises(IntegrityError):
                        async with conn.begin_nested():
                            await conn.execute(insert(ObservedProviderRefund).values(**row))
                await conn.execute(text("alter table observed_provider_refunds rename column source to synthetic_missing_source"))
            try:
                assert await asyncio.to_thread(process, database) == (cli.failure("report_unavailable"), 1)
            finally:
                async with engine.begin() as conn:
                    await conn.execute(text("alter table observed_provider_refunds rename column synthetic_missing_source to source"))
        finally:
            await engine.dispose()
    asyncio.run(schema())
    assert process(database)[0]["families"]["refunds_and_receipts"]["values"]["count"] == 0


def test_refund_inventory_pairs_time_privacy_and_restart(database, monkeypatch):
    workspace = asyncio.run(seed(database))
    table = ObservedProviderRefund.__table__
    now = datetime(2026, 11, 1, tzinfo=UTC)
    samples = [
        ("succeeded", "provider_observation", "test", None),
        ("succeeded", "provider_observation", "production", now + timedelta(days=365)),
        ("succeeded", "provider_observation", "test", now - timedelta(days=365)),
        ("canceled", "provider_observation", "test", now),
        ("succeeded", "webhook", "test", now),
        ("private-status", "private-source", "private-env", now),
    ]

    async def populate():
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                invoice = (await conn.execute(text("select id from billing_invoices"))).scalar_one()
                await conn.execute(insert(table).values([{
                    "id": uuid4(), "workspace_id": workspace, "invoice_id": invoice,
                    "shop_environment": environment, "provider_refund_id": f"private-refund-{index}",
                    "amount_minor": 98765432, "currency": "RUB", "status": status,
                    "source": source, "observed_at": observed,
                } for index, (status, source, environment, observed) in enumerate(samples)]))
        finally:
            await engine.dispose()
    asyncio.run(populate())
    before = asyncio.run(fingerprint(database))
    actual = cli.create_async_engine
    sql = []

    def instrument(*args, **kwargs):
        engine = actual(*args, **kwargs)

        @event.listens_for(engine.sync_engine, "before_cursor_execute")
        def record(conn, cursor, statement, parameters, context, executemany):
            if "observed_provider_refunds" in statement:
                sql.append(statement)
        return engine

    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected financial writer or HTTP")

    from twobrain_rec_server.billing import reconciliation
    with monkeypatch.context() as scoped:
        scoped.setattr(cli, "create_async_engine", instrument)
        scoped.setattr(httpx.Client, "request", forbidden)
        scoped.setattr(httpx.AsyncClient, "request", forbidden)
        scoped.setattr(reconciliation, "record_observed_refund", forbidden)
        scoped.setattr(reconciliation, "reverse_credit_for_payment", forbidden)
        result, code = invoke(database)
    assert code == 0
    family = result["families"]["refunds_and_receipts"]
    assert family["source"] == "observed_provider_refunds,billing_invoices.plan_snapshot.receipt_observations"
    assert family["coverage"] == "partial" and family["reason_code"] == "unrecognized"
    assert family["values"]["count"] == 6
    assert family["values"]["groups"] == [{"status": "succeeded", "count": 3}, {"status": "unrecognized", "count": 3}]
    assert family["values"]["receipts"]["reason_code"] == "missing_observations"
    assert family["values"]["receipts"]["values"]["missing_map_count"] == 1
    assert family["values"]["reconciliation_gaps"] is None
    assert len(sql) == 1
    for private in (".id", "workspace_id", "invoice_id", "provider_refund_id", "amount_minor",
                    "currency", "shop_environment", "observed_at", "plan_snapshot"):
        assert private not in sql[0]
    for day in (DAY, date(1999, 1, 1), date(2099, 1, 1)):
        restarted, code = process(database, day=day)
        assert code == 0 and restarted["families"]["refunds_and_receipts"] == family
        assert "private-" not in json.dumps(restarted) and "98765432" not in json.dumps(restarted)
    assert asyncio.run(fingerprint(database)) == before


def test_refund_inventory_repeatable_snapshot_and_new_process(database):
    workspace = asyncio.run(seed(database))
    as_of = datetime(2026, 11, 1, tzinfo=UTC)

    async def scenario():
        writer = create_async_engine(database)
        reader = create_async_engine(settings(database).database_url, execution_options={
            "isolation_level": "REPEATABLE READ", "postgresql_readonly": True,
        })
        factory = create_sessionmaker(reader)
        scope = {"environment": "test", "shop_id": "123", "report_date": DAY}

        def session():
            db = factory()
            db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                operation_name="billing_reconciliation", actor_id="synthetic-operator",
                reason_category="operator_diagnostics", feature_area="billing",
            ))
            return db
        try:
            async with session() as db:
                old = await monitoring.collect_billing_report(db, scope=scope, as_of=as_of)
                assert old["families"]["refunds_and_receipts"]["values"]["count"] == 0
                async with writer.begin() as conn:
                    invoice = (await conn.execute(text("select id from billing_invoices"))).scalar_one()
                    await conn.execute(insert(ObservedProviderRefund).values(
                        workspace_id=workspace, invoice_id=invoice, shop_environment="production",
                        provider_refund_id="private-new-refund", amount_minor=1, currency="RUB",
                        source="provider_observation", status="succeeded", observed_at=None,
                    ))
                unchanged = await monitoring.collect_billing_report(db, scope=scope, as_of=as_of)
                assert unchanged["families"]["refunds_and_receipts"] == old["families"]["refunds_and_receipts"]
            async with session() as db:
                new = await monitoring.collect_billing_report(db, scope=scope, as_of=as_of)
                values = new["families"]["refunds_and_receipts"]["values"]
                assert values["count"] == 1 and values["groups"] == [{"status": "succeeded", "count": 1}]
        finally:
            await reader.dispose()
            await writer.dispose()
    asyncio.run(scenario())
    restarted, code = process(database)
    assert code == 0 and restarted["families"]["refunds_and_receipts"]["values"]["count"] == 1


def test_receipt_inventory_empty_notnull_and_schema_failure(database):
    report, code = process(database)
    assert code == 0
    family = report["families"]["refunds_and_receipts"]
    assert family["source"] == "observed_provider_refunds,billing_invoices.plan_snapshot.receipt_observations"
    assert family["reason_code"] == "reconciliation_uninstrumented"
    assert family["values"]["receipts"] == {
        "source": "billing_invoices.plan_snapshot.receipt_observations", "scope": "database_inventory",
        "kind": "current_state", "coverage": "partial",
        "reason_code": "timing_and_reconciliation_uninstrumented", "values": {
            "invoice_count": 0, "missing_map_count": 0, "invalid_container_count": 0,
            "count": 0, "groups": [], "pending_age_seconds": None, "escalation_due": None,
        },
    }
    asyncio.run(seed(database))

    async def schema():
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                with pytest.raises(IntegrityError):
                    async with conn.begin_nested():
                        await conn.execute(text("update billing_invoices set plan_snapshot=NULL"))
                await conn.execute(text("alter table billing_invoices rename column plan_snapshot to synthetic_missing_snapshot"))
            try:
                assert await asyncio.to_thread(process, database) == (cli.failure("report_unavailable"), 1)
            finally:
                async with engine.begin() as conn:
                    await conn.execute(text("alter table billing_invoices rename column synthetic_missing_snapshot to plan_snapshot"))
        finally:
            await engine.dispose()
    asyncio.run(schema())
    assert process(database)[1] == 0


def test_receipt_inventory_all_pairs_containers_privacy_and_priorities(database, monkeypatch):
    workspace = asyncio.run(seed(database))
    expected = [{"parent_kind": parent, "status": status, "source": source, "count": 1}
                for parent in ("payment", "refund") for status in ("canceled", "pending", "succeeded")
                for source in ("poll", "registry", "webhook")]
    valid = {"parent_kind": "payment", "status": "pending", "source": "poll"}
    malformed = [None, [], "private-entry", 123, True, {}]
    for field in valid:
        malformed.append({key: value for key, value in valid.items() if key != field})
        malformed.extend({**valid, field: value} for value in (None, 123, [], {}, "private-component"))
    samples = [None, [], 123, "private-root", True,
               *[{"receipt_observations": value} for value in ([], 123, "private-map", True)],
               {}, {"receipt_registration": "succeeded"}, {"receipt_observations": None},
               {"receipt_observations": {}},
               *[{"receipt_observations": {f"private-key-{i}": {**group,
                   "provider_receipt_id": "private-id", "environment": "private-env", "shop_id": "private-shop",
                   "observed_at": "2999-01-01", "registered_at": "1900-01-01",
                   "receipt_url": "private-url", "contact": "private-contact", "amount": 987654321,
               } for i, group in enumerate(expected[start:start + 9])}} for start in (0, 9)],
               {"receipt_observations": {f"private-malformed-{i}": value for i, value in enumerate(malformed)}}]

    async def populate():
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                await conn.execute(delete(BillingInvoice))
                for snapshot in samples:
                    operation = (await conn.execute(insert(BillingOperation).values(
                        workspace_id=workspace, kind="renewal", state="unknown", idempotency_key=str(uuid4()),
                    ).returning(BillingOperation.id))).scalar_one()
                    await conn.execute(insert(BillingInvoice).values(
                        workspace_id=workspace, operation_id=operation, safe_number=str(uuid4()),
                        amount_minor=987654321, status="canceled", plan_snapshot=snapshot,
                        created_at=datetime(2999, 1, 1, tzinfo=UTC),
                    ))
        finally:
            await engine.dispose()
    asyncio.run(populate())
    before = asyncio.run(fingerprint(database))
    actual = cli.create_async_engine
    selected = []

    def instrument(*args, **kwargs):
        engine = actual(*args, **kwargs)

        @event.listens_for(engine.sync_engine, "before_cursor_execute")
        def record(conn, cursor, statement, parameters, context, executemany):
            if "json_typeof" in statement:
                selected.append(statement)
        return engine

    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected receipt writer or HTTP")

    from twobrain_rec_server.auth.email_delivery import PostalEmailLoginClient
    from twobrain_rec_server.billing import reconciliation
    with monkeypatch.context() as scoped:
        scoped.setattr(cli, "create_async_engine", instrument)
        scoped.setattr(httpx.Client, "request", forbidden)
        scoped.setattr(httpx.AsyncClient, "request", forbidden)
        scoped.setattr(reconciliation, "record_observed_receipt", forbidden)
        scoped.setattr(reconciliation, "merge_receipt_observation_snapshot", forbidden)
        scoped.setattr(PostalEmailLoginClient, "_post_message", forbidden)
        report, code = invoke(database)
    assert code == 0
    family = report["families"]["refunds_and_receipts"]
    receipt = family["values"]["receipts"]
    assert receipt["coverage"] == "partial" and receipt["reason_code"] == family["reason_code"] == "unrecognized"
    assert receipt["values"] == {
        "invoice_count": len(samples), "missing_map_count": 3, "invalid_container_count": 9,
        "count": 18 + len(malformed), "groups": expected + [{
            "parent_kind": "unrecognized", "status": "unrecognized", "source": "unrecognized", "count": len(malformed),
        }], "pending_age_seconds": None, "escalation_due": None,
    }
    assert family["values"]["count"] == 0 and family["values"]["reconciliation_gaps"] is None
    assert len(selected) == 2
    for sql in selected:
        for private in (".id", "workspace_id", "operation_id", "amount_minor", "created_at", "observed_at",
                        "registered_at", "provider_receipt_id", "shop_id", "environment", "receipt_url", "contact"):
            assert private not in sql
    for day in (DAY, date(1999, 1, 1), date(2099, 1, 1)):
        restarted, code = process(database, day=day)
        assert code == 0 and restarted["families"]["refunds_and_receipts"] == family
        assert "private-" not in json.dumps(restarted) and "987654321" not in json.dumps(restarted)
    assert asyncio.run(fingerprint(database)) == before

    async def priorities():
        engine = create_async_engine(database)
        try:
            for snapshot, reason in (([], "invalid_container"), ({"receipt_registration": "succeeded"}, "missing_observations"),
                                     ({"receipt_observations": {}}, "reconciliation_uninstrumented")):
                async with engine.begin() as conn:
                    await conn.execute(text("update billing_invoices set plan_snapshot=cast(:snapshot as json)"),
                                       {"snapshot": json.dumps(snapshot)})
                current, code = await asyncio.to_thread(process, database)
                assert code == 0 and current["families"]["refunds_and_receipts"]["reason_code"] == reason
        finally:
            await engine.dispose()
    asyncio.run(priorities())


def test_receipt_inventory_sql_null_and_duplicate_keys_defense(database, monkeypatch):
    async def scenario():
        engine = create_async_engine(database)
        raw = '{"receipt_observations":{"duplicate":{"parent_kind":"refund","status":"pending","source":"registry"},"duplicate":{"parent_kind":"refund","status":"pending","source":"registry"}}}'
        # Preserve duplicate JSON keys in a literal SQL JSON row, unlike Python dict parsing.
        synthetic = text("select null::json as plan_snapshot union all select cast(:raw as json)").bindparams(raw=raw).columns(plan_snapshot=JSON).subquery()
        with monkeypatch.context() as scoped:
            scoped.setattr(monitoring, "BillingInvoice", SimpleNamespace(__table__=synthetic))
            try:
                async with AsyncSession(engine) as db:
                    result = await monitoring._receipt_inventory(db)
            finally:
                await engine.dispose()
        values_ = result["values"]
        assert result["reason_code"] == "invalid_container"
        assert values_["invoice_count"] == 2 and values_["invalid_container_count"] == 1
        assert values_["missing_map_count"] == 0 and values_["count"] == 2
        assert values_["groups"] == [{"parent_kind": "refund", "status": "pending", "source": "registry", "count": 2}]
    asyncio.run(scenario())


def test_receipt_inventory_repeatable_snapshot_and_new_process(database):
    asyncio.run(seed(database))
    as_of = datetime(2026, 11, 1, tzinfo=UTC)

    async def scenario():
        writer = create_async_engine(database)
        reader = create_async_engine(settings(database).database_url, execution_options={
            "isolation_level": "REPEATABLE READ", "postgresql_readonly": True,
        })
        factory = create_sessionmaker(reader)
        scope = {"environment": "test", "shop_id": "123", "report_date": DAY}

        def session():
            db = factory()
            db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                operation_name="billing_reconciliation", actor_id="synthetic-operator",
                reason_category="operator_diagnostics", feature_area="billing",
            ))
            return db
        try:
            async with session() as db:
                old = await monitoring.collect_billing_report(db, scope=scope, as_of=as_of)
                assert old["families"]["refunds_and_receipts"]["values"]["receipts"]["values"]["count"] == 0
                async with writer.begin() as conn:
                    await conn.execute(text("update billing_invoices set plan_snapshot=cast(:snapshot as json)"), {
                        "snapshot": json.dumps({"receipt_observations": {"private-key": {
                            "parent_kind": "refund", "status": "canceled", "source": "webhook",
                        }}}),
                    })
                unchanged = await monitoring.collect_billing_report(db, scope=scope, as_of=as_of)
                assert unchanged["families"]["refunds_and_receipts"] == old["families"]["refunds_and_receipts"]
            async with session() as db:
                new = await monitoring.collect_billing_report(db, scope=scope, as_of=as_of)
                assert new["families"]["refunds_and_receipts"]["values"]["receipts"]["values"]["count"] == 1
        finally:
            await reader.dispose()
            await writer.dispose()
    asyncio.run(scenario())
    restarted, code = process(database)
    assert code == 0 and restarted["families"]["refunds_and_receipts"]["values"]["receipts"]["values"]["count"] == 1


def test_fair_use_inventory_empty_constraints_and_schema_failure(database):
    result, code = process(database)
    assert code == 0
    assert result["families"]["deletion_and_fair_use"] == {
        "source": "fair_use_reviews,meeting_deletion_requests", "scope": "database_inventory", "kind": "current_state",
        "coverage": "partial", "reason_code": "deletion_details_and_reaction_uninstrumented",
        "values": {"count": 0, "groups": [], "pending_review": {
            "count": 0, "invalid_schedule_count": 0, "not_started_count": 0,
            "deadline_reached_count": 0, "waiting_count": 0,
        }, "deletion": {"source": "meeting_deletion_requests", "scope": "database_inventory",
                        "kind": "current_state", "coverage": "partial",
                        "reason_code": "artifact_and_deadline_uninstrumented", "values": {
                            "count": 0, "groups": [], "artifact_completion": None, "deadline_status": None,
                            "job_attempts": None, "job_errors": None, "job_retries": None}}, "reaction": None},
    }
    workspace = asyncio.run(seed(database))
    now = datetime(2026, 11, 1, tzinfo=UTC)

    async def schema():
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                subject = (await conn.execute(text("select owner_user_id from workspaces where id=:id"),
                                              {"id": workspace})).scalar_one()
                for bad in ({"state": None}, {"starts_at": None}, {"review_by": None},
                            {"state": "private-state"}, {"review_by": now - timedelta(microseconds=1)},
                            {"review_by": now + timedelta(days=1, microseconds=1)}):
                    row = {"workspace_id": workspace, "subject_user_id": subject,
                           "capability": "private-capability", "reason_code": "security_abuse",
                           "evidence_ref": "private-ref", "state": "notice", "starts_at": now,
                           "review_by": now + timedelta(days=1), **bad}
                    with pytest.raises(IntegrityError):
                        async with conn.begin_nested():
                            await conn.execute(insert(FairUseReviewRecord).values(**row))
                await conn.execute(text("alter table fair_use_reviews rename column review_by to synthetic_missing_deadline"))
            try:
                assert await asyncio.to_thread(process, database) == (cli.failure("report_unavailable"), 1)
            finally:
                async with engine.begin() as conn:
                    await conn.execute(text("alter table fair_use_reviews rename column synthetic_missing_deadline to review_by"))
        finally:
            await engine.dispose()
    asyncio.run(schema())
    assert process(database)[0]["families"]["deletion_and_fair_use"]["values"]["count"] == 0


def test_fair_use_inventory_boundaries_infinity_privacy_and_restart(database, monkeypatch):
    workspace = asyncio.run(seed(database))
    now = datetime(2026, 11, 1, tzinfo=UTC)
    us, day = timedelta(microseconds=1), timedelta(days=1)
    schedules = [
        ("notice", now - us, now + us), ("restricted", now, now),
        ("appealed", now - us, now - us), ("notice", now + us, now + day),
        ("restricted", now - day, now - us), ("appealed", now, now + us),
        ("notice", now, now + day), ("cleared", now, now + day),
        ("confirmed", now - day, now),
        ("notice", text("'infinity'::timestamptz"), text("'infinity'::timestamptz")),
        ("appealed", text("'-infinity'::timestamptz"), text("'-infinity'::timestamptz")),
    ]

    async def populate():
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                subject = (await conn.execute(text("select owner_user_id from workspaces where id=:id"),
                                              {"id": workspace})).scalar_one()
                await conn.execute(insert(FairUseReviewRecord).values([{
                    "id": uuid4(), "workspace_id": workspace, "subject_user_id": subject,
                    "capability": "private-capability", "reason_code": "security_abuse",
                    "evidence_ref": f"private-evidence-{i}", "appeal_ref": "private-appeal",
                    "resolution_code": "private-resolution", "state": state,
                    "starts_at": start, "review_by": deadline,
                } for i, (state, start, deadline) in enumerate(schedules)]))
        finally:
            await engine.dispose()
    asyncio.run(populate())
    before = asyncio.run(fingerprint(database))
    actual, sql = cli.create_async_engine, []

    def instrument(*args, **kwargs):
        engine = actual(*args, **kwargs)

        @event.listens_for(engine.sync_engine, "before_cursor_execute")
        def record(conn, cursor, statement, parameters, context, executemany):
            if "fair_use_reviews" in statement:
                sql.append(statement)
        return engine

    class Clock:
        @staticmethod
        def now(tz):
            return now

    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected writer or HTTP")

    from twobrain_rec_server.billing import fair_use
    with monkeypatch.context() as scoped:
        scoped.setattr(cli, "datetime", Clock)
        scoped.setattr(cli, "create_async_engine", instrument)
        scoped.setattr(httpx.Client, "request", forbidden)
        scoped.setattr(httpx.AsyncClient, "request", forbidden)
        for name in ("persist_review", "appeal_persisted_review", "resolve_review", "enqueue_review_notification"):
            scoped.setattr(fair_use, name, forbidden)
        result, code = invoke(database)
    assert code == 0 and result["as_of"] == now.isoformat()
    family = result["families"]["deletion_and_fair_use"]
    assert family["coverage"] == "partial" and family["reason_code"] == "invalid_schedule"
    counts = family["values"]
    assert counts["count"] == 11 == sum(group["count"] for group in counts["groups"])
    assert counts["groups"] == [{"state": state, "count": count} for state, count in (
        ("appealed", 3), ("cleared", 1), ("confirmed", 1), ("notice", 4), ("restricted", 2),
    )]
    assert counts["pending_review"] == {
        "count": 9, "invalid_schedule_count": 2, "not_started_count": 1,
        "deadline_reached_count": 3, "waiting_count": 3,
    }
    assert counts["deletion"]["values"]["count"] == 0 and counts["reaction"] is None
    assert len(sql) == 1
    for private in (".id", "workspace_id", "subject_user_id", "capability", "reason_code",
                    "evidence_ref", "appeal", "resolved_at", "resolution_code", "created_at", "updated_at"):
        assert private not in sql[0]
    assert "private-" not in json.dumps(result)
    for report_day in (DAY, date(1999, 1, 1), date(2099, 1, 1)):
        restarted, code = process(database, day=report_day)
        assert code == 0 and restarted["families"]["deletion_and_fair_use"]["values"]["groups"] == counts["groups"]
        assert "private-" not in json.dumps(restarted)
    assert asyncio.run(fingerprint(database)) == before


def test_fair_use_inventory_synthetic_defenses_and_dst(database, monkeypatch):
    now = datetime(2026, 11, 1, 12, tzinfo=UTC)
    us, day = timedelta(microseconds=1), timedelta(days=1)
    samples = [("notice", None, now), ("notice", now, None),
               ("restricted", now, now - us), ("appealed", now - day - us, now),
               ("notice", now - day, now), ("notice", now, now + day),
               ("private-state", None, None), (None, None, None), ("confirmed", None, None)]

    async def scenario():
        engine = create_async_engine(settings(database).database_url, execution_options={
            "isolation_level": "REPEATABLE READ", "postgresql_readonly": True,
        })
        try:
            async with AsyncSession(engine) as db:
                await db.execute(text("SET TIME ZONE 'America/New_York'"))
                for rows, reason, count, invalid in (
                    (samples, "unrecognized", 9, 4),
                    (samples[:6], "invalid_schedule", 6, 4),
                    (samples[4:6], "deletion_details_and_reaction_uninstrumented", 2, 0),
                ):
                    # Malformed rows stay in a VALUES source; migrated constraints are never weakened.
                    source = values(column("state", String), column("starts_at", DateTime(timezone=True)),
                                    column("review_by", DateTime(timezone=True))).data(rows).alias("synthetic_reviews")
                    monkeypatch.setattr(monitoring, "FairUseReviewRecord", SimpleNamespace(__table__=source))
                    family = await monitoring._fair_use_inventory(db, now)
                    assert family["coverage"] == "partial" and family["reason_code"] == reason
                    summary = family["values"]
                    assert summary["count"] == count == sum(group["count"] for group in summary["groups"])
                    assert summary["pending_review"] == {
                        "count": invalid + 2, "invalid_schedule_count": invalid,
                        "not_started_count": 0, "deadline_reached_count": 1, "waiting_count": 1,
                    }
                    assert "private-" not in json.dumps(family)
        finally:
            await engine.dispose()
    asyncio.run(scenario())


def test_fair_use_inventory_repeatable_snapshot_and_new_process(database):
    workspace = asyncio.run(seed(database))
    as_of = datetime(2026, 11, 1, tzinfo=UTC)

    async def scenario():
        writer = create_async_engine(database)
        reader = create_async_engine(settings(database).database_url, execution_options={
            "isolation_level": "REPEATABLE READ", "postgresql_readonly": True,
        })
        factory = create_sessionmaker(reader)
        scope = {"environment": "test", "shop_id": "123", "report_date": DAY}

        def session():
            db = factory()
            db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                operation_name="billing_reconciliation", actor_id="synthetic-operator",
                reason_category="operator_diagnostics", feature_area="billing",
            ))
            return db
        try:
            async with session() as db:
                old = await monitoring.collect_billing_report(db, scope=scope, as_of=as_of)
                assert old["families"]["deletion_and_fair_use"]["values"]["count"] == 0
                async with writer.begin() as conn:
                    subject = (await conn.execute(text("select owner_user_id from workspaces where id=:id"),
                                                  {"id": workspace})).scalar_one()
                    await conn.execute(insert(FairUseReviewRecord).values(
                        workspace_id=workspace, subject_user_id=subject, capability="private-capability",
                        reason_code="security_abuse", evidence_ref="private-new-review", state="notice",
                        starts_at=as_of, review_by=as_of,
                    ))
                unchanged = await monitoring.collect_billing_report(db, scope=scope, as_of=as_of)
                assert unchanged["families"]["deletion_and_fair_use"] == old["families"]["deletion_and_fair_use"]
            async with session() as db:
                new = await monitoring.collect_billing_report(db, scope=scope, as_of=as_of)
                pending = new["families"]["deletion_and_fair_use"]["values"]["pending_review"]
                assert pending["count"] == pending["deadline_reached_count"] == 1
        finally:
            await reader.dispose()
            await writer.dispose()
    asyncio.run(scenario())
    restarted, code = process(database)
    assert code == 0 and restarted["families"]["deletion_and_fair_use"]["values"]["count"] == 1


async def deletion_meeting(conn, workspace):
    subject = (await conn.execute(text("select owner_user_id from workspaces where id=:id"),
                                  {"id": workspace})).scalar_one()
    device, meeting = uuid4(), uuid4()
    await conn.execute(insert(RegisteredDevice).values(
        id=device, workspace_id=workspace, user_id=subject, device_public_id=f"private-device-{device}",
    ))
    await conn.execute(insert(Meeting).values(
        id=meeting, workspace_id=workspace, created_by_user_id=subject, device_id=device,
        local_recording_id=f"private-recording-{meeting}", title="private-meeting", duration_seconds=1,
    ))
    return {"workspace_id": workspace, "meeting_id": meeting, "requested_by_user_id": subject,
            "request_source": "private-source", "reason_code": "private-reason",
            "confirmation_boundary": "private-boundary", "failure_reason": "private-failure",
            "metadata_json": {"private-key": "private-value"}}


def test_deletion_inventory_empty_notnull_and_schema_failure(database):
    result, code = process(database)
    assert code == 0
    family = result["families"]["deletion_and_fair_use"]
    assert family["source"] == "fair_use_reviews,meeting_deletion_requests"
    assert family["coverage"] == "partial" and family["reason_code"] == "deletion_details_and_reaction_uninstrumented"
    assert family["values"]["deletion"] == {
        "source": "meeting_deletion_requests", "scope": "database_inventory", "kind": "current_state",
        "coverage": "partial", "reason_code": "artifact_and_deadline_uninstrumented",
        "values": {"count": 0, "groups": [], "artifact_completion": None, "deadline_status": None,
                   "job_attempts": None, "job_errors": None, "job_retries": None},
    }
    workspace = asyncio.run(seed(database))

    async def schema():
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                row = await deletion_meeting(conn, workspace)
                with pytest.raises(IntegrityError):
                    async with conn.begin_nested():
                        await conn.execute(insert(MeetingDeletionRequest).values(**row, state=None))
                # The actual migrated default is requested, independently of the ORM default.
                assert (await conn.execute(text(
                    "select column_default from information_schema.columns "
                    "where table_name='meeting_deletion_requests' and column_name='state'"
                ))).scalar_one() == "'requested'::character varying"
                await conn.execute(text("alter table meeting_deletion_requests rename column state to synthetic_missing_state"))
            try:
                assert await asyncio.to_thread(process, database) == (cli.failure("report_unavailable"), 1)
            finally:
                async with engine.begin() as conn:
                    await conn.execute(text("alter table meeting_deletion_requests rename column synthetic_missing_state to state"))
        finally:
            await engine.dispose()
    asyncio.run(schema())
    assert process(database)[0]["families"]["deletion_and_fair_use"]["values"]["deletion"]["values"]["count"] == 0


def test_deletion_inventory_states_dates_defenses_privacy_and_restart(database, monkeypatch):
    workspace = asyncio.run(seed(database))
    states = ["requested", "deleting", "active_purge_complete", "retryable_failed",
              "complete", "terminal_failed", "none", "private-state"]
    now = datetime(2026, 11, 1, tzinfo=UTC)

    async def populate():
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                row = await deletion_meeting(conn, workspace)
                for index, state in enumerate(states):
                    await conn.execute(insert(MeetingDeletionRequest).values(
                        **row, state=state,
                        created_at=None if index == 0 else text("'infinity'::timestamptz"),
                        accepted_at=now + timedelta(days=100), completed_at=text("'-infinity'::timestamptz"),
                    ))
                await conn.execute(insert(FairUseReviewRecord).values(
                    workspace_id=workspace, subject_user_id=row["requested_by_user_id"],
                    capability="private-capability", reason_code="security_abuse", evidence_ref="private-evidence",
                    state="notice", starts_at=text("'infinity'::timestamptz"), review_by=text("'infinity'::timestamptz"),
                ))
        finally:
            await engine.dispose()
    asyncio.run(populate())
    before = asyncio.run(fingerprint(database))
    actual, sql = cli.create_async_engine, []

    def instrument(*args, **kwargs):
        engine = actual(*args, **kwargs)

        @event.listens_for(engine.sync_engine, "before_cursor_execute")
        def record(conn, cursor, statement, parameters, context, executemany):
            if "meeting_deletion_requests" in statement:
                sql.append(statement)
        return engine

    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected deletion writer or HTTP")

    from twobrain_rec_server.deletion import service
    with monkeypatch.context() as scoped:
        scoped.setattr(cli, "create_async_engine", instrument)
        scoped.setattr(httpx.Client, "request", forbidden)
        scoped.setattr(httpx.AsyncClient, "request", forbidden)
        scoped.setattr(service, "request_meeting_deletion", forbidden)
        result, code = invoke(database)
    assert code == 0
    family = result["families"]["deletion_and_fair_use"]
    assert family["reason_code"] == "unrecognized" and family["coverage"] == "partial"
    assert family["values"]["count"] == 1
    assert family["values"]["pending_review"]["invalid_schedule_count"] == 1
    assert family["values"]["reaction"] is None
    deletion = family["values"]["deletion"]
    assert deletion["reason_code"] == "unrecognized" and deletion["coverage"] == "partial"
    assert deletion["values"]["count"] == 8
    assert deletion["values"]["groups"] == [{"state": state, "count": count} for state, count in (
        ("active_purge_complete", 1), ("deleting", 1), ("requested", 1), ("retryable_failed", 1), ("unrecognized", 4),
    )]
    assert len(sql) == 1 and "private-" not in json.dumps(result)
    assert "where" not in sql[0].lower()
    for private in (".id", "workspace_id", "meeting_id", "requested_by", "request_source", "reason",
                    "confirmation_boundary", "policy", "metadata", "created_at", "accepted_at", "completed_at", "failed_at"):
        assert private not in sql[0].lower()
    for report_day in (DAY, date(1999, 1, 1), date(2099, 1, 1)):
        restarted, code = process(database, day=report_day)
        assert code == 0 and restarted["families"]["deletion_and_fair_use"] == family
        assert "private-" not in json.dumps(restarted)

    # Exercise NULL defensively without weakening the positive migrated schema.
    with monkeypatch.context() as scoped:
        source = values(column("state", String)).data([(None,), ("private-state",), ("deleting",)]).alias("synthetic_requests")
        scoped.setattr(monitoring, "MeetingDeletionRequest", SimpleNamespace(__table__=source))
        defended, code = invoke(database)
        assert code == 0
        assert defended["families"]["deletion_and_fair_use"]["values"]["deletion"]["values"]["groups"] == [
            {"state": "deleting", "count": 1}, {"state": "unrecognized", "count": 2},
        ]
    assert asyncio.run(fingerprint(database)) == before


def test_deletion_inventory_repeatable_snapshot_and_new_process(database):
    workspace = asyncio.run(seed(database))
    as_of = datetime(2026, 11, 1, tzinfo=UTC)

    async def scenario():
        writer = create_async_engine(database)
        reader = create_async_engine(settings(database).database_url, execution_options={
            "isolation_level": "REPEATABLE READ", "postgresql_readonly": True,
        })
        factory = create_sessionmaker(reader)
        scope = {"environment": "test", "shop_id": "123", "report_date": DAY}

        def session():
            db = factory()
            db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                operation_name="billing_reconciliation", actor_id="synthetic-operator",
                reason_category="operator_diagnostics", feature_area="billing",
            ))
            return db
        try:
            async with writer.begin() as conn:
                row = await deletion_meeting(conn, workspace)
            async with session() as db:
                old = await monitoring.collect_billing_report(db, scope=scope, as_of=as_of)
                assert old["families"]["deletion_and_fair_use"]["values"]["deletion"]["values"]["count"] == 0
                async with writer.begin() as conn:
                    await conn.execute(insert(MeetingDeletionRequest).values(**row, state="active_purge_complete"))
                unchanged = await monitoring.collect_billing_report(db, scope=scope, as_of=as_of)
                assert unchanged["families"]["deletion_and_fair_use"] == old["families"]["deletion_and_fair_use"]
            async with session() as db:
                new = await monitoring.collect_billing_report(db, scope=scope, as_of=as_of)
                assert new["families"]["deletion_and_fair_use"]["values"]["deletion"]["values"]["count"] == 1
        finally:
            await reader.dispose()
            await writer.dispose()
    asyncio.run(scenario())
    restarted, code = process(database)
    assert code == 0 and restarted["families"]["deletion_and_fair_use"]["values"]["deletion"]["values"]["count"] == 1


def test_storage_inventory_empty_and_missing_subscription(database):
    empty, code = process(database)
    assert code == 0
    family = empty["families"]["storage"]
    assert family["source"] == "workspaces,workspace_subscriptions,effective_paid_storage,storage_reservations,track_artifacts,upload_sessions"
    assert family["scope"] == "database_inventory" and family["coverage"] == "partial"
    assert family["reason_code"] == "reconciliation_uninstrumented"
    assert family["values"]["workspace_count"] == 0
    assert [family["values"][key] for key in ("used_bytes", "reserved_bytes", "capacity_bytes")] == [0, 0, 0]
    asyncio.run(seed(database))
    before = asyncio.run(fingerprint(database))
    populated, code = process(database)
    assert code == 0
    v = populated["families"]["storage"]["values"]
    assert populated["families"]["storage"]["reason_code"] == "capacity_unavailable"
    assert v["workspace_count"] == v["capacity_unavailable_workspace_count"] == 1
    assert v["unrecognized_plan_count"] == v["invalid_capacity_time_count"] == 0
    assert v["used_bytes"] is v["reserved_bytes"] is v["capacity_bytes"] is None
    assert asyncio.run(fingerprint(database)) == before


async def storage_workspace(conn, parent, **subscription):
    organization, owner = (await conn.execute(text(
        "select organization_id,owner_user_id from workspaces where id=:id"
    ), {"id": parent})).one()
    workspace = uuid4()
    await conn.execute(insert(Workspace).values(id=workspace, organization_id=organization, owner_user_id=owner,
                                              slug=f"private-{workspace}", name="private-workspace", kind="corporate"))
    await conn.execute(insert(WorkspaceSubscription).values(workspace_id=workspace, **subscription))
    return workspace


async def storage_base_invoice(conn, workspace, now, snapshot):
    operation, invoice, grant = uuid4(), uuid4(), uuid4()
    await conn.execute(insert(BillingOperation).values(id=operation, workspace_id=workspace, kind="renewal",
                                                      idempotency_key=f"private-{operation}"))
    await conn.execute(insert(BillingInvoice).values(id=invoice, workspace_id=workspace, operation_id=operation,
                                                   safe_number=f"private-{invoice}", amount_minor=987654321,
                                                   plan_snapshot=snapshot, receipt_contact_snapshot="private-contact"))
    await conn.execute(insert(BillingEntitlementGrant).values(
        id=grant, workspace_id=workspace, invoice_id=invoice, provider_payment_id=f"private-{invoice}",
        plan_code="personal", cycle="month", starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=1), amount_minor=987654321, currency="RUB",
    ))
    return invoice, grant


async def storage_read(url, now):
    engine = create_async_engine(settings(url).database_url, execution_options={
        "isolation_level": "REPEATABLE READ", "postgresql_readonly": True,
    })
    try:
        async with create_sessionmaker(engine)() as db:
            db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                operation_name="billing_reconciliation", actor_id="synthetic-operator",
                reason_category="operator_diagnostics", feature_area="billing",
            ))
            return (await monitoring.collect_billing_report(
                db, scope={"environment": "test", "shop_id": "123", "report_date": DAY}, as_of=now,
            ))["families"]["storage"]
    finally:
        await engine.dispose()


def test_storage_capacity_sources_cutoffs_and_snapshot_fallbacks(database):
    workspace = asyncio.run(seed(database))
    now = datetime.now(UTC)

    async def scenario():
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                await conn.execute(insert(WorkspaceSubscription).values(workspace_id=workspace, plan_code="free"))
                for end in (now + timedelta(days=1), now, None):
                    await storage_workspace(conn, workspace, plan_code="trial", trial_ends_at=end)
                for end in (now + timedelta(days=1), now, None):
                    await storage_workspace(conn, workspace, plan_code="personal", paid_through=end, capacity_bytes=20_000_000_000)
                bonus = await storage_workspace(conn, workspace, plan_code="personal", paid_through=now + timedelta(days=1))
                await conn.execute(insert(TimeCreditLedgerEntry).values(
                    workspace_id=bonus, source_ref="private-bonus", days=7, state="applied",
                    capacity_snapshot_bytes=35_000_000_000, maturity_at=now - timedelta(days=2),
                    expires_at=now + timedelta(days=2), applied_start=now, applied_end=now + timedelta(days=1),
                ))
                active = await storage_workspace(conn, workspace, plan_code="personal", paid_through=now + timedelta(days=1))
                invoice, grant = await storage_base_invoice(conn, active, now, {"purchase_schema": 2})
                price, price_amount = (await conn.execute(text(
                    "select id,amount_minor from billing_storage_price_versions "
                    "where capacity_bytes=40000000000 and cycle='month' and version=2"
                ))).one()
                await conn.execute(insert(BillingStorageEntitlementGrant).values(
                    workspace_id=active, invoice_id=invoice, base_grant_id=grant, capacity_bytes=40_000_000_000,
                    starts_at=now, ends_at=now + timedelta(days=1), catalog_version_id=price, full_period_amount_minor=price_amount,
                ))
                for snapshot in ({"purchase_schema": 2}, {"catalog_snapshot": {"storage_bytes": 30_000_000_000}}, {}):
                    target = await storage_workspace(conn, workspace, plan_code="personal", paid_through=now + timedelta(days=1),
                                                     capacity_bytes=20_000_000_000)
                    await storage_base_invoice(conn, target, now, snapshot)
                journal = await storage_workspace(conn, workspace, plan_code="personal", paid_through=now + timedelta(days=1),
                                                  capacity_bytes=100_000_000_000)
                invoice, grant = await storage_base_invoice(conn, journal, now - timedelta(days=10), {})
                await conn.execute(insert(BillingStorageEntitlementGrant).values(
                    workspace_id=journal, invoice_id=invoice, base_grant_id=grant, capacity_bytes=40_000_000_000,
                    starts_at=now - timedelta(days=10), ends_at=now - timedelta(days=9), catalog_version_id=price,
                    full_period_amount_minor=price_amount,
                ))
            before = await fingerprint(database)
            family = await storage_read(database, now)
            assert family["reason_code"] == "reconciliation_uninstrumented"
            v = family["values"]
            # 250M + Trial(500M+250M+250M) + paid(20G+250M+250M)
            # + bonus35G + active40G + base5G + legacy30G + cache20G + expired-journal5G.
            assert v["workspace_count"] == 13 and v["capacity_bytes"] == 156_750_000_000
            assert v["used_bytes"] == v["reserved_bytes"] == v["capacity_unavailable_workspace_count"] == 0
            assert "private-" not in json.dumps(family) and "987654321" not in json.dumps(family)
            assert await fingerprint(database) == before
        finally:
            await engine.dispose()
    asyncio.run(scenario())


def test_storage_reservation_states_invalid_values_and_capacity_times(database, monkeypatch):
    workspace = asyncio.run(seed(database))
    now = datetime(2026, 11, 2, tzinfo=UTC)

    async def scenario():
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                await conn.execute(insert(WorkspaceSubscription).values(workspace_id=workspace, plan_code="free",
                                  paid_through=text("'infinity'::timestamptz"), trial_ends_at=text("'-infinity'::timestamptz")))
                schedule = [("active", now + timedelta(microseconds=1), 100, 10),
                            ("active", None, 200, 20), ("active", now, 300, 30),
                            ("active", now - timedelta(days=1), 400, 40),
                            ("committed", None, 100, 100), ("released", None, 100, 0)]
                for index, (state, expiry, declared, committed) in enumerate(schedule):
                    await conn.execute(insert(StorageReservation).values(
                        workspace_id=workspace, idempotency_key=f"private-reserve-{index}", state=state,
                        expires_at=expiry, declared_bytes=declared, committed_bytes=committed,
                    ))
            family = await storage_read(database, now)
            assert family["values"]["reserved_bytes"] == 270  # 90 + 180; equality is expired.
            assert family["values"]["capacity_bytes"] == 250_000_000
            assert family["values"]["reservations"] == {"count": 6, "groups": [
                {"state": "active", "count": 4}, {"state": "committed", "count": 1}, {"state": "released", "count": 1}],
                "expired_active_count": 2, "invalid_value_count": 0}
            async with engine.begin() as conn:
                for index, (declared, committed, expiry) in enumerate((
                    (0, 1, now), (-1, -1, None), (1, 2, None),
                    (1, 0, text("'infinity'::timestamptz")), (1, 0, text("'-infinity'::timestamptz")),
                )):
                    await conn.execute(insert(StorageReservation).values(
                        workspace_id=workspace, idempotency_key=f"private-invalid-{index}", state="active",
                        expires_at=expiry, declared_bytes=declared, committed_bytes=committed,
                    ))
                await storage_workspace(conn, workspace, plan_code="trial", trial_ends_at=text("'infinity'::timestamptz"))
                await storage_workspace(conn, workspace, plan_code="personal", paid_through=text("'-infinity'::timestamptz"))
            invalid = await storage_read(database, now)
            assert invalid["reason_code"] == "invalid_storage_values"
            v = invalid["values"]
            assert v["invalid_capacity_time_count"] == v["capacity_unavailable_workspace_count"] == 2
            assert v["reservations"]["invalid_value_count"] == 5
            assert v["reservations"]["expired_active_count"] == 3
            assert v["used_bytes"] is v["reserved_bytes"] is v["capacity_bytes"] is None
            async with engine.begin() as conn:
                await conn.execute(insert(StorageReservation).values(workspace_id=workspace,
                                   idempotency_key="private-unknown", state="private-state", declared_bytes=1, committed_bytes=0))
                await storage_workspace(conn, workspace, plan_code="private-plan")
                # Preserve the actual migrated NOT NULL constraints.
                for field in ("state", "declared_bytes", "committed_bytes"):
                    with pytest.raises(IntegrityError):
                        async with conn.begin_nested():
                            await conn.execute(insert(StorageReservation).values(**{
                                "workspace_id": workspace, "idempotency_key": f"private-null-{field}",
                                "declared_bytes": 1, "committed_bytes": 0, "state": "active", field: None}))
                with pytest.raises(IntegrityError):
                    async with conn.begin_nested():
                        await conn.execute(text("update workspace_subscriptions set plan_code=NULL where workspace_id=:id"), {"id": workspace})
            before = await fingerprint(database)
            unknown = await storage_read(database, now)
            assert unknown["reason_code"] == "unrecognized" and unknown["values"]["unrecognized_plan_count"] == 1
            assert unknown["values"]["reservations"]["groups"][-1] == {"state": "unrecognized", "count": 1}
            with monkeypatch.context() as scoped:
                source = values(column("state", String), column("declared_bytes", BigInteger),
                                column("committed_bytes", BigInteger), column("expires_at", DateTime(timezone=True))).data([
                                    (None, None, 0, None), ("active", 1, None, now), ("released", 1, 0, None),
                                ]).alias("synthetic_reservations")
                scoped.setattr(monitoring, "StorageReservation", SimpleNamespace(__table__=source))
                defended = await storage_read(database, now)
                assert defended["values"]["reservations"] == {"count": 3, "groups": [
                    {"state": "active", "count": 1}, {"state": "released", "count": 1}, {"state": "unrecognized", "count": 1}],
                    "expired_active_count": 1, "invalid_value_count": 2}
            with monkeypatch.context() as scoped:
                source = values(
                    column("workspace_id", WorkspaceSubscription.__table__.c.workspace_id.type),
                    column("plan_code", String), column("capacity_bytes", BigInteger),
                    column("paid_through", DateTime(timezone=True)), column("trial_ends_at", DateTime(timezone=True)),
                ).data([(workspace, None, 250_000_000, text("NULL::timestamptz"), text("NULL::timestamptz"))]).alias("synthetic_subscriptions")
                scoped.setattr(monitoring, "WorkspaceSubscription", SimpleNamespace(__table__=source))
                null_plan = await storage_read(database, now)
                assert null_plan["reason_code"] == "unrecognized"
                assert null_plan["values"]["unrecognized_plan_count"] == 1
                assert null_plan["values"]["capacity_unavailable_workspace_count"] == 4
            assert await fingerprint(database) == before
        finally:
            await engine.dispose()
    asyncio.run(scenario())


def test_storage_falsy_financial_snapshots_and_whole_safe_failures(database, monkeypatch):
    workspace = asyncio.run(seed(database))
    now = datetime.now(UTC)

    async def scenario():
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                await conn.execute(insert(WorkspaceSubscription).values(workspace_id=workspace, plan_code="personal",
                                   paid_through=now + timedelta(days=1), capacity_bytes=20_000_000_000))
                invoice, _ = await storage_base_invoice(conn, workspace, now, {})
            # JSON null/[]/0/false/"" preserve the two existing `or {}` fallbacks.
            for snapshot in (None, [], 0, False, "", *({"catalog_snapshot": v} for v in (None, [], 0, False, ""))):
                async with engine.begin() as conn:
                    await conn.execute(BillingInvoice.__table__.update().where(BillingInvoice.id == invoice)
                                       .values(plan_snapshot=snapshot))
                before = await fingerprint(database)
                family = await storage_read(database, now)
                assert family["values"]["capacity_bytes"] == 20_000_000_000
                assert family["reason_code"] == "reconciliation_uninstrumented"
                assert await fingerprint(database) == before
            for snapshot in (["private-snapshot"], {"catalog_snapshot": ["private-snapshot"]}):
                async with engine.begin() as conn:
                    await conn.execute(BillingInvoice.__table__.update().where(BillingInvoice.id == invoice)
                                       .values(plan_snapshot=snapshot))
                before = await fingerprint(database)
                assert await asyncio.to_thread(process, database) == (cli.failure("report_unavailable"), 1)
                assert await fingerprint(database) == before
            async with engine.begin() as conn:
                await conn.execute(BillingInvoice.__table__.update().where(BillingInvoice.id == invoice).values(plan_snapshot={}))
                await conn.execute(text("alter table storage_reservations rename column declared_bytes to synthetic_missing_bytes"))
            try:
                assert await asyncio.to_thread(process, database) == (cli.failure("report_unavailable"), 1)
            finally:
                async with engine.begin() as conn:
                    await conn.execute(text("alter table storage_reservations rename column synthetic_missing_bytes to declared_bytes"))
        finally:
            await engine.dispose()
    asyncio.run(scenario())

    async def broken(*args, **kwargs):
        raise ValueError("private-helper-error")
    with monkeypatch.context() as scoped:
        scoped.setattr(monitoring, "effective_paid_storage", broken)
        assert invoke(database) == (cli.failure("report_unavailable"), 1)


def test_storage_canonical_playback_repeatable_snapshot_and_new_process(database, monkeypatch):
    from twobrain_rec_server.billing.storage import CANONICAL_PLAYBACK_PROFILE

    workspace = asyncio.run(seed(database))
    now = datetime.now(UTC)

    async def scenario():
        writer = create_async_engine(database)
        reader = create_async_engine(settings(database).database_url, execution_options={
            "isolation_level": "REPEATABLE READ", "postgresql_readonly": True,
        })
        factory = create_sessionmaker(reader)

        async def artifact(conn, byte_length, *, kind="canonical"):
            row = await deletion_meeting(conn, workspace)
            revision = uuid4()
            await conn.execute(insert(MediaRevision).values(id=revision, workspace_id=workspace,
                               meeting_id=row["meeting_id"], local_media_revision_id=f"private-revision-{revision}"))
            validated = kind in {"canonical", "noarchive", "wrong_suffix"}
            await conn.execute(insert(TrackArtifact).values(
                meeting_id=row["meeting_id"], workspace_id=workspace, media_revision_id=revision,
                track_role="media" if kind == "wav" else "playback", codec="private-codec", sample_rate_hz=48000,
                channel_count=1, duration_seconds=1, byte_length=byte_length, sha256="f" * 64,
                storage_object_key=f"private-key/{revision}/" + ("meeting-transcription.wav" if kind == "wav" else
                                   "meeting-review.m4a.tmp" if kind == "wrong_suffix" else "meeting-review.m4a"),
                status="deleted" if kind == "deleted" else "stored",
                normalization_profile_version=CANONICAL_PLAYBACK_PROFILE if validated else None,
                validated_at=now if validated else None, derivation_kind="normalized" if validated else None,
                source_fingerprint_sha256="a" * 64 if validated else None,
                validation_version="playback_validator_v1" if validated else None,
            ))
            if kind == "noarchive":
                device = (await conn.execute(text("select device_id from meetings where id=:id"), {"id": row["meeting_id"]})).scalar_one()
                await conn.execute(insert(UploadSession).values(
                    workspace_id=workspace, meeting_id=row["meeting_id"], media_revision_id=revision, device_id=device,
                    created_by_user_id=row["requested_by_user_id"], status="finalized", archive_audio=False,
                    max_package_bytes_snapshot=1_000_000, max_track_bytes_snapshot=1_000_000,
                    expires_at=now + timedelta(days=1),
                ))

        def session():
            db = factory()
            db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                operation_name="billing_reconciliation", actor_id="synthetic-operator",
                reason_category="operator_diagnostics", feature_area="billing",
            ))
            return db

        async def read(db):
            return (await monitoring.collect_billing_report(
                db, scope={"environment": "test", "shop_id": "123", "report_date": DAY}, as_of=now,
            ))["families"]["storage"]
        try:
            async with writer.begin() as conn:
                await conn.execute(insert(WorkspaceSubscription).values(workspace_id=workspace, plan_code="free"))
                for size, kind in ((111, "canonical"), (222, "noarchive"), (333, "wrong_suffix"),
                                   (444, "unvalidated"), (555, "wav"), (666, "deleted"), (777, "canonical")):
                    await artifact(conn, size, kind=kind)
                await conn.execute(insert(StorageReservation).values(workspace_id=workspace, idempotency_key="private-old",
                                   declared_bytes=100, committed_bytes=10, state="active", expires_at=None))
            before = await fingerprint(database)
            async with session() as db:
                old = await read(db)
                assert (old["values"]["used_bytes"], old["values"]["reserved_bytes"], old["values"]["capacity_bytes"]) == (888, 90, 250_000_000)
                assert await fingerprint(database) == before
                async with writer.begin() as conn:
                    await artifact(conn, 101)
                    await conn.execute(insert(StorageReservation).values(workspace_id=workspace, idempotency_key="private-late",
                                       declared_bytes=70, committed_bytes=20, state="active", expires_at=None))
                    await conn.execute(WorkspaceSubscription.__table__.update().where(WorkspaceSubscription.workspace_id == workspace)
                                       .values(plan_code="trial", trial_ends_at=now + timedelta(days=1)))
                assert await read(db) == old
            before = await fingerprint(database)
            async with session() as db:
                new = await read(db)
                assert (new["values"]["used_bytes"], new["values"]["reserved_bytes"], new["values"]["capacity_bytes"]) == (989, 140, 500_000_000)
            assert await fingerprint(database) == before
            return new
        finally:
            await reader.dispose()
            await writer.dispose()
    family = asyncio.run(scenario())
    before = asyncio.run(fingerprint(database))
    for report_day in (DAY, date(1999, 1, 1), date(2099, 1, 1)):
        restarted, code = process(database, day=report_day)
        assert code == 0 and restarted["families"]["storage"] == family
        assert "private-" not in json.dumps(restarted) and "987654321" not in json.dumps(restarted)
    def forbidden(*args, **kwargs):
        raise AssertionError("storage inventory must never call HTTP")
    monkeypatch.setattr(httpx.AsyncClient, "request", forbidden)
    monkeypatch.setattr(httpx.Client, "request", forbidden)
    assert invoke(database)[0]["families"]["storage"] == family
    assert asyncio.run(fingerprint(database)) == before


def test_storage_full_workspace_limit_and_shared_deadline(database, monkeypatch):
    workspace = asyncio.run(seed(database))

    async def populate(count):
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                organization, owner = (await conn.execute(text(
                    "select organization_id,owner_user_id from workspaces where id=:id"
                ), {"id": workspace})).one()
                await conn.execute(insert(Workspace), [{"id": uuid4(), "organization_id": organization,
                    "owner_user_id": owner, "slug": f"private-{uuid4()}", "name": "private-workspace", "kind": "corporate"}
                    for _ in range(count)])
        finally:
            await engine.dispose()
    asyncio.run(populate(499))
    result, code = process(database)
    assert code == 0 and result["families"]["storage"]["values"]["workspace_count"] == 500
    assert result["families"]["storage"]["values"]["capacity_unavailable_workspace_count"] == 500
    asyncio.run(populate(1))
    before = asyncio.run(fingerprint(database))
    assert process(database) == (cli.failure("report_limit_exceeded"), 1)
    assert asyncio.run(fingerprint(database)) == before

    async def shrink():
        engine = create_async_engine(database)
        try:
            async with engine.begin() as conn:
                await conn.execute(delete(Workspace).where(Workspace.id != workspace))
                await conn.execute(insert(WorkspaceSubscription).values(workspace_id=workspace, plan_code="free"))
        finally:
            await engine.dispose()
    asyncio.run(shrink())
    reached = []
    async def slow(db, *, subscription, now):
        reached.append(True)
        await asyncio.sleep(10)
    with monkeypatch.context() as scoped:
        scoped.setattr(monitoring, "effective_paid_storage", slow)
        scoped.setattr(cli, "REPORT_TIMEOUT_SECONDS", 0.3)
        assert invoke(database) == (cli.failure("report_timeout"), 1)
    assert reached == [True]
