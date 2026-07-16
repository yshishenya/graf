from __future__ import annotations

import asyncio
import os
import stat
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
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

import scripts.cleanup_smoke_artifacts as cleanup_smoke_artifacts_module
from scripts.cleanup_smoke_artifacts import cleanup_smoke_artifacts
from scripts.cleanup_smoke_auth_session import cleanup_smoke_auth_session
from scripts.issue_smoke_auth_session import issue_smoke_auth_session
from scripts.seed_smoke_identity import seed_identity
from tests.fixtures.postgres_rls import rls_test_database_url
from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.db.models import (
    IngestAuditEvent,
    MediaRevision,
    Meeting,
    PlaybackNormalizationAttempt,
    PlaybackNormalizationJob,
    TemporaryUploadObject,
    TrackArtifact,
    UploadPart,
    UploadSession,
)
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    TenantDatabaseContext,
    WorkspaceAuthContext,
    apply_tenant_context_to_connection,
)
from twobrain_rec_server.deployment import build_smoke_identity_seed

REPO_ROOT = Path(__file__).resolve().parents[4]
MEDIA_READ_ONLY_TABLES = (
    "alembic_version",
    "meetings",
    "media_revisions",
    "workspaces",
)
MEDIA_READ_WRITE_TABLES = (
    "playback_backfill_runs",
    "playback_normalization_attempts",
    "playback_normalization_jobs",
    "support_incidents",
    "track_artifacts",
)
MEDIA_INSERT_ONLY_TABLES = ("ingest_audit_events",)
MEDIA_LOCK_COLUMNS = (("meetings", "updated_at"), ("media_revisions", "updated_at"))


@dataclass(frozen=True, slots=True)
class MigratedPostgresUrls:
    migration_url: str
    probe_url: str
    app_url: str
    media_url: str
    probe_role: str | None = None
    app_role_created: bool = False
    media_role_created: bool = False


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


