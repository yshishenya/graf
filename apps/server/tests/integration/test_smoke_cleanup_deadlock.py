"""Real FK contention on disposable PostgreSQL, never production fixtures."""

from __future__ import annotations

import asyncio
import importlib.util
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from minio import Minio
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from scripts import bootstrap_runtime_database_roles as bootstrap
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db import models
from twobrain_rec_server.db.tenant_context import apply_tenant_context_to_connection
from twobrain_rec_server.deployment import build_smoke_identity_seed


def _helper():
    path = Path(__file__).resolve().parents[2] / "scripts/cleanup_smoke_artifacts.py"
    spec = importlib.util.spec_from_file_location("cleanup_deadlock_subject", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TABLES = (
    "organizations", "workspaces", "user_identities", "registered_devices",
    "workspace_memberships", "meetings", "upload_sessions", "media_revisions",
    "processing_workflows", "mediascribe_jobs", "processing_results", "processing_dependency_states",
)


@pytest.fixture
async def cleanup_case(postgres_isolated_cluster_database_url, monkeypatch):
    """Full migrations and real runtime LOGIN; owner is only the synthetic seeder/observer."""
    url = make_url(postgres_isolated_cluster_database_url)
    passwords = {
        "TWOBRAIN_DB_OWNER_PASSWORD_FILE": url.password,
        "TWOBRAIN_DB_APP_PASSWORD_FILE": uuid4().hex,
        "TWOBRAIN_DB_MAINTENANCE_PASSWORD_FILE": uuid4().hex,
        "TWOBRAIN_DB_MEDIA_PASSWORD_FILE": uuid4().hex,
    }
    monkeypatch.setattr(bootstrap, "_read_secret", passwords.__getitem__)
    for key, value in {"HOST": url.host, "PORT": str(url.port), "NAME": url.database}.items():
        monkeypatch.setenv(f"TWOBRAIN_DB_{key}", value)
    await bootstrap._bootstrap()
    owner_url = url.render_as_string(hide_password=False)
    maintenance_url = url.set(username="twobrain_rec_maintenance", password=passwords[
        "TWOBRAIN_DB_MAINTENANCE_PASSWORD_FILE"]).render_as_string(hide_password=False)
    owner = create_async_engine(owner_url)
    maintenance = create_async_engine(maintenance_url)
    try:
        async with maintenance.begin() as conn:
            await apply_tenant_context_to_connection(conn, _helper()._maintenance_context())
            row = (await conn.execute(text("""
                SELECT session_user, current_user, rolsuper, rolbypassrls,
                       current_setting('row_security'), public.rec_maintenance_allowed()
                FROM pg_roles WHERE rolname=current_user
            """))).one()
            assert tuple(row) == ("twobrain_rec_maintenance", "twobrain_rec_maintenance",
                                  False, False, "on", True)
        yield SimpleNamespace(owner_url=owner_url, maintenance_url=maintenance_url,
                              owner=owner, maintenance=maintenance)
    finally:
        await maintenance.dispose()
        await owner.dispose()


async def _insert(conn, model, **values):
    await conn.execute(model.__table__.insert().values(**values))


async def _storage_graph(conn, graph):
    graph = graph | {"artifact": uuid4(), "reservation": uuid4(), "unbound": uuid4()}
    await _insert(conn, models.TrackArtifact, id=graph["artifact"], meeting_id=graph["meeting"],
                  workspace_id=graph["workspace"], track_role="media", codec="pcm_s16le",
                  sample_rate_hz=16000, channel_count=1, duration_seconds=1, byte_length=2,
                  sha256="a" * 64, storage_object_key="synthetic/" + str(graph["artifact"]))
    for key, artifact in [("reservation", graph["artifact"]), ("unbound", None)]:
        await _insert(conn, models.StorageReservation, id=graph[key], workspace_id=graph["workspace"],
                      artifact_id=artifact, declared_bytes=2, idempotency_key=str(graph[key]))
    return graph


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("live_minio", [False, True], ids=["residue", "real-minio"])
async def test_interrupted_smoke_retains_unconfirmed_object_intent_and_preserves_neighbor(
    cleanup_case, monkeypatch, live_minio,
):
    helper = _helper()
    settings = Settings(database_url=cleanup_case.maintenance_url)
    storage = None
    bucket = f"graf-smoke-test-{uuid4().hex}"
    if live_minio:
        endpoint = os.environ.get("GRAF_TEST_STRICT_MINIO_ENDPOINT")
        if not endpoint:
            pytest.skip("requires a dedicated disposable MinIO")
        host, _, port = endpoint.partition(":")
        assert host == "127.0.0.1" and port.isdecimal() and 0 < int(port) < 65536
        access = os.environ["GRAF_TEST_STRICT_MINIO_ACCESS"]
        secret = os.environ["GRAF_TEST_STRICT_MINIO_SECRET"]
        settings = settings.model_copy(update=dict(
            minio_endpoint=endpoint, minio_access_key=access, minio_secret_key=secret,
            minio_secure=False, minio_bucket=bucket,
        ))
        storage = Minio(endpoint, access_key=access, secret_key=secret, secure=False)
        storage.make_bucket(bucket)
    monkeypatch.setattr(helper, "Settings", lambda: settings)
    engine = create_async_engine(cleanup_case.owner_url)
    run_id = "forward-" + "a" * 32
    checked = []
    storage_residue = 1

    def cleanup_prefix(_settings, prefix):
        checked.append(prefix)
        return 0, storage_residue

    if storage is None:
        monkeypatch.setattr(helper, "_remove_storage_prefix", cleanup_prefix)
    try:
        async with engine.begin() as conn:
            target = await _graph(conn, run_id) | {"intent": uuid4()}
            neighbor = await _graph(conn, "neighbor", ordinary=True) | {"intent": uuid4()}
            object_keys = []
            for graph in (target, neighbor):
                prefix = helper._smoke_storage_prefix({"organization_id": graph["org"], "workspace_id": graph["workspace"]})
                key = f"{prefix}meetings/{graph['meeting']}/pending-part"
                object_keys.append(key)
                await _insert(conn, models.PurgeJournal, id=graph["intent"], workspace_id=graph["workspace"],
                              meeting_id=graph["meeting"], artifact_class="object_store", object_key=key)
        if storage is not None:
            for key in object_keys:
                storage.put_object(bucket, key, BytesIO(b"synthetic"), 9)
        with pytest.raises(IntegrityError):
            await helper.cleanup_smoke_artifacts(run_id)
        assert not checked
        if storage is None:
            with pytest.raises(ValueError, match="still has storage residue"):
                await helper.cleanup_smoke_artifacts(run_id, reconcile_interrupted=True)
        else:
            assert {obj.object_name for obj in storage.list_objects(bucket, recursive=True)} == set(object_keys)
        async with engine.connect() as conn:
            assert set((await conn.scalars(text("select id from meeting_purge_journal"))).all()) == {
                target["intent"], neighbor["intent"]}
            assert set((await conn.scalars(text("select id from meetings"))).all()) == {
                target["meeting"], neighbor["meeting"]}
        storage_residue = 0  # Simulates a stopped PUT with only its durable intent left.
        removed, objects, residue = await helper.cleanup_smoke_artifacts(run_id, reconcile_interrupted=True)
        assert removed > 0 and objects == int(live_minio) and residue == []
        async with engine.connect() as conn:
            assert (await conn.scalars(text("select id from meeting_purge_journal"))).all() == [neighbor["intent"]]
            assert (await conn.scalars(text("select id from meetings"))).all() == [neighbor["meeting"]]
        if storage is None:
            assert checked == [helper._smoke_storage_prefix(
                {"organization_id": target["org"], "workspace_id": target["workspace"]})] * 2
        else:
            assert [obj.object_name for obj in storage.list_objects(bucket, recursive=True)] == object_keys[1:]
            removed, objects, residue = await helper.cleanup_smoke_artifacts(run_id, reconcile_interrupted=True)
            assert (removed, objects, residue) == (0, 0, [])
            assert [obj.object_name for obj in storage.list_objects(bucket, recursive=True)] == object_keys[1:]
    finally:
        await engine.dispose()
        if storage is not None:
            for obj in storage.list_objects(bucket, recursive=True):
                storage.remove_object(bucket, obj.object_name)
            storage.remove_bucket(bucket)


@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_forward_cleanup_requires_exact_finalized_upload_and_preserves_neighbor(
    cleanup_case, monkeypatch,
):
    helper = _helper()
    monkeypatch.setattr(helper, "Settings", lambda: Settings(database_url=cleanup_case.maintenance_url))
    storage = []
    monkeypatch.setattr(helper, "_remove_storage_prefix", lambda _settings, prefix: (storage.append(prefix) or (3, 0)))
    engine = create_async_engine(cleanup_case.owner_url)
    run_id = "forward-cleanup"
    try:
        async with engine.begin() as conn:
            target = await _graph(conn, run_id) | {"session": uuid4()}
            neighbor = await _graph(conn, "forward-neighbor", ordinary=True) | {"session": uuid4()}
            for graph in (target, neighbor):
                await _insert(conn, models.UploadSession, id=graph["session"], meeting_id=graph["meeting"],
                              workspace_id=graph["workspace"], device_id=graph["device"],
                              created_by_user_id=graph["user"], media_revision_id=graph["revision"],
                              status="finalized", finalized_at=datetime.now(UTC),
                              max_package_bytes_snapshot=1024, max_track_bytes_snapshot=1024,
                              expires_at=datetime.now(UTC) + timedelta(hours=1))
            before = await _snapshot(conn)
        for session, revision, reason in (
            (neighbor["session"], target["revision"], "does not belong"),
            (target["session"], neighbor["revision"], "not the finalized upload"),
        ):
            with pytest.raises(ValueError, match=reason):
                await helper.cleanup_smoke_artifacts(run_id, str(target["meeting"]), str(session), str(revision))
        async with engine.connect() as conn:
            assert await _snapshot(conn) == before
        assert not storage
        removed, objects, residue = await helper.cleanup_smoke_artifacts(
            run_id, str(target["meeting"]), str(target["session"]), str(target["revision"]),
        )
        assert removed > 0 and objects == 3 and not residue
        async with engine.connect() as conn:
            for table, rows in (await _snapshot(conn)).items():
                assert rows == [row for row in before[table] if row[0] not in target.values()]
        assert len(storage) == 1
    finally:
        await engine.dispose()


@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_storage_reservation_cleanup_preserves_neighbor(
    cleanup_case, monkeypatch,
):
    helper = _helper()
    monkeypatch.setattr(helper, "Settings", lambda: Settings(database_url=cleanup_case.maintenance_url))
    storage_calls = []
    monkeypatch.setattr(helper, "_remove_storage_prefix", lambda _settings, prefix:
        (storage_calls.append(prefix) or (2, 0)))
    engine = create_async_engine(cleanup_case.owner_url)
    run_id = "cleanup-storage-reservations"
    try:
        async with engine.begin() as conn:
            target = await _storage_graph(conn, await _graph(conn, run_id))
            neighbor = await _storage_graph(conn, await _graph(conn, "storage-neighbor", ordinary=True))
            before = await _snapshot(conn)
            before_storage = {
                table: (await conn.execute(text(f"select * from {table} order by id"))).all()
                for table in ("track_artifacts", "storage_reservations")
            }
        # Reproduce the old ordering on the real FK, then prove the complete
        # transaction rolls back and does not start object-storage cleanup.
        original_delete = helper._delete_statement

        async def old_order(conn, tables, table, sql, params):
            if table == "storage_reservations" and "meeting_id" in params:
                return 0
            return await original_delete(conn, tables, table, sql, params)

        monkeypatch.setattr(helper, "_delete_statement", old_order)
        with pytest.raises(IntegrityError) as failure:
            await helper.cleanup_smoke_artifacts(run_id)
        assert failure.value.orig.sqlstate == "23503"
        assert "fk_storage_reservations_artifact_id_track_artifacts" in str(failure.value.orig)
        assert storage_calls == []
        async with engine.connect() as conn:
            assert await _snapshot(conn) == before
            for table, rows in before_storage.items():
                assert (await conn.execute(text(f"select * from {table} order by id"))).all() == rows
        monkeypatch.setattr(helper, "_delete_statement", original_delete)
        removed, objects, residue = await helper.cleanup_smoke_artifacts(run_id)
        async with engine.connect() as conn:
            after = await _snapshot(conn)
            for table, rows in after.items():
                assert rows == [row for row in before[table] if row[0] not in target.values()]
            for table, rows in before_storage.items():
                remaining = (await conn.execute(text(f"select * from {table} order by id"))).all()
                assert remaining == [row for row in rows if row[0] in neighbor.values()]
        assert removed == sum(map(len, before.values())) - sum(map(len, after.values())) + 3
        assert (objects, residue) == (2, [])
        assert storage_calls == [helper._smoke_storage_prefix({
            "organization_id": str(build_smoke_identity_seed(run_id).organization_id),
            "workspace_id": str(target["workspace"]),
        })]
    finally:
        await engine.dispose()


@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_artifact_parent_lock_blocks_late_reservation_insert(
    cleanup_case, monkeypatch,
):
    helper = _helper()
    engine = create_async_engine(cleanup_case.owner_url)
    at_reservations, insert_blocked = asyncio.Event(), asyncio.Event()
    original_delete = helper._delete_statement

    async def delete(conn, tables, table, sql, params):
        if table == "storage_reservations":
            at_reservations.set()
            await asyncio.wait_for(insert_blocked.wait(), 5)
        return await original_delete(conn, tables, table, sql, params)

    monkeypatch.setattr(helper, "_delete_statement", delete)
    try:
        async with engine.begin() as conn:
            target = await _storage_graph(conn, await _graph(conn, "artifact-lock"))
            neighbor = await _storage_graph(conn, await _graph(conn, "artifact-lock-neighbor", ordinary=True))
            before = await _snapshot(conn)
            neighbor_storage = {
                table: (await conn.execute(text(
                    f"select * from {table} where workspace_id=:workspace order by id"
                ), neighbor)).all()
                for table in ("track_artifacts", "storage_reservations")
            }

        async def writer():
            # Deliberately use a different workspace: its parent is not locked
            # by meeting cleanup, so only the artifact FK can block this INSERT.
            async with engine.begin() as conn:
                pid = await conn.scalar(text("select pg_backend_pid()"))
                await asyncio.wait_for(at_reservations.wait(), 5)
                pending = asyncio.create_task(_insert(conn, models.StorageReservation, id=uuid4(),
                    workspace_id=neighbor["workspace"], artifact_id=target["artifact"],
                    idempotency_key=uuid4().hex, declared_bytes=2))
                try:
                    async with engine.connect() as observer:
                        for _ in range(100):
                            if await observer.scalar(text("select cardinality(pg_blocking_pids(:pid))"), {"pid": pid}):
                                insert_blocked.set()
                                break
                            await asyncio.sleep(.01)
                        else:
                            pytest.fail("late reservation INSERT did not block on artifact parent")
                    with pytest.raises(IntegrityError) as failure:
                        await asyncio.wait_for(pending, 5)
                    assert failure.value.orig.sqlstate == "23503"
                    assert "fk_storage_reservations_artifact_id_track_artifacts" in str(failure.value.orig)
                finally:
                    if not pending.done():
                        pending.cancel()
                    await asyncio.gather(pending, return_exceptions=True)

        writer_task = asyncio.create_task(writer())
        try:
            async with cleanup_case.maintenance.begin() as conn:
                await apply_tenant_context_to_connection(conn, helper._maintenance_context())
                available = await helper._available_tables(conn, set(models.Meeting.metadata.tables))
                removed = await helper._delete_smoke_meeting_rows(
                    conn, meeting_id=str(target["meeting"]), session_ids=[],
                    available_tables=available, processing_dependency_has_revision=True,
                )
            await asyncio.wait_for(writer_task, 5)
        finally:
            if not writer_task.done():
                writer_task.cancel()
            await asyncio.gather(writer_task, return_exceptions=True)
        assert insert_blocked.is_set()
        assert removed == 6  # meeting, revision, workflow, job, artifact, linked reservation
        async with engine.connect() as conn:
            after = await _snapshot(conn)
            for table, rows in after.items():
                deleted = {target["meeting"], target["revision"], target["workflow"], target["job"]}
                assert rows == [row for row in before[table] if row[0] not in deleted]
            for table, rows in neighbor_storage.items():
                assert (await conn.execute(text(
                    f"select * from {table} where workspace_id=:workspace order by id"
                ), neighbor)).all() == rows
            assert await conn.scalar(text(
                "select count(*) from storage_reservations where id=:unbound"
            ), target) == 1
            assert await conn.scalar(text(
                "select count(*) from storage_reservations where id=:reservation"
            ), target) == 0
    finally:
        await engine.dispose()


async def _graph(conn, run_id, *, ordinary=False):
    seed = build_smoke_identity_seed(run_id)
    p = dict(org=seed.organization_id, workspace=seed.workspace_id, user=seed.user_id,
             device=seed.device_id, meeting=uuid4(), revision=uuid4(), workflow=uuid4(), job=uuid4())
    prefix = "ordinary" if ordinary else "internal-smoke"
    await _insert(conn, models.Organization, id=p["org"], slug=f"{prefix}-org-{run_id}", name="Synthetic")
    await _insert(conn, models.Workspace, id=p["workspace"], organization_id=p["org"],
                  slug=f"{prefix}-workspace-{run_id}", name="Synthetic")
    await _insert(conn, models.UserIdentity, id=p["user"], organization_id=p["org"], external_subject=str(p["user"]))
    await _insert(conn, models.RegisteredDevice, id=p["device"], workspace_id=p["workspace"],
                  user_id=p["user"], device_public_id=f"{prefix}-{run_id}")
    await _insert(conn, models.WorkspaceMembership, workspace_id=p["workspace"], user_id=p["user"], role="owner")
    await _insert(conn, models.Meeting, id=p["meeting"], workspace_id=p["workspace"],
                  created_by_user_id=p["user"], device_id=p["device"], local_recording_id=run_id, duration_seconds=1)
    await _insert(conn, models.MediaRevision, id=p["revision"], workspace_id=p["workspace"],
                  meeting_id=p["meeting"], local_media_revision_id=run_id)
    await _insert(conn, models.ProcessingWorkflow, id=p["workflow"], workspace_id=p["workspace"],
                  meeting_id=p["meeting"], media_revision_id=p["revision"], workflow_id=run_id)
    await _insert(conn, models.MediaScribeJob, id=p["job"], workspace_id=p["workspace"],
                  meeting_id=p["meeting"], media_revision_id=p["revision"], processing_workflow_id=p["workflow"])
    return p


async def _snapshot(conn):
    result = {}
    for table in TABLES:
        rows = await conn.execute(text("select * from " + table + " order by 1"))
        result[table] = sorted(map(tuple, rows.fetchall()))
    return result


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("foreign_workspace", [False, True])
async def test_interrupted_cleanup_preserves_protected_history_before_storage(
    cleanup_case, monkeypatch, foreign_workspace,
):
    from tests.integration.test_billing_fair_use_operator import CONTEXT, CREATE, declare_operator

    helper = _helper()
    run_id = "forward-" + "b" * 32
    monkeypatch.setattr(helper, "Settings", lambda: Settings(database_url=cleanup_case.maintenance_url))
    storage_calls = []
    monkeypatch.setattr(helper, "_remove_storage_prefix", lambda *args: storage_calls.append(args))
    async with cleanup_case.owner.begin() as conn:
        target = await _graph(conn, run_id)
        neighbor = await _graph(conn, "protected-neighbor", ordinary=True)
        key = helper._smoke_storage_prefix({
            "organization_id": target["org"], "workspace_id": target["workspace"],
        }) + f"meetings/{target['meeting']}/pending-part"
        await _insert(conn, models.PurgeJournal, id=uuid4(), workspace_id=target["workspace"],
                      meeting_id=target["meeting"], artifact_class="object_store", object_key=key)
    async with cleanup_case.maintenance.begin() as conn:
        await apply_tenant_context_to_connection(conn, CONTEXT)
        await declare_operator(conn)
        await conn.execute(text(CREATE), {
            "id": uuid4(), "workspace": neighbor["workspace"] if foreign_workspace else target["workspace"],
            "subject": target["user"], "evidence": "incident:synthetic-cleanup",
            "start": datetime.now(UTC), "deadline": datetime.now(UTC) + timedelta(hours=24),
        })

    async def snapshot():
        async with cleanup_case.owner.connect() as conn:
            return await _snapshot(conn), {
                table: (await conn.execute(text(f"SELECT * FROM {table} ORDER BY id"))).all()
                for table in ("meeting_purge_journal", "fair_use_reviews", "billing_audit_events")
            }

    before = await snapshot()
    assert await helper.cleanup_smoke_artifacts(run_id, reconcile_interrupted=True) == (
        0, 0, ["protected_fair_use_history"],
    )
    assert storage_calls == []
    assert await snapshot() == before


@pytest.mark.asyncio
async def test_history_read_error_refuses_interrupted_cleanup_before_effects(monkeypatch):
    helper = _helper()
    calls = []

    class Connection:
        dialect = SimpleNamespace(name="postgresql")

        async def execute(self, statement, *args):
            calls.append(str(statement))
            raise DBAPIError(None, None, _DatabaseFailure("42501"))

    class Engine:
        @asynccontextmanager
        async def begin(self):
            yield Connection()

        async def dispose(self):
            calls.append("disposed")

    async def context(*_args):
        pass

    monkeypatch.setattr(helper, "create_async_engine", lambda _url: Engine())
    monkeypatch.setattr(helper, "apply_tenant_context_to_connection", context)
    monkeypatch.setattr(helper, "_remove_storage_prefix", lambda *_args: pytest.fail("storage effect"))
    result = await helper.cleanup_smoke_artifacts("forward-" + "c" * 32, reconcile_interrupted=True)
    assert result == (0, 0, ["protected_fair_use_history"])
    assert len(calls) == 2 and "SELECT session_user" in calls[0] and calls[1] == "disposed"


def _assert_committed_before_storage(database_url, workspace):
    async def probe():
        engine = create_async_engine(database_url)
        try:
            async with engine.connect() as conn:
                # A separate backend would still see these rows before commit.
                assert await conn.scalar(text("select count(*) from workspaces where id=:id"),
                                         {"id": workspace}) == 0
                assert await conn.scalar(text("select count(*) from processing_workflows where workspace_id=:id"),
                                         {"id": workspace}) == 0
        finally:
            await engine.dispose()

    # The production storage callback is synchronous. A separate test loop keeps
    # this real DB observation independent of cleanup's connection/transaction.
    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(asyncio.run, probe()).result(timeout=5)


@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_real_deadlock_retries_exact_cleanup_and_preserves_neighbor(
    cleanup_case, monkeypatch,
):
    helper = _helper()
    settings = Settings(database_url=cleanup_case.maintenance_url)
    monkeypatch.setattr(helper, "Settings", lambda: settings)
    # The cleanup backend detects the cycle first; the writer cannot win a timeout race.
    async with cleanup_case.owner.begin() as conn:
        await conn.execute(text("ALTER ROLE twobrain_rec_maintenance SET deadlock_timeout='50ms'"))
    engine = create_async_engine(cleanup_case.owner_url,
        connect_args={"server_settings": {"deadlock_timeout": "10s"}})
    run_id = "cleanup-fk-contention"
    locked, cleanup_ready, insert_blocked = asyncio.Event(), asyncio.Event(), asyncio.Event()
    contexts, deleted_workflows, storage_calls = [], [], []
    original_context = helper.apply_tenant_context_to_connection
    original_delete = helper._delete_statement

    async def context(conn, value):
        contexts.append(type(value).__name__)
        await original_context(conn, value)

    async def delete(conn, tables, table, sql, params):
        if table == "processing_workflows":
            deleted_workflows.append(True)
            if len(deleted_workflows) == 1:
                cleanup_ready.set()
                await asyncio.wait_for(insert_blocked.wait(), 5)
        return await original_delete(conn, tables, table, sql, params)

    monkeypatch.setattr(helper, "apply_tenant_context_to_connection", context)
    monkeypatch.setattr(helper, "_delete_statement", delete)
    def storage(_settings, prefix):
        _assert_committed_before_storage(cleanup_case.owner_url, target["workspace"])
        storage_calls.append(prefix)
        return 2, 0

    monkeypatch.setattr(helper, "_remove_storage_prefix", storage)
    try:
        async with engine.begin() as conn:
            target = await _graph(conn, run_id)
            await _graph(conn, "neighbor", ordinary=True)
            before = await _snapshot(conn)

        async def writer():
            async with engine.begin() as conn:
                pid = await conn.scalar(text("select pg_backend_pid()"))
                await conn.execute(text("select id from processing_workflows where id=:workflow for update"), target)
                locked.set()
                await asyncio.wait_for(cleanup_ready.wait(), 5)
                async def insert():
                    await _insert(conn, models.ProcessingResult, id=uuid4(), meeting_id=target["meeting"],
                                  workspace_id=target["workspace"], mediascribe_job_id=target["job"],
                                  processing_workflow_id=target["workflow"], media_revision_id=target["revision"])
                pending = asyncio.create_task(insert())
                try:
                    async with engine.connect() as observer:
                        for _ in range(100):
                            if await observer.scalar(text("select cardinality(pg_blocking_pids(:pid))"), {"pid": pid}):
                                insert_blocked.set()
                                break
                            await asyncio.sleep(.01)
                        else:
                            pytest.fail("synthetic INSERT did not block on cleanup FK locks")
                    await asyncio.wait_for(pending, 5)
                finally:
                    if not pending.done():
                        pending.cancel()
                    await asyncio.gather(pending, return_exceptions=True)

        writer_task = asyncio.create_task(writer())
        try:
            await asyncio.wait_for(locked.wait(), 5)
            removed, objects, residue = await asyncio.wait_for(helper.cleanup_smoke_artifacts(run_id), 10)
            await asyncio.wait_for(writer_task, 5)
        finally:
            if not writer_task.done():
                writer_task.cancel()
            await asyncio.gather(writer_task, return_exceptions=True)
        async with engine.connect() as conn:
            after = await _snapshot(conn)
        # The writer committed one extra result after cleanup's first transaction rolled back.
        assert removed == sum(map(len, before.values())) + 1 - sum(map(len, after.values()))
        assert objects == 2 and residue == []
        assert len(deleted_workflows) == 2
        assert contexts.count("TenantDatabaseContext") == 2
        assert storage_calls == [helper._smoke_storage_prefix({
            "organization_id": str(build_smoke_identity_seed(run_id).organization_id),
            "workspace_id": str(target["workspace"]),
        })]
        for table, rows in after.items():
            assert rows == [row for row in before[table] if row[0] not in target.values()]
    finally:
        await engine.dispose()


class _DatabaseFailure(Exception):
    def __init__(self, sqlstate):
        super().__init__("synthetic database failure")
        self.sqlstate = sqlstate


@pytest.mark.asyncio
@pytest.mark.parametrize("sqlstate, expected_attempts", [("40P01", 3), ("23503", 1)])
async def test_precommit_failures_are_bounded_and_never_touch_storage(
    monkeypatch, sqlstate, expected_attempts,
):
    helper = _helper()
    created, disposed, storage, delays = [], [], [], []

    class Engine:
        @asynccontextmanager
        async def begin(self):
            raise DBAPIError(None, None, _DatabaseFailure(sqlstate))
            yield  # pragma: no cover

        async def dispose(self):
            disposed.append(self)

    def engine(_url):
        instance = Engine()
        created.append(instance)
        return instance

    async def pause(seconds):
        assert len(disposed) == len(created), "failed transaction must close before backoff"
        delays.append(seconds)

    monkeypatch.setattr(helper, "create_async_engine", engine)
    monkeypatch.setattr(helper.asyncio, "sleep", pause)
    monkeypatch.setattr(helper, "_remove_storage_prefix", lambda *args: storage.append(args))
    with pytest.raises((DBAPIError, RuntimeError)):
        await helper.cleanup_smoke_artifacts("bounded-fixture")
    assert len(created) == expected_attempts
    assert disposed == created
    assert storage == []
    assert delays == ([.1, .3] if sqlstate == "40P01" else [])


@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_postcommit_deadlock_is_not_retried_or_reported_as_success(
    cleanup_case, monkeypatch,
):
    helper = _helper()
    monkeypatch.setattr(helper, "Settings", lambda: Settings(database_url=cleanup_case.maintenance_url))
    engine = create_async_engine(cleanup_case.owner_url)
    attempts, storage = [], []

    def cleanup_engine(url):
        attempts.append(url)
        return create_async_engine(url)

    async def residue(*_args):
        raise DBAPIError(None, None, _DatabaseFailure("40P01"))

    monkeypatch.setattr(helper, "create_async_engine", cleanup_engine)
    monkeypatch.setattr(helper, "_database_residue", residue)
    monkeypatch.setattr(helper, "_remove_storage_prefix", lambda _settings, prefix:
        (storage.append(prefix) or (2, 0)))
    try:
        async with engine.begin() as conn:
            await _graph(conn, "postcommit-fixture")
        with pytest.raises(DBAPIError):
            await helper.cleanup_smoke_artifacts("postcommit-fixture")
        assert len(attempts) == len(storage) == 1
        async with engine.connect() as conn:
            assert all(not rows for rows in (await _snapshot(conn)).values())
    finally:
        await engine.dispose()
