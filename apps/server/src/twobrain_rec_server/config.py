from functools import lru_cache
from pathlib import Path
from urllib.parse import quote
from uuid import UUID

from pydantic import AliasChoices, AnyUrl, Field, PositiveInt, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ALLOWED_READINESS_VERDICTS = ("not_ready", "blocked", "infra_smoke_ready")
FORBIDDEN_READINESS_VERDICTS = ("production_ready", "user_rollout_ready", "internal_user_pilot_ready")
SMOKE_IDENTITY_CLASS = "internal_smoke"
SUPPORT_INCIDENT_GITHUB_OWNER = "yshishenya"
SUPPORT_INCIDENT_GITHUB_REPO = "crisp"

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
        populate_by_name=True,
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
    credential_encryption_key_file: Path | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "GRAF_CREDENTIAL_ENCRYPTION_KEY_FILE",
            "TWOBRAIN_CREDENTIAL_ENCRYPTION_KEY_FILE",
            "TWOBRAIN_CALENDAR_CREDENTIAL_KEY_FILE",
        ),
    )
    web_csrf_secret_file: Path | None = None
    support_incident_github_token_file: Path | None = None

    smoke_identity_class: str | None = None
    smoke_organization_id: UUID | None = None
    smoke_workspace_id: UUID | None = None
    smoke_user_id: UUID | None = None
    smoke_device_id: UUID | None = None
    web_login_workspace_id: UUID | None = None
    email_login_delivery_enabled: bool = False
    email_login_from_address: str | None = None
    email_login_from_name: str = "GRAF"
    postal_api_url: AnyUrl | None = None
    postal_api_key_file: Path | None = None
    postal_host_header: str | None = None
    postal_request_timeout_seconds: PositiveInt = Field(default=10)
    support_incident_github_owner: str = SUPPORT_INCIDENT_GITHUB_OWNER
    support_incident_github_repo: str = SUPPORT_INCIDENT_GITHUB_REPO
    support_incident_github_timeout_seconds: PositiveInt = Field(default=4)
    support_incident_rate_limit_window_seconds: PositiveInt = Field(default=3600)
    support_incident_rate_limit_max_attempts: PositiveInt = Field(default=10)
    public_analytics_enabled: bool = False
    public_analytics_yandex_metrica_id: str | None = None
    public_analytics_validation_mode: str = "disabled"
    public_analytics_replay_enabled: bool = False
    public_analytics_consent_copy_version: str = "2026-07-08.1"
    product_analytics_enabled: bool = False
    product_analytics_validation_mode: str = "disabled"
    product_analytics_provider_mode: str = "disabled"
    product_analytics_posthog_enabled: bool = False
    product_analytics_posthog_host: AnyUrl | None = None
    product_analytics_posthog_project_key_file: Path | None = None
    product_analytics_yandex_all_pages_enabled: bool = False
    product_analytics_yandex_offline_enabled: bool = False
    product_analytics_yandex_counter_id: str | None = None
    product_analytics_yandex_oauth_token_file: Path | None = None
    product_analytics_replay_enabled: bool = False
    product_analytics_retention_min_days: PositiveInt = Field(default=90)
    product_analytics_consent_copy_version: str = "2026-07-09.1"
    product_analytics_direct_desktop_egress_enabled: bool = False
    product_analytics_direct_desktop_egress_approved: bool = False
    product_analytics_legal_approved: bool = False
    product_analytics_dashboard_ready: bool = False
    product_analytics_provider_smoke_approved: bool = False
    product_analytics_campaign_readiness_approved: bool = False

    mediascribe_base_url: AnyUrl | None = None
    mediascribe_health_url: AnyUrl | None = None
    mediascribe_api_key_file: Path | None = None
    mediascribe_request_timeout_seconds: PositiveInt = Field(default=30)
    mediascribe_diarize: bool = True
    mediascribe_summarize: bool = False
    langfuse_base_url: AnyUrl | None = None
    langfuse_health_url: AnyUrl | None = None
    langfuse_credential_file: Path | None = None

    processing_enabled: bool = False
    processing_poll_interval_seconds: PositiveInt = Field(default=5)
    processing_max_poll_attempts: PositiveInt = Field(default=120)
    processing_max_in_memory_audio_bytes: PositiveInt = Field(default=536_870_912)
    temporal_address: str | None = None
    temporal_namespace: str = "default"
    temporal_task_queue: str = "twobrain-rec-processing"

    max_recording_duration_seconds: PositiveInt = Field(default=14_400)
    max_track_bytes: PositiveInt = Field(default=2_684_354_560)
    max_package_bytes: PositiveInt = Field(default=5_368_709_120)
    max_upload_part_bytes: PositiveInt = Field(default=1_073_741_824)
    max_upload_spool_memory_bytes: PositiveInt = Field(default=8_388_608)
    upload_session_ttl_seconds: PositiveInt = Field(default=86_400)
    auth_session_ttl_seconds: PositiveInt = Field(default=86_400)
    web_csrf_secret: str = "twobrain_rec_dev_web_csrf_secret"
    auth_callback_state_ttl_seconds: PositiveInt = Field(default=900)
    legacy_header_auth_enabled: bool = False
    retention_meeting_delete_after_days: PositiveInt | None = Field(default=365)
    retention_backup_expiry_days: PositiveInt | None = Field(default=30)
    retention_local_buffer_expiry_days: PositiveInt | None = Field(default=7)
    auth_storage_region_tag: str = "ru"
    auth_ru_local_storage_attested: bool = False

    yandex_client_id: str = "twobrain-yandex-client-id"
    vk_client_id: str = "twobrain-vk-client-id"
    telegram_bot_name: str = "twobrain-telegram-bot"
    telegram_client_id: str = "twobrain-telegram-client-id"
    yandex_client_secret_file: Path | None = None
    vk_client_secret_file: Path | None = None
    telegram_client_secret_file: Path | None = None
    yandex_redirect_path: str = "/api/v1/auth/callback/yandex"
    vk_redirect_path: str = "/api/v1/auth/callback/vk"
    telegram_redirect_path: str = "/api/v1/auth/callback/telegram"
    auth_base_url: AnyUrl | None = None

    redact_headers: tuple[str, ...] = (
        "authorization",
        "cookie",
        "set-cookie",
        "x-content-sha256",
    )

    @field_validator(
        "public_base_url",
        "postal_api_url",
        "mediascribe_base_url",
        "mediascribe_health_url",
        "langfuse_base_url",
        "langfuse_health_url",
        "auth_base_url",
        "web_login_workspace_id",
        "postal_host_header",
        "credential_encryption_key_file",
        "web_csrf_secret_file",
        "support_incident_github_token_file",
        "public_analytics_yandex_metrica_id",
        "product_analytics_posthog_host",
        "product_analytics_posthog_project_key_file",
        "product_analytics_yandex_counter_id",
        "product_analytics_yandex_oauth_token_file",
        mode="before",
    )
    @classmethod
    def empty_optional_string_is_unset(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @field_validator("public_analytics_validation_mode")
    @classmethod
    def validate_public_analytics_validation_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"disabled", "render_only", "provider_smoke"}:
            raise ValueError("public_analytics_validation_mode must be disabled, render_only, or provider_smoke")
        return normalized

    @field_validator("product_analytics_validation_mode")
    @classmethod
    def validate_product_analytics_validation_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"disabled", "render_only", "provider_smoke"}:
            raise ValueError("product_analytics_validation_mode must be disabled, render_only, or provider_smoke")
        return normalized

    @field_validator("product_analytics_provider_mode")
    @classmethod
    def validate_product_analytics_provider_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"disabled", "posthog_primary", "parallel_measurement"}:
            raise ValueError(
                "product_analytics_provider_mode must be disabled, posthog_primary, or parallel_measurement"
            )
        return normalized

    @field_validator("product_analytics_retention_min_days")
    @classmethod
    def validate_product_analytics_retention_min_days(cls, value: int) -> int:
        if value < 90:
            raise ValueError("product_analytics_retention_min_days must be at least 90")
        return value

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.env.lower() != "production":
            return self
        if self.public_analytics_enabled and self.public_analytics_yandex_metrica_id is None:
            raise ValueError("production public analytics requires public_analytics_yandex_metrica_id")
        if self.public_analytics_yandex_metrica_id is not None:
            counter_id = self.public_analytics_yandex_metrica_id.strip()
            lowered_counter_id = counter_id.lower()
            placeholder_markers = ("test", "replace", "changeme", "google", "gtm", "ga4", "measurement")
            if not counter_id.isdigit() or any(marker in lowered_counter_id for marker in placeholder_markers):
                raise ValueError("production public_analytics_yandex_metrica_id must be a real numeric Yandex counter ID")
        if self.product_analytics_retention_min_days < 90:
            raise ValueError("production product analytics retention must be at least 90 days")
        if self.product_analytics_enabled and self.product_analytics_validation_mode == "disabled":
            raise ValueError("production product analytics requires a non-disabled validation mode")
        if self.product_analytics_enabled and self.product_analytics_provider_mode == "disabled":
            raise ValueError("production product analytics requires an explicit provider mode")
        if self.product_analytics_posthog_enabled:
            if self.product_analytics_posthog_host is None:
                raise ValueError("production PostHog product analytics requires product_analytics_posthog_host")
            if self.product_analytics_posthog_project_key_file is None:
                raise ValueError(
                    "production PostHog product analytics requires product_analytics_posthog_project_key_file"
                )
        if self.product_analytics_yandex_all_pages_enabled or self.product_analytics_yandex_offline_enabled:
            if self.product_analytics_yandex_counter_id is None:
                raise ValueError("production Yandex product analytics requires product_analytics_yandex_counter_id")
            yandex_counter_id = self.product_analytics_yandex_counter_id.strip()
            lowered_yandex_counter_id = yandex_counter_id.lower()
            if not yandex_counter_id.isdigit() or any(
                marker in lowered_yandex_counter_id for marker in ("test", "replace", "changeme", "google", "gtm")
            ):
                raise ValueError("production product_analytics_yandex_counter_id must be a real numeric Yandex counter ID")
        if self.product_analytics_direct_desktop_egress_enabled and not (
            self.product_analytics_direct_desktop_egress_approved
            and self.product_analytics_legal_approved
            and self.product_analytics_provider_smoke_approved
        ):
            raise ValueError("direct desktop product analytics egress requires legal/security/QA/provider approval")
        required_secret_files = {
            "postgres_password_file": self.postgres_password_file,
            "minio_access_key_file": self.minio_access_key_file,
            "minio_secret_key_file": self.minio_secret_key_file,
            "smoke_credential_file": self.smoke_credential_file,
            "mediascribe_api_key_file": self.mediascribe_api_key_file,
            "credential_encryption_key_file": self.credential_encryption_key_file,
            "web_csrf_secret_file": self.web_csrf_secret_file,
            "support_incident_github_token_file": self.support_incident_github_token_file,
            "product_analytics_posthog_project_key_file": self.product_analytics_posthog_project_key_file,
            "product_analytics_yandex_oauth_token_file": self.product_analytics_yandex_oauth_token_file,
        }
        for field_name, path in required_secret_files.items():
            if path is None:
                continue
            if not path.is_file():
                raise ValueError(f"production Docker secret file is missing or unreadable: {field_name}")
            try:
                with path.open("r", encoding="utf-8"):
                    pass
            except OSError as exc:
                raise ValueError(f"production Docker secret file is missing or unreadable: {field_name}") from exc
        if self.processing_enabled and not self.temporal_address:
            raise ValueError("production processing requires temporal_address")
        if (
            self.mediascribe_api_key_file is not None
            and self.mediascribe_api_key_file.read_text(encoding="utf-8").strip() == ""
        ):
            raise ValueError("production MediaScribe API key file must be non-empty")
        if (
            self.credential_encryption_key_file is not None
            and self.credential_encryption_key_file.read_text(encoding="utf-8").strip() == ""
        ):
            raise ValueError("production credential encryption key file must be non-empty")
        if (
            self.support_incident_github_token_file is not None
            and self.support_incident_github_token_file.read_text(encoding="utf-8").strip() == ""
        ):
            raise ValueError("production support incident GitHub token file must be non-empty")
        if (
            self.support_incident_github_owner != SUPPORT_INCIDENT_GITHUB_OWNER
            or self.support_incident_github_repo != SUPPORT_INCIDENT_GITHUB_REPO
        ):
            raise ValueError("production support incidents must target yshishenya/crisp")
        if self.email_login_delivery_enabled:
            if self.web_login_workspace_id is None:
                raise ValueError("production email login delivery requires web_login_workspace_id")
            if self.postal_api_url is None:
                raise ValueError("production email login delivery requires postal_api_url")
            if self.postal_api_key_file is None:
                raise ValueError("production email login delivery requires postal_api_key_file")
            if self.email_login_from_address is None or not _is_valid_email_address(self.email_login_from_address):
                raise ValueError("production email login delivery requires a valid email_login_from_address")
            if not self.postal_api_key_file.is_file():
                raise ValueError("production Docker secret file is missing or unreadable: postal_api_key_file")
            if self.postal_api_key_file.read_text(encoding="utf-8").strip() == "":
                raise ValueError("production Postal API key file must be non-empty")
        if self.postgres_password_file is not None:
            postgres_password = self.postgres_password_file.read_text(encoding="utf-8").strip()
            self.database_url = self.database_url.replace("__POSTGRES_PASSWORD__", quote(postgres_password, safe=""))
        if self.minio_access_key_file is not None:
            self.minio_access_key = self.minio_access_key_file.read_text(encoding="utf-8").strip()
        if self.minio_secret_key_file is not None:
            self.minio_secret_key = self.minio_secret_key_file.read_text(encoding="utf-8").strip()
        if self.web_csrf_secret_file is not None:
            self.web_csrf_secret = self.web_csrf_secret_file.read_text(encoding="utf-8").strip()
        provider_secret_files = {
            "yandex_client_secret_file": self.yandex_client_secret_file,
            "vk_client_secret_file": self.vk_client_secret_file,
            "telegram_client_secret_file": self.telegram_client_secret_file,
        }
        for field_name, path in provider_secret_files.items():
            if path is None:
                continue
            if not path.is_file():
                raise ValueError(f"production Docker secret file is missing or unreadable: {field_name}")
            if path.read_text(encoding="utf-8").strip() == "":
                raise ValueError(f"production auth provider secret file must be non-empty: {field_name}")
        placeholder_values = {"replace-me", "changeme", "password", "secret", "default"}
        insecure_client_ids = {
            self.yandex_client_id.lower(),
            self.vk_client_id.lower(),
            self.telegram_client_id.lower(),
            self.telegram_bot_name.lower(),
        }
        if insecure_client_ids.intersection(placeholder_values):
            raise ValueError("production auth provider IDs must be explicit and non-placeholder")
        unsafe_hosts = ("localhost", "127.0.0.1", "0.0.0.0", "::1")
        if any(host in self.database_url for host in unsafe_hosts):
            raise ValueError("production database_url must not point at localhost or wildcard hosts")
        if self.minio_endpoint.split(":", maxsplit=1)[0] in unsafe_hosts:
            raise ValueError("production minio_endpoint must not point at localhost or wildcard hosts")
        dev_secrets = {
            "twobrain_rec",
            "twobrain_rec_dev_secret",
            "twobrain_rec_dev_web_csrf_secret",
            "minioadmin",
            "password",
            "changeme",
        }
        if self.minio_access_key in dev_secrets or self.minio_secret_key in dev_secrets:
            raise ValueError("production MinIO API credentials must not use development defaults")
        if self.web_csrf_secret in dev_secrets or len(self.web_csrf_secret) < 32:
            raise ValueError("production web_csrf_secret must be explicit and non-placeholder")
        root_markers = ("root", "admin")
        if any(marker in self.minio_access_key.lower() for marker in root_markers):
            raise ValueError("production MinIO API access key must not be a root/admin credential")
        if self.smoke_identity_class is not None and self.smoke_identity_class != SMOKE_IDENTITY_CLASS:
            raise ValueError("production smoke identity class must be internal_smoke")
        if self.auth_storage_region_tag.strip().lower() != "ru":
            raise ValueError("production auth storage region must be ru")
        if not self.auth_ru_local_storage_attested:
            raise ValueError("production auth RU-local storage attestation is required")
        smoke_ids = (
            self.smoke_organization_id,
            self.smoke_workspace_id,
            self.smoke_user_id,
            self.smoke_device_id,
        )
        if any(identifier in LOCAL_DEV_SMOKE_IDS for identifier in smoke_ids if identifier is not None):
            raise ValueError("production smoke identity/device must not reuse local development seed identifiers")
        return self


def _is_valid_email_address(value: str) -> bool:
    stripped = value.strip()
    if not stripped or "@" not in stripped or len(stripped) > 240:
        return False
    local, _, domain = stripped.partition("@")
    if not local or not domain or "." not in domain:
        return False
    if domain.startswith(".") or domain.endswith("."):
        return False
    unsafe_domains = {"localhost", "local", "example.com", "example.test"}
    return domain.lower() not in unsafe_domains


@lru_cache
def get_settings() -> Settings:
    return Settings()
