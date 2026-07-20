import os
import subprocess
from pathlib import Path

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.provider_config import ProductAnalyticsProviderConfig

REPO_ROOT = Path(__file__).parents[4]
ROLLBACK_PATH = REPO_ROOT / "infra/scripts/rollback-product-analytics-providers.sh"
GUARD_PATH = REPO_ROOT / "infra/scripts/posthog-runtime-guard.sh"
GUARD_SERVICE_PATH = REPO_ROOT / "infra/posthog/graf-posthog-runtime-guard.service"
GUARD_TIMER_PATH = REPO_ROOT / "infra/posthog/graf-posthog-runtime-guard.timer"


def test_rollback_script_reports_switches_without_state_change() -> None:
    result = subprocess.run(
        [str(ROLLBACK_PATH), "--target", "all"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    output = result.stdout

    assert "provider_rollback_result=pass" in output
    assert "rollback_execution=dry_run_no_state_change" in output
    assert "target=all" in output
    assert "product_impact=measurement_gap_only" in output
    assert "posthog_delivery_switch=TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_ENABLED=false" in output
    assert "posthog_stack_stop=dry_run_metadata_only" in output
    assert "posthog_deploy_dry_run=required_after_switch" in output
    assert "posthog_move_out_failure=restore_endpoint_or_disable_delivery" in output
    assert "yandex_all_pages_switch=TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_ALL_PAGES_ENABLED=false" in output
    assert "yandex_offline_switch=TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_OFFLINE_ENABLED=false" in output
    assert "provider_validation_switch=TWOBRAIN_PRODUCT_ANALYTICS_VALIDATION_MODE=disabled" in output
    assert "normal_product_workflows=preserved" in output
    assert "secrets=not_printed" in output


def test_rollback_mode_is_configured_as_measurement_gap_not_product_failure() -> None:
    config = ProductAnalyticsProviderConfig.from_settings(
        Settings(product_analytics_rollback_mode="all_disabled")
    ).as_redacted_dict()

    assert config["rollback_mode"] == "all_disabled"
    assert config["posthog"]["replay_enabled"] is False
    assert config["campaign_launch_allowed"] is False


def test_posthog_runtime_guard_has_metadata_only_alert_and_fail_closed_rollback() -> None:
    subprocess.run(["bash", "-n", str(GUARD_PATH)], cwd=REPO_ROOT, check=True)
    script = GUARD_PATH.read_text(encoding="utf-8")
    service = GUARD_SERVICE_PATH.read_text(encoding="utf-8")
    timer = GUARD_TIMER_PATH.read_text(encoding="utf-8")

    assert "available_memory_mib < 16384" in script
    assert "disk_free_percent < 10" in script
    assert "analytics_path=\"${GRAF_POSTHOG_ANALYTICS_PATH:-$app_dir}\"" in script
    assert "restart_delta=$((restart_delta + restarts - previous_restarts))" in script
    assert "health_failures >= 2" in script
    assert 'logger -t graf-posthog-runtime-guard' in script
    assert "product_impact=measurement_gap_only" in script
    assert "docker compose --env-file" in script
    assert "rec-api" in script
    assert "api_key" not in script
    assert "secret" not in script.lower()
    assert "EnvironmentFile=-/etc/graf-posthog-runtime-guard.env" in service
    assert "ExecStart=/usr/local/libexec/graf-posthog-runtime-guard.sh" in service
    assert "ProtectSystem=strict" in service
    assert "NoNewPrivileges=true" in service
    assert "OnUnitActiveSec=1min" in timer


def test_posthog_runtime_guard_handles_zero_restart_count_without_exiting(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "docker").write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  ps) printf 'container-1\\n' ;;\n"
        "  inspect) printf 'false 0 1000000000 1073741824\\n' ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    (bin_dir / "curl").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (bin_dir / "logger").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    for executable in bin_dir.iterdir():
        executable.chmod(0o755)

    state_dir = tmp_path / "state"
    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{bin_dir}:{os.defpath}",
            "GRAF_POSTHOG_PROJECT": "graf-posthog",
            "GRAF_APP_DIR": str(tmp_path),
            "GRAF_POSTHOG_ANALYTICS_PATH": str(tmp_path),
            "GRAF_POSTHOG_GUARD_STATE_DIR": str(state_dir),
            "GRAF_POSTHOG_GUARD_AUTO_ROLLBACK": "0",
            "GRAF_POSTHOG_GUARD_DRY_RUN": "1",
            "GRAF_POSTHOG_HEALTH_URL": "http://guard-test.invalid/health",
            "GRAF_READY_URL": "http://guard-test.invalid/ready",
        }
    )
    result = subprocess.run(
        [str(GUARD_PATH)],
        cwd=REPO_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "posthog_guard_restart_count=0" in result.stdout
    assert "posthog_guard_product_impact=measurement_gap_only" in result.stdout


def test_posthog_runtime_guard_rollback_is_atomic_and_has_no_secret_backup(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "docker").write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  ps) printf 'container-1\\n' ;;\n"
        "  inspect) printf 'false 0 1000000000 1073741824\\n' ;;\n"
        "  compose) exit 0 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    (bin_dir / "curl").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    (bin_dir / "logger").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    for executable in bin_dir.iterdir():
        executable.chmod(0o755)

    app_dir = tmp_path / "app"
    (app_dir / "infra").mkdir(parents=True)
    (app_dir / "infra/docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    env_file = app_dir / ".env"
    env_file.write_text(
        "TWOBRAIN_PRODUCT_ANALYTICS_ENABLED=true\n"
        "TWOBRAIN_PRODUCT_ANALYTICS_PROVIDER_MODE=posthog\n"
        "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_ENABLED=true\n"
        "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_WEB_DIRECT_ENABLED=true\n"
        "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_DESKTOP_DIRECT_ENABLED=true\n"
        "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_AUTOCAPTURE_ENABLED=true\n"
        "TWOBRAIN_PRODUCT_ANALYTICS_REPLAY_ENABLED=true\n"
        "TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_ALL_PAGES_ENABLED=true\n"
        "TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_OFFLINE_ENABLED=true\n"
        "TWOBRAIN_PRODUCT_ANALYTICS_VALIDATION_MODE=live_safe\n",
        encoding="utf-8",
    )
    state_dir = tmp_path / "state"
    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{bin_dir}:{os.defpath}",
            "GRAF_POSTHOG_PROJECT": "graf-posthog",
            "GRAF_APP_DIR": str(app_dir),
            "GRAF_ENV_FILE": str(env_file),
            "GRAF_POSTHOG_ANALYTICS_PATH": str(app_dir),
            "GRAF_POSTHOG_GUARD_STATE_DIR": str(state_dir),
            "GRAF_POSTHOG_GUARD_AUTO_ROLLBACK": "1",
            "GRAF_POSTHOG_GUARD_DRY_RUN": "0",
            "GRAF_POSTHOG_GUARD_STOP_STACK": "0",
            "GRAF_POSTHOG_HEALTH_URL": "http://guard-test.invalid/health",
            "GRAF_READY_URL": "http://guard-test.invalid/ready",
        }
    )

    results = [
        subprocess.run(
            [str(GUARD_PATH)],
            cwd=REPO_ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        for _ in range(2)
    ]

    assert all(result.returncode == 0 for result in results), [result.stderr for result in results]
    assert "TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_ENABLED=false" in env_file.read_text(encoding="utf-8")
    assert "TWOBRAIN_PRODUCT_ANALYTICS_REPLAY_ENABLED=false" in env_file.read_text(encoding="utf-8")
    assert "TWOBRAIN_PRODUCT_ANALYTICS_PROVIDER_MODE=disabled" in env_file.read_text(encoding="utf-8")
    assert not list(app_dir.glob(".env.bak"))
    assert any("posthog_guard_rollback=executed" in result.stdout for result in results)
