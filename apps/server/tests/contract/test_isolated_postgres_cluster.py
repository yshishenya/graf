"""Exercise the lifecycle of the cluster reserved for runtime-role proof."""
import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

from tests.fixtures import postgres_test_database as resources


@pytest.mark.parametrize("failure", [None, "missing_docker", "start", "ready", "deadline", "port", "migration", "body", "cleanup"])
def test_isolated_cluster_cleans_up_every_attempt(monkeypatch, failure):
    calls, migrated = [], []

    def run(args, **kwargs):
        assert kwargs["timeout"] <= 30
        calls.append(args)
        command = args[1]
        if command == "run" and failure == "missing_docker":
            raise FileNotFoundError("synthetic missing docker")
        if command == "run" and failure == "start":
            raise subprocess.TimeoutExpired(args, 30)
        if command == "logs":
            if failure == "ready":
                raise subprocess.TimeoutExpired(args, 5)
            stdout = "" if failure == "deadline" else "PostgreSQL init process complete; ready for start up."
        elif command == "port":
            stdout = "0.0.0.0:5432" if failure == "port" else "127.0.0.1:49152\n"
        else:
            stdout = ""
        return subprocess.CompletedProcess(args, int(command == "rm" and failure == "cleanup"), stdout, "")

    def migrate(url):
        migrated.append(url)
        if failure == "migration":
            raise RuntimeError("synthetic migration failure")

    monkeypatch.setattr(resources.subprocess, "run", run)
    monkeypatch.setattr(resources, "prepare_schema", migrate)
    if failure == "deadline":
        clock = iter([0, 0, 31])
        monkeypatch.setattr(resources.time, "monotonic", lambda: next(clock))
        monkeypatch.setattr(resources.time, "sleep", lambda _: None)
    fixture = resources.postgres_isolated_cluster_database_url.__wrapped__()
    if failure in {"missing_docker", "start", "ready", "deadline", "port"}:
        with pytest.raises(pytest.fail.Exception):
            next(fixture)
        assert not migrated
    elif failure == "migration":
        with pytest.raises(RuntimeError, match="synthetic migration failure"):
            next(fixture)
    else:
        url = next(fixture)
        parsed = make_url(url)
        assert parsed.username == "twobrain_rec" and parsed.password
        assert parsed.host == "127.0.0.1" and parsed.port == 49152
        resources._validate_disposable_database_name(parsed.database)
        assert migrated == [url]
        if failure == "body":
            with pytest.raises(RuntimeError, match="synthetic test failure"):
                fixture.throw(RuntimeError("synthetic test failure"))
        elif failure == "cleanup":
            with pytest.raises(pytest.fail.Exception, match="cannot remove"):
                fixture.close()
        else:
            fixture.close()
    start = next(call for call in calls if call[1] == "run")
    name = start[start.index("--name") + 1]
    assert name.startswith("graf-postgres-test-bootstrap-")
    assert "127.0.0.1::5432" in start and "postgres:17-alpine" in start
    assert calls[-1] == ["docker", "rm", "--force", "--volumes", name]


def test_collecting_bootstrap_proof_does_not_start_docker(tmp_path):
    server = Path(__file__).resolve().parents[2]
    calls = tmp_path / "docker-calls"
    docker = tmp_path / "docker"
    docker.write_text('#!/bin/sh\nprintf called >> "$DOCKER_CALLS"\nexit 79\n')
    docker.chmod(0o755)
    result = subprocess.run(
        ["uv", "run", "--frozen", "--extra", "dev", "pytest", "--collect-only", "-q",
         "tests/integration/test_playback_normalization_postgres.py::"
         "test_runtime_role_bootstrap_is_idempotent_and_verifies_privileges"],
        cwd=server, env={**os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"],
                         "DOCKER_CALLS": str(calls)},
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not calls.exists()
