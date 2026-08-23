from __future__ import annotations

import asyncio
import os
import stat
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

import scripts.cleanup_smoke_artifacts as cleanup_smoke_artifacts_module
from scripts.cleanup_smoke_artifacts import cleanup_smoke_artifacts
from scripts.cleanup_smoke_auth_session import cleanup_smoke_auth_session
from scripts.issue_smoke_auth_session import issue_smoke_auth_session
from scripts.seed_smoke_identity import seed_identity
from tests.fixtures.postgres_rls import optional_rls_test_database_url, rls_test_database_url
from tests.fixtures.postgres_test_database import ensure_disposable_media_role
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth import callbacks as callbacks_module
from twobrain_rec_server.auth.account_closure import (
    begin_account_close_finalization,
    ensure_account_membership_activation_allowed,
)
from twobrain_rec_server.auth.account_merge import (
    _merge_preview_from_db,
    confirm_merge_intent,
    preview_merge_intent,
)
from twobrain_rec_server.auth.callbacks import (
    CallbackFlowError,
    resolve_callback_to_provider_link,
)
from twobrain_rec_server.auth.context import AuthenticatedPrincipal
from twobrain_rec_server.auth.provider_links import (
    ProviderLinkError,
    apply_provider_link_auth_context,
    apply_provider_link_request_context,
    confirm_provider_link,
    create_link_intent,
    link_for_callback,
)
from twobrain_rec_server.auth.providers.base import ProviderCredentials, ProviderIdentity
from twobrain_rec_server.auth.sessions import fingerprint_identity, hash_token
from twobrain_rec_server.auth.workspace_onboarding import activate_workspace_session
from twobrain_rec_server.billing.fair_use import (
    appeal_persisted_review,
    fair_use_restricted_for_lineage,
)
from twobrain_rec_server.billing.referral_binding import referral_attribution_exists_for_lineage
from twobrain_rec_server.billing.trial import trial_used_by_lineage
from twobrain_rec_server.cabinet.auth_return import resolve_browser_auth_return_path
from twobrain_rec_server.cabinet.web_routes.auth_email_flow import (
    EmailLinkCompletion,
    EmailLoginCompletion,
    _consume_email_login_code,
    _create_email_login_state,
    _email_auth_browser_cookie_name,
    consume_email_link_code,
)
from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.db.models import (
    AuthAuditEvent,
    AuthCallbackState,
    ExternalIdentity,
    IngestAuditEvent,
    MediaRevision,
    Meeting,
    MeetingShareRateLimitBucket,
    PlaybackNormalizationAttempt,
    PlaybackNormalizationJob,
    ProcessingDependencyState,
    TemporaryUploadObject,
    TrackArtifact,
    UploadPart,
    UploadSession,
    WorkspaceProviderLinkState,
)
from twobrain_rec_server.db.tenant_context import (
    AccountMergeTenantContext,
    AuthCallbackLookupContext,
    AuthReferralUserLookupContext,
    MaintenanceTenantContext,
    TenantDatabaseContext,
    WorkspaceAuthContext,
    apply_tenant_context,
    apply_tenant_context_to_connection,
)
from twobrain_rec_server.deployment import build_smoke_identity_seed

REPO_ROOT = Path(__file__).resolve().parents[4]
MEDIA_READ_ONLY_TABLES = (
    "alembic_version",
    "meetings",
    "media_revisions",
    "workspace_subscriptions",
    "workspaces",
)
MEDIA_READ_WRITE_TABLES = (
    "playback_backfill_runs",
    "playback_normalization_attempts",
    "playback_normalization_jobs",
    "storage_reservations",
    "support_incidents",
    "track_artifacts",
)
MEDIA_INSERT_ONLY_TABLES = ("ingest_audit_events",)
MEDIA_LOCK_COLUMNS = (("meetings", "updated_at"), ("media_revisions", "updated_at"))
pytestmark = pytest.mark.strict_rls


@dataclass(frozen=True, slots=True)
class MigratedPostgresUrls:
    migration_url: str
    probe_url: str
    app_url: str
    media_url: str
    probe_role: str | None = None
    app_role: str | None = None
    media_role_created: bool = False


TEST_WEB_CSRF_SECRET = "rls-email-auth-test-secret"
TEST_EMAIL_AUTH_BROWSER_NONCE = "rls-email-auth-browser-nonce"


def _email_auth_request(
    settings: Settings,
    *,
    path: str = "/login/email/verify",
    state_nonce: str | None = None,
) -> Request:
    headers = []
    if state_nonce is not None:
        cookie_name = _email_auth_browser_cookie_name(state_nonce=state_nonce, secure=True)
        headers.append(
            (
                b"cookie",
                f"{cookie_name}={TEST_EMAIL_AUTH_BROWSER_NONCE}".encode("ascii"),
            )
        )
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": headers,
            "client": ("127.0.0.1", 41000),
            "app": SimpleNamespace(
                state=SimpleNamespace(
                    settings=settings,
                    web_csrf_secret=TEST_WEB_CSRF_SECRET,
                )
            ),
        }
    )


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
            await conn.execute(
                text(
                    f"grant execute on function rec_account_merge_context_valid() to {quoted_role}"
                )
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
                pytest.fail(
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
            exists = bool(
                await conn.scalar(
                    text("select exists(select 1 from pg_roles where rolname = :role_name)"),
                    {"role_name": role_name},
                )
            )
            if not exists:
                return
            quoted_role = _quote_identifier(role_name)
            await conn.execute(text(f"drop owned by {quoted_role}"))
            await conn.execute(text(f"drop role if exists {quoted_role}"))
    finally:
        await engine.dispose()


@asynccontextmanager
async def _exact_app_role_engine(migration_url: str) -> AsyncIterator[AsyncEngine]:
    await _drop_probe_role(migration_url, "twobrain_rec_app")
    role_name, password = await _create_probe_role(
        migration_url,
        role_name="twobrain_rec_app",
    )
    try:
        app_engine = create_async_engine(
            make_url(migration_url)
            .set(username=role_name, password=password)
            .render_as_string(hide_password=False),
            pool_pre_ping=True,
        )
        try:
            yield app_engine
        finally:
            await app_engine.dispose()
    finally:
        await _drop_probe_role(migration_url, role_name)


@pytest.fixture(scope="module")
def migrated_postgres_urls(postgres_advisory_lock: None) -> Iterator[MigratedPostgresUrls]:
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
    probe_url = optional_rls_test_database_url("RLS_TEST_PROBE_DATABASE_URL")
    if not probe_url:
        probe_role, password = asyncio.run(
            _create_probe_role(url, role_name="twobrain_rec_maintenance")
        )
        probe_url = (
            make_url(url)
            .set(username=probe_role, password=password)
            .render_as_string(hide_password=False)
        )
    app_role: str | None = None
    app_url = optional_rls_test_database_url("RLS_TEST_APP_DATABASE_URL")
    if not app_url:
        app_role, app_password = asyncio.run(
            _create_probe_role(url, role_name=f"twobrain_rec_app_{uuid4().hex[:12]}")
        )
        app_url = (
            make_url(url)
            .set(username=app_role, password=app_password)
            .render_as_string(hide_password=False)
        )
    media_role_created = False
    media_url = optional_rls_test_database_url("RLS_TEST_MEDIA_DATABASE_URL")
    if media_url:
        media_url = asyncio.run(
            ensure_disposable_media_role(
                url,
                media_database_url=media_url,
            )
        )
    else:
        media_url, media_role_created = asyncio.run(_create_media_role(url))
    try:
        yield MigratedPostgresUrls(
            migration_url=url,
            probe_url=probe_url,
            app_url=app_url,
            media_url=media_url,
            probe_role=probe_role,
            app_role=app_role,
            media_role_created=media_role_created,
        )
    finally:
        if probe_role is not None:
            asyncio.run(_drop_probe_role(url, probe_role))
        if app_role is not None:
            asyncio.run(_drop_probe_role(url, app_role))
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


@pytest.mark.asyncio
async def test_account_linking_migration_has_exact_binding_and_operation_policies(
    migrated_postgres_urls: MigratedPostgresUrls,
) -> None:
    engine = create_async_engine(migrated_postgres_urls.migration_url, pool_pre_ping=True)
    table_names = (
        "user_identities",
        "external_identities",
        "auth_callback_states",
        "workspace_provider_link_states",
        "account_merge_intents",
        "account_merge_journals",
    )
    try:
        async with engine.connect() as conn:
            column = (
                await conn.execute(
                    text(
                        """
                        select is_nullable
                        from information_schema.columns
                        where table_schema = 'public'
                          and table_name = 'auth_callback_states'
                          and column_name = 'verified_external_identity_id'
                        """
                    )
                )
            ).one()
            foreign_key = await conn.scalar(
                text(
                    """
                    select pg_get_constraintdef(oid)
                    from pg_constraint
                    where conname = 'fk_auth_callback_states_verified_external_identity'
                      and conrelid = 'auth_callback_states'::regclass
                    """
                )
            )
            index_definition = await conn.scalar(
                text(
                    """
                    select indexdef
                    from pg_indexes
                    where schemaname = 'public'
                      and tablename = 'auth_callback_states'
                      and indexname = 'ix_auth_callback_states_verified_external_identity'
                    """
                )
            )
            policy_rows = (
                await conn.execute(
                    text(
                        """
                        select tablename, policyname, cmd, qual, with_check
                        from pg_policies
                        where schemaname = 'public'
                          and tablename in (
                              'user_identities', 'external_identities',
                              'auth_callback_states', 'workspace_provider_link_states',
                              'account_merge_intents', 'account_merge_journals'
                          )
                        order by tablename, cmd
                        """
                    )
                )
            ).all()
    finally:
        await engine.dispose()

    assert column.is_nullable == "YES"
    assert foreign_key is not None
    assert "FOREIGN KEY (verified_external_identity_id)" in foreign_key
    assert "REFERENCES external_identities(id)" in foreign_key
    assert index_definition is not None
    assert "(verified_external_identity_id)" in index_definition

    policies_by_table: dict[str, dict[str, object]] = {}
    for row in policy_rows:
        assert row.policyname != f"{row.tablename}_tenant_isolation"
        assert row.cmd != "ALL"
        rendered = f"{row.qual or ''} {row.with_check or ''}"
        assert "rec_maintenance_allowed()" in rendered
        assert "rec_context_kind() = 'maintenance'" in rendered
        if "'account_merge'" in rendered:
            assert "rec_account_merge_context_valid()" in rendered
        policies_by_table.setdefault(row.tablename, {})[row.cmd] = row

    assert set(policies_by_table) == set(table_names)
    assert all(
        set(command_rows) == {"SELECT", "INSERT", "UPDATE", "DELETE"}
        for command_rows in policies_by_table.values()
    )


async def _seed_content_export_rows(
    engine: AsyncEngine,
    ids: dict[str, UUID | str],
) -> None:
    async with engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_rls_postgres_policies",
                reason_category="content_export_rls_seed",
                feature_area="security",
            ),
        )
        for label in ("a", "b"):
            workflow_id = uuid4()
            job_id = uuid4()
            result_id = uuid4()
            segment_id = uuid4()
            outcome_set_id = uuid4()
            ids[f"result_{label}"] = result_id
            await conn.execute(
                text(
                    """
                    insert into processing_workflows
                        (id, meeting_id, workspace_id, workflow_id, status, attempt_count)
                    values (:id, :meeting_id, :workspace_id, :workflow_id, 'completed', 1)
                    """
                ),
                {
                    "id": workflow_id,
                    "meeting_id": ids[f"meeting_{label}"],
                    "workspace_id": ids[f"workspace_{label}"],
                    "workflow_id": f"rls-export-workflow-{label}-{ids['slug']}",
                },
            )
            await conn.execute(
                text(
                    """
                    insert into mediascribe_jobs
                        (id, meeting_id, workspace_id, processing_workflow_id, status,
                         request_mode, diarize, summarize)
                    values
                        (:id, :meeting_id, :workspace_id, :workflow_id, 'ready',
                         'mixed', true, false)
                    """
                ),
                {
                    "id": job_id,
                    "meeting_id": ids[f"meeting_{label}"],
                    "workspace_id": ids[f"workspace_{label}"],
                    "workflow_id": workflow_id,
                },
            )
            await conn.execute(
                text(
                    """
                    insert into processing_results
                        (id, meeting_id, workspace_id, mediascribe_job_id, result_version,
                         status, transcript_status, diarization_status, summary_status,
                         language, segment_count, diarization_segment_count)
                    values
                        (:id, :meeting_id, :workspace_id, :job_id, 1, 'imported',
                         'available', 'available', 'available', 'ru', 1, 1)
                    """
                ),
                {
                    "id": result_id,
                    "meeting_id": ids[f"meeting_{label}"],
                    "workspace_id": ids[f"workspace_{label}"],
                    "job_id": job_id,
                },
            )
            common = {
                "workspace_id": ids[f"workspace_{label}"],
                "meeting_id": ids[f"meeting_{label}"],
                "result_id": result_id,
            }
            await conn.execute(
                text(
                    """
                    insert into transcript_segments
                        (id, processing_result_id, meeting_id, workspace_id, sequence,
                         start_seconds, end_seconds, text, source_role)
                    values
                        (:id, :result_id, :meeting_id, :workspace_id, 0, 0, 1,
                         'synthetic export rls text', 'incoming')
                    """
                ),
                {**common, "id": segment_id},
            )
            await conn.execute(
                text(
                    """
                    insert into diarization_segments
                        (id, processing_result_id, meeting_id, workspace_id, sequence,
                         start_seconds, end_seconds, speaker_label, text, source_role)
                    values
                        (:id, :result_id, :meeting_id, :workspace_id, 0, 0, 1,
                         'speaker-a', 'synthetic export rls text', 'incoming')
                    """
                ),
                {**common, "id": uuid4()},
            )
            await conn.execute(
                text(
                    """
                    insert into meeting_speaker_names
                        (id, workspace_id, meeting_id, speaker_key, display_name,
                         updated_by_user_id)
                    values
                        (:id, :workspace_id, :meeting_id, 'speaker_00', 'Synthetic', :user_id)
                    """
                ),
                {
                    **common,
                    "id": uuid4(),
                    "user_id": ids[f"user_{label}"],
                },
            )
            await conn.execute(
                text(
                    """
                    insert into meeting_outcome_sets
                        (id, workspace_id, meeting_id, processing_result_id, status,
                         summary_state, key_points_state, decisions_state,
                         action_items_state, followups_state, risks_state,
                         questions_state, evidence_state, source_kind, generator_kind,
                         generator_version, lifecycle_state)
                    values
                        (:id, :workspace_id, :meeting_id, :result_id, 'available',
                         'available', 'not_found', 'not_found', 'not_found', 'not_found',
                         'not_found', 'not_found', 'available', 'stored_output',
                         'deterministic_extractive', 'rls-fixture-v1', 'active')
                    """
                ),
                {**common, "id": outcome_set_id},
            )
            await conn.execute(
                text(
                    """
                    insert into meeting_outcome_items
                        (id, workspace_id, meeting_id, outcome_set_id, category,
                         sequence, state, text, truth_label, source_refs_json)
                    values
                        (:id, :workspace_id, :meeting_id, :outcome_set_id, 'summary',
                         0, 'available', 'synthetic summary', 'supported', '[]'::json)
                    """
                ),
                {
                    **common,
                    "id": uuid4(),
                    "outcome_set_id": outcome_set_id,
                },
            )
            await conn.execute(
                text(
                    """
                    insert into meeting_artifact_policies
                        (id, workspace_id, meeting_id, audio_download,
                         transcript_download, summary_download, package_export,
                         policy_source)
                    values
                        (:id, :workspace_id, :meeting_id, 'disabled', 'allowed',
                         'allowed', 'disabled', 'rls_fixture')
                    """
                ),
                {**common, "id": uuid4()},
            )
            await conn.execute(
                text(
                    """
                    insert into meeting_egress_audit_events
                        (id, workspace_id, meeting_id, actor_user_id, device_id,
                         event_type, artifact_class, policy_reason, outcome, metadata_json)
                    values
                        (:id, :workspace_id, :meeting_id, :user_id, :device_id,
                         'content_export_completed', 'transcript', 'policy_allowed',
                         'completed', '{}'::json)
                    """
                ),
                {
                    **common,
                    "id": uuid4(),
                    "user_id": ids[f"user_{label}"],
                    "device_id": ids[f"device_{label}"],
                },
            )


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
async def test_content_export_sources_and_audit_sink_are_tenant_isolated(
    rls_engine: AsyncEngine,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    await _seed_content_export_rows(rls_engine, ids)
    export_tables = (
        "transcript_segments",
        "diarization_segments",
        "meeting_speaker_names",
        "meeting_outcome_sets",
        "meeting_outcome_items",
        "meeting_artifact_policies",
        "meeting_egress_audit_events",
    )

    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(ids, "a"))
        visible_counts = {
            table_name: await conn.scalar(text(f"select count(*) from {table_name}"))
            for table_name in export_tables
        }
        foreign_counts = {
            table_name: await conn.scalar(
                text(f"select count(*) from {table_name} where workspace_id=:workspace_id"),
                {"workspace_id": ids["workspace_b"]},
            )
            for table_name in export_tables
        }
        await conn.execute(
            text(
                """
                insert into meeting_egress_audit_events
                    (id, workspace_id, meeting_id, actor_user_id, device_id,
                     event_type, artifact_class, policy_reason, outcome, metadata_json)
                values
                    (:id, :workspace_id, :meeting_id, :user_id, :device_id,
                     'content_export_requested', 'transcript', 'policy_allowed',
                     'allowed', '{}'::json)
                """
            ),
            {
                "id": uuid4(),
                "workspace_id": ids["workspace_a"],
                "meeting_id": ids["meeting_a"],
                "user_id": ids["user_a"],
                "device_id": ids["device_a"],
            },
        )

    assert visible_counts == {table_name: 1 for table_name in export_tables}
    assert foreign_counts == {table_name: 0 for table_name in export_tables}

    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(ids, "a"))
        with pytest.raises(DBAPIError, match="row-level security|violates"):
            await conn.execute(
                text(
                    """
                    insert into meeting_egress_audit_events
                        (id, workspace_id, meeting_id, actor_user_id, device_id,
                         event_type, artifact_class, policy_reason, outcome, metadata_json)
                    values
                        (:id, :workspace_id, :meeting_id, :user_id, :device_id,
                         'content_export_requested', 'transcript', 'policy_allowed',
                         'allowed', '{}'::json)
                    """
                ),
                {
                    "id": uuid4(),
                    "workspace_id": ids["workspace_b"],
                    "meeting_id": ids["meeting_b"],
                    "user_id": ids["user_b"],
                    "device_id": ids["device_b"],
                },
            )


