from functools import lru_cache

from pydantic import AnyUrl, Field, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the ingest API."""

    model_config = SettingsConfigDict(
        env_prefix="TWOBRAIN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://twobrain_rec:twobrain_rec@localhost:54329/twobrain_rec"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "twobrain_rec"
    minio_secret_key: str = "twobrain_rec_dev_secret"
    minio_bucket: str = "twobrain-rec-ingest"
    minio_secure: bool = False

    public_base_url: AnyUrl | None = None

    max_recording_duration_seconds: PositiveInt = Field(default=14_400)
    max_track_bytes: PositiveInt = Field(default=2_684_354_560)
    max_package_bytes: PositiveInt = Field(default=5_368_709_120)
    upload_session_ttl_seconds: PositiveInt = Field(default=86_400)

    redact_headers: tuple[str, ...] = (
        "authorization",
        "cookie",
        "set-cookie",
        "x-content-sha256",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
