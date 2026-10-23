"""Contract tests for analytics retention, backup and restore (T024).

Scheduled tasks have to prove three things without a production run:

* a backup archives every inventory volume class as a verified local set, keeps
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
import json
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
    if os.environ.get("FAKE_VOLUME_LIST_FAIL") == "1" or ("--filter" in args and os.environ.get("FAKE_LABEL_LIST_FAIL") == "1"):
        sys.exit(7)
    for name in os.environ.get("FAKE_VOLUMES", "").split():
        print(name)
    sys.exit(0)
if args[:2] in (["volume", "create"], ["volume", "rm"]):
    sys.exit(0)
if args[:1] == ["inspect"]:
    if os.environ.get("FAKE_INSPECT_FAIL") == "1":
        sys.exit(7)
    for name in os.environ.get("FAKE_MOUNTED_VOLUMES", os.environ.get("FAKE_VOLUMES", "")).split():
        print(name)
    sys.exit(0)
if args[:1] == ["ps"] and "--filter" in args:
    if os.environ.get("FAKE_PROJECT_PS_FAIL") == "1":
        sys.exit(7)
    print("c" * 64)
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
            if os.environ.get("FAKE_ARCHIVE_LATE_FAIL") == name:
                sys.exit(7)
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
            "GRAF_POSTHOG_BACKUP_KEEP": "7",
            "GRAF_POSTHOG_BACKUP_MIN_COPIES": "2",
            "GRAF_POSTHOG_BACKUP_IMAGE": "alpine:3.20",
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
        assert "secret" not in text.lower().replace("secret_policy", "").replace("twobrain_runtime_secret_gid", ""), path.name
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
        assert "GRAF_POSTHOG_OFFSITE_COMMAND" not in BACKUP_ENV_EXAMPLE.read_text(encoding="utf-8")

    backup_service = (UNIT_DIR / "graf-posthog-backup.service").read_text(encoding="utf-8")
    assert "ExecStart=/usr/local/libexec/graf-posthog-backup.sh --execute" in backup_service
    assert "EnvironmentFile=-/etc/graf-posthog-backup.env" in backup_service
    assert "ReadWritePaths=-/var/backups/graf-posthog" in backup_service

    restore_service = (UNIT_DIR / "graf-posthog-restore-verify.service").read_text(encoding="utf-8")
    assert "ExecStart=/usr/local/libexec/graf-posthog-restore-verify.sh --execute" in restore_service

    retention_service = (UNIT_DIR / "graf-posthog-retention-enforce.service").read_text(encoding="utf-8")
    assert "ExecStart=/usr/local/libexec/graf-posthog-retention-enforce.sh --execute" in retention_service
    assert "EnvironmentFile=-/etc/graf-posthog-retention.env" in retention_service


def test_backup_archives_every_required_class_as_verified_local_set(tmp_path: Path) -> None:
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
    assert "offsite" not in result.stdout
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
    assert (backup_dir / ".complete").is_file()
    assert (backup_dir / "inventory.txt").read_bytes() == inventory.read_bytes()
    assert backup_dir.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o077 == 0 for p in backup_dir.iterdir())

    state = (tmp_path / "state" / "backup-state").read_text(encoding="utf-8")
    assert "last_attempt_result=pass" in state
    assert "copies_local=1" in state
    assert "backup_state_version=2" in state
    assert "backup_set_complete=true" in state
    assert f"last_success_reference={reference}" in state
    assert "product_impact=measurement_gap_only" in state
    assert state.count("last_success_epoch=") == 1


def _seed_complete_copy(directory: Path, inventory: Path, label: str) -> None:
    directory.mkdir(parents=True)
    (directory / 'inventory.txt').write_bytes(inventory.read_bytes())
    rows = []
    for volume in ('graf-posthog_postgres-data', 'graf-posthog_clickhouse-data', 'graf-posthog_objectstorage'):
        data = b'synthetic archive'
        (directory / (volume + '.tar.gz')).write_bytes(data)
        rows.append(f'volume={volume} bytes={len(data)} sha256={hashlib.sha256(data).hexdigest()}')
    manifest = ('backup_reference=' + label + '\n' + '\n'.join(rows)).encode()
    (directory / 'manifest.txt').write_bytes(manifest)
    (directory / '.complete').write_text(json.dumps({
        'version': 2, 'finished_epoch': int(time.time()) - 86400,
        'project': 'graf-posthog',
        'manifest_sha256': hashlib.sha256(manifest).hexdigest(),
        'inventory_sha256': hashlib.sha256(inventory.read_bytes()).hexdigest(),
    }))


def test_backup_rotates_only_verified_complete_sets(tmp_path: Path) -> None:
    inventory = _inventory(tmp_path)
    environment = _backup_environment(tmp_path, inventory)
    environment['FAKE_VOLUMES'] = 'graf-posthog_postgres-data graf-posthog_clickhouse-data graf-posthog_objectstorage'
    backups = tmp_path / 'backups'
    for day in range(1, 9):
        label = f'202601{day:02d}T023000Z'
        _seed_complete_copy(backups / label, inventory, label)
    # Incomplete/corrupt sets stay untouched and never count or evict good sets.
    incomplete = backups / '20260109T023000Z'
    incomplete.mkdir()
    corrupt = backups / '20260110T023000Z'
    _seed_complete_copy(corrupt, inventory, corrupt.name)
    (corrupt / 'graf-posthog_postgres-data.tar.gz').write_bytes(b'corrupt')
    result = _run(BACKUP_PATH, environment, '--execute')
    assert result.returncode == 0, result.stderr
    assert 'copies_local=7' in result.stdout
    assert not (backups / '20260101T023000Z').exists()
    assert not (backups / '20260102T023000Z').exists()
    assert incomplete.is_dir() and corrupt.is_dir()
    assert 'retention_deleted=20260101T023000Z' in result.stdout
    assert 'result=retention_deleted reference=20260101T023000Z' in (tmp_path / 'logger.log').read_text()


@pytest.mark.parametrize('change', ['inventory', 'project', 'volumes'])
def test_backup_counts_only_copies_of_current_scope(tmp_path: Path, change: str) -> None:
    inventory = _inventory(tmp_path)
    environment = _backup_environment(tmp_path, inventory)
    old = tmp_path / 'backups/20260101T023000Z'
    _seed_complete_copy(old, inventory, old.name)
    if change == 'inventory':
        inventory.write_text(inventory.read_text() + 'graf-posthog_new-data?\n')
    elif change == 'project':
        environment['GRAF_POSTHOG_PROJECT'] = 'replacement-project'
        environment['FAKE_VOLUMES'] = 'replacement-project_postgres-data replacement-project_clickhouse-data replacement-project_objectstorage'
    result = _run(BACKUP_PATH, environment, '--execute')
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'copies_local=1' in result.stdout
    assert old.is_dir(), 'Incompatible historical copies must stay intact'
    reference = next(line.split('=', 1)[1] for line in result.stdout.splitlines() if line.startswith('backup_reference='))
    current = tmp_path / 'backups' / reference
    assert (current / 'inventory.txt').read_bytes() == inventory.read_bytes()
    assert json.loads((current / '.complete').read_text())['inventory_sha256'] == hashlib.sha256(inventory.read_bytes()).hexdigest()


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


def test_backup_fails_closed_for_unclassified_project_volume(tmp_path: Path) -> None:
    inventory = _inventory(tmp_path)
    environment = _backup_environment(tmp_path, inventory)
    environment['FAKE_VOLUMES'] += ' graf-posthog_unreviewed-data'
    result = _run(BACKUP_PATH, environment, '--execute')
    assert result.returncode == 1
    assert 'reason=project_volume_unclassified' in result.stdout
    assert not list((tmp_path / 'backups').glob('*/.complete'))


def test_failed_archive_does_not_publish_complete_set_or_rotate(tmp_path: Path) -> None:
    inventory = _inventory(tmp_path)
    environment = _backup_environment(tmp_path, inventory)
    backups = tmp_path / 'backups'
    for day in range(1, 9):
        label = f'202601{day:02d}T023000Z'
        _seed_complete_copy(backups / label, inventory, label)
    foreign = backups / '.foreign.incomplete'
    foreign.mkdir()
    (foreign / 'keep').write_bytes(b'previous attempt')
    environment['FAKE_ARCHIVE_LATE_FAIL'] = 'graf-posthog_clickhouse-data.tar.gz'
    result = _run(BACKUP_PATH, environment, '--execute')
    assert result.returncode == 1
    assert 'reason=volume_archive_failed' in result.stdout
    assert 'volume_archived=graf-posthog_postgres-data' in result.stdout
    assert list(backups.glob('.*.incomplete')) == [foreign]
    assert (foreign / 'keep').read_bytes() == b'previous attempt'
    assert len(list(backups.glob('20*/.complete'))) == 8
    state = (tmp_path / 'state/backup-state').read_text()
    assert 'last_attempt_result=failed' in state
    assert 'backup_set_complete=false' in state


@pytest.mark.parametrize("failure", ["volume_list", "project_list", "container_list", "mount_inspect", "anonymous_mount", "state_write", "inventory", "rotation"])
def test_failed_attempt_invalidates_previous_pass_and_always_alerts(tmp_path: Path, failure: str) -> None:
    inventory = _inventory(tmp_path)
    environment = _backup_environment(tmp_path, inventory)
    state_file = tmp_path / "state/backup-state"
    state_file.parent.mkdir()
    state_file.write_text(
        "backup_state_version=2\nbackup_set_complete=true\nlast_attempt_result=pass\n"
        f"last_success_epoch={int(time.time()) - 60}\ncopies_local=2\n"
    )
    if failure == "volume_list":
        environment["FAKE_VOLUME_LIST_FAIL"] = "1"
    elif failure == "project_list":
        environment["FAKE_LABEL_LIST_FAIL"] = "1"
    elif failure == "container_list":
        environment["FAKE_PROJECT_PS_FAIL"] = "1"
    elif failure == "mount_inspect":
        environment["FAKE_INSPECT_FAIL"] = "1"
    elif failure == "anonymous_mount":
        environment["FAKE_MOUNTED_VOLUMES"] = environment["FAKE_VOLUMES"] + " " + "a" * 64
    elif failure == "inventory":
        inventory.unlink()
    elif failure == "state_write":
        _write_executable(tmp_path / "bin/python3", """#!{python}
