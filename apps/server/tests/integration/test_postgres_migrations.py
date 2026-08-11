import asyncio
import importlib.util
import re
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.db.models import (
    Organization,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.main import create_app

from tests.fakes.fake_minio import FakeMinioStorage

ROOT = Path(__file__).parents[4]
ORG_ID = UUID("10000000-0000-0000-0000-000000000001")
WORKSPACE_ID = UUID("20000000-0000-0000-0000-000000000001")
USER_ID = UUID("30000000-0000-0000-0000-000000000001")
DEVICE_ID = UUID("40000000-0000-0000-0000-000000000001")
USER_SCOPED_RECORDING_MIGRATION = (
    ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0020_user_scoped_recording_ids.py"
)
WORKSPACE_ONBOARDING_MIGRATION = (
    ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0027_workspace_account_onboarding.py"
)
SPEAKER_NAMES_MIGRATION = (
    ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0029_meeting_speaker_names.py"
)


class _ScalarResult:
    def __init__(self, value: object | None) -> None:
        self.value = value

    def scalar(self) -> object | None:
        return self.value


class _FakePostgresBind:
    dialect = SimpleNamespace(name="postgresql")

    def __init__(
        self,
        existing_constraints: set[str],
        constraints_by_columns: dict[tuple[str, str], str] | None = None,
    ) -> None:
        self.existing_constraints = existing_constraints
        self.constraints_by_columns = constraints_by_columns or {}

    def execute(self, _statement, params) -> _ScalarResult:
        if "constraint_name" in params:
            return _ScalarResult(
                1 if params["constraint_name"] in self.existing_constraints else None
            )
        constraint_name = self.constraints_by_columns.get(
            (params["table_name"], params["columns_key"])
        )
        return _ScalarResult(constraint_name)


class _FakeMigrationOp:
    def __init__(
        self,
        existing_constraints: set[str],
        constraints_by_columns: dict[tuple[str, str], str] | None = None,
    ) -> None:
        self.bind = _FakePostgresBind(existing_constraints, constraints_by_columns)
        self.dropped_constraints: list[tuple[str, str, str | None]] = []
        self.created_constraints: list[tuple[str, str, list[str]]] = []

    def get_bind(self) -> _FakePostgresBind:
        return self.bind

    def drop_constraint(self, name: str, table_name: str, type_: str | None = None) -> None:
        self.dropped_constraints.append((name, table_name, type_))

    def create_unique_constraint(self, name: str, table_name: str, columns: list[str]) -> None:
        self.created_constraints.append((name, table_name, columns))


def _load_migration_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _seed_identity(sessionmaker) -> None:
    async with sessionmaker() as db:
        db.add(Organization(id=ORG_ID, slug="local-org", name="Local Org"))
        await db.flush()
        db.add_all(
            [
                Workspace(
                    id=WORKSPACE_ID,
                    organization_id=ORG_ID,
                    slug="local-workspace",
                    name="Local Workspace",
                ),
                UserIdentity(
                    id=USER_ID,
                    organization_id=ORG_ID,
                    external_subject=str(USER_ID),
                    display_name="Local User",
                ),
            ]
        )
        await db.flush()
        db.add_all(
            [
                WorkspaceMembership(
                    workspace_id=WORKSPACE_ID, user_id=USER_ID, role="owner", status="active"
                ),
                RegisteredDevice(
                    id=DEVICE_ID,
                    workspace_id=WORKSPACE_ID,
                    user_id=USER_ID,
                    device_public_id="local-macos-device",
                    status="active",
                ),
            ]
        )
        await db.commit()


def test_server_image_contains_alembic_migration_artifacts() -> None:
    dockerfile = (ROOT / "infra/server/Dockerfile").read_text(encoding="utf-8")

    assert "COPY apps/server/alembic.ini /app/alembic.ini" in dockerfile
    assert "COPY apps/server/src /app/src" in dockerfile


def test_alembic_migration_files_exist_for_clean_database_path() -> None:
    assert (ROOT / "apps/server/alembic.ini").exists()
    versions = ROOT / "apps/server/src/twobrain_rec_server/db/migrations/versions"
    assert (versions / "0001_ingest_foundation.py").exists()
    assert (versions / "0002_access_placeholders.py").exists()
    assert (versions / "0004_mediascribe_processing_pipeline.py").exists()
    assert (versions / "0006_access_sharing_downloads.py").exists()
    assert SPEAKER_NAMES_MIGRATION.exists()
    assert (versions / "0036_share_invitation_auth_lookup.py").exists()
    assert (versions / "0037_auth_rate_limit_buckets.py").exists()
    assert (versions / "0040_merge_content_regeneration_and_share_heads.py").exists()
    assert (versions / "0041_share_account_created_email.py").exists()


def test_production_share_head_upgrades_to_regeneration_merge(
    postgres_clean_database_url: str,
    monkeypatch,
) -> None:
    """A database at the legacy auth head must reach the current migration head."""

    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", postgres_clean_database_url)
    get_settings.cache_clear()
    alembic_config = Config(str(ROOT / "apps/server/alembic.ini"))
    alembic_config.set_main_option(
        "script_location", str(ROOT / "apps/server/src/twobrain_rec_server/db/migrations")
    )

    command.upgrade(alembic_config, "0037_auth_rate_limit_buckets")
    command.upgrade(alembic_config, "head")

    async def inspect_schema() -> tuple[list[str], set[str], set[tuple[str, str]], str]:
        engine = create_async_engine(postgres_clean_database_url)
        try:
            async with engine.connect() as connection:
                versions = (
                    await connection.scalars(text("select version_num from alembic_version"))
                ).all()
                tables = set(
                    (
                        await connection.scalars(
                            text(
                                "select table_name from information_schema.tables "
                                "where table_schema = 'public'"
                            )
                        )
                    ).all()
                )
                columns = {
                    (row.table_name, row.column_name)
                    for row in (
                        await connection.execute(
                            text(
                                "select table_name, column_name "
                                "from information_schema.columns "
                                "where table_schema = 'public'"
                            )
                        )
                    ).all()
                }
                maintenance_helper = await connection.scalar(
                    text("select pg_get_functiondef('rec_maintenance_allowed()'::regprocedure)")
                )
                return versions, tables, columns, str(maintenance_helper)
        finally:
            await engine.dispose()

    versions, tables, columns, maintenance_helper = asyncio.run(inspect_schema())
    assert versions == ["0070_fair_use_review_metadata"]
    assert {
        "dispatch_intents",
        "meeting_deletion_fences",
        "meeting_purge_journal",
    }.issubset(tables)
    required_columns = {
        "meetings": {"deletion_epoch"},
        "processing_workflows": {"purpose", "source_fingerprint", "deletion_epoch_at_start"},
        "processing_results": {"processing_workflow_id", "deletion_epoch_at_start"},
        "mediascribe_jobs": {
            "idempotency_key",
            "source_fingerprint",
            "deletion_epoch_at_start",
            "submission_claim_token",
            "submission_claimed_at",
        },
        "meeting_outcome_sets": {
            "source_fingerprint",
            "deletion_epoch_at_start",
            "expires_at",
            "generator_config_hash",
            "candidate_id",
        },
        "meeting_outcome_generation_attempts": {
            "idempotency_key",
            "request_intent",
            "source_result_hash",
            "source_fingerprint",
            "deletion_epoch_at_start",
            "expires_at",
            "display_format_name",
            "generator_config_hash",
        },
        "dispatch_intents": {"reconciliation_state", "last_reconciled_at"},
        "time_credit_ledger_entries": {"referral_attribution_id"},
    }
    assert all(
        (table_name, column_name) in columns
        for table_name, column_names in required_columns.items()
        for column_name in column_names
    )
    assert "prompt_optimization" in maintenance_helper
    assert "processing_legacy_lineage_reconciliation" in maintenance_helper


def test_fair_use_review_metadata_constraints_are_postgres_enforced(
    postgres_clean_database_url: str,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", postgres_clean_database_url)
    get_settings.cache_clear()
    alembic_config = Config(str(ROOT / "apps/server/alembic.ini"))
    alembic_config.set_main_option(
        "script_location", str(ROOT / "apps/server/src/twobrain_rec_server/db/migrations")
    )
    command.upgrade(alembic_config, "head")

    async def inspect_constraints() -> dict[str, str]:
        engine = create_async_engine(postgres_clean_database_url)
        try:
            async with engine.connect() as connection:
                rows = await connection.execute(
                    text(
                        "select conname, pg_get_constraintdef(oid) "
                        "from pg_constraint "
                        "where conrelid = 'fair_use_reviews'::regclass and contype = 'c'"
                    )
                )
                return {str(row[0]): str(row[1]).lower() for row in rows}
        finally:
            await engine.dispose()

    constraints = asyncio.run(inspect_constraints())
    deadline_name = next(
        name for name in constraints if name.endswith("_ck_fair_use_review_deadline")
    )
    deadline = constraints[deadline_name]
    assert "review_by >= starts_at" in deadline
    assert "review_by <=" in deadline
    assert "24:00:00" in deadline
    safe_evidence_name = next(
        name for name in constraints if name.endswith("_ck_fair_use_review_evidence_safe")
    )
    safe_evidence = constraints[safe_evidence_name]
    assert "!~*" in safe_evidence
    assert "meeting|content|email|card|token|payload" in safe_evidence


def test_speaker_name_migration_is_tenant_scoped_and_unique() -> None:
    migration = SPEAKER_NAMES_MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "0029_speaker_names"' in migration
    assert 'down_revision: str | None = "0028_active_space_read"' in migration
    assert '"meeting_speaker_names"' in migration
    assert all(name in migration for name in ('"workspace_id"', '"meeting_id"', '"speaker_key"'))
    assert "enable row level security" in migration
    assert "force row level security" in migration


def test_mediascribe_migration_names_workspace_unique_constraints_distinctly() -> None:
    migration = (
        ROOT
        / "apps/server/src/twobrain_rec_server/db/migrations/versions/0004_mediascribe_processing_pipeline.py"
    ).read_text(encoding="utf-8")

    assert 'name="uq_mediascribe_jobs_workspace_meeting"' in migration
    assert 'name="uq_mediascribe_jobs_workspace_external_job"' in migration


def test_content_regen_downgrade_restores_legacy_meeting_unique_constraints() -> None:
    migration = (
        ROOT
        / "apps/server/src/twobrain_rec_server/db/migrations/versions/0032_content_regeneration_lineage.py"
    ).read_text(encoding="utf-8")

    assert "_restore_legacy_unique_constraints" in migration
    assert "archive or deduplicate" in migration
    assert all(
        constraint in migration
        for constraint in (
            "processing_workflows_workspace_id_meeting_id_key",
            "uq_mediascribe_jobs_workspace_meeting",
            "processing_dependency_states_workspace_id_meeting_id_dependency",
        )
    )
    assert "op.create_unique_constraint(constraint_name, table_name" in migration


def test_alembic_revision_ids_fit_default_version_table_length() -> None:
    versions = ROOT / "apps/server/src/twobrain_rec_server/db/migrations/versions"
    legacy_overlength = {
        "0048_billing_notification_preferences",
        "0050_referral_token_lookup_context",
    }

    for migration_path in versions.glob("*.py"):
        migration = migration_path.read_text(encoding="utf-8")
        match = re.search(r'^revision: str = "([^"]+)"', migration, re.MULTILINE)

        assert match is not None, migration_path.name
        revision = match.group(1)
        assert len(revision) <= 32 or revision in legacy_overlength, migration_path.name


def test_workspace_onboarding_migration_keeps_personal_space_and_offer_boundaries() -> None:
    migration = WORKSPACE_ONBOARDING_MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "0027_workspace_onboarding"' in migration
    assert 'down_revision: str | None = "0026_active_cleanup"' in migration
    assert '"workspace_join_offers"' in migration
    assert '"owner_user_id"' in migration
    assert '"kind"' in migration
    assert "workspace_join_offers_tenant_isolation" in migration


def test_workspace_onboarding_migration_downgrades_cleanly(
    postgres_clean_database_url: str,
    monkeypatch,
) -> None:
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", postgres_clean_database_url)
    get_settings.cache_clear()
    alembic_config = Config(str(ROOT / "apps/server/alembic.ini"))
    alembic_config.set_main_option(
        "script_location", str(ROOT / "apps/server/src/twobrain_rec_server/db/migrations")
    )

    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "0026_active_cleanup")

    async def inspect_schema() -> tuple[set[str], set[str]]:
        engine = create_async_engine(postgres_clean_database_url)
        try:
            async with engine.connect() as connection:
                tables = set(
                    (
                        await connection.scalars(
                            text("select tablename from pg_tables where schemaname = 'public'")
                        )
                    ).all()
                )
                workspace_columns = set(
                    (
                        await connection.scalars(
                            text(
                                "select column_name from information_schema.columns "
                                "where table_schema = 'public' and table_name = 'workspaces'"
                            )
                        )
                    ).all()
                )
                return tables, workspace_columns
        finally:
            await engine.dispose()

    tables, workspace_columns = asyncio.run(inspect_schema())

    get_settings.cache_clear()
    assert "workspace_join_offers" not in tables
    assert "kind" not in workspace_columns
    assert "owner_user_id" not in workspace_columns


def test_user_scoped_recording_migration_drops_both_postgres_legacy_constraint_names() -> None:
    migration = _load_migration_module(
        USER_SCOPED_RECORDING_MIGRATION, "user_scoped_recording_migration"
    )

    for legacy_name in (
        "uq_meetings_workspace_id",
        "meetings_workspace_id_local_recording_id_key",
        "uq_meetings_workspace_id_local_recording_id",
    ):
        fake_op = _FakeMigrationOp({legacy_name})
        migration.op = fake_op

        migration._drop_legacy_constraint()

        assert fake_op.dropped_constraints == [(legacy_name, "meetings", "unique")]

    for legacy_name in (
        "media_revisions_workspace_id_local_media_revision_id_key",
        "uq_media_revisions_workspace_local_revision",
    ):
        fake_op = _FakeMigrationOp({legacy_name})
        migration.op = fake_op

        migration._drop_legacy_media_revision_constraint()

        assert fake_op.dropped_constraints == [(legacy_name, "media_revisions", "unique")]


def test_user_scoped_recording_migration_falls_back_to_postgres_constraint_columns() -> None:
    migration = _load_migration_module(
        USER_SCOPED_RECORDING_MIGRATION, "user_scoped_recording_migration_columns"
    )
    fake_op = _FakeMigrationOp(
        set(),
        {
            ("meetings", "workspace_id,local_recording_id"): "custom_meetings_recording_unique",
            (
                "media_revisions",
                "workspace_id,local_media_revision_id",
            ): "custom_media_revision_unique",
        },
    )
    migration.op = fake_op

    migration._drop_legacy_constraint()
    migration._drop_legacy_media_revision_constraint()

    assert fake_op.dropped_constraints == [
        ("custom_meetings_recording_unique", "meetings", "unique"),
        ("custom_media_revision_unique", "media_revisions", "unique"),
    ]


def test_user_scoped_recording_migration_skips_existing_postgres_target_constraints() -> None:
    migration = _load_migration_module(
        USER_SCOPED_RECORDING_MIGRATION, "user_scoped_recording_migration_existing"
    )
    fake_op = _FakeMigrationOp(
        set(),
        {
            (
                "meetings",
                "workspace_id,created_by_user_id,local_recording_id",
            ): migration.NEW_CONSTRAINT,
            (
                "media_revisions",
                "workspace_id,meeting_id,local_media_revision_id",
            ): migration.NEW_MEDIA_REVISION_CONSTRAINT,
        },
    )
    migration.op = fake_op

    migration.upgrade()

    assert fake_op.dropped_constraints == []
    assert fake_op.created_constraints == []


def test_clean_database_migrates_and_accepts_seeded_identity_request(
    postgres_clean_database_url: str,
    monkeypatch,
) -> None:
    database_url = postgres_clean_database_url
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", database_url)
    get_settings.cache_clear()
    alembic_config = Config(str(ROOT / "apps/server/alembic.ini"))
    alembic_config.set_main_option(
        "script_location", str(ROOT / "apps/server/src/twobrain_rec_server/db/migrations")
    )

    command.upgrade(alembic_config, "head")

    settings = Settings(
        database_url=database_url,
        minio_access_key="test",
        minio_secret_key="test",
        minio_bucket="test-bucket",
    )
    import asyncio

    seed_engine = create_async_engine(database_url)
    seed_sessionmaker = async_sessionmaker(seed_engine, expire_on_commit=False)
    asyncio.run(_seed_identity(seed_sessionmaker))
    asyncio.run(seed_engine.dispose())
    engine = create_async_engine(database_url)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    app = create_app(settings)
    app.state.db_sessionmaker = sessionmaker
    app.state.storage = FakeMinioStorage()

    headers = {
        "X-Organization-Id": str(ORG_ID),
        "X-Workspace-Id": str(WORKSPACE_ID),
        "X-User-Id": str(USER_ID),
        "X-Device-Id": str(DEVICE_ID),
    }
    with TestClient(app) as test_client:
        ready = test_client.get("/api/v1/health/ready")
        meeting = test_client.post(
            "/api/v1/meetings",
            headers=headers,
            json={"local_recording_id": "migrated-clean-db", "duration_seconds": 60},
        )
        openapi = test_client.get("/openapi.json")

    get_settings.cache_clear()
    asyncio.run(engine.dispose())
    assert ready.status_code == 200
    assert meeting.status_code == 200
    assert "/api/v1/meetings/{meeting_id}/processing" in openapi.json()["paths"]
