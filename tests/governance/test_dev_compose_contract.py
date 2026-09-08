from pathlib import Path
import os
import re
import subprocess


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
    match = re.search(
        r"^\s*image:\s*\"\$\{GRAF_DEV_TEMPORAL_IMAGE:-temporalio/auto-setup:(\d+)\.(\d+)\.(\d+)\}\"",
        temporal.group(1),
        re.MULTILINE,
    )
    assert match, "Dev Compose must pin an explicit Temporal Server image"
    assert tuple(int(part) for part in match.groups()) >= (1, 28, 0)


def test_compose_does_not_consume_inherited_env_file_or_disable_processing():
    assert "env_file:" not in COMPOSE
    assert 'TWOBRAIN_PROCESSING_ENABLED: "true"' in COMPOSE
    assert "GRAF_DEV_SOURCE_SHA is required" in COMPOSE
    assert "GRAF_DEV_EXPECTED_MIGRATION_HEAD is required" in COMPOSE
    assert 'TWOBRAIN_LOCAL_HTTP_AUTH_COOKIE_ENABLED: "true"' in COMPOSE
    assert 'TWOBRAIN_LOCAL_EMAIL_LOGIN_CODE: "000000"' in COMPOSE


def test_every_compose_service_has_an_explicit_manifest_image_override():
    for variable in (
        "GRAF_DEV_API_IMAGE",
        "GRAF_DEV_PROCESSING_WORKER_IMAGE",
        "GRAF_DEV_MAINTENANCE_IMAGE",
        "GRAF_DEV_MEDIA_WORKER_IMAGE",
        "GRAF_DEV_MIGRATION_IMAGE",
        "GRAF_DEV_TEMPORAL_IMAGE",
        "GRAF_DEV_DATABASE_IMAGE",
        "GRAF_DEV_STORAGE_IMAGE",
        "GRAF_DEV_STORAGE_INIT_IMAGE",
    ):
        assert variable in COMPOSE


def test_direct_runtime_start_rejects_mutable_image_defaults(tmp_path):
    startup = ROOT / "infra" / "scripts" / "start-dev-runtime.sh"
    env = os.environ.copy()
    env["GRAF_DEV_SOURCE_SHA"] = "a" * 40
    env["GRAF_DEV_STATE_ROOT"] = str(tmp_path)
    env.pop("GRAF_DEV_API_IMAGE", None)

    result = subprocess.run(
        ["sh", str(startup)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "GRAF_DEV_API_IMAGE must be an immutable Docker image ID" in result.stderr


def test_dev_start_seeds_deterministic_local_identity_after_migration():
    startup = (ROOT / "infra/scripts/start-dev-runtime.sh").read_text()
    assert "compose run --rm rec-migrate python scripts/seed_dev_identity.py --print-login" in startup
    assert "compose run --rm rec-migrate python /app/scripts/dev-migration-preflight.py" in startup
    assert 'SERVER_ROOT=' not in startup


def test_dev_start_waits_for_long_running_infra_before_one_shot_minio_init():
    startup = (ROOT / "infra/scripts/start-dev-runtime.sh").read_text()
    assert "compose up -d --wait --force-recreate rec-postgres rec-minio rec-temporal\n" in startup
    assert "compose run --rm rec-minio-init" in startup


def test_runtime_monitor_does_not_stop_services_when_docker_inspection_fails():
    startup = (ROOT / "infra/scripts/start-dev-runtime.sh").read_text()
    loop = startup[startup.index("empty_observations=0"):]
    # Command substitutions run in subshells; sleep advances the parent counter.
    stubs = """set -eu
attempt=0
compose() {
  case "$attempt" in 0) return 1;; 1|3) echo api;; 2|4|5) return 0;; *) exit 99;; esac
}
sleep() { attempt=$((attempt + 1)); }
"""
    result = subprocess.run(["sh", "-c", stubs + loop + '\nprintf "attempts=%s" "$attempt"'],
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 0
    assert result.stdout == "attempts=5"
    assert "service inspection failed; retrying" in result.stderr


def test_runtime_termination_cleans_up_once_with_fixed_reason(tmp_path):
    startup = (ROOT / "infra/scripts/start-dev-runtime.sh").read_text()
    cleanup = startup[startup.index("cleanup() {"):startup.index("# Config is the first safety gate")]
    script = 'set -eu\ncompose() { echo stop >> "$1.stop"; }\n' + cleanup + '\necho ready\nwhile :; do :; done\n'
    process = subprocess.Popen(["sh", "-c", script], cwd=tmp_path, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        assert process.stdout.readline().strip() == "ready"
        process.terminate()
        output, _ = process.communicate(timeout=5)
        assert "reason=terminate" in output
        assert (tmp_path / "stop.stop").read_text().splitlines() == ["stop"]
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