async def _create_probe_role(
    migration_url: str,
    *,
    role_name: str,
) -> tuple[str, str]:
    password = uuid4().hex
    engine = create_async_engine(migration_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.begin() as conn:
            quoted_role = _quote_identifier(role_name)
            await conn.execute(
                text(
                    f"create role {quoted_role} login password {_quote_literal(password)} "
                    "nosuperuser nocreatedb nocreaterole noinherit noreplication nobypassrls"
                )
            )
            await conn.execute(text(f"grant usage on schema public to {quoted_role}"))
            await conn.execute(
                text(
                    f"grant select, insert, update, delete on all tables in schema public to {quoted_role}"
                )
            )
            await conn.execute(
                text(f"grant usage, select on all sequences in schema public to {quoted_role}")
            )
    finally:
        await engine.dispose()
    return role_name, password


async def _create_media_role(migration_url: str) -> tuple[str, bool]:
    role_name = "twobrain_rec_media"
    password = uuid4().hex
    engine = create_async_engine(migration_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.begin() as conn:
            exists = bool(
                await conn.scalar(
                    text("select exists(select 1 from pg_roles where rolname = :role_name)"),
                    {"role_name": role_name},
                )
            )
            if exists:
                pytest.skip(
                    "RLS_TEST_MEDIA_DATABASE_URL is required when twobrain_rec_media exists"
                )
            quoted_role = _quote_identifier(role_name)
            await conn.execute(
                text(
                    f"create role {quoted_role} login password {_quote_literal(password)} "
                    "nosuperuser nocreatedb nocreaterole noinherit noreplication nobypassrls"
                )
            )
            await conn.execute(text(f"alter role {quoted_role} set row_security = on"))
            await conn.execute(text(f"grant usage on schema public to {quoted_role}"))
            await conn.execute(
                text(
                    "grant select on "
                    + ", ".join(f"public.{table_name}" for table_name in MEDIA_READ_ONLY_TABLES)
                    + f" to {quoted_role}"
                )
            )
            await conn.execute(
                text(
                    "grant select, insert, update on "
                    + ", ".join(f"public.{table_name}" for table_name in MEDIA_READ_WRITE_TABLES)
                    + f" to {quoted_role}"
                )
            )
            await conn.execute(
                text(
                    "grant insert on "
                    + ", ".join(f"public.{table_name}" for table_name in MEDIA_INSERT_ONLY_TABLES)
                    + f" to {quoted_role}"
                )
            )
            for table_name, column_name in MEDIA_LOCK_COLUMNS:
                await conn.execute(
                    text(f"grant update ({column_name}) on public.{table_name} to {quoted_role}")
                )
            await conn.execute(
                text(
                    "grant execute on function "
                    "rec_playback_normalization_workspace_page(uuid, integer) "
                    f"to {quoted_role}"
                )
            )
            await conn.execute(
                text(
                    "grant execute on function "
                    "rec_playback_normalization_cleanup_page(integer) "
                    f"to {quoted_role}"
                )
            )
    finally:
        await engine.dispose()
    media_url = (
        make_url(migration_url)
        .set(
            username=role_name,
            password=password,
        )
        .render_as_string(hide_password=False)
    )
    return media_url, True


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
        probe_role, password = asyncio.run(
            _create_probe_role(url, role_name="twobrain_rec_maintenance")
        )
        probe_url = (
            make_url(url)
            .set(username=probe_role, password=password)
            .render_as_string(hide_password=False)
        )
    app_role_created = False
    app_url = os.getenv("RLS_TEST_APP_DATABASE_URL")
    if not app_url:
        app_role, app_password = asyncio.run(
            _create_probe_role(url, role_name="twobrain_rec_app")
        )
        app_role_created = True
        app_url = (
            make_url(url)
            .set(username=app_role, password=app_password)
            .render_as_string(hide_password=False)
        )
    media_role_created = False
    media_url = os.getenv("RLS_TEST_MEDIA_DATABASE_URL")
    if not media_url:
        media_url, media_role_created = asyncio.run(_create_media_role(url))
    try:
        yield MigratedPostgresUrls(
            migration_url=url,
            probe_url=probe_url,
            app_url=app_url,
            media_url=media_url,
            probe_role=probe_role,
            app_role_created=app_role_created,
            media_role_created=media_role_created,
        )
    finally:
        if probe_role is not None:
            asyncio.run(_drop_probe_role(url, probe_role))
        if app_role_created:
            asyncio.run(_drop_probe_role(url, "twobrain_rec_app"))
        if media_role_created:
            asyncio.run(_drop_probe_role(url, "twobrain_rec_media"))
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


@pytest.fixture
async def media_rls_engine(
    migrated_postgres_urls: MigratedPostgresUrls,
) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated_postgres_urls.media_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def app_rls_engine(
    migrated_postgres_urls: MigratedPostgresUrls,
) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated_postgres_urls.app_url, pool_pre_ping=True)
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


async def _seed_normalization_rows(
    migration_url: str,
    ids: dict[str, UUID | str],
) -> dict[str, UUID]:
    normalization_ids: dict[str, UUID] = {}
    engine = create_async_engine(migration_url, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            for label in ("a", "b"):
                media_revision_id = uuid4()
                backfill_run_id = uuid4()
                job_id = uuid4()
                attempt_id = uuid4()
                normalization_ids[f"media_revision_{label}"] = media_revision_id
                normalization_ids[f"backfill_run_{label}"] = backfill_run_id
                normalization_ids[f"job_{label}"] = job_id
                normalization_ids[f"attempt_{label}"] = attempt_id
                await conn.execute(
                    text(
                        """
                        insert into media_revisions
                            (id, workspace_id, meeting_id, local_media_revision_id,
                             revision_number, source_kind, status, immutable, accepted_at)
                        values
                            (:id, :workspace_id, :meeting_id, :local_media_revision_id,
                             1, 'initial_recording', 'accepted', true, :accepted_at)
                        """
                    ),
                    {
                        "id": media_revision_id,
                        "workspace_id": ids[f"workspace_{label}"],
                        "meeting_id": ids[f"meeting_{label}"],
                        "local_media_revision_id": f"rls-normalization-{label}-{ids['slug']}",
                        "accepted_at": datetime.now(UTC),
                    },
                )
                await conn.execute(
                    text(
                        """
                        insert into playback_backfill_runs (id, workspace_id)
                        values (:id, :workspace_id)
                        """
                    ),
                    {"id": backfill_run_id, "workspace_id": ids[f"workspace_{label}"]},
                )
                await conn.execute(
                    text(
                        """
                        insert into playback_normalization_jobs
                            (id, organization_id, workspace_id, requested_by_user_id,
                             source_device_id, meeting_id, media_revision_id, trigger_kind,
                             priority_class, source_kind, source_fingerprint_sha256,
                             planned_action, workflow_id)
                        values
                            (:id, :organization_id, :workspace_id, :requested_by_user_id,
                             :source_device_id, :meeting_id, :media_revision_id,
                             'finalize', 'new_ingest', 'initial_recording',
                             :source_fingerprint_sha256, 'normalize_source', :workflow_id)
                        """
                    ),
                    {
                        "id": job_id,
                        "organization_id": ids[f"org_{label}"],
                        "workspace_id": ids[f"workspace_{label}"],
                        "requested_by_user_id": ids[f"user_{label}"],
                        "source_device_id": ids[f"device_{label}"],
                        "meeting_id": ids[f"meeting_{label}"],
                        "media_revision_id": media_revision_id,
                        "source_fingerprint_sha256": f"{attempt_id.hex}{attempt_id.hex}",
                        "workflow_id": f"rls-normalization-{job_id}",
                    },
                )
                await conn.execute(
                    text(
                        """
                        insert into playback_normalization_attempts
                            (id, workspace_id, meeting_id, media_revision_id, job_id,
                             attempt_number, cycle_number, storage_object_key,
                             derivation_kind, source_stream_count, source_audio_stream_count)
                        values
                            (:id, :workspace_id, :meeting_id, :media_revision_id, :job_id,
                             1, 1, :storage_object_key, 'dual_source_mix_transcode', 1, 1)
                        """
                    ),
                    {
                        "id": attempt_id,
                        "workspace_id": ids[f"workspace_{label}"],
                        "meeting_id": ids[f"meeting_{label}"],
                        "media_revision_id": media_revision_id,
                        "job_id": job_id,
                        "storage_object_key": f"rls-normalization/{attempt_id}.m4a",
                    },
                )
    finally:
        await engine.dispose()
    return normalization_ids


def _request_context(
    ids: dict[str, UUID | str], label: str, *, context_kind: str = "request"
) -> TenantDatabaseContext:
    return TenantDatabaseContext(
        organization_id=ids[f"org_{label}"],
        workspace_id=ids[f"workspace_{label}"],
        user_id=ids[f"user_{label}"],
        device_id=ids[f"device_{label}"],
        context_kind=context_kind,
    )


@pytest.mark.asyncio
async def test_same_tenant_and_cross_tenant_reads_follow_workspace_context(
    rls_engine: AsyncEngine,
) -> None:
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
        await apply_tenant_context_to_connection(
            conn, _request_context(ids, "a", context_kind="worker")
        )
        worker_count = await conn.scalar(text("select count(*) from meetings"))

    async with rls_engine.connect() as conn:
        await conn.execute(text("select set_config('app.context_kind', 'maintenance', true)"))
        await conn.execute(
            text("select set_config('app.maintenance_operation', 'migration_verification', true)")
        )
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
        await conn.execute(
            text("select set_config('app.context_kind', 'auth_session_lookup', true)")
        )
        await conn.execute(
            text("select set_config('app.auth_session_token_hash', :session_hash, true)"),
            {"session_hash": ids["session_hash_a"]},
        )
        lookup_count = await conn.scalar(text("select count(*) from auth_sessions"))

    assert partial_count == 0
    assert lookup_count == 1


@pytest.mark.asyncio
async def test_auth_callback_completion_requires_auth_bootstrap_context(
    rls_engine: AsyncEngine,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    callback_id = uuid4()
    callback_nonce = f"rls-callback-{ids['slug']}"

    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_rls_postgres_policies",
                reason_category="rls_probe_seed",
                feature_area="security",
            ),
        )
        await conn.execute(
            text(
                """
                insert into auth_callback_states
                    (id, provider, state_nonce, workspace_id, expected_state, expires_at, result)
                values
                    (:id, 'email', :state_nonce, :workspace_id, 'expected', :expires_at, 'pending')
                """
            ),
            {
                "id": callback_id,
                "state_nonce": callback_nonce,
                "workspace_id": ids["workspace_a"],
                "expires_at": datetime.now(UTC) + timedelta(minutes=5),
            },
        )

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(ids, "a"))
        with pytest.raises(Exception, match="row-level security|violates"):
            await conn.execute(
                text("update auth_callback_states set result='completed' where id=:id"),
                {"id": callback_id},
            )
        await conn.rollback()

    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            WorkspaceAuthContext(
                workspace_id=ids["workspace_a"],
                organization_id=ids["org_a"],
                user_id=ids["user_a"],
                context_kind="auth_bootstrap",
            ),
        )
        updated = await conn.scalar(
            text(
                "update auth_callback_states set result='completed' where id=:id returning id"
            ),
            {"id": callback_id},
        )

    assert updated == callback_id


