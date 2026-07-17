import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import twobrain_rec_server.ingest.store as store_module
from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, REVOKED_DEVICE_ID, USER_ID, WORKSPACE_ID
from tests.fakes.fake_minio import FakeMinioStorage
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.base import Base
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

pytest_plugins = ("tests.fixtures.postgres_test_database",)

REGISTRY_DATA = (
    Path(__file__).resolve().parents[1]
    / "src/twobrain_rec_server/db/migrations/data/0019_meeting_target_registry.json"
)


@pytest.fixture
def test_settings(postgres_test_database_url: str) -> Settings:
    return Settings(
        database_url=postgres_test_database_url,
        minio_endpoint="localhost:9000",
        minio_access_key="test",
        minio_secret_key="test",
        minio_bucket="test-bucket",
        web_login_workspace_id=WORKSPACE_ID,
    )


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    seed_engine = create_async_engine(test_settings.database_url)
    seed_sessionmaker = async_sessionmaker(seed_engine, expire_on_commit=False)

    async def seed_database() -> None:
        async with seed_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with seed_sessionmaker() as session:
            registry_document = json.loads(REGISTRY_DATA.read_text(encoding="utf-8"))
            registry_version = MeetingTargetRegistryVersion(
                workspace_id=None,
                registry_version=registry_document["registryVersion"],
                schema_version=registry_document["schemaVersion"],
                status="published",
                source="migration",
                document_json=registry_document,
                etag=registry_etag(registry_document),
            )
            session.add_all(
                [
                    Organization(id=ORG_ID, slug="test-org", name="Test Org"),
                ]
            )
            await session.flush()
            session.add_all(
                [
                    Workspace(id=WORKSPACE_ID, organization_id=ORG_ID, slug="test-workspace", name="Test Workspace"),
                    UserIdentity(id=USER_ID, organization_id=ORG_ID, external_subject=str(USER_ID), display_name="Test User"),
                    registry_version,
                ]
            )
            await session.flush()
            session.add_all(
                [
                    WorkspaceMembership(workspace_id=WORKSPACE_ID, user_id=USER_ID, role="owner", status="active"),
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
            await session.flush()
            session.add_all(
                MeetingTargetRegistryEntry(
                    registry_version_id=registry_version.id,
                    **entry,
                )
                for entry in registry_entries(registry_document)
            )
            await session.commit()
        await seed_engine.dispose()

    asyncio.run(seed_database())
    engine = create_async_engine(test_settings.database_url, poolclass=NullPool)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    app = create_app(test_settings)
    app.state.db_engine = engine
    app.state.db_sessionmaker = sessionmaker
    app.state.storage = FakeMinioStorage()
    with TestClient(app) as test_client:
        test_client.app_state["engine"] = engine
        test_client.app_state["sessionmaker"] = sessionmaker
        test_client.app_state["storage"] = app.state.storage
        yield test_client


@pytest.fixture(autouse=True)
def reset_ingest_store() -> None:
    store_module.store = InMemoryIngestStore()
