"""Contract tests for analytics degradation alerting (SC-009, T023).

The analytics measurement stack must keep working while the product serves a
traffic spike, so the runtime guard splits its thresholds into two scopes:

* the analytics scope fires first and may disable measurement only;
* the host scope never disables measurement on its own.

The external alert must leave the server within fifteen minutes, carry no
visitor or user data, and its own channel must be probed by an independent path.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from twobrain_rec_server.product_analytics import provider_readiness

REPO_ROOT = Path(__file__).parents[4]
GUARD_PATH = REPO_ROOT / "infra/scripts/posthog-runtime-guard.sh"
GUARD_ENV_EXAMPLE = REPO_ROOT / "infra/posthog/runtime-guard.env.example"
ALERT_PATH = REPO_ROOT / "infra/scripts/alert-analytics-degradation.sh"
ALERT_ENV_EXAMPLE = REPO_ROOT / "infra/posthog/alert-analytics-degradation.env.example"
RULES_PATH = REPO_ROOT / "infra/posthog/alert-rules.txt"
UNIT_DIR = REPO_ROOT / "infra/posthog"
RUNBOOK_PATH = REPO_ROOT / "docs/analytics/product-analytics-posthog-runbook.md"
BACKUP_RESTORE_PATH = REPO_ROOT / "infra/posthog/backup-restore.md"

RULE_SCOPES = {"analytics", "host", "backup", "restore", "retention", "alerting"}
RULE_OWNER_ROLES = {"infra_operator", "analytics_operator", "product_owner"}
RULE_SEVERITIES = {"critical", "warning"}
BASH = shutil.which("bash") or "/bin/bash"


def _guard_breach_codes() -> set[str]:
    script = GUARD_PATH.read_text(encoding="utf-8")
    codes = set(re.findall(r'add_(?:analytics_breach|analytics_disable|host_breach)\s+"([a-z0-9_]+)"', script))
    codes |= set(re.findall(r'\$\{(?:sensor_failure|host_sensor_failure):-([a-z0-9_]+)\}', script))
    codes |= set(re.findall(r'host_sensor_failure="([a-z0-9_]+)"', script))
    return codes


def _alert_reason_codes() -> set[str]:
    script = ALERT_PATH.read_text(encoding="utf-8")
    codes = set(re.findall(r'reasons\+=\("([a-z0-9_]+)"\)', script))
    # A channel outage maps to one rule; the specific probe reasons stay local
    # to the channel-check output but still require owner mappings.
    codes.update({"alert_channel_unavailable", "last_delivery_missing", "last_delivery_stale"})
    return codes


def _readiness_blocker_codes() -> set[str]:
    codes = set()
    for name in dir(provider_readiness):
        if name.startswith("BLOCKER_"):
            codes.add(getattr(provider_readiness, name).split(":")[0])
    return codes


def _rule_lines() -> list[dict[str, str]]:
    rules = []
    for line in RULES_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("rule "):
            continue
        rules.append(dict(field.split("=", 1) for field in stripped.split()[1:] if "=" in field))
    return rules


def _rule_map() -> dict[str, dict[str, str]]:
    return {rule["code"]: rule for rule in _rule_lines()}


def _write_state(path: Path, lines: list[str]) -> None:
    if path.name == "guard-state":
        # Normal alert fixtures represent the current complete writer schema.
        lines = ["alert_state_version=2", "capacity_ready=true", "protection_status=observed", *lines]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _valid_operations_state(directory: Path, *, now: int) -> dict[str, Path]:
    backup = directory / "backup-state"
    _write_state(
        backup,
        [
            "backup_state_version=2",
                "backup_set_complete=true",
            "last_attempt_result=pass",
            "last_success_at=recent",
            f"last_success_epoch={now - 3600}",
            "copies_local=7",
        ],
    )
    restore = directory / "restore-state"
    _write_state(
        restore,
        [
            "restore_state_version=1",
            "last_verify_result=pass",
            f"last_verify_epoch={now - 86400}",
        ],
    )
    retention = directory / "retention-state"
    _write_state(
        retention,
        [
            "retention_state_version=2",
                f"recorded_at_epoch={now}",
            "result=pass",
            "category=measurement_events retention_mode=until_decision retention_days=none storage=clickhouse enforcement=decision_required "
            "last_enforced_at=recent rows_deleted=0 enforcement_verified=true",
            "category=anonymous_aggregate retention_mode=until_decision retention_days=none storage=postgres enforcement=decision_required "
            "last_enforced_at=recent rows_deleted=1 enforcement_verified=true",
            "category=visit_attribution retention_mode=until_decision retention_days=none storage=postgres enforcement=decision_required "
            "last_enforced_at=recent rows_deleted=1 enforcement_verified=true",
            "category=acquisition_attribute retention_mode=until_decision retention_days=none storage=postgres enforcement=decision_required "
            "last_enforced_at=recent rows_deleted=1 enforcement_verified=true",
        ],
    )
    return {"backup": backup, "restore": restore, "retention": retention}


def _alert_environment(tmp_path: Path, state: dict[str, Path], *, token: str = "111111:TESTTOKEN", chat: str = "424242"):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    curl_log = tmp_path / "curl.log"
    curl = bin_dir / "curl"
    curl.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$*" >> "$CURL_LOG"\n'
        'if [ -n "$CURL_FAIL" ]; then exit 7; fi\n'
        "printf '{\"ok\":true}\\n200'\n",
        encoding="utf-8",
    )
    curl.chmod(0o755)
    environment = {
        "PATH": f"{bin_dir}:{Path(BASH).parent}:/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(tmp_path),
        "CURL_LOG": str(curl_log),
        "GRAF_ANALYTICS_ALERT_STATE_DIR": str(tmp_path / "alert-state"),
        "GRAF_ANALYTICS_GUARD_STATE_FILE": str(tmp_path / "guard-state"),
        "GRAF_ANALYTICS_BACKUP_STATE_FILE": str(state["backup"]),
        "GRAF_ANALYTICS_RESTORE_STATE_FILE": str(state["restore"]),
        "GRAF_ANALYTICS_RETENTION_STATE_FILE": str(state["retention"]),
        "GRAF_ANALYTICS_ALERT_RULES_FILE": str(RULES_PATH),
        "GRAF_ANALYTICS_ALERT_BOT_TOKEN": token,
        "GRAF_ANALYTICS_ALERT_CHAT_ID": chat,
        "GRAF_ANALYTICS_ALERT_OWNER_ANALYTICS_OPERATOR": "analytics-oncall",
        "GRAF_ANALYTICS_ALERT_OWNER_INFRA_OPERATOR": "infra-oncall",
        "GRAF_ANALYTICS_ALERT_OWNER_PRODUCT_OWNER": "product-oncall",
    }
    return environment, curl_log


def _run_alert(environment: dict[str, str], *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [BASH, str(ALERT_PATH), *arguments],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )


def test_guard_splits_analytics_and_host_scopes() -> None:
    subprocess.run([BASH, "-n", str(GUARD_PATH)], cwd=REPO_ROOT, check=True)
    script = GUARD_PATH.read_text(encoding="utf-8")

    # Analytics scope fires first, with thresholds deliberately stricter than the
    # host scope so measurement degrades before the whole host does.
    assert 'analytics_health_failure_threshold="${GRAF_POSTHOG_GUARD_ANALYTICS_HEALTH_FAILURES:-1}"' in script
    assert 'capacity_helper="$script_dir/posthog-capacity.py"' in script
    assert 'analytics_lag_seconds_threshold="${GRAF_POSTHOG_GUARD_ANALYTICS_LAG_SECONDS:-900}"' in script
    assert 'analytics_queue_depth_threshold="${GRAF_POSTHOG_GUARD_ANALYTICS_QUEUE_DEPTH:-100000}"' in script
    assert 'analytics_queue_growth_threshold="${GRAF_POSTHOG_GUARD_ANALYTICS_QUEUE_GROWTH_PER_MIN:-5000}"' in script
    assert 'analytics_strict_metrics="${GRAF_POSTHOG_GUARD_ANALYTICS_STRICT_METRICS:-0}"' in script

    # Host scope keeps its own, later thresholds.
    assert 'host_load_threshold="${GRAF_POSTHOG_GUARD_HOST_LOAD:-11}"' in script
    assert 'host_memory_mib_threshold="${GRAF_POSTHOG_GUARD_HOST_MEMORY_MIB:-16384}"' in script
    assert 'host_health_failure_threshold="${GRAF_POSTHOG_GUARD_HOST_HEALTH_FAILURES:-2}"' in script

    # The two scopes are recorded separately and the product keeps running.
    assert 'add_host_breach "host_load"' in script
    assert 'add_host_breach "host_memory"' in script
    assert 'host_reasons) capacity_host_reasons="$value"' in script
    assert "posthog_guard_analytics_breaches" in script
    assert "posthog_guard_host_breaches" in script
    assert "posthog_guard_breach_scope" in script
    assert "product_impact=measurement_gap_only" in script
    assert "rec-api" in script


def test_guard_disables_measurement_only_from_analytics_scope() -> None:
    script = GUARD_PATH.read_text(encoding="utf-8")

    assert 'if [[ -n "$analytics_disable_reasons" ]]; then' in script
    assert 'reason=$analytics_disable_reasons' in script
    assert "host_breaches" in script
    # A host breach must never reach the rollback branch.
    rollback_section = script.split('if [[ -n "$analytics_disable_reasons" ]]; then', 1)[1]
    assert "host_breaches" not in rollback_section.split("\nfi\n", 1)[0]
    # Auto-rollback is opt-in and dry-run remains the default.
    assert 'auto_rollback="${GRAF_POSTHOG_GUARD_AUTO_ROLLBACK:-0}"' in script
    assert 'dry_run="${GRAF_POSTHOG_GUARD_DRY_RUN:-1}"' in script


def test_guard_keeps_legacy_environment_names_for_production() -> None:
    script = GUARD_PATH.read_text(encoding="utf-8")

    # Every production variable that existed before the scope split still works.
    for legacy in (
        "GRAF_POSTHOG_PROJECT",
        "GRAF_APP_DIR",
        "GRAF_ENV_FILE",
        "GRAF_POSTHOG_GUARD_STATE_DIR",
        "GRAF_POSTHOG_GUARD_DRY_RUN",
        "GRAF_POSTHOG_GUARD_AUTO_ROLLBACK",
        "GRAF_POSTHOG_GUARD_STOP_STACK",
        "GRAF_POSTHOG_HEALTH_URL",
        "GRAF_READY_URL",
    ):
        assert legacy in script, legacy
    assert 'GRAF_POSTHOG_ANALYTICS_PATH' in (REPO_ROOT / 'infra/scripts/posthog-storage.py').read_text()
    assert "restart_delta=$((restart_delta + restarts - previous_restarts))" in script
    assert 'logger -t graf-posthog-runtime-guard' in script
    assert "docker compose --env-file" in script
    assert "api_key" not in script
    # The existing reader-group name is metadata, not access to a credential.
    assert "secret" not in script.replace("TWOBRAIN_RUNTIME_SECRET_GID", "").lower()

    example = GUARD_ENV_EXAMPLE.read_text(encoding="utf-8")
    for name in (
        "GRAF_POSTHOG_GUARD_ANALYTICS_HEALTH_FAILURES",
        "GRAF_POSTHOG_GUARD_ANALYTICS_LAG_SECONDS",
        "GRAF_POSTHOG_GUARD_ANALYTICS_QUEUE_DEPTH",
        "GRAF_POSTHOG_GUARD_ANALYTICS_QUEUE_GROWTH_PER_MIN",
        "GRAF_POSTHOG_GUARD_HOST_LOAD",
        "GRAF_POSTHOG_GUARD_HOST_MEMORY_MIB",
        "GRAF_POSTHOG_GUARD_HOST_HEALTH_FAILURES",
    ):
        assert name in example, name
    assert "host scope alone alerts only" in example


def test_alert_script_reads_credentials_outside_the_repository() -> None:
    subprocess.run([BASH, "-n", str(ALERT_PATH)], cwd=REPO_ROOT, check=True)
    script = ALERT_PATH.read_text(encoding="utf-8")

    assert 'GRAF_ANALYTICS_ALERT_BOT_TOKEN_FILE' in script
    assert 'GRAF_ANALYTICS_ALERT_CHAT_ID_FILE' in script
    assert "read_value_file" in script
    assert "redact()" in script
    assert "alert_secrets=not_printed" in script
    assert "alert_delivery_deadline_minutes=15" in script

    # No committed credential: no Telegram token shape anywhere in the alert
    # surface, and the example file carries empty values only.
    token_pattern = re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{20,}\b")
    assert not token_pattern.search(script)
    example = ALERT_ENV_EXAMPLE.read_text(encoding="utf-8")
    assert not token_pattern.search(example)
    for line in example.splitlines():
        if line.startswith(("GRAF_ANALYTICS_ALERT_BOT_TOKEN=", "GRAF_ANALYTICS_ALERT_CHAT_ID=")):
            assert line.endswith("="), line
    assert not token_pattern.search(RULES_PATH.read_text(encoding="utf-8"))


def test_alert_delivers_scope_aware_metadata_only_message(tmp_path: Path) -> None:
    now = int(time.time())
    state = _valid_operations_state(tmp_path, now=now)
    guard_state = tmp_path / "guard-state"
    _write_state(
        guard_state,
        [
            "version=1",
            f"recorded_at_epoch={now}",
            "result=alert",
            "breach_scope=analytics",
            "analytics_breaches=analytics_queue_depth",
            "host_breaches=none",
            "measurement_action=applied",
        ],
    )
    environment, curl_log = _alert_environment(tmp_path, state)

    result = _run_alert(environment)

    assert result.returncode == 0, result.stderr
    assert "alert_result=delivered" in result.stdout
    assert "alert_reasons=analytics_queue_depth" in result.stdout
    assert "alert_scope=analytics" in result.stdout
    assert "alert_transport=telegram" in result.stdout
    assert "alert_delivery_deadline_minutes=15" in result.stdout
    assert "alert_secrets=not_printed" in result.stdout

    payload = curl_log.read_text(encoding="utf-8")
    # The transport URL carries the bot token by the Telegram API contract; the
    # alert text itself must never carry a credential.
    message = payload.split("--data-urlencode text=", 1)[1].split(" --data ", 1)[0]
    assert "analytics_queue_depth" in message
    assert "delivery_deadline_minutes: 15" in message
    assert "analytics-oncall" in message
    assert "measurement gap only" in message
    # Nothing about visitors, users or accounts may travel with the alert.
    for forbidden in ("visitor", "user_id", "account_id", "email", "session_id", "ip_address", "distinct_id"):
        assert forbidden not in message.lower(), forbidden
    assert environment["GRAF_ANALYTICS_ALERT_BOT_TOKEN"] not in message
    assert environment["GRAF_ANALYTICS_ALERT_BOT_TOKEN"] not in result.stdout
    assert environment["GRAF_ANALYTICS_ALERT_BOT_TOKEN"] not in result.stderr

    delivery_state = (tmp_path / "alert-state" / "last-delivery").read_text(encoding="utf-8")
    assert "transport=telegram" in delivery_state
    assert environment["GRAF_ANALYTICS_ALERT_BOT_TOKEN"] not in delivery_state


def test_alert_suppresses_repeats_and_keeps_the_deadline_visible(tmp_path: Path) -> None:
    now = int(time.time())
    state = _valid_operations_state(tmp_path, now=now)
    _write_state(
        tmp_path / "guard-state",
        [
            f"recorded_at_epoch={now}",
            "result=alert",
            "breach_scope=analytics",
            "analytics_breaches=analytics_storage",
            "host_breaches=none",
        ],
    )
    environment, curl_log = _alert_environment(tmp_path, state)

    first = _run_alert(environment)
    assert "alert_result=delivered" in first.stdout
    calls_after_first = len(curl_log.read_text(encoding="utf-8").splitlines())

    second = _run_alert(environment)
    assert second.returncode == 0
    assert "alert_result=suppressed" in second.stdout
    assert "alert_reasons=analytics_storage" in second.stdout
    assert len(curl_log.read_text(encoding="utf-8").splitlines()) == calls_after_first

    status = _run_alert(environment, "--status")
    assert "alert_channel=" in status.stdout
    assert "alert_last_delivery=" in status.stdout


def test_alert_dry_run_never_contacts_the_external_channel(tmp_path: Path) -> None:
    now = int(time.time())
    state = _valid_operations_state(tmp_path, now=now)
    _write_state(
        tmp_path / "guard-state",
        [f"recorded_at_epoch={now}", "result=alert", "analytics_breaches=analytics_storage", "host_breaches=none"],
    )
    environment, curl_log = _alert_environment(tmp_path, state)

    result = _run_alert(environment, "--dry-run")

    assert result.returncode == 0, result.stderr
    assert "alert_result=dry_run" in result.stdout
    assert "alert_transport=none" in result.stdout
    assert "analytics_storage" in result.stdout
    assert "delivery_deadline_minutes: 15" in result.stdout
    assert not curl_log.exists()


def test_alert_drill_verifies_the_channel_without_a_degradation(tmp_path: Path) -> None:
    now = int(time.time())
    state = _valid_operations_state(tmp_path, now=now)
    _write_state(tmp_path / "guard-state", [f"recorded_at_epoch={now}", "result=pass"])
    environment, curl_log = _alert_environment(tmp_path, state)

    result = _run_alert(environment, "--drill")

    assert result.returncode == 0, result.stderr
    assert "alert_result=drill_delivered" in result.stdout
    assert "alert_delivery_deadline_minutes=15" in result.stdout
    assert "TRAINING ALERT" in curl_log.read_text(encoding="utf-8")
    assert (tmp_path / "alert-state" / "last-drill").exists()


def test_alert_channel_outage_is_detected_independently(tmp_path: Path) -> None:
    now = int(time.time())
    state = _valid_operations_state(tmp_path, now=now)

    # A missing token must be reported locally without any outbound call.
    environment, curl_log = _alert_environment(tmp_path, state, token="", chat="")
    missing = _run_alert(environment, "--check-channel")
    assert missing.returncode == 1
    assert "alert_channel_result=fail" in missing.stdout
    assert "alert_channel_reason=bot_token_unset" in missing.stdout
    assert "alert_channel_independent_detection=journald_and_channel_state_file" in missing.stdout

    channel_state = (tmp_path / "alert-state" / "channel-state").read_text(encoding="utf-8")
    assert "result=fail" in channel_state
    assert "reason=bot_token_unset" in channel_state

    # A reachable process with an unreachable API is also a channel outage, and
    # the independent probe reports it instead of pretending delivery works.
    environment, curl_log = _alert_environment(tmp_path, state)
    environment["CURL_FAIL"] = "1"
    unreachable = _run_alert(environment, "--check-channel")
    assert unreachable.returncode == 1
    assert "alert_channel_result=fail" in unreachable.stdout
    assert "alert_channel_reason=channel_api_unreachable" in unreachable.stdout
    assert curl_log.exists()

    # A fresh guard state and a working channel pass.
    environment.pop("CURL_FAIL")
    _write_state(tmp_path / "guard-state", [f"recorded_at_epoch={now}", "result=pass"])
    healthy = _run_alert(environment, "--check-channel")
    assert healthy.returncode == 0, healthy.stderr
    assert "alert_channel_result=pass" in healthy.stdout


def test_alert_channel_allows_first_run_without_last_delivery_file(tmp_path: Path) -> None:
    now = int(time.time())
    state = _valid_operations_state(tmp_path, now=now)
    _write_state(tmp_path / "guard-state", [f"recorded_at_epoch={now}", "result=pass"])
    environment, _ = _alert_environment(tmp_path, state)

    result = _run_alert(environment, "--check-channel")

    assert result.returncode == 0, result.stderr
    assert "alert_channel_result=pass" in result.stdout
    assert "alert_channel_reason=none" in result.stdout
    channel_state = (tmp_path / "alert-state" / "channel-state").read_text(encoding="utf-8")
    assert "first_run_grace_status=active" in channel_state
    assert "last_delivery_status=first_run_grace" in channel_state
    assert "last_delivery_missing" not in channel_state


def test_alert_channel_fails_closed_when_last_delivery_file_is_missing_after_grace(tmp_path: Path) -> None:
    now = int(time.time())
    state = _valid_operations_state(tmp_path, now=now)
    _write_state(tmp_path / "guard-state", [f"recorded_at_epoch={now}", "result=pass"])
    alert_state_dir = tmp_path / "alert-state"
    alert_state_dir.mkdir()
    _write_state(
        alert_state_dir / "channel-state",
        [
            "channel_state_version=1",
            f"checked_at_epoch={now - 3600}",
            f"first_checked_at_epoch={now - 3600}",
            "result=pass",
        ],
    )
    environment, _ = _alert_environment(tmp_path, state)

    result = _run_alert(environment, "--check-channel")

    assert result.returncode == 1
    assert "alert_channel_result=fail" in result.stdout
    assert "alert_channel_reason=last_delivery_missing" in result.stdout
    channel_state = (alert_state_dir / "channel-state").read_text(encoding="utf-8")
    assert "reason=last_delivery_missing" in channel_state
    assert "last_delivery_status=missing" in channel_state


def test_alert_channel_fails_closed_when_last_delivery_file_is_stale(tmp_path: Path) -> None:
    now = int(time.time())
    state = _valid_operations_state(tmp_path, now=now)
    _write_state(tmp_path / "guard-state", [f"recorded_at_epoch={now}", "result=pass"])
    alert_state_dir = tmp_path / "alert-state"
    alert_state_dir.mkdir()
    _write_state(
        alert_state_dir / "channel-state",
        [
            "channel_state_version=1",
            f"checked_at_epoch={now - 3600}",
            f"first_checked_at_epoch={now - 3600}",
            "result=pass",
        ],
    )
    _write_state(
        alert_state_dir / "last-delivery",
        [
            "delivery_state_version=1",
            f"sent_at_epoch={now - 3600}",
            "transport=telegram",
            "result=alert",
        ],
    )
    environment, _ = _alert_environment(tmp_path, state)

    result = _run_alert(environment, "--check-channel")

    assert result.returncode == 1
    assert "alert_channel_result=fail" in result.stdout
    assert "alert_channel_reason=last_delivery_stale" in result.stdout
    channel_state = (alert_state_dir / "channel-state").read_text(encoding="utf-8")
    assert "reason=last_delivery_stale" in channel_state
    assert "last_delivery_status=stale" in channel_state


def test_alert_labels_a_mixed_breach_list_with_both_scopes(tmp_path: Path) -> None:
    now = int(time.time())
    state = _valid_operations_state(tmp_path, now=now)
    _write_state(
        tmp_path / "guard-state",
        [
            f"recorded_at_epoch={now}",
            "result=alert",
            "breach_scope=analytics+host",
            "analytics_breaches=analytics_queue_depth,container_restarts",
            "host_breaches=host_disk",
            "measurement_action=disabled",
        ],
    )
    environment, _ = _alert_environment(tmp_path, state)

    result = _run_alert(environment, "--dry-run")

    assert result.returncode == 0, result.stderr
    assert "scope: analytics+host" in result.stdout
    assert "analytics_queue_depth" in result.stdout
    assert "container_restarts" in result.stdout
    assert "host_disk" in result.stdout
    assert "analytics-oncall" in result.stdout
    assert "infra-oncall" in result.stdout
    assert "alert_owner_unnamed" not in result.stdout


def test_alert_uses_the_fallback_transport_when_the_primary_channel_is_unavailable(tmp_path: Path) -> None:
    now = int(time.time())
    state = _valid_operations_state(tmp_path, now=now)
    _write_state(
        tmp_path / "guard-state",
        [f"recorded_at_epoch={now}", "result=alert", "analytics_breaches=analytics_storage"],
    )
    environment, curl_log = _alert_environment(tmp_path, state, token="", chat="")
    environment["GRAF_ANALYTICS_ALERT_FALLBACK_URL"] = "https://fallback.example.test/hook"

    result = _run_alert(environment)

    assert result.returncode == 0, result.stderr
    assert "alert_result=delivered" in result.stdout
    assert "alert_transport=fallback" in result.stdout
    assert "https://fallback.example.test/hook" in curl_log.read_text(encoding="utf-8")


def test_alert_reports_a_stale_guard_as_degradation(tmp_path: Path) -> None:
    now = int(time.time())
    state = _valid_operations_state(tmp_path, now=now)
    _write_state(
        tmp_path / "guard-state",
        [f"recorded_at_epoch={now - 3600}", "result=pass"],
    )
    environment, _ = _alert_environment(tmp_path, state)

    result = _run_alert(environment, "--dry-run")

    assert "alert_reasons=guard_state_stale" in result.stdout


def test_every_alert_code_has_an_owner_rule() -> None:
    rules = _rule_map()
    assert rules, "alert rules file is empty"

    for code, rule in rules.items():
        assert rule.get("scope") in RULE_SCOPES, code
        assert rule.get("owner_role") in RULE_OWNER_ROLES, code
        assert rule.get("severity") in RULE_SEVERITIES, code
        assert rule.get("escalate_after_minutes", "").isdigit(), code
        assert rule.get("requirement", "").startswith("FR-"), code

    # Every code the guard, the alert path and the readiness report can emit has
    # a named owner role.
    for code in sorted(_guard_breach_codes() | _alert_reason_codes() | _readiness_blocker_codes()):
        assert code in rules, f"alert rule missing for {code}"

    # Roles only: the person behind a role is named outside the repository.
    text = RULES_PATH.read_text(encoding="utf-8")
    assert "@" not in text
    assert not re.search(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", text.replace("GRAF product", ""))


def test_scheduled_alerting_units_exist_with_the_reviewed_cadence() -> None:
    expected = {
        "graf-analytics-degradation-alert.timer": "OnUnitActiveSec=5min",
        "graf-analytics-alert-channel-check.timer": "OnUnitActiveSec=15min",
        "graf-posthog-backup.timer": "OnCalendar=*-*-* 02:30:00",
        "graf-posthog-restore-verify.timer": "OnCalendar=*-*-01,15 04:30:00",
        "graf-posthog-retention-enforce.timer": "OnCalendar=*-*-* 03:15:00",
    }
    for name, schedule in expected.items():
        timer = (UNIT_DIR / name).read_text(encoding="utf-8")
        assert schedule in timer, name
        assert "Persistent=true" in timer, name
        assert "WantedBy=timers.target" in timer, name

    for name in ("graf-analytics-degradation-alert.service", "graf-analytics-alert-channel-check.service"):
        service = (UNIT_DIR / name).read_text(encoding="utf-8")
        assert "ExecStart=/usr/local/libexec/" in service, name
        assert "EnvironmentFile=-/etc/graf-analytics-alert.env" in service, name
        assert "ProtectSystem=strict" in service, name
        assert "NoNewPrivileges=true" in service, name
        assert "User=root" in service, name

    # The delivery deadline is at most fifteen minutes (SC-009), so the timer
    # must fire well inside that window.
    assert "OnUnitActiveSec=5min" in (UNIT_DIR / "graf-analytics-degradation-alert.timer").read_text(encoding="utf-8")


def test_documentation_keeps_the_scope_split_and_the_delivery_deadline() -> None:
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")
    assert "Threshold Scopes: Analytics First, Host Second" in runbook
    assert "Alert Rules And Named Owners" in runbook
    assert "Two Operators And Mandatory Second Factor" in runbook
    assert "Operator Change And Access Revocation Procedure" in runbook
    assert "Analytics Readiness Blockers" in runbook
    assert "alert-analytics-degradation.sh" in runbook
    assert "graf-analytics-alert-channel-check.timer" in runbook
    assert "15 minutes" in runbook

    backup_restore = BACKUP_RESTORE_PATH.read_text(encoding="utf-8")
    assert "What A Restore Recreates And What Is Lost" in backup_restore
    assert "infra/scripts/backup-posthog.sh" in backup_restore
    assert "infra/scripts/verify-posthog-restore.sh" in backup_restore


@pytest.mark.parametrize("path", [GUARD_PATH, ALERT_PATH])
def test_operational_scripts_run_under_the_system_shell(path: Path) -> None:
    result = subprocess.run([BASH, "-n", str(path)], cwd=REPO_ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

def test_guard_alert_state_keys_match_the_alert_reader() -> None:
    guard = GUARD_PATH.read_text(encoding="utf-8")
    alert = ALERT_PATH.read_text(encoding="utf-8")

    writer = guard.split("alert_state_version=2", 1)[1].split('} > "$tmp_alert_state"', 1)[0]
    written = set(re.findall(r"printf '([a-z0-9_]+)=", writer))
    for key in (
        "recorded_at_epoch",
        "result",
        "breach_scope",
        "analytics_scope",
        "host_scope",
        "analytics_breaches",
        "host_breaches",
        "analytics_disable_reasons",
        "measurement_action",
        "product_impact",
    ):
        assert key in written, key

    reader = alert.split("metrics_summary()", 1)[1].split("\n}", 1)[0]
    for key in set(re.findall(r'state_value "\$guard_state_file" ([a-z0-9_]+)', reader)):
        assert key in written, key

    for key in ("recorded_at_epoch", "result", "analytics_breaches", "host_breaches", "measurement_action"):
        assert re.search(rf'state_values? "\$guard_state_file" {key}\b', alert), key


def test_guard_state_feeds_the_alert_end_to_end(tmp_path: Path) -> None:
    """The guard's real state file must drive a delivered, owner-resolved alert."""

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
    (bin_dir / "curl").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    (bin_dir / "logger").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    for executable in bin_dir.iterdir():
        executable.chmod(0o755)

    guard_state_dir = tmp_path / "guard-state-dir"
    guard_environment = {
        "PATH": f"{bin_dir}:{Path(sys.executable).parent}:{os.defpath}",
        "HOME": str(tmp_path),
        "GRAF_POSTHOG_PROJECT": "graf-posthog",
        "GRAF_APP_DIR": str(tmp_path),
        "GRAF_POSTHOG_ANALYTICS_PATH": str(tmp_path),
        "GRAF_POSTHOG_GUARD_STATE_DIR": str(guard_state_dir),
        "GRAF_POSTHOG_GUARD_AUTO_ROLLBACK": "0",
        "GRAF_POSTHOG_GUARD_DRY_RUN": "1",
        "GRAF_POSTHOG_HEALTH_URL": "http://guard-test.invalid/health",
        "GRAF_READY_URL": "http://guard-test.invalid/ready",
    }
    guard = subprocess.run(
        [BASH, str(GUARD_PATH)], cwd=REPO_ROOT, env=guard_environment, capture_output=True, text=True
    )

    assert guard.returncode == 0, guard.stderr
    assert "analytics_node_unavailable" in guard.stdout
    state_text = (guard_state_dir / "alert-state").read_text(encoding="utf-8")
    assert "result=alert" in state_text
    assert re.search(r"breach_scope=analytics(\+host)?", state_text)
    assert "analytics_node_unavailable" in state_text
    assert "analytics_disable_reasons=" in state_text
    assert "measurement_action=" in state_text
    assert "product_impact=measurement_gap_only" in state_text

    now = int(time.time())
    operations = _valid_operations_state(tmp_path, now=now)
    environment, curl_log = _alert_environment(tmp_path, operations)
    environment["GRAF_ANALYTICS_GUARD_STATE_FILE"] = str(guard_state_dir / "alert-state")
    environment["GRAF_ANALYTICS_ALERT_STATE_DIR"] = str(tmp_path / "alert-state-dir")

    result = _run_alert(environment)

    assert result.returncode == 0, result.stderr
    assert "alert_result=delivered" in result.stdout
    assert "analytics_node_unavailable" in result.stdout
    assert re.search(r"alert_scope=analytics", result.stdout)
    assert "guard_state_missing" not in result.stdout
    assert "guard_state_stale" not in result.stdout

    assert "alert_owner_unnamed" not in result.stdout
    message = (
        curl_log.read_text(encoding="utf-8")
        .split("--data-urlencode text=", 1)[1]
        .split(" --data ", 1)[0]
    )
    assert "analytics_node_unavailable" in message
    assert "analytics-oncall" in message
    assert "delivery_deadline_minutes: 15" in message


