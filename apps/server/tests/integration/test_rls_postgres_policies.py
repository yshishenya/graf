from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from tests.fixtures.postgres_rls import rls_test_database_url
from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    TenantDatabaseContext,
    apply_tenant_context_to_connection,
)

REPO_ROOT = Path(__file__).resolve().parents[4]

pytestmark = pytest.mark.strict_rls


@dataclass(frozen=True, slots=True)
class MigratedPostgresUrls:
    migration_url: str
    probe_url: str
    probe_role: str | None = None


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


async def _create_probe_role(migration_url: str) -> tuple[str, str]:
    role_name = f"twobrain_rls_probe_{uuid4().hex[:16]}"
    password = uuid4().hex
    engine = create_async_engine(migration_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.begin() as conn:
            quoted_role = _quote_identifier(role_name)
            await conn.execute(text(f"create role {quoted_role} login password {_quote_literal(password)}"))
            await conn.execute(text(f"grant usage on schema public to {quoted_role}"))
            await conn.execute(text(f"grant select, insert, update, delete on all tables in schema public to {quoted_role}"))
            await conn.execute(text(f"grant usage, select on all sequences in schema public to {quoted_role}"))
    finally:
        await engine.dispose()
    return role_name, password


async def _drop_probe_role(migration_url: str, role_name: str) -> None:
    engine = create_async_engine(migration_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.begin() as conn:
            quoted_role = _quote_identifier(role_name)
            await conn.execute(text(f"drop owned by {quoted_role}"))
            await conn.execute(text(f"drop role if exists {quoted_role}"))
    finally:
        await engine.dispose()


@pytest.fixture(scope="module")
def migrated_postgres_urls() -> Iterator[MigratedPostgresUrls]:
    url = rls_test_database_url()
    previous_url = os.environ.get("TWOBRAIN_DATABASE_URL")
    os.environ["TWOBRAIN_DATABASE_URL"] = url
    get_settings.cache_clear()
    alembic_config = Config(str(REPO_ROOT / "apps/server/alembic.ini"))
    alembic_config.set_main_option(
        "script_location",
        str(REPO_ROOT / "apps/server/src/twobrain_rec_server/db/migrations"),
    )
    command.upgrade(alembic_config, "head")
    probe_role: str | None = None
    probe_url = os.getenv("RLS_TEST_PROBE_DATABASE_URL")
    if not probe_url:
        probe_role, password = asyncio.run(_create_probe_role(url))
        probe_url = make_url(url).set(username=probe_role, password=password).render_as_string(
            hide_password=False
        )
    try:
        yield MigratedPostgresUrls(migration_url=url, probe_url=probe_url, probe_role=probe_role)
    finally:
        if probe_role is not None:
            asyncio.run(_drop_probe_role(url, probe_role))
        if previous_url is None:
            os.environ.pop("TWOBRAIN_DATABASE_URL", None)
        else:
            os.environ["TWOBRAIN_DATABASE_URL"] = previous_url
        get_settings.cache_clear()


@pytest.fixture
async def rls_engine(migrated_postgres_urls: MigratedPostgresUrls) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated_postgres_urls.probe_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()


async def _seed_probe_rows(engine: AsyncEngine) -> dict[str, UUID | str]:
    suffix = uuid4().hex[:12]
    ids: dict[str, UUID | str] = {
        "org_a": uuid4(),
        "org_b": uuid4(),
        "workspace_a": uuid4(),
        "workspace_b": uuid4(),
        "user_a": uuid4(),
        "user_b": uuid4(),
        "device_a": uuid4(),
        "device_b": uuid4(),
        "meeting_a": uuid4(),
        "meeting_b": uuid4(),
        "session_a": uuid4(),
        "session_hash_a": f"rls-session-{suffix}",
        "slug": suffix,
    }
    async with engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_rls_postgres_policies",
                reason_category="rls_probe_seed",
                feature_area="security",
            ),
        )
        for label in ("a", "b"):
            await conn.execute(
                text(
                    """
                    insert into organizations (id, slug, name)
                    values (:org_id, :org_slug, :org_name)
                    """
                ),
                {
                    "org_id": ids[f"org_{label}"],
                    "org_slug": f"rls-org-{label}-{suffix}",
                    "org_name": f"RLS Org {label.upper()}",
                },
            )
            await conn.execute(
                text(
                    """
                    insert into workspaces (id, organization_id, slug, name)
                    values (:workspace_id, :org_id, :workspace_slug, :workspace_name)
                    """
                ),
                {
                    "workspace_id": ids[f"workspace_{label}"],
                    "org_id": ids[f"org_{label}"],
                    "workspace_slug": f"rls-workspace-{label}-{suffix}",
                    "workspace_name": f"RLS Workspace {label.upper()}",
                },
            )
            await conn.execute(
                text(
                    """
                    insert into user_identities (id, organization_id, external_subject, display_name)
                    values (:user_id, :org_id, :external_subject, :display_name)
                    """
                ),
                {
                    "user_id": ids[f"user_{label}"],
                    "org_id": ids[f"org_{label}"],
                    "external_subject": f"rls-user-{label}-{suffix}",
                    "display_name": f"RLS User {label.upper()}",
                },
            )
            await conn.execute(
                text(
                    """
                    insert into workspace_memberships (workspace_id, user_id, role, status)
                    values (:workspace_id, :user_id, 'owner', 'active')
                    """
                ),
                {"workspace_id": ids[f"workspace_{label}"], "user_id": ids[f"user_{label}"]},
            )
            await conn.execute(
                text(
                    """
                    insert into registered_devices
                        (id, workspace_id, user_id, device_public_id, status, registration_state)
                    values
                        (:device_id, :workspace_id, :user_id, :device_public_id, 'active', 'approved')
                    """
                ),
                {
                    "device_id": ids[f"device_{label}"],
                    "workspace_id": ids[f"workspace_{label}"],
                    "user_id": ids[f"user_{label}"],
                    "device_public_id": f"rls-device-{label}-{suffix}",
                },
            )
            await conn.execute(
                text(
                    """
                    insert into meetings
                        (id, workspace_id, created_by_user_id, device_id, local_recording_id,
                         duration_seconds, status)
                    values
                        (:meeting_id, :workspace_id, :user_id, :device_id, :local_recording_id,
                         60, 'ingested_pending_processing')
                    """
                ),
                {
                    "meeting_id": ids[f"meeting_{label}"],
                    "workspace_id": ids[f"workspace_{label}"],
                    "user_id": ids[f"user_{label}"],
                    "device_id": ids[f"device_{label}"],
                    "local_recording_id": f"rls-meeting-{label}-{suffix}",
                },
            )
        await conn.execute(
            text(
                """
                insert into auth_sessions
                    (id, user_id, workspace_id, device_id, provider, session_token_hash, expires_at)
                values
                    (:session_id, :user_id, :workspace_id, :device_id, 'yandex',
                     :session_token_hash, :expires_at)
                """
            ),
            {
                "session_id": ids["session_a"],
                "user_id": ids["user_a"],
                "workspace_id": ids["workspace_a"],
                "device_id": ids["device_a"],
                "session_token_hash": ids["session_hash_a"],
                "expires_at": datetime.now(UTC) + timedelta(hours=1),
            },
        )
    return ids