@pytest.mark.asyncio
async def test_normalization_tables_force_rls_and_isolate_request_and_worker_contexts(
    rls_engine: AsyncEngine,
    migrated_postgres_urls: MigratedPostgresUrls,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    normalization_ids = await _seed_normalization_rows(migrated_postgres_urls.migration_url, ids)

    owner_engine = create_async_engine(migrated_postgres_urls.migration_url, pool_pre_ping=True)
    try:
        async with owner_engine.connect() as conn:
            flags = (
                await conn.execute(
                    text(
                        """
                        select relname, relrowsecurity, relforcerowsecurity
                        from pg_class
                        where relname = any(:table_names)
                        order by relname
                        """
                    ),
                    {
                        "table_names": [
                            "playback_backfill_runs",
                            "playback_normalization_attempts",
                            "playback_normalization_jobs",
                        ]
                    },
                )
            ).all()
    finally:
        await owner_engine.dispose()

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(ids, "a"))
        request_counts = {
            table_name: await conn.scalar(text(f"select count(*) from {table_name}"))
            for table_name in (
                "playback_backfill_runs",
                "playback_normalization_jobs",
                "playback_normalization_attempts",
            )
        }
        foreign_job_count = await conn.scalar(
            text("select count(*) from playback_normalization_jobs where id = :job_id"),
            {"job_id": normalization_ids["job_b"]},
        )

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn, _request_context(ids, "a", context_kind="worker")
        )
        worker_job_count = await conn.scalar(
            text("select count(*) from playback_normalization_jobs")
        )

    async with rls_engine.connect() as conn:
        missing_context_count = await conn.scalar(
            text("select count(*) from playback_normalization_jobs")
        )

    assert flags == [
        ("playback_backfill_runs", True, True),
        ("playback_normalization_attempts", True, True),
        ("playback_normalization_jobs", True, True),
    ]
    assert request_counts == {
        "playback_backfill_runs": 1,
        "playback_normalization_jobs": 1,
        "playback_normalization_attempts": 1,
    }
    assert foreign_job_count == 0
    assert worker_job_count == 1
    assert missing_context_count == 0