@pytest.mark.asyncio
async def test_join_offers_are_visible_only_to_their_owner(rls_engine: AsyncEngine) -> None:
    ids = await _seed_probe_rows(rls_engine)
    offer_ids = {"a": uuid4(), "b": uuid4()}

    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_rls_postgres_policies",
                reason_category="join_offer_seed",
                feature_area="security",
            ),
        )
        for label in ("a", "b"):
            invitation_id = uuid4()
            await conn.execute(
                text(
                    """
                    insert into workspace_invitations
                        (id, workspace_id, target_contact, invited_role, status, source,
                         created_by_user_id, expires_at, metadata_json)
                    values
                        (:id, :workspace_id, :target_contact, 'member', 'pending', 'admin',
                         :created_by_user_id, now() + interval '1 day', '{}'::json)
                    """
                ),
                {
                    "id": invitation_id,
                    "workspace_id": ids[f"workspace_{label}"],
                    "target_contact": f"offer-{label}-{ids['slug']}@example.test",
                    "created_by_user_id": ids[f"user_{label}"],
                },
            )
            await conn.execute(
                text(
                    """
                    insert into workspace_join_offers
                        (id, workspace_id, user_id, invitation_id, workspace_name, invited_role, status, expires_at)
                    values
                        (:id, :workspace_id, :user_id, :invitation_id, 'RLS offer', 'member', 'offered',
                         now() + interval '1 day')
                    """
                ),
                {
                    "id": offer_ids[label],
                    "workspace_id": ids[f"workspace_{label}"],
                    "user_id": ids[f"user_{label}"],
                    "invitation_id": invitation_id,
                },
            )

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(ids, "a"))
        visible_offer_ids = set(
            (await conn.scalars(text("select id from workspace_join_offers"))).all()
        )

    assert visible_offer_ids == {offer_ids["a"]}


@pytest.mark.asyncio
async def test_auth_bootstrap_can_list_only_own_active_spaces_without_cross_workspace_writes(
    rls_engine: AsyncEngine,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    second_workspace_id = uuid4()

    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_rls_postgres_policies",
                reason_category="active_space_seed",
                feature_area="security",
            ),
        )
        await conn.execute(
            text(
                """
                insert into workspaces (id, organization_id, slug, name, kind)
                values (:id, :organization_id, :slug, 'RLS Second Space', 'corporate')
                """
            ),
            {
                "id": second_workspace_id,
                "organization_id": ids["org_a"],
                "slug": f"rls-second-space-{ids['slug']}",
            },
        )
        await conn.execute(
            text(
                """
                insert into workspace_memberships (workspace_id, user_id, role, status)
                values (:workspace_id, :user_id, 'member', 'active')
                """
            ),
            {"workspace_id": second_workspace_id, "user_id": ids["user_a"]},
        )

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn,
            WorkspaceAuthContext(
                workspace_id=ids["workspace_a"],
                organization_id=ids["org_a"],
                user_id=ids["user_a"],
                context_kind="auth_bootstrap",
            ),
        )
        visible_workspace_ids = set(
            (await conn.scalars(text("select workspace_id from workspace_memberships"))).all()
        )
        with pytest.raises(DBAPIError):
            await conn.execute(
                text(
                    """
                    update workspace_memberships
                    set status = 'revoked'
                    where workspace_id = :workspace_id
                    returning workspace_id
                    """
                ),
                {"workspace_id": second_workspace_id},
            )
        await conn.rollback()

    assert visible_workspace_ids == {ids["workspace_a"], second_workspace_id}


@pytest.mark.asyncio
async def test_active_space_switch_replaces_session_inside_rls_context(
    rls_engine: AsyncEngine,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    target_workspace_id = uuid4()
    provider_subject = f"rls-switch-yandex-{ids['slug']}"

    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_rls_postgres_policies",
                reason_category="active_space_switch_seed",
                feature_area="security",
            ),
        )
        await conn.execute(
            text(
                """
                insert into workspaces (id, organization_id, slug, name, kind)
                values (:id, :organization_id, :slug, 'RLS Switch Target', 'corporate')
                """
            ),
            {
                "id": target_workspace_id,
                "organization_id": ids["org_a"],
                "slug": f"rls-switch-target-{ids['slug']}",
            },
        )
        await conn.execute(
            text(
                """
                insert into external_identities
                    (id, user_id, provider, provider_subject, is_verified, is_active)
                values (:id, :user_id, 'yandex', :provider_subject, true, true)
                """
            ),
            {
                "id": uuid4(),
                "user_id": ids["user_a"],
                "provider_subject": provider_subject,
            },
        )
        await conn.execute(
            text(
                "update auth_sessions set claims_fingerprint = :fingerprint "
                "where id = :session_id"
            ),
            {
                "session_id": ids["session_a"],
                "fingerprint": fingerprint_identity(
                    provider_subject,
                    "yandex",
                    ids["workspace_a"],
                ),
            },
        )
        await conn.execute(
            text(
                """
                insert into workspace_memberships (workspace_id, user_id, role, status)
                values (:workspace_id, :user_id, 'member', 'active')
                """
            ),
            {"workspace_id": target_workspace_id, "user_id": ids["user_a"]},
        )

    sessionmaker = async_sessionmaker(rls_engine, expire_on_commit=False)
    async with sessionmaker() as db:
        await apply_tenant_context(
            db,
            TenantDatabaseContext(
                organization_id=ids["org_a"],
                workspace_id=ids["workspace_a"],
                user_id=ids["user_a"],
                device_id=ids["device_a"],
                auth_session_id=ids["session_a"],
            ),
        )
        activated = await activate_workspace_session(
            db,
            organization_id=ids["org_a"],
            current_workspace_id=ids["workspace_a"],
            internal_workspace_id=uuid4(),
            user_id=ids["user_a"],
            current_session_id=ids["session_a"],
            target_workspace_id=target_workspace_id,
        )
        await db.commit()

    assert activated.workspace.id == target_workspace_id
    assert activated.issued_session.token

    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_rls_postgres_policies",
                reason_category="active_space_switch_verify",
                feature_area="security",
            ),
        )
        source_status = await conn.scalar(
            text("select status from auth_sessions where id = :session_id"),
            {"session_id": ids["session_a"]},
        )
        replacement_count = await conn.scalar(
            text(
                """
                select count(*) from auth_sessions
                where workspace_id = :workspace_id and user_id = :user_id and status = 'active'
                """
            ),
            {"workspace_id": target_workspace_id, "user_id": ids["user_a"]},
        )

    assert source_status == "replaced"
    assert replacement_count == 1


