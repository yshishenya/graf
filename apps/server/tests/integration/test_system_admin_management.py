"""Assignment concurrency preserves an indefinite superadministrator."""

import json
from uuid import uuid4

import asyncpg
import pytest

from tests.integration import test_system_admin_security as security

system_database = security.system_database
pytestmark = pytest.mark.strict_rls


@pytest.mark.asyncio
async def test_temporary_admin_cannot_remove_last_indefinite_admin(system_database):
    db = system_database
    owner = db["owner"]
    await owner.execute("update system_control.role_assignments set role='superadmin',expires_at=now()+interval '1 hour'")
    target = uuid4()
    await owner.execute("""insert into system_control.principals(id,normalized_email,status,auth_version)
        values($1,'second@example.invalid','active',1)""", target)
    await owner.execute("""insert into system_control.role_assignments(id,principal_id,role,starts_at)
        values($1,$2,'superadmin',now())""", uuid4(), target)
    conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        async with conn.transaction():
            await security._context(conn, db, **{"app.system_permission": "admins.manage"})
            result = json.loads(await conn.fetchval(
                "select system_control.update_administrator($1,1,'support','blocked',null,'Synthetic reason')", target,
            ))
            assert result["error"] == "last_superadmin"
            own = json.loads(await conn.fetchval(
                "select system_control.update_administrator($1,1,'superadmin','active',null,'Synthetic reason')", db["actor"],
            ))
            assert own["error"] == "access_denied"
        assert await owner.fetchval("select auth_version from system_control.principals where id=$1", target) == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_invitation_has_no_session_and_role_update_revokes_access(system_database):
    db = system_database
    await db["owner"].execute("update system_control.role_assignments set role='superadmin'")
    conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        async with conn.transaction():
            await security._context(conn, db, **{"app.system_permission": "admins.manage"})
            invited = await conn.fetchval(
                "select system_control.invite_administrator('invited@example.invalid','support',null,'Test',$1)", uuid4().hex*2,
            )
            assert invited is not None
        assert await db["owner"].fetchval("select count(*) from system_control.sessions where principal_id=$1", invited) == 0
        async with conn.transaction():
            await security._context(conn, db, **{"app.system_permission": "admins.manage"})
            result = json.loads(await conn.fetchval(
                "select system_control.update_administrator($1,1,'support','active',null,'Test')", invited,
            ))
            assert result["error"] == "enrolment_required"
            result = json.loads(await conn.fetchval(
                "select system_control.update_administrator($1,1,'support','revoked',null,'Test')", invited,
            ))
            assert result["version"] == 2
        assert await db["owner"].fetchval(
            "select count(*) from system_control.challenges where principal_id=$1 and consumed_at is null", invited,
        ) == 0
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_concurrent_last_administrator_removals_are_serialized(system_database):
    import asyncio

    db = system_database
    await db["owner"].execute("update system_control.role_assignments set role='superadmin',expires_at=now()+interval '1 hour'")
    targets = [uuid4(), uuid4()]
    for i, target in enumerate(targets):
        await db["owner"].execute("""insert into system_control.principals(id,normalized_email,status,auth_version)
            values($1,$2,'active',1)""", target, f"race{i}@example.invalid")
        await db["owner"].execute("""insert into system_control.role_assignments(id,principal_id,role,starts_at)
            values($1,$2,'superadmin',now())""", uuid4(), target)

    async def remove(target):
        conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
        try:
            async with conn.transaction():
                await security._context(conn, db, **{"app.system_permission": "admins.manage"})
                return json.loads(await conn.fetchval(
                    "select system_control.update_administrator($1,1,'support','blocked',null,'Race test')", target,
                ))
        finally:
            await conn.close()

    results = await asyncio.gather(*(remove(target) for target in targets))
    assert sum("version" in result for result in results) == 1
    assert sum(result.get("error") == "last_superadmin" for result in results) == 1


