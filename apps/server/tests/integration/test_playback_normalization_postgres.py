from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from types import ModuleType
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from tests.fakes.fake_minio import FakeMinioStorage
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.postgres_rls import rls_test_database_url
from tests.integration.test_playback_normalization_workflow import (
    FakeNormalizationPipeline,
)
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.models import (
    Meeting,
    PlaybackNormalizationAttempt,
    PlaybackNormalizationJob,
    TrackArtifact,
)
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    apply_tenant_context,
    apply_tenant_scope,
)
from twobrain_rec_server.ingest.media_revisions import source_fingerprint_sha256
from twobrain_rec_server.normalization.pickup import (
    claim_due_normalization_job,
    dispatch_normalization_after_accepted_commit,
    enumerate_backfill_workspace_candidates,
    enumerate_normalization_cleanup_candidates,
)
from twobrain_rec_server.normalization.service import (
    inventory_playback_backfill_page,
    run_normalization_job,
)
from twobrain_rec_server.normalization.worker import require_schema_head

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0022_playback_normalization.py"
)
RUNTIME_ROLE_BOOTSTRAP = REPO_ROOT / "apps/server/scripts/bootstrap_runtime_database_roles.py"
RUNTIME_IDENTITY_VERIFY = REPO_ROOT / "apps/server/scripts/verify_runtime_database_identity.py"
PROFILE_VERSION = "review_m4a_aac_lc_48k_mono_64k_v1"
VALIDATION_VERSION = "playback_validator_v1"


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("playback_normalization_postgres", MIGRATION)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_runtime_role_bootstrap() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "playback_normalization_runtime_roles",
        RUNTIME_ROLE_BOOTSTRAP,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_runtime_identity_verify() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "playback_normalization_runtime_identity",
        RUNTIME_IDENTITY_VERIFY,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


async def _create_media_test_role(owner_url: str) -> tuple[str, bool]:
    role_name = "twobrain_rec_media"
    password = uuid4().hex
    engine = create_async_engine(owner_url, isolation_level="AUTOCOMMIT")
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
            bootstrap = _load_runtime_role_bootstrap()
            await conn.execute(
                text(
                    "grant select on "
                    f"{bootstrap._table_list(bootstrap.MEDIA_READ_ONLY_TABLES)} "
                    f"to {quoted_role}"
                )
            )
            await conn.execute(
                text(
                    "grant select, insert, update on "
                    f"{bootstrap._table_list(bootstrap.MEDIA_READ_WRITE_TABLES)} "
                    f"to {quoted_role}"
                )
            )
            await conn.execute(
                text(
                    "grant insert on "
                    f"{bootstrap._table_list(bootstrap.MEDIA_INSERT_ONLY_TABLES)} "
                    f"to {quoted_role}"
                )
            )
            for table_name, column_name in bootstrap.MEDIA_LOCK_COLUMNS:
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
    return (
        make_url(owner_url)
        .set(username=role_name, password=password)
        .render_as_string(hide_password=False),
        True,
    )


