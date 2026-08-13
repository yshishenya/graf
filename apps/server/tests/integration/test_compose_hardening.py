import json
import shlex
import tomllib
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parents[4]
COMPOSE_PATH = REPO_ROOT / "infra/docker-compose.yml"
DEV_COMPOSE_PATH = REPO_ROOT / "infra/docker-compose.dev.yml"
ENV_TEMPLATE_PATH = REPO_ROOT / "infra/env/rec.production.env.example"
DOCKERFILE_PATH = REPO_ROOT / "infra/server/Dockerfile"
CONSTRAINTS_PATH = REPO_ROOT / "apps/server/constraints.txt"
UV_LOCK_PATH = REPO_ROOT / "apps/server/uv.lock"


class _ComposeLoader(yaml.SafeLoader):
    pass


def _construct_compose_override(loader, node):
    return loader.construct_sequence(node)


_ComposeLoader.add_constructor("!override", _construct_compose_override)


def _compose() -> dict:
    return yaml.safe_load(COMPOSE_PATH.read_text())


def _dev_compose() -> dict:
    return yaml.load(DEV_COMPOSE_PATH.read_text(), Loader=_ComposeLoader)


def _active_env_template_keys() -> set[str]:
    keys: set[str] = set()
    for line in ENV_TEMPLATE_PATH.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        keys.add(stripped.split("=", maxsplit=1)[0])
    return keys


def _media_minio_policy(compose: dict) -> dict:
    script = compose["services"]["rec-minio-init"]["entrypoint"][-1]
    lines = script.splitlines()
    marker = "cat >/tmp/rec-media-policy.json <<'JSON'"
    marker_index = next(index for index, line in enumerate(lines) if line.strip() == marker)
    return json.loads(lines[marker_index + 1].strip())


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
        "rec-db-runtime-bootstrap",
        "rec-maintenance",
        "rec-reprocess-maintenance",
        "rec-migrate",
        "rec-postgres",
        "rec-minio",
        "rec-minio-init",
        "rec-temporal",
        "rec-processing-worker",
        "rec-prompt-optimization-worker",
        "rec-media-worker",
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
    bootstrap = compose["services"]["rec-db-runtime-bootstrap"]
    api = compose["services"]["rec-api"]

    assert migrate["command"] == ["alembic", "upgrade", "head"]
    assert bootstrap["depends_on"]["rec-migrate"]["condition"] == ("service_completed_successfully")
    assert api["depends_on"]["rec-db-runtime-bootstrap"]["condition"] == (
        "service_completed_successfully"
    )


def test_runtime_image_uses_runtime_dependencies_and_constraints() -> None:
    dockerfile = DOCKERFILE_PATH.read_text()
    constraints = CONSTRAINTS_PATH.read_text()

    assert "constraints.txt" in dockerfile
    assert 'pip install --constraint constraints.txt ".[evaluation]"' in dockerfile
    assert '".[dev]"' not in dockerfile
    assert "pytest" not in constraints
    assert "ruff" not in constraints
    assert "fastapi==" in constraints
    assert "sqlalchemy==" in constraints


def test_runtime_image_disables_uvicorn_access_logs() -> None:
    dockerfile = DOCKERFILE_PATH.read_text()

    assert '"--no-access-log"' in dockerfile


def test_runtime_image_copy_sources_exist_in_repository() -> None:
    missing_sources: list[str] = []

    for raw_line in DOCKERFILE_PATH.read_text().splitlines():
        line = raw_line.strip()
        if not line.startswith("COPY "):
            continue

        parts = shlex.split(line)
        operands = parts[1:]
        while operands and operands[0].startswith("--"):
            operands = operands[1:]

        for source in operands[:-1]:
            if not source.startswith(".") and source.startswith("/"):
                continue
            if not (REPO_ROOT / source).exists():
                missing_sources.append(source)

    assert missing_sources == []