@pytest.mark.asyncio
async def test_share_magic_link_flushes_audit_before_source_workspace_context(
    rls_engine: AsyncEngine,
    app_rls_engine: AsyncEngine,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    sessionmaker = async_sessionmaker(app_rls_engine, expire_on_commit=False)
    personal_context = _request_context(ids, "a")
    source_context = _request_context(ids, "b")
    action_key = f"share_magic_regression_{ids['slug']}"
    event_type = f"email_auth_completed_{ids['slug']}"

    async with sessionmaker() as db:
        await apply_tenant_context(db, personal_context)
        db.add(
            AuthAuditEvent(
                workspace_id=ids["workspace_a"],
                user_id=ids["user_a"],
                actor_user_id=ids["user_a"],
                event_type=event_type,
                provider="email",
                outcome="success",
                metadata_json={"flow": "share_magic_link"},
            )
        )
        await apply_tenant_context(db, source_context)
        db.add(
            MeetingShareRateLimitBucket(
                workspace_id=ids["workspace_b"],
                user_id=ids["user_b"],
                device_id=ids["device_b"],
                action_key=action_key,
                window_started_at=datetime.now(UTC),
            )
        )
        with pytest.raises(DBAPIError, match="row-level security|violates"):
            await db.flush()
        await db.rollback()

    async with sessionmaker() as db:
        await apply_tenant_context(db, personal_context)
        db.add(
            AuthAuditEvent(
                workspace_id=ids["workspace_a"],
                user_id=ids["user_a"],
                actor_user_id=ids["user_a"],
                event_type=event_type,
                provider="email",
                outcome="success",
                metadata_json={"flow": "share_magic_link"},
            )
        )
        await db.flush()
        await apply_tenant_context(db, source_context)
        db.add(
            MeetingShareRateLimitBucket(
                workspace_id=ids["workspace_b"],
                user_id=ids["user_b"],
                device_id=ids["device_b"],
                action_key=action_key,
                window_started_at=datetime.now(UTC),
            )
        )
        await db.flush()
        await db.rollback()


@pytest.mark.asyncio
async def test_join_offer_exposes_only_its_safe_target_metadata_to_the_owner(
    rls_engine: AsyncEngine,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    target_workspace_id = uuid4()
    invitation_id = uuid4()
    offer_id = uuid4()

    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_rls_postgres_policies",
                reason_category="join_offer_target_seed",
                feature_area="security",
            ),
        )
        await conn.execute(
            text(
                """
                insert into workspaces (id, organization_id, slug, name)
                values (:id, :organization_id, :slug, :name)
                """
            ),
            {
                "id": target_workspace_id,
                "organization_id": ids["org_a"],
                "slug": f"rls-offer-target-{ids['slug']}",
                "name": "RLS Offer Target",
            },
        )
        await conn.execute(
            text(
                """
                insert into workspace_invitations
                    (id, workspace_id, target_contact, invited_role, status, source,
                     created_by_user_id, expires_at, metadata_json)
                values
                    (:id, :workspace_id, 'private-target@example.test', 'member', 'pending', 'admin',
                     :created_by_user_id, now() + interval '1 day', '{}'::json)
                """
            ),
            {
                "id": invitation_id,
                "workspace_id": target_workspace_id,
                "created_by_user_id": ids["user_a"],
            },
        )
        await conn.execute(
            text(
                """
                insert into workspace_join_offers
                    (id, workspace_id, user_id, invitation_id, workspace_name, invited_role, status, expires_at)
                values
                    (:id, :workspace_id, :user_id, :invitation_id, 'RLS Offer Target', 'member', 'offered',
                     now() + interval '1 day')
                """
            ),
            {
                "id": offer_id,
                "workspace_id": target_workspace_id,
                "user_id": ids["user_a"],
                "invitation_id": invitation_id,
            },
        )

    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(ids, "a"))
        offer_target = (
            await conn.execute(
                text(
                    """
                    select workspace_name, invited_role
                    from workspace_join_offers
                    where id = :offer_id
                    """
                ),
                {"offer_id": offer_id},
            )
        ).one_or_none()
        rejected = await conn.scalar(
            text(
                "update workspace_join_offers set status = 'rejected' where id = :offer_id returning status"
            ),
            {"offer_id": offer_id},
        )
        invitation_visible = await conn.scalar(
            text("select count(*) from workspace_invitations where id = :invitation_id"),
            {"invitation_id": invitation_id},
        )

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(ids, "b"))
        foreign_count = await conn.scalar(
            text("select count(*) from workspace_join_offers where id = :offer_id"),
            {"offer_id": offer_id},
        )

    assert offer_target == ("RLS Offer Target", "member")
    assert rejected == "rejected"
    assert invitation_visible == 0
    assert foreign_count == 0


@pytest.mark.asyncio
async def test_browser_auth_return_resolver_keeps_only_authenticated_detail_candidates(
    rls_engine: AsyncEngine,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    sessionmaker = async_sessionmaker(rls_engine, expire_on_commit=False)

    async with sessionmaker() as db:
        allowed_path = f"/meetings/{ids['meeting_a']}?calendar_context_action=change"
        assert (
            await resolve_browser_auth_return_path(
                db,
                requested_redirect=allowed_path,
                organization_id=ids["org_a"],
                workspace_id=ids["workspace_a"],
                user_id=ids["user_a"],
                auth_session_id=ids["session_a"],
            )
            == allowed_path
        )
        assert (
            await resolve_browser_auth_return_path(
                db,
                requested_redirect=f"/meetings/{ids['meeting_b']}",
                organization_id=ids["org_a"],
                workspace_id=ids["workspace_a"],
                user_id=ids["user_a"],
                auth_session_id=ids["session_a"],
            )
            == "/meetings"
        )
        assert (
            await resolve_browser_auth_return_path(
                db,
                requested_redirect=f"/desktop/meetings/{ids['meeting_a']}",
                organization_id=ids["org_b"],
                workspace_id=ids["workspace_b"],
                user_id=ids["user_b"],
                auth_session_id=None,
            )
            == "/desktop/meetings"
        )


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
async def test_merged_billing_lineage_remains_visible_and_appealable_under_forced_rls(
    rls_engine: AsyncEngine,
    migrated_postgres_urls: MigratedPostgresUrls,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    trial_id = uuid4()
    referral_link_id = uuid4()
    referral_attribution_id = uuid4()
    fair_use_id = uuid4()
    token_hash = "a" * 64

    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_merged_billing_lineage_rls",
                reason_category="rls_probe_seed",
                feature_area="security",
            ),
        )
        await conn.execute(
            text(
                """
                update user_identities
                set organization_id = :organization_id, status = 'merged',
                    merged_into_user_id = :survivor_user_id, merged_at = now()
                where id = :source_user_id
                """
            ),
            {
                "organization_id": ids["org_a"],
                "survivor_user_id": ids["user_a"],
                "source_user_id": ids["user_b"],
            },
        )
        await conn.execute(
            text(
                """
                update workspaces
                set organization_id = :organization_id, owner_user_id = :survivor_user_id,
                    kind = 'linked'
                where id = :source_workspace_id
                """
            ),
            {
                "organization_id": ids["org_a"],
                "survivor_user_id": ids["user_a"],
                "source_workspace_id": ids["workspace_b"],
            },
        )
        await conn.execute(
            text(
                """
                update workspace_memberships
                set user_id = :survivor_user_id
                where workspace_id = :source_workspace_id and user_id = :source_user_id
                """
            ),
            {
                "survivor_user_id": ids["user_a"],
                "source_user_id": ids["user_b"],
                "source_workspace_id": ids["workspace_b"],
            },
        )
        await conn.execute(
            text(
                """
                insert into trial_activations
                    (id, user_id, workspace_id, starts_at, ends_at, policy_version)
                values
                    (:trial_id, :source_user_id, :source_workspace_id,
                     now() - interval '1 day', now() + interval '6 days', 'lineage-test')
                """
            ),
            {
                "trial_id": trial_id,
                "source_user_id": ids["user_b"],
                "source_workspace_id": ids["workspace_b"],
            },
        )
        await conn.execute(
            text(
                """
                insert into referral_links
                    (id, workspace_id, inviter_user_id, token_hash, campaign_version,
                     expires_at, state)
                values
                    (:link_id, :survivor_workspace_id, :survivor_user_id, :token_hash,
                     'lineage-test', now() + interval '7 days', 'active')
                """
            ),
            {
                "link_id": referral_link_id,
                "survivor_workspace_id": ids["workspace_a"],
                "survivor_user_id": ids["user_a"],
                "token_hash": token_hash,
            },
        )
        await conn.execute(
            text(
                """
                insert into referral_attributions
                    (id, workspace_id, inviter_user_id, invitee_user_id, referral_link_id,
                     token_hash, campaign_version, first_touched_at, bound_at, state)
                values
                    (:attribution_id, :survivor_workspace_id, :survivor_user_id,
                     :source_user_id, :link_id, :token_hash, 'lineage-test', now(), now(),
                     'registered')
                """
            ),
            {
                "attribution_id": referral_attribution_id,
                "survivor_workspace_id": ids["workspace_a"],
                "survivor_user_id": ids["user_a"],
                "source_user_id": ids["user_b"],
                "link_id": referral_link_id,
                "token_hash": token_hash,
            },
        )
        await conn.execute(
            text(
                """
                insert into fair_use_reviews
                    (id, workspace_id, subject_user_id, capability, reason_code,
                     evidence_ref, starts_at, review_by, state)
                values
                    (:fair_use_id, :source_workspace_id, :source_user_id,
                     'server_processing', 'resale', :evidence_ref,
                     now(), now() + interval '24 hours', 'restricted')
                """
            ),
            {
                "source_user_id": ids["user_b"],
                "source_workspace_id": ids["workspace_b"],
                "fair_use_id": fair_use_id,
                "evidence_ref": f"fu-lineage-{ids['slug']}",
            },
        )

    async with _exact_app_role_engine(migrated_postgres_urls.migration_url) as app_engine:
        sessionmaker = async_sessionmaker(app_engine, expire_on_commit=False)
        async with sessionmaker() as db:
            await apply_tenant_context(db, _request_context(ids, "a"))
            assert await trial_used_by_lineage(db, user_id=ids["user_a"])
            assert await fair_use_restricted_for_lineage(db, user_id=ids["user_a"])
            appealed = await appeal_persisted_review(
                db,
                review_id=fair_use_id,
                subject_user_id=ids["user_a"],
                at=datetime.now(UTC),
            )
            assert appealed is not None and appealed.state == "appealed"

            await apply_tenant_context(
                db,
                AuthReferralUserLookupContext(user_id=ids["user_a"]),
            )
            assert await referral_attribution_exists_for_lineage(db, user_id=ids["user_a"])
            await apply_tenant_context(
                db,
                AuthReferralUserLookupContext(user_id=ids["user_b"]),
            )
            with pytest.raises(RuntimeError, match="exact referral user lookup context"):
                await referral_attribution_exists_for_lineage(db, user_id=ids["user_a"])
            await db.commit()

    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_merged_billing_lineage_rls",
                reason_category="rls_probe_cycle",
                feature_area="security",
            ),
        )
        await conn.execute(
            text(
                "update user_identities set status = 'merged', "
                "merged_into_user_id = :source_user_id, merged_at = now() "
                "where id = :survivor_user_id"
            ),
            {
                "source_user_id": ids["user_b"],
                "survivor_user_id": ids["user_a"],
            },
        )

    async with _exact_app_role_engine(migrated_postgres_urls.migration_url) as app_engine:
        sessionmaker = async_sessionmaker(app_engine, expire_on_commit=False)
        async with sessionmaker() as db:
            await apply_tenant_context(db, _request_context(ids, "a"))
            assert await trial_used_by_lineage(db, user_id=ids["user_a"])

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_merged_billing_lineage_rls",
                reason_category="rls_probe_verify",
                feature_area="security",
            ),
        )
        assert (
            await conn.scalar(
                text("select state from fair_use_reviews where id = :id"),
                {"id": fair_use_id},
            )
            == "appealed"
        )


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
async def test_auth_callback_completion_requires_exact_callback_lookup_context(
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
        blocked_update = await conn.execute(
            text("update auth_callback_states set result='completed' where id=:id"),
            {"id": callback_id},
        )
        assert blocked_update.rowcount == 0
        await conn.rollback()

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn,
            WorkspaceAuthContext(
                workspace_id=ids["workspace_a"],
                organization_id=ids["org_a"],
                user_id=ids["user_a"],
                context_kind="auth_bootstrap",
            ),
        )
        bootstrap_update = await conn.execute(
            text("update auth_callback_states set result='completed' where id=:id returning id"),
            {"id": callback_id},
        )
        assert bootstrap_update.scalar_one_or_none() is None
        await conn.rollback()

    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            AuthCallbackLookupContext(state_nonce=callback_nonce),
        )
        updated = await conn.scalar(
            text("update auth_callback_states set result='completed' where id=:id returning id"),
            {"id": callback_id},
        )

    assert updated == callback_id


