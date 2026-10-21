"""Contract tests for analytics retention, backup and restore (T024).

Scheduled tasks have to prove three things without a production run:

* a backup archives every inventory volume class, ships one copy offsite, keeps
  at least two copies and alerts when it fails (FR-033, FR-051, FR-052);
* a restore verification proves that a stored copy can be read back, records
  metadata-only evidence and alerts when it fails (FR-035, SC-010);
* every retention category has an explicit mode and scheduled verification never
  deletes history by age (FR-036, FR-050, SC-011).

The Docker runtime and the shell logger are replaced by deterministic stubs, so
the tests exercise the scripts themselves and never touch a container, the
network or production.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from twobrain_rec_server.product_analytics import provider_readiness

REPO_ROOT = Path(__file__).parents[4]
BACKUP_PATH = REPO_ROOT / "infra/scripts/backup-posthog.sh"
RESTORE_PATH = REPO_ROOT / "infra/scripts/verify-posthog-restore.sh"
RETENTION_PATH = REPO_ROOT / "infra/scripts/enforce-product-analytics-retention.sh"
TTL_APPLY_PATH = REPO_ROOT / "infra/scripts/apply-posthog-event-ttl.sh"
TTL_SQL_PATH = REPO_ROOT / "infra/posthog/clickhouse-retention.sql"
PRODUCT_ANALYTICS_MODELS_PATH = (
    REPO_ROOT / "apps/server/src/twobrain_rec_server/db/models/product_analytics.py"
)
PRODUCT_ANALYTICS_MIGRATIONS = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0094_anonymous_page_aggregate.py",
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0095_public_attribution.py",
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0096_client_attribution_bridge.py",
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0097_public_attribution_admission_index.py",
)
BILLING_MODELS_PATH = REPO_ROOT / "apps/server/src/twobrain_rec_server/db/models/billing.py"
INVENTORY_PATH = REPO_ROOT / "infra/posthog/backup-volumes.txt"
COMPOSE_PATH = REPO_ROOT / "infra/posthog/docker-compose.posthog.yml"
PRODUCTION_ENV_EXAMPLE = REPO_ROOT / "infra/posthog/posthog.production.env.example"
BACKUP_ENV_EXAMPLE = REPO_ROOT / "infra/posthog/backup.env.example"
RETENTION_ENV_EXAMPLE = REPO_ROOT / "infra/posthog/retention.env.example"
UNIT_DIR = REPO_ROOT / "infra/posthog"
DOC_PATH = REPO_ROOT / "infra/posthog/backup-restore.md"
RUNBOOK_PATH = REPO_ROOT / "docs/analytics/product-analytics-posthog-runbook.md"
CAPACITY_PATH = REPO_ROOT / "docs/analytics/product-analytics-capacity-baseline.md"
GROWTH_PATH = REPO_ROOT / "infra/scripts/measure-posthog-storage-growth.sh"
BASH = shutil.which("bash") or "/bin/bash"

FAKE_DOCKER = """#!{python}
import os
import pathlib
import sys

args = sys.argv[1:]
log = os.environ.get("FAKE_DOCKER_LOG")
if log:
    with open(log, "a", encoding="utf-8") as handle:
        handle.write(" ".join(args) + "\\n")
    handle = None

if args[:2] == ["volume", "ls"]:
    for name in os.environ.get("FAKE_VOLUMES", "").split():
        print(name)
    sys.exit(0)
if args[:2] in (["volume", "create"], ["volume", "rm"]):
    sys.exit(0)
if args[:1] == ["ps"]:
    print(os.environ.get("FAKE_CONTAINER", "clickhouse-container"))
    sys.exit(0)
