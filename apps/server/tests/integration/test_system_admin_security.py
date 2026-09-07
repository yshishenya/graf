"""Real PostgreSQL boundary tests; all identities and records are synthetic."""

from __future__ import annotations

import importlib.util
import os
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.conftest import DEVICE_ID, PERSONAL_WORKSPACE_ID, USER_ID, WORKSPACE_ID
from twobrain_rec_server.db.models import Meeting

pytestmark = pytest.mark.strict_rls


@pytest_asyncio.fixture
async def system_database(postgres_seeded_database_url: str) -> AsyncIterator[dict]:
    owner = await asyncpg.connect(postgres_seeded_database_url.replace("+asyncpg", ""))
    password = uuid4().hex
    quoted = await owner.fetchval("select quote_literal($1::text)", password)
    await owner.execute(f"alter role twobrain_rec_system login password {quoted}")
    url = (
        make_url(postgres_seeded_database_url)
        .set(
            username="twobrain_rec_system",
            password=password,
        )
        .render_as_string(hide_password=False)
    )
    actor, session_id, assignment = uuid4(), uuid4(), uuid4()
    token_hash = uuid4().hex + uuid4().hex
    engine = create_async_engine(postgres_seeded_database_url)
    try:
        async with async_sessionmaker(engine)() as session:
            session.add_all(
                [
                    Meeting(
                        id=uuid4(),
                        workspace_id=workspace,
                        created_by_user_id=USER_ID,
                        device_id=DEVICE_ID,
                        local_recording_id=uuid4().hex,
                        duration_seconds=60,
                        title="Synthetic private title",
                    )
                    for workspace in (WORKSPACE_ID, PERSONAL_WORKSPACE_ID)
                ]
            )
            await session.commit()
        # An ordinary product owner is never copied into the system identity store.
        assert await owner.fetchval("select count(*) from system_control.principals") == 0
        await owner.execute(
            """
            insert into system_control.principals
                (id, normalized_email, password_hash, status, auth_version)
            values ($1, 'synthetic@example.invalid', 'synthetic-not-a-password', 'active', 1)
        """,
            actor,
        )
        await owner.execute(
            """
            insert into system_control.role_assignments (id, principal_id, role, starts_at)
            values ($1, $2, 'system_admin', now() - interval '1 minute')
        """,
            assignment,
            actor,
        )
        await owner.execute(
            """
            insert into system_control.sessions
                (id, principal_id, token_hash, auth_version, issued_at,
                 last_interaction_at, absolute_expires_at, mfa_at)
            values ($1, $2, $3, 1, now(), now(), now() + interval '12 hours', now())
        """,
            session_id,
            actor,
            token_hash,
        )
        yield dict(
            owner=owner,
            url=url,
            actor=actor,
            session=session_id,
            token_hash=token_hash,
            assignment=assignment,
        )
    finally:
        await engine.dispose()
        await owner.close()


async def _context(connection: asyncpg.Connection, db: dict, **overrides: str) -> None:
    settings = {
        "app.context_kind": "system",
        "app.system_actor_id": str(db["actor"]),
        "app.system_session_id": str(db["session"]),
        "app.system_session_token_hash": db["token_hash"],
        "app.system_permission": "meetings.metadata",
    }
    settings.update(overrides)
    for key, value in settings.items():
        await connection.execute("select set_config($1, $2, true)", key, value)


@pytest.mark.asyncio
async def test_system_metadata_is_global_but_content_and_mutations_are_closed(system_database):
    db = system_database
    connection = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        async with connection.transaction():
            assert await connection.fetch("select id, status from public.meetings") == []
            await _context(connection, db)
            assert len(await connection.fetch("select id, status from public.meetings")) == 2
            for sql in (
                "select * from public.meetings",
                "select title from public.meetings",
                "select * from system_control.principals",
                "select * from system_control.sessions",
                "update public.meetings set status = 'ready'",
                "delete from public.meetings",
                "set role twobrain_rec",
                "set role twobrain_rec_system_authority",
            ):
                with pytest.raises(asyncpg.InsufficientPrivilegeError):
                    async with connection.transaction():
                        await connection.execute(sql)
    finally:
        await connection.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["request", "worker", "auth_bootstrap", "maintenance"])