@pytest.mark.asyncio
async def test_provider_link_start_context_inserts_callback_under_exact_app_role(
    rls_engine: AsyncEngine,
    app_rls_engine: AsyncEngine,
    monkeypatch,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    principal = AuthenticatedPrincipal(
        user_id=ids["user_a"],
        organization_id=ids["org_a"],
        workspace_ids=frozenset({ids["workspace_a"]}),
        subject=str(ids["user_a"]),
        session_id=ids["session_a"],
        auth_via_session=True,
        session_workspace_id=ids["workspace_a"],
        session_device_id=ids["device_a"],
    )
    sessionmaker = async_sessionmaker(app_rls_engine, expire_on_commit=False)

    async with sessionmaker() as db:
        await apply_tenant_context(db, _request_context(ids, "a"))
        db.add(
            AuthCallbackState(
                provider="yandex",
                state_nonce=f"request-denied-{ids['slug']}",
                workspace_id=ids["workspace_a"],
                expected_state="request-denied",
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            )
        )
        with pytest.raises(DBAPIError, match="row-level security|violates"):
            await db.flush()
        await db.rollback()

    callback_id = uuid4()
    callback_nonce = f"provider-link-start-{ids['slug']}"
    source_identity_id = uuid4()
    source_subject = f"provider-link-source-{ids['slug']}"
    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_provider_link_start_context",
                reason_category="rls_probe_seed",
                feature_area="security",
            ),
        )
        await conn.execute(
            text(
                """
                insert into external_identities
                    (id, user_id, provider, provider_subject, is_verified, is_active)
                values (:id, :user_id, 'yandex', :subject, false, true)
                """
            ),
            {
                "id": source_identity_id,
                "user_id": ids["user_a"],
                "subject": source_subject,
            },
        )
        await conn.execute(
            text(
                "update auth_sessions set provider = 'yandex', claims_fingerprint = :fingerprint "
                "where id = :session_id"
            ),
            {
                "session_id": ids["session_a"],
                "fingerprint": hash_token(
                    f"{ids['workspace_a']}|yandex|{source_subject}"
                ),
            },
        )
    async with sessionmaker() as db:
        await apply_provider_link_auth_context(
            db,
            principal=principal,
            workspace_id=ids["workspace_a"],
        )
        db.add(
            AuthCallbackState(
                id=callback_id,
                provider="yandex",
                state_nonce=callback_nonce,
                workspace_id=ids["workspace_a"],
                expected_state=callback_nonce,
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            )
        )
        await db.flush()
        callback_state = await db.get(AuthCallbackState, callback_id)
        assert callback_state is not None
        await apply_provider_link_request_context(
            db,
            principal=principal,
            workspace_id=ids["workspace_a"],
        )
        link = await create_link_intent(
            db,
            principal=principal,
            workspace_id=ids["workspace_a"],
            provider="yandex",
            callback_state=callback_state,
        )
        callback_state.requested_redirect = f"/settings/provider-links/{link.id}"
        await apply_tenant_context(
            db,
            AuthCallbackLookupContext(state_nonce=callback_nonce),
        )
        await db.flush()
        await db.commit()

    async with sessionmaker() as db:
        await apply_tenant_context(
            db,
            AuthCallbackLookupContext(state_nonce=callback_nonce),
        )
        callback_state = await db.get(AuthCallbackState, callback_id)
        assert callback_state is not None
        link = await link_for_callback(db, callback_id)
        assert link is not None
        with pytest.raises(CallbackFlowError, match="callback denied") as error:
            await resolve_callback_to_provider_link(
                db,
                provider="yandex",
                query={"error": "access_denied"},
                state_nonce=callback_nonce,
                link_state=link,
                provider_credentials=ProviderCredentials(
                    client_id="test",
                    client_secret="test",
                    redirect_uri="http://testserver/api/v1/auth/callback/yandex",
                ),
            )
        assert error.value.code == "callback_denied"
        await db.commit()

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_provider_link_start_context",
                reason_category="rls_probe_verify",
                feature_area="security",
            ),
        )
        persisted = await conn.execute(
            text(
                """
                select callback.result, callback.error_code, link.status, link.resolution
                from auth_callback_states callback
                join workspace_provider_link_states link
                  on link.callback_state_id = callback.id
                where callback.id = :id
                """
            ),
            {"id": callback_id},
        )

    assert persisted.one() == ("rejected", "callback_denied", "rejected", "callback_denied")

    foreign_user_id = uuid4()
    foreign_identity_id = uuid4()
    foreign_subject = f"provider-link-foreign-{ids['slug']}"
    success_callback_id = uuid4()
    success_callback_nonce = f"provider-link-success-{ids['slug']}"
    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_provider_link_cross_profile_binding",
                reason_category="rls_probe_seed",
                feature_area="security",
            ),
        )
        await conn.execute(
            text(
                """
                insert into user_identities
                    (id, organization_id, external_subject, display_name)
                values (:id, :organization_id, :subject, 'Foreign profile')
                """
            ),
            {
                "id": foreign_user_id,
                "organization_id": ids["org_a"],
                "subject": foreign_subject,
            },
        )
        await conn.execute(
            text(
                """
                insert into external_identities
                    (id, user_id, provider, provider_subject, is_verified, is_active)
                values (:id, :user_id, 'yandex', :subject, false, true)
                """
            ),
            {
                "id": foreign_identity_id,
                "user_id": foreign_user_id,
                "subject": foreign_subject,
            },
        )

    async with sessionmaker() as db:
        await apply_provider_link_auth_context(
            db,
            principal=principal,
            workspace_id=ids["workspace_a"],
        )
        success_callback = AuthCallbackState(
            id=success_callback_id,
            provider="yandex",
            state_nonce=success_callback_nonce,
            workspace_id=ids["workspace_a"],
            expected_state=success_callback_nonce,
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        db.add(success_callback)
        await db.flush()
        await apply_provider_link_request_context(
            db,
            principal=principal,
            workspace_id=ids["workspace_a"],
        )
        success_link = await create_link_intent(
            db,
            principal=principal,
            workspace_id=ids["workspace_a"],
            provider="yandex",
            callback_state=success_callback,
        )
        success_callback.requested_redirect = f"/settings/provider-links/{success_link.id}"
        await apply_tenant_context(
            db,
            AuthCallbackLookupContext(state_nonce=success_callback_nonce),
        )
        await db.flush()
        await db.commit()

    async def allow_provider(*_args, **_kwargs):
        return None

    monkeypatch.setattr(callbacks_module, "_assert_provider_allowed", allow_provider)
    monkeypatch.setattr(
        callbacks_module,
        "get_provider_adapter",
        lambda _provider: SimpleNamespace(
            verify_callback=lambda *_args, **_kwargs: ProviderIdentity(
                provider="yandex",
                provider_subject=foreign_subject,
                is_verified=False,
            )
        ),
    )

    async def run_callback() -> str:
        async with sessionmaker() as db:
            await apply_tenant_context(
                db,
                AuthCallbackLookupContext(state_nonce=success_callback_nonce),
            )
            assert await db.get(AuthCallbackState, success_callback_id) is not None
            success_link = await link_for_callback(db, success_callback_id)
            assert success_link is not None
            try:
                await resolve_callback_to_provider_link(
                    db,
                    provider="yandex",
                    query={"code": "verified-provider-code"},
                    state_nonce=success_callback_nonce,
                    link_state=success_link,
                    provider_credentials=ProviderCredentials(
                        client_id="test",
                        client_secret="test",
                        redirect_uri="http://testserver/api/v1/auth/callback/yandex",
                    ),
                )
            except CallbackFlowError as exc:
                result = exc.code
            else:
                result = "success"
            await db.commit()
            return result

    callback_results = await asyncio.gather(run_callback(), run_callback())
    assert sorted(callback_results) == ["callback_state_reused", "success"]

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_provider_link_cross_profile_binding",
                reason_category="rls_probe_verify",
                feature_area="security",
            ),
        )
        bound = (
            await conn.execute(
                text(
                    """
                    select callback.result, callback.verified_external_identity_id, link.status
                    from auth_callback_states callback
                    join workspace_provider_link_states link
                      on link.callback_state_id = callback.id
                    where callback.id = :id
                    """
                ),
                {"id": success_callback_id},
            )
        ).one()

    assert bound == ("completed", foreign_identity_id, "callback_verified")


@pytest.mark.asyncio
async def test_email_auth_completion_crosses_workspace_under_forced_rls(
    rls_engine: AsyncEngine,
    app_rls_engine: AsyncEngine,
    migrated_postgres_urls: MigratedPostgresUrls,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    email = f"email-auth-{ids['slug']}@example.test"
    code = "381204"
    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_email_auth_forced_rls",
                reason_category="rls_probe_seed",
                feature_area="security",
            ),
        )
        await conn.execute(
            text(
                """
                insert into external_identities
                    (id, user_id, provider, provider_subject, email, is_verified, is_active)
                values
                    (:id, :user_id, 'email', :email, :email, true, true)
                """
            ),
            {"id": uuid4(), "user_id": ids["user_a"], "email": email},
        )

    settings = Settings(
        database_url=migrated_postgres_urls.app_url,
        web_login_workspace_id=ids["workspace_a"],
    )
    sessionmaker = async_sessionmaker(app_rls_engine, expire_on_commit=False)
    async with sessionmaker() as db:
        state = await _create_email_login_state(
            db,
            workspace_id=ids["workspace_a"],
            next_path="/meetings",
            email=email,
            code=code,
            ttl_seconds=300,
            browser_nonce=TEST_EMAIL_AUTH_BROWSER_NONCE,
            secret=TEST_WEB_CSRF_SECRET,
        )
        await db.commit()
        result = await _consume_email_login_code(
            db,
            request=_email_auth_request(settings, state_nonce=state.state_nonce),
            workspace_id=ids["workspace_a"],
            email=email,
            code=code,
            state_nonce=state.state_nonce,
            next_path="/meetings",
        )
        assert isinstance(result, EmailLoginCompletion)
        assert result.workspace_id != ids["workspace_a"]
        await db.commit()

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_email_auth_forced_rls",
                reason_category="rls_probe_verify",
                feature_area="security",
            ),
        )
        callback = (
            await conn.execute(
                text(
                    """
                    select result, error_code, used_at
                    from auth_callback_states where state_nonce = :state_nonce
                    """
                ),
                {"state_nonce": state.state_nonce},
            )
        ).one()
        session_count = await conn.scalar(
            text("select count(*) from auth_sessions where id = :session_id"),
            {"session_id": result.auth_session_id},
        )

    assert callback.result == "completed"
    assert callback.error_code is None
    assert callback.used_at is not None
    assert session_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("submitted_code", "expected_callback_error"),
    (("000000", "email_code_invalid"), ("381204", "email_identity_not_found")),
)
async def test_email_auth_failures_write_public_audit_then_finish_exact_callback(
    app_rls_engine: AsyncEngine,
    migrated_postgres_urls: MigratedPostgresUrls,
    rls_engine: AsyncEngine,
    submitted_code: str,
    expected_callback_error: str,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    email = f"email-auth-invalid-{ids['slug']}@example.test"
    settings = Settings(
        database_url=migrated_postgres_urls.app_url,
        web_login_workspace_id=ids["workspace_a"],
    )
    sessionmaker = async_sessionmaker(app_rls_engine, expire_on_commit=False)
    async with sessionmaker() as db:
        state = await _create_email_login_state(
            db,
            workspace_id=ids["workspace_a"],
            next_path="/meetings",
            email=email,
            code="381204",
            ttl_seconds=300,
            browser_nonce=TEST_EMAIL_AUTH_BROWSER_NONCE,
            secret=TEST_WEB_CSRF_SECRET,
        )
        await db.commit()
        result = await _consume_email_login_code(
            db,
            request=_email_auth_request(settings, state_nonce=state.state_nonce),
            workspace_id=ids["workspace_a"],
            email=email,
            code=submitted_code,
            state_nonce=state.state_nonce,
            next_path="/meetings",
        )
        assert isinstance(result, HTMLResponse)
        await db.commit()

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_email_auth_invalid_forced_rls",
                reason_category="rls_probe_verify",
                feature_area="security",
            ),
        )
        callback_result, callback_error = (
            await conn.execute(
                text(
                    """
                    select result, error_code from auth_callback_states
                    where state_nonce = :state_nonce
                    """
                ),
                {"state_nonce": state.state_nonce},
            )
        ).one()
        audit_count = await conn.scalar(
            text(
                """
                select count(*) from auth_audit_events
                where workspace_id = :workspace_id
                  and event_type = 'email_auth_started'
                  and outcome = 'failure'
                  and metadata_json ->> 'error_code' = 'email_code_invalid'
                """
            ),
            {"workspace_id": ids["workspace_a"]},
        )

    assert callback_result == "failed"
    assert callback_error == expected_callback_error
    assert audit_count == 1


