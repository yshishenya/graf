from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parents[4]
POSTHOG_COMPOSE_PATH = REPO_ROOT / "infra/posthog/docker-compose.posthog.yml"
POSTHOG_ENV_EXAMPLE_PATH = REPO_ROOT / "infra/posthog/posthog.production.env.example"
CD_REMOTE_PATH = REPO_ROOT / "infra/scripts/cd-remote.sh"


def _posthog_compose() -> dict:
    return yaml.safe_load(POSTHOG_COMPOSE_PATH.read_text(encoding="utf-8"))


def test_posthog_compose_has_separate_project_services_healthchecks_and_resources() -> None:
    compose = _posthog_compose()
    services = compose["services"]
    handoff = compose["x-graf-official-runtime-handoff"]

    assert compose["name"] == "graf-posthog"
    assert handoff["local_file_purpose"] == "metadata_only_handoff_contract_not_full_posthog_runtime"
    assert handoff["production_runtime_source"] == "official_posthog_hobby_generated_compose"
    assert handoff["production_execute"] == "requires_explicit_release_approval"
    assert {
        "web",
        "worker",
        "plugins",
        "ingestion",
        "capture",
        "clickhouse",
        "kafka",
        "object_storage",
        "proxy",
        "redis",
        "postgres",
    } <= set(handoff["required_upstream_components"])
    assert {"posthog-web", "posthog-worker", "posthog-db", "posthog-redis"} <= set(services)
    assert services["posthog-web"]["ports"] == ["127.0.0.1:18082:8000"]
    assert "healthcheck" in services["posthog-web"]
    assert "healthcheck" in services["posthog-db"]
    assert services["posthog-web"]["deploy"]["resources"]["limits"]["memory"] == "4g"
    assert services["posthog-db"]["deploy"]["resources"]["limits"]["memory"] == "2g"
    assert services["posthog-web"]["logging"]["options"]["max-size"] == "10m"
    assert "latest" not in POSTHOG_COMPOSE_PATH.read_text(encoding="utf-8")
    assert "REPLACE_WITH_PINNED_RELEASE_TAG" in services["posthog-web"]["image"]
    assert "REPLACE_WITH_PINNED_RELEASE_TAG" in services["posthog-worker"]["image"]
    assert "posthog-db-data" in compose["volumes"]
    assert "posthog-media" in compose["volumes"]


def test_posthog_compose_uses_secret_files_without_values() -> None:
    compose_text = POSTHOG_COMPOSE_PATH.read_text(encoding="utf-8")
    compose = _posthog_compose()

    assert {"posthog_secret_key", "posthog_db_password"} <= set(compose["secrets"])
    assert "${POSTHOG_RUNTIME_ENV_FILE:-./posthog.production.env.example}" in compose_text
    assert "../secrets/posthog_secret_key" in compose_text
    assert "../secrets/posthog_db_password" in compose_text
    assert "phc_" not in compose_text
    assert "POSTHOG_PROJECT_KEY=" not in compose_text


def test_posthog_env_example_records_retention_resource_thresholds_and_replay_disabled() -> None:
    env = POSTHOG_ENV_EXAMPLE_PATH.read_text(encoding="utf-8")

    assert "DOMAIN=analytics.2brain.pro" in env
    assert "SITE_URL=https://analytics.2brain.pro" in env
    assert "ALLOWED_HOSTS=analytics.2brain.pro" in env
    assert "POSTHOG_APP_TAG=REPLACE_WITH_PINNED_RELEASE_TAG" in env
    assert "POSTHOG_RETENTION_MIN_DAYS=90" in env
    assert "POSTHOG_IMAGE=posthog/posthog:REPLACE_WITH_PINNED_RELEASE_TAG" in env
    assert "POSTHOG_RESOURCE_LIMIT_CPU_WEB=2" in env
    assert "POSTHOG_RESOURCE_LIMIT_MEMORY_WEB=4g" in env
    assert "POSTHOG_SESSION_REPLAY_ENABLED=false" in env
    assert "POSTHOG_EVIDENCE_MODE=metadata_only" in env
    assert "POSTHOG_LIVE_SECRET_VALUES_IN_GIT=false" in env


def test_cd_remote_dry_run_documents_posthog_stack_handoff_without_execution_path() -> None:
    script = CD_REMOTE_PATH.read_text(encoding="utf-8")

    assert "posthog_stack_handoff=dry_run_metadata_only" in script
    assert "posthog_stack_contract=infra/posthog/docker-compose.posthog.yml" in script
    assert "posthog_stack_runtime_source=official_posthog_hobby_generated_compose_required" in script
    assert "posthog_stack_execute=requires_explicit_release_approval" in script
    assert "docker compose -f infra/posthog/docker-compose.posthog.yml up" not in script