import os, sys
body = sys.stdin.read()
if "os.replace(*sys.argv[1:])" in body:
    sys.exit(9)
os.execv(sys.executable, [sys.executable, "-c", body, *sys.argv[2:]])
""")
    else:
        environment['FAKE_VOLUMES'] = 'graf-posthog_postgres-data graf-posthog_clickhouse-data graf-posthog_objectstorage'
        for day in range(1, 9):
            label = f"202601{day:02d}T023000Z"
            _seed_complete_copy(tmp_path / "backups" / label, inventory, label)
        _write_executable(tmp_path / "bin/rm", """#!{python}
import os, sys
if "-rf" in sys.argv:
    sys.exit(7)
os.execv("/bin/rm", ["/bin/rm", *sys.argv[1:]])
""")
    result = _run(BACKUP_PATH, environment, "--execute")
    assert result.returncode != 0, result.stdout
    assert "backup_result=failed" in result.stdout
    assert "backup_result=pass" not in result.stdout
    assert (tmp_path / "alert.log").read_text().strip() == "alert invoked"
    state = state_file.read_text() if state_file.exists() else ""
    assert "last_attempt_result=pass" not in state
    evidence = provider_readiness.collect_analytics_operations_evidence({
        provider_readiness.BACKUP_STATE_FILE_ENV: str(state_file),
    })
    assert evidence.backup_result != "pass"
    if failure == "rotation":
        assert len(list((tmp_path / "backups").glob("20*/.complete"))) == 9
        assert "reason=retention_delete_failed" in result.stdout


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


def test_storage_growth_measurement_fails_closed_without_runtime_metadata(tmp_path: Path) -> None:
    environment = _runtime(tmp_path)
    environment["GRAF_POSTHOG_STORAGE_STATE_FILE"] = str(tmp_path / "storage-state")
    environment["GRAF_POSTHOG_ANALYTICS_PATH"] = str(tmp_path)
    environment["GRAF_APP_DIR"] = str(tmp_path)
    result = _run(GROWTH_PATH, environment)
    assert result.returncode == 1, result.stderr
    assert "storage_result=incomplete" in result.stdout
    assert "analytics_storage_bytes=unknown" in result.stdout
    assert "storage_growth_result=incomplete" in result.stdout
    assert "storage_growth_result=pass" not in result.stdout
    assert str(tmp_path) not in result.stdout
    assert str(tmp_path) not in (tmp_path / "storage-state.json").read_text()
    assert "analytics_filesystem_total" not in result.stdout


def _storage_collector():
    import importlib.util
    spec = importlib.util.spec_from_file_location("posthog_storage", REPO_ROOT / "infra/scripts/posthog-storage.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _capacity_evaluator():
    import importlib.util
    spec = importlib.util.spec_from_file_location("posthog_capacity", REPO_ROOT / "infra/scripts/posthog-capacity.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _capacity_inputs():
    capacity = _capacity_evaluator()
    now = 1792634400
    classes = dict.fromkeys(capacity.CLASSES, 0)
    classes['events'] = 10_000
    sample = {'storage_sample_version': 2, 'recorded_at_epoch': now,
              'inventory_version': 'a' * 64, 'result': 'complete', 'reasons': [],
              'classes': classes, 'analytics_storage_bytes': 10_000,
              'filesystems': [{'identity': 'b' * 64, 'total_bytes': 1000,
                               'available_bytes': 500, 'roles': ['analytics', 'host']}]}
    budget = {'budget_state_version': 1, 'status': 'accepted', 'role': 'infra_operator',
              'inventory_version': 'a' * 64, 'budget_version': 'c' * 64,
              'config_version': 'd' * 64, 't097_evidence_sha256': 'e' * 64,
              'accepted_at_epoch': now - 1, 'review_deadline_epoch': now + 3600,
              'analytics_budget_bytes': capacity.INITIAL_CEILING}
    return capacity, sample, budget, now


@pytest.mark.parametrize(('available', 'disable', 'host'), [
    (200, False, False), (199, True, False), (100, True, False), (99, True, True),
])
def test_capacity_uses_exact_bytes_at_shared_filesystem_boundaries(available, disable, host):
    capacity, sample, budget, now = _capacity_inputs()
    sample['filesystems'][0]['available_bytes'] = available
    decision = capacity.evaluate(sample, budget, now=now, config_version='d' * 64)
    assert decision['input_verified'] and decision['budget_accepted']
    assert ('analytics_storage' in decision['disable_reasons']) is disable
    assert ('host_disk' in decision['host_reasons']) is host
    assert decision['capacity_ready'] is (not disable)
    assert len(decision['filesystems']) == 1


@pytest.mark.parametrize('delta', [-1, 0, 1])
def test_capacity_budget_boundary_and_combined_causes(delta):
    capacity, sample, budget, now = _capacity_inputs()
    sample['analytics_storage_bytes'] = capacity.INITIAL_CEILING + delta
    sample['classes']['events'] = sample['analytics_storage_bytes']
    sample['filesystems'][0]['available_bytes'] = 99
    decision = capacity.evaluate(sample, budget, now=now, config_version='d' * 64)
    assert ('analytics_storage_budget' in decision['disable_reasons']) is (delta >= 0)
    assert 'analytics_storage' in decision['disable_reasons']
    assert decision['host_reasons'] == ['host_disk']


@pytest.mark.parametrize('age', [-1, 0, 119, 120])
def test_capacity_sample_age_is_nonnegative_and_strictly_below_120(age):
    capacity, sample, budget, now = _capacity_inputs()
    sample['recorded_at_epoch'] = now - age
    sample['filesystems'][0]['available_bytes'] = 99
    decision = capacity.evaluate(sample, budget, now=now, config_version='d' * 64)
    assert decision['input_verified'] is (0 <= age < 120)
    assert bool(decision['disable_reasons']) is (0 <= age < 120)
    assert ('capacity_input_unverified' in decision['analytics_reasons']) is (not 0 <= age < 120)


@pytest.mark.parametrize('change', [
    {'status': 'pending'}, {'role': 'product_owner'}, {'accepted_at_epoch': 1792634401},
    {'review_deadline_epoch': 1792634400}, {'review_deadline_epoch': 1999999999},
    {'inventory_version': 'f' * 64}, {'config_version': 'f' * 64},
    {'t097_evidence_sha256': ''}, {'budget_version': ''},
    {'analytics_budget_bytes': 0}, {'analytics_budget_bytes': 128 * 1024**3 + 1},
    {'budget_state_version': True},
])
def test_capacity_unaccepted_budget_keeps_readiness_closed_and_known_space_breach(change):
    capacity, sample, budget, now = _capacity_inputs()
    sample['filesystems'][0]['available_bytes'] = 99
    decision = capacity.evaluate(sample, {**budget, **change}, now=now, config_version='d' * 64)
    assert not decision['budget_accepted'] and not decision['capacity_ready']
    assert 'capacity_budget_unverified' in decision['analytics_reasons']
    assert decision['disable_reasons'] == ['analytics_storage']


def test_capacity_incomplete_sizes_and_separate_filesystems_remain_distinct():
    capacity, sample, budget, now = _capacity_inputs()
    sample['filesystems'] = [
        {'identity': 'b' * 64, 'total_bytes': 1000, 'available_bytes': 500, 'roles': ['analytics']},
        {'identity': 'f' * 64, 'total_bytes': 1000, 'available_bytes': 99, 'roles': ['host']},
    ]
    decision = capacity.evaluate(sample, budget, now=now, config_version='d' * 64)
    assert decision['capacity_ready'] and decision['disable_reasons'] == []
    assert decision['host_reasons'] == ['host_disk']
    sample['result'] = 'incomplete'
    sample['filesystems'][0]['available_bytes'] = 199
    decision = capacity.evaluate(sample, budget, now=now, config_version='d' * 64)
    assert not decision['capacity_ready'] and not decision['input_verified']
    assert decision['disable_reasons'] == ['analytics_storage']
    assert decision['analytics_storage_bytes'] is None
    assert capacity.evaluate(None, None, now=now, config_version='')['analytics_reasons'] == [
        'capacity_budget_unverified', 'capacity_input_unverified',
    ]


def test_capacity_invalid_metadata_never_becomes_ready_or_erases_known_low_space():
    from copy import deepcopy
    capacity, sample, budget, now = _capacity_inputs()
    for key, value in [('classes', []), ('analytics_storage_bytes', True),
                       ('inventory_version', 'bad'), ('filesystems', []),
                       ('reasons', ['runtime_mount_unclassified']), ('storage_sample_version', True)]:
        invalid = {**sample, key: value}
        assert not capacity.evaluate(invalid, budget, now=now, config_version='d' * 64)['capacity_ready']
    duplicate = deepcopy(sample)
    duplicate['filesystems'].append({**duplicate['filesystems'][0], 'available_bytes': 99})
    decision = capacity.evaluate(duplicate, budget, now=now, config_version='d' * 64)
    assert not decision['input_verified']
    assert decision['disable_reasons'] == ['analytics_storage']
    assert decision['host_reasons'] == ['host_disk']


def test_protection_requires_durable_request_and_verified_runtime_before_manual_restoration(tmp_path: Path):
    capacity, sample, budget, now = _capacity_inputs()
    path = tmp_path / 'protection-state.json'
    runtime = [f'{key}={value}' for key, value in capacity.DISABLED_ENV.items()]
    with pytest.raises(ValueError, match='protection_request_required'):
        capacity.transition(path, [], 'protected', now=now, runtime_env=runtime)
    assert capacity.transition(path, ['analytics_storage'], 'protection_requested', now=now - 20) == 'protection_requested'
    incident = json.loads(path.read_text())['incident_id']
    with pytest.raises(ValueError, match='readback_unverified'):
        capacity.transition(path, [], 'protected', now=now, runtime_env=[])
    assert json.loads(path.read_text())['status'] == 'protection_requested'
    assert capacity.transition(path, [], 'apply_failed', now=now - 10) == 'apply_failed'
    assert capacity.transition(path, [], 'protected', now=now, runtime_env=runtime) == 'protected'
    sample['growth'] = {'result': 'measured', 'interval_seconds': 86400, 'end_epoch': now,
                        'bytes_per_day': dict.fromkeys(capacity.CLASSES, 1)}
    receipt = {'restore_receipt_version': 1, 'incident_id': incident, 'role': 'infra_operator',
               'approved_at_epoch': now, 'expires_at_epoch': now + 300,
               'config_version': 'd' * 64, 'budget_version': 'c' * 64,
               'runtime_env_sha256': hashlib.sha256(json.dumps(capacity.DISABLED_ENV, sort_keys=True).encode()).hexdigest(),
               'proofs': dict.fromkeys(['growth_review', 'expansion_review', 'runtime_review',
                                       'basis_consent_review', 'provider_smoke', 'page_validation'], 'f' * 64)}
    for invalid in ({**receipt, 'incident_id': '0' * 32}, {**receipt, 'config_version': '0' * 64},
                    {**receipt, 'expires_at_epoch': now}, {**receipt, 'approved_at_epoch': now + 1},
                    {**receipt, 'proofs': {}}, {**receipt, 'restore_receipt_version': True}):
        with pytest.raises(ValueError):
            capacity.restore(path, invalid, sample, budget, runtime, now=now, config_version='d' * 64)
        assert json.loads(path.read_text())['status'] == 'protected'
    with pytest.raises(ValueError, match='readback_unverified'):
        capacity.restore(path, receipt, sample, budget, [*runtime, runtime[0]], now=now, config_version='d' * 64)
    assert capacity.restore(path, receipt, sample, budget, runtime, now=now, config_version='d' * 64) == 'observed'
    assert json.loads(path.read_text())['closed_incident_id'] == incident
    capacity.transition(path, ['analytics_storage'], 'protection_requested', now=now)
    with pytest.raises(ValueError):
        capacity.restore(path, receipt, sample, budget, runtime, now=now, config_version='d' * 64)


def test_protection_request_write_failure_does_not_claim_success(tmp_path: Path, monkeypatch):
    capacity = _capacity_evaluator()
    def failed_write(*args):
        raise OSError('synthetic state write failure')
    monkeypatch.setattr(capacity.runpy, 'run_path', lambda *args: {'atomic_json': failed_write})
    with pytest.raises(OSError):
        capacity.transition(tmp_path / 'state', ['analytics_storage'], 'protection_requested', now=1792634400)
    assert not (tmp_path / 'state').exists()


def test_allocated_storage_counts_sparse_files_hardlinks_archives_once(tmp_path: Path) -> None:
    import os
    collector = _storage_collector()
    events = tmp_path / "events"
    backups = tmp_path / "backups"
    events.mkdir()
    backups.mkdir()
    sparse = events / "sparse"
    with sparse.open("wb") as stream:
        stream.seek(8 * 1024 * 1024)
        stream.write(b"x")
    os.link(sparse, events / "alias")
    for name in ("complete.tar", "failed.tar", "staging.tar"):
        (backups / name).write_bytes(b"archive" * 1000)
    amounts, roots = collector.allocated([("events", events), ("events", events), ("backup_artifacts", backups)])
    assert amounts["events"] == (events.stat().st_blocks + sparse.stat().st_blocks) * 512
    # Allocation may be dense on APFS; the measured blocks, not logical length, are authoritative.
    assert amounts["backup_artifacts"] == sum(p.stat().st_blocks * 512 for p in [backups, *backups.iterdir()])
    assert len(roots) == 2
    assert sum(amounts.values()) == amounts["events"] + amounts["backup_artifacts"]


def test_allocated_storage_rejects_cross_class_overlap_links_and_missing(tmp_path: Path) -> None:
    import os
    collector = _storage_collector()
    root = tmp_path / "root"
    root.mkdir()
    file = root / "data"
    file.write_bytes(b"x")
    for roots in ([('events', root), ('relational', file)], [('events', root), ('unknown', root)]):
        with pytest.raises(collector.Incomplete):
            collector.allocated(roots)
    other = tmp_path / "other"
    os.link(file, other)
    with pytest.raises(collector.Incomplete):
        collector.allocated([('events', root), ('relational', other)])
    link = root / "link"
    link.symlink_to(file)
    amounts, _ = collector.allocated([('events', root)])
    assert amounts['events'] == sum(p.lstat().st_blocks * 512 for p in (root, file, link))
    link.unlink()
    link.symlink_to(other)
    with pytest.raises(collector.Incomplete):
        collector.allocated([('events', root)])
    link.unlink()
    link.symlink_to(root / 'missing')
    with pytest.raises(collector.Incomplete):
        collector.allocated([('events', root)])
    with pytest.raises(OSError):
        collector.allocated([('events', tmp_path / 'missing')])


def test_growth_requires_comparable_day_and_keeps_archive_decrease_visible() -> None:
    collector = _storage_collector()
    first = {'inventory_version': 'a', 'recorded_at_epoch': 100000,
             'classes': dict.fromkeys(collector.CLASSES, 100)}
    sample = {**first, 'recorded_at_epoch': 186400, 'classes': {**first['classes'], 'events': 300, 'backup_artifacts': 50}}
    growth, anchor = collector.measured_growth(first, {}, 100000)
    assert growth['result'] == 'pending'
    early, unchanged = collector.measured_growth(sample, anchor, 186399)
    assert early['result'] == 'pending'
    assert unchanged['recorded_at_epoch'] == 100000
    growth, anchor = collector.measured_growth(sample, anchor, 186400)
    assert growth['result'] == 'decrease_requires_review'
    assert growth['archive_bytes_per_day'] == -50
    assert growth['live_bytes_per_day'] == 200
    assert growth['interval_seconds'] == 86400
    assert collector.measured_growth(sample, anchor, 186401)[0] == growth
    assert collector.measured_growth({**sample, 'inventory_version': 'b'}, anchor, 300000)[0]['result'] == 'pending'
    assert collector.measured_growth(sample, anchor, 186399)[0]['reason'] == 'growth_anchor_future'
    for invalid in ([], {**anchor, 'recorded_at_epoch': 'bad'},
                    {**anchor, 'classes': []}, {**anchor, 'last_growth': {'result': 'pass'}}):
        assert collector.measured_growth(sample, invalid, 186401)[0]['result'] == 'incomplete'
        assert collector.measured_growth(sample, invalid, 300000)[0]['result'] == 'incomplete'


def test_relation_inventory_covers_analytics_models() -> None:
    import inspect

    from twobrain_rec_server.db.models import product_analytics
    inventory = (REPO_ROOT / 'infra/posthog/storage-relations.txt').read_text()
    for _, model in inspect.getmembers(product_analytics, inspect.isclass):
        if hasattr(model, '__tablename__'):
            assert 'public.' + model.__tablename__ in inventory


def test_collector_shared_filesystem_is_sampled_once_and_first_growth_is_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
) -> None:
    import sys
    collector = _storage_collector()
    events = tmp_path / 'events'
    backups = tmp_path / 'backups'
    events.mkdir()
    backups.mkdir()
    (events / 'block').write_bytes(b'x' * 8192)
    monkeypatch.setattr(collector, 'runtime_roots', lambda *args: ([('events', events)], 'mount-v1'))
    monkeypatch.setattr(collector, 'graf_relation_roots', lambda *args: ([], 'relations-v1', 0, ['public.network_access_metadata']))
    monkeypatch.setenv('GRAF_POSTHOG_STORAGE_STATE_FILE', str(tmp_path / 'state'))
    monkeypatch.setenv('GRAF_POSTHOG_BACKUP_DIR', str(backups))
    monkeypatch.setenv('GRAF_APP_DIR', str(tmp_path))
    monkeypatch.setenv('GRAF_POSTHOG_ANALYTICS_PATH', str(events))
    monkeypatch.setattr(sys, 'argv', ['posthog-storage.py'])
    probes = []
    filesystem = collector.filesystem
    def observed(path):
        probes.append(path)
        return filesystem(path)
    monkeypatch.setattr(collector, 'filesystem', observed)
    assert collector.main() == 0
    sample = json.loads((tmp_path / 'state.json').read_text())
    assert len(probes) == len(sample['filesystems']) == 1
    assert set(sample['filesystems'][0]['roles']) == {'analytics', 'host'}
    assert sample['analytics_storage_bytes'] == sum(sample['classes'].values())
    assert sample['growth']['result'] == 'pending'
    output = capsys.readouterr().out
    assert 'projected_bytes_12_months=unknown' in output
    assert str(tmp_path) not in output


@pytest.mark.parametrize('failure', ['runtime_mount', 'required_volume', 'relations', 'relation_missing', 'backups'])
def test_incomplete_collector_keeps_discovered_low_space(tmp_path: Path, monkeypatch, failure: str) -> None:
    collector = _storage_collector()
    capacity, _, budget, _ = _capacity_inputs()
    events = tmp_path / 'events'
    events.mkdir()
    runtime_roots = collector.runtime_roots
    monkeypatch.setattr(collector, 'runtime_roots', lambda *args: ([('events', events)], 'mount-v1'))
    if failure in ('runtime_mount', 'required_volume'):
        # Use the real discovery function with metadata-only Docker replies.
        monkeypatch.setattr(collector, 'runtime_roots', runtime_roots)
        monkeypatch.setattr(collector, 'command', lambda *args: (
            'container' if args[1] == 'ps' else json.dumps([{
                'Config': {'Labels': {'com.docker.compose.service': 'db'}},
                'Mounts': [{'Type': 'volume', 'Name': 'synthetic', 'Source': str(events),
                            'Destination': '/data'}] + ([{'Type': 'bind', 'Source': str(tmp_path),
                            'Destination': '/unknown'}] if failure == 'runtime_mount' else []),
            }]) if args[1] == 'inspect' else ''))
        (tmp_path / 'storage-mounts.txt').write_text('db /data relational\n')
        (tmp_path / 'backup-volumes.txt').write_text('graf-posthog_required\n')
        monkeypatch.setenv('GRAF_POSTHOG_STORAGE_INVENTORY_DIR', str(tmp_path))
    def relations(*args):
        if failure == 'relations':
            raise collector.Incomplete('metadata_probe_failed')
        return [], 'relations-v1', 0, []
    if failure == 'relation_missing':
        monkeypatch.setattr(collector, 'runtime_roots', lambda *args: ([], 'mount-v1'))
        monkeypatch.setattr(collector, 'command', lambda *args: (
            'container' if args[1] == 'ps' else json.dumps([{
                'Mounts': [{'Destination': '/data', 'Source': str(events)}],
            }]) if args[1] == 'inspect' else json.dumps({
                'data_directory': '/data', 'present': [], 'files': [],
            })))
        (tmp_path / 'storage-relations.txt').write_text('public.required\n')
        monkeypatch.setenv('GRAF_POSTHOG_STORAGE_INVENTORY_DIR', str(tmp_path))
    else:
        monkeypatch.setattr(collector, 'graf_relation_roots', relations)
    monkeypatch.setenv('GRAF_POSTHOG_STORAGE_STATE_FILE', str(tmp_path / 'state'))
    monkeypatch.setenv('GRAF_POSTHOG_BACKUP_DIR', str(tmp_path / 'missing'))
    monkeypatch.setenv('GRAF_APP_DIR', str(tmp_path))
    monkeypatch.setenv('GRAF_POSTHOG_ANALYTICS_PATH', str(tmp_path))
    monkeypatch.setattr(sys, 'argv', ['posthog-storage.py'])
    real_stat = Path.stat
    from types import SimpleNamespace
    monkeypatch.setattr(Path, 'stat', lambda path, *args, **kwargs: (
        SimpleNamespace(st_dev=-1) if path == events else real_stat(path, *args, **kwargs)))
    monkeypatch.setattr(collector, 'filesystem', lambda path: {
        'identity': ('e' if path == events else 'f') * 64,
        'total_bytes': 1000, 'available_bytes': 199 if path == events else 500,
    })
    assert collector.main() == 1
    sample = json.loads((tmp_path / 'state.json').read_text())
    assert sample['result'] == 'incomplete'
    assert any(fs['available_bytes'] == 199 for fs in sample['filesystems'])
    now = sample['recorded_at_epoch']
    result = capacity.evaluate(sample, budget, now=now, config_version='d' * 64)
    assert 'analytics_storage' in result['disable_reasons']
    assert 'capacity_input_unverified' in result['analytics_reasons']


def test_installed_guard_constrains_collector_state_to_writable_sandbox(tmp_path: Path) -> None:
    import os
    import shlex
    service = (UNIT_DIR / 'graf-posthog-runtime-guard.service').read_text()
    command = shlex.split(next(line.split('=', 1)[1] for line in service.splitlines() if line.startswith('ExecStart=')))
    result = subprocess.run(command[:-1] + [sys.executable, '-c',
        'import os,json; print(json.dumps({k:os.environ.get(k) for k in ("GRAF_POSTHOG_STORAGE_STATE_DIR","GRAF_POSTHOG_STORAGE_STATE_FILE")}))'],
        env={**os.environ, 'GRAF_POSTHOG_STORAGE_STATE_DIR': str(tmp_path),
             'GRAF_POSTHOG_STORAGE_STATE_FILE': str(tmp_path / 'override')}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert observed == {'GRAF_POSTHOG_STORAGE_STATE_DIR': '/var/lib/graf-posthog-storage',
                        'GRAF_POSTHOG_STORAGE_STATE_FILE': '/var/lib/graf-posthog-storage/storage-growth-state'}


def test_retention_receipt_has_readonly_api_mount_and_reader_permissions(tmp_path: Path) -> None:
    import yaml
    compose = yaml.safe_load((REPO_ROOT / 'infra/docker-compose.yml').read_text())
    api = compose['services']['rec-api']
    assert '/var/lib/graf-posthog-retention:/run/graf-analytics-retention:ro' in api['volumes']
    assert api['environment']['GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_DIR'] == '/run/graf-analytics-retention'
    environment = _runtime(tmp_path)
    environment['GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_DIR'] = str(tmp_path / 'state')
    result = _run(RETENTION_PATH, environment, '--execute')
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / 'state').stat().st_mode & 0o777 == 0o750
    assert (tmp_path / 'state/retention-state').stat().st_mode & 0o777 == 0o640


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
    assert evidence.backup_set_complete is True
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


def test_custom_project_rejects_old_project_volumes(tmp_path: Path) -> None:
    inventory = _inventory(tmp_path)
    environment = _backup_environment(tmp_path, inventory)
    environment['GRAF_POSTHOG_PROJECT'] = 'replacement-project'
    result = _run(BACKUP_PATH, environment, '--execute')
    assert result.returncode != 0, result.stdout
    assert 'backup_result=pass' not in result.stdout
    assert not list((tmp_path / 'backups').glob('*/.complete'))


@pytest.mark.parametrize('collision', ['.incomplete', 'final'])
def test_backup_preserves_reference_collision(tmp_path: Path, collision: str) -> None:
    inventory = _inventory(tmp_path)
    environment = _backup_environment(tmp_path, inventory)
    label = '20261023T120000Z'
    _write_executable(tmp_path / 'bin/date', """#!{python}