def test_dev_lint_toolchain_pins_supported_ruff_version() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "apps/server/pyproject.toml").read_text())
    dev_dependencies = pyproject["project"]["optional-dependencies"]["dev"]
    uv_lock = UV_LOCK_PATH.read_text()

    assert "ruff==0.15.20" in dev_dependencies
    assert 'name = "ruff"\nversion = "0.15.20"' in uv_lock


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
        "twobrain_postgres_app_password",
        "twobrain_postgres_maintenance_password",
        "twobrain_postgres_media_password",
        "twobrain_minio_root_user",
        "twobrain_minio_root_password",
        "twobrain_minio_api_access_key",
        "twobrain_minio_api_secret_key",
        "twobrain_minio_media_access_key",
        "twobrain_minio_media_secret_key",
        "twobrain_smoke_credential",
        "twobrain_web_csrf_secret",
        "twobrain_support_incident_github_token",
        "twobrain_yookassa_secret",
        "twobrain_yookassa_webhook_secret",
        "twobrain_billing_referral_secret",
    ]:
        assert secret_name in secrets

    api = compose["services"]["rec-api"]
    api_secret_sources = {secret["source"] for secret in api["secrets"]}
    assert {
        "twobrain_postgres_app_password",
        "twobrain_minio_api_access_key",
        "twobrain_minio_api_secret_key",
        "twobrain_smoke_credential",
        "twobrain_web_csrf_secret",
        "twobrain_support_incident_github_token",
        "twobrain_yookassa_secret",
        "twobrain_yookassa_webhook_secret",
        "twobrain_billing_referral_secret",
    } <= api_secret_sources
    assert api["environment"]["TWOBRAIN_BILLING_YOOKASSA_SECRET_FILE"] == "/run/secrets/twobrain_yookassa_secret"
    assert api["environment"]["TWOBRAIN_BILLING_YOOKASSA_WEBHOOK_SECRET_FILE"] == "/run/secrets/twobrain_yookassa_webhook_secret"
    assert api["environment"]["TWOBRAIN_BILLING_REFERRAL_SECRET_FILE"] == "/run/secrets/twobrain_billing_referral_secret"
    assert (
        api["environment"]["TWOBRAIN_SUPPORT_INCIDENT_GITHUB_TOKEN_FILE"]
        == "/run/secrets/twobrain_support_incident_github_token"
    )

    postgres = compose["services"]["rec-postgres"]
    assert any(secret["source"] == "twobrain_postgres_password" for secret in postgres["secrets"])


def test_generated_runtime_secrets_use_private_deploy_group_mounts() -> None:
    compose = _compose()
    generated_secret_files = {
        "twobrain_postgres_app_password": (
            "${TWOBRAIN_POSTGRES_APP_PASSWORD_FILE:-./secrets/twobrain_postgres_app_password}"
        ),
        "twobrain_postgres_maintenance_password": (
            "${TWOBRAIN_POSTGRES_MAINTENANCE_PASSWORD_FILE:-"
            "./secrets/twobrain_postgres_maintenance_password}"
        ),
        "twobrain_postgres_media_password": (
            "${TWOBRAIN_POSTGRES_MEDIA_PASSWORD_FILE:-./secrets/twobrain_postgres_media_password}"
        ),
        "twobrain_minio_media_access_key": (
            "${TWOBRAIN_MINIO_MEDIA_ACCESS_KEY_FILE:-./secrets/twobrain_minio_media_access_key}"
        ),
        "twobrain_minio_media_secret_key": (
            "${TWOBRAIN_MINIO_MEDIA_SECRET_KEY_FILE:-./secrets/twobrain_minio_media_secret_key}"
        ),
    }
    private_group_services = {
        "rec-api",
        "rec-processing-worker",
        "rec-media-worker",
        "rec-migrate",
        "rec-db-runtime-bootstrap",
        "rec-maintenance",
        "rec-reprocess-maintenance",
        "rec-prompt-optimization-worker",
        "rec-minio-init",
    }

    for secret_name, file_source in generated_secret_files.items():
        assert compose["secrets"][secret_name] == {"file": file_source}

    for service_name in private_group_services:
        assert compose["services"][service_name]["group_add"] == [
            "${TWOBRAIN_RUNTIME_SECRET_GID:-1001}"
        ]

    for service_name, service in compose["services"].items():
        for secret in service.get("secrets", []):
            if secret["source"] not in generated_secret_files:
                continue
            assert {"uid", "gid", "mode"}.isdisjoint(secret)
            assert service_name == "rec-minio-init" or service_name in private_group_services


