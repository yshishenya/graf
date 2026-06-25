import tomllib
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parents[4]
COMPOSE_PATH = REPO_ROOT / "infra/docker-compose.yml"
ENV_TEMPLATE_PATH = REPO_ROOT / "infra/env/rec.production.env.example"
DOCKERFILE_PATH = REPO_ROOT / "infra/server/Dockerfile"
CONSTRAINTS_PATH = REPO_ROOT / "apps/server/constraints.txt"
UV_LOCK_PATH = REPO_ROOT / "apps/server/uv.lock"


def _compose() -> dict:
    return yaml.safe_load(COMPOSE_PATH.read_text())


def _active_env_template_keys() -> set[str]:
    keys: set[str] = set()
    for line in ENV_TEMPLATE_PATH.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        keys.add(stripped.split("=", maxsplit=1)[0])
    return keys


def test_production_compose_api_has_healthcheck_and_localhost_bind_policy() -> None:
    api = _compose()["services"]["rec-api"]

    assert api["ports"] == ["127.0.0.1:18081:8080"]
    assert "healthcheck" in api
    healthcheck = " ".join(api["healthcheck"]["test"])
    assert "/api/v1/health/ready" in healthcheck
    assert "127.0.0.1:8080" in healthcheck


def test_production_compose_sets_log_rotation_and_resource_limits_for_services() -> None:
    compose = _compose()

    for service_name in [
        "rec-api",
        "rec-migrate",
        "rec-postgres",
        "rec-minio",
        "rec-minio-init",
        "rec-temporal",
        "rec-processing-worker",
    ]:
        service = compose["services"][service_name]
        assert service["logging"]["driver"] == "json-file"
        assert service["logging"]["options"]["max-size"] == "10m"
        assert service["logging"]["options"]["max-file"] == "5"
        assert service["deploy"]["resources"]["limits"]["memory"]
        assert service["deploy"]["resources"]["limits"]["cpus"]


def test_production_compose_runs_migrations_before_api_readiness() -> None:
    compose = _compose()
    migrate = compose["services"]["rec-migrate"]
    api = compose["services"]["rec-api"]

    assert migrate["command"] == ["alembic", "upgrade", "head"]
    assert api["depends_on"]["rec-migrate"]["condition"] == "service_completed_successfully"


def test_runtime_image_uses_runtime_dependencies_and_constraints() -> None:
    dockerfile = DOCKERFILE_PATH.read_text()
    constraints = CONSTRAINTS_PATH.read_text()

    assert "constraints.txt" in dockerfile
    assert "pip install --constraint constraints.txt \".\"" in dockerfile
    assert "\".[dev]\"" not in dockerfile
    assert "pytest" not in constraints
    assert "ruff" not in constraints
    assert "fastapi==" in constraints
    assert "sqlalchemy==" in constraints


def test_dev_lint_toolchain_pins_supported_ruff_version() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "apps/server/pyproject.toml").read_text())
    dev_dependencies = pyproject["project"]["optional-dependencies"]["dev"]
    uv_lock = UV_LOCK_PATH.read_text()

    assert "ruff==0.15.15" in dev_dependencies
    assert 'name = "ruff"\nversion = "0.15.15"' in uv_lock


def test_production_compose_uses_required_secret_placeholders_without_dev_defaults() -> None:
    compose_text = COMPOSE_PATH.read_text()
    compose = _compose()
    api_env = compose["services"]["rec-api"]["environment"]

    assert "__POSTGRES_PASSWORD__" in api_env["TWOBRAIN_DATABASE_URL"]
    assert api_env["TWOBRAIN_MINIO_ACCESS_KEY"] == "__DOCKER_SECRET_FILE__"
    assert api_env["TWOBRAIN_MINIO_SECRET_KEY"] == "__DOCKER_SECRET_FILE__"
    assert "localhost" not in api_env["TWOBRAIN_DATABASE_URL"]
    assert api_env["TWOBRAIN_MINIO_ENDPOINT"] == "rec-minio:9000"
    assert "twobrain_rec_dev_secret" not in compose_text
    assert "TWOBRAIN_POSTGRES_PASSWORD:?set in deployment environment" not in compose_text
    assert "TWOBRAIN_MINIO_API_SECRET_KEY:?set in deployment environment" not in compose_text