async def _drop_media_test_role(owner_url: str) -> None:
    engine = create_async_engine(owner_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.begin() as conn:
            quoted_role = _quote_identifier("twobrain_rec_media")
            await conn.execute(text(f"drop owned by {quoted_role}"))
            await conn.execute(text(f"drop role if exists {quoted_role}"))
    finally:
        await engine.dispose()


@pytest.fixture(scope="module")
def migrated_postgres_url() -> Iterator[str]:
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
    try:
        yield url
    finally:
        if previous_url is None:
            os.environ.pop("TWOBRAIN_DATABASE_URL", None)
        else:
            os.environ["TWOBRAIN_DATABASE_URL"] = previous_url
        get_settings.cache_clear()


@pytest.fixture(scope="module")
def media_postgres_url(migrated_postgres_url: str) -> Iterator[str]:
    media_url = os.getenv("RLS_TEST_MEDIA_DATABASE_URL")
    created = False
    if not media_url:
        media_url, created = asyncio.run(_create_media_test_role(migrated_postgres_url))
    try:
        yield media_url
    finally:
        if created:
            asyncio.run(_drop_media_test_role(migrated_postgres_url))


async def _seed_revision(engine: AsyncEngine) -> dict[str, UUID]:
    ids = {
        "organization_id": uuid4(),
        "workspace_id": uuid4(),
        "user_id": uuid4(),
        "device_id": uuid4(),
        "meeting_id": uuid4(),
        "media_revision_id": uuid4(),
    }
    suffix = uuid4().hex[:12]
    async with engine.begin() as conn:
        await conn.execute(
            text("insert into organizations (id, slug, name) values (:id, :slug, :name)"),
            {
                "id": ids["organization_id"],
                "slug": f"normalization-pg-{suffix}",
                "name": "Normalization PostgreSQL Proof",
            },
        )
        await conn.execute(
            text(
                """
                insert into workspaces (id, organization_id, slug, name)
                values (:id, :organization_id, :slug, :name)
                """
            ),
            {
                "id": ids["workspace_id"],
                "organization_id": ids["organization_id"],
                "slug": f"normalization-pg-{suffix}",
                "name": "Normalization PostgreSQL Proof",
            },
        )
        await conn.execute(
            text(
                """
                insert into user_identities (id, organization_id, external_subject, display_name)
                values (:id, :organization_id, :external_subject, :display_name)
                """
            ),
            {
                "id": ids["user_id"],
                "organization_id": ids["organization_id"],
                "external_subject": f"normalization-pg-{suffix}",
                "display_name": "Normalization PostgreSQL Proof",
            },
        )
        await conn.execute(
            text(
                """
                insert into workspace_memberships (workspace_id, user_id, role, status)
                values (:workspace_id, :user_id, 'owner', 'active')
                """
            ),
            {"workspace_id": ids["workspace_id"], "user_id": ids["user_id"]},
        )
        await conn.execute(
            text(
                """
                insert into registered_devices
                    (id, workspace_id, user_id, device_public_id, status, registration_state)
                values (:id, :workspace_id, :user_id, :device_public_id, 'active', 'approved')
                """
            ),
            {
                "id": ids["device_id"],
                "workspace_id": ids["workspace_id"],
                "user_id": ids["user_id"],
                "device_public_id": f"normalization-pg-{suffix}",
            },
        )
        await conn.execute(
            text(
                """
                insert into meetings
                    (id, workspace_id, created_by_user_id, device_id, local_recording_id,
                     duration_seconds, status)
                values
                    (:id, :workspace_id, :user_id, :device_id, :local_recording_id,
                     60, 'ingested_pending_processing')
                """
            ),
            {
                "id": ids["meeting_id"],
                "workspace_id": ids["workspace_id"],
                "user_id": ids["user_id"],
                "device_id": ids["device_id"],
                "local_recording_id": f"normalization-pg-{suffix}",
            },
        )
        await conn.execute(
            text(
                """
                insert into media_revisions
                    (id, workspace_id, meeting_id, local_media_revision_id, revision_number,
                     source_kind, status, immutable, accepted_at)
                values
                    (:id, :workspace_id, :meeting_id, :local_media_revision_id, 1,
                     'initial_recording', 'accepted', true, :accepted_at)
                """
            ),
            {
                "id": ids["media_revision_id"],
                "workspace_id": ids["workspace_id"],
                "meeting_id": ids["meeting_id"],
                "local_media_revision_id": f"normalization-pg-{suffix}",
                "accepted_at": datetime.now(UTC),
            },
        )
    return ids


async def _seed_queued_job(
    engine: AsyncEngine,
    ids: dict[str, UUID],
    *,
    candidate_body: bytes | None = None,
) -> dict[str, UUID | str]:
    job_id = uuid4()
    workflow_id = f"playback-normalization/{ids['media_revision_id']}/v1"
    manifest_sha256 = sha256(b"postgres-normalization-manifest" + job_id.bytes).hexdigest()
    track_sha256_by_role = {
        "microphone": sha256(b"postgres-normalization-microphone" + job_id.bytes).hexdigest(),
        "system": sha256(b"postgres-normalization-system" + job_id.bytes).hexdigest(),
    }
    source_fingerprint = source_fingerprint_sha256(
        media_revision_id=ids["media_revision_id"],
        source_kind="initial_recording",
        manifest_sha256=manifest_sha256,
        track_sha256_by_role=track_sha256_by_role,
        duration_seconds=60,
    )
    candidate_sha256 = sha256(candidate_body).hexdigest() if candidate_body is not None else None
    candidate_id = uuid4() if candidate_body is not None else None
    candidate_key = f"normalization-proof/{candidate_id}.m4a" if candidate_id is not None else None
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                update media_revisions
                set manifest_sha256 = :manifest_sha256,
                    track_sha256_by_role = cast(:track_sha256_by_role as jsonb),
                    duration_seconds = 60
                where id = :media_revision_id
                """
            ),
            {
                "manifest_sha256": manifest_sha256,
                "track_sha256_by_role": json.dumps(track_sha256_by_role, sort_keys=True),
                "media_revision_id": ids["media_revision_id"],
            },
        )
        await conn.execute(
            text(
                """
                insert into playback_normalization_jobs
                    (id, organization_id, workspace_id, requested_by_user_id,
                     source_device_id, meeting_id, media_revision_id, profile_version,
                     validation_version, trigger_kind, priority_class, source_kind,
                     source_fingerprint_sha256, planned_action, state, workflow_id)
                values
                    (:id, :organization_id, :workspace_id, :requested_by_user_id,
                     :source_device_id, :meeting_id, :media_revision_id, :profile_version,
                     :validation_version, 'finalize', 'new_ingest', 'initial_recording',
                     :source_fingerprint_sha256, :planned_action, 'queued', :workflow_id)
                """
            ),
            {
                "id": job_id,
                "organization_id": ids["organization_id"],
                "workspace_id": ids["workspace_id"],
                "requested_by_user_id": ids["user_id"],
                "source_device_id": ids["device_id"],
                "meeting_id": ids["meeting_id"],
                "media_revision_id": ids["media_revision_id"],
                "profile_version": PROFILE_VERSION,
                "validation_version": VALIDATION_VERSION,
                "source_fingerprint_sha256": source_fingerprint,
                "planned_action": (
                    "validate_candidate" if candidate_body is not None else "normalize_source"
                ),
                "workflow_id": workflow_id,
            },
        )
        if candidate_id is not None and candidate_key is not None and candidate_body is not None:
            await conn.execute(
                text(
                    """
                    insert into track_artifacts
                        (id, meeting_id, media_revision_id, workspace_id, track_role, codec,
                         sample_rate_hz, channel_count, duration_seconds, byte_length, sha256,
                         storage_object_key, status)
                    values
                        (:id, :meeting_id, :media_revision_id, :workspace_id, 'playback',
                         'm4a-aac-lc', 48000, 1, 60, :byte_length, :sha256,
                         :storage_object_key, 'candidate')
                    """
                ),
                {
                    "id": candidate_id,
                    "meeting_id": ids["meeting_id"],
                    "media_revision_id": ids["media_revision_id"],
                    "workspace_id": ids["workspace_id"],
                    "byte_length": len(candidate_body),
                    "sha256": candidate_sha256,
                    "storage_object_key": candidate_key,
                },
            )
    return {
        "job_id": job_id,
        "workflow_id": workflow_id,
        "candidate_id": candidate_id or "",
        "candidate_key": candidate_key or "",
    }


def _artifact_values(ids: dict[str, UUID], *, validated: bool) -> dict[str, object]:
    artifact_id = uuid4()
    digest = artifact_id.hex + artifact_id.hex
    values: dict[str, object] = {
        "id": artifact_id,
        "meeting_id": ids["meeting_id"],
        "media_revision_id": ids["media_revision_id"],
        "workspace_id": ids["workspace_id"],
        "codec": "aac",
        "sha256": digest,
        "storage_object_key": f"normalization-proof/{artifact_id}.m4a",
    }
    if validated:
        values.update(
            {
                "normalization_profile_version": PROFILE_VERSION,
                "validated_at": datetime.now(UTC),
                "derivation_kind": "uploaded_candidate",
                "source_fingerprint_sha256": digest,
                "validation_version": VALIDATION_VERSION,
            }
        )
    else:
        values.update(
            {
                "normalization_profile_version": None,
                "validated_at": None,
                "derivation_kind": None,
                "source_fingerprint_sha256": None,
                "validation_version": None,
            }
        )
    return values


async def _insert_artifact(engine: AsyncEngine, values: dict[str, object]) -> UUID:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                insert into track_artifacts
                    (id, meeting_id, media_revision_id, workspace_id, track_role, codec,
                     sample_rate_hz, channel_count, duration_seconds, byte_length, sha256,
                     storage_object_key, status, normalization_profile_version, validated_at,
                     derivation_kind, source_fingerprint_sha256, validation_version)
                values
                    (:id, :meeting_id, :media_revision_id, :workspace_id, 'playback', :codec,
                     48000, 1, 60, 4096, :sha256, :storage_object_key, 'stored',
                     :normalization_profile_version, :validated_at, :derivation_kind,
                     :source_fingerprint_sha256, :validation_version)
                """
            ),
            values,
        )
    return values["id"]  # type: ignore[return-value]