def test_prompt_optimization_worker_is_operations_only_and_isolated_from_recording_workers() -> None:
    compose = _compose()
    optimizer = compose["services"]["rec-prompt-optimization-worker"]
    processing = compose["services"]["rec-processing-worker"]

    assert optimizer["profiles"] == ["operations"]
    assert optimizer["command"] == [
        "python",
        "-m",
        "twobrain_rec_server.workflows.prompt_optimization_worker",
    ]
    assert optimizer["environment"]["TWOBRAIN_DATABASE_URL"].startswith(
        "postgresql+asyncpg://twobrain_rec_maintenance:"
    )
    assert optimizer["environment"]["TWOBRAIN_PROMPT_OPTIMIZATION_ENABLED"].endswith(
        "false}"
    )
    assert {
        secret["source"] for secret in optimizer["secrets"]
    } >= {
        "twobrain_postgres_maintenance_password",
        "twobrain_litellm_api_key",
        "twobrain_langfuse_public_key",
        "twobrain_langfuse_secret_key",
    }
    assert "twobrain_postgres_maintenance_password" not in {
        secret["source"] for secret in processing["secrets"]
    }
    assert "TWOBRAIN_PROMPT_OPTIMIZATION_DATABASE_URL" not in processing["environment"]


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
            "TWOBRAIN_LANGFUSE_PUBLIC_KEY_FILE",
            "TWOBRAIN_LANGFUSE_SECRET_KEY_FILE",
            "TWOBRAIN_LITELLM_API_KEY_FILE",
            "TWOBRAIN_SUPPORT_INCIDENT_GITHUB_TOKEN_FILE",
            "TWOBRAIN_WEB_CSRF_SECRET_FILE",
        }
    )


def test_production_runtime_database_roles_are_least_privilege_and_bootstrapped() -> None:
    compose = _compose()
    services = compose["services"]
    api = services["rec-api"]
    processing = services["rec-processing-worker"]
    maintenance = services["rec-maintenance"]
    reprocess = services["rec-reprocess-maintenance"]
    media = services["rec-media-worker"]
    migrate = services["rec-migrate"]
    bootstrap = services["rec-db-runtime-bootstrap"]

    assert "//twobrain_rec_app:" in api["environment"]["TWOBRAIN_DATABASE_URL"]
    assert "//twobrain_rec_app:" in processing["environment"]["TWOBRAIN_DATABASE_URL"]
    assert "//twobrain_rec_maintenance:" in maintenance["environment"]["TWOBRAIN_DATABASE_URL"]
    assert "//twobrain_rec_maintenance:" in reprocess["environment"]["TWOBRAIN_DATABASE_URL"]
    assert "//twobrain_rec_media:" in media["environment"]["TWOBRAIN_DATABASE_URL"]
    assert "//twobrain_rec:" in migrate["environment"]["TWOBRAIN_DATABASE_URL"]
    assert {secret["source"] for secret in api["secrets"]} >= {"twobrain_postgres_app_password"}
    assert {secret["source"] for secret in processing["secrets"]} >= {
        "twobrain_postgres_app_password"
    }
    assert {secret["source"] for secret in maintenance["secrets"]} >= {
        "twobrain_postgres_maintenance_password"
    }
    assert {secret["source"] for secret in reprocess["secrets"]} >= {
        "twobrain_postgres_maintenance_password"
    }
    assert {secret["source"] for secret in media["secrets"]} >= {"twobrain_postgres_media_password"}
    assert bootstrap["command"] == [
        "python",
        "/app/scripts/bootstrap_runtime_database_roles.py",
    ]
    assert {secret["source"] for secret in bootstrap["secrets"]} == {
        "twobrain_postgres_password",
        "twobrain_postgres_app_password",
        "twobrain_postgres_maintenance_password",
        "twobrain_postgres_media_password",
    }


def test_only_api_receives_web_runtime_secret() -> None:
    compose = _compose()
    services = compose["services"]
    api = services["rec-api"]

    assert api["environment"]["TWOBRAIN_WEB_RUNTIME_ENABLED"] == "true"
    assert api["environment"]["TWOBRAIN_WEB_CSRF_SECRET_FILE"] == (
        "/run/secrets/twobrain_web_csrf_secret"
    )
    for service_name in (
        "rec-processing-worker",
        "rec-maintenance",
        "rec-reprocess-maintenance",
        "rec-media-worker",
        "rec-migrate",
    ):
        service = services[service_name]
        assert service["environment"]["TWOBRAIN_WEB_RUNTIME_ENABLED"] == "false"
        assert "TWOBRAIN_WEB_CSRF_SECRET_FILE" not in service["environment"]
        assert "twobrain_web_csrf_secret" not in {secret["source"] for secret in service["secrets"]}


