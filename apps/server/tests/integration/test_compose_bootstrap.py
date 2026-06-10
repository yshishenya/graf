from pathlib import Path

import yaml

ROOT = Path(__file__).parents[4]


def test_production_compose_separates_minio_root_and_api_credentials() -> None:
    compose = yaml.safe_load((ROOT / "infra/docker-compose.yml").read_text(encoding="utf-8"))
    api_env = compose["services"]["rec-api"]["environment"]
    minio_env = compose["services"]["rec-minio"]["environment"]

    assert api_env["TWOBRAIN_MINIO_ACCESS_KEY"] == "__DOCKER_SECRET_FILE__"
    assert api_env["TWOBRAIN_MINIO_SECRET_KEY"] == "__DOCKER_SECRET_FILE__"
    assert "MINIO_ROOT_USER" not in minio_env
    assert "MINIO_ROOT_PASSWORD" not in minio_env
    assert minio_env["MINIO_ROOT_USER_FILE"] == "/run/secrets/twobrain_minio_root_user"
    assert minio_env["MINIO_ROOT_PASSWORD_FILE"] == "/run/secrets/twobrain_minio_root_password"
    assert "rec-minio-init" in compose["services"]


def test_seed_dev_identity_script_is_packaged_and_uses_stable_ids() -> None:
    script = (ROOT / "apps/server/scripts/seed_dev_identity.py").read_text(encoding="utf-8")

    assert "DEFAULT_ORG_ID" in script
    assert "DEFAULT_WORKSPACE_ID" in script
    assert "DEFAULT_USER_ID" in script
    assert "DEFAULT_DEVICE_ID" in script
    assert "WorkspaceMembership" in script