if args[:1] == ["compose"]:
    joined = " ".join(args)
    if "to_regclass" in joined:
        print("f" if os.environ.get("FAKE_TABLE_MISSING") == "1" else "t")
    elif "information_schema.columns" in joined:
        print("f" if os.environ.get("FAKE_COLUMN_MISSING") == "1" else "t")
    elif "DELETE" in joined:
        print(os.environ.get("FAKE_ROWS_DELETED", "2"))
    elif "pg_database_size" in joined:
        print(os.environ.get("FAKE_DB_BYTES", "52428800"))
    else:
        print("")
    sys.exit(0)
if args[:1] == ["exec"]:
    joined = " ".join(args)
    if "create_table_query" in joined:
        state = pathlib.Path(os.environ["FAKE_TTL_STATE"])
        print(state.read_text() if state.exists() else os.environ.get("FAKE_CLICKHOUSE_TTL", "0"))
    elif "sum(bytes_on_disk)" in joined:
        print(os.environ.get("FAKE_EVENTS_BYTES", "104857600"))
    elif "INTERVAL" in joined and "count()" in joined:
        print(os.environ.get("FAKE_WINDOW_EVENTS", "1000"))
    elif "count()" in joined:
        print(os.environ.get("FAKE_TOTAL_EVENTS", "100000"))
    elif "--multiquery" in args:
        sys.stdin.read()
        if os.environ.get("FAKE_TTL_STATEMENT_FAIL") == "1":
            sys.exit(1)
        pathlib.Path(os.environ["FAKE_TTL_STATE"]).write_text("0")
    sys.exit(0)