@pytest.mark.asyncio
async def test_grant_api_boundary_pins_recipient_assignment_and_object(system_database):
    db=system_database
    await db["owner"].execute("update system_control.role_assignments set role='superadmin'")
    target=uuid4()
    assignment=uuid4()
    await db["owner"].execute("insert into system_control.principals(id,normalized_email,status,auth_version) values($1,'grantee@example.invalid','active',1)",target)
    await db["owner"].execute("insert into system_control.role_assignments(id,principal_id,role,starts_at) values($1,$2,'support',now())",assignment,target)
    meeting=await db["owner"].fetchval("select id from meetings limit 1")
    conn=await asyncpg.connect(db["url"].replace("+asyncpg",""))
    try:
        async with conn.transaction():
            await security._context(conn,db,**{"app.system_permission":"admins.manage"})
            query="select system_control.create_administrator_grant($1,1,$2,'meeting',$3,now()+interval '1 hour','Synthetic grant')"
            denied=json.loads(await conn.fetchval(query,target,"admins.manage",meeting))
            assert denied["error"]=="permission_not_grantable"
            grant=json.loads(await conn.fetchval(query,target,"content.read",meeting))
            assert grant["version"]==1
        row=await db["owner"].fetchrow("select assignment_id,assignment_version,target_id from system_control.permission_grants")
        assert row["assignment_id"]==assignment
        assert row["assignment_version"]==1
        assert row["target_id"]==meeting
        async with conn.transaction():
            await security._context(conn,db,**{"app.system_permission":"admins.manage"})
            from uuid import UUID
            result=json.loads(await conn.fetchval("select system_control.revoke_administrator_grant($1,1,'Synthetic revoke')",UUID(grant["id"])))
            assert result["version"]==2
        assert await db["owner"].fetchval("select revoked_at from system_control.permission_grants") is not None
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_invitation_delivery_is_durable_and_replacement_revokes_old_link(system_database):
    db = system_database
    await db["owner"].execute("update system_control.role_assignments set role='superadmin'")
    conn = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    old_hash, new_hash = uuid4().hex*2, uuid4().hex*2
    try:
        async with conn.transaction():
            await security._context(conn, db, **{"app.system_permission":"admins.manage"})
            principal = await conn.fetchval("select system_control.invite_administrator('delivery@example.invalid','support',null,'Synthetic delivery',$1)", old_hash)
        assert not await conn.fetchval("select system_control.auth_delivery($1,'submitted')", old_hash)
        assert await conn.fetchval("select system_control.auth_delivery($1,'sending')", old_hash)
        assert not await conn.fetchval("select system_control.auth_delivery($1,'sending')", old_hash)
        # A disconnected sender leaves uncertainty durably visible to the next request.
        assert await db["owner"].fetchval("select delivery_state from system_control.challenges where token_hash=$1", old_hash) == "sending"
        async with conn.transaction():
            await security._context(conn, db, **{"app.system_permission":"admins.manage"})
            response = json.loads(await conn.fetchval("select system_control.resend_administrator_invitation($1,1,'Synthetic retry',$2)", principal, new_hash))
            assert response["error"] == "rate_limited"
        await db["owner"].execute("update system_control.audit_events set occurred_at=now()-interval '2 minutes'")
        async with conn.transaction():
            await security._context(conn, db, **{"app.system_permission":"admins.manage"})
            response = json.loads(await conn.fetchval("select system_control.resend_administrator_invitation($1,1,'Synthetic retry',$2)", principal, new_hash))
            assert response["version"] == 2
        assert await conn.fetchval("select system_control.auth_challenge($1)", old_hash) is None
        assert await conn.fetchval("select system_control.auth_challenge($1)", new_hash) is not None
        assert await conn.fetchval("select system_control.auth_delivery($1,'failed')", old_hash)
        assert not await conn.fetchval("select system_control.auth_delivery($1,'submitted')", old_hash)
    finally:
        await conn.close()