import os, sys
if sys.argv[1:] == ['-u', '+%Y%m%dT%H%M%SZ']:
    print('20261023T120000Z')
else:
    os.execv('/bin/date', ['/bin/date', *sys.argv[1:]])
""")
    directory = tmp_path / 'backups' / ('.' + label + collision if collision == '.incomplete' else label)
    directory.mkdir(parents=True)
    (directory / 'keep').write_bytes(b'not owned')
    result = _run(BACKUP_PATH, environment, '--execute')
    assert result.returncode != 0
    assert 'reason=backup_reference_exists' in result.stdout
    assert (directory / 'keep').read_bytes() == b'not owned'
    assert 'run --rm' not in (tmp_path / 'docker.log').read_text()


@pytest.mark.parametrize('failure', ['after_rename', 'cleanup'])
def test_backup_failure_preserves_published_set_and_reports_cleanup_failure(tmp_path: Path, failure: str) -> None:
    inventory = _inventory(tmp_path)
    environment = _backup_environment(tmp_path, inventory)
    if failure == 'after_rename':
        _write_executable(tmp_path / 'bin/python3', """#!{python}
import os, sys
body = sys.stdin.read()
if 'os.rename(stage, target)' in body:
    sys.argv = ['-', *sys.argv[2:]]
    exec(body)
    sys.exit(7)
