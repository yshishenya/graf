"""Object grants and access audit use actual restricted PostgreSQL logins."""

from uuid import uuid4

import asyncpg
import pytest

from tests.integration import test_system_admin_security as security

system_database = security.system_database
_context = security._context

pytestmark = pytest.mark.strict_rls


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "permission", "expected"),
    [
        ("superadmin", "admins.manage", True),
        ("superadmin", "audio.download", True),
        ("superadmin", "unknown.permission", False),
        ("system_admin", "processing.reprocess", True),
        ("system_admin", "content.read", False),
        ("system_admin", "admins.manage", False),
        ("support", "support.manage", True),
        ("support", "exports.table", False),
        ("billing_manager", "billing.read", True),
        ("billing_manager", "billing.manage", False),
        ("billing_manager", "meetings.metadata", False),
        ("analyst", "analytics.read", True),
        ("analyst", "users.read", False),
        ("auditor", "audit.read", True),
    ],
)
async def test_fixed_role_authority(system_database, role, permission, expected):
    db = system_database
    await db["owner"].execute("update system_control.role_assignments set role = $1", role)
    connection = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        async with connection.transaction():
            await _context(connection, db, **{"app.system_permission": permission})
            assert (
                await connection.fetchval(
                    "select system_control.permission_allowed($1, 'meeting', $2)",
                    permission,
                    uuid4(),
                )
                is expected
            )
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_scoped_grant_cannot_escape_object_assignment_or_expiry(system_database):
    db = system_database
    owner = db["owner"]
    target, grant_id = uuid4(), uuid4()
    await owner.execute(
        """
        insert into system_control.permission_grants
            (id, principal_id, assignment_id, assignment_version, permission,
             target_type, target_id, starts_at, expires_at, granted_by, reason)
        values ($1, $2, $3, 1, 'content.read', 'meeting', $4,
                now() - interval '1 minute', now() + interval '1 hour', $2, 'Synthetic case')
    """,
        grant_id,
        db["actor"],
        db["assignment"],
        target,
    )
    connection = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        async with connection.transaction():
            await _context(connection, db, **{"app.system_permission": "content.read"})
            query = "select system_control.permission_allowed('content.read', 'meeting', $1)"
            assert await connection.fetchval(query, target)
            assert not await connection.fetchval(query, uuid4())
            assert not await connection.fetchval(
                "select system_control.permission_allowed('audio.download', 'meeting', $1)",
                target,
            )
            await owner.execute("update system_control.role_assignments set version = 2")
            assert not await connection.fetchval(query, target)
            await owner.execute("update system_control.role_assignments set version = 1")
            await owner.execute("update system_control.permission_grants set expires_at = now()")
            assert not await connection.fetchval(query, target)
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_grant_constraint_rejects_ungrantable_permission_and_overlong_lifetime(
    system_database,
):
    db = system_database
    for permission, duration in [("admins.manage", "1 hour"), ("content.read", "25 hours")]:
        with pytest.raises(asyncpg.CheckViolationError):
            async with db["owner"].transaction():
                await db["owner"].execute(
                    """
                    insert into system_control.permission_grants
                        (id, principal_id, assignment_id, assignment_version, permission,
                         target_type, target_id, starts_at, expires_at, granted_by, reason)
                    values ($1, $2, $3, 1, $4, 'meeting', $5, now(),
                            now() + $6::text::interval, $2, 'Synthetic case')
                """,
                    uuid4(),
                    db["actor"],
                    db["assignment"],
                    permission,
                    uuid4(),
                    duration,
                )