def _capacity_guard_runtime(tmp_path: Path):
    from tests.contract.test_analytics_retention_enforcement import _capacity_inputs
    capacity, sample, budget, _ = _capacity_inputs()
    now = int(time.time())
    sample['recorded_at_epoch'] = now
    budget.update(accepted_at_epoch=now - 1, review_deadline_epoch=now + 3600)
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    (bin_dir / 'docker').write_text(f'#!{sys.executable}\n' + '''
import json, os, pathlib, sys
args = sys.argv[1:]
if args[0] == 'ps':
    print('analytics-container')
elif args[0] == 'exec':
    print(0)
elif args[0] == 'compose':
    if 'up' in args:
        with open(os.environ['RESTART_LOG'], 'a') as stream: stream.write('restart\\n')
        raise SystemExit(7 if os.environ.get('FAIL_RESTART') else 0)
    if 'ps' in args: print('api-container')
elif args[0] == 'inspect':
    if '.Config.Env' in args[2]:
        values = pathlib.Path(os.environ['GRAF_ENV_FILE']).read_text().splitlines()
        if os.environ.get('FAIL_READBACK'): values = []
        print(json.dumps(values))
    else:
        print('false 0 1000000000 1073741824')
''')
    for name in ('curl', 'logger', 'collector'):
        (bin_dir / name).write_text('#!/bin/sh\nexit 0\n')
    for p in bin_dir.iterdir():
        p.chmod(0o755)
    (tmp_path / 'infra').mkdir()
    (tmp_path / 'infra/docker-compose.yml').write_text('services: {}\n')
    env_file = tmp_path / '.env'
    env_file.write_text('\n'.join(key + '=true' for key in capacity.DISABLED_ENV) + '\n')
    state = tmp_path / 'storage.state'
    state.with_suffix('.json').write_text(json.dumps(sample))
    budget_path = tmp_path / 'budget.json'
    budget_path.write_text(json.dumps(budget))
    environment = {
        'PATH': f'{bin_dir}:{Path(sys.executable).parent}:{os.defpath}',
        'HOME': str(tmp_path), 'GRAF_APP_DIR': str(tmp_path),
        'GRAF_ENV_FILE': str(env_file), 'GRAF_POSTHOG_STORAGE_STATE_FILE': str(state),
        'GRAF_POSTHOG_STORAGE_COLLECTOR': str(bin_dir / 'collector'),
        'GRAF_POSTHOG_CAPACITY_BUDGET_FILE': str(budget_path),
        'GRAF_POSTHOG_GUARD_CONFIG_VERSION': 'd' * 64,
        'GRAF_POSTHOG_GUARD_STATE_DIR': str(tmp_path / 'guard'),
        'GRAF_POSTHOG_GUARD_AUTO_ROLLBACK': '1', 'GRAF_POSTHOG_GUARD_DRY_RUN': '0',
        'GRAF_POSTHOG_HEALTH_URL': 'https://guard-test.invalid/health',
        'GRAF_READY_URL': 'https://guard-test.invalid/ready',
        'RESTART_LOG': str(tmp_path / 'restart-log'),
    }
    return environment, sample, state.with_suffix('.json')


