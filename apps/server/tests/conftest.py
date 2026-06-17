import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import twobrain_rec_server.ingest.store as store_module
from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, REVOKED_DEVICE_ID, USER_ID, WORKSPACE_ID
from tests.fakes.fake_minio import FakeMinioStorage
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.base import Base
from twobrain_rec_server.db.models import (
    Organization,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.ingest.store import InMemoryIngestStore
from twobrain_rec_server.main import create_app


@pytest.fixture
def test_settings(tmp_path) -> Settings:
    return Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'rec-test.db'}",
        minio_endpoint="localhost:9000",
        minio_access_key="test",
        minio_secret_key="test",
        minio_bucket="test-bucket",
        web_login_workspace_id=WORKSPACE_ID,
    )


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    engine = create_async_engine(test_settings.database_url)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def seed_database() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with sessionmaker() as session:
            session.add_all(
                [
                    Organization(id=ORG_ID, slug="test-org", name="Test Org"),
                    Workspace(id=WORKSPACE_ID, organization_id=ORG_ID, slug="test-workspace", name="Test Workspace"),
                    UserIdentity(id=USER_ID, organization_id=ORG_ID, external_subject=str(USER_ID), display_name="Test User"),
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
            await session.commit()

    asyncio.run(seed_database())
    app = create_app(test_settings)
    app.state.db_sessionmaker = sessionmaker
    app.state.storage = FakeMinioStorage()
    with TestClient(app) as test_client:
        test_client.app_state["engine"] = engine
        test_client.app_state["sessionmaker"] = sessionmaker
        test_client.app_state["storage"] = app.state.storage
        yield test_client
    asyncio.run(engine.dispose())


@pytest.fixture(autouse=True)
def reset_ingest_store() -> None:
    store_module.store = InMemoryIngestStore()