def test_maintenance_runtime_is_explicit_hardened_and_has_no_user_runtime_secrets() -> None:
    compose = _compose()
    service = compose["services"]["rec-maintenance"]
    secret_sources = {secret["source"] for secret in service["secrets"]}

    assert service["profiles"] == ["operations"]
    assert service["user"] == "twobrain"
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert service["security_opt"] == ["no-new-privileges:true"]
    assert service["networks"] == ["rec-private"]
    assert secret_sources == {
        "twobrain_postgres_maintenance_password",
        "twobrain_minio_api_access_key",
        "twobrain_minio_api_secret_key",
        "twobrain_yookassa_secret",
        "twobrain_yookassa_webhook_secret",
        "twobrain_billing_referral_secret",
        "twobrain_litellm_api_key",
        "twobrain_langfuse_public_key",
        "twobrain_langfuse_secret_key",
    }
    assert "twobrain_mediascribe_api_key" not in secret_sources
    assert "twobrain_web_csrf_secret" not in secret_sources
    assert service["environment"]["TWOBRAIN_LITELLM_API_KEY_FILE"] == (
        "/run/secrets/twobrain_litellm_api_key"
    )
    assert service["environment"]["TWOBRAIN_LANGFUSE_PUBLIC_KEY_FILE"] == (
        "/run/secrets/twobrain_langfuse_public_key"
    )
    assert service["environment"]["TWOBRAIN_LANGFUSE_SECRET_KEY_FILE"] == (
        "/run/secrets/twobrain_langfuse_secret_key"
    )
    assert service["environment"]["TWOBRAIN_BILLING_YOOKASSA_SECRET_FILE"] == (
        "/run/secrets/twobrain_yookassa_secret"
    )
    assert service["environment"]["TWOBRAIN_BILLING_YOOKASSA_WEBHOOK_SECRET_FILE"] == (
        "/run/secrets/twobrain_yookassa_webhook_secret"
    )


def test_reprocess_runtime_is_explicit_hardened_and_scoped_to_recovery_secrets() -> None:
    compose = _compose()
    service = compose["services"]["rec-reprocess-maintenance"]
    secret_sources = {secret["source"] for secret in service["secrets"]}

    assert service["profiles"] == ["operations"]
    assert service["user"] == "twobrain"
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert service["security_opt"] == ["no-new-privileges:true"]
    assert service["networks"] == ["rec-private"]
    assert secret_sources == {
        "twobrain_postgres_maintenance_password",
        "twobrain_minio_api_access_key",
        "twobrain_minio_api_secret_key",
        "twobrain_mediascribe_api_key",
    }
    assert "twobrain_web_csrf_secret" not in secret_sources
    assert "twobrain_smoke_credential" not in secret_sources
    assert "twobrain_support_incident_github_token" not in secret_sources


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
    assert temporal_env["BIND_ON_IP"] == "0.0.0.0"
    assert "POSTGRES_PWD" not in temporal_env
    assert temporal["user"] == "root"
    assert 'POSTGRES_PWD="$$(cat /run/secrets/twobrain_postgres_password)"' in entrypoint
    assert "/etc/temporal/entrypoint.sh autosetup" in entrypoint
    assert {
        "source": "twobrain_postgres_password",
        "target": "twobrain_postgres_password",
    } in temporal["secrets"]
    assert temporal["depends_on"]["rec-postgres"]["condition"] == "service_healthy"
    assert "127.0.0.1:7233" in " ".join(temporal["healthcheck"]["test"])


