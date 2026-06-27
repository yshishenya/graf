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
        "auth_ru_local_storage_attested": True,
    }
    values.update(overrides)
    return Settings(**values)


def test_production_config_accepts_non_local_runtime_credentials() -> None:
    settings = _production_settings()

    assert settings.env == "production"


def test_default_upload_part_contract_is_one_gib() -> None:
    assert Settings().max_upload_part_bytes == 1_073_741_824


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


def test_production_accepts_existing_secret_files(tmp_path) -> None:
    secret = tmp_path / "secret"
    secret.write_text("redacted-test-value")

    settings = _production_settings(
        postgres_password_file=secret,
        minio_access_key_file=secret,
        minio_secret_key_file=secret,
        smoke_credential_file=secret,
        calendar_credential_key_file=secret,
    )

    assert settings.postgres_password_file == secret
    assert settings.calendar_credential_key_file == secret


def test_empty_calendar_credential_key_file_is_unset() -> None:
    settings = _production_settings(calendar_credential_key_file="")

    assert settings.calendar_credential_key_file is None


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


def test_production_email_login_delivery_requires_default_browser_workspace(tmp_path) -> None:
    key_file = tmp_path / "postal-key"
    key_file.write_text("postal-api-key")

    with pytest.raises(ValidationError, match="web_login_workspace_id"):
        _production_settings(
            email_login_delivery_enabled=True,
            email_login_from_address="no-reply@rec.2brain.pro",
            postal_api_url="http://postal-web:5000",
            postal_api_key_file=key_file,
        )


def test_empty_web_login_workspace_id_is_unset_when_email_delivery_is_disabled() -> None:
    settings = _production_settings(
        web_login_workspace_id="",
        postal_host_header="",
        email_login_delivery_enabled=False,
    )

    assert settings.web_login_workspace_id is None
    assert settings.postal_host_header is None


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
