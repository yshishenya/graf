"""Real PostgreSQL/CLI proofs on synthetic reports and disposable roles only."""
import asyncio
import json
import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, func, insert, select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from tests.unit.test_billing_registry import DAY, report
from twobrain_rec_server.billing.database import BillingMaintenanceDatabaseError
from twobrain_rec_server.billing.registry_store import registry_status
from twobrain_rec_server.cli.billing_registry import build_parser, run
from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.db.models import BillingRegistryGap, BillingRegistryImport
from twobrain_rec_server.db.session import create_sessionmaker
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    maintenance_context_settings,
)

pytestmark = pytest.mark.strict_rls


@pytest.fixture
def registry_database(postgres_isolated_cluster_database_url):
    url = postgres_isolated_cluster_database_url

    async def setup():
        engine = create_async_engine(url)
        try:
            async with engine.begin() as conn:
                for role in ("twobrain_rec_app", "twobrain_rec_maintenance", "registry_worker"):
                    password = (await conn.execute(select(func.quote_literal(make_url(url).password)))).scalar_one()
                    await conn.execute(text(f"CREATE ROLE {role} LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT PASSWORD {password}"))
                    await conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
                    # Even a later broad bootstrap grant cannot weaken the exact RLS policy.
                    await conn.execute(text(f"GRANT SELECT,INSERT,UPDATE,DELETE ON billing_registry_imports,billing_registry_gaps TO {role}"))
                    await conn.execute(text(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {role}"))
                await conn.execute(text("GRANT twobrain_rec_maintenance TO registry_worker"))
        finally:
            await engine.dispose()
    asyncio.run(setup())
    return url


def settings(url, role="twobrain_rec_maintenance"):
    return Settings(database_url=make_url(url).set(username=role).render_as_string(hide_password=False),
                    billing_yookassa_environment="test", billing_yookassa_shop_id="123")


def files(tmp_path, *, payment_count=1, refunds=True):
    paths = []
    for kind, count in (("payments", payment_count), ("refunds", 1)):
        if kind == "refunds" and not refunds:
            continue
        path = tmp_path / f"yoomoney-{kind}-123-{DAY}.csv"
        path.write_bytes(report(kind, count))
        paths.extend((f"--{kind}", str(path)))
    return paths


def arguments(*paths, execute=True, extra=()):
    return build_parser().parse_args(["import", "--date", str(DAY), "--owner", "billing-operations",
                                     "--operator", "test-operator", *paths, *extra,
                                     *(["--execute"] if execute else [])])


def invoke(url, *paths, **kwargs):
    return asyncio.run(run(arguments(*paths, **kwargs), settings=settings(url)))


def status(url):
    args = build_parser().parse_args(["status", "--date", str(DAY)])
    return asyncio.run(run(args, settings=settings(url)))


def test_cli_dry_run_restart_replay_and_safe_metadata(registry_database, tmp_path):
    url = registry_database
    paths = files(tmp_path)
    dry, code = invoke(url, *paths, execute=False)
    assert code == 0 and dry["dry_run"] and dry["files_complete"]
    assert status(url)[0]["latest_accepted"] is None
    first, code = invoke(url, *paths)
    assert code == 0 and first["financial_status"] == "not_checked"
    replay, code = invoke(url, *paths)
    assert code == 0 and replay["replay"] and replay["receipt_id"] == first["receipt_id"]
    env = {**os.environ, "TWOBRAIN_DATABASE_URL": settings(url).database_url,
           "TWOBRAIN_BILLING_YOOKASSA_SHOP_ID": "123", "TWOBRAIN_BILLING_YOOKASSA_ENVIRONMENT": "test"}
    restarted = subprocess.run([sys.executable, "-m", "twobrain_rec_server.cli.billing_registry", "status", "--date", str(DAY)],
                               env=env, capture_output=True, text=True, timeout=30)
    assert restarted.returncode == 0, "new CLI process must read persisted status"
    saved = json.loads(restarted.stdout)
    assert saved["latest_accepted"]["receipt_id"] == first["receipt_id"]
    assert saved["last_attempt"] == saved["latest_accepted"]
    rendered = restarted.stdout
    for private in ("synthetic", "1.00", str(tmp_path), "contract", "payment_id"):
        assert private not in rendered


def test_replacement_rejected_input_historical_replay_and_gap_generations(registry_database, tmp_path):
    url = registry_database
    paths = files(tmp_path, refunds=False)
    first, code = invoke(url, *paths)
    assert code == 0 and not first["files_complete"]
    gap = status(url)[0]["open_gaps"][0]
    assert gap["owner"] == "billing-operations" and gap["severity"] == "high"
    assert gap["containment"] == "report_unverified" and gap["generation"] == 1
    assert invoke(url, *paths)[0]["replay"]
    assert status(url)[0]["open_gaps"][0] == gap
    full_paths = files(tmp_path)
    assert invoke(url, *full_paths)[1] != 0  # no blind replacement
    assert status(url)[0]["latest_accepted"]["receipt_id"] == first["receipt_id"]
    assert status(url)[0]["open_gaps"][0] == gap
    fixed, code = invoke(url, *full_paths, extra=("--replace", first["input_digest"], "--reason", "corrected_export"))
    assert code == 0 and fixed["files_complete"]
    assert status(url)[0]["open_gaps"] == []
    old, code = invoke(url, *paths)
    assert code == 0 and old["replay"] and old["receipt_id"] == first["receipt_id"]
    assert status(url)[0]["latest_accepted"]["receipt_id"] == fixed["receipt_id"]
    payment_path = tmp_path / f"yoomoney-payments-123-{DAY}.csv"
    payment_path.write_bytes(b"private-invalid-report")
    assert invoke(url, *full_paths)[1] != 0
    saved = status(url)[0]
    assert saved["latest_accepted"]["receipt_id"] == fixed["receipt_id"]
    assert saved["last_attempt"]["result_code"] == "invalid_csv"
    bad_gap = next(g for g in saved["open_gaps"] if g["reason"] == "invalid_csv")
    payment_path.write_bytes(report("payments", 2))
    newer, code = invoke(url, *full_paths, extra=("--replace", fixed["input_digest"], "--reason", "corrected_export"))
    assert code == 0 and status(url)[0]["open_gaps"] == []
    payment_path.write_bytes(b"private-invalid-report")
    invoke(url, *full_paths)
    reopened = next(g for g in status(url)[0]["open_gaps"] if g["reason"] == "invalid_csv")
    assert reopened["generation"] == bad_gap["generation"] + 1
    assert reopened["gap_id"] != bad_gap["gap_id"]
    assert newer["receipt_id"] > fixed["receipt_id"]


def test_real_roles_guard_before_file_and_store(registry_database, tmp_path, monkeypatch):
    url = registry_database
    first, code = invoke(url, *files(tmp_path))
    assert code == 0 and first["accepted"]
    opened = []
    from twobrain_rec_server.cli import billing_registry
    def unexpected_read(*args, **kwargs):
        opened.append(True)
        raise AssertionError("database guard must run before reading files")
    monkeypatch.setattr(billing_registry, "read_registry_files", unexpected_read)
    args = arguments("--payments", str(tmp_path / "missing.csv"))
    for role in ("twobrain_rec", "twobrain_rec_app", "registry_worker"):
        result, code = asyncio.run(run(args, settings=settings(url, role)))
        assert code != 0 and result["result_code"] == "database_identity_rejected"
    assert opened == []

    async def probe():
        for role in ("twobrain_rec_app", "registry_worker", "twobrain_rec_maintenance"):
            engine = create_async_engine(settings(url, role).database_url)
            try:
                contexts = [("operator_diagnostics", "billing"), ("billing_reconciliation", "wrong")]
                if role != "twobrain_rec_maintenance":
                    contexts.append(("billing_reconciliation", "billing"))
                for operation, area in contexts:
                    async with create_sessionmaker(engine)() as db:
                        db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                            operation_name=operation, feature_area=area, actor_id="test", reason_category="test"))
                        assert (await db.execute(select(BillingRegistryImport))).all() == []
                        with pytest.raises(BillingMaintenanceDatabaseError):
                            await registry_status(db, environment="test", shop_id="123", report_date=DAY)
            finally:
                await engine.dispose()
        engine = create_async_engine(settings(url, "registry_worker").database_url)
        try:
            async with create_sessionmaker(engine)() as db:
                db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                    operation_name="billing_reconciliation", feature_area="billing", actor_id="test", reason_category="test"))
                await db.execute(text("SET ROLE twobrain_rec_maintenance"))
                assert (await db.execute(select(BillingRegistryImport))).all() == []
                with pytest.raises(BillingMaintenanceDatabaseError):
                    await registry_status(db, environment="test", shop_id="123", report_date=DAY)
            async with create_sessionmaker(engine)() as db:
                await db.execute(text("SET row_security = off"))
                with pytest.raises(BillingMaintenanceDatabaseError):
                    await registry_status(db, environment="test", shop_id="123", report_date=DAY)
        finally:
            await engine.dispose()
    asyncio.run(probe())


