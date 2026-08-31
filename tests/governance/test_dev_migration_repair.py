from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "dev_migration_repair", ROOT / "scripts" / "dev-migration-repair.py"
)
assert SPEC and SPEC.loader
dev_migration_repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dev_migration_repair)


SOURCE_SHA = "a" * 40
DEV_DATABASE_URL = "postgresql://twobrain_rec:dev-secret@127.0.0.1:54329/twobrain_rec"


def migration_root(tmp_path: Path) -> Path:
    versions = tmp_path / "apps/server/src/twobrain_rec_server/db/migrations/versions"
    versions.mkdir(parents=True)
    (versions / "0074_linked_workspace_and_merge_proofs.py").write_text(
        'revision: str = "0074_linked_workspace_proofs"\n'
        "down_revision: str | None = None\n",
        encoding="utf-8",
    )
    (versions / "0085_merge_summary_mediascribe_and_processing_recovery.py").write_text(
        'revision: str = "0085_merge_summary_mediascribe"\n'
        'down_revision: str = "0074_linked_workspace_proofs"\n',
        encoding="utf-8",
    )
    return tmp_path


def probe_args(output: Path, database_url: str | None = DEV_DATABASE_URL) -> Namespace:
    return Namespace(target="dev-existing", database_url=database_url, output=output)


def test_dev_existing_reads_known_drift_from_allowed_local_postgres(monkeypatch, tmp_path, capsys):
    migration_root(tmp_path)
    monkeypatch.setattr(dev_migration_repair, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(dev_migration_repair, "source_sha", lambda _root: SOURCE_SHA)

    def fake_run(command, **kwargs):
        assert command[-1] == dev_migration_repair.ALEMBIC_REVISION_QUERY
        assert kwargs["env"]["PGHOST"] == "127.0.0.1"
        assert kwargs["env"]["PGPORT"] == "54329"
        assert kwargs["env"]["PGDATABASE"] == "twobrain_rec"
        return subprocess.CompletedProcess(command, 0, stdout="0074_calendar_sync_maintenance\n", stderr="")

    monkeypatch.setattr(dev_migration_repair.subprocess, "run", fake_run)
    output = tmp_path / "probe.json"

    assert dev_migration_repair.probe(probe_args(output)) == 0

    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["source_sha"] == SOURCE_SHA
    assert record["current_revision"] == "0074_calendar_sync_maintenance"
    assert record["code_heads"] == ["0085_merge_summary_mediascribe"]
    assert record["graph_mismatch"] is True
    assert record["boundary"] == "dev-existing"
    assert record["status"] == "blocked"
    assert record["database_probe"] == {
        "current_revision": "0074_calendar_sync_maintenance",
        "reason_code": "current_revision_read",
        "status": "pass",
    }
    printed = capsys.readouterr().out
    assert "dev-secret" not in printed
    assert "user@example" not in printed


def test_unavailable_dev_postgres_is_metadata_only_and_fail_closed(monkeypatch, tmp_path, capsys):
    migration_root(tmp_path)
    monkeypatch.setattr(dev_migration_repair, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(dev_migration_repair, "source_sha", lambda _root: SOURCE_SHA)

    def unavailable(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("psql", 10, stderr="password=dev-secret /private/user/rows")

    monkeypatch.setattr(dev_migration_repair.subprocess, "run", unavailable)
    output = tmp_path / "probe.json"

    assert dev_migration_repair.probe(probe_args(output)) == 0

    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["status"] == "blocked"
    assert record["current_revision"] is None
    assert record["database_probe"] == {
        "current_revision": None,
        "reason_code": "database_unavailable",
        "status": "blocked",
    }
    serialized = output.read_text(encoding="utf-8") + capsys.readouterr().out
    assert "dev-secret" not in serialized
    assert "/private/user/rows" not in serialized


def test_production_database_boundary_is_rejected_before_psql(monkeypatch):
    called = False

    def should_not_run(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(dev_migration_repair.subprocess, "run", should_not_run)

    with pytest.raises(dev_migration_repair.RepairError, match="host must be loopback"):
        dev_migration_repair.read_dev_postgres_revision(
            "postgresql://twobrain_rec:secret@production.example:54329/twobrain_rec"
        )
    assert called is False


def test_multiple_code_heads_remain_blocked_even_when_database_revision_matches(monkeypatch, tmp_path):
    migration_root(tmp_path)
    versions = tmp_path / "apps/server/src/twobrain_rec_server/db/migrations/versions"
    (versions / "0086_unmerged_branch.py").write_text(
        'revision: str = "0086_unmerged_branch"\n'
        'down_revision: str = "0074_linked_workspace_proofs"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(dev_migration_repair, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(dev_migration_repair, "source_sha", lambda _root: SOURCE_SHA)
    monkeypatch.setattr(
        dev_migration_repair.subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(
            command, 0, stdout="0085_merge_summary_mediascribe\n", stderr=""
        ),
    )
    output = tmp_path / "probe.json"

    assert dev_migration_repair.probe(probe_args(output)) == 0

    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["code_heads"] == ["0085_merge_summary_mediascribe", "0086_unmerged_branch"]
    assert record["graph_mismatch"] is True
    assert record["status"] == "blocked"
    assert "multiple heads" in record["reason"]


def test_missing_explicit_dev_database_does_not_fall_back_to_generic_database_url(monkeypatch, tmp_path):
    migration_root(tmp_path)
    monkeypatch.setattr(dev_migration_repair, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(dev_migration_repair, "source_sha", lambda _root: SOURCE_SHA)
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", "postgresql://twobrain_rec:secret@production.example:5432/twobrain_rec")
    monkeypatch.delenv("GRAF_DEV_DATABASE_URL", raising=False)

    output = tmp_path / "probe.json"
    assert dev_migration_repair.probe(probe_args(output, database_url=None)) == 0

    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["database_probe"]["reason_code"] == "database_not_configured"
    assert record["status"] == "blocked"


def test_postgres_probe_queries_only_alembic_metadata_and_never_user_rows(monkeypatch):
    observed = {}
    monkeypatch.setenv("PGSERVICE", "production-service")
    monkeypatch.setenv("PGHOSTADDR", "production.example")
    monkeypatch.setenv("PGOPTIONS", "-c search_path=production")

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed["env"] = kwargs["env"]
        return subprocess.CompletedProcess(command, 0, stdout="0085_merge_summary_mediascribe\n", stderr="users must not be queried")

    monkeypatch.setattr(dev_migration_repair.subprocess, "run", fake_run)
    result = dev_migration_repair.read_dev_postgres_revision(DEV_DATABASE_URL)

    assert result["status"] == "pass"
    assert result["current_revision"] == "0085_merge_summary_mediascribe"
    query = observed["command"][-1].lower()
    assert query == "select version_num from alembic_version order by version_num;"
    assert "select *" not in query
    assert "users" not in query
    assert "meetings" not in query
    assert observed["env"]["PGPASSWORD"] == "dev-secret"
    assert "PGSERVICE" not in observed["env"]
    assert "PGHOSTADDR" not in observed["env"]
    assert "PGOPTIONS" not in observed["env"]
