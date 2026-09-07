"""Actual DB identities exercise preview, idempotency and effect fences."""

import json
from uuid import UUID, uuid4

import asyncpg
import pytest
from sqlalchemy.engine import make_url

from tests.integration import test_system_admin_security as security

system_database = security.system_database
pytestmark = pytest.mark.strict_rls


async def _command(db, connection, *, kind="meeting.reprocess", target=None):
    target = target or await db["owner"].fetchval("select id from meetings limit 1")
    version = await db["owner"].fetchval("select control_version from meetings where id=$1", target)
    permission = "processing.reprocess" if kind == "meeting.reprocess" else "deletion.manage"
    await security._context(connection, db, **{"app.system_permission": permission})
    command = dict(kind=kind, target_id=str(target), expected_version=version, reason="Synthetic test")
    preview = json.loads(await connection.fetchval(
        "select system_control.preview_meeting_operation($1::jsonb)", json.dumps(command),
    ))
    assert "error" not in preview, preview
    return target, preview


async def _commit(connection, preview, key=None):
    return json.loads(await connection.fetchval(
        "select system_control.commit_operation($1,$2,$3)",
        UUID(preview["preview_id"]), preview["effect_hash"], key or uuid4(),
    ))


async def _worker(db):
    password = uuid4().hex
    quoted = await db["owner"].fetchval("select quote_literal($1::text)", password)
    await db["owner"].execute(f"alter role twobrain_rec_maintenance login password {quoted}")
    # Match the production bootstrap; RLS still requires the maintenance context.
    await db["owner"].execute("grant usage on schema public to twobrain_rec_maintenance")
    await db["owner"].execute(
        "grant select,insert,update,delete on all tables in schema public to twobrain_rec_maintenance"
    )
    url = make_url(db["url"]).set(username="twobrain_rec_maintenance", password=password)
    db["worker_url"] = url.render_as_string(hide_password=False)
    return await asyncpg.connect(db["worker_url"].replace("+asyncpg", ""))


@pytest.mark.asyncio
async def test_preview_commit_repeat_and_version_conflict(system_database):
    db = system_database
    conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        async with conn.transaction():
            target, preview = await _command(db, conn)
            key = uuid4()
            operation = await _commit(conn, preview, key)
            assert operation["state"] == "queued"
            assert await _commit(conn, preview, key) == operation
            assert (await _commit(conn, preview))["error"] == "preview_consumed"
        assert await db["owner"].fetchval("select count(*) from system_control.operations") == 1
        assert await db["owner"].fetchval(
            "select count(*) from system_control.audit_events where action='command.commit'",
        ) == 1
        async with conn.transaction():
            _, preview = await _command(db, conn, target=target)
            await db["owner"].execute("update meetings set status='ready' where id=$1", target)
            assert (await _commit(conn, preview))["error"] == "version_conflict"
        assert await db["owner"].fetchval("select count(*) from system_control.operations") == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_worker_claim_and_continuation_after_revoke(system_database):
    db = system_database
    conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    worker = await _worker(db)
    try:
        async with conn.transaction():
            target, preview = await _command(db, conn)
            operation = await _commit(conn, preview)
        operation_id = UUID(operation["operation_id"])
        for connection in (conn, worker):
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await connection.fetch("select * from system_control.operations")
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.fetchval("select system_control.claim_system_operation($1,$2)", operation_id, target)
        claim = json.loads(await worker.fetchval(
            "select system_control.claim_system_operation($1,$2)", operation_id, target,
        ))
        assert claim["mode"] == "start"
        assert await worker.fetchval(
            "select system_control.claim_system_operation($1,$2)", operation_id, target,
        ) is None
        await db["owner"].execute("update system_control.sessions set revoked_at=now()")
        args = (operation_id, target, claim["attempt_fence"], UUID(claim["domain_ref"]))
        query = "select system_control.continue_system_operation($1,$2,$3,$4,$5)"
        assert json.loads(await worker.fetchval(query, *args, "reconcile"))["mode"] == "reconcile"
        for action in ("start", "delete", "send", None):
            assert await worker.fetchval(query, *args, action) is None
        assert await worker.fetchval(query, operation_id, uuid4(), *args[2:], "reconcile") is None
        assert await worker.fetchval(query, operation_id, target, 999, args[3], "reconcile") is None
        result = "select system_control.record_system_operation_result($1,$2,$3,$4,$5)"
        assert await worker.fetchval(result, *args, "succeeded")
        assert await worker.fetchval(result, *args, "succeeded")
        assert not await worker.fetchval(result, *args, "failed")
        assert await worker.fetchval(query, *args, "reconcile") is None
    finally:
        await conn.close()
        await worker.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("change,expected", [
    ("update system_control.sessions set revoked_at=now()", "cancelled"),
    ("update system_control.principals set auth_version=2", "cancelled"),
    ("update system_control.role_assignments set version=2", "cancelled"),
    ("update meetings set status='ready'", "failed"),
])
async def test_revocation_or_changed_target_prevents_effect(system_database, change, expected):
    db = system_database
    conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    worker = await _worker(db)
    try:
        async with conn.transaction():
            target, preview = await _command(db, conn)
            operation = await _commit(conn, preview)
        await db["owner"].execute(change)
        assert await worker.fetchval(
            "select system_control.claim_system_operation($1,$2)", UUID(operation["operation_id"]), target,
        ) is None
        row = await db["owner"].fetchrow("select state,effect_started_at from system_control.operation_targets")
        assert row["state"] == expected
        assert row["effect_started_at"] is None
    finally:
        await conn.close()
        await worker.close()