@pytest.mark.asyncio
async def test_email_auth_concurrent_replay_expiry_and_rollback_under_forced_rls(
    app_rls_engine: AsyncEngine,
    migrated_postgres_urls: MigratedPostgresUrls,
    rls_engine: AsyncEngine,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    email = f"email-auth-terminal-{ids['slug']}@example.test"
    code = "381204"
    settings = Settings(
        database_url=migrated_postgres_urls.app_url,
        web_login_workspace_id=ids["workspace_a"],
    )
    sessionmaker = async_sessionmaker(app_rls_engine, expire_on_commit=False)
    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_email_auth_terminal_forced_rls",
                reason_category="rls_probe_seed",
                feature_area="security",
            ),
        )
        await conn.execute(
            text(
                """
                insert into external_identities
                    (id, user_id, provider, provider_subject, email, is_verified, is_active)
                values (:id, :user_id, 'email', :email, :email, true, true)
                """
            ),
            {"id": uuid4(), "user_id": ids["user_a"], "email": email},
        )

    async with sessionmaker() as db:
        concurrent_state = await _create_email_login_state(
            db,
            workspace_id=ids["workspace_a"],
            next_path="/meetings",
            email=email,
            code=code,
            ttl_seconds=300,
            browser_nonce=TEST_EMAIL_AUTH_BROWSER_NONCE,
            secret=TEST_WEB_CSRF_SECRET,
        )
        rollback_state = await _create_email_login_state(
            db,
            workspace_id=ids["workspace_a"],
            next_path="/meetings",
            email=email,
            code=code,
            ttl_seconds=300,
            browser_nonce=TEST_EMAIL_AUTH_BROWSER_NONCE,
            secret=TEST_WEB_CSRF_SECRET,
        )
        expired_state = await _create_email_login_state(
            db,
            workspace_id=ids["workspace_a"],
            next_path="/meetings",
            email=email,
            code=code,
            ttl_seconds=-1,
            browser_nonce=TEST_EMAIL_AUTH_BROWSER_NONCE,
            secret=TEST_WEB_CSRF_SECRET,
        )
        await db.commit()

    async def consume_valid_code() -> HTMLResponse | EmailLoginCompletion:
        async with sessionmaker() as db:
            result = await _consume_email_login_code(
                db,
                request=_email_auth_request(
                    settings,
                    state_nonce=concurrent_state.state_nonce,
                ),
                workspace_id=ids["workspace_a"],
                email=email,
                code=code,
                state_nonce=concurrent_state.state_nonce,
                next_path="/meetings",
            )
            await db.commit()
            return result

    concurrent_results = await asyncio.gather(consume_valid_code(), consume_valid_code())
    completed_results = [
        result for result in concurrent_results if isinstance(result, EmailLoginCompletion)
    ]
    rejected_results = [result for result in concurrent_results if isinstance(result, HTMLResponse)]
    assert len(completed_results) == 1
    assert len(rejected_results) == 1
    concurrent_session_id = completed_results[0].auth_session_id

    async with sessionmaker() as db:
        rollback_result = await _consume_email_login_code(
            db,
            request=_email_auth_request(
                settings,
                state_nonce=rollback_state.state_nonce,
            ),
            workspace_id=ids["workspace_a"],
            email=email,
            code=code,
            state_nonce=rollback_state.state_nonce,
            next_path="/meetings",
        )
        assert isinstance(rollback_result, EmailLoginCompletion)
        rollback_session_id = rollback_result.auth_session_id
        await db.rollback()

    async with sessionmaker() as db:
        expired_result = await _consume_email_login_code(
            db,
            request=_email_auth_request(
                settings,
                state_nonce=expired_state.state_nonce,
            ),
            workspace_id=ids["workspace_a"],
            email=email,
            code=code,
            state_nonce=expired_state.state_nonce,
            next_path="/meetings",
        )
        assert isinstance(expired_result, HTMLResponse)
        await db.commit()

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_email_auth_terminal_forced_rls",
                reason_category="rls_probe_verify",
                feature_area="security",
            ),
        )
        callbacks = {
            row.state_nonce: (row.result, row.error_code)
            for row in (
                await conn.execute(
                    text(
                        """
                        select state_nonce, result, error_code
                        from auth_callback_states
                        where state_nonce in (:concurrent_nonce, :rollback_nonce, :expired_nonce)
                        """
                    ),
                    {
                        "concurrent_nonce": concurrent_state.state_nonce,
                        "rollback_nonce": rollback_state.state_nonce,
                        "expired_nonce": expired_state.state_nonce,
                    },
                )
            )
        }
        rollback_session_count = await conn.scalar(
            text("select count(*) from auth_sessions where id = :session_id"),
            {"session_id": rollback_session_id},
        )
        concurrent_session_count = await conn.scalar(
            text("select count(*) from auth_sessions where id = :session_id"),
            {"session_id": concurrent_session_id},
        )
        audit_codes = tuple(
            await conn.scalars(
                text(
                    """
                    select metadata_json ->> 'error_code'
                    from auth_audit_events
                    where workspace_id = :workspace_id
                      and outcome = 'failure'
                      and metadata_json ->> 'error_code' in
                          ('email_code_replayed', 'email_code_expired')
                    order by metadata_json ->> 'error_code'
                    """
                ),
                {"workspace_id": ids["workspace_a"]},
            )
        )

    assert callbacks[concurrent_state.state_nonce] == ("completed", None)
    assert callbacks[rollback_state.state_nonce] == ("pending", None)
    assert callbacks[expired_state.state_nonce] == ("expired", "email_code_expired")
    assert concurrent_session_count == 1
    assert rollback_session_count == 0
    assert audit_codes == ("email_code_expired", "email_code_replayed")


