import pytest
from pydantic import ValidationError

from twobrain_rec_server.config import LOCAL_DEV_SMOKE_IDS, SMOKE_IDENTITY_CLASS, Settings


def _production_settings(**overrides):
    values = {
        "env": "production",
        "database_url": "postgresql+asyncpg://twobrain_rec:secret@rec-postgres:5432/twobrain_rec",
        "minio_endpoint": "rec-minio:9000",
        "minio_access_key": "twobrain_rec_api",
        "minio_secret_key": "prod-api-secret",
        "minio_bucket": "twobrain-rec-ingest",
        "web_csrf_secret": "prod-web-csrf-secret-32-bytes-minimum",
        "auth_ru_local_storage_attested": True,
        "playback_normalization_enabled": True,
        "temporal_address": "rec-temporal:7233",
    }
    values.update(overrides)
    return Settings(**values)


def test_production_config_accepts_non_local_runtime_credentials() -> None:
    settings = _production_settings()

    assert settings.env == "production"


def test_non_web_production_runtime_does_not_require_web_csrf_secret() -> None:
    settings = _production_settings(
        web_runtime_enabled=False,
        web_csrf_secret="twobrain_rec_dev_web_csrf_secret",
    )

    assert settings.web_runtime_enabled is False


def test_web_production_runtime_still_rejects_default_csrf_secret() -> None:
    with pytest.raises(ValidationError, match="web_csrf_secret"):
        _production_settings(web_csrf_secret="twobrain_rec_dev_web_csrf_secret")


def test_default_upload_part_contract_is_one_gib() -> None:
    assert Settings().max_upload_part_bytes == 1_073_741_824


def test_database_url_rejects_non_postgresql_async_driver() -> None:
    with pytest.raises(ValidationError, match="PostgreSQL"):
        Settings(database_url="sqli" + "te+aio" + "sqli" + "te:////tmp/rec.db")


