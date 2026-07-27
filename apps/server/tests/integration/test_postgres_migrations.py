import re
from pathlib import Path
from uuid import UUID

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from tests.fakes.fake_minio import FakeMinioStorage
from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.db.models import (
    Organization,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.main import create_app

ROOT = Path(__file__).parents[4]
ORG_ID = UUID("10000000-0000-0000-0000-000000000001")
WORKSPACE_ID = UUID("20000000-0000-0000-0000-000000000001")
USER_ID = UUID("30000000-0000-0000-0000-000000000001")
DEVICE_ID = UUID("40000000-0000-0000-0000-000000000001")


async def _seed_identity(sessionmaker) -> None:
    async with sessionmaker() as db:
        db.add_all(
            [
                Organization(id=ORG_ID, slug="local-org", name="Local Org"),
                Workspace(id=WORKSPACE_ID, organization_id=ORG_ID, slug="local-workspace", name="Local Workspace"),
                UserIdentity(id=USER_ID, organization_id=ORG_ID, external_subject=str(USER_ID), display_name="Local User"),
            ]
        )
        await db.flush()
        db.add_all(
            [
                WorkspaceMembership(workspace_id=WORKSPACE_ID, user_id=USER_ID, role="owner", status="active"),
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


def test_mediascribe_migration_names_workspace_unique_constraints_distinctly() -> None:
    migration = (
        ROOT
        / "apps/server/src/twobrain_rec_server/db/migrations/versions/0004_mediascribe_processing_pipeline.py"
    ).read_text(encoding="utf-8")

    assert 'name="uq_mediascribe_jobs_workspace_meeting"' in migration
    assert 'name="uq_mediascribe_jobs_workspace_external_job"' in migration


def test_alembic_revision_ids_fit_default_version_table_length() -> None:
    versions = ROOT / "apps/server/src/twobrain_rec_server/db/migrations/versions"

    for migration_path in versions.glob("*.py"):
        migration = migration_path.read_text(encoding="utf-8")
        match = re.search(r'^revision: str = "([^"]+)"', migration, re.MULTILINE)

        assert match is not None, migration_path.name
        assert len(match.group(1)) <= 32, migration_path.name


def test_clean_database_migrates_and_accepts_seeded_identity_request(
    postgres_clean_database_url: str,
    monkeypatch,
) -> None:
    database_url = postgres_clean_database_url
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", database_url)
    get_settings.cache_clear()
    alembic_config = Config(str(ROOT / "apps/server/alembic.ini"))
    alembic_config.set_main_option("script_location", str(ROOT / "apps/server/src/twobrain_rec_server/db/migrations"))

    command.upgrade(alembic_config, "head")

    settings = Settings(database_url=database_url, minio_access_key="test", minio_secret_key="test", minio_bucket="test-bucket")
    import asyncio

    engine = create_async_engine(database_url, poolclass=NullPool)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    asyncio.run(_seed_identity(sessionmaker))
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