def test_direct_rls_denies_both_tables_and_history_is_preserved(registry_database, tmp_path):
    url = registry_database
    first, _ = invoke(url, *files(tmp_path, refunds=False))

    async def probe():
        admin = create_async_engine(url)
        tables = (BillingRegistryImport.__table__, BillingRegistryGap.__table__)
        try:
            async with admin.connect() as conn:
                rows = [(await conn.execute(select(t))).mappings().one() for t in tables]
                flags = (await conn.execute(text("SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname IN ('billing_registry_imports','billing_registry_gaps')"))).all()
                assert flags == [(True, True), (True, True)]
            for role, operation, area in (("twobrain_rec_app", "billing_reconciliation", "billing"),
                                           ("registry_worker", "billing_reconciliation", "billing"),
                                           ("twobrain_rec_maintenance", "operator_diagnostics", "billing"),
                                           ("twobrain_rec_maintenance", "billing_reconciliation", "wrong")):
                engine = create_async_engine(settings(url, role).database_url)
                try:
                    async with create_sessionmaker(engine)() as db:
                        db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                            operation_name=operation, feature_area=area, actor_id="test", reason_category="test"))
                        for table, row in zip(tables, rows, strict=True):
                            assert (await db.execute(select(table))).all() == []
                            assert (await db.execute(update(table).values(shop_id="456"))).rowcount == 0
                            assert (await db.execute(delete(table))).rowcount == 0
                            values = {k: v for k, v in row.items() if k != "id"}
                            with pytest.raises(DBAPIError) as failure:
                                async with db.begin_nested():
                                    await db.execute(insert(table).values(**values))
                            assert failure.value.orig.sqlstate == "42501"
                            assert "row-level security" in str(failure.value.orig)
                finally:
                    await engine.dispose()
            for field, value in (("owner", "changed-owner"), ("deadline_at", rows[1]["deadline_at"] + timedelta(seconds=1))):
                with pytest.raises(DBAPIError):
                    async with admin.begin() as conn:
                        await conn.execute(update(tables[1]).values(**{field: value}))
        finally:
            await admin.dispose()
    asyncio.run(probe())
    gap = status(url)[0]["open_gaps"][0]
    fixed, code = invoke(url, *files(tmp_path), extra=("--replace", first["input_digest"], "--reason", "corrected_export"))
    assert code == 0

    async def resolution():
        engine = create_async_engine(url)
        try:
            async with engine.connect() as conn:
                saved = (await conn.execute(select(BillingRegistryGap))).mappings().one()
                assert saved["state"] == "resolved" and saved["resolved_by"] == "test-operator"
                assert saved["closing_receipt_id"] == fixed["receipt_id"]
                assert saved["resolved_at"] >= saved["detected_at"]
                assert saved["deadline_at"].isoformat() == gap["deadline_at"]
                assert saved["owner"] == gap["owner"]
            with pytest.raises(DBAPIError):
                async with engine.begin() as conn:
                    await conn.execute(update(BillingRegistryGap).values(checked_at=func.clock_timestamp()))
        finally:
            await engine.dispose()
    asyncio.run(resolution())


