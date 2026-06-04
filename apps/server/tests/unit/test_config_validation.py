import pytest
from pydantic import ValidationError

from twobrain_rec_server.config import Settings


def _production_settings(**overrides):
    values = {
        "env": "production",
        "database_url": "postgresql+asyncpg://twobrain_rec:secret@rec-postgres:5432/twobrain_rec",
        "minio_endpoint": "rec-minio:9000",
        "minio_access_key": "twobrain_rec_api",
        "minio_secret_key": "prod-api-secret",
        "minio_bucket": "twobrain-rec-ingest",
    }
    values.update(overrides)
    return Settings(**values)


def test_production_config_accepts_non_local_runtime_credentials() -> None:
    settings = _production_settings()

    assert settings.env == "production"


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+asyncpg://twobrain_rec:secret@localhost:5432/twobrain_rec",
        "postgresql+asyncpg://twobrain_rec:secret@127.0.0.1:5432/twobrain_rec",
    ],
)
def test_production_rejects_localhost_database_urls(database_url: str) -> None:
    with pytest.raises(ValidationError, match="database_url"):
        _production_settings(database_url=database_url)


@pytest.mark.parametrize("minio_endpoint", ["localhost:9000", "127.0.0.1:9000", "0.0.0.0:9000"])
def test_production_rejects_localhost_minio_endpoints(minio_endpoint: str) -> None:
    with pytest.raises(ValidationError, match="minio_endpoint"):
        _production_settings(minio_endpoint=minio_endpoint)


@pytest.mark.parametrize(
    ("minio_access_key", "minio_secret_key"),
    [
        ("twobrain_rec", "prod-api-secret"),
        ("twobrain_rec_api", "twobrain_rec_dev_secret"),
        ("minioadmin", "prod-api-secret"),
    ],
)
def test_production_rejects_default_dev_minio_credentials(
    minio_access_key: str,
    minio_secret_key: str,
) -> None:
    with pytest.raises(ValidationError, match="development defaults"):
        _production_settings(minio_access_key=minio_access_key, minio_secret_key=minio_secret_key)


def test_production_rejects_root_minio_api_credentials() -> None:
    with pytest.raises(ValidationError, match="root/admin"):
        _production_settings(minio_access_key="twobrain_root_api")