def test_database_url_accepts_postgresql_async_driver() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://twobrain_rec:secret@127.0.0.1:54329/twobrain_rec_test_x"
    )

    assert settings.database_url.startswith("postgresql+asyncpg://")


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({}, "temporal_address"),
        ({"temporal_address": "temporal:7233"}, "LiteLLM"),
    ],
)
def test_prompt_optimization_requires_ai_runtime_independently_of_outcomes(
    overrides: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        Settings(prompt_optimization_enabled=True, **overrides)


def test_prompt_optimization_accepts_complete_ai_runtime_without_outcomes(tmp_path) -> None:
    lite_key = tmp_path / "litellm-key"
    public_key = tmp_path / "langfuse-public-key"
    secret_key = tmp_path / "langfuse-secret-key"
    for path in (lite_key, public_key, secret_key):
        path.write_text("test", encoding="utf-8")

    settings = Settings(
        prompt_optimization_enabled=True,
        outcome_generation_enabled=False,
        temporal_address="temporal:7233",
        litellm_base_url="https://litellm.example.test",
        litellm_api_key_file=lite_key,
        langfuse_base_url="https://langfuse.example.test",
        langfuse_public_key_file=public_key,
        langfuse_secret_key_file=secret_key,
    )

    assert settings.prompt_optimization_enabled is True
    assert settings.outcome_generation_enabled is False


@pytest.mark.parametrize(
    "litellm_base_url",
    (
        "http://litellm.example.test",
        "https://user:password@litellm.example.test",
        "https://litellm.example.test?token=value",
        "https://litellm.example.test#fragment",
    ),
)
def test_ai_runtime_rejects_unsafe_litellm_base_url(tmp_path, litellm_base_url) -> None:
    lite_key = tmp_path / "litellm-key"
    public_key = tmp_path / "langfuse-public-key"
    secret_key = tmp_path / "langfuse-secret-key"
    for path in (lite_key, public_key, secret_key):
        path.write_text("test", encoding="utf-8")

    with pytest.raises(ValidationError, match="LiteLLM"):
        Settings(
            outcome_generation_enabled=True,
            temporal_address="temporal:7233",
            litellm_base_url=litellm_base_url,
            litellm_api_key_file=lite_key,
            langfuse_base_url="https://langfuse.example.test",
            langfuse_public_key_file=public_key,
            langfuse_secret_key_file=secret_key,
        )


def test_production_ai_runtime_rejects_empty_secret_files(tmp_path) -> None:
    lite_key = tmp_path / "litellm-key"
    public_key = tmp_path / "langfuse-public-key"
    secret_key = tmp_path / "langfuse-secret-key"
    for path in (lite_key, public_key, secret_key):
        path.write_text("test", encoding="utf-8")
    lite_key.write_text("", encoding="utf-8")

    with pytest.raises(ValidationError, match="litellm_api_key_file"):
        _production_settings(
            outcome_generation_enabled=True,
            litellm_base_url="https://litellm.example.test",
            litellm_api_key_file=lite_key,
            langfuse_base_url="https://cloud.langfuse.com",
            langfuse_public_key_file=public_key,
            langfuse_secret_key_file=secret_key,
        )


def test_playback_normalization_defaults_are_bounded_and_isolated() -> None:
    settings = Settings(playback_normalization_enabled=True)

    assert settings.playback_normalization_task_queue != settings.temporal_task_queue
    assert settings.playback_normalization_worker_concurrency == 1
    assert settings.playback_normalization_output_max_bytes == 128 * 1024 * 1024
    assert settings.playback_normalization_work_budget_bytes >= (
        settings.max_package_bytes
        + settings.playback_normalization_output_max_bytes
        + settings.playback_normalization_work_reserve_bytes
    )


def test_playback_normalization_rejects_shared_queue_and_unsafe_budget() -> None:
    with pytest.raises(ValidationError, match="task queue"):
        Settings(
            playback_normalization_enabled=True,
            playback_normalization_task_queue="twobrain-rec-processing",
        )
    with pytest.raises(ValidationError, match="work budget"):
        Settings(
            playback_normalization_enabled=True,
            playback_normalization_work_budget_bytes=1024,
        )


@pytest.mark.parametrize(
    ("field_name", "unsafe_value", "message"),
    [
        ("playback_normalization_max_streams", 17, "stream limit"),
        ("playback_normalization_max_audio_streams", 9, "audio stream limit"),
        ("playback_normalization_probe_stdout_max_bytes", 262_145, "probe stdout cap"),
        ("playback_normalization_process_stderr_max_bytes", 1_048_577, "stderr cap"),
    ],
)
def test_playback_normalization_rejects_runtime_cap_drift(
    field_name: str,
    unsafe_value: int,
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        Settings(playback_normalization_enabled=True, **{field_name: unsafe_value})


def test_production_allows_playback_dispatch_to_remain_disabled_during_staged_rollout() -> None:
    settings = _production_settings(
        playback_normalization_enabled=False,
        playback_normalization_automatic_dispatch_enabled=False,
    )

    assert settings.playback_normalization_enabled is False
    assert settings.playback_normalization_automatic_dispatch_enabled is False


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


def test_production_rejects_default_dev_web_csrf_secret() -> None:
    with pytest.raises(ValidationError, match="web_csrf_secret"):
        _production_settings(web_csrf_secret="twobrain_rec_dev_web_csrf_secret")


def test_production_reads_web_csrf_secret_from_file(tmp_path) -> None:
    secret = tmp_path / "web-csrf-secret"
    secret.write_text("prod-web-csrf-secret-from-file-32-bytes")

    settings = _production_settings(
        web_csrf_secret="will-be-replaced-by-file",
        web_csrf_secret_file=secret,
    )

    assert settings.web_csrf_secret == "prod-web-csrf-secret-from-file-32-bytes"


def test_production_rejects_root_minio_api_credentials() -> None:
    with pytest.raises(ValidationError, match="root/admin"):
        _production_settings(minio_access_key="twobrain_root_api")


def test_production_accepts_existing_secret_files(tmp_path) -> None:
    secret = tmp_path / "secret"
    secret.write_text("redacted-test-value")

    settings = _production_settings(
        postgres_password_file=secret,
        minio_access_key_file=secret,
        minio_secret_key_file=secret,
        smoke_credential_file=secret,
        credential_encryption_key_file=secret,
    )

    assert settings.postgres_password_file == secret
    assert settings.credential_encryption_key_file == secret


def test_empty_credential_encryption_key_file_is_unset() -> None:
    settings = _production_settings(credential_encryption_key_file="")

    assert settings.credential_encryption_key_file is None


def test_graf_credential_encryption_key_env_is_supported(monkeypatch, tmp_path) -> None:
    secret = tmp_path / "graf-credential-encryption-key"
    secret.write_text("redacted-test-value")
    monkeypatch.setenv("GRAF_CREDENTIAL_ENCRYPTION_KEY_FILE", str(secret))

    settings = _production_settings()

    assert settings.credential_encryption_key_file == secret


def test_legacy_calendar_credential_key_env_is_supported(monkeypatch, tmp_path) -> None:
    secret = tmp_path / "legacy-calendar-credential-key"
    secret.write_text("redacted-test-value")
    monkeypatch.setenv("TWOBRAIN_CALENDAR_CREDENTIAL_KEY_FILE", str(secret))

    settings = _production_settings()

    assert settings.credential_encryption_key_file == secret


def test_empty_support_incident_github_token_file_is_unset() -> None:
    settings = _production_settings(support_incident_github_token_file="")

    assert settings.support_incident_github_token_file is None


def test_production_rejects_wrong_support_incident_repo() -> None:
    with pytest.raises(ValidationError, match="yshishenya/crisp"):
        _production_settings(support_incident_github_repo="public-triage")


def test_production_rejects_empty_support_incident_github_token_file(tmp_path) -> None:
    token_file = tmp_path / "support-token"
    token_file.write_text("")

    with pytest.raises(ValidationError, match="GitHub token file"):
        _production_settings(support_incident_github_token_file=token_file)


def test_production_rejects_empty_yandex_client_secret_file(tmp_path) -> None:
    secret_file = tmp_path / "yandex-client-secret"
    secret_file.write_text("")

    with pytest.raises(ValidationError, match="yandex_client_secret_file"):
        _production_settings(yandex_client_secret_file=secret_file)


def test_production_rejects_empty_vk_client_secret_file(tmp_path) -> None:
    secret_file = tmp_path / "vk-client-secret"
    secret_file.write_text("")

    with pytest.raises(ValidationError, match="vk_client_secret_file"):
        _production_settings(vk_client_secret_file=secret_file)


def test_production_rejects_missing_vk_client_secret_file(tmp_path) -> None:
    missing = tmp_path / "missing-vk-client-secret"

    with pytest.raises(ValidationError, match="vk_client_secret_file"):
        _production_settings(vk_client_secret_file=missing)


def test_production_reads_runtime_credentials_from_secret_files(tmp_path) -> None:
    postgres_password = tmp_path / "postgres-password"
    minio_access_key = tmp_path / "minio-access-key"
    minio_secret_key = tmp_path / "minio-secret-key"
    smoke_credential = tmp_path / "smoke-credential"
    postgres_password.write_text("prod pg password")
    minio_access_key.write_text("twobrain_rec_api")
    minio_secret_key.write_text("prod-api-secret")
    smoke_credential.write_text("smoke")

    settings = _production_settings(
        database_url="postgresql+asyncpg://twobrain_rec:__POSTGRES_PASSWORD__@rec-postgres:5432/twobrain_rec",
        minio_access_key="__DOCKER_SECRET_FILE__",
        minio_secret_key="__DOCKER_SECRET_FILE__",
        postgres_password_file=postgres_password,
        minio_access_key_file=minio_access_key,
        minio_secret_key_file=minio_secret_key,
        smoke_credential_file=smoke_credential,
    )

    assert "prod%20pg%20password" in settings.database_url
    assert settings.minio_access_key == "twobrain_rec_api"
    assert settings.minio_secret_key == "prod-api-secret"


def test_production_rejects_missing_secret_files(tmp_path) -> None:
    missing = tmp_path / "missing-secret"

    with pytest.raises(ValidationError, match="minio_secret_key_file"):
        _production_settings(minio_secret_key_file=missing)


def test_production_missing_secret_error_names_field(tmp_path) -> None:
    missing = tmp_path / "missing-smoke-secret"

    with pytest.raises(ValidationError, match="smoke_credential_file"):
        _production_settings(smoke_credential_file=missing)


def test_production_email_login_delivery_requires_postal_settings(tmp_path) -> None:
    key_file = tmp_path / "postal-key"
    key_file.write_text("postal-api-key")

    with pytest.raises(ValidationError, match="postal_api_url"):
        _production_settings(
            email_login_delivery_enabled=True,
            web_login_workspace_id="20000000-0000-0000-0000-000000000010",
            email_login_from_address="no-reply@rec.2brain.pro",
            postal_api_key_file=key_file,
        )
    with pytest.raises(ValidationError, match="email_login_from_address"):
        _production_settings(
            email_login_delivery_enabled=True,
            web_login_workspace_id="20000000-0000-0000-0000-000000000010",
            postal_api_url="http://postal-web:5000",
            postal_api_key_file=key_file,
        )


def test_production_email_login_delivery_requires_internal_auth_bootstrap(tmp_path) -> None:
    key_file = tmp_path / "postal-key"
    key_file.write_text("postal-api-key")

    with pytest.raises(ValidationError, match="web_login_workspace_id"):
        _production_settings(
            email_login_delivery_enabled=True,
            email_login_from_address="no-reply@rec.2brain.pro",
            postal_api_url="http://postal-web:5000",
            postal_api_key_file=key_file,
        )


def test_web_login_workspace_is_documented_as_an_internal_bootstrap_only() -> None:
    field = Settings.model_fields["web_login_workspace_id"]

    assert field.description is not None
    assert "Internal bootstrap workspace" in field.description
    assert "never a public enrollment destination" in field.description


def test_empty_web_login_workspace_id_is_unset_when_email_delivery_is_disabled() -> None:
    settings = _production_settings(
        web_login_workspace_id="",
        postal_host_header="",
        email_login_delivery_enabled=False,
    )

    assert settings.web_login_workspace_id is None
    assert settings.postal_host_header is None


def test_empty_optional_url_is_unset_when_feature_is_disabled() -> None:
    settings = _production_settings(
        postal_api_url="",
        email_login_delivery_enabled=False,
    )

    assert settings.postal_api_url is None


def test_production_email_login_delivery_reads_non_empty_postal_secret(tmp_path) -> None:
    key_file = tmp_path / "postal-key"
    key_file.write_text("postal-api-key")

    settings = _production_settings(
        email_login_delivery_enabled=True,
        web_login_workspace_id="20000000-0000-0000-0000-000000000010",
        email_login_from_address="no-reply@rec.2brain.pro",
        postal_api_url="http://postal-web:5000",
        postal_api_key_file=key_file,
    )

    assert settings.postal_api_key_file == key_file


def test_production_email_login_delivery_rejects_empty_postal_secret(tmp_path) -> None:
    key_file = tmp_path / "postal-key"
    key_file.write_text("")

    with pytest.raises(ValidationError, match="Postal API key file"):
        _production_settings(
            email_login_delivery_enabled=True,
            web_login_workspace_id="20000000-0000-0000-0000-000000000010",
            email_login_from_address="no-reply@rec.2brain.pro",
            postal_api_url="http://postal-web:5000",
            postal_api_key_file=key_file,
        )


def test_production_rejects_non_internal_smoke_identity_class() -> None:
    with pytest.raises(ValidationError, match="internal_smoke"):
        _production_settings(smoke_identity_class="local_dev")


def test_production_rejects_missing_auth_ru_local_storage_attestation() -> None:
    with pytest.raises(ValidationError, match="RU-local storage attestation"):
        _production_settings(auth_ru_local_storage_attested=False)


def test_production_rejects_non_ru_auth_storage_region() -> None:
    with pytest.raises(ValidationError, match="auth storage region"):
        _production_settings(auth_storage_region_tag="eu")


def test_production_rejects_local_dev_smoke_ids() -> None:
    local_user_id = next(iter(LOCAL_DEV_SMOKE_IDS))

    with pytest.raises(ValidationError, match="local development seed"):
        _production_settings(
            smoke_identity_class=SMOKE_IDENTITY_CLASS,
            smoke_user_id=local_user_id,
        )
