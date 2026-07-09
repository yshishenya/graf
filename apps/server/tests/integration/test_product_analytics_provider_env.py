from pathlib import Path

import yaml

from twobrain_rec_server.product_analytics.provider_secrets import (
    default_provider_secret_inventory,
)

REPO_ROOT = Path(__file__).parents[4]
COMPOSE_PATH = REPO_ROOT / "infra/docker-compose.yml"
ENV_TEMPLATE_PATH = REPO_ROOT / "infra/env/rec.production.env.example"
POSTHOG_COMPOSE_PATH = REPO_ROOT / "infra/posthog/docker-compose.posthog.yml"
POSTHOG_ENV_EXAMPLE_PATH = REPO_ROOT / "infra/posthog/posthog.production.env.example"
CD_REMOTE_PATH = REPO_ROOT / "infra/scripts/cd-remote.sh"


def _compose() -> dict:
    return yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))


def test_096_provider_env_reaches_only_rec_api() -> None:
    compose = _compose()
    api_env = compose["services"]["rec-api"]["environment"]
    worker_env = compose["services"]["rec-processing-worker"]["environment"]
    migrate_env = compose["services"]["rec-migrate"]["environment"]
    expected_api_keys = {
        "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_AUTOCAPTURE_ENABLED",
        "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_CREDENTIAL_SUPPRESSION_ENABLED",
        "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_WEB_DIRECT_ENABLED",
        "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_DESKTOP_DIRECT_ENABLED",
        "TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_INVENTORY_VERSION",
        "TWOBRAIN_PRODUCT_ANALYTICS_ROLLBACK_MODE",
        "TWOBRAIN_PRODUCT_ANALYTICS_PRIVACY_APPROVED",
        "TWOBRAIN_PRODUCT_ANALYTICS_SECURITY_APPROVED",
        "TWOBRAIN_PRODUCT_ANALYTICS_QA_APPROVED",
        "TWOBRAIN_PRODUCT_ANALYTICS_DISCLOSURE_APPROVED",
        "TWOBRAIN_PRODUCT_ANALYTICS_ROLLBACK_APPROVED",
        "TWOBRAIN_PRODUCT_ANALYTICS_LIVE_PROVIDER_DELIVERY_APPROVED",
    }

    assert expected_api_keys <= set(api_env)
    assert expected_api_keys.isdisjoint(worker_env)
    assert expected_api_keys.isdisjoint(migrate_env)
    assert api_env["TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_AUTOCAPTURE_ENABLED"].endswith(":-true}")
    assert api_env["TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_CREDENTIAL_SUPPRESSION_ENABLED"].endswith(":-true}")
    assert api_env["TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_DESKTOP_DIRECT_ENABLED"].endswith(":-false}")


def test_provider_secret_mounts_are_rec_api_only() -> None:
    compose = _compose()
    api_secrets = {
        secret["source"] if isinstance(secret, dict) else secret
        for secret in compose["services"]["rec-api"]["secrets"]
    }
    worker_secrets = {
        secret["source"] if isinstance(secret, dict) else secret
        for secret in compose["services"]["rec-processing-worker"]["secrets"]
    }
    migrate_secrets = {
        secret["source"] if isinstance(secret, dict) else secret
        for secret in compose["services"]["rec-migrate"]["secrets"]
    }

    assert {"graf_posthog_project_key", "graf_yandex_offline_oauth_token"} <= api_secrets
    assert "graf_posthog_project_key" not in worker_secrets
    assert "graf_yandex_offline_oauth_token" not in worker_secrets
    assert "graf_posthog_project_key" not in migrate_secrets
    assert "graf_yandex_offline_oauth_token" not in migrate_secrets


def test_env_template_documents_owner_rotation_and_redacted_defaults() -> None:
    template = ENV_TEMPLATE_PATH.read_text(encoding="utf-8")

    for key in (
        "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_AUTOCAPTURE_ENABLED",
        "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_CREDENTIAL_SUPPRESSION_ENABLED",
        "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_WEB_DIRECT_ENABLED",
        "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_DESKTOP_DIRECT_ENABLED",
        "TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_INVENTORY_VERSION",
        "TWOBRAIN_PRODUCT_ANALYTICS_ROLLBACK_MODE",
        "TWOBRAIN_PRODUCT_ANALYTICS_PRIVACY_APPROVED",
        "TWOBRAIN_PRODUCT_ANALYTICS_SECURITY_APPROVED",
        "TWOBRAIN_PRODUCT_ANALYTICS_QA_APPROVED",
        "TWOBRAIN_PRODUCT_ANALYTICS_DISCLOSURE_APPROVED",
        "TWOBRAIN_PRODUCT_ANALYTICS_ROLLBACK_APPROVED",
        "TWOBRAIN_PRODUCT_ANALYTICS_LIVE_PROVIDER_DELIVERY_APPROVED",
    ):
        assert f"# {key}=" in template
    assert "Owner role:" in template
    assert "Rotation:" in template
    assert "phc_" not in template
    assert "oauth_token=" not in template.lower()


def test_default_secret_inventory_has_owner_rotation_and_propagation_tests() -> None:
    inventory = default_provider_secret_inventory()
    logical_names = {entry.logical_name for entry in inventory}

    assert {
        "POSTHOG_PROJECT_KEY",
        "POSTHOG_SECRET_KEY",
        "POSTHOG_DB_PASSWORD",
        "YANDEX_COUNTER_ID",
        "YANDEX_OAUTH_TOKEN",
        "PRODUCT_ANALYTICS_FLAGS",
    } <= logical_names
    assert all(entry.owner_role for entry in inventory)
    assert all(entry.rotation_note for entry in inventory)
    assert all(entry.propagation_test for entry in inventory)
    assert all(entry.committed_default in {"empty", "placeholder", "disabled"} for entry in inventory)


def test_posthog_stack_uses_separate_project_secret_files_and_redacted_env() -> None:
    posthog_compose = yaml.safe_load(POSTHOG_COMPOSE_PATH.read_text(encoding="utf-8"))
    posthog_compose_text = POSTHOG_COMPOSE_PATH.read_text(encoding="utf-8")
    posthog_env = POSTHOG_ENV_EXAMPLE_PATH.read_text(encoding="utf-8")

    assert posthog_compose["name"] == "graf-posthog"
    assert (
        posthog_compose["x-graf-official-runtime-handoff"]["production_runtime_source"]
        == "official_posthog_hobby_generated_compose"
    )
    assert "${POSTHOG_RUNTIME_ENV_FILE:-./posthog.production.env.example}" in posthog_compose_text
    assert "posthog_secret_key" in posthog_compose["secrets"]
    assert "posthog_db_password" in posthog_compose["secrets"]
    assert "POSTHOG_SECRET_KEY_FILE=/run/secrets/posthog_secret_key" in posthog_env
    assert "POSTHOG_DB_PASSWORD_FILE=/run/secrets/posthog_db_password" in posthog_env
    assert "POSTHOG_RETENTION_MIN_DAYS=90" in posthog_env
    assert "POSTHOG_LIVE_SECRET_VALUES_IN_GIT=false" in posthog_env


def test_cd_remote_dry_run_includes_metadata_only_posthog_stack_handoff() -> None:
    script = CD_REMOTE_PATH.read_text(encoding="utf-8")

    assert "posthog_stack_handoff=dry_run_metadata_only" in script
    assert "posthog_stack_contract=infra/posthog/docker-compose.posthog.yml" in script
    assert "posthog_stack_runtime_source=official_posthog_hobby_generated_compose_required" in script
    assert "posthog_stack_execute=requires_explicit_release_approval" in script