if args[:1] == ["run"]:
    if os.environ.get("FAKE_DOCKER_FAIL") == "1":
        sys.exit(1)
    mounts = []
    index = 0
    while index < len(args):
        if args[index] == "-v" and index + 1 < len(args):
            mounts.append(args[index + 1])
            index += 2
            continue
        index += 1
    backup_host = None
    for mount in mounts:
        parts = mount.split(":")
        if len(parts) >= 2 and parts[1] == "/backup":
            backup_host = parts[0]
    if "tar" in args:
        target = None
        for position, token in enumerate(args):
            if token == "-czf" and position + 1 < len(args):
                target = args[position + 1]
        if target and backup_host:
            name = os.path.basename(target)
            path = pathlib.Path(backup_host, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            body = os.environ.get("FAKE_ARCHIVE_BODY", "archive:" + name).encode()
            path.write_bytes(body)
        sys.exit(0)
    if "sh" in args or "find" in " ".join(args):
        print(os.environ.get("FAKE_FILE_COUNT", "3"))
        sys.exit(0)
    sys.exit(0)
sys.exit(0)
"""

FAKE_LOGGER = """#!{python}
import os
import sys

target = os.environ.get("FAKE_LOGGER_LOG")
if target:
    with open(target, "a", encoding="utf-8") as handle:
        handle.write(" ".join(sys.argv[1:]) + "\\n")
sys.exit(0)
"""

FAKE_ALERT = """#!{python}
import os
import sys

target = os.environ.get("FAKE_ALERT_LOG")
if target:
    with open(target, "a", encoding="utf-8") as handle:
        handle.write("alert invoked\\n")
sys.exit(0)
"""


def _write_executable(path: Path, content: str) -> Path:
    path.write_text(content.format(python=sys.executable), encoding="utf-8")
    path.chmod(0o755)
    return path


def _inventory(tmp_path: Path) -> Path:
    path = tmp_path / "backup-volumes.txt"
    path.write_text(
        "\n".join(
            [
                "# fixture inventory",
                "graf-posthog_postgres-data",
                "graf-posthog_clickhouse-data",
                "graf-posthog_objectstorage",
                "graf-posthog_redis-data?",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _runtime(tmp_path: Path, *, volumes: str | None = None) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    _write_executable(bin_dir / "docker", FAKE_DOCKER)
    _write_executable(bin_dir / "logger", FAKE_LOGGER)
    _write_executable(bin_dir / "stub-alert.sh", FAKE_ALERT)
    return {
        "PATH": f"{bin_dir}:{Path(BASH).parent}:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin",
        "HOME": str(tmp_path),
        "FAKE_VOLUMES": volumes
        if volumes is not None
        else "graf-posthog_postgres-data graf-posthog_clickhouse-data graf-posthog_objectstorage graf-posthog_redis-data",
        "GRAF_PRODUCT_ANALYTICS_RETENTION_MODE": "until_decision",
        "FAKE_TTL_STATE": str(tmp_path / "ttl-state"),
        "FAKE_DOCKER_LOG": str(tmp_path / "docker.log"),
        "FAKE_LOGGER_LOG": str(tmp_path / "logger.log"),
        "FAKE_ALERT_LOG": str(tmp_path / "alert.log"),
    }


def _backup_environment(tmp_path: Path, inventory: Path) -> dict[str, str]:
    environment = _runtime(tmp_path)
    environment.update(
        {
            "GRAF_POSTHOG_BACKUP_DIR": str(tmp_path / "backups"),
            "GRAF_POSTHOG_BACKUP_STATE_DIR": str(tmp_path / "state"),
            "GRAF_POSTHOG_BACKUP_INVENTORY": str(inventory),
            "GRAF_POSTHOG_BACKUP_KEEP": "3",
            "GRAF_POSTHOG_BACKUP_MIN_COPIES": "2",
            "GRAF_POSTHOG_BACKUP_MIN_OFFSITE_COPIES": "1",
            "GRAF_POSTHOG_BACKUP_IMAGE": "alpine:3.20",
            "GRAF_POSTHOG_OFFSITE_COMMAND": 'printf "%s" "%LABEL%" > "$FAKE_OFFSITE_LOG"',
            "FAKE_OFFSITE_LOG": str(tmp_path / "offsite.log"),
            "GRAF_POSTHOG_ALERT_SCRIPT": str(tmp_path / "bin" / "stub-alert.sh"),
        }
    )
    return environment


def _restore_environment(tmp_path: Path, backup_environment: dict[str, str]) -> dict[str, str]:
    environment = dict(backup_environment)
    environment.update(
        {
            "GRAF_POSTHOG_RESTORE_EVIDENCE_DIR": str(tmp_path / "evidence"),
            "GRAF_POSTHOG_RESTORE_VOLUME_PREFIX": "graf-posthog-rehearsal",
        }
    )
    return environment


def _run(script: Path, environment: dict[str, str], *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [BASH, str(script), *arguments], cwd=REPO_ROOT, env=environment, capture_output=True, text=True
    )


def test_scheduled_scripts_are_valid_and_documented() -> None:
    for path in (BACKUP_PATH, RESTORE_PATH, RETENTION_PATH, TTL_APPLY_PATH, GROWTH_PATH):
        assert path.exists(), path
        result = subprocess.run([BASH, "-n", str(path)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        text = path.read_text(encoding="utf-8")
        assert text.startswith("#!/usr/bin/env bash\nset -euo pipefail\n"), path.name
        assert "secret" not in text.lower().replace("secret_policy", ""), path.name
        assert "password" not in text.lower(), path.name

    inventory = INVENTORY_PATH.read_text(encoding="utf-8")
    assert "graf-posthog_postgres-data" in inventory
    assert "graf-posthog_clickhouse-data" in inventory
    assert "?" in inventory, "optional classes must be marked"
    assert "backup-posthog.sh" in DOC_PATH.read_text(encoding="utf-8")
    assert "verify-posthog-restore.sh" in DOC_PATH.read_text(encoding="utf-8")


def test_backup_example_and_units_are_installed_outside_git() -> None:
    for example in (BACKUP_ENV_EXAMPLE, RETENTION_ENV_EXAMPLE):
        text = example.read_text(encoding="utf-8")
        assert "mode 0600" in text
        assert "GRAF_POSTHOG_OFFSITE_COMMAND" in BACKUP_ENV_EXAMPLE.read_text(encoding="utf-8")

    backup_service = (UNIT_DIR / "graf-posthog-backup.service").read_text(encoding="utf-8")
    assert "ExecStart=/usr/local/libexec/graf-posthog-backup.sh --execute" in backup_service
    assert "EnvironmentFile=-/etc/graf-posthog-backup.env" in backup_service
    assert "ReadWritePaths=-/var/backups/graf-posthog" in backup_service

    restore_service = (UNIT_DIR / "graf-posthog-restore-verify.service").read_text(encoding="utf-8")
    assert "ExecStart=/usr/local/libexec/graf-posthog-restore-verify.sh --execute" in restore_service

    retention_service = (UNIT_DIR / "graf-posthog-retention-enforce.service").read_text(encoding="utf-8")
    assert "ExecStart=/usr/local/libexec/graf-posthog-retention-enforce.sh --execute" in retention_service
    assert "EnvironmentFile=-/etc/graf-posthog-retention.env" in retention_service


def test_backup_archives_every_required_class_and_ships_one_copy_offsite(tmp_path: Path) -> None:
    inventory = _inventory(tmp_path)
    environment = _backup_environment(tmp_path, inventory)

    dry_run = _run(BACKUP_PATH, environment)
    assert dry_run.returncode == 0, dry_run.stderr
    assert "backup_result=dry_run" in dry_run.stdout
    assert "volumes_matched=4" in dry_run.stdout
    assert "required_classes=3" in dry_run.stdout
    assert "optional_classes=1" in dry_run.stdout
    assert "unmatched_required=none" in dry_run.stdout
    assert not (tmp_path / "backups").exists()

    result = _run(BACKUP_PATH, environment, "--execute")

    assert result.returncode == 0, result.stderr
    assert "backup_result=pass" in result.stdout
    assert "volumes_archived=4" in result.stdout
    assert "copies_local=1" in result.stdout
    assert "copies_offsite=1" in result.stdout
    assert "product_impact=none" in result.stdout

    reference = next(part.split("=", 1)[1] for part in result.stdout.splitlines() if part.startswith("backup_reference="))
    backup_dir = tmp_path / "backups" / reference
    manifest = (backup_dir / "manifest.txt").read_text(encoding="utf-8")
    for volume in ("graf-posthog_postgres-data", "graf-posthog_clickhouse-data", "graf-posthog_objectstorage"):
        archive = backup_dir / f"{volume}.tar.gz"
        assert archive.exists(), volume
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        assert f"volume={volume}" in manifest
        assert digest in manifest
    assert (backup_dir / ".offsite").exists()
    assert (tmp_path / "offsite.log").read_text(encoding="utf-8") == reference

    state = (tmp_path / "state" / "backup-state").read_text(encoding="utf-8")
    assert "last_attempt_result=pass" in state
    assert "copies_local=1" in state
    assert "copies_offsite=1" in state
    assert "offsite_required=1" in state
    assert f"last_success_reference={reference}" in state
    assert "product_impact=measurement_gap_only" in state
    assert state.count("last_success_epoch=") == 1


def test_backup_keeps_two_copies_and_deletes_older_ones_with_a_log(tmp_path: Path) -> None:
    inventory = _inventory(tmp_path)
    environment = _backup_environment(tmp_path, inventory)
    backups = tmp_path / "backups"
    backups.mkdir()
    for label in ("20260101T023000Z", "20260102T023000Z", "20260103T023000Z", "20260104T023000Z"):
        (backups / label).mkdir()
        (backups / label / ".offsite").write_text("", encoding="utf-8")

    result = _run(BACKUP_PATH, environment, "--execute")

    assert result.returncode == 0, result.stderr
    remaining = sorted(path.name for path in backups.iterdir() if path.is_dir())
    assert len(remaining) == 3, remaining  # retention keep of three, never below the minimum of two
    assert "20260101T023000Z" not in remaining
    assert "retention_deleted=20260101T023000Z" in result.stdout
    assert "20260102T023000Z" not in remaining
    assert "retention_deleted=20260102T023000Z" in result.stdout
    journal = (tmp_path / "logger.log").read_text(encoding="utf-8")
    assert "result=retention_deleted reference=20260101T023000Z" in journal


def test_backup_fails_closed_and_alerts_when_a_required_class_is_absent(tmp_path: Path) -> None:
    inventory = _inventory(tmp_path)
    environment = _backup_environment(tmp_path, inventory)
    environment["FAKE_VOLUMES"] = "graf-posthog_postgres-data"

    result = _run(BACKUP_PATH, environment, "--execute")

    assert result.returncode == 1
    assert "backup_result=failed" in result.stdout
    assert "reason=required_volume_class_missing" in result.stdout
    assert (tmp_path / "alert.log").read_text(encoding="utf-8").strip() == "alert invoked"
    state = (tmp_path / "state" / "backup-state").read_text(encoding="utf-8")
    assert "last_attempt_result=failed" in state
    assert "last_failure_reason=required_volume_class_missing" in state
    journal = (tmp_path / "logger.log").read_text(encoding="utf-8")
    assert "result=backup_failed reason=required_volume_class_missing" in journal


def test_backup_requires_an_offsite_destination(tmp_path: Path) -> None:
    inventory = _inventory(tmp_path)
    environment = _backup_environment(tmp_path, inventory)
    environment["GRAF_POSTHOG_OFFSITE_COMMAND"] = ""

    result = _run(BACKUP_PATH, environment, "--execute")

    assert result.returncode == 1
    assert "reason=offsite_command_not_configured" in result.stdout


def test_backup_rejects_a_retention_count_below_the_minimum(tmp_path: Path) -> None:
    inventory = _inventory(tmp_path)
    environment = _backup_environment(tmp_path, inventory)
    environment["GRAF_POSTHOG_BACKUP_KEEP"] = "1"

    result = _run(BACKUP_PATH, environment, "--execute")

    assert result.returncode == 2
    assert "backup_result=blocked" in result.stdout
    assert "reason=retention_below_minimum_copies" in result.stdout


def test_restore_verification_replays_a_stored_copy_without_touching_the_live_stack(tmp_path: Path) -> None:
    inventory = _inventory(tmp_path)
    environment = _backup_environment(tmp_path, inventory)
    backup = _run(BACKUP_PATH, environment, "--execute")
    assert "backup_result=pass" in backup.stdout, backup.stderr
    reference = next(part.split("=", 1)[1] for part in backup.stdout.splitlines() if part.startswith("backup_reference="))
    restore_environment = _restore_environment(tmp_path, environment)

    dry_run = _run(RESTORE_PATH, restore_environment)
    assert dry_run.returncode == 0, dry_run.stderr
    assert "restore_verification_result=dry_run" in dry_run.stdout
    assert "live_stack_touched=0" in dry_run.stdout
    assert f"backup_reference={reference}" in dry_run.stdout

    result = _run(RESTORE_PATH, restore_environment, "--execute")

    assert result.returncode == 0, result.stderr
    assert "restore_verification_result=pass" in result.stdout
    assert "archives_verified=4" in result.stdout
    assert "volumes_restored=4" in result.stdout
    assert "integrity=sha256_manifest_verified" in result.stdout
    assert "live_stack_touched=0" in result.stdout

    state = (tmp_path / "state" / "restore-state").read_text(encoding="utf-8")
    assert "last_verify_result=pass" in state
    assert f"last_verify_reference={reference}" in state
    assert "volumes_restored=4" in state
    assert "rehearsal_scope=isolated_volumes_removed_after_check" in state
    assert "live_stack_touched=0" in state

    evidence = tmp_path / "evidence" / f"restore-evidence-{reference}.txt"
    assert evidence.exists()
    evidence_text = evidence.read_text(encoding="utf-8")
    assert "result=pass" in evidence_text
    assert "integrity=sha256_manifest_verified" in evidence_text
    assert "content_policy=metadata_only_no_visitor_or_user_data" in evidence_text

    docker_log = (tmp_path / "docker.log").read_text(encoding="utf-8")
    assert "volume create graf-posthog-rehearsal-graf-posthog_postgres-data" in docker_log
    assert "volume rm graf-posthog-rehearsal-graf-posthog_postgres-data" in docker_log

    status = _run(RESTORE_PATH, restore_environment, "--status")
    assert "last_verify_result=pass" in status.stdout
    assert "verification_age_days=" in status.stdout


def test_restore_verification_detects_a_corrupted_archive(tmp_path: Path) -> None:
    inventory = _inventory(tmp_path)
    environment = _backup_environment(tmp_path, inventory)
    backup = _run(BACKUP_PATH, environment, "--execute")
    reference = next(part.split("=", 1)[1] for part in backup.stdout.splitlines() if part.startswith("backup_reference="))
    archive = tmp_path / "backups" / reference / "graf-posthog_postgres-data.tar.gz"
    archive.write_bytes(b"corrupted archive")
    restore_environment = _restore_environment(tmp_path, environment)

    result = _run(RESTORE_PATH, restore_environment, "--execute")

    assert result.returncode == 1
    assert "restore_verification_result=failed" in result.stdout
    assert "reason=archive_integrity_failed" in result.stdout
    state = (tmp_path / "state" / "restore-state").read_text(encoding="utf-8")
    assert "last_verify_result=fail" in state
    assert "last_verify_reason=archive_integrity_failed" in state
    assert (tmp_path / "alert.log").read_text(encoding="utf-8").strip() == "alert invoked"


def test_restore_verification_fails_when_no_copy_exists(tmp_path: Path) -> None:
    inventory = _inventory(tmp_path)
    environment = _backup_environment(tmp_path, inventory)
    restore_environment = _restore_environment(tmp_path, environment)

    result = _run(RESTORE_PATH, restore_environment, "--execute")

    assert result.returncode == 1
    assert "reason=backup_reference_missing" in result.stdout


def test_retention_terms_match_the_approved_contract() -> None:
    assert dict(provider_readiness.REQUIRED_RETENTION_TERMS) == {
        category: None
        for category in (
            "measurement_events",
            "anonymous_aggregate",
            "visit_attribution",
            "acquisition_attribute",
        )
    }
    script = RETENTION_PATH.read_text()
    assert "DELETE" not in script
    assert "missing_category=" in script
    assert "rows_deleted=0" in script


def test_retention_dry_run_lists_every_category_and_its_mechanism(tmp_path: Path) -> None:
    environment = _runtime(tmp_path)
    environment["GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_DIR"] = str(tmp_path / "state")
    result = _run(RETENTION_PATH, environment)
    assert result.returncode == 0, result.stderr
    assert "retention_mode=until_decision" in result.stdout
    assert "rows_deleted_total=0" in result.stdout
    assert not (tmp_path / "state").exists()
    assert not (tmp_path / "docker.log").exists()


def test_retention_rejects_legacy_age_configuration_before_database_access(tmp_path: Path) -> None:
    environment = _runtime(tmp_path)
    environment["POSTHOG_EVENT_RETENTION_DAYS"] = "365"
    result = _run(RETENTION_PATH, environment)
    assert result.returncode != 0
    assert "legacy_age_configuration" in result.stdout
    assert not (tmp_path / "docker.log").exists()


def test_retention_execution_only_observes_storage_and_produces_current_evidence(
    tmp_path: Path,
) -> None:
    environment = _runtime(tmp_path)
    environment["GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_DIR"] = str(tmp_path / "state")
    result = _run(RETENTION_PATH, environment, "--execute")
    assert result.returncode == 0, result.stderr
    state_file = tmp_path / "state" / "retention-state"
    state = state_file.read_text()
    assert "result=pass" in state
    assert "rows_deleted_total=0" in state
    assert state.count("enforcement_verified=true") == 4
    assert state.count("retention_days=none") == 4
    log = (tmp_path / "docker.log").read_text()
    assert not any(word in log for word in ("DELETE", "UPDATE", "ALTER", "TRUNCATE"))
    evidence = provider_readiness.collect_analytics_operations_evidence(
        {"GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_FILE": str(state_file)}, now=time.time()
    )
    assert not any(
        "retention" in blocker
        for blocker in provider_readiness.analytics_operations_blockers(evidence, {})
    )


def test_retention_fails_closed_when_a_category_has_no_storage(tmp_path: Path) -> None:
    environment = _runtime(tmp_path)
    environment["GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_DIR"] = str(tmp_path / "state")
    environment["GRAF_POSTHOG_ALERT_SCRIPT"] = str(tmp_path / "bin/stub-alert.sh")
    environment["FAKE_TABLE_MISSING"] = "1"
    result = _run(RETENTION_PATH, environment, "--execute")
    assert result.returncode == 1
    assert "reason=retention_category_missing" in result.stdout
    state = (tmp_path / "state/retention-state").read_text()
    assert "result=failed" in state
    assert "enforcement_verified=false" in state
    assert "rows_deleted_total=0" in state
    assert (tmp_path / "alert.log").read_text().strip() == "alert invoked"
    assert "DELETE" not in (tmp_path / "docker.log").read_text()


def test_missing_or_unknown_mode_never_queries_or_changes_storage(tmp_path: Path) -> None:
    environment = _runtime(tmp_path)
    environment["GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_DIR"] = str(tmp_path / "state")
    for mode in ("", "unknown", "age"):
        environment["GRAF_PRODUCT_ANALYTICS_RETENTION_MODE"] = mode
        for script in (RETENTION_PATH, TTL_APPLY_PATH):
            result = _run(script, environment)
            assert result.returncode != 0
            assert "retention_mode_missing_or_unknown" in result.stdout
    assert not (tmp_path / "docker.log").exists()


def test_retention_refuses_a_restored_legacy_ttl(tmp_path: Path) -> None:
    environment = _runtime(tmp_path)
    environment["GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_DIR"] = str(tmp_path / "state")
    environment["FAKE_CLICKHOUSE_TTL"] = "1"
    result = _run(RETENTION_PATH, environment, "--execute")
    assert result.returncode == 1
    assert "reason=age_ttl_present_or_unknown" in result.stdout
    assert "result=failed" in (tmp_path / "state/retention-state").read_text()
    assert "DELETE" not in (tmp_path / "docker.log").read_text()


def test_event_ttl_statement_removes_age_deletion_from_the_storage_table() -> None:
    sql = TTL_SQL_PATH.read_text()
    assert "ALTER TABLE posthog.sharded_events REMOVE TTL;" in sql
    compose = COMPOSE_PATH.read_text()
    assert 'retention_mode: "until_decision"' in compose
    assert 'enforcement: "decision_required"' in compose
    for example in (PRODUCTION_ENV_EXAMPLE, RETENTION_ENV_EXAMPLE):
        assert "GRAF_PRODUCT_ANALYTICS_RETENTION_MODE=until_decision" in example.read_text()
        assert "POSTHOG_EVENT_RETENTION_DAYS=" not in example.read_text()


def test_event_ttl_applier_is_idempotent_and_verifies_the_result(tmp_path: Path) -> None:
    environment = _runtime(tmp_path)
    environment["FAKE_CLICKHOUSE_TTL"] = "1"
    dry_run = _run(TTL_APPLY_PATH, environment)
    assert dry_run.returncode == 0, dry_run.stderr
    assert "REMOVE TTL" in dry_run.stdout
    assert not (tmp_path / "docker.log").exists()
    for _ in range(2):
        applied = _run(TTL_APPLY_PATH, environment, "--execute")
        assert applied.returncode == 0, applied.stderr
        assert "posthog_event_ttl_present=0" in applied.stdout
    assert (tmp_path / "docker.log").read_text().count("--multiquery") == 1
    (tmp_path / "ttl-state").unlink()
    environment["FAKE_TTL_STATEMENT_FAIL"] = "1"
    assert _run(TTL_APPLY_PATH, environment, "--execute").returncode == 1
    environment["FAKE_CLICKHOUSE_TTL"] = "unknown"
    assert _run(TTL_APPLY_PATH, environment, "--execute").returncode == 1


def test_storage_growth_measurement_reports_the_documented_keys(tmp_path: Path) -> None:
    environment = _runtime(tmp_path)
    environment["GRAF_POSTHOG_STORAGE_STATE_FILE"] = str(tmp_path / "storage-state")
    environment["GRAF_POSTHOG_ANALYTICS_PATH"] = str(tmp_path)

    result = _run(GROWTH_PATH, environment)

    assert result.returncode == 0, result.stderr
    for key in (
        "storage_class=analytics_filesystem_total",
        "absolute_bytes=",
        "window_hours=",
        "events_in_window=",
        "bytes_per_day=",
        "bytes_per_1000_events=",
        "projected_bytes_12_months=",
        "projected_bytes_36_months=",
        "analytics_disk_free_percent=",
        "recorded_at=",
    ):
        assert key in result.stdout, key

    capacity = CAPACITY_PATH.read_text(encoding="utf-8")
    for key in ("storage_class", "absolute_bytes", "projected_bytes_36_months", "pending operator receipt"):
        assert key in capacity, key
    assert "measure-posthog-storage-growth.sh" in capacity
    assert "measure-posthog-storage-growth.sh" in RUNBOOK_PATH.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", [BACKUP_PATH, RESTORE_PATH, RETENTION_PATH, TTL_APPLY_PATH, GROWTH_PATH])
def test_scheduled_scripts_have_no_hard_coded_production_secrets(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert not re.search(r"\b\d{6,12}:[A-Za-z0-9_-]{20,}\b", text), path.name
    assert "BEGIN PRIVATE KEY" not in text
    assert "PRIVATE KEY" not in text


def test_backup_state_contract_is_readable_by_readiness_and_alerting(tmp_path: Path) -> None:
    inventory = _inventory(tmp_path)
    environment = _backup_environment(tmp_path, inventory)
    result = _run(BACKUP_PATH, environment, "--execute")
    assert "backup_result=pass" in result.stdout, result.stderr
    state_file = tmp_path / "state" / "backup-state"

    evidence = provider_readiness.collect_analytics_operations_evidence(
        {
            "GRAF_POSTHOG_BACKUP_STATE_FILE": str(state_file),
            "GRAF_POSTHOG_RESTORE_STATE_FILE": str(tmp_path / "state" / "restore-state"),
            "GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_FILE": str(tmp_path / "state" / "retention-state"),
        },
        now=time.time(),
    )

    assert evidence.backup_state_available is True
    assert evidence.backup_result == "pass"
    assert evidence.backup_copies_local == 1
    assert evidence.backup_copies_offsite == 1
    assert evidence.backup_age_hours is not None and evidence.backup_age_hours < 1


def test_retention_script_targets_the_tables_the_models_declare() -> None:
    from twobrain_rec_server.db.models.product_analytics import (
        AnonymousPageAggregateBucket,
        ClientAcquisitionAttribute,
        PublicVisitAttribution,
    )

    script = RETENTION_PATH.read_text()
    for model in (AnonymousPageAggregateBucket, ClientAcquisitionAttribute, PublicVisitAttribution):
        assert model.__tablename__ in script
    assert "to_regclass" in script


def test_retention_scope_excludes_provider_event_metadata_and_provider_held_data() -> None:
    script = RETENTION_PATH.read_text()
    assert "billing_webhook_events" not in script
    assert "metadata_json" not in script
    assert "DELETE" not in script
    assert "sharded_events" in script