@pytest.mark.asyncio
async def test_runtime_roles_are_non_superuser_and_cannot_bypass_rls(
    rls_engine: AsyncEngine,
    app_rls_engine: AsyncEngine,
    media_rls_engine: AsyncEngine,
    migrated_postgres_urls: MigratedPostgresUrls,
) -> None:
    async with rls_engine.connect() as conn:
        maintenance_role = await conn.scalar(text("select current_user"))
    async with app_rls_engine.connect() as conn:
        app_role = await conn.scalar(text("select current_user"))
    async with media_rls_engine.connect() as conn:
        media_role = await conn.scalar(text("select current_user"))

    owner_engine = create_async_engine(migrated_postgres_urls.migration_url, pool_pre_ping=True)
    try:
        async with owner_engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        "select rolname, rolsuper, rolcreatedb, rolcreaterole, "
                        "rolreplication, rolbypassrls from pg_roles "
                        "where rolname = any(:role_names) order by rolname"
                    ),
                    {"role_names": [app_role, maintenance_role, media_role]},
                )
            ).all()
    finally:
        await owner_engine.dispose()

    assert app_role == "twobrain_rec_app"
    assert maintenance_role == "twobrain_rec_maintenance"
    assert media_role == "twobrain_rec_media"
    assert len(rows) == 3
    assert all(
        not any(
            (
                row.rolsuper,
                row.rolcreatedb,
                row.rolcreaterole,
                row.rolreplication,
                row.rolbypassrls,
            )
        )
        for row in rows
    )


@pytest.mark.asyncio
async def test_media_role_cannot_spoof_legacy_maintenance_access(
    rls_engine: AsyncEngine,
    media_rls_engine: AsyncEngine,
) -> None:
    await _seed_probe_rows(rls_engine)
    legacy_context = MaintenanceTenantContext(
        operation_name="operator_diagnostics",
        actor_id="spoofed-media-worker",
        reason_category="rls_probe",
        feature_area="playback_normalization",
    )

    async with media_rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(conn, legacy_context)
        legacy_maintenance_allowed = bool(
            await conn.scalar(text("select rec_maintenance_allowed()"))
        )
        visible_meeting_count = int(await conn.scalar(text("select count(*) from meetings")) or 0)
        timestamp_update = await conn.execute(text("update meetings set updated_at = updated_at"))

    async with media_rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(conn, legacy_context)
        with pytest.raises(Exception, match="permission denied"):
            await conn.execute(text("update meetings set status = 'deleted'"))

    assert legacy_maintenance_allowed is False
    assert visible_meeting_count == 0
    assert timestamp_update.rowcount == 0


@pytest.mark.asyncio
async def test_app_role_cannot_spoof_legacy_maintenance_access(
    rls_engine: AsyncEngine,
    app_rls_engine: AsyncEngine,
) -> None:
    await _seed_probe_rows(rls_engine)
    legacy_context = MaintenanceTenantContext(
        operation_name="operator_diagnostics",
        actor_id="spoofed-api-process",
        reason_category="rls_probe",
        feature_area="playback_normalization",
    )

    async with app_rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(conn, legacy_context)
        legacy_maintenance_allowed = bool(
            await conn.scalar(text("select rec_maintenance_allowed()"))
        )
        visible_meeting_count = int(await conn.scalar(text("select count(*) from meetings")) or 0)
        timestamp_update = await conn.execute(text("update meetings set updated_at = updated_at"))
        business_update = await conn.execute(text("update meetings set status = 'deleted'"))

    assert legacy_maintenance_allowed is False
    assert visible_meeting_count == 0
    assert timestamp_update.rowcount == 0
    assert business_update.rowcount == 0