def test_production_api_autostarts_processing_and_worker_can_read_processing_secrets() -> None:
    compose = _compose()
    api = compose["services"]["rec-api"]
    worker = compose["services"]["rec-processing-worker"]
    api_env = api["environment"]
    api_secret_sources = {secret["source"] for secret in api["secrets"]}

    assert api_env["TWOBRAIN_PROCESSING_ENABLED"] == "true"
    assert api_env["TWOBRAIN_TEMPORAL_ADDRESS"] == "rec-temporal:7233"
    assert "TWOBRAIN_MEDIASCRIBE_API_KEY_FILE" not in api_env
    assert api["depends_on"]["rec-temporal"]["condition"] == "service_healthy"
    assert "twobrain_mediascribe_api_key" not in api_secret_sources
    assert worker["user"] == "twobrain"
    assert (
        worker["environment"]["TWOBRAIN_MEDIASCRIBE_API_KEY_FILE"]
        == "/run/secrets/twobrain_mediascribe_api_key"
    )
    assert any(secret["source"] == "twobrain_mediascribe_api_key" for secret in worker["secrets"])
    assert worker["depends_on"]["rec-temporal"]["condition"] == "service_healthy"
    assert worker["healthcheck"]["test"] == [
        "CMD",
        "python",
        "/app/scripts/verify_processing_worker_ready.py",
    ]
    assert worker["networks"] == ["rec-private", "postal-network"]
    assert compose["networks"]["postal-network"]["external"] is True


def test_private_group_runtime_secrets_are_only_mounted_by_group_enabled_services() -> None:
    compose = _compose()
    private_group_secrets = {
        "graf_credential_encryption_key",
        "twobrain_web_csrf_secret",
        "twobrain_postal_api_key",
        "twobrain_yandex_client_secret",
        "twobrain_vk_client_secret",
        "twobrain_support_incident_github_token",
        "twobrain_yookassa_secret",
        "twobrain_yookassa_webhook_secret",
        "twobrain_billing_referral_secret",
        "twobrain_mediascribe_api_key",
        "twobrain_minio_api_access_key",
        "twobrain_minio_api_secret_key",
        "twobrain_smoke_credential",
    }

    for service in compose["services"].values():
        secret_sources = {secret["source"] for secret in service.get("secrets", [])}
        if secret_sources & private_group_secrets:
            assert service["group_add"] == ["${TWOBRAIN_RUNTIME_SECRET_GID:-1001}"]


def test_media_worker_is_isolated_non_root_and_has_no_mediascribe_secret() -> None:
    compose = _compose()
    worker = compose["services"]["rec-media-worker"]
    worker_env = worker["environment"]
    secret_sources = {secret["source"] for secret in worker["secrets"]}

    assert worker["build"]["target"] == "media-runtime"
    assert worker["user"] == "twobrain"
    assert worker["read_only"] is True
    assert worker["cap_drop"] == ["ALL"]
    assert worker["security_opt"] == ["no-new-privileges:true"]
    assert worker["pids_limit"] == 128
    assert worker["cpus"] == "1.0"
    assert worker["mem_limit"] == "1g"
    assert worker_env["TWOBRAIN_PLAYBACK_NORMALIZATION_ENABLED"] == "true"
    assert worker_env["TWOBRAIN_PLAYBACK_NORMALIZATION_AUTOMATIC_DISPATCH_ENABLED"] == (
        "${TWOBRAIN_PLAYBACK_NORMALIZATION_AUTOMATIC_DISPATCH_ENABLED:-true}"
    )
    assert worker_env["TWOBRAIN_PLAYBACK_NORMALIZATION_TASK_QUEUE"] == (
        "twobrain-rec-playback-normalization"
    )
    assert worker_env["TWOBRAIN_PLAYBACK_NORMALIZATION_WORKER_CONCURRENCY"] == "1"
    assert worker["healthcheck"]["test"] == [
        "CMD",
        "python",
        "/app/scripts/verify_playback_normalization_worker_ready.py",
    ]
    assert "TWOBRAIN_MEDIASCRIBE_API_KEY_FILE" not in worker_env
    assert "twobrain_mediascribe_api_key" not in secret_sources
    assert worker_env["TWOBRAIN_MINIO_ACCESS_KEY_FILE"] == (
        "/run/secrets/twobrain_minio_media_access_key"
    )
    assert worker_env["TWOBRAIN_MINIO_SECRET_KEY_FILE"] == (
        "/run/secrets/twobrain_minio_media_secret_key"
    )
    assert {
        "twobrain_minio_media_access_key",
        "twobrain_minio_media_secret_key",
    } <= secret_sources
    assert "twobrain_minio_api_access_key" not in secret_sources
    assert "twobrain_minio_api_secret_key" not in secret_sources
    assert worker["volumes"] == ["rec-media-work:/var/lib/twobrain-rec/playback-normalization"]
    assert worker["depends_on"]["rec-temporal"]["condition"] == "service_healthy"
    assert worker["networks"] == ["rec-media-private"]
    assert compose["networks"]["rec-media-private"]["internal"] is True
    for dependency in ("rec-postgres", "rec-minio", "rec-temporal"):
        assert "rec-media-private" in compose["services"][dependency]["networks"]
    for unrelated in ("rec-api", "rec-processing-worker", "rec-migrate", "rec-minio-init"):
        assert "rec-media-private" not in compose["services"][unrelated]["networks"]


