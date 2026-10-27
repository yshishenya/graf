import os
import subprocess
from pathlib import Path

from tests.contract.test_analytics_degradation_alerting import _capacity_guard_runtime
from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.provider_config import ProductAnalyticsProviderConfig

REPO_ROOT = Path(__file__).parents[4]
ROLLBACK_PATH = REPO_ROOT / "infra/scripts/rollback-product-analytics-providers.sh"
GUARD_PATH = REPO_ROOT / "infra/scripts/posthog-runtime-guard.sh"
GUARD_SERVICE_PATH = REPO_ROOT / "infra/posthog/graf-posthog-runtime-guard.service"
GUARD_TIMER_PATH = REPO_ROOT / "infra/posthog/graf-posthog-runtime-guard.timer"


def test_rollback_script_reports_switches_without_state_change() -> None:
    result = subprocess.run(
        [str(ROLLBACK_PATH), "--metadata-only", "--target", "all"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    output = result.stdout

    assert "provider_rollback_result=pass" in output
    assert "rollback_execution=metadata_only_no_state_change" in output
    assert "provider_state_mutation=not_requested" in output
    assert "operator_executor_hook=not_invoked" in output
    assert "target=all" in output
    assert "product_impact=measurement_gap_only" in output
    assert "posthog_delivery_switch=TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_ENABLED=false" in output
    assert "posthog_stack_stop=metadata_only_no_state_change" in output
    assert "posthog_deploy_dry_run=required_after_switch" in output
    assert "posthog_move_out_failure=restore_endpoint_or_disable_delivery" in output
    assert "yandex_all_pages_switch=TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_ALL_PAGES_ENABLED=false" in output
    assert "yandex_offline_switch=TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_OFFLINE_ENABLED=false" in output
    assert "provider_validation_switch=TWOBRAIN_PRODUCT_ANALYTICS_VALIDATION_MODE=disabled" in output
    assert "normal_product_workflows=preserved" in output
    assert "secrets=not_printed" in output
    assert "execute_confirmed_metadata_only" not in output


def test_dry_run_is_only_a_metadata_only_compatibility_alias() -> None:
    result = subprocess.run(
        [str(ROLLBACK_PATH), "--dry-run", "--target", "all"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "provider_rollback_result=pass" in result.stdout
    assert "rollback_execution=metadata_only_no_state_change" in result.stdout
    assert "provider_state_mutation=not_requested" in result.stdout


def test_metadata_only_never_invokes_a_configured_operator_hook(tmp_path: Path) -> None:
    marker = tmp_path / "hook-invoked"
    hook = tmp_path / "executor.sh"
    hook.write_text(f"#!/usr/bin/env bash\ntouch {marker}\n", encoding="utf-8")
    hook.chmod(0o755)
    environment = os.environ.copy()
    environment["TWOBRAIN_PROVIDER_ROLLBACK_EXECUTOR_HOOK"] = str(hook)
    environment.pop("TWOBRAIN_ALLOW_PROVIDER_ROLLBACK_EXECUTE", None)

    result = subprocess.run(
        [str(ROLLBACK_PATH), "--metadata-only", "--target", "all"],
        cwd=REPO_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "rollback_execution=metadata_only_no_state_change" in result.stdout
    assert "operator_executor_hook=not_invoked" in result.stdout
    assert not marker.exists()


def test_execute_is_fail_closed_without_an_operator_executor_hook() -> None:
    environment = os.environ.copy()
    environment.pop("TWOBRAIN_PROVIDER_ROLLBACK_EXECUTOR_HOOK", None)
    environment["TWOBRAIN_ALLOW_PROVIDER_ROLLBACK_EXECUTE"] = "1"

    result = subprocess.run(
        [str(ROLLBACK_PATH), "--execute", "--target", "all"],
        cwd=REPO_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "provider_rollback_result=blocked" in result.stdout
    assert "rollback_execution=execute_blocked" in result.stdout
    assert "rollback_blocker=missing_operator_executor_hook" in result.stdout
    assert "operator_executor_hook=not_invoked" in result.stdout


def test_execute_requires_explicit_approval_even_when_a_hook_is_configured(tmp_path: Path) -> None:
    hook = tmp_path / "executor.sh"
    hook.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    hook.chmod(0o755)
    environment = os.environ.copy()
    environment.pop("TWOBRAIN_ALLOW_PROVIDER_ROLLBACK_EXECUTE", None)
    environment["TWOBRAIN_PROVIDER_ROLLBACK_EXECUTOR_HOOK"] = str(hook)

    result = subprocess.run(
        [str(ROLLBACK_PATH), "--execute", "--target", "all"],
        cwd=REPO_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "rollback_blocker=missing_explicit_execute_approval" in result.stdout
    assert "operator_executor_hook=not_invoked" in result.stdout


def test_rollback_mode_is_configured_as_measurement_gap_not_product_failure() -> None:
    config = ProductAnalyticsProviderConfig.from_settings(
        Settings(product_analytics_rollback_mode="all_disabled")
    ).as_redacted_dict()

    assert config["rollback_mode"] == "all_disabled"
    assert config["posthog"]["replay_enabled"] is False
    assert config["campaign_launch_allowed"] is False


def test_posthog_runtime_guard_has_metadata_only_alert_and_scoped_rollback() -> None:
    """The guard alert contract, including the analytics/host scope split (T011).

    The thresholds became configurable when the scopes were separated, because a
    site traffic spike must degrade measurement before it degrades the host. The
    literal threshold defaults are asserted instead of inline comparisons, and
    the auto-rollback branch is asserted to depend on analytics-scope reasons
    only.
    """

    subprocess.run(["bash", "-n", str(GUARD_PATH)], cwd=REPO_ROOT, check=True)
    script = GUARD_PATH.read_text(encoding="utf-8")
    service = GUARD_SERVICE_PATH.read_text(encoding="utf-8")
    timer = GUARD_TIMER_PATH.read_text(encoding="utf-8")

    # Storage now comes from the shared collector and capacity evaluator.
    assert 'collector="${GRAF_POSTHOG_STORAGE_COLLECTOR:-$script_dir/measure-posthog-storage-growth.sh}"' in script
    assert 'capacity_helper="$script_dir/posthog-capacity.py"' in script
    assert 'auto_rollback="${GRAF_POSTHOG_GUARD_AUTO_ROLLBACK:-0}"' in script
    assert "restart_delta=$((restart_delta + restarts - previous_restarts))" in script

    # Analytics scope: stricter defaults, evaluation first, measurement only.
    assert 'analytics_health_failure_threshold="${GRAF_POSTHOG_GUARD_ANALYTICS_HEALTH_FAILURES:-1}"' in script
    assert 'analytics_reasons) capacity_analytics_reasons="$value"' in script
    assert 'disable_reasons) capacity_disable_reasons="$value"' in script
    assert "analytics_health_failures >= analytics_health_failure_threshold" in script

    # Host scope: later defaults, alert only, never a measurement rollback.
    assert 'host_memory_mib_threshold="${GRAF_POSTHOG_GUARD_HOST_MEMORY_MIB:-16384}"' in script
    assert 'host_reasons) capacity_host_reasons="$value"' in script
    assert 'host_health_failure_threshold="${GRAF_POSTHOG_GUARD_HOST_HEALTH_FAILURES:-2}"' in script
    assert "available_memory_mib < host_memory_mib_threshold" in script
    assert "health_failures >= host_health_failure_threshold" in script

    # Only analytics-scope reasons may disable measurement.
    assert 'if [[ -n "$analytics_disable_reasons" ]]; then' in script
    assert 'reason=$analytics_disable_reasons' in script
    assert "posthog_guard_analytics_breaches" in script
    assert "posthog_guard_host_breaches" in script
    assert "posthog_guard_breach_scope" in script
    assert "product_impact=measurement_gap_only" in script

    assert 'logger -t graf-posthog-runtime-guard' in script
    assert "docker compose --env-file" in script
    assert "rec-api" in script
    assert "api_key" not in script
    assert "secret" not in script.replace("TWOBRAIN_RUNTIME_SECRET_GID", "").lower()
    assert "EnvironmentFile=-/etc/graf-posthog-runtime-guard.env" in service
    assert (
        "ExecStart=/usr/bin/env "
        "GRAF_POSTHOG_STORAGE_STATE_DIR=/var/lib/graf-posthog-storage "
        "GRAF_POSTHOG_STORAGE_STATE_FILE=/var/lib/graf-posthog-storage/storage-growth-state "
        "/usr/local/libexec/graf-posthog-runtime-guard.sh"
    ) in service
    assert "ProtectSystem=strict" in service
    assert "NoNewPrivileges=true" in service
    assert "OnUnitActiveSec=1min" in timer


def test_posthog_runtime_guard_handles_zero_restart_count_without_exiting(tmp_path: Path) -> None:
    environment, _, _ = _capacity_guard_runtime(tmp_path)
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
    environment, _, _ = _capacity_guard_runtime(tmp_path)
    env_file = Path(environment["GRAF_ENV_FILE"])
    initial_keys = {line.split("=", 1)[0] for line in env_file.read_text().splitlines()}
    sentinel = "synthetic-private-value-do-not-export"
    with env_file.open("a") as stream:
        stream.write(f"UNRELATED_SETTING={sentinel}\n")
    # Trigger the real health failure; the reused double reads Config.Env from
    # the file after the switch and reports the running API container id.
    (tmp_path / "bin/curl").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    results = [
        subprocess.run(
            [str(GUARD_PATH)], cwd=REPO_ROOT, env=environment,
            check=False, capture_output=True, text=True,
        )
        for _ in range(2)
    ]

    assert all(result.returncode == 0 for result in results), [
        (result.stdout, result.stderr) for result in results
    ]
    lines = env_file.read_text().splitlines()
    values = dict(line.split("=", 1) for line in lines)
    assert len(values) == len(lines)
    assert set(values) == initial_keys | {"UNRELATED_SETTING"}
    assert values["UNRELATED_SETTING"] == sentinel
    for key, value in values.items():
        if key.startswith("TWOBRAIN_PRODUCT_ANALYTICS_"):
            assert value == ("false" if key.endswith("ENABLED") else "disabled")
    assert env_file.stat().st_mode & 0o777 == 0o600
    assert not list(tmp_path.glob(".env.bak*"))
    assert not list(tmp_path.glob(".env.guard.*"))
    assert "posthog_guard_rollback=executed" in results[0].stdout
    assert "posthog_guard_rollback=already_protected" in results[1].stdout
    assert (tmp_path / "restart-log").read_text().splitlines() == ["restart"]
    for result in results:
        assert "posthog_guard_protection_status=protected" in result.stdout
        assert sentinel not in result.stdout + result.stderr
    assert all(sentinel not in path.read_text() for path in (tmp_path / "guard").iterdir())
