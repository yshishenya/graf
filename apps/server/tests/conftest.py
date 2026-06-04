import pytest
from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.ingest.store import InMemoryIngestStore
from twobrain_rec_server.main import create_app
import twobrain_rec_server.ingest.store as store_module


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://twobrain_rec:twobrain_rec@localhost:54329/twobrain_rec",
        minio_endpoint="localhost:9000",
        minio_access_key="test",
        minio_secret_key="test",
        minio_bucket="test-bucket",
    )


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    return TestClient(create_app(test_settings))


@pytest.fixture(autouse=True)
def reset_ingest_store() -> None:
    store_module.store = InMemoryIngestStore()
