"""Real FK contention on disposable PostgreSQL, never production fixtures."""

from __future__ import annotations

import asyncio
import importlib.util
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from twobrain_rec_server.config import Settings
from twobrain_rec_server.deployment import build_smoke_identity_seed


def _helper():
    path = Path(__file__).resolve().parents[2] / "scripts/cleanup_smoke_artifacts.py"
    spec = importlib.util.spec_from_file_location("cleanup_deadlock_subject", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DDL = (
    "create table organizations(id uuid primary key, slug text)",
    "create table workspaces(id uuid primary key, organization_id uuid references organizations, slug text)",
    "create table user_identities(id uuid primary key, organization_id uuid references organizations)",
    "create table registered_devices(id uuid primary key, workspace_id uuid references workspaces, user_id uuid references user_identities, device_public_id text)",
    "create table workspace_memberships(workspace_id uuid references workspaces, user_id uuid references user_identities)",
    "create table meetings(id uuid primary key, workspace_id uuid references workspaces, created_by_user_id uuid references user_identities, device_id uuid references registered_devices)",
    "create table upload_sessions(id uuid primary key, meeting_id uuid references meetings)",
    "create table media_revisions(id uuid primary key, meeting_id uuid references meetings, workspace_id uuid references workspaces)",
    "create table processing_workflows(id uuid primary key, meeting_id uuid references meetings, workspace_id uuid references workspaces, media_revision_id uuid references media_revisions)",
    "create table processing_results(id uuid primary key, meeting_id uuid references meetings, workspace_id uuid references workspaces, processing_workflow_id uuid references processing_workflows, media_revision_id uuid references media_revisions)",
    "create table processing_dependency_states(meeting_id uuid references meetings, media_revision_id uuid references media_revisions)",
)

STORAGE_DDL = (
    "create table track_artifacts(id uuid primary key, meeting_id uuid references meetings, workspace_id uuid references workspaces)",
    "create table storage_reservations(id uuid primary key, workspace_id uuid references workspaces, artifact_id uuid constraint fk_storage_reservations_artifact_id_track_artifacts references track_artifacts)",
)


async def _storage_graph(conn, graph):
    graph = graph | {"artifact": uuid4(), "reservation": uuid4(), "unbound": uuid4()}
    await conn.execute(text("insert into track_artifacts values (:artifact, :meeting, :workspace)"), graph)
    await conn.execute(text("insert into storage_reservations values (:reservation, :workspace, :artifact)"), graph)
    await conn.execute(text("insert into storage_reservations values (:unbound, :workspace, null)"), graph)
    return graph


@pytest.mark.asyncio
async def test_storage_reservation_cleanup_preserves_neighbor(
    postgres_clean_database_url, monkeypatch,
):
    helper = _helper()
    monkeypatch.setattr(helper, "Settings", lambda: Settings(database_url=postgres_clean_database_url))
    storage_calls = []
    monkeypatch.setattr(helper, "_remove_storage_prefix", lambda _settings, prefix:
        (storage_calls.append(prefix) or (2, 0)))
    engine = create_async_engine(postgres_clean_database_url)
    run_id = "cleanup-storage-reservations"
    try:
        async with engine.begin() as conn:
            for sql in (*DDL, *STORAGE_DDL):
                await conn.execute(text(sql))
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


@pytest.mark.asyncio
async def test_artifact_parent_lock_blocks_late_reservation_insert(
    postgres_clean_database_url, monkeypatch,
):
    helper = _helper()
    engine = create_async_engine(postgres_clean_database_url)
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
            for sql in (*DDL, *STORAGE_DDL):
                await conn.execute(text(sql))
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
                pending = asyncio.create_task(conn.execute(text(
                    "insert into storage_reservations values (:id, :workspace, :artifact)"
                ), {"id": uuid4(), "workspace": neighbor["workspace"], "artifact": target["artifact"]}))
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
            async with engine.begin() as conn:
                available = await helper._available_tables(conn, {
                    sql.split()[2].split("(")[0] for sql in (*DDL, *STORAGE_DDL)
                })
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
        assert removed == 5  # meeting, revision, workflow, artifact, linked reservation
        async with engine.connect() as conn:
            after = await _snapshot(conn)
            for table, rows in after.items():
                deleted = {target["meeting"], target["revision"], target["workflow"]}
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
    params = dict(org=seed.organization_id, workspace=seed.workspace_id, user=seed.user_id,
                  device=seed.device_id, meeting=uuid4(), revision=uuid4(), workflow=uuid4())
    prefix = "ordinary" if ordinary else "internal-smoke"
    statements = (
        ("insert into organizations values (:org, :slug)", {"slug": prefix + "-org-" + run_id}),
        ("insert into workspaces values (:workspace, :org, :slug)", {"slug": prefix + "-workspace-" + run_id}),
        ("insert into user_identities values (:user, :org)", {}),
        ("insert into registered_devices values (:device, :workspace, :user, :public)", {"public": prefix + "-" + run_id}),
        ("insert into workspace_memberships values (:workspace, :user)", {}),
        ("insert into meetings values (:meeting, :workspace, :user, :device)", {}),
        ("insert into media_revisions values (:revision, :meeting, :workspace)", {}),
        ("insert into processing_workflows values (:workflow, :meeting, :workspace, :revision)", {}),
    )
    for sql, extra in statements:
        await conn.execute(text(sql), params | extra)
    return params


async def _snapshot(conn):
    result = {}
    for sql in DDL:
        table = sql.split()[2].split("(")[0]
        rows = await conn.execute(text("select * from " + table + " order by 1"))
        result[table] = sorted(map(tuple, rows.fetchall()))
    return result


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


@pytest.mark.asyncio
async def test_real_deadlock_retries_exact_cleanup_and_preserves_neighbor(
    postgres_clean_database_url, monkeypatch,
):
    helper = _helper()
    settings = Settings(database_url=postgres_clean_database_url)
    monkeypatch.setattr(helper, "Settings", lambda: settings)
    # The cleanup backend detects the cycle first; the writer cannot win a timeout race.
    monkeypatch.setattr(helper, "create_async_engine", lambda url: create_async_engine(
        url, connect_args={"server_settings": {"deadlock_timeout": "50ms"}},
    ))
    engine = create_async_engine(postgres_clean_database_url,
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
        _assert_committed_before_storage(postgres_clean_database_url, target["workspace"])
        storage_calls.append(prefix)
        return 2, 0

    monkeypatch.setattr(helper, "_remove_storage_prefix", storage)
    try:
        async with engine.begin() as conn:
            for sql in DDL:
                await conn.execute(text(sql))
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
                    await conn.execute(text("insert into processing_results values (:result, :meeting, :workspace, :workflow, :revision)"), target | {"result": uuid4()})
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


@pytest.mark.asyncio
async def test_postcommit_deadlock_is_not_retried_or_reported_as_success(
    postgres_clean_database_url, monkeypatch,
):
    helper = _helper()
    monkeypatch.setattr(helper, "Settings", lambda: Settings(database_url=postgres_clean_database_url))
    engine = create_async_engine(postgres_clean_database_url)
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
            for sql in DDL:
                await conn.execute(text(sql))
            await _graph(conn, "postcommit-fixture")
        with pytest.raises(DBAPIError):
            await helper.cleanup_smoke_artifacts("postcommit-fixture")
        assert len(attempts) == len(storage) == 1
        async with engine.connect() as conn:
            assert all(not rows for rows in (await _snapshot(conn)).values())
    finally:
        await engine.dispose()
