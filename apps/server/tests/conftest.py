import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import twobrain_rec_server.ingest.store as store_module
from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, REVOKED_DEVICE_ID, USER_ID, WORKSPACE_ID
from tests.fakes.fake_minio import FakeMinioStorage
from tests.fixtures.postgres_test_database import (
    ensure_disposable_media_role,
    prepare_schema,
    reset_mapped_tables,
)
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    MeetingTargetRegistryEntry,
    MeetingTargetRegistryVersion,
    Organization,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.ingest.store import InMemoryIngestStore
from twobrain_rec_server.main import create_app
from twobrain_rec_server.meeting_detection.registry import registry_entries, registry_etag

pytest_plugins = (
    "tests.fixtures.postgres_test_database",
    "tests.fixtures.postgres_rls",
)

REGISTRY_DATA = (
    Path(__file__).resolve().parents[1]
    / "src/twobrain_rec_server/db/migrations/data/0030_meeting_target_registry.json"
)
REGISTRY_DOCUMENT = json.loads(REGISTRY_DATA.read_text(encoding="utf-8"))


async def _seed_database(database_url: str) -> None:
    seed_engine = create_async_engine(database_url, poolclass=NullPool)
    seed_sessionmaker = async_sessionmaker(seed_engine, expire_on_commit=False)
    try:
        async with seed_sessionmaker() as session:
            registry_version = MeetingTargetRegistryVersion(
                workspace_id=None,
                registry_version=REGISTRY_DOCUMENT["registryVersion"],
                schema_version=REGISTRY_DOCUMENT["schemaVersion"],
                status="published",
                source="migration",
                document_json=REGISTRY_DOCUMENT,
                etag=registry_etag(REGISTRY_DOCUMENT),
            )
            session.add_all(
                [
                    Organization(id=ORG_ID, slug="test-org", name="Test Org"),
                    Workspace(
                        id=WORKSPACE_ID,
                        organization_id=ORG_ID,
                        slug="test-workspace",
                        name="Test Workspace",
                    ),
                    UserIdentity(
                        id=USER_ID,
                        organization_id=ORG_ID,
                        external_subject=str(USER_ID),
                        display_name="Test User",
                    ),
                    registry_version,
                ]
            )
            await session.flush()
            session.add_all(
                [
                    WorkspaceMembership(
                        workspace_id=WORKSPACE_ID,
                        user_id=USER_ID,
                        role="owner",
                        status="active",
                    ),
                    RegisteredDevice(
                        id=DEVICE_ID,
                        workspace_id=WORKSPACE_ID,
                        user_id=USER_ID,
                        device_public_id="test-device",
                        status="active",
                    ),
                    RegisteredDevice(
                        id=REVOKED_DEVICE_ID,
                        workspace_id=WORKSPACE_ID,
                        user_id=USER_ID,
                        device_public_id="revoked-device",
                        status="revoked",
                    ),
                ]
            )
            session.add_all(
                MeetingTargetRegistryEntry(
                    registry_version_id=registry_version.id,
                    **entry,
                )
                for entry in registry_entries(REGISTRY_DOCUMENT)
            )
            await session.commit()
    finally:
        await seed_engine.dispose()


@pytest.fixture(scope="session")
def postgres_schema_database_url(postgres_worker_database_url: str) -> str:
    prepare_schema(postgres_worker_database_url)
    return postgres_worker_database_url


@pytest.fixture(scope="session")
def postgres_media_database_url(postgres_schema_database_url: str) -> str:
    return asyncio.run(ensure_disposable_media_role(postgres_schema_database_url))


@pytest.fixture
def postgres_seeded_database_url(postgres_schema_database_url: str) -> str:
    asyncio.run(reset_mapped_tables(postgres_schema_database_url))
    asyncio.run(_seed_database(postgres_schema_database_url))
    return postgres_schema_database_url


@pytest.fixture
def test_settings(postgres_seeded_database_url: str) -> Settings:
    return Settings(
        database_url=postgres_seeded_database_url,
        minio_endpoint="localhost:9000",
        minio_access_key="test",
        minio_secret_key="test",
        minio_bucket="test-bucket",
        web_login_workspace_id=WORKSPACE_ID,
    )


@pytest.fixture
def client(test_settings: Settings, postgres_media_database_url: str) -> TestClient:
    engine = create_async_engine(test_settings.database_url, poolclass=NullPool)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    media_engine = create_async_engine(postgres_media_database_url, poolclass=NullPool)
    media_sessionmaker = async_sessionmaker(media_engine, expire_on_commit=False)
    storage = FakeMinioStorage()
    with (
        patch("twobrain_rec_server.main.create_engine", return_value=engine),
        patch("twobrain_rec_server.main.create_sessionmaker", return_value=sessionmaker),
        patch("twobrain_rec_server.main.get_storage", return_value=storage),
    ):
        app = create_app(test_settings)
    try:
        with TestClient(app) as test_client:
            test_client.app_state["engine"] = engine
            test_client.app_state["sessionmaker"] = sessionmaker
            test_client.app_state["media_engine"] = media_engine
            test_client.app_state["media_sessionmaker"] = media_sessionmaker
            test_client.app_state["storage"] = storage
            yield test_client
    finally:
        asyncio.run(media_engine.dispose())
        asyncio.run(engine.dispose())


@pytest.fixture(autouse=True)
def reset_ingest_store() -> None:
    store_module.store = InMemoryIngestStore()
