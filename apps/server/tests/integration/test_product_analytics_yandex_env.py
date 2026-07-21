from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parents[4]
COMPOSE_PATH = REPO_ROOT / "infra/docker-compose.yml"
ENV_TEMPLATE_PATH = REPO_ROOT / "infra/env/rec.production.env.example"


def test_yandex_offline_secret_mount_and_runtime_env_are_api_only() -> None:
    compose = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))
    api_env = compose["services"]["rec-api"]["environment"]
    worker_env = compose["services"]["rec-processing-worker"]["environment"]
    api_secrets = {
        secret["source"] if isinstance(secret, dict) else secret
        for secret in compose["services"]["rec-api"]["secrets"]
    }

    assert api_env["TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_COUNTER_ID"] == (
        "${TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_COUNTER_ID:-}"
    )
    assert api_env["TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_OAUTH_TOKEN_FILE"] == (
        "${TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_OAUTH_TOKEN_FILE:-}"
    )
    assert "graf_yandex_offline_oauth_token" in api_secrets
    assert "TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_OAUTH_TOKEN_FILE" not in worker_env


def test_yandex_env_template_has_redacted_counter_and_oauth_rotation_notes() -> None:
    template = ENV_TEMPLATE_PATH.read_text(encoding="utf-8")

    assert "# TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_COUNTER_ID=" in template
    assert "# TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_OAUTH_TOKEN_FILE=/run/secrets/graf_yandex_offline_oauth_token" in template
    assert "# TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_OAUTH_TOKEN_SECRET_FILE=./secrets/graf_yandex_offline_oauth_token" in template
    assert "growth analytics operator" in template
    assert "Do not commit live IDs" in template
    assert "oauth_token=" not in template.lower()
