import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import twobrain_rec_server.ingest.store as store_module
from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, REVOKED_DEVICE_ID, USER_ID, WORKSPACE_ID
from tests.fakes.fake_minio import FakeMinioStorage
from tests.fixtures import postgres_test_database
from tests.fixtures.postgres_test_database import reset_mapped_tables
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    Organization,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.ingest.store import InMemoryIngestStore
from twobrain_rec_server.main import create_app

postgres_worker_database_url = postgres_test_database.postgres_worker_database_url
postgres_schema_database_url = postgres_test_database.postgres_schema_database_url
postgres_clean_database_url = postgres_test_database.postgres_clean_database_url

pytest_plugins = ("tests.fixtures.postgres_rls",)

GOVERNANCE_TEST_NAMES = frozenset(
    {
        "test_mvp_launch_proof_contract.py",
        "test_mvp_loop_readiness_contract.py",
        "test_mvp_owner_journey_proof_contract.py",
        "test_owner_review_live_proof_contract.py",
        "test_rls_evidence_contract.py",
        "test_rls_future_table_contract.py",
        "test_rls_migration_rollback_contract.py",
        "test_rls_openapi_scope.py",
        "test_rls_out_of_scope_boundaries.py",
        "test_rls_policy_matrix_contract.py",
        "test_rls_production_boundary.py",
        "test_rls_production_state_contract.py",
        "test_rls_production_truth_contract.py",
        "test_rls_rollout_truth_docs.py",
        "test_rls_table_inventory_contract.py",
        "test_rls_tenant_isolation_contract.py",
        "test_rls_validation_output_contract.py",
    }
)


async def _seed_database(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessionmaker() as session:
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
            await session.commit()
    finally:
        await engine.dispose()


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
def client(test_settings: Settings) -> TestClient:
    engine = create_async_engine(test_settings.database_url, poolclass=NullPool)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
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
            test_client.app_state["storage"] = storage
            yield test_client
    finally:
        asyncio.run(engine.dispose())


@pytest.fixture(autouse=True)
def reset_ingest_store() -> None:
    store_module.store = InMemoryIngestStore()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    del config
    for item in items:
        test_path = Path(str(item.fspath))
        test_name = test_path.name
        if any(
            fixture_name in item.fixturenames
            for fixture_name in (
                "client",
                "test_settings",
                "postgres_clean_database_url",
                "postgres_schema_database_url",
            )
        ):
            item.add_marker("requires_postgres")
        if (
            "governance" in test_path.parts
            or test_name in GOVERNANCE_TEST_NAMES
            or test_name.startswith("test_mvp_")
            or test_name.startswith("test_product_analytics")
            or test_name.startswith("test_product_activation_analytics")
        ):
            item.add_marker("governance")