@pytest.mark.asyncio
async def test_provider_link_callback_lookup_requires_exact_state_nonce(
    rls_engine: AsyncEngine,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    callback_id = uuid4()
    link_id = uuid4()
    source_identity_id = uuid4()
    callback_nonce = f"provider-link-callback-{ids['slug']}"

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
                    (:id, 'vk', :state_nonce, :workspace_id, :state_nonce, :expires_at, 'pending')
                """
            ),
            {
                "id": callback_id,
                "state_nonce": callback_nonce,
                "workspace_id": ids["workspace_a"],
                "expires_at": datetime.now(UTC) + timedelta(minutes=5),
            },
        )
        await conn.execute(
            text(
                """
                insert into external_identities (id, user_id, provider, provider_subject, is_verified)
                values (:id, :user_id, 'yandex', :provider_subject, true)
                """
            ),
            {
                "id": source_identity_id,
                "user_id": ids["user_a"],
                "provider_subject": f"provider-link-source-{ids['slug']}",
            },
        )
        await conn.execute(
            text(
                """
                insert into workspace_provider_link_states
                    (id, workspace_id, initiating_user_id, source_provider_identity_id,
                     initiating_auth_session_id, callback_state_id, candidate_provider,
                     status, expires_at)
                values
                    (:id, :workspace_id, :user_id, :source_identity_id,
                     :session_id, :callback_id, 'vk', 'initiated', :expires_at)
                """
            ),
            {
                "id": link_id,
                "workspace_id": ids["workspace_a"],
                "user_id": ids["user_a"],
                "source_identity_id": source_identity_id,
                "session_id": ids["session_a"],
                "callback_id": callback_id,
                "expires_at": datetime.now(UTC) + timedelta(minutes=5),
            },
        )

    async with rls_engine.connect() as conn:
        missing_context = await conn.scalar(
            text("select count(*) from workspace_provider_link_states where id=:id"),
            {"id": link_id},
        )

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn, AuthCallbackLookupContext(state_nonce=callback_nonce)
        )
        matching_nonce = await conn.scalar(
            text("select count(*) from workspace_provider_link_states where id=:id"),
            {"id": link_id},
        )

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn, AuthCallbackLookupContext(state_nonce=f"wrong-{callback_nonce}")
        )
        wrong_nonce = await conn.scalar(
            text("select count(*) from workspace_provider_link_states where id=:id"),
            {"id": link_id},
        )
        wrong_nonce_update = await conn.execute(
            text(
                "update workspace_provider_link_states set status='callback_verified' where id=:id"
            ),
            {"id": link_id},
        )
        await conn.rollback()

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(ids, "a"))
        owner_request = await conn.scalar(
            text("select count(*) from workspace_provider_link_states where id=:id"),
            {"id": link_id},
        )

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(ids, "b"))
        foreign_request = await conn.scalar(
            text("select count(*) from workspace_provider_link_states where id=:id"),
            {"id": link_id},
        )
        foreign_update = await conn.execute(
            text(
                "update workspace_provider_link_states set status='callback_verified' where id=:id"
            ),
            {"id": link_id},
        )
        await conn.rollback()

    assert missing_context == 0
    assert matching_nonce == 1
    assert wrong_nonce == 0
    assert wrong_nonce_update.rowcount == 0
    assert owner_request == 1
    assert foreign_request == 0
    assert foreign_update.rowcount == 0


@pytest.mark.asyncio
async def test_provider_link_concurrent_confirmation_keeps_one_identity_and_safe_audit(
    migrated_postgres_urls: MigratedPostgresUrls,
) -> None:
    engine = create_async_engine(migrated_postgres_urls.migration_url, pool_pre_ping=True)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        ids = await _seed_probe_rows(engine)
        source_identity_id = uuid4()
        candidate_subject = f"provider-link-race-{ids['slug']}"
        link_ids = (uuid4(), uuid4())
        expires_at = datetime.now(UTC) + timedelta(minutes=5)
        async with sessionmaker() as db:
            db.add(
                ExternalIdentity(
                    id=source_identity_id,
                    user_id=ids["user_a"],
                    provider="yandex",
                    provider_subject=f"provider-link-source-{ids['slug']}",
                    is_verified=True,
                )
            )
            for link_id in link_ids:
                callback_state_id = uuid4()
                db.add(
                    AuthCallbackState(
                        id=callback_state_id,
                        provider="vk",
                        state_nonce=f"provider-link-race-state-{callback_state_id}",
                        workspace_id=ids["workspace_a"],
                        expected_state=f"provider-link-race-state-{callback_state_id}",
                        expires_at=expires_at,
                        result="completed",
                    )
                )
                db.add(
                    WorkspaceProviderLinkState(
                        id=link_id,
                        workspace_id=ids["workspace_a"],
                        initiating_user_id=ids["user_a"],
                        source_provider_identity_id=source_identity_id,
                        initiating_auth_session_id=ids["session_a"],
                        callback_state_id=callback_state_id,
                        candidate_provider="vk",
                        candidate_identity_subject=candidate_subject,
                        candidate_email="candidate@example.test",
                        candidate_display_name="Candidate Name",
                        status="callback_verified",
                        callback_verified_at=datetime.now(UTC),
                        expires_at=expires_at,
                    )
                )
            await db.commit()

        principal = AuthenticatedPrincipal(
            user_id=ids["user_a"],
            organization_id=ids["org_a"],
            workspace_ids=frozenset({ids["workspace_a"]}),
            subject=str(ids["user_a"]),
            session_id=ids["session_a"],
            auth_via_session=True,
            session_workspace_id=ids["workspace_a"],
            session_device_id=ids["device_a"],
        )
        start = asyncio.Event()
        ready = 0
        ready_lock = asyncio.Lock()

        async def confirm(link_id: UUID) -> bool:
            nonlocal ready
            async with sessionmaker() as db:
                async with ready_lock:
                    ready += 1
                    if ready == len(link_ids):
                        start.set()
                await start.wait()
                result = await confirm_provider_link(
                    db,
                    principal=principal,
                    link_state_id=link_id,
                )
                await db.commit()
                return result.idempotent

        results = await asyncio.gather(*(confirm(link_id) for link_id in link_ids))
        assert sorted(results) == [False, True]

        async with sessionmaker() as db:
            identities = list(
                await db.scalars(
                    select(ExternalIdentity).where(
                        ExternalIdentity.provider == "vk",
                        ExternalIdentity.provider_subject == candidate_subject,
                    )
                )
            )
            links = [await db.get(WorkspaceProviderLinkState, link_id) for link_id in link_ids]
            audit_events = list(
                await db.scalars(
                    select(AuthAuditEvent).where(
                        AuthAuditEvent.event_type == "provider_link_confirmed"
                    )
                )
            )

        assert len(identities) == 1
        assert identities[0].user_id == ids["user_a"]
        assert all(link is not None and link.status == "confirmed" for link in links)
        assert all(link is not None and link.candidate_identity_subject is None for link in links)
        assert sorted(event.metadata_json["idempotent"] for event in audit_events) == [False, True]
        for event in audit_events:
            assert "candidate@example.test" not in str(event.metadata_json)
            assert candidate_subject not in str(event.metadata_json)
    finally:
        await engine.dispose()


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

    assert app_role is not None
    assert app_role.startswith("twobrain_rec_app_")
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
async def test_app_role_gets_only_proof_bound_account_merge_access(
    rls_engine: AsyncEngine,
    migrated_postgres_urls: MigratedPostgresUrls,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    intent_id = uuid4()
    source_identity_id = uuid4()
    wrong_identity_id = uuid4()
    callback_id = uuid4()
    wrong_callback_id = uuid4()
    wrong_session_id = uuid4()
    provider_link_id = uuid4()
    journal_id = uuid4()
    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_account_merge_rls",
                reason_category="rls_probe_seed",
                feature_area="security",
            ),
        )
        await conn.execute(
            text(
                """
                    insert into external_identities
                        (id, user_id, provider, provider_subject, email,
                         is_verified, is_active)
                    values
                        (:source_identity_id, :source_user_id, 'email', :source_subject,
                         :source_email, true, true),
                        (:wrong_identity_id, :survivor_user_id, 'email', :wrong_subject,
                         :wrong_email, true, true)
                    """
            ),
            {
                "source_identity_id": source_identity_id,
                "source_user_id": ids["user_b"],
                "source_subject": f"merge-source-{ids['slug']}",
                "source_email": f"merge-source-{ids['slug']}@example.test",
                "wrong_identity_id": wrong_identity_id,
                "survivor_user_id": ids["user_a"],
                "wrong_subject": f"merge-wrong-{ids['slug']}",
                "wrong_email": f"merge-wrong-{ids['slug']}@example.test",
            },
        )
        await conn.execute(
            text(
                """
                    insert into auth_sessions
                        (id, user_id, workspace_id, device_id, provider,
                         session_token_hash, status, expires_at)
                    values
                        (:id, :user_id, :workspace_id, :device_id, 'email',
                         :token_hash, 'active', now() + interval '15 minutes')
                    """
            ),
            {
                "id": wrong_session_id,
                "user_id": ids["user_b"],
                "workspace_id": ids["workspace_b"],
                "device_id": ids["device_b"],
                "token_hash": f"merge-wrong-session-{ids['slug']}",
            },
        )
        await conn.execute(
            text(
                """
                    insert into auth_callback_states
                        (id, provider, state_nonce, workspace_id, expected_state,
                         expires_at, used_at, result, verified_external_identity_id)
                    values
                        (:callback_id, 'email_link', :callback_nonce, :workspace_id,
                         :callback_nonce, now() + interval '15 minutes', now(), 'completed',
                         :source_identity_id),
                        (:wrong_callback_id, 'email_link', :wrong_callback_nonce,
                         :wrong_workspace_id, :wrong_callback_nonce,
                         now() + interval '15 minutes', now(), 'completed',
                         :wrong_identity_id)
                    """
            ),
            {
                "callback_id": callback_id,
                "callback_nonce": f"merge-callback-{ids['slug']}",
                "workspace_id": ids["workspace_a"],
                "source_identity_id": source_identity_id,
                "wrong_callback_id": wrong_callback_id,
                "wrong_callback_nonce": f"merge-wrong-callback-{ids['slug']}",
                "wrong_workspace_id": ids["workspace_b"],
                "wrong_identity_id": wrong_identity_id,
            },
        )
        await conn.execute(
            text(
                """
                    insert into workspace_provider_link_states
                        (id, workspace_id, initiating_user_id,
                         source_provider_identity_id, target_provider_identity_id,
                         initiating_auth_session_id,
                         callback_state_id, candidate_provider,
                         candidate_identity_subject, status, expires_at)
                    values
                        (:id, :workspace_id, :survivor_user_id, :source_provider_identity_id,
                         :target_provider_identity_id, :session_id, :callback_id,
                         'yandex', :candidate_subject,
                         'callback_verified', now() + interval '15 minutes')
                    """
            ),
            {
                "id": provider_link_id,
                "workspace_id": ids["workspace_a"],
                "survivor_user_id": ids["user_a"],
                "source_provider_identity_id": wrong_identity_id,
                "target_provider_identity_id": source_identity_id,
                "session_id": ids["session_a"],
                "callback_id": callback_id,
                "candidate_subject": f"merge-source-{ids['slug']}",
            },
        )
        await conn.execute(
            text(
                """
                    insert into account_merge_intents
                        (id, workspace_id, survivor_user_id, source_user_id,
                         initiating_auth_session_id, source_external_identity_id,
                         proof_callback_state_id, email_proof_state, oauth_proof_state,
                         preview_fingerprint, status, expires_at)
                    values
                        (:id, :workspace_id, :survivor_user_id, :source_user_id,
                         :session_id, :source_identity_id, :callback_id,
                         'verified', 'verified', :preview_fingerprint,
                         'preview_ready', now() + interval '15 minutes')
                    """
            ),
            {
                "id": intent_id,
                "workspace_id": ids["workspace_a"],
                "survivor_user_id": ids["user_a"],
                "source_user_id": ids["user_b"],
                "session_id": ids["session_a"],
                "source_identity_id": source_identity_id,
                "callback_id": callback_id,
                "preview_fingerprint": f"seed-preview-{ids['slug']}",
            },
        )

    async with _exact_app_role_engine(migrated_postgres_urls.migration_url) as app_engine:

        async def assert_access(expected: bool) -> None:
            async with app_engine.begin() as conn:
                await apply_tenant_context_to_connection(
                    conn,
                    AccountMergeTenantContext(
                        intent_id=intent_id,
                        workspace_id=ids["workspace_a"],
                        survivor_user_id=ids["user_a"],
                        source_user_id=ids["user_b"],
                    ),
                )
                assert (
                    bool(await conn.scalar(text("select rec_account_merge_context_valid()")))
                    is expected
                )
                assert bool(await conn.scalar(text("select rec_maintenance_allowed()"))) is expected
                assert int(
                    await conn.scalar(text("select count(*) from account_merge_intents")) or 0
                ) == int(expected)

        async def update_proof(sql: str, **params: object) -> None:
            async with rls_engine.begin() as conn:
                await apply_tenant_context_to_connection(
                    conn,
                    MaintenanceTenantContext(
                        operation_name="migration_verification",
                        actor_id="test_account_merge_rls",
                        reason_category="rls_probe_mutation",
                        feature_area="security",
                    ),
                )
                await conn.execute(text(sql), params)

        await assert_access(True)

        await update_proof(
            "update account_merge_intents set initiating_auth_session_id = null, "
            "source_external_identity_id = null, proof_callback_state_id = null "
            "where id = :id",
            id=intent_id,
        )
        await assert_access(False)
        await update_proof(
            "update account_merge_intents set initiating_auth_session_id = :session_id, "
            "source_external_identity_id = :source_identity_id, "
            "proof_callback_state_id = :callback_id where id = :id",
            id=intent_id,
            session_id=ids["session_a"],
            source_identity_id=source_identity_id,
            callback_id=callback_id,
        )

        for column_name, wrong_value, exact_value in (
            ("initiating_auth_session_id", wrong_session_id, ids["session_a"]),
            ("source_external_identity_id", wrong_identity_id, source_identity_id),
            ("proof_callback_state_id", wrong_callback_id, callback_id),
        ):
            await update_proof(
                f"update account_merge_intents set {column_name} = :value where id = :id",
                id=intent_id,
                value=wrong_value,
            )
            await assert_access(False)
            await update_proof(
                f"update account_merge_intents set {column_name} = :value where id = :id",
                id=intent_id,
                value=exact_value,
            )

        await update_proof(
            "update auth_sessions set status = 'revoked' where id = :id",
            id=ids["session_a"],
        )
        await assert_access(False)
        await update_proof(
            "update auth_sessions set status = 'active' where id = :id",
            id=ids["session_a"],
        )
        await update_proof(
            "update auth_sessions set expires_at = now() - interval '1 minute' where id = :id",
            id=ids["session_a"],
        )
        await assert_access(False)
        await update_proof(
            "update auth_sessions set expires_at = now() + interval '15 minutes' where id = :id",
            id=ids["session_a"],
        )
        await update_proof(
            "update account_merge_intents set expires_at = now() - interval '1 minute' where id = :id",
            id=intent_id,
        )
        await assert_access(False)
        await update_proof(
            "update account_merge_intents set expires_at = now() + interval '15 minutes' where id = :id",
            id=intent_id,
        )
        await update_proof(
            "update external_identities set is_active = false where id = :id",
            id=source_identity_id,
        )
        await assert_access(False)
        await update_proof(
            "update external_identities set is_active = true where id = :id",
            id=source_identity_id,
        )
        await update_proof(
            "update auth_callback_states set result = 'failed' where id = :id",
            id=callback_id,
        )
        await assert_access(False)
        await update_proof(
            "update auth_callback_states set result = 'completed' where id = :id",
            id=callback_id,
        )
        await update_proof(
            "update auth_callback_states set verified_external_identity_id = :identity_id "
            "where id = :id",
            id=callback_id,
            identity_id=wrong_identity_id,
        )
        await assert_access(False)
        await update_proof(
            "update auth_callback_states set verified_external_identity_id = :identity_id "
            "where id = :id",
            id=callback_id,
            identity_id=source_identity_id,
        )
        await update_proof(
            "update auth_callback_states set provider = 'yandex' where id = :id",
            id=callback_id,
        )
        await assert_access(False)
        await update_proof(
            "update auth_callback_states set provider = 'email_link' where id = :id",
            id=callback_id,
        )
        await update_proof(
            "update external_identities set provider = 'vk' where id = :id",
            id=source_identity_id,
        )
        await assert_access(False)
        await update_proof(
            "update external_identities set provider = 'email' where id = :id",
            id=source_identity_id,
        )
        await update_proof(
            "update external_identities set is_verified = false where id = :id",
            id=source_identity_id,
        )
        await assert_access(False)
        await update_proof(
            "update external_identities set is_verified = true where id = :id",
            id=source_identity_id,
        )

        await update_proof(
            "update account_merge_intents set provider_link_state_id = :link_id where id = :id",
            id=intent_id,
            link_id=provider_link_id,
        )
        await assert_access(False)
        await update_proof(
            "update workspace_provider_link_states set status = 'confirmed' where id = :id",
            id=provider_link_id,
        )
        await assert_access(False)
        await update_proof(
            "update auth_callback_states set provider = 'yandex' where id = :id",
            id=callback_id,
        )
        await update_proof(
            "update external_identities set provider = 'yandex', is_verified = false "
            "where id = :id",
            id=source_identity_id,
        )
        await assert_access(True)
        await update_proof(
            "update workspace_provider_link_states set candidate_provider = 'vk' where id = :id",
            id=provider_link_id,
        )
        await assert_access(False)
        await update_proof(
            "update workspace_provider_link_states set candidate_provider = 'yandex' "
            "where id = :id",
            id=provider_link_id,
        )
        await assert_access(True)
        await update_proof(
            "update workspace_provider_link_states set callback_state_id = :callback_id "
            "where id = :id",
            id=provider_link_id,
            callback_id=wrong_callback_id,
        )
        await assert_access(False)
        await update_proof(
            "update workspace_provider_link_states set callback_state_id = :callback_id "
            "where id = :id",
            id=provider_link_id,
            callback_id=callback_id,
        )
        await update_proof(
            "update workspace_provider_link_states set target_provider_identity_id = :identity_id "
            "where id = :id",
            id=provider_link_id,
            identity_id=wrong_identity_id,
        )
        await assert_access(False)
        await update_proof(
            "update workspace_provider_link_states set target_provider_identity_id = :identity_id "
            "where id = :id",
            id=provider_link_id,
            identity_id=source_identity_id,
        )
        await assert_access(True)

        async with app_engine.begin() as conn:
            await apply_tenant_context_to_connection(
                conn,
                AccountMergeTenantContext(
                    intent_id=intent_id,
                    workspace_id=ids["workspace_a"],
                    survivor_user_id=ids["user_a"],
                    source_user_id=ids["user_b"],
                ),
            )
            inserted_journal = await conn.scalar(
                text(
                    """
                    insert into account_merge_journals
                        (id, merge_intent_id, workspace_id, survivor_user_id,
                         source_user_id, policy_version, preview_fingerprint,
                         status, counts_json, blocker_codes_json)
                    values
                        (:id, :intent_id, :workspace_id, :survivor_user_id,
                         :source_user_id, 1, :preview_fingerprint,
                         'completed', '{}'::json, '[]'::json)
                    returning id
                    """
                ),
                {
                    "id": journal_id,
                    "intent_id": intent_id,
                    "workspace_id": ids["workspace_a"],
                    "survivor_user_id": ids["user_a"],
                    "source_user_id": ids["user_b"],
                    "preview_fingerprint": f"seed-preview-{ids['slug']}",
                },
            )
            blocked_journal_update = await conn.execute(
                text("update account_merge_journals set status = 'failed' where id = :id"),
                {"id": journal_id},
            )
            blocked_journal_delete = await conn.execute(
                text("delete from account_merge_journals where id = :id"),
                {"id": journal_id},
            )
            visible_journal_count = await conn.scalar(
                text("select count(*) from account_merge_journals where id = :id"),
                {"id": journal_id},
            )

        assert inserted_journal == journal_id
        assert blocked_journal_update.rowcount == 0
        assert blocked_journal_delete.rowcount == 0
        assert visible_journal_count == 1

        await update_proof(
            "update account_merge_intents set status = 'blocked' where id = :id",
            id=intent_id,
        )
        await assert_access(True)
        await update_proof(
            "update account_merge_intents set status = 'completed' where id = :id",
            id=intent_id,
        )
        await assert_access(False)


@pytest.mark.asyncio
async def test_email_link_and_oauth_provider_link_terminal_states_restore_narrow_rls_context(
    rls_engine: AsyncEngine,
    migrated_postgres_urls: MigratedPostgresUrls,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    source_user_id = uuid4()
    source_workspace_id = uuid4()
    source_email_identity_id = uuid4()
    candidate_identity_id = uuid4()
    callback_ids = tuple(uuid4() for _ in range(3))
    link_ids = tuple(uuid4() for _ in range(3))
    candidate_subject = f"forced-rls-provider-{ids['slug']}"
    candidate_email = f"forced-rls-source-{ids['slug']}@example.test"
    survivor_email = f"forced-rls-current-{ids['slug']}@example.test"
    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_auth_link_terminal_rls",
                reason_category="rls_probe_seed",
                feature_area="security",
            ),
        )
        await conn.execute(
            text(
                """
                    update workspaces
                    set owner_user_id = :survivor_user_id, kind = 'personal'
                    where id = :survivor_workspace_id
                    """
            ),
            {
                "survivor_workspace_id": ids["workspace_a"],
                "survivor_user_id": ids["user_a"],
            },
        )
        await conn.execute(
            text(
                """
                    insert into user_identities
                        (id, organization_id, external_subject, display_name)
                    values (:id, :organization_id, :subject, 'Synthetic source')
                    """
            ),
            {
                "id": source_user_id,
                "organization_id": ids["org_a"],
                "subject": f"forced-rls-source-{ids['slug']}",
            },
        )
        await conn.execute(
            text(
                """
                    insert into workspaces
                        (id, organization_id, owner_user_id, slug, name, kind)
                    values
                        (:id, :organization_id, :owner_user_id, :slug,
                         'Synthetic source', 'personal')
                    """
            ),
            {
                "id": source_workspace_id,
                "organization_id": ids["org_a"],
                "owner_user_id": source_user_id,
                "slug": f"forced-rls-source-{ids['slug']}",
            },
        )
        await conn.execute(
            text(
                """
                    insert into workspace_memberships
                        (workspace_id, user_id, role, status)
                    values (:workspace_id, :user_id, 'owner', 'active')
                    """
            ),
            {"workspace_id": source_workspace_id, "user_id": source_user_id},
        )
        await conn.execute(
            text(
                """
                    insert into external_identities
                        (id, user_id, provider, provider_subject, email, is_verified, is_active)
                    values
                        (:source_id, :survivor_user_id, 'email', :source_email,
                         :source_email, true, true),
                        (:candidate_id, :source_user_id, 'vk', :candidate_subject,
                         :candidate_email, true, true)
                    """
            ),
            {
                "source_id": source_email_identity_id,
                "survivor_user_id": ids["user_a"],
                "source_email": survivor_email,
                "candidate_id": candidate_identity_id,
                "source_user_id": source_user_id,
                "candidate_subject": candidate_subject,
                "candidate_email": candidate_email,
            },
        )
        await conn.execute(
            text(
                """
                    insert into workspace_auth_policies
                        (id, workspace_id, allow_yandex, allow_vk, allow_telegram,
                         allow_tid, allow_sber_id, allow_mts_id, allow_esia,
                         allow_provider_self_enrollment, require_ru_local,
                         residency_region_tag, consent_text_version)
                    values
                        (:id, :workspace_id, true, true, true,
                         false, false, false, false, false, true, 'ru', 'v1')
                    """
            ),
            {"id": uuid4(), "workspace_id": ids["workspace_a"]},
        )
        await conn.execute(
            text(
                "update auth_sessions set provider = 'email', claims_fingerprint = :fingerprint "
                "where id = :session_id"
            ),
            {
                "session_id": ids["session_a"],
                "fingerprint": hash_token(
                    f"email:{survivor_email}:{ids['workspace_a']}"
                ),
            },
        )
        for index, (callback_id, link_id) in enumerate(zip(callback_ids, link_ids, strict=True)):
            nonce = f"forced-rls-provider-callback-{index}-{ids['slug']}"
            await conn.execute(
                text(
                    """
                    insert into auth_callback_states
                        (id, provider, state_nonce, workspace_id, expected_state,
                             expires_at, used_at, result, verified_external_identity_id)
                        values
                            (:id, 'vk', :nonce, :workspace_id, :nonce,
                             :expires_at, now(), 'completed', :verified_identity_id)
                        """
                ),
                {
                    "id": callback_id,
                    "nonce": nonce,
                    "workspace_id": ids["workspace_a"],
                    "expires_at": datetime.now(UTC) + timedelta(minutes=5),
                    "verified_identity_id": candidate_identity_id,
                },
            )
            await conn.execute(
                text(
                    """
                        insert into workspace_provider_link_states
                            (id, workspace_id, initiating_user_id,
                             source_provider_identity_id, initiating_auth_session_id,
                             callback_state_id, candidate_provider,
                             candidate_identity_subject, status, expires_at)
                        values
                            (:id, :workspace_id, :user_id, :source_identity_id,
                             :session_id, :callback_id, 'vk', :candidate_subject,
                             'callback_verified', :expires_at)
                        """
                ),
                {
                    "id": link_id,
                    "workspace_id": ids["workspace_a"],
                    "user_id": ids["user_a"],
                    "source_identity_id": source_email_identity_id,
                    "session_id": ids["session_a"],
                    "callback_id": callback_id,
                    "candidate_subject": candidate_subject,
                    "expires_at": datetime.now(UTC) + timedelta(minutes=5),
                },
            )

    async with _exact_app_role_engine(migrated_postgres_urls.migration_url) as app_engine:
        app_url = app_engine.url.render_as_string(hide_password=False)
        sessionmaker = async_sessionmaker(app_engine, expire_on_commit=False)
        principal = AuthenticatedPrincipal(
            user_id=ids["user_a"],
            organization_id=ids["org_a"],
            workspace_ids=frozenset({ids["workspace_a"]}),
            subject=str(ids["user_a"]),
            session_id=ids["session_a"],
            auth_via_session=True,
            session_workspace_id=ids["workspace_a"],
            session_device_id=ids["device_a"],
        )

        async def confirm_merge_link(link_state_id: UUID) -> object:
            async with sessionmaker() as db:
                await apply_tenant_context(
                    db,
                    TenantDatabaseContext(
                        organization_id=ids["org_a"],
                        workspace_id=ids["workspace_a"],
                        user_id=ids["user_a"],
                        device_id=ids["device_a"],
                        auth_session_id=ids["session_a"],
                    ),
                )
                try:
                    result = await confirm_provider_link(
                        db,
                        principal=principal,
                        link_state_id=link_state_id,
                    )
                    await db.commit()
                    return result
                except ProviderLinkError as exc:
                    await db.rollback()
                    return exc.code

        async def consume_new_email_link(*, email: str, state_nonce: str) -> object:
            async with sessionmaker() as db:
                result = await consume_email_link_code(
                    db,
                    request=_email_auth_request(
                        Settings(
                            database_url=app_url,
                            web_login_workspace_id=ids["workspace_a"],
                        ),
                        path="/settings/account/email-link/verify",
                    ),
                    principal=principal,
                    workspace_id=ids["workspace_a"],
                    email=email,
                    code="381204",
                    state_nonce=state_nonce,
                )
                await db.commit()
                return result

        different_state_results = await asyncio.gather(
            confirm_merge_link(link_ids[0]),
            confirm_merge_link(link_ids[1]),
        )
        provider_results = [
            result for result in different_state_results if not isinstance(result, str)
        ]
        assert len(provider_results) == 2, different_state_results
        assert (
            len({result.merge_intent_id for result in provider_results}) == 1
        ), different_state_results
        provider_result = provider_results[0]

        concurrent_results = await asyncio.gather(
            confirm_merge_link(link_ids[2]),
            confirm_merge_link(link_ids[2]),
        )
        concurrent_provider_results = [
            result for result in concurrent_results if not isinstance(result, str)
        ]
        assert len(concurrent_provider_results) == 1, concurrent_results
        assert concurrent_results.count("provider_link_reused") == 1, concurrent_results
        assert concurrent_provider_results[0].merge_intent_id == provider_result.merge_intent_id
        assert provider_result.status == "merge_preview_ready"

        async with sessionmaker() as db:
            await apply_tenant_context(
                db,
                TenantDatabaseContext(
                    organization_id=ids["org_a"],
                    workspace_id=ids["workspace_a"],
                    user_id=ids["user_a"],
                    device_id=ids["device_a"],
                    auth_session_id=ids["session_a"],
                ),
            )
            email = f"forced-rls-new-link-{ids['slug']}@example.test"
            code = "381204"
            new_link_state = await _create_email_login_state(
                db,
                workspace_id=ids["workspace_a"],
                next_path="/settings/account",
                email=email,
                code=code,
                ttl_seconds=300,
                provider="email_link",
                secret=TEST_WEB_CSRF_SECRET,
            )
            await db.commit()
            email_result = await consume_email_link_code(
                db,
                request=_email_auth_request(
                    Settings(
                        database_url=app_url,
                        web_login_workspace_id=ids["workspace_a"],
                    ),
                    path="/settings/account/email-link/verify",
                ),
                principal=principal,
                workspace_id=ids["workspace_a"],
                email=email,
                code=code,
                state_nonce=new_link_state.state_nonce,
            )
            assert isinstance(email_result, EmailLinkCompletion)
            assert email_result.status == "identity_linked"
            await db.commit()

            concurrent_email = f"forced-rls-concurrent-link-{ids['slug']}@example.test"
            concurrent_link_states = tuple(
                [
                    await _create_email_login_state(
                        db,
                        workspace_id=ids["workspace_a"],
                        next_path="/settings/account",
                        email=concurrent_email,
                        code=code,
                        ttl_seconds=300,
                        provider="email_link",
                        secret=TEST_WEB_CSRF_SECRET,
                    )
                    for _ in range(2)
                ]
            )
            concurrent_link_state_nonces = tuple(
                state.state_nonce for state in concurrent_link_states
            )
            await db.commit()
            concurrent_email_results = await asyncio.gather(
                *(
                    consume_new_email_link(
                        email=concurrent_email,
                        state_nonce=state_nonce,
                    )
                    for state_nonce in concurrent_link_state_nonces
                )
            )
            assert all(
                isinstance(result, EmailLinkCompletion) and result.status == "identity_linked"
                for result in concurrent_email_results
            )

            merge_state = await _create_email_login_state(
                db,
                workspace_id=ids["workspace_a"],
                next_path="/settings/account",
                email=candidate_email,
                code=code,
                ttl_seconds=300,
                provider="email_link",
                secret=TEST_WEB_CSRF_SECRET,
            )
            await db.commit()
            oauth_metadata_email_result = await consume_email_link_code(
                db,
                request=_email_auth_request(
                    Settings(
                        database_url=app_url,
                        web_login_workspace_id=ids["workspace_a"],
                    ),
                    path="/settings/account/email-link/verify",
                ),
                principal=principal,
                workspace_id=ids["workspace_a"],
                email=candidate_email,
                code=code,
                state_nonce=merge_state.state_nonce,
            )
            assert isinstance(oauth_metadata_email_result, EmailLinkCompletion)
            assert oauth_metadata_email_result.status == "identity_linked"
            assert oauth_metadata_email_result.intent_id is None
            await db.commit()

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_auth_link_terminal_rls",
                reason_category="rls_probe_verify",
                feature_area="security",
            ),
        )
        link_status = await conn.scalar(
            text(
                """
                    select count(*) from workspace_provider_link_states
                    where id in (:link_a, :link_b, :link_c)
                      and resolution = 'merge_preview_ready'
                    """
            ),
            {
                "link_a": link_ids[0],
                "link_b": link_ids[1],
                "link_c": link_ids[2],
            },
        )
        intent_status = await conn.scalar(
            text(
                """
                    select status from account_merge_intents
                    where survivor_user_id = :survivor_user_id
                      and source_user_id = :source_user_id
                    """
            ),
            {
                "survivor_user_id": ids["user_a"],
                "source_user_id": source_user_id,
            },
        )
        email_callback_results = tuple(
            await conn.scalars(
                text(
                    """
                    select result from auth_callback_states
                    where state_nonce in (
                        :new_link_state_nonce, :concurrent_link_state_nonce_a,
                        :concurrent_link_state_nonce_b, :merge_state_nonce
                    )
                    order by state_nonce
                    """
                ),
                {
                    "new_link_state_nonce": new_link_state.state_nonce,
                    "concurrent_link_state_nonce_a": concurrent_link_state_nonces[0],
                    "concurrent_link_state_nonce_b": concurrent_link_state_nonces[1],
                    "merge_state_nonce": merge_state.state_nonce,
                },
            )
        )
        concurrent_identity_count = await conn.scalar(
            text(
                """
                    select count(*) from external_identities
                    where provider = 'email' and provider_subject = :email
                      and user_id = :user_id and is_active and is_verified
                    """
            ),
            {"email": concurrent_email, "user_id": ids["user_a"]},
        )
        oauth_metadata_email_identity_count = await conn.scalar(
            text(
                """
                    select count(*) from external_identities
                    where provider = 'email' and provider_subject = :email
                      and user_id = :user_id and is_active and is_verified
                    """
            ),
            {"email": candidate_email, "user_id": ids["user_a"]},
        )
        merge_preview_audit_count = await conn.scalar(
            text(
                """
                    select count(*) from auth_audit_events
                    where event_type = 'account_merge_preview_prepared'
                      and actor_user_id = :user_id
                    """
            ),
            {"user_id": ids["user_a"]},
        )

    assert link_status == 3
    assert intent_status == "preview_ready"
    assert email_callback_results == ("completed",) * 4
    assert concurrent_identity_count == 1
    assert oauth_metadata_email_identity_count == 1
    assert merge_preview_audit_count == 3


@pytest.mark.asyncio
async def test_forced_rls_account_merge_confirmation_revokes_access_after_completion(
    rls_engine: AsyncEngine,
    migrated_postgres_urls: MigratedPostgresUrls,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    intent_id = uuid4()
    source_identity_id = uuid4()
    callback_id = uuid4()
    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_account_merge_confirmation_rls",
                reason_category="rls_probe_seed",
                feature_area="security",
            ),
        )
        await conn.execute(
            text(
                """
                    update workspaces
                    set owner_user_id = :survivor_user_id, kind = 'personal'
                    where id = :survivor_workspace_id
                    """
            ),
            {
                "survivor_workspace_id": ids["workspace_a"],
                "survivor_user_id": ids["user_a"],
            },
        )
        await conn.execute(
            text(
                "update user_identities set organization_id = :organization_id "
                "where id = :source_user_id"
            ),
            {"organization_id": ids["org_a"], "source_user_id": ids["user_b"]},
        )
        await conn.execute(
            text(
                """
                    update workspaces
                    set organization_id = :organization_id,
                        owner_user_id = :source_user_id,
                        kind = 'personal'
                    where id = :source_workspace_id
                    """
            ),
            {
                "organization_id": ids["org_a"],
                "source_workspace_id": ids["workspace_b"],
                "source_user_id": ids["user_b"],
            },
        )
        await conn.execute(
            text(
                """
                    insert into external_identities
                        (id, user_id, provider, provider_subject, email,
                         is_verified, is_active)
                    values
                        (:id, :source_user_id, 'email', :subject, :subject, true, true)
                    """
            ),
            {
                "id": source_identity_id,
                "source_user_id": ids["user_b"],
                "subject": f"merge-confirm-source-{ids['slug']}",
            },
        )
        callback_nonce = f"merge-confirm-callback-{ids['slug']}"
        await conn.execute(
            text(
                """
                    insert into auth_callback_states
                        (id, provider, state_nonce, workspace_id, expected_state,
                         expires_at, used_at, result, verified_external_identity_id)
                    values
                        (:id, 'email', :nonce, :workspace_id, :nonce,
                         now() + interval '15 minutes', now(), 'completed',
                         :source_identity_id)
                    """
            ),
            {
                "id": callback_id,
                "nonce": callback_nonce,
                "workspace_id": ids["workspace_a"],
                "source_identity_id": source_identity_id,
            },
        )
        await conn.execute(
            text(
                """
                    insert into account_merge_intents
                        (id, workspace_id, survivor_user_id, source_user_id,
                         initiating_auth_session_id, source_external_identity_id,
                         proof_callback_state_id, email_proof_state, oauth_proof_state,
                         status, expires_at)
                    values
                        (:id, :workspace_id, :survivor_user_id, :source_user_id,
                         :session_id, :source_identity_id, :callback_id,
                         'verified', 'verified', 'preview_ready',
                         now() + interval '15 minutes')
                    """
            ),
            {
                "id": intent_id,
                "workspace_id": ids["workspace_a"],
                "survivor_user_id": ids["user_a"],
                "source_user_id": ids["user_b"],
                "session_id": ids["session_a"],
                "source_identity_id": source_identity_id,
                "callback_id": callback_id,
            },
        )

    async with _exact_app_role_engine(migrated_postgres_urls.migration_url) as app_engine:
        sessionmaker = async_sessionmaker(app_engine, expire_on_commit=False)
        merge_context = AccountMergeTenantContext(
            intent_id=intent_id,
            workspace_id=ids["workspace_a"],
            survivor_user_id=ids["user_a"],
            source_user_id=ids["user_b"],
        )
        async with sessionmaker() as db:
            await apply_tenant_context(db, merge_context)
            preview = await _merge_preview_from_db(
                db,
                workspace_id=ids["workspace_a"],
                survivor_user_id=ids["user_a"],
                source_user_id=ids["user_b"],
            )
            await db.execute(
                text(
                    "update account_merge_intents "
                    "set status = 'preview_ready', policy_version = :policy_version, "
                    "preview_fingerprint = :fingerprint "
                    "where id = :intent_id"
                ),
                {
                    "policy_version": preview.policy_version,
                    "fingerprint": preview.fingerprint,
                    "intent_id": intent_id,
                },
            )
            await db.flush()
            preview = await preview_merge_intent(db, intent_id=intent_id)
            result = await confirm_merge_intent(
                db,
                intent_id=intent_id,
                preview_fingerprint=preview.fingerprint,
                idempotency_key="forced-rls-merge-confirmation",
            )
            assert result.status == "completed"
            await db.commit()

        async with app_engine.connect() as conn:
            await apply_tenant_context_to_connection(conn, merge_context)
            assert not bool(await conn.scalar(text("select rec_account_merge_context_valid()")))
            assert (
                await conn.scalar(
                    text(
                        "select count(*) from account_merge_journals "
                        "where merge_intent_id = :intent_id"
                    ),
                    {"intent_id": intent_id},
                )
                == 0
            )

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_account_merge_confirmation_rls",
                reason_category="rls_probe_verify",
                feature_area="security",
            ),
        )
        intent_status = await conn.scalar(
            text("select status from account_merge_intents where id = :id"),
            {"id": intent_id},
        )
        journal_count = await conn.scalar(
            text(
                "select count(*) from account_merge_journals "
                "where merge_intent_id = :id and status = 'completed'"
            ),
            {"id": intent_id},
        )
        source_status = await conn.scalar(
            text("select status from user_identities where id = :id"),
            {"id": ids["user_b"]},
        )
        source_workspace = (
            await conn.execute(
                text("select owner_user_id, kind from workspaces where id = :id"),
                {"id": ids["workspace_b"]},
            )
        ).one()
        source_membership_count = await conn.scalar(
            text(
                "select count(*) from workspace_memberships "
                "where workspace_id = :workspace_id and user_id = :user_id "
                "and status = 'active'"
            ),
            {"workspace_id": ids["workspace_b"], "user_id": ids["user_a"]},
        )
        source_meeting_owner = await conn.scalar(
            text("select created_by_user_id from meetings where id = :id"),
            {"id": ids["meeting_b"]},
        )
        survivor_session_status = await conn.scalar(
            text("select status from auth_sessions where id = :id"),
            {"id": ids["session_a"]},
        )

    assert intent_status == "completed"
    assert journal_count == 1
    assert source_status == "merged"
    assert source_workspace == (None, "linked")
    assert source_membership_count == 0
    assert source_meeting_owner == ids["user_a"]
    assert survivor_session_status == "revoked"


@pytest.mark.asyncio
async def test_forced_rls_hidden_closure_blocks_finalizing_identity_activation(
    rls_engine: AsyncEngine,
    migrated_postgres_urls: MigratedPostgresUrls,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    request_id = uuid4()
    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_account_close_admin_race",
                reason_category="rls_probe_seed",
                feature_area="security",
            ),
        )
        await conn.execute(
            text(
                "update user_identities set organization_id = :organization_id where id = :user_id"
            ),
            {"organization_id": ids["org_a"], "user_id": ids["user_b"]},
        )
        await conn.execute(
            text(
                "update workspaces set organization_id = :organization_id, "
                "owner_user_id = :user_id, kind = 'personal' where id = :workspace_id"
            ),
            {
                "organization_id": ids["org_a"],
                "user_id": ids["user_b"],
                "workspace_id": ids["workspace_b"],
            },
        )
        await conn.execute(
            text(
                "insert into workspace_memberships "
                "(workspace_id, user_id, role, status) "
                "values (:workspace_id, :user_id, 'member', 'active')"
            ),
            {"workspace_id": ids["workspace_a"], "user_id": ids["user_b"]},
        )
        await conn.execute(
            text(
                "insert into account_closure_requests "
                "(id, workspace_id, requested_by_user_id, request_key, state, "
                "policy_version, requested_at, finalize_at, metadata_json) "
                "values (:id, :workspace_id, :user_id, :request_key, 'scheduled', "
                "'account-close-v1', now() - interval '8 days', "
                "now() - interval '1 day', '{}'::json)"
            ),
            {
                "id": request_id,
                "workspace_id": ids["workspace_b"],
                "user_id": ids["user_b"],
                "request_key": f"forced-rls-close-{ids['slug']}",
            },
        )

    async with _exact_app_role_engine(migrated_postgres_urls.migration_url) as app_engine:
        sessionmaker = async_sessionmaker(app_engine, expire_on_commit=False)
        async with sessionmaker() as db:
            await apply_tenant_context(
                db,
                TenantDatabaseContext(
                    organization_id=ids["org_a"],
                    workspace_id=ids["workspace_a"],
                    user_id=ids["user_a"],
                ),
            )
            await ensure_account_membership_activation_allowed(db, user_id=ids["user_b"])
            await db.rollback()

        maintenance_sessionmaker = async_sessionmaker(rls_engine, expire_on_commit=False)
        async with maintenance_sessionmaker() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="migration_verification",
                    actor_id="test_account_close_admin_race",
                    reason_category="account_close_finalization",
                    feature_area="security",
                ),
            )
            view, workspace_ids = await begin_account_close_finalization(
                db,
                request_id=request_id,
                now=datetime.now(UTC),
            )
            assert view.state == "finalizing"
            assert workspace_ids == (ids["workspace_b"],)
            await db.commit()

        async with sessionmaker() as db:
            await apply_tenant_context(
                db,
                TenantDatabaseContext(
                    organization_id=ids["org_a"],
                    workspace_id=ids["workspace_a"],
                    user_id=ids["user_a"],
                ),
            )
            with pytest.raises(ProblemDetail) as error:
                await ensure_account_membership_activation_allowed(
                    db,
                    user_id=ids["user_b"],
                )
            assert error.value.code == "account_membership_activation_unavailable"
            await db.rollback()

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_account_close_admin_race",
                reason_category="rls_probe_verify",
                feature_area="security",
            ),
        )
        assert (
            await conn.scalar(
                text("select status from user_identities where id = :user_id"),
                {"user_id": ids["user_b"]},
            )
            == "closed"
        )
        assert (
            await conn.scalar(
                text(
                    "select status from workspace_memberships "
                    "where workspace_id = :workspace_id and user_id = :user_id"
                ),
                {"workspace_id": ids["workspace_a"], "user_id": ids["user_b"]},
            )
            == "active"
        )


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
    hidden_run_id = f"smoke-hidden-{uuid4().hex}"
    seed = build_smoke_identity_seed(run_id)
    hidden_seed = build_smoke_identity_seed(hidden_run_id)
    maintenance_settings = Settings(database_url=migrated_postgres_urls.probe_url)
    await seed_identity(maintenance_settings, run_id, execute=True)
    await seed_identity(maintenance_settings, hidden_run_id, execute=True)

    meeting_id = uuid4()
    hidden_meeting_id = uuid4()
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

    hidden_engine = create_async_engine(migrated_postgres_urls.probe_url, pool_pre_ping=True)
    hidden_session_factory = async_sessionmaker(hidden_engine, expire_on_commit=False)
    try:
        async with hidden_session_factory() as db:
            await apply_tenant_context_to_connection(
                await db.connection(),
                MaintenanceTenantContext(
                    operation_name="production_smoke_setup",
                    actor_id="test_rls_postgres_policies",
                    reason_category="smoke_setup",
                    feature_area="deployment",
                ),
            )
            db.add(
                Meeting(
                    id=hidden_meeting_id,
                    workspace_id=hidden_seed.workspace_id,
                    created_by_user_id=hidden_seed.user_id,
                    device_id=hidden_seed.device_id,
                    local_recording_id=f"hidden-{run_id}",
                    duration_seconds=1,
                    status="ingested_pending_processing",
                )
            )
            db.add(
                ProcessingDependencyState(
                    meeting_id=hidden_meeting_id,
                    media_revision_id=media_revision_id,
                    workspace_id=seed.workspace_id,
                    dependency="mediascribe",
                    state="not_contacted",
                )
            )
            await db.commit()
    finally:
        await hidden_engine.dispose()

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

    rerun_removed_rows, rerun_removed_objects, rerun_residue = await cleanup_smoke_artifacts(run_id)
    assert rerun_removed_rows == 0
    assert rerun_removed_objects == 0
    assert rerun_residue == []

    verification_engine = create_async_engine(migrated_postgres_urls.probe_url, pool_pre_ping=True)
    try:
        async with verification_engine.connect() as conn:
            await apply_tenant_context_to_connection(
                conn,
                MaintenanceTenantContext(
                    operation_name="production_smoke_cleanup",
                    actor_id="test_rls_postgres_policies",
                    reason_category="residue_probe",
                    feature_area="deployment",
                ),
            )
            hidden_identity_count = int(
                await conn.scalar(
                    text("select count(*) from user_identities where id=:user_id"),
                    {"user_id": str(hidden_seed.user_id)},
                )
                or 0
            )
    finally:
        await verification_engine.dispose()
    assert hidden_identity_count == 1


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

    async def remove_linked_workspace_downgrade_guard() -> None:
        engine = create_async_engine(migrated_postgres_urls.migration_url)
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text("update workspaces set kind = 'corporate' where kind = 'linked'")
                )
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
    asyncio.run(remove_linked_workspace_downgrade_guard())
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