@pytest.mark.asyncio
async def test_production_smoke_setup_uses_maintenance_then_exact_app_context(
    rls_engine: AsyncEngine,
    migrated_postgres_urls: MigratedPostgresUrls,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_id = f"smoke-postgres-{uuid4().hex}"
    seed = build_smoke_identity_seed(run_id)
    maintenance_settings = Settings(database_url=migrated_postgres_urls.probe_url)
    app_settings = Settings(database_url=migrated_postgres_urls.app_url)
    token_file = tmp_path / "smoke-token"
    auth_session_id: str | None = None
    cleanup_result: tuple[int, int, list[str]] | None = None

    class EmptyMinio:
        def list_objects(self, _bucket: str, *, prefix: str, recursive: bool):
            assert prefix.endswith(f"workspaces/{seed.workspace_id}/")
            assert recursive is True
            return []

        def remove_object(self, _bucket: str, _object_name: str) -> None:
            raise AssertionError("empty storage must not remove objects")

    monkeypatch.setattr(
        cleanup_smoke_artifacts_module,
        "Minio",
        lambda *_args, **_kwargs: EmptyMinio(),
    )

    try:
        seed_result = await seed_identity(maintenance_settings, run_id, execute=True)
        assert seed_result["seed_result"] == "pass"

        issued = await issue_smoke_auth_session(
            app_settings,
            run_id=run_id,
            token_file=token_file,
            ttl_seconds=600,
            purpose="production_smoke",
            execute=True,
        )
        auth_session_id = str(issued["auth_session_id"])
        assert issued["auth_session_result"] == "pass"
        assert issued["token_written"] is True
        assert stat.S_IMODE(token_file.stat().st_mode) == 0o600
        assert "bearer" not in str(issued).lower()

        app_engine = create_async_engine(migrated_postgres_urls.app_url, pool_pre_ping=True)
        try:
            async with app_engine.connect() as conn:
                await apply_tenant_context_to_connection(
                    conn,
                    TenantDatabaseContext(
                        organization_id=seed.organization_id,
                        workspace_id=seed.workspace_id,
                        user_id=seed.user_id,
                        device_id=seed.device_id,
                        context_kind="request",
                    ),
                )
                session_count = int(
                    await conn.scalar(
                        text("select count(*) from auth_sessions where id=:auth_session_id"),
                        {"auth_session_id": auth_session_id},
                    )
                    or 0
                )
                binding_count = int(
                    await conn.scalar(
                        text(
                            "select count(*) from auth_session_device_bindings "
                            "where auth_session_id=:auth_session_id"
                        ),
                        {"auth_session_id": auth_session_id},
                    )
                    or 0
                )
        finally:
            await app_engine.dispose()
        assert session_count == 1
        assert binding_count == 1
    finally:
        await cleanup_smoke_auth_session(
            maintenance_settings,
            run_id=run_id,
            auth_session_id=auth_session_id,
            execute=True,
        )
        monkeypatch.setenv("TWOBRAIN_DATABASE_URL", migrated_postgres_urls.probe_url)
        cleanup_result = await cleanup_smoke_artifacts(run_id)
        token_file.unlink(missing_ok=True)

    assert cleanup_result is not None
    removed_rows, removed_objects, residue = cleanup_result
    assert removed_rows >= 5
    assert removed_objects == 0
    assert residue == []
    assert not token_file.exists()

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="production_smoke_cleanup",
                actor_id="test_rls_postgres_policies",
                reason_category="residue_probe",
                feature_area="deployment",
            ),
        )
        residue_count = int(
            await conn.scalar(
                text(
                    """
                    select
                        (select count(*) from organizations where id=:organization_id)
                      + (select count(*) from workspaces where id=:workspace_id)
                      + (select count(*) from user_identities where id=:user_id)
                      + (select count(*) from registered_devices where id=:device_id)
                      + (select count(*) from auth_sessions where workspace_id=:workspace_id)
                    """
                ),
                {
                    "organization_id": str(seed.organization_id),
                    "workspace_id": str(seed.workspace_id),
                    "user_id": str(seed.user_id),
                    "device_id": str(seed.device_id),
                },
            )
            or 0
        )
    assert residue_count == 0