def _request_context(ids: dict[str, UUID | str], label: str, *, context_kind: str = "request") -> TenantDatabaseContext:
    return TenantDatabaseContext(
        organization_id=ids[f"org_{label}"],
        workspace_id=ids[f"workspace_{label}"],
        user_id=ids[f"user_{label}"],
        device_id=ids[f"device_{label}"],
        context_kind=context_kind,
    )


@pytest.mark.asyncio
async def test_same_tenant_and_cross_tenant_reads_follow_workspace_context(rls_engine: AsyncEngine) -> None:
    ids = await _seed_probe_rows(rls_engine)

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(ids, "a"))
        visible_count = await conn.scalar(text("select count(*) from meetings"))
        foreign_count = await conn.scalar(
            text("select count(*) from meetings where id=:meeting_id"),
            {"meeting_id": ids["meeting_b"]},
        )

    assert visible_count == 1
    assert foreign_count == 0


@pytest.mark.asyncio
async def test_cross_tenant_insert_and_missing_context_fail_closed(rls_engine: AsyncEngine) -> None:
    ids = await _seed_probe_rows(rls_engine)

    async with rls_engine.begin() as conn:
        missing_count = await conn.scalar(text("select count(*) from meetings"))
        assert missing_count == 0

    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(ids, "a"))
        with pytest.raises(Exception, match="row-level security|violates"):
            await conn.execute(
                text(
                    """
                    insert into meetings
                        (id, workspace_id, created_by_user_id, device_id, local_recording_id,
                         duration_seconds, status)
                    values
                        (:meeting_id, :workspace_id, :user_id, :device_id, :local_recording_id,
                         60, 'draft')
                    """
                ),
                {
                    "meeting_id": uuid4(),
                    "workspace_id": ids["workspace_b"],
                    "user_id": ids["user_b"],
                    "device_id": ids["device_b"],
                    "local_recording_id": f"cross-insert-{ids['slug']}",
                },
            )


@pytest.mark.asyncio
async def test_worker_context_and_maintenance_context_are_explicit(rls_engine: AsyncEngine) -> None:
    ids = await _seed_probe_rows(rls_engine)

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(ids, "a", context_kind="worker"))
        worker_count = await conn.scalar(text("select count(*) from meetings"))

    async with rls_engine.connect() as conn:
        await conn.execute(text("select set_config('app.context_kind', 'maintenance', true)"))
        await conn.execute(text("select set_config('app.maintenance_operation', 'migration_verification', true)"))
        incomplete_maintenance_count = await conn.scalar(text("select count(*) from meetings"))

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_rls_postgres_policies",
                reason_category="rls_probe",
                feature_area="security",
            ),
        )
        maintenance_count = await conn.scalar(text("select count(*) from meetings"))

    assert worker_count == 1
    assert incomplete_maintenance_count == 0
    assert maintenance_count >= 2


@pytest.mark.asyncio
async def test_auth_session_lookup_requires_context_kind(rls_engine: AsyncEngine) -> None:
    ids = await _seed_probe_rows(rls_engine)

    async with rls_engine.connect() as conn:
        await conn.execute(
            text("select set_config('app.auth_session_token_hash', :session_hash, true)"),
            {"session_hash": ids["session_hash_a"]},
        )
        partial_count = await conn.scalar(text("select count(*) from auth_sessions"))

    async with rls_engine.connect() as conn:
        await conn.execute(text("select set_config('app.context_kind', 'auth_session_lookup', true)"))
        await conn.execute(
            text("select set_config('app.auth_session_token_hash', :session_hash, true)"),
            {"session_hash": ids["session_hash_a"]},
        )
        lookup_count = await conn.scalar(text("select count(*) from auth_sessions"))

    assert partial_count == 0
    assert lookup_count == 1
