from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = (ROOT / "infra/docker-compose.dev.yml").read_text()


def test_compose_is_explicitly_namespaced_and_loopback_only():
    assert "name: graf-dev" in COMPOSE
    assert '127.0.0.1:8081:8080' in COMPOSE
    assert '127.0.0.1:54329:5432' in COMPOSE
    assert '127.0.0.1:9002:9000' in COMPOSE
    assert '127.0.0.1:7233:7233' in COMPOSE
    assert "rec-processing-worker" in COMPOSE and "rec-media-worker" in COMPOSE


def test_dev_temporal_server_includes_reserved_partition_poll_fix():
    temporal = re.search(r"(?ms)^  rec-temporal:\n(.*?)(?=^  \S|\Z)", COMPOSE)
    assert temporal, "Dev Compose must define rec-temporal"
    match = re.search(r"^\s*image:\s*temporalio/auto-setup:(\d+)\.(\d+)\.(\d+)", temporal.group(1), re.MULTILINE)
    assert match, "Dev Compose must pin an explicit Temporal Server image"
    assert tuple(int(part) for part in match.groups()) >= (1, 28, 0)


def test_compose_does_not_consume_inherited_env_file_or_disable_processing():
    assert "env_file:" not in COMPOSE
    assert 'TWOBRAIN_PROCESSING_ENABLED: "true"' in COMPOSE
    assert "GRAF_DEV_SOURCE_SHA is required" in COMPOSE
    assert 'TWOBRAIN_LOCAL_HTTP_AUTH_COOKIE_ENABLED: "true"' in COMPOSE
    assert 'TWOBRAIN_LOCAL_EMAIL_LOGIN_CODE: "000000"' in COMPOSE


def test_dev_start_seeds_deterministic_local_identity_after_migration():
    startup = (ROOT / "infra/scripts/start-dev-runtime.sh").read_text()
    assert "scripts/seed_dev_identity.py --print-login" in startup


def test_dev_start_waits_for_long_running_infra_before_one_shot_minio_init():
    startup = (ROOT / "infra/scripts/start-dev-runtime.sh").read_text()
    assert "compose up -d --wait --force-recreate rec-postgres rec-minio rec-temporal\n" in startup
    assert "compose run --rm rec-minio-init" in startup