def test_postgres_partial_uniqueness_predicate_matches_canonical_truth() -> None:
    migration = _load_migration()
    predicate = " ".join(migration.CANONICAL_PLAYBACK_PREDICATE.lower().split())

    assert "track_role = 'playback'" in predicate
    assert "status = 'stored'" in predicate
    assert "normalization_profile_version = 'review_m4a_aac_lc_48k_mono_64k_v1'" in predicate
    assert "validated_at is not null" in predicate


def test_postgres_new_tables_force_rls_and_downgrade_restores_maintenance_allowlist() -> None:
    migration_text = MIGRATION.read_text(encoding="utf-8").lower()

    for table_name in (
        "playback_normalization_jobs",
        "playback_normalization_attempts",
        "playback_backfill_runs",
    ):
        assert table_name in migration_text
    assert "enable row level security" in migration_text
    assert "force row level security" in migration_text
    assert "playback_normalization_inventory" in migration_text
    assert "playback_normalization_dispatch" in migration_text
    assert "rec_playback_normalization_maintenance_allowed" in migration_text
    assert "for select" in migration_text


@pytest.mark.asyncio
async def test_runtime_role_bootstrap_is_idempotent_and_verifies_privileges(
    migrated_postgres_url: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    owner_url = make_url(migrated_postgres_url)
    owner_password = owner_url.password
    if not owner_password:
        pytest.skip("disposable PostgreSQL owner password is required")

    owner_engine = create_async_engine(migrated_postgres_url, isolation_level="AUTOCOMMIT")
    role_names = [
        "twobrain_rec_app",
        "twobrain_rec_maintenance",
        "twobrain_rec_media",
    ]
    created_roles = False
    membership_fixture_created = False
    membership_fixture_role = "twobrain_rec_membership_fixture"
    try:
        async with owner_engine.connect() as conn:
            existing = int(
                await conn.scalar(
                    text("select count(*) from pg_roles where rolname = any(:role_names)"),
                    {"role_names": role_names},
                )
                or 0
            )
        if existing:
            pytest.skip("runtime-role bootstrap proof requires a disposable role namespace")

        owner_secret = tmp_path / "owner"
        app_secret = tmp_path / "app"
        maintenance_secret = tmp_path / "maintenance"
        media_secret = tmp_path / "media"
        owner_secret.write_text(owner_password, encoding="utf-8")
        app_password = "graf_099_app_runtime_password"
        maintenance_password = "graf_099_maintenance_runtime_password"
        media_password = "graf_099_media_runtime_password"
        app_secret.write_text(app_password, encoding="utf-8")
        maintenance_secret.write_text(maintenance_password, encoding="utf-8")
        media_secret.write_text(media_password, encoding="utf-8")
        for path in (owner_secret, app_secret, maintenance_secret, media_secret):
            path.chmod(0o600)

        monkeypatch.setenv("TWOBRAIN_DB_HOST", owner_url.host or "127.0.0.1")
        monkeypatch.setenv("TWOBRAIN_DB_PORT", str(owner_url.port or 5432))
        monkeypatch.setenv("TWOBRAIN_DB_NAME", owner_url.database or "twobrain_rec")
        monkeypatch.setenv("TWOBRAIN_DB_OWNER_PASSWORD_FILE", str(owner_secret))
        monkeypatch.setenv("TWOBRAIN_DB_APP_PASSWORD_FILE", str(app_secret))
        monkeypatch.setenv(
            "TWOBRAIN_DB_MAINTENANCE_PASSWORD_FILE",
            str(maintenance_secret),
        )
        monkeypatch.setenv("TWOBRAIN_DB_MEDIA_PASSWORD_FILE", str(media_secret))
        bootstrap = _load_runtime_role_bootstrap()
        created_roles = True
        await bootstrap._bootstrap()
        await bootstrap._bootstrap()

        media_runtime_url = owner_url.set(
            username="twobrain_rec_media",
            password=media_password,
        ).render_as_string(hide_password=False)
        media_engine = create_async_engine(media_runtime_url, pool_pre_ping=True)
        try:
            await require_schema_head(media_engine)
        finally:
            await media_engine.dispose()

        identity = _load_runtime_identity_verify()
        for expected_role, password, expected_scheduler_access, expected_maintenance_access in (
            ("twobrain_rec_app", app_password, False, False),
            (
                "twobrain_rec_maintenance",
                maintenance_password,
                False,
                True,
            ),
            ("twobrain_rec_media", media_password, True, False),
        ):
            runtime_url = owner_url.set(
                username=expected_role,
                password=password,
            ).render_as_string(hide_password=False)
            monkeypatch.setenv("TWOBRAIN_DATABASE_URL", runtime_url)
            monkeypatch.setenv("TWOBRAIN_EXPECTED_DATABASE_ROLE", expected_role)
            get_settings.cache_clear()
            assert await identity._verify() == (
                expected_role,
                expected_scheduler_access,
                expected_maintenance_access,
            )

        async with owner_engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        "select rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, "
                        "rolinherit, rolreplication, rolbypassrls from pg_roles "
                        "where rolname = any(:role_names) order by rolname"
                    ),
                    {"role_names": role_names},
                )
            ).all()
            app_workspace_execute = await conn.scalar(
                text(
                    "select has_function_privilege('twobrain_rec_app', "
                    "'rec_playback_normalization_workspace_page(uuid, integer)', 'execute')"
                )
            )
            maintenance_workspace_execute = await conn.scalar(
                text(
                    "select has_function_privilege('twobrain_rec_maintenance', "
                    "'rec_playback_normalization_workspace_page(uuid, integer)', 'execute')"
                )
            )
            media_workspace_execute = await conn.scalar(
                text(
                    "select has_function_privilege('twobrain_rec_media', "
                    "'rec_playback_normalization_workspace_page(uuid, integer)', 'execute')"
                )
            )
            role_memberships = int(
                await conn.scalar(
                    text(
                        "select count(*) from pg_auth_members as memberships "
                        "join pg_roles as members on members.oid = memberships.member "
                        "join pg_roles as granted on granted.oid = memberships.roleid "
                        "where members.rolname = any(:role_names) "
                        "or granted.rolname = any(:role_names)"
                    ),
                    {"role_names": role_names},
                )
                or 0
            )
            media_table_grants = {
                (row.table_name, row.privilege_type)
                for row in (
                    await conn.execute(
                        text(
                            "select table_name, privilege_type "
                            "from information_schema.role_table_grants "
                            "where grantee = 'twobrain_rec_media' "
                            "and table_schema = 'public'"
                        )
                    )
                ).all()
            }
            media_can_update_meeting_timestamp = bool(
                await conn.scalar(
                    text(
                        "select has_column_privilege('twobrain_rec_media', "
                        "'public.meetings', 'updated_at', 'update')"
                    )
                )
            )
            media_can_update_meeting_status = bool(
                await conn.scalar(
                    text(
                        "select has_column_privilege('twobrain_rec_media', "
                        "'public.meetings', 'status', 'update')"
                    )
                )
            )

        assert len(rows) == 3
        assert all(row.rolcanlogin for row in rows)
        assert all(
            not any(
                (
                    row.rolsuper,
                    row.rolcreatedb,
                    row.rolcreaterole,
                    row.rolinherit,
                    row.rolreplication,
                    row.rolbypassrls,
                )
            )
            for row in rows
        )
        assert app_workspace_execute is False
        assert maintenance_workspace_execute is False
        assert media_workspace_execute is True
        assert role_memberships == 0
        expected_media_table_grants = {
            *((table_name, "SELECT") for table_name in bootstrap.MEDIA_READ_ONLY_TABLES),
            *(
                (table_name, privilege_type)
                for table_name in bootstrap.MEDIA_READ_WRITE_TABLES
                for privilege_type in ("INSERT", "SELECT", "UPDATE")
            ),
            *((table_name, "INSERT") for table_name in bootstrap.MEDIA_INSERT_ONLY_TABLES),
        }
        assert ("alembic_version", "SELECT") in media_table_grants
        assert media_table_grants == expected_media_table_grants
        assert media_can_update_meeting_timestamp is True
        assert media_can_update_meeting_status is False

        async with owner_engine.begin() as conn:
            await conn.execute(text(f"create role {_quote_identifier(membership_fixture_role)}"))
            membership_fixture_created = True
            await conn.execute(
                text(
                    "grant twobrain_rec_maintenance "
                    f"to {_quote_identifier(membership_fixture_role)}"
                )
            )
        with pytest.raises(RuntimeError, match="membership is unsafe"):
            await bootstrap._bootstrap()
        async with owner_engine.begin() as conn:
            await conn.execute(text(f"drop role {_quote_identifier(membership_fixture_role)}"))
            membership_fixture_created = False
    finally:
        get_settings.cache_clear()
        try:
            if membership_fixture_created:
                async with owner_engine.connect() as conn:
                    await conn.execute(
                        text(f"drop role if exists {_quote_identifier(membership_fixture_role)}")
                    )
            if created_roles:
                async with owner_engine.connect() as conn:
                    for role_name in role_names:
                        exists = bool(
                            await conn.scalar(
                                text("select exists(select 1 from pg_roles where rolname = :name)"),
                                {"name": role_name},
                            )
                        )
                        if exists:
                            quoted_role = _quote_identifier(role_name)
                            await conn.execute(text(f"drop owned by {quoted_role}"))
                            await conn.execute(text(f"drop role {quoted_role}"))
        finally:
            await owner_engine.dispose()