def test_production_compose_declares_docker_secret_files_for_required_secret_classes() -> None:
    compose = _compose()
    secrets = compose["secrets"]

    for secret_name in [
        "twobrain_postgres_password",
        "twobrain_minio_root_user",
        "twobrain_minio_root_password",
        "twobrain_minio_api_access_key",
        "twobrain_minio_api_secret_key",
        "twobrain_smoke_credential",
    ]:
        assert secret_name in secrets

    api = compose["services"]["rec-api"]
    api_secret_sources = {secret["source"] for secret in api["secrets"]}
    assert {"twobrain_postgres_password", "twobrain_minio_api_access_key", "twobrain_minio_api_secret_key", "twobrain_smoke_credential"} <= api_secret_sources

    postgres = compose["services"]["rec-postgres"]
    assert any(secret["source"] == "twobrain_postgres_password" for secret in postgres["secrets"])


def test_production_env_template_does_not_broadcast_service_specific_secret_files() -> None:
    active_keys = _active_env_template_keys()

    assert active_keys.isdisjoint(
        {
            "TWOBRAIN_MINIO_ROOT_USER_FILE",
            "TWOBRAIN_MINIO_ROOT_PASSWORD_FILE",
            "TWOBRAIN_SMOKE_CREDENTIAL_FILE",
            "TWOBRAIN_MEDIASCRIBE_CREDENTIAL_FILE",
            "TWOBRAIN_MEDIASCRIBE_API_KEY_FILE",
            "TWOBRAIN_LANGFUSE_CREDENTIAL_FILE",
        }
    )


def test_production_temporal_uses_postgres_backend_with_secret_file_wrapper() -> None:
    compose = _compose()
    temporal = compose["services"]["rec-temporal"]
    temporal_env = temporal["environment"]
    entrypoint = "\n".join(temporal["entrypoint"])

    assert temporal_env["DB"] == "postgres12"
    assert temporal_env["DB_PORT"] == "5432"
    assert temporal_env["POSTGRES_SEEDS"] == "rec-postgres"
    assert temporal_env["POSTGRES_USER"] == "twobrain_rec"
    assert temporal_env["DBNAME"] == "temporal"
    assert temporal_env["VISIBILITY_DBNAME"] == "temporal_visibility"
    assert "POSTGRES_PWD" not in temporal_env
    assert temporal["user"] == "root"
    assert 'POSTGRES_PWD="$$(cat /run/secrets/twobrain_postgres_password)"' in entrypoint
    assert "/etc/temporal/entrypoint.sh autosetup" in entrypoint
    assert {"source": "twobrain_postgres_password", "target": "twobrain_postgres_password"} in temporal["secrets"]
    assert temporal["depends_on"]["rec-postgres"]["condition"] == "service_healthy"


def test_production_api_autostarts_processing_and_worker_can_read_processing_secrets() -> None:
    compose = _compose()
    api = compose["services"]["rec-api"]
    worker = compose["services"]["rec-processing-worker"]
    api_env = api["environment"]
    api_secret_sources = {secret["source"] for secret in api["secrets"]}

    assert api_env["TWOBRAIN_PROCESSING_ENABLED"] == "true"
    assert api_env["TWOBRAIN_TEMPORAL_ADDRESS"] == "rec-temporal:7233"
    assert "TWOBRAIN_MEDIASCRIBE_API_KEY_FILE" not in api_env
    assert api["depends_on"]["rec-temporal"]["condition"] == "service_started"
    assert "twobrain_mediascribe_api_key" not in api_secret_sources
    assert worker["user"] == "root"
    assert worker["environment"]["TWOBRAIN_MEDIASCRIBE_API_KEY_FILE"] == "/run/secrets/twobrain_mediascribe_api_key"
    assert {"source": "twobrain_mediascribe_api_key", "target": "twobrain_mediascribe_api_key"} in worker["secrets"]


def test_remote_cd_blocks_static_postgres_pwd_in_compose_config() -> None:
    script = (REPO_ROOT / "infra/scripts/cd-remote.sh").read_text()

    assert "POSTGRES_PWD:" in script
