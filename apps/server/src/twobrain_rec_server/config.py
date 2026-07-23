from functools import lru_cache
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from uuid import UUID

from pydantic import AliasChoices, AnyUrl, Field, PositiveInt, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ALLOWED_READINESS_VERDICTS = ("not_ready", "blocked", "infra_smoke_ready")
FORBIDDEN_READINESS_VERDICTS = (
    "production_ready",
    "user_rollout_ready",
    "internal_user_pilot_ready",
)
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
    web_runtime_enabled: bool = True

    database_url: str = (
        "postgresql+asyncpg://twobrain_rec:twobrain_rec@localhost:54329/twobrain_rec"
    )
    # Deployment-global prompt optimization uses the maintenance role only.
    prompt_optimization_database_url: str | None = None

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "twobrain_rec"
    minio_secret_key: str = "twobrain_rec_dev_secret"
    minio_bucket: str = "twobrain-rec-ingest"
    minio_secure: bool = False

    public_base_url: AnyUrl | None = None

    postgres_password_file: Path | None = None
    prompt_optimization_postgres_password_file: Path | None = None
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
    web_login_workspace_id: UUID | None = Field(
        default=None,
        description=(
            "Internal bootstrap workspace for public auth policy and organization lookup; "
            "never a public enrollment destination."
        ),
    )
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
    product_analytics_posthog_autocapture_enabled: bool = True
    product_analytics_posthog_credential_suppression_enabled: bool = True
    product_analytics_posthog_web_direct_enabled: bool = True
    product_analytics_posthog_desktop_direct_enabled: bool = False
    product_analytics_yandex_all_pages_enabled: bool = False
    product_analytics_yandex_offline_enabled: bool = False
    product_analytics_yandex_counter_id: str | None = None
    product_analytics_yandex_oauth_token_file: Path | None = None
    product_analytics_yandex_inventory_version: str = "096.2026-07-09.1"
    product_analytics_rollback_mode: str = "none"
    product_analytics_replay_enabled: bool = False
    product_analytics_retention_min_days: PositiveInt = Field(default=90)
    product_analytics_consent_copy_version: str = "2026-07-09.1"
    product_analytics_direct_desktop_egress_enabled: bool = False
    product_analytics_direct_desktop_egress_approved: bool = False
    product_analytics_legal_approved: bool = False
    product_analytics_privacy_approved: bool = False
    product_analytics_security_approved: bool = False
    product_analytics_qa_approved: bool = False
    product_analytics_disclosure_approved: bool = False
    product_analytics_dashboard_ready: bool = False
    product_analytics_provider_smoke_approved: bool = False
    product_analytics_rollback_approved: bool = False
    product_analytics_live_provider_delivery_approved: bool = False
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
    langfuse_public_key_file: Path | None = None
    langfuse_secret_key_file: Path | None = None
    langfuse_environment: str = "development"
    langfuse_release: str | None = None

    outcome_generation_enabled: bool = False
    litellm_base_url: AnyUrl | None = None
    litellm_api_key_file: Path | None = None
    litellm_request_timeout_seconds: PositiveInt = Field(default=120)
    outcome_transcript_chunk_bytes: PositiveInt = Field(default=196_608)
    outcome_temporal_payload_bytes: PositiveInt = Field(default=262_144)
    outcome_transcript_max_bytes: PositiveInt = Field(default=8_388_608)
    prompt_optimization_enabled: bool = False

    share_workspace_audience_enabled: bool = False
    share_team_audience_enabled: bool = False
    share_public_links_enabled: bool = False
    share_public_links_abuse_gate_approved: bool = False
    share_external_invitations_enabled: bool = False
    share_invitation_ttl_seconds: PositiveInt = Field(default=604_800)

    processing_enabled: bool = False
    processing_poll_interval_seconds: PositiveInt = Field(default=5)
    processing_max_poll_attempts: PositiveInt = Field(default=120)
    processing_max_submit_audio_bytes: PositiveInt = Field(
        default=536_870_912,
        validation_alias=AliasChoices(
            "TWOBRAIN_PROCESSING_MAX_SUBMIT_AUDIO_BYTES",
            "TWOBRAIN_PROCESSING_MAX_IN_MEMORY_AUDIO_BYTES",
        ),
    )
    temporal_address: str | None = None
    temporal_namespace: str = "default"
    temporal_task_queue: str = "twobrain-rec-processing"

    playback_normalization_enabled: bool = False
    playback_normalization_automatic_dispatch_enabled: bool = True
    playback_normalization_task_queue: str = "twobrain-rec-playback-normalization"
    playback_normalization_work_directory: Path = Path(
        "/var/lib/twobrain-rec/playback-normalization"
    )
    playback_normalization_probe_timeout_seconds: PositiveInt = Field(default=60)
    playback_normalization_activity_timeout_seconds: PositiveInt = Field(default=21_600)
    playback_normalization_workflow_timeout_seconds: PositiveInt = Field(default=43_200)
    playback_normalization_heartbeat_seconds: PositiveInt = Field(default=30)
    playback_normalization_reconcile_interval_seconds: PositiveInt = Field(default=60)
    playback_normalization_work_budget_bytes: PositiveInt = Field(default=6_442_450_944)
    playback_normalization_output_max_bytes: PositiveInt = Field(default=134_217_728)
    playback_normalization_work_reserve_bytes: PositiveInt = Field(default=268_435_456)
    playback_normalization_probe_stdout_max_bytes: PositiveInt = Field(default=262_144)
    playback_normalization_process_stderr_max_bytes: PositiveInt = Field(default=1_048_576)
    playback_normalization_max_streams: PositiveInt = Field(default=16)
    playback_normalization_max_audio_streams: PositiveInt = Field(default=8)
    playback_normalization_worker_concurrency: PositiveInt = Field(default=1)
    playback_normalization_workspace_page_size: PositiveInt = Field(default=50)
    playback_normalization_inventory_page_size: PositiveInt = Field(default=100)
    playback_normalization_dispatch_batch_size: PositiveInt = Field(default=25)
    playback_normalization_ffmpeg_path: Path = Path("/usr/bin/ffmpeg")
    playback_normalization_ffprobe_path: Path = Path("/usr/bin/ffprobe")

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
        "litellm_base_url",
        "auth_base_url",
        "web_login_workspace_id",
        "postal_host_header",
        "credential_encryption_key_file",
        "web_csrf_secret_file",
        "support_incident_github_token_file",
        "langfuse_public_key_file",
        "langfuse_secret_key_file",
        "langfuse_release",
        "litellm_api_key_file",
        "prompt_optimization_database_url",
        "prompt_optimization_postgres_password_file",
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

    @field_validator("database_url")
    @classmethod
    def database_url_requires_postgresql_asyncpg(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("database_url must use PostgreSQL with the asyncpg driver")
        return value

    @field_validator("prompt_optimization_database_url")
    @classmethod
    def prompt_optimization_database_url_requires_postgresql_asyncpg(
        cls, value: str | None
    ) -> str | None:
        if value is not None and not value.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "prompt_optimization_database_url must use PostgreSQL with the asyncpg driver"
            )
        if value is not None:
            try:
                username = unquote(urlsplit(value).username or "")
            except ValueError as exc:
                raise ValueError("prompt_optimization_database_url is invalid") from exc
            if username != "twobrain_rec_maintenance":
                raise ValueError(
                    "prompt_optimization_database_url must use the twobrain_rec_maintenance role"
                )
        return value

    @field_validator("public_analytics_validation_mode")
    @classmethod
    def validate_public_analytics_validation_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"disabled", "render_only", "provider_smoke"}:
            raise ValueError(
                "public_analytics_validation_mode must be disabled, render_only, or provider_smoke"
            )
        return normalized

    @field_validator("product_analytics_validation_mode")
    @classmethod
    def validate_product_analytics_validation_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"disabled", "render_only", "provider_smoke", "live_safe"}:
            raise ValueError(
                "product_analytics_validation_mode must be disabled, render_only, provider_smoke, or live_safe"
            )
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

    @field_validator("product_analytics_rollback_mode")
    @classmethod
    def validate_product_analytics_rollback_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {
            "none",
            "posthog_delivery_disabled",
            "posthog_autocapture_disabled",
            "yandex_disabled",
            "all_disabled",
        }:
            raise ValueError(
                "product_analytics_rollback_mode must be none, posthog_delivery_disabled, "
                "posthog_autocapture_disabled, yandex_disabled, or all_disabled"
            )
        return normalized

    @field_validator("product_analytics_retention_min_days")
    @classmethod
    def validate_product_analytics_retention_min_days(cls, value: int) -> int:
        if value < 90:
            raise ValueError("product_analytics_retention_min_days must be at least 90")
        return value

    @model_validator(mode="after")
    def validate_playback_normalization_safety(self) -> "Settings":
        if not self.playback_normalization_enabled:
            return self
        if not self.playback_normalization_task_queue.strip():
            raise ValueError("playback normalization task queue must be explicit")
        if self.playback_normalization_task_queue == self.temporal_task_queue:
            raise ValueError("playback normalization task queue must be isolated from processing")
        if self.playback_normalization_worker_concurrency != 1:
            raise ValueError("playback normalization worker concurrency must be exactly 1")
        if self.playback_normalization_workspace_page_size != 50:
            raise ValueError("playback normalization workspace page must remain exactly 50")
        if self.playback_normalization_inventory_page_size != 100:
            raise ValueError("playback normalization inventory page must remain exactly 100")
        if self.playback_normalization_dispatch_batch_size != 25:
            raise ValueError("playback normalization dispatch batch must remain exactly 25")
        if self.playback_normalization_max_streams != 16:
            raise ValueError("playback normalization stream limit must remain exactly 16")
        if self.playback_normalization_max_audio_streams != 8:
            raise ValueError("playback normalization audio stream limit must remain exactly 8")
        if self.playback_normalization_probe_stdout_max_bytes != 262_144:
            raise ValueError("playback normalization probe stdout cap must remain exactly 256 KiB")
        if self.playback_normalization_process_stderr_max_bytes != 1_048_576:
            raise ValueError("playback normalization process stderr cap must remain exactly 1 MiB")
        if self.playback_normalization_output_max_bytes != 134_217_728:
            raise ValueError("playback normalization output cap must remain exactly 128 MiB")
        required_work_budget = (
            self.max_package_bytes
            + self.playback_normalization_output_max_bytes
            + self.playback_normalization_work_reserve_bytes
        )
        if self.playback_normalization_work_budget_bytes < required_work_budget:
            raise ValueError(
                "playback normalization work budget is below accepted package plus reserves"
            )
        if (
            self.playback_normalization_probe_timeout_seconds
            >= self.playback_normalization_activity_timeout_seconds
            or self.playback_normalization_activity_timeout_seconds
            > self.playback_normalization_workflow_timeout_seconds
        ):
            raise ValueError("playback normalization timeout ordering is unsafe")
        if (
            self.playback_normalization_heartbeat_seconds
            >= self.playback_normalization_reconcile_interval_seconds
        ):
            raise ValueError("playback normalization heartbeat must be shorter than reconciliation")
        if self.env.lower() == "production":
            if not self.temporal_address:
                raise ValueError("production playback normalization requires temporal_address")
            if not self.playback_normalization_work_directory.is_absolute():
                raise ValueError(
                    "production playback normalization work directory must be absolute"
                )
            if not self.playback_normalization_ffmpeg_path.is_absolute():
                raise ValueError("production playback normalization ffmpeg path must be absolute")
            if not self.playback_normalization_ffprobe_path.is_absolute():
                raise ValueError("production playback normalization ffprobe path must be absolute")
        return self

    @model_validator(mode="after")
    def validate_outcome_generation_safety(self) -> "Settings":
        if self.outcome_transcript_chunk_bytes != 196_608:
            raise ValueError("outcome transcript chunks must remain exactly 192 KiB")
        if self.outcome_temporal_payload_bytes != 262_144:
            raise ValueError("outcome Temporal payload ceiling must remain exactly 256 KiB")
        if self.outcome_transcript_max_bytes != 8_388_608:
            raise ValueError("outcome transcript snapshot ceiling must remain exactly 8 MiB")
        if self.outcome_transcript_chunk_bytes >= self.outcome_temporal_payload_bytes:
            raise ValueError("outcome transcript chunk must remain below serialized payload ceiling")
        if not (self.outcome_generation_enabled or self.prompt_optimization_enabled):
            return self
        capability = (
            "outcome generation"
            if self.outcome_generation_enabled
            else "prompt optimization"
        )
        if self.temporal_address is None:
            raise ValueError(f"{capability} requires temporal_address")
        if self.litellm_base_url is None or self.litellm_api_key_file is None:
            raise ValueError(f"{capability} requires the LiteLLM URL and API key file")
        if self.litellm_base_url.scheme != "https":
            raise ValueError(f"{capability} requires an HTTPS LiteLLM URL")
        if any(
            (
                self.litellm_base_url.username,
                self.litellm_base_url.password,
                self.litellm_base_url.query,
                self.litellm_base_url.fragment,
            )
        ):
            raise ValueError(f"{capability} requires a credential-free LiteLLM base URL")
        if self.langfuse_base_url is None:
            raise ValueError(f"{capability} requires langfuse_base_url")
        if self.langfuse_public_key_file is None or self.langfuse_secret_key_file is None:
            raise ValueError(
                f"{capability} requires Langfuse public and secret key files"
            )
        if not self.langfuse_environment.strip():
            raise ValueError(f"{capability} requires a Langfuse environment")
        if self.prompt_optimization_enabled and (
            self.prompt_optimization_database_url is None
            or self.prompt_optimization_postgres_password_file is None
        ):
            raise ValueError(
                "prompt optimization requires the maintenance database URL and password file"
            )
        return self

    @model_validator(mode="after")
    def validate_recording_sharing_safety(self) -> "Settings":
        if self.share_team_audience_enabled:
            raise ValueError(
                "team sharing requires a canonical workspace team directory"
            )
        if self.share_public_links_enabled and self.public_base_url is None:
            raise ValueError("public meeting links require public_base_url")
        if (
            self.share_public_links_enabled
            and not self.share_public_links_abuse_gate_approved
        ):
            raise ValueError(
                "public meeting links require the shared ingress abuse gate"
            )
        if not self.share_external_invitations_enabled:
            return self
        if self.temporal_address is None:
            raise ValueError("external meeting invitations require temporal_address")
        if not self.email_login_delivery_enabled:
            raise ValueError("external meeting invitations require email delivery")
        if self.credential_encryption_key_file is None:
            raise ValueError("external meeting invitations require credential encryption key")
        if self.public_base_url is None:
            raise ValueError("external meeting invitations require public_base_url")
        return self

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.env.lower() != "production":
            return self
        if self.public_analytics_enabled and self.public_analytics_yandex_metrica_id is None:
            raise ValueError(
                "production public analytics requires public_analytics_yandex_metrica_id"
            )
        if self.public_analytics_yandex_metrica_id is not None:
            counter_id = self.public_analytics_yandex_metrica_id.strip()
            lowered_counter_id = counter_id.lower()
            placeholder_markers = (
                "test",
                "replace",
                "changeme",
                "google",
                "gtm",
                "ga4",
                "measurement",
            )
            if not counter_id.isdigit() or any(
                marker in lowered_counter_id for marker in placeholder_markers
            ):
                raise ValueError(
                    "production public_analytics_yandex_metrica_id must be a real numeric Yandex counter ID"
                )
        if self.product_analytics_retention_min_days < 90:
            raise ValueError("production product analytics retention must be at least 90 days")
        if self.product_analytics_enabled and self.product_analytics_validation_mode == "disabled":
            raise ValueError("production product analytics requires a non-disabled validation mode")
        if self.product_analytics_enabled and self.product_analytics_provider_mode == "disabled":
            raise ValueError("production product analytics requires an explicit provider mode")
        if (
            self.product_analytics_validation_mode == "live_safe"
            and not self.product_analytics_live_provider_delivery_allowed()
        ):
            raise ValueError(
                "live-safe product analytics provider delivery requires legal/privacy/security/QA/disclosure/"
                "dashboard/provider-smoke/rollback approval gates"
            )
        if self.product_analytics_posthog_enabled:
            if self.product_analytics_posthog_host is None:
                raise ValueError(
                    "production PostHog product analytics requires product_analytics_posthog_host"
                )
            if self.product_analytics_posthog_project_key_file is None:
                raise ValueError(
                    "production PostHog product analytics requires product_analytics_posthog_project_key_file"
                )
            if (
                self.product_analytics_posthog_autocapture_enabled
                and not self.product_analytics_posthog_credential_suppression_enabled
            ):
                raise ValueError("production PostHog autocapture requires credential suppression")
        if (
            self.product_analytics_posthog_desktop_direct_enabled
            and not self.product_analytics_direct_desktop_egress_enabled
        ):
            raise ValueError("PostHog desktop-direct route requires direct desktop egress gate")
        if (
            self.product_analytics_yandex_all_pages_enabled
            or self.product_analytics_yandex_offline_enabled
        ):
            if self.product_analytics_yandex_counter_id is None:
                raise ValueError(
                    "production Yandex product analytics requires product_analytics_yandex_counter_id"
                )
            yandex_counter_id = self.product_analytics_yandex_counter_id.strip()
            lowered_yandex_counter_id = yandex_counter_id.lower()
            if not yandex_counter_id.isdigit() or any(
                marker in lowered_yandex_counter_id
                for marker in ("test", "replace", "changeme", "google", "gtm")
            ):
                raise ValueError(
                    "production product_analytics_yandex_counter_id must be a real numeric Yandex counter ID"
                )
        if self.product_analytics_yandex_offline_enabled and self.product_analytics_yandex_oauth_token_file is None:
            raise ValueError("production Yandex offline upload requires product_analytics_yandex_oauth_token_file")
        if self.product_analytics_direct_desktop_egress_enabled and not (
            self.product_analytics_direct_desktop_egress_approved
            and self.product_analytics_live_provider_delivery_allowed()
        ):
            raise ValueError(
                "direct desktop product analytics egress requires legal/security/QA/provider approval"
            )
        required_secret_files = {
            "postgres_password_file": self.postgres_password_file,
            "prompt_optimization_postgres_password_file": self.prompt_optimization_postgres_password_file,
            "minio_access_key_file": self.minio_access_key_file,
            "minio_secret_key_file": self.minio_secret_key_file,
            "smoke_credential_file": self.smoke_credential_file,
            "mediascribe_api_key_file": self.mediascribe_api_key_file,
            "credential_encryption_key_file": self.credential_encryption_key_file,
            "web_csrf_secret_file": (
                self.web_csrf_secret_file if self.web_runtime_enabled else None
            ),
            "support_incident_github_token_file": self.support_incident_github_token_file,
            "product_analytics_posthog_project_key_file": self.product_analytics_posthog_project_key_file,
            "product_analytics_yandex_oauth_token_file": self.product_analytics_yandex_oauth_token_file,
            "langfuse_public_key_file": self.langfuse_public_key_file,
            "langfuse_secret_key_file": self.langfuse_secret_key_file,
            "litellm_api_key_file": self.litellm_api_key_file,
        }
        for field_name, path in required_secret_files.items():
            if path is None:
                continue
            if not path.is_file():
                raise ValueError(
                    f"production Docker secret file is missing or unreadable: {field_name}"
                )
            try:
                with path.open("r", encoding="utf-8"):
                    pass
            except OSError as exc:
                raise ValueError(
                    f"production Docker secret file is missing or unreadable: {field_name}"
                ) from exc
        if self.outcome_generation_enabled or self.prompt_optimization_enabled:
            ai_secret_files = {
                "langfuse_public_key_file": self.langfuse_public_key_file,
                "langfuse_secret_key_file": self.langfuse_secret_key_file,
                "litellm_api_key_file": self.litellm_api_key_file,
            }
            for field_name, path in ai_secret_files.items():
                if path is None or path.read_text(encoding="utf-8").strip() == "":
                    raise ValueError(
                        f"production AI secret file must be non-empty: {field_name}"
                    )
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
                raise ValueError(
                    "production email login delivery requires web_login_workspace_id "
                    "as an internal bootstrap"
                )
            if self.postal_api_url is None:
                raise ValueError("production email login delivery requires postal_api_url")
            if self.postal_api_key_file is None:
                raise ValueError("production email login delivery requires postal_api_key_file")
            if self.email_login_from_address is None or not _is_valid_email_address(
                self.email_login_from_address
            ):
                raise ValueError(
                    "production email login delivery requires a valid email_login_from_address"
                )
            if not self.postal_api_key_file.is_file():
                raise ValueError(
                    "production Docker secret file is missing or unreadable: postal_api_key_file"
                )
            if self.postal_api_key_file.read_text(encoding="utf-8").strip() == "":
                raise ValueError("production Postal API key file must be non-empty")
        if self.postgres_password_file is not None:
            postgres_password = self.postgres_password_file.read_text(encoding="utf-8").strip()
            self.database_url = self.database_url.replace(
                "__POSTGRES_PASSWORD__", quote(postgres_password, safe="")
            )
        if self.prompt_optimization_postgres_password_file is not None:
            maintenance_password = self.prompt_optimization_postgres_password_file.read_text(
                encoding="utf-8"
            ).strip()
            if self.prompt_optimization_database_url is not None:
                self.prompt_optimization_database_url = self.prompt_optimization_database_url.replace(
                    "__POSTGRES_PASSWORD__", quote(maintenance_password, safe="")
                )
        if self.minio_access_key_file is not None:
            self.minio_access_key = self.minio_access_key_file.read_text(encoding="utf-8").strip()
        if self.minio_secret_key_file is not None:
            self.minio_secret_key = self.minio_secret_key_file.read_text(encoding="utf-8").strip()
        if self.web_runtime_enabled and self.web_csrf_secret_file is not None:
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
                raise ValueError(
                    f"production Docker secret file is missing or unreadable: {field_name}"
                )
            if path.read_text(encoding="utf-8").strip() == "":
                raise ValueError(
                    f"production auth provider secret file must be non-empty: {field_name}"
                )
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
            raise ValueError(
                "production database_url must not point at localhost or wildcard hosts"
            )
        if self.prompt_optimization_database_url is not None:
            prompt_database_host = urlsplit(self.prompt_optimization_database_url).hostname
            if prompt_database_host is None or prompt_database_host in unsafe_hosts:
                raise ValueError(
                    "production prompt_optimization_database_url must not point at localhost or wildcard hosts"
                )
        if self.minio_endpoint.split(":", maxsplit=1)[0] in unsafe_hosts:
            raise ValueError(
                "production minio_endpoint must not point at localhost or wildcard hosts"
            )
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
        if self.web_runtime_enabled and (
            self.web_csrf_secret in dev_secrets or len(self.web_csrf_secret) < 32
        ):
            raise ValueError("production web_csrf_secret must be explicit and non-placeholder")
        root_markers = ("root", "admin")
        if any(marker in self.minio_access_key.lower() for marker in root_markers):
            raise ValueError("production MinIO API access key must not be a root/admin credential")
        if (
            self.smoke_identity_class is not None
            and self.smoke_identity_class != SMOKE_IDENTITY_CLASS
        ):
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
        if any(
            identifier in LOCAL_DEV_SMOKE_IDS for identifier in smoke_ids if identifier is not None
        ):
            raise ValueError(
                "production smoke identity/device must not reuse local development seed identifiers"
            )
        return self

    def product_analytics_live_provider_delivery_allowed(self) -> bool:
        return (
            self.product_analytics_live_provider_delivery_approved
            and self.product_analytics_legal_approved
            and self.product_analytics_privacy_approved
            and self.product_analytics_security_approved
            and self.product_analytics_qa_approved
            and self.product_analytics_disclosure_approved
            and self.product_analytics_dashboard_ready
            and self.product_analytics_provider_smoke_approved
            and self.product_analytics_rollback_approved
            and self.product_analytics_rollback_mode == "none"
        )


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
