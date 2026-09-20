"""Contract tests for analytics retention, backup and restore (T024).

Scheduled tasks have to prove three things without a production run:

* a backup archives every inventory volume class, ships one copy offsite, keeps
  at least two copies and alerts when it fails (FR-033, FR-051, FR-052);
* a restore verification proves that a stored copy can be read back, records
  metadata-only evidence and alerts when it fails (FR-035, SC-010);
* every retention category has a term, the term is enforced, and every deletion
  is logged with the row count it removed (FR-036, FR-050, SC-011).

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
PRODUCT_ANALYTICS_MODELS_PATH = REPO_ROOT / "apps/server/src/twobrain_rec_server/db/models/product_analytics.py"
PRODUCT_ANALYTICS_MIGRATIONS = (
    REPO_ROOT / "apps/server/src/twobrain_rec_server/db/migrations/versions/0094_anonymous_page_aggregate.py",
    REPO_ROOT / "apps/server/src/twobrain_rec_server/db/migrations/versions/0095_public_attribution.py",
    REPO_ROOT / "apps/server/src/twobrain_rec_server/db/migrations/versions/0096_client_attribution_bridge.py",
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

FAKE_DOCKER = '''#!{python}
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
    if "extract" in joined:
        print(os.environ.get("FAKE_CLICKHOUSE_TTL", "365"))
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
'''

FAKE_LOGGER = '''#!{python}
import os
import sys

target = os.environ.get("FAKE_LOGGER_LOG")
if target:
    with open(target, "a", encoding="utf-8") as handle:
        handle.write(" ".join(sys.argv[1:]) + "\\n")
sys.exit(0)
'''

FAKE_ALERT = '''#!{python}
import os
import sys

target = os.environ.get("FAKE_ALERT_LOG")
if target:
    with open(target, "a", encoding="utf-8") as handle:
        handle.write("alert invoked\\n")
sys.exit(0)
'''


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
    terms = dict(provider_readiness.REQUIRED_RETENTION_TERMS)
    assert terms == {
        "measurement_events": 365,
        "anonymous_aggregate": 1095,
        "visit_attribution": 90,
        "acquisition_attribute": 1095,
    }

    script = RETENTION_PATH.read_text(encoding="utf-8")
    for category, days in terms.items():
        assert f'"{category}:{days}:' in script, category
    assert "retention_term_missing" in script
    assert "missing_category=" in script
    assert 'anonymous_page_aggregate)' not in script
    assert 'client_acquisition_attribute)' not in script
    assert "rows_deleted=" in script
    assert "result=retention_deleted" in script
    assert "row_ttl" in script
    assert "scheduled_task" in script
    assert "information_schema.columns" in script
    assert "Preflight every target before issuing any DELETE" in script


def test_retention_dry_run_lists_every_category_and_its_mechanism(tmp_path: Path) -> None:
    environment = _runtime(tmp_path)
    environment["GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_DIR"] = str(tmp_path / "retention-state-dir")

    result = _run(RETENTION_PATH, environment)

    assert result.returncode == 0, result.stderr
    assert "retention_result=dry_run" in result.stdout
    assert "category=measurement_events retention_days=365 storage=clickhouse enforcement=row_ttl" in result.stdout
    assert "category=anonymous_aggregate retention_days=1095 storage=postgres enforcement=scheduled_task" in result.stdout
    assert "category=visit_attribution retention_days=90 storage=postgres enforcement=scheduled_task" in result.stdout
    assert "category=acquisition_attribute retention_days=1095 storage=postgres enforcement=scheduled_task" in result.stdout
    assert not (tmp_path / "retention-state-dir").exists()


def test_retention_rejects_a_shorter_measurement_term_before_database_access(tmp_path: Path) -> None:
    environment = _runtime(tmp_path)
    environment["GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_DIR"] = str(tmp_path / "retention-state-dir")
    environment["POSTHOG_EVENT_RETENTION_DAYS"] = "90"

    result = _run(RETENTION_PATH, environment, "--execute")

    assert result.returncode == 2
    assert "reason=retention_term_below_required:measurement_events" in result.stdout
    assert not (tmp_path / "docker.log").exists()
    assert not (tmp_path / "retention-state-dir").exists()


def test_retention_execution_deletes_by_age_and_logs_every_deletion(tmp_path: Path) -> None:
    environment = _runtime(tmp_path)
    environment["GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_DIR"] = str(tmp_path / "retention-state-dir")
    environment["GRAF_PRODUCT_ANALYTICS_CLICKHOUSE_CONTAINER"] = "clickhouse-container"
    environment["GRAF_POSTHOG_ALERT_SCRIPT"] = str(tmp_path / "bin" / "stub-alert.sh")
    environment["GRAF_APP_COMPOSE_FILE"] = str(tmp_path / "docker-compose.yml")
    environment["POSTHOG_EVENT_RETENTION_DAYS"] = "365"
    environment["FAKE_ROWS_DELETED"] = "7"

    result = _run(RETENTION_PATH, environment, "--execute")

    assert result.returncode == 0, result.stderr
    assert "retention_result=pass" in result.stdout
    assert "categories_enforced=4" in result.stdout
    assert "event_retention_days=365" in result.stdout
    assert "table=anonymous_page_aggregate_buckets rows_deleted=7" in result.stdout

    state = (tmp_path / "retention-state-dir" / "retention-state").read_text(encoding="utf-8")
    assert "result=pass" in state
    assert "missing_categories=none" in state
    assert "rows_deleted_total=21" in state
    assert state.count("category=") == 4
    assert state.count("enforcement_verified=true") == 4
    assert "category=measurement_events retention_days=365 storage=clickhouse enforcement=row_ttl" in state
    assert "category=visit_attribution retention_days=90" in state
    assert "content_policy=metadata_only_no_visitor_or_user_data" in state

    journal = (tmp_path / "logger.log").read_text(encoding="utf-8")
    assert "result=retention_deleted category=anonymous_aggregate" in journal
    assert "rows=7" in journal
    docker_log = (tmp_path / "docker.log").read_text(encoding="utf-8")
    assert "DELETE FROM public.anonymous_page_aggregate_buckets" in docker_log
    assert "interval '1095 days'" in docker_log
    assert "DELETE FROM public.public_visit_attributions" in docker_log
    assert "DELETE FROM public.client_acquisition_attributes" in docker_log
    assert "< now()" in docker_log
    assert "interval '1095 days'" in docker_log
    assert "billing_webhook_events" not in docker_log
    assert "metadata_json" not in docker_log


def test_retention_fails_closed_when_a_category_has_no_storage(tmp_path: Path) -> None:
    environment = _runtime(tmp_path)
    environment["GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_DIR"] = str(tmp_path / "retention-state-dir")
    environment["GRAF_PRODUCT_ANALYTICS_CLICKHOUSE_CONTAINER"] = "clickhouse-container"
    environment["GRAF_POSTHOG_ALERT_SCRIPT"] = str(tmp_path / "bin" / "stub-alert.sh")
    environment["FAKE_TABLE_MISSING"] = "1"

    result = _run(RETENTION_PATH, environment, "--execute")

    assert result.returncode == 1
    assert "retention_result=failed" in result.stdout
    assert "reason=retention_category_missing" in result.stdout
    state = (tmp_path / "retention-state-dir" / "retention-state").read_text(encoding="utf-8")
    assert "missing_category=anonymous_aggregate" in state
    assert "missing_category=visit_attribution" in state
    assert "missing_category=acquisition_attribute" in state
    assert "enforcement_verified=false" in state
    # A category without storage is never treated as retained forever.
    assert "retention_days=1095" in state
    assert (tmp_path / "alert.log").read_text(encoding="utf-8").strip() == "alert invoked"
    # The preflight failure must not issue a partial DELETE for an earlier
    # category. The database command log contains only schema probes.
    assert "DELETE FROM public." not in (tmp_path / "docker.log").read_text(encoding="utf-8")


def test_retention_fails_closed_when_an_age_column_is_missing(tmp_path: Path) -> None:
    environment = _runtime(tmp_path)
    environment["GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_DIR"] = str(tmp_path / "retention-state-dir")
    environment["GRAF_PRODUCT_ANALYTICS_CLICKHOUSE_CONTAINER"] = "clickhouse-container"
    environment["GRAF_POSTHOG_ALERT_SCRIPT"] = str(tmp_path / "bin" / "stub-alert.sh")
    environment["FAKE_COLUMN_MISSING"] = "1"

    result = _run(RETENTION_PATH, environment, "--execute")

    assert result.returncode == 1
    assert "reason=retention_schema_mismatch" in result.stdout
    state = (tmp_path / "retention-state-dir" / "retention-state").read_text(encoding="utf-8")
    assert "missing_category=anonymous_aggregate" in state
    assert "missing_category=visit_attribution" in state
    assert "missing_category=acquisition_attribute" in state
    assert "rows_deleted_total=0" in state
    assert "DELETE FROM public." not in (tmp_path / "docker.log").read_text(encoding="utf-8")


def test_retention_verifies_the_clickhouse_row_ttl(tmp_path: Path) -> None:
    environment = _runtime(tmp_path)
    environment["GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_DIR"] = str(tmp_path / "retention-state-dir")
    environment["GRAF_PRODUCT_ANALYTICS_CLICKHOUSE_CONTAINER"] = "clickhouse-container"
    environment["GRAF_POSTHOG_ALERT_SCRIPT"] = str(tmp_path / "bin" / "stub-alert.sh")
    environment["FAKE_CLICKHOUSE_TTL"] = "90"

    result = _run(RETENTION_PATH, environment, "--execute")

    assert result.returncode == 1
    assert "reason=clickhouse_ttl_not_enforced" in result.stdout
    state = (tmp_path / "retention-state-dir" / "retention-state").read_text(encoding="utf-8")
    assert "category=measurement_events retention_days=365 storage=clickhouse" in state
    assert "enforcement_verified=false" in state


def test_event_ttl_statement_targets_the_storage_table_for_365_days() -> None:
    sql = TTL_SQL_PATH.read_text(encoding="utf-8")
    assert "ALTER TABLE sharded_events" in sql
    assert "MODIFY TTL toDateTime(timestamp) + toIntervalDay({{RETENTION_DAYS}});" in sql
    assert "Distributed" in sql

    compose = COMPOSE_PATH.read_text(encoding="utf-8")
    assert "x-graf-clickhouse-retention:" in compose
    assert "retention_days: 365" in compose
    assert "enforcement: \"row_ttl_on_sharded_events\"" in compose
    assert "POSTHOG_EVENT_RETENTION_DAYS=365" in compose
    assert "apply-posthog-event-ttl.sh" in compose
    # The pre-existing provider retention setting keeps working.
    assert "POSTHOG_RETENTION_MIN_DAYS=90" in PRODUCTION_ENV_EXAMPLE.read_text(encoding="utf-8")
    assert "POSTHOG_EVENT_RETENTION_DAYS=365" in PRODUCTION_ENV_EXAMPLE.read_text(encoding="utf-8")


def test_event_ttl_applier_is_idempotent_and_verifies_the_result(tmp_path: Path) -> None:
    environment = _runtime(tmp_path)
    environment["GRAF_POSTHOG_CLICKHOUSE_CONTAINER"] = "clickhouse-container"

    dry_run = _run(TTL_APPLY_PATH, environment)
    assert dry_run.returncode == 0, dry_run.stderr
    assert "posthog_event_ttl_result=dry_run" in dry_run.stdout
    assert "toIntervalDay(365)" in dry_run.stdout
    assert "sharded_events" in dry_run.stdout

    applied = _run(TTL_APPLY_PATH, environment, "--execute")
    assert applied.returncode == 0, applied.stderr
    assert "posthog_event_ttl_result=pass" in applied.stdout
    assert "posthog_event_ttl_days=365" in applied.stdout
    assert "posthog_event_ttl_enforcement=row_ttl" in applied.stdout

    environment["FAKE_CLICKHOUSE_TTL"] = "30"
    rejected = _run(TTL_APPLY_PATH, environment, "--execute")
    assert rejected.returncode == 1
    assert "reason=ttl_not_verified" in rejected.stdout


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


def test_retention_script_targets_the_tables_and_columns_the_models_declare() -> None:
    """The retention run has to resolve the real tables, not plausible names.

    The script resolves every GRAF-stored category with
    ``to_regclass('public.<candidate>')``, which is an exact table name. A
    candidate that no model declares can never resolve, and then the category is
    reported as missing on every single run: legally required deletion never
    happens, the run fails, and analytics readiness stays blocked for good. This
    cross-check against the models themselves is what was missing, because the
    script's own execution test answers ``to_regclass`` from a stub and therefore
    passes for any candidate list.
    """

    from twobrain_rec_server.db.models.product_analytics import (
        AnonymousPageAggregateBucket,
        ClientAcquisitionAttribute,
        PublicVisitAttribution,
    )

    text = RETENTION_PATH.read_text(encoding="utf-8")

    def function_body(name: str) -> str:
        match = re.search(
            rf"^{name}\(\) \{{(.*?)^\}}", text, re.MULTILINE | re.DOTALL
        )
        assert match is not None, f"the script declares no {name}()"
        return match.group(1)

    tables_body = function_body("table_candidates_for")
    columns_body = function_body("timestamp_column_for")

    # The category name is the key the retention rules in
    # product_analytics/retention.py use, and it is also the argument the script
    # passes to both helpers.
    expected = {
        "anonymous_aggregate": (AnonymousPageAggregateBucket, "bucket_date"),
        "visit_attribution": (PublicVisitAttribution, "expires_at"),
        "acquisition_attribute": (ClientAcquisitionAttribute, "captured_at"),
    }

    def resolved(body: str, category: str) -> str:
        match = re.search(
            rf"^[ \t]*{category}\)[ \t]*printf[ \t]*'([^']*)'", body, re.MULTILINE
        )
        assert match is not None, f"{category} is absent from the script"
        return match.group(1).strip()

    for category, (model, age_column) in expected.items():
        table = model.__tablename__

        candidates = resolved(tables_body, category).split()
        assert candidates, f"{category} resolves to no table name at all"
        assert table in candidates, (
            f"{category} resolves to {candidates}, but the model declares {table!r}; "
            "to_regclass matches exact names, so this category would be reported "
            "missing and never purged"
        )

        column = resolved(columns_body, category)
        declared = {column.name for column in model.__table__.columns}
        assert column == age_column, (
            f"{category} purges by {column!r}, but the retention rule and this test "
            f"expect {age_column!r}"
        )
        assert column in declared, (
            f"{category} purges by {column!r}, which the model {table!r} does not "
            f"declare; it declares {sorted(declared)}"
        )

    # Migrations and model metadata must agree with the allowlist too. This is
    # intentionally source-level: the shell test double must not be able to
    # make a guessed table name look valid.
    model_text = PRODUCT_ANALYTICS_MODELS_PATH.read_text(encoding="utf-8")
    migration_text = "\n".join(path.read_text(encoding="utf-8") for path in PRODUCT_ANALYTICS_MIGRATIONS)
    expected_migration_columns = {
        "anonymous_page_aggregate_buckets": "bucket_date",
        "public_visit_attributions": "expires_at",
        "client_acquisition_attributes": "captured_at",
    }
    for table, age_column in expected_migration_columns.items():
        assert f'__tablename__ = "{table}"' in model_text
        assert f'"{table}"' in migration_text
        assert f'sa.Column("{age_column}"' in migration_text


def test_retention_scope_excludes_provider_event_metadata_and_provider_held_data() -> None:
    script = RETENTION_PATH.read_text(encoding="utf-8")
    assert "billing_webhook_events" not in script
    assert "metadata_json" not in script
    assert "provider-held" in script
    assert "DELETE FROM public.$table_name" in script
    assert "sharded_events" in script
    # The billing model still documents where provider-event metadata lives; it
    # must not accidentally become a product-analytics purge target.
    billing_model = BILLING_MODELS_PATH.read_text(encoding="utf-8")
    assert '__tablename__ = "billing_webhook_events"' in billing_model
    assert "metadata_json" in billing_model