def test_atomic_rollback_and_immutable_receipt(registry_database, tmp_path):
    url = registry_database
    invoke(url, *files(tmp_path, refunds=False))

    async def probe():
        engine = create_async_engine(url)
        try:
            async with engine.begin() as conn:
                rows = (await conn.execute(select(BillingRegistryImport))).all()
                assert len(rows) == 1
                gap = (await conn.execute(select(BillingRegistryGap))).mappings().one()
                assert gap["deadline_at"] - gap["detected_at"] <= timedelta(hours=24)
            async with engine.begin() as conn:
                with pytest.raises(DBAPIError):
                    await conn.execute(text("UPDATE billing_registry_imports SET operator = 'changed'"))
            async with engine.begin() as conn:
                with pytest.raises(DBAPIError):
                    await conn.execute(text("DELETE FROM billing_registry_imports"))
        finally:
            await engine.dispose()
    asyncio.run(probe())


def test_two_concurrent_replacements_use_same_scope_lock(registry_database, tmp_path):
    url = registry_database
    original, _ = invoke(url, *files(tmp_path))
    left, right = tmp_path / "left", tmp_path / "right"
    left.mkdir()
    right.mkdir()
    paths_left = files(left, payment_count=2)
    paths_right = files(right, payment_count=3)
    extra = ("--replace", original["input_digest"], "--reason", "corrected_export")

    async def race():
        return await asyncio.gather(run(arguments(*paths_left, extra=extra), settings=settings(url)),
                                    run(arguments(*paths_right, extra=extra), settings=settings(url)))
    results = asyncio.run(race())
    assert sorted(code for _, code in results) == [0, 1]
    assert next(r for r, code in results if code)["result_code"] == "replace_conflict"
    saved = status(url)[0]
    winner = next(r for r, code in results if not code)
    assert saved["latest_accepted"]["receipt_id"] == winner["receipt_id"]
    assert winner["previous_accepted_id"] == original["receipt_id"]