def test_guard_persists_one_successful_transition_and_does_not_auto_restore(tmp_path: Path):
    environment, sample, sample_path = _capacity_guard_runtime(tmp_path)
    sample['filesystems'][0]['available_bytes'] = 99
    sample_path.write_text(json.dumps(sample))
    for _ in range(2):
        result = subprocess.run([BASH, str(GUARD_PATH)], env=environment, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert 'posthog_guard_protection_status=protected' in result.stdout
    incident_path = tmp_path / 'guard/protection-state.json'
    incident = json.loads(incident_path.read_text())
    assert incident['status'] == 'protected'
    assert incident['reasons'] == ['analytics_storage']
    assert len(incident['incident_id']) == 32
    assert (tmp_path / 'restart-log').read_text().splitlines() == ['restart']
    sample['filesystems'][0]['available_bytes'] = 500
    sample_path.write_text(json.dumps(sample))
    result = subprocess.run([BASH, str(GUARD_PATH)], env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'posthog_guard_capacity_ready=false' in result.stdout
    assert 'analytics_protection_latched' in result.stdout
    assert (tmp_path / 'restart-log').read_text().splitlines() == ['restart']
    assert json.loads(incident_path.read_text())['incident_id'] == incident['incident_id']
    assert str(tmp_path) not in incident_path.read_text()


@pytest.mark.parametrize('failure', ['FAIL_RESTART', 'FAIL_READBACK'])
def test_guard_failure_stays_closed_and_retries_application(tmp_path: Path, failure: str):
    environment, sample, sample_path = _capacity_guard_runtime(tmp_path)
    sample['filesystems'][0]['available_bytes'] = 199
    sample_path.write_text(json.dumps(sample))
    result = subprocess.run([BASH, str(GUARD_PATH)], env={**environment, failure: '1'}, capture_output=True, text=True)
    assert result.returncode == 1, result.stderr
    assert 'posthog_guard_protection_status=apply_failed' in result.stdout
    assert json.loads((tmp_path / 'guard/protection-state.json').read_text())['status'] == 'apply_failed'
    # The durable request survives even if the triggering symptom disappears.
    sample['filesystems'][0]['available_bytes'] = 500
    sample_path.write_text(json.dumps(sample))
    result = subprocess.run([BASH, str(GUARD_PATH)], env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'posthog_guard_protection_status=protected' in result.stdout
    assert len((tmp_path / 'restart-log').read_text().splitlines()) == 2


@pytest.mark.parametrize(('mode', 'status'), [
    ({'GRAF_POSTHOG_GUARD_DRY_RUN': '1'}, 'blocked_dry_run'),
    ({'GRAF_POSTHOG_GUARD_AUTO_ROLLBACK': '0'}, 'not_enabled'),
])
def test_guard_dry_run_and_auto_off_never_claim_protection(tmp_path: Path, mode, status):
    environment, sample, sample_path = _capacity_guard_runtime(tmp_path)
    sample['filesystems'][0]['available_bytes'] = 199
    sample_path.write_text(json.dumps(sample))
    result = subprocess.run([BASH, str(GUARD_PATH)], env={**environment, **mode}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert f'posthog_guard_protection_status={status}' in result.stdout
    assert 'posthog_guard_capacity_ready=false' in result.stdout
    assert not (tmp_path / 'restart-log').exists()


def test_guard_bad_state_and_failed_fresh_probe_prevent_readiness(tmp_path: Path):
    environment, sample, _ = _capacity_guard_runtime(tmp_path)
    collector = Path(environment['GRAF_POSTHOG_STORAGE_COLLECTOR'])
    collector.write_text('#!/bin/sh\nexit 1\n')
    result = subprocess.run([BASH, str(GUARD_PATH)], env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'capacity_input_unverified' in result.stdout
    assert 'posthog_guard_capacity_ready=false' in result.stdout
    assert not (tmp_path / 'restart-log').exists()
    (tmp_path / 'guard/protection-state.json').write_text('{broken')
    sample['filesystems'][0]['available_bytes'] = 99
    Path(environment['GRAF_POSTHOG_STORAGE_STATE_FILE']).with_suffix('.json').write_text(json.dumps(sample))
    result = subprocess.run([BASH, str(GUARD_PATH)], env=environment, capture_output=True, text=True)
    assert result.returncode == 1, result.stderr
    assert 'protection_state_unverified' in result.stdout
    assert not (tmp_path / 'restart-log').exists()


def test_parallel_guard_runs_apply_once_and_real_state_feeds_readiness(tmp_path: Path):
    environment, sample, sample_path = _capacity_guard_runtime(tmp_path)
    sample['filesystems'][0]['available_bytes'] = 199
    sample_path.write_text(json.dumps(sample))
    runs = [subprocess.Popen([BASH, str(GUARD_PATH)], env=environment, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True) for _ in range(2)]
    for run in runs:
        output, error = run.communicate(timeout=30)
        assert run.returncode == 0, error
        assert 'posthog_guard_protection_status=protected' in output
    assert (tmp_path / 'restart-log').read_text().splitlines() == ['restart']
    assert 'analytics_protection_latched' in provider_readiness.runtime_guard_blockers(environment)


@pytest.mark.parametrize('age', [-1, 0, 119, 120])
def test_readiness_consumes_fresh_capacity_and_immediate_incident_latch(tmp_path: Path, age: int):
    from tests.fixtures.analytics_operations import write_runtime_guard
    now = 1792634400
    environment = write_runtime_guard(tmp_path, now=now - age)
    blockers = provider_readiness.runtime_guard_blockers(environment, now=now)
    assert ('capacity_input_unverified' in blockers) is (not 0 <= age < 120)
    guard = Path(environment['GRAF_POSTHOG_GUARD_STATE_DIR'])
    # A pre-switch incident must block even while the last alert-state says pass.
    (guard / 'protection-state.json').write_text(json.dumps({
        'protection_state_version': 1, 'status': 'protection_requested',
        'reasons': ['analytics_storage'],
    }))
    assert 'analytics_protection_latched' in provider_readiness.runtime_guard_blockers(environment, now=now)


def test_readiness_rejects_budget_expiry_between_guard_ticks_and_invalid_state(tmp_path: Path):
    from tests.fixtures.analytics_operations import write_runtime_guard
    now = 1792634400
    environment = write_runtime_guard(tmp_path, now=now)
    guard = Path(environment['GRAF_POSTHOG_GUARD_STATE_DIR'])
    state = guard / 'alert-state'
    state.write_text(state.read_text().replace(str(now + 3600), str(now)))
    assert 'capacity_budget_unverified' in provider_readiness.runtime_guard_blockers(environment, now=now)
    (guard / 'protection-state.json').write_text('{broken')
    assert 'protection_state_unverified' in provider_readiness.runtime_guard_blockers(environment, now=now)


@pytest.mark.parametrize('reasons', [None, 'bad', [None], ['unsafe value'], ['analytics_storage']])
def test_observed_state_validation_matches_guard_and_api(tmp_path: Path, reasons):
    from tests.contract.test_analytics_retention_enforcement import _capacity_evaluator
    from tests.fixtures.analytics_operations import write_runtime_guard
    now = int(time.time())
    environment = write_runtime_guard(tmp_path, now=now)
    path = Path(environment['GRAF_POSTHOG_GUARD_STATE_DIR']) / 'protection-state.json'
    capacity = _capacity_evaluator()
    assert provider_readiness.runtime_guard_blockers(environment, now=now) == ()
    assert capacity.transition(path, [], 'status', now=now) == 'observed'
    state = json.loads(path.read_text())
    if reasons is None:
        state.pop('reasons')
    else:
        state['reasons'] = reasons
    path.write_text(json.dumps(state))
    assert 'protection_state_unverified' in provider_readiness.runtime_guard_blockers(environment, now=now)
    with pytest.raises(ValueError, match='protection_state_unverified'):
        capacity.transition(path, [], 'status', now=now)


def test_guard_does_not_report_success_when_healthy_state_cannot_be_written(tmp_path: Path):
    environment, _, _ = _capacity_guard_runtime(tmp_path)
    real_awk = shutil.which('awk')
    (tmp_path / 'bin/awk').write_text(
        '#!/bin/sh\ncase "$*" in\n'
        '  */proc/loadavg*) printf "1\\n" ;;\n'
        '  */proc/meminfo*) printf "32768\\n" ;;\n'
        f'  *) exec "{real_awk}" "$@" ;;\nesac\n'
    )
    (tmp_path / 'bin/awk').chmod(0o755)
    (tmp_path / 'bin/mv').write_text(
        '#!/bin/sh\ncase "$2" in */alert-state) exit 1 ;; esac\nexec /bin/mv "$@"\n'
    )
    (tmp_path / 'bin/mv').chmod(0o755)
    result = subprocess.run([BASH, str(GUARD_PATH)], env=environment, capture_output=True, text=True)
    assert result.returncode == 1, result.stderr
    assert not (tmp_path / 'guard/alert-state').exists()
    assert not (tmp_path / 'restart-log').exists()


@pytest.mark.parametrize(('change', 'blocker'), [
    ('future', 'backup_stale'),
    ('boundary', 'backup_stale'),
    ('unknown_time', 'backup_missing'),
    ('failed', 'backup_failed'),
    ('unknown_result', 'backup_failed'),
    ('old_schema', 'backup_set_unverified'),
    ('incomplete', 'backup_set_unverified'),
    ('unknown_count', 'backup_copy_count_below_minimum'),
    ('one_copy', 'backup_copy_count_below_minimum'),
    ('valid', None),
])
def test_backup_readiness_and_alerting_share_local_set_boundaries(tmp_path: Path, change: str, blocker: str | None) -> None:
    now = int(time.time())
    state = _valid_operations_state(tmp_path, now=now)
    backup = state['backup']
    text = backup.read_text()
    replacements = {
        'future': (f'last_success_epoch={now - 3600}', f'last_success_epoch={now + 3600}'),
        'boundary': (f'last_success_epoch={now - 3600}', f'last_success_epoch={now - 26 * 3600}'),
        'unknown_time': (f'last_success_epoch={now - 3600}', 'last_success_epoch=unknown'),
        'failed': ('last_attempt_result=pass', 'last_attempt_result=failed'),
        'unknown_result': ('last_attempt_result=pass', 'last_attempt_result=unknown'),
        'old_schema': ('backup_state_version=2', 'backup_state_version=1'),
        'incomplete': ('backup_set_complete=true', 'backup_set_complete=false'),
        'unknown_count': ('copies_local=7', 'copies_local=unknown'),
        'one_copy': ('copies_local=7', 'copies_local=1'),
    }
    if change in replacements:
        before, after = replacements[change]
        assert before in text
        text = text.replace(before, after)
    backup.write_text(text)
    environment, _ = _alert_environment(tmp_path, state)
    # Operator knobs cannot weaken the accepted 26h/2-set limits.
    environment['GRAF_POSTHOG_BACKUP_MAX_AGE_HOURS'] = '100'
    environment['GRAF_POSTHOG_BACKUP_MIN_COPIES'] = '1'
    environment['GRAF_POSTHOG_BACKUP_STATE_FILE'] = str(backup)
    evidence = provider_readiness.collect_analytics_operations_evidence(environment, now=now)
    blockers = provider_readiness.analytics_operations_blockers(evidence, environment)
    alert = _run_alert(environment, '--dry-run')
    assert alert.returncode == 0, alert.stderr
    if blocker:
        assert blocker in blockers
        assert blocker in alert.stdout
    else:
        assert not any(code.startswith('backup_') for code in blockers)
        assert 'backup_offsite' not in alert.stdout