@pytest.mark.asyncio
async def test_rls_verifier_reuses_existing_role_without_global_state_mutation(
    migrated_postgres_url: str,
    tmp_path: Path,
) -> None:
    owner_url = make_url(migrated_postgres_url)
    if owner_url.username != "twobrain_rec" or not owner_url.password or not owner_url.host:
        pytest.skip("production-parity PostgreSQL owner URL is required")

    scratch_database = f"twobrain_rec_rls_regression_{uuid4().hex[:12]}"
    maintenance_role = "twobrain_rec_maintenance"
    membership_fixture_role = f"twobrain_rls_member_{uuid4().hex[:12]}"
    maintenance_password = f"graf-099:/?#%{uuid4().hex}"
    owner_engine = create_async_engine(migrated_postgres_url, isolation_level="AUTOCOMMIT")
    scratch_created = False
    maintenance_created = False
    membership_fixture_created = False

    async def role_snapshot() -> tuple[tuple[object, ...], tuple[tuple[object, ...], ...]]:
        async with owner_engine.connect() as conn:
            role_row = tuple(
                (
                    await conn.execute(
                        text(
                            "select oid, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, "
                            "rolinherit, rolreplication, rolbypassrls, rolconnlimit, "
                            "rolpassword, rolvaliduntil, "
                            "(select rolconfig from pg_roles where oid = pg_authid.oid) "
                            "from pg_authid where rolname = :role_name"
                        ),
                        {"role_name": maintenance_role},
                    )
                ).one()
            )
            memberships = tuple(
                tuple(row)
                for row in (
                    await conn.execute(
                        text(
                            "select roleid, member, grantor, admin_option "
                            "from pg_auth_members "
                            "where roleid = (select oid from pg_roles where rolname = :role_name) "
                            "or member = (select oid from pg_roles where rolname = :role_name) "
                            "order by roleid, member, grantor"
                        ),
                        {"role_name": maintenance_role},
                    )
                ).all()
            )
        return role_row, memberships

    def run_verifier(
        owner_secret: Path, maintenance_secret: Path
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.pop("RLS_TEST_DATABASE_URL", None)
        env.pop("RLS_TEST_PROBE_DATABASE_URL", None)
        env.pop("RLS_DESTRUCTIVE_PROBE_DATABASE_CLASS", None)
        return subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "apps/server/scripts/verify_rls_hardening.py"),
                "--runtime-owner-password-file",
                str(owner_secret),
                "--runtime-maintenance-password-file",
                str(maintenance_secret),
                "--runtime-database-name",
                scratch_database,
                "--runtime-database-host",
                owner_url.host,
                "--runtime-database-port",
                str(owner_url.port or 5432),
                "--destructive-probe-database",
                "disposable",
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    try:
        async with owner_engine.connect() as conn:
            existing = int(
                await conn.scalar(
                    text(
                        "select count(*) from pg_roles "
                        "where rolname in (:maintenance_role, :membership_role)"
                    ),
                    {
                        "maintenance_role": maintenance_role,
                        "membership_role": membership_fixture_role,
                    },
                )
                or 0
            )
            if existing:
                pytest.skip("existing-role regression requires a disposable role namespace")
            await conn.execute(text(f"create database {_quote_identifier(scratch_database)}"))
            scratch_created = True
            await conn.execute(
                text(
                    f"create role {_quote_identifier(maintenance_role)} login "
                    f"password {_quote_literal(maintenance_password)} "
                    "nosuperuser nocreatedb nocreaterole noinherit noreplication nobypassrls"
                )
            )
            maintenance_created = True
            await conn.execute(
                text(f"alter role {_quote_identifier(maintenance_role)} set row_security = on")
            )

        owner_secret = tmp_path / "owner-password"
        maintenance_secret = tmp_path / "maintenance-password"
        owner_secret.write_text(owner_url.password, encoding="utf-8")
        maintenance_secret.write_text(maintenance_password, encoding="utf-8")
        owner_secret.chmod(0o600)
        maintenance_secret.chmod(0o600)
        baseline = await role_snapshot()

        async with owner_engine.connect() as conn:
            await conn.execute(text(f"create role {_quote_identifier(membership_fixture_role)}"))
            membership_fixture_created = True
            await conn.execute(
                text(
                    f"grant {_quote_identifier(maintenance_role)} "
                    f"to {_quote_identifier(membership_fixture_role)}"
                )
            )
        blocked = run_verifier(owner_secret, maintenance_secret)
        blocked_output = blocked.stdout + blocked.stderr
        assert blocked.returncode != 0
        assert "reason=rls_probe_command_failed" in blocked_output
        assert "error_type=RuntimeError" in blocked_output
        assert owner_url.password not in blocked_output
        assert maintenance_password not in blocked_output
        scratch_url = owner_url.set(database=scratch_database).render_as_string(hide_password=False)
        scratch_engine = create_async_engine(scratch_url, pool_pre_ping=True)
        try:
            async with scratch_engine.connect() as conn:
                scratch_migrated = await conn.scalar(
                    text("select to_regclass('public.alembic_version') is not null")
                )
        finally:
            await scratch_engine.dispose()
        async with owner_engine.connect() as conn:
            await conn.execute(text(f"drop role {_quote_identifier(membership_fixture_role)}"))
            membership_fixture_created = False
        assert scratch_migrated is False
        assert await role_snapshot() == baseline

        passed = run_verifier(owner_secret, maintenance_secret)
        passed_output = passed.stdout + passed.stderr
        assert passed.returncode == 0, passed_output
        assert "rls_validation_result=pass" in passed_output
        assert "destructive_probe_database=disposable" in passed_output
        assert "probe_suite=direct_sql_rls_probes" in passed_output
        assert owner_url.password not in passed_output
        assert maintenance_password not in passed_output
        assert await role_snapshot() == baseline

        async with owner_engine.connect() as conn:
            await conn.execute(
                text(f"drop database {_quote_identifier(scratch_database)} with (force)")
            )
            scratch_created = False
            residue = await conn.scalar(
                text("select count(*) from pg_database where datname = :database_name"),
                {"database_name": scratch_database},
            )
            await conn.execute(text(f"drop role {_quote_identifier(maintenance_role)}"))
            maintenance_created = False
        assert residue == 0
    finally:
        async with owner_engine.connect() as conn:
            if scratch_created:
                await conn.execute(
                    text(
                        f"drop database if exists {_quote_identifier(scratch_database)} with (force)"
                    )
                )
            if membership_fixture_created:
                await conn.execute(
                    text(f"drop role if exists {_quote_identifier(membership_fixture_role)}")
                )
            if maintenance_created:
                await conn.execute(
                    text(f"drop role if exists {_quote_identifier(maintenance_role)}")
                )
        await owner_engine.dispose()