def test_database_failure_rolls_back_receipt_and_gap_transitions(registry_database, tmp_path):
    url = registry_database
    first, _ = invoke(url, *files(tmp_path))

    async def inject_failure():
        engine = create_async_engine(url)
        try:
            async with engine.begin() as conn:
                await conn.execute(text("""CREATE FUNCTION registry_test_fail() RETURNS trigger LANGUAGE plpgsql AS $$
                    BEGIN RAISE EXCEPTION 'synthetic failure'; END $$"""))
                await conn.execute(text("CREATE TRIGGER registry_test_fail BEFORE INSERT ON billing_registry_gaps FOR EACH ROW EXECUTE FUNCTION registry_test_fail()"))
        finally:
            await engine.dispose()
    asyncio.run(inject_failure())
    result, code = invoke(url, *files(tmp_path, payment_count=2, refunds=False),
                          extra=("--replace", first["input_digest"], "--reason", "corrected_export"))
    assert code != 0 and result == {"result_code": "database_unavailable"}
    saved = status(url)[0]
    assert saved["last_attempt"]["receipt_id"] == first["receipt_id"]
    assert saved["open_gaps"] == []


def test_status_keeps_one_generation_while_replacement_waits(registry_database, tmp_path, monkeypatch):
    from twobrain_rec_server.billing import registry_store

    url = registry_database
    first, _ = invoke(url, *files(tmp_path, refunds=False))
    full_paths = files(tmp_path, payment_count=2)

    async def race():
        selected = asyncio.Event()
        release_reader = asyncio.Event()
        original_access = registry_store._access
        reader_session = None

        async def pause_after_first_select(db, statement):
            result = await original_access(db, statement)
            if db is reader_session and not selected.is_set():
                selected.set()
                await asyncio.wait_for(release_reader.wait(), 10)
            return result

        monkeypatch.setattr(registry_store, "_access", pause_after_first_select)
        engine = create_async_engine(settings(url).database_url)
        try:
            async with create_sessionmaker(engine)() as db:
                reader_session = db
                db.sync_session.info["tenant_context"] = maintenance_context_settings(MaintenanceTenantContext(
                    operation_name="billing_reconciliation", feature_area="billing", actor_id="test", reason_category="test"))
                async with db.begin():
                    await db.execute(text("SET TRANSACTION READ ONLY"))
                    reader = asyncio.create_task(registry_status(db, environment="test", shop_id="123", report_date=DAY))
                    await asyncio.wait_for(selected.wait(), 10)
                    writer = asyncio.create_task(run(arguments(*full_paths, extra=(
                        "--replace", first["input_digest"], "--reason", "corrected_export")), settings=settings(url)))
                    # Observe the writer actually waiting on the advisory lock, not
                    # merely an unfinished task which might not have started yet.
                    async with engine.connect() as observer:
                        async with asyncio.timeout(10):
                            while not (await observer.execute(text("SELECT EXISTS (SELECT 1 FROM pg_locks WHERE locktype = 'advisory' AND NOT granted)"))).scalar_one():
                                await asyncio.sleep(0.01)
                    release_reader.set()
                    snapshot = await reader
                    assert not writer.done()
                    assert snapshot["last_attempt"]["receipt_id"] == first["receipt_id"]
                    assert snapshot["latest_accepted"]["receipt_id"] == first["receipt_id"]
                    assert snapshot["open_gaps"][0]["reason"] == "missing_kind"
            replacement, code = await asyncio.wait_for(writer, 10)
            assert code == 0 and replacement["files_complete"]
        finally:
            release_reader.set()
            await engine.dispose()
    asyncio.run(race())
    assert status(url)[0]["open_gaps"] == []


def test_migration_roundtrip_and_history_blocks_downgrade(registry_database, tmp_path, monkeypatch):
    server_root = Path(__file__).resolve().parents[2]
    config = Config(str(server_root / "alembic.ini"))
    config.set_main_option("script_location", str(server_root / "src/twobrain_rec_server/db/migrations"))
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", registry_database)
    get_settings.cache_clear()
    try:
        command.downgrade(config, "0106_activation_milestones")
        command.upgrade(config, "head")
        accepted, code = invoke(registry_database, *files(tmp_path))
        assert code == 0 and accepted["files_complete"]
        with pytest.raises(DBAPIError, match="registry history exists"):
            command.downgrade(config, "0106_activation_milestones")
        assert status(registry_database)[0]["latest_accepted"]["receipt_id"] == accepted["receipt_id"]
    finally:
        get_settings.cache_clear()