@pytest.mark.asyncio
async def test_unknown_parameters_and_delete_permission_fail_closed(system_database):
    db = system_database
    conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        async with conn.transaction():
            target, _ = await _command(db, conn)
            command = dict(kind="meeting.delete", target_id=str(target), expected_version=1, reason="Test")
            await security._context(conn, db, **{"app.system_permission": "deletion.manage"})
            query = "select system_control.preview_meeting_operation($1::jsonb)"
            assert json.loads(await conn.fetchval(query, json.dumps(command)))["error"] == "access_denied"
            command["callback"] = "https://example.invalid"
            assert json.loads(await conn.fetchval(query, json.dumps(command)))["error"] == "invalid_command"
        assert await db["owner"].fetchval(
            "select count(*) from system_control.audit_events where action='command.denied'",
        ) == 2
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_domain_effect_is_bound_to_claim_and_resumed_without_changing_actor(system_database):
    db = system_database
    conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    worker = await _worker(db)
    try:
        async with conn.transaction():
            target, preview = await _command(db, conn)
            operation = await _commit(conn, preview)
        operation_id = UUID(operation["operation_id"])
        workspace = await db["owner"].fetchval("select workspace_id from meetings where id=$1", target)
        async with worker.transaction():
            claim = json.loads(await worker.fetchval("select system_control.claim_system_operation($1,$2)", operation_id, target))
            for key,value in {"app.context_kind":"maintenance","app.maintenance_operation":"processing_recovery_reconciliation",
                              "app.maintenance_actor":"synthetic-worker","app.maintenance_reason":"synthetic-test",
                              "app.maintenance_feature_area":"system-admin"}.items():
                await worker.execute("select set_config($1,$2,true)", key, value)
            insert = """insert into processing_workflows(id,system_operation_id,workspace_id,meeting_id,workflow_id)
                values($1,$2,$3,$4,$5)"""
            with pytest.raises(asyncpg.InsufficientPrivilegeError, match="claimed system operation"):
                async with worker.transaction():
                    await worker.execute(insert, uuid4(), operation_id, workspace, target, "synthetic-wrong-reference")
            domain = UUID(claim["domain_ref"])
            await worker.execute(insert, domain, operation_id, workspace, target, "synthetic-exact-reference")
        await db["owner"].execute("update system_control.sessions set revoked_at=now()")
        resume = json.loads(await worker.fetchval("select system_control.resume_system_operation($1,$2)", operation_id, target))
        assert resume["actor_id"] == str(db["actor"])
        assert resume["domain_ref"] == str(domain)
        assert resume["mode"] == "observe"
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.fetchval("select system_control.resume_system_operation($1,$2)", operation_id, target)
        with pytest.raises(asyncpg.InsufficientPrivilegeError, match="immutable"):
            await db["owner"].execute("update processing_workflows set system_operation_id=null where id=$1", domain)
    finally:
        await conn.close()
        await worker.close()