@pytest.mark.asyncio
async def test_case_and_audit_are_required_before_content_authority(system_database):
    from twobrain_rec_server.db.session import create_system_admin_database
    from twobrain_rec_server.db.tenant_context import SystemDatabaseContext, apply_system_context
    from twobrain_rec_server.system_admin.audit import authorize_access, create_case_context

    db = system_database
    owner = db["owner"]
    await owner.execute("update system_control.role_assignments set role = 'superadmin'")
    target = await owner.fetchval("select id from meetings limit 1")
    engine, sessions = create_system_admin_database(database_url=db["url"])
    context = SystemDatabaseContext(
        admin_session_id=db["session"],
        actor_id=db["actor"],
        session_token_hash=db["token_hash"],
        permission="content.read",
        target_type="meeting",
        target_id=target,
    )
    try:
        # Permissions alone are insufficient for content; a case and persisted
        # audit are separate prerequisites, including for the superadmin.
        async with sessions() as session:
            await apply_system_context(session, context)
            from sqlalchemy import text

            assert not await session.scalar(
                text("select system_control.content_allowed('content.read', 'meeting', :id)"),
                {"id": target},
            )
        case = await create_case_context(
            sessions, context, reason="Synthetic support investigation"
        )
        from dataclasses import replace

        context = replace(context, case_context_id=case)
        approved = await authorize_access(sessions, context)
        assert approved.audit_event_id is not None
        async with sessions() as session:
            await apply_system_context(session, approved)
            query = text("select system_control.content_allowed('content.read', 'meeting', :id)")
            assert await session.scalar(query, {"id": target})
            assert not await session.scalar(query, {"id": uuid4()})
            await owner.execute("update system_control.sessions set revoked_at = now()")
            assert not await session.scalar(query, {"id": target})
        assert await owner.fetchval("select count(*) from system_control.audit_events") == 2
        connection = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
        try:
            for statement in (
                "delete from system_control.audit_events",
                "update system_control.audit_events set result = 'allowed'",
                "select * from system_control.permission_grants",
            ):
                with pytest.raises(asyncpg.InsufficientPrivilegeError):
                    await connection.execute(statement)
        finally:
            await connection.close()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_denied_access_is_audited_and_audit_failure_denies_access(system_database):
    from twobrain_rec_server.db.session import create_system_admin_database
    from twobrain_rec_server.db.tenant_context import SystemDatabaseContext
    from twobrain_rec_server.system_admin.audit import authorize_access

    db = system_database
    engine, sessions = create_system_admin_database(database_url=db["url"])
    context = SystemDatabaseContext(
        admin_session_id=db["session"],
        actor_id=db["actor"],
        session_token_hash=db["token_hash"],
        permission="content.read",
        target_type="meeting",
        target_id=uuid4(),
    )
    try:
        with pytest.raises(PermissionError):
            await authorize_access(sessions, context)
        assert (
            await db["owner"].fetchval("select result from system_control.audit_events") == "denied"
        )
        await db["owner"].execute(
            "revoke insert on system_control.audit_events from twobrain_rec_system_authority"
        )
        try:
            from sqlalchemy.exc import DBAPIError

            with pytest.raises(DBAPIError):
                await authorize_access(sessions, context)
        finally:
            await db["owner"].execute(
                "grant insert on system_control.audit_events to twobrain_rec_system_authority"
            )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_audit_must_commit_before_content_can_be_read(system_database):
    from twobrain_rec_server.db.session import create_system_admin_database
    from twobrain_rec_server.db.tenant_context import SystemDatabaseContext
    from twobrain_rec_server.system_admin.audit import create_case_context

    db = system_database
    await db["owner"].execute("update system_control.role_assignments set role = 'superadmin'")
    target = await db["owner"].fetchval("select id from meetings limit 1")
    engine, sessions = create_system_admin_database(database_url=db["url"])
    context = SystemDatabaseContext(
        admin_session_id=db["session"],
        actor_id=db["actor"],
        session_token_hash=db["token_hash"],
        permission="content.read",
        target_type="meeting",
        target_id=target,
    )
    connection = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        case_id = await create_case_context(sessions, context, reason="Synthetic transaction proof")
        query = "select system_control.content_allowed('content.read', 'meeting', $1)"
        settings = {
            "app.system_permission": "content.read",
            "app.system_target_type": "meeting",
            "app.system_target_id": str(target),
            "app.system_case_context_id": str(case_id),
        }
        async with connection.transaction():
            await _context(connection, db, **settings)
            event = await connection.fetchrow("select * from system_control.record_access()")
            assert event["allowed"]
            await connection.execute(
                "select set_config('app.system_audit_event_id', $1, true)",
                str(event["audit_event_id"]),
            )
            assert not await connection.fetchval(query, target)
        async with connection.transaction():
            await _context(
                connection,
                db,
                **settings,
                **{"app.system_audit_event_id": str(event["audit_event_id"])},
            )
            assert await connection.fetchval(query, target)
    finally:
        await connection.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_revoked_session_denial_keeps_actual_actor_in_audit(system_database):
    from twobrain_rec_server.db.session import create_system_admin_database
    from twobrain_rec_server.db.tenant_context import SystemDatabaseContext
    from twobrain_rec_server.system_admin.audit import authorize_access

    db = system_database
    engine, sessions = create_system_admin_database(database_url=db["url"])
    context = SystemDatabaseContext(
        admin_session_id=db["session"],
        actor_id=db["actor"],
        session_token_hash=db["token_hash"],
        permission="meetings.metadata",
    )
    await db["owner"].execute("update system_control.sessions set revoked_at = now()")
    try:
        with pytest.raises(PermissionError):
            await authorize_access(sessions, context)
        row = await db["owner"].fetchrow(
            "select principal_id, session_id, result from system_control.audit_events"
        )
        assert tuple(row.values()) == (db["actor"], db["session"], "denied")
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_case_and_audit_do_not_transfer_between_sessions_or_purposes(system_database):
    from dataclasses import replace

    from sqlalchemy import text

    from twobrain_rec_server.db.session import create_system_admin_database
    from twobrain_rec_server.db.tenant_context import SystemDatabaseContext, apply_system_context
    from twobrain_rec_server.system_admin.audit import authorize_access, create_case_context

    db = system_database
    await db["owner"].execute("update system_control.role_assignments set role = 'superadmin'")
    target = await db["owner"].fetchval("select id from meetings limit 1")
    engine, sessions = create_system_admin_database(database_url=db["url"])
    context = SystemDatabaseContext(
        admin_session_id=db["session"],
        actor_id=db["actor"],
        session_token_hash=db["token_hash"],
        permission="audio.listen",
        target_type="meeting",
        target_id=target,
    )
    try:
        case = await create_case_context(sessions, context, reason="Synthetic scoped playback")
        approved = await authorize_access(sessions, replace(context, case_context_id=case))
        second_session, second_hash = uuid4(), uuid4().hex + uuid4().hex
        await db["owner"].execute(
            """
            insert into system_control.sessions
                (id, principal_id, token_hash, auth_version, issued_at, last_interaction_at,
                 absolute_expires_at, mfa_at)
            values ($1, $2, $3, 1, now(), now(), now() + interval '1 hour', now())
        """,
            second_session,
            db["actor"],
            second_hash,
        )
        for other in (
            replace(approved, permission="audio.download"),
            replace(approved, admin_session_id=second_session, session_token_hash=second_hash),
        ):
            async with sessions() as session:
                await apply_system_context(session, other)
                assert not await session.scalar(
                    text("select system_control.content_allowed(:permission, 'meeting', :target)"),
                    {"permission": other.permission, "target": target},
                )
        await db["owner"].execute(
            "update system_control.audit_events set occurred_at = now() - interval '61 seconds'"
        )
        async with sessions() as session:
            await apply_system_context(session, approved)
            assert not await session.scalar(
                text("select system_control.content_allowed('audio.listen', 'meeting', :target)"),
                {"target": target},
            )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_auditor_projection_and_grant_revocation(system_database):
    db = system_database
    owner = db["owner"]
    target = uuid4()
    await owner.execute(
        """
        insert into system_control.permission_grants
            (id, principal_id, assignment_id, assignment_version, permission,
             target_type, target_id, starts_at, expires_at, granted_by, reason)
        values ($1, $2, $3, 1, 'audio.listen', 'meeting', $4,
                now() - interval '1 minute', now() + interval '1 hour', $2, 'Synthetic grant')
    """,
        uuid4(),
        db["actor"],
        db["assignment"],
        target,
    )
    connection = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        async with connection.transaction():
            await _context(connection, db, **{"app.system_permission": "audio.listen"})
            query = "select system_control.permission_allowed('audio.listen', 'meeting', $1)"
            assert await connection.fetchval(query, target)
            await owner.execute("update system_control.permission_grants set revoked_at = now()")
            assert not await connection.fetchval(query, target)
            # Even the previous grantee can neither broaden the grant nor read audit.
            assert await connection.fetch("select id from system_control.audit_events") == []
            await connection.fetchrow("select * from system_control.record_access()")
        await owner.execute("update system_control.role_assignments set role = 'auditor'")
        async with connection.transaction():
            await _context(connection, db, **{"app.system_permission": "audit.read"})
            assert len(await connection.fetch("select id from system_control.audit_events")) == 1
            assert await connection.fetch("select id from meetings") == []
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_case_context_never_grants_content_permission(system_database):
    from dataclasses import replace

    from twobrain_rec_server.db.session import create_system_admin_database
    from twobrain_rec_server.db.tenant_context import SystemDatabaseContext
    from twobrain_rec_server.system_admin.audit import authorize_access, create_case_context

    db = system_database
    engine, sessions = create_system_admin_database(database_url=db["url"])
    target = await db["owner"].fetchval("select id from meetings limit 1")
    context = SystemDatabaseContext(
        admin_session_id=db["session"],
        actor_id=db["actor"],
        session_token_hash=db["token_hash"],
        permission="content.read",
        target_type="meeting",
        target_id=target,
    )
    try:
        case = await create_case_context(
            sessions, context, reason="Synthetic metadata-only investigation"
        )
        with pytest.raises(PermissionError):
            await authorize_access(sessions, replace(context, case_context_id=case))
        events = await db["owner"].fetch(
            "select action, result, reason from system_control.audit_events order by occurred_at"
        )
        assert [(row["action"], row["result"]) for row in events] == [
            ("case.open", "allowed"),
            ("access", "denied"),
        ]
        assert all(row["reason"] == "Synthetic metadata-only investigation" for row in events)
    finally:
        await engine.dispose()