def test_dev_media_worker_keeps_the_same_non_root_resource_boundary() -> None:
    compose = _dev_compose()
    worker = compose["services"]["rec-media-worker"]

    assert worker["user"] == "twobrain"
    assert worker["init"] is True
    assert worker["read_only"] is True
    assert worker["cap_drop"] == ["ALL"]
    assert worker["security_opt"] == ["no-new-privileges:true"]
    assert worker["pids_limit"] == 128
    assert worker["cpus"] == "1.0"
    assert worker["mem_limit"] == "1g"
    assert worker["environment"]["TWOBRAIN_PLAYBACK_NORMALIZATION_WORKER_CONCURRENCY"] == "1"
    assert worker["environment"]["TWOBRAIN_MINIO_ACCESS_KEY"] == "twobrain_rec_media"
    assert worker["healthcheck"]["test"][-1] == (
        "/app/scripts/verify_playback_normalization_worker_ready.py"
    )
    assert worker["networks"] == ["rec-media-private"]
    assert worker["depends_on"]["rec-temporal"]["condition"] == "service_healthy"


def test_dev_temporal_and_processing_worker_use_readiness_gates() -> None:
    compose = _dev_compose()
    temporal = compose["services"]["rec-temporal"]
    worker = compose["services"]["rec-processing-worker"]

    assert temporal["environment"]["BIND_ON_IP"] == "0.0.0.0"
    assert "127.0.0.1:7233" in " ".join(temporal["healthcheck"]["test"])
    assert worker["depends_on"]["rec-temporal"]["condition"] == "service_healthy"
    assert worker["healthcheck"]["test"][-1] == "/app/scripts/verify_processing_worker_ready.py"


def test_media_worker_minio_policy_is_prefix_scoped_without_bucket_listing() -> None:
    for compose in (_compose(), _dev_compose()):
        policy = _media_minio_policy(compose)
        statements = policy["Statement"]
        actions = {action for statement in statements for action in statement["Action"]}
        resources_by_action = {
            action: {
                resource
                for statement in statements
                if action in statement["Action"]
                for resource in statement["Resource"]
            }
            for action in actions
        }

        bucket_resource = "arn:aws:s3:::twobrain-rec-ingest"
        source_resources = {
            "arn:aws:s3:::twobrain-rec-ingest/organizations/*/workspaces/*/meetings/*/"
            "artifacts/media-revisions/*/tracks/media",
            "arn:aws:s3:::twobrain-rec-ingest/organizations/*/workspaces/*/meetings/*/"
            "artifacts/media-revisions/*/tracks/microphone",
            "arn:aws:s3:::twobrain-rec-ingest/organizations/*/workspaces/*/meetings/*/"
            "artifacts/media-revisions/*/tracks/system",
            "arn:aws:s3:::twobrain-rec-ingest/organizations/*/workspaces/*/meetings/*/"
            "artifacts/media-revisions/*/tracks/playback",
        }
        normalization_resource = (
            "arn:aws:s3:::twobrain-rec-ingest/organizations/*/workspaces/*/meetings/*/"
            "artifacts/playback-normalization/revisions/*/attempts/*/meeting-review.m4a"
        )
        assert "s3:ListBucket" not in actions
        assert resources_by_action["s3:GetBucketLocation"] == {bucket_resource}
        assert resources_by_action["s3:GetObject"] == {
            "arn:aws:s3:::twobrain-rec-ingest/_system/readiness/ready",
            "arn:aws:s3:::twobrain-rec-ingest/organizations/*/workspaces/*/meetings/*/"
            "sessions/*/tracks/media/parts/*",
            "arn:aws:s3:::twobrain-rec-ingest/organizations/*/workspaces/*/meetings/*/"
            "sessions/*/tracks/microphone/parts/*",
            "arn:aws:s3:::twobrain-rec-ingest/organizations/*/workspaces/*/meetings/*/"
            "sessions/*/tracks/system/parts/*",
            "arn:aws:s3:::twobrain-rec-ingest/organizations/*/workspaces/*/meetings/*/"
            "sessions/*/tracks/playback/parts/*",
            *source_resources,
            normalization_resource,
        }
        for action in (
            "s3:PutObject",
            "s3:DeleteObject",
            "s3:AbortMultipartUpload",
            "s3:ListMultipartUploadParts",
        ):
            assert resources_by_action[action] == {normalization_resource}