@pytest.mark.asyncio
async def test_dispatcher_records_rejected_admission_without_domain_effect(system_database, test_settings):
    from sqlalchemy.ext.asyncio import create_async_engine

    from tests.fakes.fake_temporal import FakeTemporalClient
    from twobrain_rec_server.db.session import create_sessionmaker
    from twobrain_rec_server.system_admin.worker import execute_operation

    db = system_database
    worker = await _worker(db)
    await worker.close()
    engine = create_async_engine(db["worker_url"])
    conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        async with conn.transaction():
            target, preview = await _command(db, conn)
            operation = await _commit(conn, preview)
        async with create_sessionmaker(engine)() as session:
            await execute_operation(session, operation_id=UUID(operation["operation_id"]),
                target_id=target, settings=test_settings, temporal_client=FakeTemporalClient(), storage=None)
        assert await db["owner"].fetchval("select state from system_control.operations") == "failed"
        assert await db["owner"].fetchval("select count(*) from processing_workflows") == 0
    finally:
        await conn.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_dispatcher_commits_deletion_with_real_system_actor(system_database, test_settings):
    from sqlalchemy.ext.asyncio import create_async_engine

    from tests.fakes.fake_minio import FakeMinioStorage
    from tests.fakes.fake_temporal import FakeTemporalClient
    from twobrain_rec_server.db.session import create_sessionmaker
    from twobrain_rec_server.system_admin.worker import execute_operation

    db = system_database
    await db["owner"].execute("update system_control.role_assignments set role='superadmin'")
    worker = await _worker(db)
    await worker.close()
    engine = create_async_engine(db["worker_url"])
    conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        async with conn.transaction():
            target, preview = await _command(db, conn, kind="meeting.delete")
            operation = await _commit(conn, preview)
        operation_id = UUID(operation["operation_id"])
        for attempt in range(2):
            if attempt:
                await db["owner"].execute("update system_control.sessions set revoked_at=now()")
            async with create_sessionmaker(engine)() as session:
                await execute_operation(session, operation_id=operation_id,
                    target_id=target, settings=test_settings,
                    temporal_client=FakeTemporalClient(), storage=FakeMinioStorage())
        rows = await db["owner"].fetch("select * from meeting_deletion_requests where meeting_id=$1", target)
        assert len(rows) == 1
        assert rows[0]["system_operation_id"] == operation_id
        assert rows[0]["requested_by_user_id"] is None
        assert rows[0]["requested_by_device_id"] is None
        assert await db["owner"].fetchval("select deleted_at is not null from meetings where id=$1", target)
    finally:
        await conn.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_dispatcher_starts_one_real_attempt_and_observes_after_revoke(system_database, client, test_settings):
    from sqlalchemy.ext.asyncio import create_async_engine

    from tests.fakes.fake_temporal import FakeTemporalClient
    from tests.fixtures.processing import create_finalized_meeting
    from tests.integration.test_processing_attempts import _seed_complete_result
    from twobrain_rec_server.db.session import create_sessionmaker
    from twobrain_rec_server.system_admin.worker import execute_operation

    db = system_database
    finalized = create_finalized_meeting(client, "system-reprocess")
    target = UUID(finalized["meeting"]["meeting_id"])
    revision = UUID(finalized["meeting"]["media_revision"]["media_revision_id"])
    workspace = UUID(finalized["meeting"]["workspace_id"])
    await _seed_complete_result(client, workspace_id=workspace, meeting_id=target, media_revision_id=revision)
    worker = await _worker(db)
    await worker.close()
    engine = create_async_engine(db["worker_url"])
    conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    temporal = FakeTemporalClient()
    try:
        async with conn.transaction():
            _, preview = await _command(db, conn, target=target)
            operation = await _commit(conn, preview)
        operation_id = UUID(operation["operation_id"])
        for attempt in range(2):
            if attempt:
                await db["owner"].execute("update system_control.sessions set revoked_at=now()")
            async with create_sessionmaker(engine)() as session:
                await execute_operation(session, operation_id=operation_id, target_id=target,
                    settings=test_settings, temporal_client=temporal, storage=client.app_state["storage"])
        assert len(temporal.starts) == 1, await db["owner"].fetch("select state,error_code from system_control.operation_targets")
        assert await db["owner"].fetchval("select count(*) from processing_workflows where meeting_id=$1", target) == 2
        row = await db["owner"].fetchrow("select * from processing_workflows where system_operation_id=$1", operation_id)
        assert row["attempt_ordinal"] == 2
        assert row["workflow_run_id"] is not None
        assert await db["owner"].fetchval("select count(*) from processing_results where meeting_id=$1", target) == 1
        assert await db["owner"].fetchval("select state from system_control.operations where id=$1", operation_id) == "awaiting_reconciliation"
        await db["owner"].execute("update processing_workflows set status='processed' where id=$1", row["id"])
        async with create_sessionmaker(engine)() as session:
            await execute_operation(session, operation_id=operation_id, target_id=target,
                settings=test_settings, temporal_client=temporal, storage=client.app_state["storage"])
        assert await db["owner"].fetchval("select state from system_control.operations where id=$1", operation_id) == "succeeded"
        assert len(temporal.starts) == 1
    finally:
        await conn.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_crash_before_domain_commit_leaves_command_unclaimed(system_database, test_settings, monkeypatch):
    from sqlalchemy.ext.asyncio import create_async_engine

    from tests.fakes.fake_minio import FakeMinioStorage
    from tests.fakes.fake_temporal import FakeTemporalClient
    from twobrain_rec_server.db.session import create_sessionmaker
    from twobrain_rec_server.system_admin import worker as dispatcher

    db = system_database
    await db["owner"].execute("update system_control.role_assignments set role='superadmin'")
    worker = await _worker(db)
    await worker.close()
    engine = create_async_engine(db["worker_url"])
    conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        async with conn.transaction():
            target, preview = await _command(db, conn, kind="meeting.delete")
            operation = await _commit(conn, preview)
        async def crash(*args, **kwargs):
            raise RuntimeError("synthetic crash before commit")
        monkeypatch.setattr(dispatcher, "request_meeting_deletion", crash)
        with pytest.raises(RuntimeError, match="synthetic crash"):
            async with create_sessionmaker(engine)() as session:
                await dispatcher.execute_operation(session, operation_id=UUID(operation["operation_id"]),
                    target_id=target, settings=test_settings, temporal_client=FakeTemporalClient(), storage=FakeMinioStorage())
        row = await db["owner"].fetchrow("select state,effect_started_at,domain_ref from system_control.operation_targets")
        assert row["state"] == "queued" and row["effect_started_at"] is None and row["domain_ref"] is None
        assert await db["owner"].fetchval("select count(*) from meeting_deletion_requests") == 0
        await db["owner"].execute("update system_control.sessions set revoked_at=now()")
        async with create_sessionmaker(engine)() as session:
            await dispatcher.execute_operation(session, operation_id=UUID(operation["operation_id"]),
                target_id=target, settings=test_settings, temporal_client=FakeTemporalClient(), storage=FakeMinioStorage())
        assert await db["owner"].fetchval("select state from system_control.operations") == "cancelled"
    finally:
        await conn.close()
        await engine.dispose()