@pytest.mark.asyncio
async def test_production_smoke_cleanup_discovers_partial_upload_and_normalization_residue(
    migrated_postgres_urls: MigratedPostgresUrls,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = f"smoke-partial-{uuid4().hex}"
    seed = build_smoke_identity_seed(run_id)
    maintenance_settings = Settings(database_url=migrated_postgres_urls.probe_url)
    await seed_identity(maintenance_settings, run_id, execute=True)

    meeting_id = uuid4()
    media_revision_id = uuid4()
    upload_session_id = uuid4()
    normalization_job_id = uuid4()
    normalization_attempt_id = uuid4()
    prefix = (
        f"organizations/{seed.organization_id}/workspaces/{seed.workspace_id}/"
        f"meetings/{meeting_id}/"
    )
    upload_object_key = f"{prefix}sessions/{upload_session_id}/tracks/microphone/parts/00000000"
    track_object_key = f"{prefix}artifacts/media-revisions/{media_revision_id}/tracks/microphone"
    attempt_object_key = (
        f"{prefix}artifacts/playback-normalization/revisions/{media_revision_id}/"
        f"attempts/{normalization_attempt_id}/meeting-review.m4a"
    )
    orphan_object_key = f"{prefix}orphaned-before-database-write"

    app_engine = create_async_engine(migrated_postgres_urls.app_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(app_engine, expire_on_commit=False)
    try:
        async with session_factory() as db:
            await apply_tenant_context_to_connection(
                await db.connection(),
                TenantDatabaseContext(
                    organization_id=seed.organization_id,
                    workspace_id=seed.workspace_id,
                    user_id=seed.user_id,
                    device_id=seed.device_id,
                    context_kind="request",
                ),
            )
            db.add(
                Meeting(
                    id=meeting_id,
                    workspace_id=seed.workspace_id,
                    created_by_user_id=seed.user_id,
                    device_id=seed.device_id,
                    local_recording_id=f"partial-{run_id}",
                    duration_seconds=3,
                    status="ingested_pending_processing",
                )
            )
            await db.flush()
            db.add(
                MediaRevision(
                    id=media_revision_id,
                    workspace_id=seed.workspace_id,
                    meeting_id=meeting_id,
                    local_media_revision_id=f"partial-{run_id}",
                    revision_number=1,
                    source_kind="initial_recording",
                    status="accepted",
                    immutable=True,
                    accepted_at=datetime.now(UTC),
                )
            )
            await db.flush()
            db.add(
                UploadSession(
                    id=upload_session_id,
                    meeting_id=meeting_id,
                    media_revision_id=media_revision_id,
                    workspace_id=seed.workspace_id,
                    device_id=seed.device_id,
                    created_by_user_id=seed.user_id,
                    expected_track_roles=["microphone"],
                    expected_track_sizes={"microphone": 16},
                    max_package_bytes_snapshot=1024,
                    max_track_bytes_snapshot=1024,
                    expires_at=datetime.now(UTC) + timedelta(minutes=10),
                )
            )
            await db.flush()
            db.add(
                PlaybackNormalizationJob(
                    id=normalization_job_id,
                    organization_id=seed.organization_id,
                    workspace_id=seed.workspace_id,
                    requested_by_user_id=seed.user_id,
                    source_device_id=seed.device_id,
                    meeting_id=meeting_id,
                    media_revision_id=media_revision_id,
                    trigger_kind="finalize",
                    priority_class="new_ingest",
                    source_kind="initial_recording",
                    source_fingerprint_sha256="c" * 64,
                    planned_action="normalize_source",
                    state="queued",
                    workflow_id=f"partial-{run_id}",
                )
            )
            await db.flush()
            db.add_all(
                [
                    UploadPart(
                        upload_session_id=upload_session_id,
                        track_role="microphone",
                        part_number=0,
                        byte_offset=0,
                        byte_length=16,
                        sha256="a" * 64,
                        storage_object_key=upload_object_key,
                    ),
                    TemporaryUploadObject(
                        upload_session_id=upload_session_id,
                        media_revision_id=media_revision_id,
                        workspace_id=seed.workspace_id,
                        storage_object_key=upload_object_key,
                        byte_length=16,
                    ),
                    TrackArtifact(
                        meeting_id=meeting_id,
                        media_revision_id=media_revision_id,
                        workspace_id=seed.workspace_id,
                        track_role="microphone",
                        codec="pcm_s16le",
                        sample_rate_hz=48_000,
                        channel_count=1,
                        duration_seconds=3,
                        byte_length=16,
                        sha256="b" * 64,
                        storage_object_key=track_object_key,
                        status="stored",
                    ),
                    IngestAuditEvent(
                        workspace_id=seed.workspace_id,
                        meeting_id=meeting_id,
                        media_revision_id=media_revision_id,
                        upload_session_id=upload_session_id,
                        actor_user_id=seed.user_id,
                        device_id=seed.device_id,
                        event_type="part_accepted",
                        metadata_json={"track_role": "microphone"},
                    ),
                    PlaybackNormalizationAttempt(
                        id=normalization_attempt_id,
                        workspace_id=seed.workspace_id,
                        meeting_id=meeting_id,
                        media_revision_id=media_revision_id,
                        job_id=normalization_job_id,
                        attempt_number=1,
                        cycle_number=1,
                        state="local_preparing",
                        storage_object_key=attempt_object_key,
                        derivation_kind="single_source_transcode",
                        source_stream_count=1,
                        source_audio_stream_count=1,
                    ),
                ]
            )
            await db.commit()
    finally:
        await app_engine.dispose()

    class FakeObject:
        def __init__(self, object_name: str) -> None:
            self.object_name = object_name

    class FakeMinio:
        def __init__(self) -> None:
            self.objects = {
                upload_object_key,
                track_object_key,
                attempt_object_key,
                orphan_object_key,
            }

        def list_objects(self, _bucket: str, *, prefix: str, recursive: bool):
            assert recursive is True
            return [FakeObject(name) for name in sorted(self.objects) if name.startswith(prefix)]

        def remove_object(self, _bucket: str, object_name: str) -> None:
            self.objects.remove(object_name)

    fake_minio = FakeMinio()
    monkeypatch.setattr(
        cleanup_smoke_artifacts_module,
        "Minio",
        lambda *_args, **_kwargs: fake_minio,
    )
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", migrated_postgres_urls.probe_url)
    removed_rows, removed_objects, residue = await cleanup_smoke_artifacts(run_id)

    assert removed_rows >= 12
    assert removed_objects == 4
    assert residue == []
    assert fake_minio.objects == set()

    rerun_removed_rows, rerun_removed_objects, rerun_residue = await cleanup_smoke_artifacts(
        run_id
    )
    assert rerun_removed_rows == 0
    assert rerun_removed_objects == 0
    assert rerun_residue == []


def test_production_smoke_setup_migration_downgrade_removes_operation(
    migrated_postgres_urls: MigratedPostgresUrls,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def setup_allowed() -> bool:
        engine = create_async_engine(migrated_postgres_urls.probe_url, pool_pre_ping=True)
        try:
            async with engine.connect() as conn:
                await apply_tenant_context_to_connection(
                    conn,
                    MaintenanceTenantContext(
                        operation_name="production_smoke_setup",
                        actor_id="test_rls_postgres_policies",
                        reason_category="migration_probe",
                        feature_area="deployment",
                    ),
                )
                return bool(await conn.scalar(text("select rec_maintenance_allowed()")))
        finally:
            await engine.dispose()

    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", migrated_postgres_urls.migration_url)
    get_settings.cache_clear()
    config = Config(str(REPO_ROOT / "apps/server/alembic.ini"))
    config.set_main_option(
        "script_location",
        str(REPO_ROOT / "apps/server/src/twobrain_rec_server/db/migrations"),
    )

    assert asyncio.run(setup_allowed()) is True
    try:
        command.downgrade(config, "0022_playback_normalization")
        assert asyncio.run(setup_allowed()) is False
    finally:
        command.upgrade(config, "head")
        get_settings.cache_clear()
    assert asyncio.run(setup_allowed()) is True


@pytest.mark.asyncio
async def test_normalization_rls_rejects_cross_workspace_write(
    rls_engine: AsyncEngine,
    migrated_postgres_urls: MigratedPostgresUrls,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    normalization_ids = await _seed_normalization_rows(migrated_postgres_urls.migration_url, ids)

    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(ids, "a"))
        with pytest.raises(Exception, match="row-level security|violates"):
            await conn.execute(
                text(
                    """
                    insert into playback_normalization_jobs
                        (id, organization_id, workspace_id, requested_by_user_id,
                         source_device_id, meeting_id, media_revision_id, trigger_kind,
                         priority_class, source_kind, source_fingerprint_sha256,
                         planned_action, workflow_id)
                    values
                        (:id, :organization_id, :workspace_id, :requested_by_user_id,
                         :source_device_id, :meeting_id, :media_revision_id,
                         'finalize', 'new_ingest', 'initial_recording',
                         :source_fingerprint_sha256, 'normalize_source', :workflow_id)
                    """
                ),
                {
                    "id": uuid4(),
                    "organization_id": ids["org_b"],
                    "workspace_id": ids["workspace_b"],
                    "requested_by_user_id": ids["user_b"],
                    "source_device_id": ids["device_b"],
                    "meeting_id": ids["meeting_b"],
                    "media_revision_id": normalization_ids["media_revision_b"],
                    "source_fingerprint_sha256": uuid4().hex * 2,
                    "workflow_id": f"rls-cross-workspace-{uuid4()}",
                },
            )


@pytest.mark.asyncio
async def test_normalization_maintenance_operations_are_exact_select_only_boundaries(
    rls_engine: AsyncEngine,
    media_rls_engine: AsyncEngine,
    migrated_postgres_urls: MigratedPostgresUrls,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    await _seed_normalization_rows(migrated_postgres_urls.migration_url, ids)

    # An application role cannot gain scheduler visibility by spoofing GUCs.
    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="playback_normalization_inventory",
                actor_id="test_rls_postgres_policies",
                reason_category="rls_probe",
                feature_area="playback_normalization",
            ),
        )
        app_inventory_job_count = await conn.scalar(
            text("select count(*) from playback_normalization_jobs")
        )
        app_inventory_backfill_count = await conn.scalar(
            text("select count(*) from playback_backfill_runs")
        )
        app_inventory_attempt_count = await conn.scalar(
            text("select count(*) from playback_normalization_attempts")
        )
        app_update_result = await conn.execute(
            text("update playback_normalization_jobs set state = 'running' where state = 'queued'")
        )
    async with rls_engine.connect() as conn:
        app_workspace_function_execute = await conn.scalar(
            text(
                "select has_function_privilege(current_user, "
                "'rec_playback_normalization_workspace_page(uuid, integer)', 'execute')"
            )
        )
        app_cleanup_function_execute = await conn.scalar(
            text(
                "select has_function_privilege(current_user, "
                "'rec_playback_normalization_cleanup_page(integer)', 'execute')"
            )
        )

    # Only the dedicated non-bypass media login receives scheduler SELECT/function access.
    async with media_rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="playback_normalization_inventory",
                actor_id="test_rls_postgres_policies",
                reason_category="rls_probe",
                feature_area="playback_normalization",
            ),
        )
        inventory_job_count = await conn.scalar(
            text("select count(*) from playback_normalization_jobs")
        )
        inventory_backfill_count = await conn.scalar(
            text("select count(*) from playback_backfill_runs")
        )
        inventory_attempt_count = await conn.scalar(
            text("select count(*) from playback_normalization_attempts")
        )
        workspace_page_count = await conn.scalar(
            text("select count(*) from rec_playback_normalization_workspace_page(null, 50)")
        )
        update_result = await conn.execute(
            text("update playback_normalization_jobs set state = 'running' where state = 'queued'")
        )

    async with media_rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="playback_normalization_dispatch",
                actor_id="test_rls_postgres_policies",
                reason_category="rls_probe",
                feature_area="playback_normalization",
            ),
        )
        dispatch_job_count = await conn.scalar(
            text("select count(*) from playback_normalization_jobs")
        )
        cleanup_page_count = await conn.scalar(
            text("select count(*) from rec_playback_normalization_cleanup_page(25)")
        )
        media_workspace_function_execute = await conn.scalar(
            text(
                "select has_function_privilege(current_user, "
                "'rec_playback_normalization_workspace_page(uuid, integer)', 'execute')"
            )
        )
        media_cleanup_function_execute = await conn.scalar(
            text(
                "select has_function_privilege(current_user, "
                "'rec_playback_normalization_cleanup_page(integer)', 'execute')"
            )
        )

    async with media_rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="playback_normalization_inventory",
                actor_id="test_rls_postgres_policies",
                reason_category="rls_probe",
                feature_area="security",
            ),
        )
        wrong_feature_count = await conn.scalar(
            text("select count(*) from playback_normalization_jobs")
        )
        wrong_feature_page_count = await conn.scalar(
            text("select count(*) from rec_playback_normalization_workspace_page(null, 50)")
        )

    assert app_inventory_job_count == 0
    assert app_inventory_backfill_count == 0
    assert app_inventory_attempt_count == 0
    assert app_update_result.rowcount == 0
    assert app_workspace_function_execute is False
    assert app_cleanup_function_execute is False
    assert inventory_job_count >= 2
    assert inventory_backfill_count >= 2
    assert inventory_attempt_count == 0
    assert workspace_page_count >= 2
    assert update_result.rowcount == 0
    assert dispatch_job_count >= 2
    assert cleanup_page_count >= 2
    assert media_workspace_function_execute is True
    assert media_cleanup_function_execute is True
    assert wrong_feature_count == 0
    assert wrong_feature_page_count == 0