def test_minio_init_publishes_storage_readiness_sentinel() -> None:
    for compose in (_compose(), _dev_compose()):
        script = compose["services"]["rec-minio-init"]["entrypoint"][-1]
        assert "_system/readiness/ready" in script
    assert compose["networks"]["rec-media-private"]["internal"] is True


def test_dockerfile_keeps_ffmpeg_in_media_target_only() -> None:
    dockerfile = DOCKERFILE_PATH.read_text()
    media_block = dockerfile.split("FROM base AS media-runtime", maxsplit=1)[1].split(
        "FROM base AS runtime",
        maxsplit=1,
    )[0]
    runtime_block = dockerfile.split("FROM base AS runtime", maxsplit=1)[1]

    assert (
        DOCKERFILE_PATH.read_text()
        .splitlines()[0]
        .startswith("FROM python:3.13-slim-bookworm@sha256:")
    )
    assert "snapshot.debian.org/archive/debian/20260518T000000Z" in media_block
    assert "apt-get install --no-install-recommends --yes ffmpeg=7:5.1.9-0+deb12u1" in (media_block)
    assert "USER twobrain" in media_block
    assert "ffmpeg" not in runtime_block


def test_production_api_allows_runtime_public_analytics_overrides() -> None:
    compose = _compose()
    api_env = compose["services"]["rec-api"]["environment"]
    worker_env = compose["services"]["rec-processing-worker"]["environment"]

    assert (
        api_env["TWOBRAIN_PUBLIC_ANALYTICS_ENABLED"]
        == "${TWOBRAIN_PUBLIC_ANALYTICS_ENABLED:-false}"
    )
    assert (
        api_env["TWOBRAIN_PUBLIC_ANALYTICS_YANDEX_METRICA_ID"]
        == "${TWOBRAIN_PUBLIC_ANALYTICS_YANDEX_METRICA_ID:-}"
    )
    assert (
        api_env["TWOBRAIN_PUBLIC_ANALYTICS_VALIDATION_MODE"]
        == "${TWOBRAIN_PUBLIC_ANALYTICS_VALIDATION_MODE:-disabled}"
    )
    assert (
        api_env["TWOBRAIN_PUBLIC_ANALYTICS_REPLAY_ENABLED"]
        == "${TWOBRAIN_PUBLIC_ANALYTICS_REPLAY_ENABLED:-false}"
    )
    assert (
        api_env["TWOBRAIN_PUBLIC_ANALYTICS_CONSENT_COPY_VERSION"]
        == "${TWOBRAIN_PUBLIC_ANALYTICS_CONSENT_COPY_VERSION:-2026-08-13.1}"
    )
    assert "TWOBRAIN_PUBLIC_ANALYTICS_YANDEX_METRICA_ID" not in worker_env


def test_remote_cd_blocks_static_postgres_pwd_in_compose_config() -> None:
    script = (REPO_ROOT / "infra/scripts/cd-remote-runtime.sh").read_text()

    assert "POSTGRES_PWD:" in script


def test_remote_cd_normalizes_billing_secret_paths_and_fails_closed_on_placeholder() -> None:
    script = (REPO_ROOT / "infra/scripts/cd-remote-runtime.sh").read_text()

    assert "normalize_compose_secret_path" in script
    assert 'TWOBRAIN_BILLING_YOOKASSA_SECRET_FILE:-./secrets/twobrain_yookassa_secret' in script
    assert 'TWOBRAIN_BILLING_YOOKASSA_WEBHOOK_SECRET_FILE:-./secrets/twobrain_yookassa_webhook_secret' in script
    assert 'TWOBRAIN_BILLING_REFERRAL_SECRET_FILE:-./secrets/twobrain_billing_referral_secret' in script
    assert "TWOBRAIN_BILLING_PROVIDER_OBSERVATION_ENABLED:-false" in script
    assert "expected_disabled_billing_secret_count=2" in script
    assert "billing_enabled_compose_uses_disabled_secret_placeholder" in script
