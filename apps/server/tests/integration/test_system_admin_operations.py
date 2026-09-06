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
    url = make_url(db["url"]).set(username="twobrain_rec_maintenance", password=password)
    return await asyncpg.connect(url.render_as_string(hide_password=False).replace("+asyncpg", ""))


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