os.execv(sys.executable, [sys.executable, '-c', body, *sys.argv[2:]])
""")
    else:
        environment['FAKE_ARCHIVE_LATE_FAIL'] = 'graf-posthog_clickhouse-data.tar.gz'
        _write_executable(tmp_path / 'bin/rm', """#!{python}
import os, sys
if any(arg.endswith('.incomplete') for arg in sys.argv[1:]):
    sys.exit(7)
os.execv('/bin/rm', ['/bin/rm', *sys.argv[1:]])
""")
    result = _run(BACKUP_PATH, environment, '--execute')
    assert result.returncode != 0
    assert 'backup_result=pass' not in result.stdout
    assert 'last_attempt_result=failed' in (tmp_path / 'state/backup-state').read_text()
    assert (tmp_path / 'alert.log').read_text().strip() == 'alert invoked'
    if failure == 'after_rename':
        assert len(list((tmp_path / 'backups').glob('20*/.complete'))) == 1
        assert not list((tmp_path / 'backups').glob('.*.incomplete'))
    else:
        assert 'result=backup_staging_cleanup_failed' in (tmp_path / 'logger.log').read_text()
        assert len(list((tmp_path / 'backups').glob('.*.incomplete'))) == 1


@pytest.mark.parametrize('gid', ['', '0', '123', '01001', '2147483648', 'bad', '4321'])
def test_runbook_persists_selected_gid_for_all_state_writers(tmp_path: Path, gid: str) -> None:
    runbook = RUNBOOK_PATH.read_text()
    section = runbook.split('### Подготовка общей группы чтения состояния', 1)[1]
    block = section.split('```bash\n', 1)[1].split('```', 1)[0]
    environment = _runtime(tmp_path)
    if gid:
        environment['TWOBRAIN_RUNTIME_SECRET_GID'] = gid
    files = []
    original = 'KEEP=value with spaces\nTWOBRAIN_RUNTIME_SECRET_GID=1001\nTWOBRAIN_RUNTIME_SECRET_GID=2222\n'
    for name in ('runtime-guard', 'backup', 'retention'):
        path = tmp_path / f'graf-posthog-{name}.env'
        path.write_text(original)
        files.append(path)
        block = block.replace(f'/etc/graf-posthog-{name}.env', str(path))
    _write_executable(tmp_path / 'bin/install', """#!{python}
import os, shutil, sys
assert sys.argv[1:7] == ['-o', 'root', '-g', 'root', '-m', '0600']
shutil.copyfile(*sys.argv[7:])
os.chmod(sys.argv[8], 0o600)
""")
    result = subprocess.run([BASH, '-c', block], env=environment, capture_output=True, text=True)
    if gid != '4321':
        assert result.returncode != 0
        assert all(path.read_text() == original for path in files)
    else:
        assert result.returncode == 0, result.stderr
        for selected in ('4321', '5432'):
            environment['TWOBRAIN_RUNTIME_SECRET_GID'] = selected
            result = subprocess.run([BASH, '-c', block], env=environment, capture_output=True, text=True)
            assert result.returncode == 0, result.stderr
            for path in files:
                assert path.read_text() == f'KEEP=value with spaces\nTWOBRAIN_RUNTIME_SECRET_GID={selected}\n'
                assert path.stat().st_mode & 0o777 == 0o600
