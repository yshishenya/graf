from functools import lru_cache
from pathlib import Path
from urllib.parse import quote
from uuid import UUID

from pydantic import AnyUrl, Field, PositiveInt, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ALLOWED_READINESS_VERDICTS = ("not_ready", "blocked", "infra_smoke_ready")
FORBIDDEN_READINESS_VERDICTS = ("production_ready", "user_rollout_ready", "internal_user_pilot_ready")
SMOKE_IDENTITY_CLASS = "internal_smoke"

LOCAL_DEV_SMOKE_IDS = {
    UUID("10000000-0000-0000-0000-000000000001"),
    UUID("20000000-0000-0000-0000-000000000001"),
    UUID("30000000-0000-0000-0000-000000000001"),
    UUID("40000000-0000-0000-0000-000000000001"),
}


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

    postgres_password_file: Path | None = None
    minio_access_key_file: Path | None = None
    minio_secret_key_file: Path | None = None
    smoke_credential_file: Path | None = None

    smoke_identity_class: str | None = None
    smoke_organization_id: UUID | None = None
    smoke_workspace_id: UUID | None = None
    smoke_user_id: UUID | None = None
    smoke_device_id: UUID | None = None

    mediascribe_base_url: AnyUrl | None = None
    mediascribe_health_url: AnyUrl | None = None
    mediascribe_credential_file: Path | None = None
    langfuse_base_url: AnyUrl | None = None
    langfuse_health_url: AnyUrl | None = None
    langfuse_credential_file: Path | None = None

    max_recording_duration_seconds: PositiveInt = Field(default=14_400)
    max_track_bytes: PositiveInt = Field(default=2_684_354_560)
    max_package_bytes: PositiveInt = Field(default=5_368_709_120)
    max_upload_part_bytes: PositiveInt = Field(default=67_108_864)
    max_upload_spool_memory_bytes: PositiveInt = Field(default=8_388_608)
    upload_session_ttl_seconds: PositiveInt = Field(default=86_400)

    redact_headers: tuple[str, ...] = (
        "authorization",
        "cookie",
        "set-cookie",
        "x-content-sha256",
    )

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.env.lower() != "production":
            return self
        for path in (
            self.postgres_password_file,
            self.minio_access_key_file,
            self.minio_secret_key_file,
            self.smoke_credential_file,
        ):
            if path is not None and not path.is_file():
                raise ValueError("production Docker secret files must exist and be readable")
        if self.postgres_password_file is not None:
            postgres_password = self.postgres_password_file.read_text(encoding="utf-8").strip()
            self.database_url = self.database_url.replace("__POSTGRES_PASSWORD__", quote(postgres_password, safe=""))
        if self.minio_access_key_file is not None:
            self.minio_access_key = self.minio_access_key_file.read_text(encoding="utf-8").strip()
        if self.minio_secret_key_file is not None:
            self.minio_secret_key = self.minio_secret_key_file.read_text(encoding="utf-8").strip()
        unsafe_hosts = ("localhost", "127.0.0.1", "0.0.0.0", "::1")
        if any(host in self.database_url for host in unsafe_hosts):
            raise ValueError("production database_url must not point at localhost or wildcard hosts")
        if self.minio_endpoint.split(":", maxsplit=1)[0] in unsafe_hosts:
            raise ValueError("production minio_endpoint must not point at localhost or wildcard hosts")
        dev_secrets = {"twobrain_rec", "twobrain_rec_dev_secret", "minioadmin", "password", "changeme"}
        if self.minio_access_key in dev_secrets or self.minio_secret_key in dev_secrets:
            raise ValueError("production MinIO API credentials must not use development defaults")
        root_markers = ("root", "admin")
        if any(marker in self.minio_access_key.lower() for marker in root_markers):
            raise ValueError("production MinIO API access key must not be a root/admin credential")
        if self.smoke_identity_class is not None and self.smoke_identity_class != SMOKE_IDENTITY_CLASS:
            raise ValueError("production smoke identity class must be internal_smoke")
        smoke_ids = (
            self.smoke_organization_id,
            self.smoke_workspace_id,
            self.smoke_user_id,
            self.smoke_device_id,
        )
        if any(identifier in LOCAL_DEV_SMOKE_IDS for identifier in smoke_ids if identifier is not None):
            raise ValueError("production smoke identity/device must not reuse local development seed identifiers")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