async def test_existing_public_policies_cannot_bypass_system_authority(system_database, kind):
    db = system_database
    connection = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        async with connection.transaction():
            await _context(
                connection,
                db,
                **{
                    "app.context_kind": kind,
                    "app.workspace_id": str(WORKSPACE_ID),
                    "app.user_id": str(USER_ID),
                    "app.maintenance_operation": "operator_diagnostics",
                },
            )
            assert await connection.fetch("select id from public.meetings") == []
    finally:
        await connection.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    [
        "update system_control.principals set status = 'blocked'",
        "update system_control.principals set status = 'recovery_pending'",
        "update system_control.principals set auth_version = auth_version + 1",
        "update system_control.sessions set revoked_at = now()",
        "update system_control.sessions set absolute_expires_at = now(), "
        "issued_at = now() - interval '1 minute'",
        "update system_control.sessions set last_interaction_at = now() - interval '31 minutes', "
        "issued_at = now() - interval '32 minutes', absolute_expires_at = now() + interval '1 hour'",
        "update system_control.role_assignments set role = 'billing_manager'",
        "update system_control.role_assignments set revoked_at = now()",
        "update system_control.role_assignments set expires_at = now()",
    ],
)
async def test_current_authority_is_rechecked_on_each_statement(system_database, change):
    db = system_database
    connection = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        async with connection.transaction():
            await _context(connection, db)
            assert len(await connection.fetch("select id from public.meetings")) == 2
            await db["owner"].execute(change)
            assert await connection.fetch("select id from public.meetings") == []
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_forged_session_and_pooled_transaction_do_not_retain_access(system_database):
    from twobrain_rec_server.db.session import (
        create_system_admin_database,
        verify_system_admin_database_identity,
    )
    from twobrain_rec_server.db.tenant_context import (
        SystemDatabaseContext,
        WorkspaceAuthContext,
        apply_system_context,
        apply_tenant_context,
    )

    db = system_database
    engine, sessions = create_system_admin_database(database_url=db["url"])
    context = SystemDatabaseContext(
        admin_session_id=db["session"],
        actor_id=db["actor"],
        session_token_hash=db["token_hash"],
        permission="meetings.metadata",
    )
    try:
        await verify_system_admin_database_identity(sessions)
        async with sessions() as session:
            await apply_system_context(session, context)
            assert len((await session.execute(text("select id from meetings"))).all()) == 2
            await session.commit()
            assert len((await session.execute(text("select id from meetings"))).all()) == 2
            await session.rollback()
            with pytest.raises(RuntimeError, match="mix"):
                await apply_tenant_context(session, WorkspaceAuthContext(workspace_id=WORKSPACE_ID))
        async with sessions() as session:
            assert (await session.execute(text("select id from meetings"))).all() == []
            await session.rollback()
            with pytest.raises(RuntimeError, match="mix"):
                await apply_tenant_context(session, WorkspaceAuthContext(workspace_id=WORKSPACE_ID))
        async with async_sessionmaker(engine)() as session:
            await apply_tenant_context(session, WorkspaceAuthContext(workspace_id=WORKSPACE_ID))
            with pytest.raises(RuntimeError, match="mix"):
                await apply_system_context(session, context)
        connection = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
        try:
            for value in ("", "malformed", str(uuid4())):
                async with connection.transaction():
                    await _context(connection, db, **{"app.system_session_id": value})
                    assert await connection.fetch("select id from meetings") == []
            async with connection.transaction():
                await _context(connection, db, **{"app.system_session_token_hash": "0" * 64})
                assert await connection.fetch("select id from meetings") == []
        finally:
            await connection.close()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_optional_runtime_bootstrap_keeps_system_boundary(
    system_database, tmp_path, monkeypatch
):
    db = system_database
    script = Path(__file__).resolve().parents[2] / "scripts/bootstrap_runtime_database_roles.py"
    spec = importlib.util.spec_from_file_location("f254_role_bootstrap", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    url = make_url(db["url"])
    monkeypatch.setenv("TWOBRAIN_DB_HOST", url.host)
    monkeypatch.setenv("TWOBRAIN_DB_PORT", str(url.port))
    monkeypatch.setenv("TWOBRAIN_DB_NAME", url.database)
    for kind in ("OWNER", "APP", "MAINTENANCE", "MEDIA", "SYSTEM"):
        secret = tmp_path / kind.lower()
        password = "twobrain_rec" if kind == "OWNER" else uuid4().hex
        if kind == "MEDIA":
            password = os.environ.get("GRAF_TEST_POSTGRES_MEDIA_PASSWORD", password)
        secret.write_text(password)
        monkeypatch.setenv(f"TWOBRAIN_DB_{kind}_PASSWORD_FILE", str(secret))
    await module._bootstrap()
    await module._bootstrap()
    for role in ("twobrain_rec_app", "twobrain_rec_media"):
        assert not await db["owner"].fetchval(
            "select has_schema_privilege($1::name, 'system_control', 'USAGE')",
            role,
        )
    # A claimed system GUC under the ordinary application login is not authority.
    app_password = (tmp_path / "app").read_text()
    app_url = url.set(username="twobrain_rec_app", password=app_password)
    app = await asyncpg.connect(
        app_url.render_as_string(hide_password=False).replace("+asyncpg", "")
    )
    try:
        async with app.transaction():
            await _context(app, db)
            assert await app.fetch("select id from public.meetings") == []
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                async with app.transaction():
                    await app.execute("select * from system_control.principals")
    finally:
        await app.close()
    monkeypatch.delenv("TWOBRAIN_DB_SYSTEM_PASSWORD_FILE")
    await module._bootstrap()  # Existing deployments do not require the optional secret.
    await db["owner"].execute("grant twobrain_rec_system to twobrain_rec_app")
    try:
        with pytest.raises(RuntimeError, match="membership"):
            await module._bootstrap()
    finally:
        await db["owner"].execute("revoke twobrain_rec_system from twobrain_rec_app")


@pytest.mark.asyncio
async def test_restrictive_policies_survive_permissive_allow_all(system_database):
    db = system_database
    owner = db["owner"]
    # Reproduce the worst possible permissive PUBLIC policy. Mandatory system
    # guards still deny unauthenticated reads and every domain write.
    await owner.execute(
        "create policy f254_permissive_probe on meetings using (true) with check (true)"
    )
    await owner.execute("grant update (status), delete on meetings to twobrain_rec_system")
    connection = await asyncpg.connect(db["url"].replace("+asyncpg", ""))
    try:
        async with connection.transaction():
            assert await connection.fetch("select id from meetings") == []
            await _context(connection, db)
            assert len(await connection.fetch("select id from meetings")) == 2
            assert await connection.execute("update meetings set status = 'ready'") == "UPDATE 0"
            assert await connection.execute("delete from meetings") == "DELETE 0"
    finally:
        await connection.close()
        await owner.execute("revoke update (status), delete on meetings from twobrain_rec_system")
        await owner.execute("drop policy f254_permissive_probe on meetings")


@pytest.mark.asyncio
async def test_system_migration_refuses_destructive_downgrade(system_database):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy.exc import DBAPIError

    migration_path = (
        Path(__file__).resolve().parents[2]
        / "src/twobrain_rec_server/db/migrations/versions/0086_system_admin_boundary.py"
    )
    spec = importlib.util.spec_from_file_location("f254_boundary_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    owner = system_database["owner"]
    url = make_url(system_database["url"]).set(username="twobrain_rec", password="twobrain_rec")
    engine = create_async_engine(url)

    later_spec = importlib.util.spec_from_file_location(
        "f254_scoped_migration", migration_path.with_name("0087_system_scoped_authority.py"),
    )
    later_migration = importlib.util.module_from_spec(later_spec)
    later_spec.loader.exec_module(later_migration)

    operation_spec = importlib.util.spec_from_file_location(
        "f254_operations_migration", migration_path.with_name("0088_system_operations.py"),
    )
    operation_migration = importlib.util.module_from_spec(operation_spec)
    operation_spec.loader.exec_module(operation_migration)

    auth_spec = importlib.util.spec_from_file_location(
        "f254_auth_migration", migration_path.with_name("0089_system_auth.py"),
    )
    auth_migration = importlib.util.module_from_spec(auth_spec)
    auth_spec.loader.exec_module(auth_migration)

    management_spec = importlib.util.spec_from_file_location(
        "f254_management_migration", migration_path.with_name("0090_system_admin_management.py"),
    )
    management_migration = importlib.util.module_from_spec(management_spec)
    management_spec.loader.exec_module(management_migration)

    projection_spec = importlib.util.spec_from_file_location(
        "f254_projection_migration", migration_path.with_name("0091_system_user_projection.py"),
    )
    projection_migration = importlib.util.module_from_spec(projection_spec)
    projection_spec.loader.exec_module(projection_migration)

    content_spec = importlib.util.spec_from_file_location(
        "f254_content_migration", migration_path.with_name("0092_system_meeting_content.py"),
    )
    content_migration = importlib.util.module_from_spec(content_spec)
    content_spec.loader.exec_module(content_migration)

    lineage_spec = importlib.util.spec_from_file_location(
        "f254_lineage_migration", migration_path.with_name("0093_system_domain_lineage.py"),
    )
    lineage_migration = importlib.util.module_from_spec(lineage_spec)
    lineage_spec.loader.exec_module(lineage_migration)

    overview_spec = importlib.util.spec_from_file_location(
        "f254_overview_migration", migration_path.with_name("0094_system_meeting_overview.py"),
    )
    overview_migration = importlib.util.module_from_spec(overview_spec)
    overview_spec.loader.exec_module(overview_migration)

    media_spec = importlib.util.spec_from_file_location(
        "f254_media_migration", migration_path.with_name("0095_system_media_access.py"),
    )
    media_migration = importlib.util.module_from_spec(media_spec)
    media_spec.loader.exec_module(media_migration)

    def downgrade(connection):
        with Operations.context(MigrationContext.configure(connection)):
            media_migration.downgrade()
            overview_migration.downgrade()
            lineage_migration.downgrade()
            content_migration.downgrade()
            projection_migration.downgrade()
            management_migration.downgrade()
            auth_migration.downgrade()
            operation_migration.downgrade()
            later_migration.downgrade()
            migration.downgrade()

    try:
        with pytest.raises(DBAPIError, match="destructive downgrade refused"):
            async with engine.begin() as connection:
                await connection.run_sync(downgrade)
        assert await owner.fetchval("select count(*) from system_control.principals") == 1
        await owner.execute("delete from system_control.sessions")
        await owner.execute("delete from system_control.role_assignments")
        await owner.execute("delete from system_control.principals")
        async with engine.connect() as connection:
            # Empty-schema rollback must be usable before launch. Roll back the
            # test transaction to preserve the shared migrated fixture.
            await connection.run_sync(downgrade)
            assert await connection.scalar(text("select to_regnamespace('system_control')")) is None
            await connection.rollback()
        assert await owner.fetchval("select to_regnamespace('system_control') is not null")
    finally:
        await engine.dispose()


def test_existing_playback_harness_prepares_complete_schema(
    postgres_clean_database_url,
    tmp_path,
    monkeypatch,
):
    import asyncio

    from tests.fixtures import playback_normalization_ui_harness as harness

    monkeypatch.setattr(harness, "_synthetic_m4a", lambda directory: b"synthetic-harness-fixture")
    app, state = harness.create_harness(
        runtime_directory=tmp_path,
        origin="http://127.0.0.1:8099",
        database_url=postgres_clean_database_url,
    )

    async def verify():
        try:
            async with app.state.db_engine.connect() as connection:
                assert await connection.scalar(
                    text("select to_regnamespace('system_control') is not null")
                )
                assert (
                    await connection.scalar(text("select count(*) from system_control.principals"))
                    == 0
                )
                assert await connection.scalar(text("select count(*) from meetings")) >= 4
        finally:
            await app.state.db_engine.dispose()

    assert state["available_id"] != state["preparing_id"]
    asyncio.run(verify())
