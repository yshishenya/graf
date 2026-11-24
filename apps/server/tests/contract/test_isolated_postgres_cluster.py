"""Exercise the lifecycle of the cluster reserved for runtime-role proof."""
import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

from tests.fixtures import postgres_test_database as resources


@pytest.mark.parametrize("failure", [None, "missing_docker", "start", "start_nonzero", "ready", "deadline", "port", "migration", "body", "cleanup"])
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
        elif command == "container" and failure == "cleanup":
            stdout = next(call[call.index("--name") + 1] for call in calls if call[1] == "run")
        else:
            stdout = ""
        return subprocess.CompletedProcess(args, int((command == "rm" and failure == "cleanup") or (command == "run" and failure == "start_nonzero")), stdout, "")

    def migrate(url):
        migrated.append(url)
        if failure == "migration":
            raise RuntimeError("synthetic migration failure")

    monkeypatch.setattr(resources.subprocess, "run", run)
    monkeypatch.setattr(resources, "prepare_schema", migrate)
    if failure == "deadline":
        clock = iter([0, resources.ISOLATED_CLUSTER_READY_DEADLINE_SECONDS])
        monkeypatch.setattr(resources.time, "monotonic", lambda: next(clock))
        monkeypatch.setattr(resources.time, "sleep", lambda _: None)
    fixture = resources.postgres_isolated_cluster_database_url.__wrapped__()
    if failure in {"missing_docker", "start", "start_nonzero", "ready", "deadline", "port"}:
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
            with pytest.raises(pytest.fail.Exception, match="cannot confirm"):
                fixture.close()
        else:
            fixture.close()
    start = next(call for call in calls if call[1] == "run")
    name = start[start.index("--name") + 1]
    assert name.startswith("graf-postgres-test-bootstrap-")
    assert "127.0.0.1::5432" in start and "postgres:17-alpine" in start
    assert [call for call in calls if call[1] == "rm"][-1] == ["docker", "rm", "--force", "--volumes", name]
    assert sum(call[1] == "run" for call in calls) == (2 if failure == "start" else 1)


@pytest.mark.parametrize("case", [
    "transient", "double_timeout", "absent", "present", "remove_timeout", "remove_oserror",
    "lookup_nonzero", "lookup_timeout", "lookup_oserror", "lookup_unexpected",
])
def test_start_timeout_retries_only_after_verified_cleanup(monkeypatch, case, capsys):
    calls, migrations = [], []
    run_count = remove_count = 0
    owned_name = None

    def run(args, **kwargs):
        nonlocal run_count, remove_count, owned_name
        calls.append(args)
        operation = args[1]
        expected_timeout = (
            resources.ISOLATED_CLUSTER_CLEANUP_TIMEOUT_SECONDS
            if operation in {"run", "rm", "container"}
            else resources.ISOLATED_CLUSTER_CALL_TIMEOUT_SECONDS
        )
        assert kwargs["timeout"] == expected_timeout
        code, stdout = 0, ""
        if operation == "run":
            run_count += 1
            name = args[args.index("--name") + 1]
            owned_name = owned_name or name
            assert name == owned_name
            if run_count == 1 or case == "double_timeout":
                raise subprocess.TimeoutExpired(args, 30, output="private-output", stderr="private-stderr")
        elif operation == "rm":
            remove_count += 1
            assert args == ["docker", "rm", "--force", "--volumes", owned_name]
            if remove_count == 1:
                if case == "remove_timeout":
                    raise subprocess.TimeoutExpired(args, 30, stderr="private-stderr")
                if case == "remove_oserror":
                    raise OSError("private-oserror")
            if case in {"absent", "present", "lookup_nonzero", "lookup_timeout", "lookup_oserror", "lookup_unexpected"}:
                code = 1
        elif operation == "container":
            assert args == ["docker", "container", "ls", "--all", "--filter", f"name=^/{owned_name}$", "--format", "{{.Names}}"]
            if case == "lookup_timeout":
                raise subprocess.TimeoutExpired(args, 5, stderr="private-stderr")
            if case == "lookup_oserror":
                raise OSError("private-oserror")
            code = int(case == "lookup_nonzero")
            stdout = owned_name if case == "present" else "unexpected-value" if case == "lookup_unexpected" else ""
        elif operation == "logs":
            stdout = "PostgreSQL init process complete; ready for start up."
        elif operation == "port":
            stdout = "127.0.0.1:49152\n"
        return subprocess.CompletedProcess(args, code, stdout, "private-stderr")

    monkeypatch.setattr(resources.subprocess, "run", run)
    monkeypatch.setattr(resources, "prepare_schema", migrations.append)
    fixture = resources.postgres_isolated_cluster_database_url.__wrapped__()
    if case in {"transient", "absent"}:
        url = next(fixture)
        assert migrations == [url]
        fixture.close()
        assert run_count == 2 and remove_count == 2
    else:
        with pytest.raises(pytest.fail.Exception) as failure:
            next(fixture)
        assert not migrations
        assert run_count == (2 if case == "double_timeout" else 1)
        assert remove_count >= 1
        assert "private-" not in str(failure.value)
        error = failure.value
        while error is not None:
            assert not isinstance(error, (subprocess.TimeoutExpired, OSError))
            assert "private-" not in str(error)
            error = error.__context__
    output = capsys.readouterr()
    assert "private-" not in output.out + output.err
    assert not any("POSTGRES_PASSWORD=" in str(call) for call in calls)


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