@pytest.mark.asyncio
async def test_postgres_inventory_function_returns_only_bounded_scope_ids(
    migrated_postgres_url: str,
    media_postgres_url: str,
) -> None:
    owner_engine = create_async_engine(migrated_postgres_url, pool_pre_ping=True)
    media_engine = create_async_engine(media_postgres_url, pool_pre_ping=True)
    sessionmaker = async_sessionmaker(media_engine, expire_on_commit=False)
    try:
        ids = await _seed_revision(owner_engine)
        async with sessionmaker() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="playback_normalization_inventory",
                    actor_id="postgres-inventory-test",
                    reason_category="automatic_backfill",
                    feature_area="playback_normalization",
                ),
            )
            rows = await enumerate_backfill_workspace_candidates(
                db,
                after_workspace_id=None,
                page_size=50,
            )
        matching = [row for row in rows if row.tenant_scope.workspace_id == ids["workspace_id"]]
        assert len(matching) == 1
        assert matching[0].tenant_scope == TenantScope(
            organization_id=ids["organization_id"],
            workspace_id=ids["workspace_id"],
            user_id=ids["user_id"],
            device_id=ids["device_id"],
        )
        async with sessionmaker() as db:
            await apply_tenant_scope(db, matching[0].tenant_scope, context_kind="worker")
            inventory = await inventory_playback_backfill_page(
                db,
                workspace_id=ids["workspace_id"],
                page_size=100,
                now=datetime(2026, 7, 14, 18, 0, tzinfo=UTC),
            )
        assert inventory.inventory_completed is True
        assert inventory.state == "complete"

        async with sessionmaker() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="playback_normalization_dispatch",
                    actor_id="postgres-dispatch-test",
                    reason_category="automatic_recovery",
                    feature_area="playback_normalization",
                ),
            )
            with pytest.raises(RuntimeError, match="maintenance context is not exact"):
                await enumerate_backfill_workspace_candidates(
                    db,
                    after_workspace_id=None,
                    page_size=50,
                )
    finally:
        await media_engine.dispose()
        await owner_engine.dispose()


