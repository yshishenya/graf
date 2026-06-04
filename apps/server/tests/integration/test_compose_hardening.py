from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parents[4]
COMPOSE_PATH = REPO_ROOT / "infra/docker-compose.yml"
DOCKERFILE_PATH = REPO_ROOT / "infra/server/Dockerfile"
CONSTRAINTS_PATH = REPO_ROOT / "apps/server/constraints.txt"


def _compose() -> dict:
    return yaml.safe_load(COMPOSE_PATH.read_text())


def test_production_compose_api_has_healthcheck_and_localhost_bind_policy() -> None:
    api = _compose()["services"]["rec-api"]

    assert api["ports"] == ["127.0.0.1:8080:8080"]
    assert "healthcheck" in api
    healthcheck = " ".join(api["healthcheck"]["test"])
    assert "/api/v1/health/ready" in healthcheck
    assert "127.0.0.1:8080" in healthcheck


def test_production_compose_sets_log_rotation_and_resource_limits_for_services() -> None:
    compose = _compose()

    for service_name in ["rec-api", "rec-postgres", "rec-minio", "rec-minio-init"]:
        service = compose["services"][service_name]
        assert service["logging"]["driver"] == "json-file"
        assert service["logging"]["options"]["max-size"] == "10m"
        assert service["logging"]["options"]["max-file"] == "5"
        assert service["deploy"]["resources"]["limits"]["memory"]
        assert service["deploy"]["resources"]["limits"]["cpus"]


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


def test_production_compose_uses_required_secret_placeholders_without_dev_defaults() -> None:
    compose_text = COMPOSE_PATH.read_text()
    compose = _compose()
    api_env = compose["services"]["rec-api"]["environment"]

    for variable in [
        "TWOBRAIN_POSTGRES_PASSWORD",
        "TWOBRAIN_MINIO_ROOT_USER",
        "TWOBRAIN_MINIO_ROOT_PASSWORD",
        "TWOBRAIN_MINIO_API_ACCESS_KEY",
        "TWOBRAIN_MINIO_API_SECRET_KEY",
    ]:
        assert f"${{{variable}:?set in deployment environment}}" in compose_text

    assert "localhost" not in api_env["TWOBRAIN_DATABASE_URL"]
    assert api_env["TWOBRAIN_MINIO_ENDPOINT"] == "rec-minio:9000"
    assert "twobrain_rec_dev_secret" not in compose_text