@pytest.mark.asyncio
async def test_postgres_cleanup_function_returns_only_unverified_purged_attempts(
    migrated_postgres_url: str,
    media_postgres_url: str,
) -> None:
    owner_engine = create_async_engine(migrated_postgres_url, pool_pre_ping=True)
    media_engine = create_async_engine(media_postgres_url, pool_pre_ping=True)
    sessionmaker = async_sessionmaker(media_engine, expire_on_commit=False)
    try:
        ids = await _seed_revision(owner_engine)
        job_id = uuid4()
        unverified_deleted_attempt_id = uuid4()
        verified_deleted_attempt_id = uuid4()
        unrelated_purged_attempt_id = uuid4()
        current_time = datetime.now(UTC)
        async with owner_engine.begin() as conn:
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
                    "organization_id": ids["organization_id"],
                    "workspace_id": ids["workspace_id"],
                    "requested_by_user_id": ids["user_id"],
                    "source_device_id": ids["device_id"],
                    "meeting_id": ids["meeting_id"],
                    "media_revision_id": ids["media_revision_id"],
                    "source_fingerprint_sha256": uuid4().hex * 2,
                    "workflow_id": f"postgres-cleanup-{job_id}",
                },
            )
            await conn.execute(
                text(
                    """
                    insert into playback_normalization_attempts
                        (id, workspace_id, meeting_id, media_revision_id, job_id,
                         attempt_number, cycle_number, state, storage_object_key,
                         derivation_kind, source_stream_count, source_audio_stream_count,
                         cleanup_reason, cleaned_at, created_at, updated_at)
                    values
                        (:unverified_id, :workspace_id, :meeting_id, :media_revision_id, :job_id,
                         1, 1, 'purged', :unverified_key, 'single_source_transcode', 1, 1,
                         'meeting_deleting', null, :created_at, :now),
                        (:verified_id, :workspace_id, :meeting_id, :media_revision_id, :job_id,
                         2, 1, 'purged', :verified_key, 'single_source_transcode', 1, 1,
                         'meeting_deleting', :now, :created_at, :now),
                        (:unrelated_id, :workspace_id, :meeting_id, :media_revision_id, :job_id,
                         3, 1, 'purged', :unrelated_key, 'single_source_transcode', 1, 1,
                         'audio_purged', :now, :created_at, :now)
                    """
                ),
                {
                    "unverified_id": unverified_deleted_attempt_id,
                    "verified_id": verified_deleted_attempt_id,
                    "unrelated_id": unrelated_purged_attempt_id,
                    "workspace_id": ids["workspace_id"],
                    "meeting_id": ids["meeting_id"],
                    "media_revision_id": ids["media_revision_id"],
                    "job_id": job_id,
                    "unverified_key": (
                        f"normalization-attempts/{unverified_deleted_attempt_id}.m4a"
                    ),
                    "verified_key": f"normalization-attempts/{verified_deleted_attempt_id}.m4a",
                    "unrelated_key": f"normalization-attempts/{unrelated_purged_attempt_id}.m4a",
                    "now": current_time,
                    "created_at": current_time - timedelta(hours=7),
                },
            )

        async with sessionmaker() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="playback_normalization_dispatch",
                    actor_id="postgres-cleanup-test",
                    reason_category="automatic_recovery",
                    feature_area="playback_normalization",
                ),
            )
            candidates = await enumerate_normalization_cleanup_candidates(
                db,
                batch_size=25,
            )

        candidate_ids = {candidate.attempt_id for candidate in candidates}
        assert unverified_deleted_attempt_id in candidate_ids
        assert verified_deleted_attempt_id not in candidate_ids
        assert unrelated_purged_attempt_id not in candidate_ids

        active_attempt_id = uuid4()
        async with owner_engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    update playback_normalization_jobs
                    set state = 'running', lease_expires_at = :lease_expires_at
                    where id = :job_id
                    """
                ),
                {"job_id": job_id, "lease_expires_at": current_time + timedelta(hours=1)},
            )
            await conn.execute(
                text(
                    """
                    insert into playback_normalization_attempts
                        (id, workspace_id, meeting_id, media_revision_id, job_id,
                         attempt_number, cycle_number, state, storage_object_key,
                         derivation_kind, source_stream_count, source_audio_stream_count,
                         created_at, updated_at)
                    values
                        (:id, :workspace_id, :meeting_id, :media_revision_id, :job_id,
                         4, 1, 'local_preparing', :storage_object_key,
                         'single_source_transcode', 1, 1, :now, :now)
                    """
                ),
                {
                    "id": active_attempt_id,
                    "workspace_id": ids["workspace_id"],
                    "meeting_id": ids["meeting_id"],
                    "media_revision_id": ids["media_revision_id"],
                    "job_id": job_id,
                    "storage_object_key": f"normalization-attempts/{active_attempt_id}.m4a",
                    "now": current_time,
                },
            )

        async with sessionmaker() as db:
            await apply_tenant_context(
                db,
                MaintenanceTenantContext(
                    operation_name="playback_normalization_dispatch",
                    actor_id="postgres-cleanup-test",
                    reason_category="automatic_recovery",
                    feature_area="playback_normalization",
                ),
            )
            active_candidates = await enumerate_normalization_cleanup_candidates(
                db,
                batch_size=25,
            )

        assert active_attempt_id not in {candidate.attempt_id for candidate in active_candidates}
    finally:
        await media_engine.dispose()
        await owner_engine.dispose()


@pytest.mark.asyncio
async def test_postgres_finalize_commit_dispatches_normalization_in_same_request_session(
    migrated_postgres_url: str,
    media_postgres_url: str,
) -> None:
    owner_engine = create_async_engine(migrated_postgres_url, pool_pre_ping=True)
    media_engine = create_async_engine(media_postgres_url, pool_pre_ping=True)
    sessionmaker = async_sessionmaker(media_engine, expire_on_commit=False)
    try:
        ids = await _seed_revision(owner_engine)
        seeded = await _seed_queued_job(owner_engine, ids)
        scope = TenantScope(
            organization_id=ids["organization_id"],
            workspace_id=ids["workspace_id"],
            user_id=ids["user_id"],
            device_id=ids["device_id"],
        )
        settings = get_settings().model_copy(
            update={
                "playback_normalization_enabled": True,
                "playback_normalization_automatic_dispatch_enabled": True,
            }
        )
        temporal = FakeTemporalClient()
        async with sessionmaker() as db:
            await apply_tenant_scope(db, scope)
            accepted_job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.id == seeded["job_id"]
                )
            )
            assert accepted_job is not None
            await db.commit()
            db.sync_session.expunge_all()

            dispatch = await dispatch_normalization_after_accepted_commit(
                db=db,
                settings=settings,
                tenant_scope=scope,
                media_revision_id=ids["media_revision_id"],
                temporal_client=temporal,
                lease_owner="postgres-finalize-request",
                now=datetime(2026, 7, 14, 19, 0, tzinfo=UTC),
            )
            db.sync_session.expunge_all()
            persisted = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.id == seeded["job_id"]
                )
            )

        assert dispatch.started is True
        assert dispatch.reused is False
        assert list(temporal.starts) == [seeded["workflow_id"]]
        assert persisted is not None
        assert persisted.workflow_run_id == "run-1"
        assert persisted.lease_owner_sha256 is not None
    finally:
        await media_engine.dispose()
        await owner_engine.dispose()


@pytest.mark.asyncio
async def test_postgres_dispatch_rehydrates_scope_after_claim_commit(
    migrated_postgres_url: str,
    media_postgres_url: str,
) -> None:
    owner_engine = create_async_engine(migrated_postgres_url, pool_pre_ping=True)
    media_engine = create_async_engine(media_postgres_url, pool_pre_ping=True)
    sessionmaker = async_sessionmaker(media_engine, expire_on_commit=False)
    try:
        ids = await _seed_revision(owner_engine)
        foreign_ids = await _seed_revision(owner_engine)
        seeded = await _seed_queued_job(owner_engine, ids)
        foreign_seeded = await _seed_queued_job(owner_engine, foreign_ids)
        scope = TenantScope(
            organization_id=ids["organization_id"],
            workspace_id=ids["workspace_id"],
            user_id=ids["user_id"],
            device_id=ids["device_id"],
        )
        async with sessionmaker() as db:
            await apply_tenant_scope(db, scope, context_kind="worker")
            lease = await claim_due_normalization_job(
                db=db,
                job_id=seeded["job_id"],
                lease_owner="postgres-claim-boundary",
                lease_duration=timedelta(minutes=3),
                now=datetime(2026, 7, 14, 19, 5, tzinfo=UTC),
            )
            db.sync_session.expunge_all()
            visible_jobs = list(
                await db.scalars(
                    select(PlaybackNormalizationJob).where(
                        PlaybackNormalizationJob.id.in_(
                            (seeded["job_id"], foreign_seeded["job_id"])
                        )
                    )
                )
            )
            assert [job.id for job in visible_jobs] == [seeded["job_id"]]
            visible_jobs[0].workflow_run_id = "postgres-claim-run"
            await db.commit()
            db.sync_session.expunge_all()
            persisted = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.id == seeded["job_id"]
                )
            )
            workspace_setting = await db.scalar(
                text("select current_setting('app.workspace_id', true)")
            )

        assert lease.claimed is True
        assert persisted is not None
        assert persisted.workflow_run_id == "postgres-claim-run"
        assert workspace_setting == str(ids["workspace_id"])
    finally:
        await media_engine.dispose()
        await owner_engine.dispose()


@pytest.mark.asyncio
async def test_postgres_run_job_rehydrates_scope_after_prepare_commit_and_publishes(
    migrated_postgres_url: str,
    media_postgres_url: str,
    tmp_path: Path,
) -> None:
    owner_engine = create_async_engine(migrated_postgres_url, pool_pre_ping=True)
    media_engine = create_async_engine(media_postgres_url, pool_pre_ping=True)
    sessionmaker = async_sessionmaker(media_engine, expire_on_commit=False)
    storage = FakeMinioStorage()
    candidate_body = b"untrusted-playback-candidate"
    try:
        ids = await _seed_revision(owner_engine)
        seeded = await _seed_queued_job(
            owner_engine,
            ids,
            candidate_body=candidate_body,
        )
        storage.put_bytes(str(seeded["candidate_key"]), candidate_body)
        scope = TenantScope(
            organization_id=ids["organization_id"],
            workspace_id=ids["workspace_id"],
            user_id=ids["user_id"],
            device_id=ids["device_id"],
        )
        pipeline = FakeNormalizationPipeline("copy")
        async with sessionmaker() as db:
            await apply_tenant_scope(db, scope, context_kind="worker")
            execution = await run_normalization_job(
                db=db,
                storage=storage,
                job_id=seeded["job_id"],
                work_directory=tmp_path,
                pipeline=pipeline,
                lease_owner="postgres-publication-boundary",
            )
            db.sync_session.expunge_all()
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.id == seeded["job_id"]
                )
            )
            attempt = await db.scalar(
                select(PlaybackNormalizationAttempt).where(
                    PlaybackNormalizationAttempt.job_id == seeded["job_id"]
                )
            )
            artifacts = list(
                await db.scalars(
                    select(TrackArtifact).where(
                        TrackArtifact.meeting_id == ids["meeting_id"],
                        TrackArtifact.track_role == "playback",
                    )
                )
            )

        assert execution.reused is False
        assert pipeline.calls == ["candidate"]
        assert job is not None
        assert job.state == "ready"
        assert job.canonical_track_artifact_id is not None
        assert attempt is not None
        assert attempt.state == "published"
        assert attempt.published_track_artifact_id == job.canonical_track_artifact_id
        canonical = next(
            artifact for artifact in artifacts if artifact.id == job.canonical_track_artifact_id
        )
        assert canonical.status == "stored"
        assert canonical.validated_at is not None
        assert canonical.normalization_profile_version == PROFILE_VERSION
        assert storage.objects[canonical.storage_object_key] == b"canonical-candidate-copy"
    finally:
        await media_engine.dispose()
        await owner_engine.dispose()


@pytest.mark.asyncio
async def test_postgres_concurrent_due_pickup_grants_one_durable_lease(
    migrated_postgres_url: str,
    media_postgres_url: str,
) -> None:
    owner_engine = create_async_engine(migrated_postgres_url, pool_pre_ping=True)
    media_engine = create_async_engine(media_postgres_url, pool_pre_ping=True)
    sessionmaker = async_sessionmaker(media_engine, expire_on_commit=False)
    try:
        ids = await _seed_revision(owner_engine)
        scope = TenantScope(
            organization_id=ids["organization_id"],
            workspace_id=ids["workspace_id"],
            user_id=ids["user_id"],
            device_id=ids["device_id"],
        )
        job = PlaybackNormalizationJob(
            organization_id=ids["organization_id"],
            workspace_id=ids["workspace_id"],
            requested_by_user_id=ids["user_id"],
            source_device_id=ids["device_id"],
            meeting_id=ids["meeting_id"],
            media_revision_id=ids["media_revision_id"],
            profile_version=PROFILE_VERSION,
            validation_version=VALIDATION_VERSION,
            trigger_kind="finalize",
            priority_class="new_ingest",
            source_kind="initial_recording",
            source_fingerprint_sha256="f" * 64,
            planned_action="validate_candidate",
            state="queued",
            workflow_id=f"playback-normalization/{ids['media_revision_id']}/v1",
        )
        async with sessionmaker() as db:
            await apply_tenant_scope(db, scope, context_kind="worker")
            db.add(job)
            await db.commit()

        start = asyncio.Event()
        ready = 0
        ready_lock = asyncio.Lock()
        now = datetime(2026, 7, 14, 17, 30, tzinfo=UTC)

        async def claim(owner: str):
            nonlocal ready
            async with sessionmaker() as db:
                await apply_tenant_scope(db, scope, context_kind="worker")
                async with ready_lock:
                    ready += 1
                    if ready == 2:
                        start.set()
                await start.wait()
                return await claim_due_normalization_job(
                    db=db,
                    job_id=job.id,
                    lease_owner=owner,
                    lease_duration=timedelta(minutes=3),
                    now=now,
                )

        results = await asyncio.gather(claim("postgres-owner-a"), claim("postgres-owner-b"))
        assert sum(result.claimed for result in results) == 1
        assert sum(result.reused for result in results) == 1
        async with sessionmaker() as db:
            await apply_tenant_scope(db, scope, context_kind="worker")
            persisted = await db.get(PlaybackNormalizationJob, job.id)
            assert persisted is not None
            assert persisted.lease_owner_sha256 in {
                result.owner_sha256 for result in results if result.claimed
            }
            assert persisted.lease_expires_at == now + timedelta(minutes=3)
    finally:
        await media_engine.dispose()
        await owner_engine.dispose()


@pytest.mark.asyncio
async def test_postgres_partial_unique_index_allows_legacy_rows_and_one_concurrent_canonical(
    migrated_postgres_url: str,
) -> None:
    engine = create_async_engine(migrated_postgres_url, pool_pre_ping=True)
    try:
        ids = await _seed_revision(engine)
        await _insert_artifact(engine, _artifact_values(ids, validated=False))
        await _insert_artifact(engine, _artifact_values(ids, validated=False))

        start = asyncio.Event()
        ready = 0
        ready_lock = asyncio.Lock()

        async def publish(values: dict[str, object]) -> UUID:
            nonlocal ready
            async with engine.connect() as conn:
                transaction = await conn.begin()
                try:
                    async with ready_lock:
                        ready += 1
                        if ready == 2:
                            start.set()
                    await start.wait()
                    await conn.execute(
                        text(
                            """
                            insert into track_artifacts
                                (id, meeting_id, media_revision_id, workspace_id, track_role,
                                 codec, sample_rate_hz, channel_count, duration_seconds,
                                 byte_length, sha256, storage_object_key, status,
                                 normalization_profile_version, validated_at, derivation_kind,
                                 source_fingerprint_sha256, validation_version)
                            values
                                (:id, :meeting_id, :media_revision_id, :workspace_id,
                                 'playback', :codec, 48000, 1, 60, 4096, :sha256,
                                 :storage_object_key, 'stored', :normalization_profile_version,
                                 :validated_at, :derivation_kind, :source_fingerprint_sha256,
                                 :validation_version)
                            """
                        ),
                        values,
                    )
                    await transaction.commit()
                except BaseException:
                    await transaction.rollback()
                    raise
            return values["id"]  # type: ignore[return-value]

        results = await asyncio.gather(
            publish(_artifact_values(ids, validated=True)),
            publish(_artifact_values(ids, validated=True)),
            return_exceptions=True,
        )

        winners = [result for result in results if isinstance(result, UUID)]
        conflicts = [result for result in results if isinstance(result, IntegrityError)]
        async with engine.connect() as conn:
            canonical_count = await conn.scalar(
                text(
                    """
                    select count(*) from track_artifacts
                    where workspace_id = :workspace_id
                      and media_revision_id = :media_revision_id
                      and track_role = 'playback'
                      and status = 'stored'
                      and normalization_profile_version = :profile_version
                      and validated_at is not null
                    """
                ),
                {
                    "workspace_id": ids["workspace_id"],
                    "media_revision_id": ids["media_revision_id"],
                    "profile_version": PROFILE_VERSION,
                },
            )

        assert len(winners) == 1
        assert len(conflicts) == 1
        assert canonical_count == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_meeting_row_lock_serializes_deletion_against_publication(
    migrated_postgres_url: str,
) -> None:
    engine = create_async_engine(migrated_postgres_url, pool_pre_ping=True)
    try:
        ids = await _seed_revision(engine)
        async with engine.connect() as publisher, engine.connect() as deleter:
            publisher_tx = await publisher.begin()
            await publisher.execute(
                text("select id from meetings where id = :meeting_id for update"),
                {"meeting_id": ids["meeting_id"]},
            )

            deleter_tx = await deleter.begin()
            await deleter.execute(text("set local lock_timeout = '150ms'"))
            with pytest.raises(DBAPIError):
                await deleter.execute(
                    text("select id from meetings where id = :meeting_id for update"),
                    {"meeting_id": ids["meeting_id"]},
                )
            await deleter_tx.rollback()
            await publisher_tx.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_media_upload_lock_serializes_deletion_before_object_publication(
    migrated_postgres_url: str,
    media_postgres_url: str,
) -> None:
    owner_engine = create_async_engine(migrated_postgres_url, pool_pre_ping=True)
    media_engine = create_async_engine(media_postgres_url, pool_pre_ping=True)
    media_sessionmaker = async_sessionmaker(media_engine, expire_on_commit=False)
    try:
        ids = await _seed_revision(owner_engine)
        scope = TenantScope(
            organization_id=ids["organization_id"],
            workspace_id=ids["workspace_id"],
            user_id=ids["user_id"],
            device_id=ids["device_id"],
        )
        async with media_sessionmaker() as uploader:
            await apply_tenant_scope(uploader, scope, context_kind="worker")
            lock_result = await uploader.execute(
                update(Meeting)
                .where(
                    Meeting.id == ids["meeting_id"],
                    Meeting.workspace_id == ids["workspace_id"],
                )
                .values(updated_at=Meeting.updated_at)
            )
            assert lock_result.rowcount == 1

            async with owner_engine.connect() as deleter:
                deleter_tx = await deleter.begin()
                await deleter.execute(text("set local lock_timeout = '150ms'"))
                with pytest.raises(DBAPIError):
                    await deleter.execute(
                        text("select id from meetings where id = :meeting_id for update"),
                        {"meeting_id": ids["meeting_id"]},
                    )
                await deleter_tx.rollback()
            await uploader.rollback()
    finally:
        await media_engine.dispose()
        await owner_engine.dispose()
