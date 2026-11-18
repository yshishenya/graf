from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SERVER_ROOT = Path(__file__).resolve().parents[2]
ROOT = SERVER_ROOT.parents[1]
ACCEPTANCE = SERVER_ROOT / "acceptance/playback_normalization_real_transport.py"
SUPERVISOR = SERVER_ROOT / "scripts/run_playback_normalization_real_transport.py"
PYPROJECT = SERVER_ROOT / "pyproject.toml"


def test_supervisor_imports_only_the_standard_library() -> None:
    tree = ast.parse(SUPERVISOR.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".", 1)[0])
    assert imported
    assert imported <= set(sys.stdlib_module_names), sorted(imported - set(sys.stdlib_module_names))


def test_supervisor_help_does_not_touch_docker_or_settings(tmp_path) -> None:
    docker_calls = tmp_path / "docker-calls"
    docker = tmp_path / "docker"
    docker.write_text('#!/bin/sh\nprintf called >> "$DOCKER_CALLS"\nexit 79\n')
    docker.chmod(0o755)
    result = subprocess.run(
        [sys.executable, str(SUPERVISOR), "--help"],
        cwd=ROOT,
        env={
            **os.environ,
            "PATH": str(tmp_path) + os.pathsep + os.environ.get("PATH", ""),
            "DOCKER_CALLS": str(docker_calls),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "real-transport acceptance" in result.stdout
    assert not docker_calls.exists()


def test_supervisor_rejects_a_dotenv_before_any_resource(tmp_path) -> None:
    sys.path.insert(0, str(SERVER_ROOT / "scripts"))
    try:
        from run_playback_normalization_real_transport import _require_no_dotenv
    finally:
        sys.path.pop(0)
    (tmp_path / "apps/server").mkdir(parents=True)
    (tmp_path / "apps/server/.env").write_text("SECRET=value\n")
    with pytest.raises(SystemExit) as stopped:
        _require_no_dotenv(tmp_path)
    assert stopped.value.code == 2


def test_supervisor_requires_an_explicit_local_unix_socket(monkeypatch, tmp_path) -> None:
    sys.path.insert(0, str(SERVER_ROOT / "scripts"))
    try:
        from run_playback_normalization_real_transport import _resolve_docker_host
    finally:
        sys.path.pop(0)
    monkeypatch.delenv("GRAF_F099_DOCKER_HOST", raising=False)
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    with pytest.raises(SystemExit):
        _resolve_docker_host()
    monkeypatch.setenv("GRAF_F099_DOCKER_HOST", f"unix://{tmp_path / 'missing.sock'}")
    with pytest.raises(SystemExit):
        _resolve_docker_host()


def test_acceptance_is_outside_the_ordinary_discovery_patterns() -> None:
    assert ACCEPTANCE.name == "playback_normalization_real_transport.py"
    assert not ACCEPTANCE.name.startswith("test_")
    assert not ACCEPTANCE.name.endswith("_test.py")
    assert "testpaths = [\"tests\"]" in PYPROJECT.read_text(encoding="utf-8")
    assert ACCEPTANCE.parent.name == "acceptance"


def test_synthetic_project_discovery_and_explicit_selection(tmp_path) -> None:
    project = tmp_path / "project"
    tests = project / "tests"
    acceptance = project / "acceptance"
    tests.mkdir(parents=True)
    acceptance.mkdir()
    (project / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\ntestpaths = [\"tests\"]\n", encoding="utf-8"
    )
    inside_marker = tmp_path / "inside-imported"
    outside_marker = tmp_path / "outside-imported"
    (tests / "test_inside.py").write_text(
        f"from pathlib import Path\nPath({str(inside_marker)!r}).touch()\n"
        "def test_inside(): pass\n",
        encoding="utf-8",
    )
    (acceptance / "playback_normalization_real_transport.py").write_text(
        f"from pathlib import Path\nPath({str(outside_marker)!r}).touch()\n"
        "def test_outside(): pass\n",
        encoding="utf-8",
    )

    ordinary = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert ordinary.returncode == 0, ordinary.stdout + ordinary.stderr
    assert inside_marker.exists()
    assert not outside_marker.exists()
    assert "test_inside" in ordinary.stdout

    explicit = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "acceptance/playback_normalization_real_transport.py",
        ],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert explicit.returncode == 0, explicit.stdout + explicit.stderr
    assert outside_marker.exists()
    assert "test_outside" in explicit.stdout


def test_explicit_selection_without_context_fails_before_application_imports(tmp_path) -> None:
    recorder = tmp_path / "sitecustomize.py"
    sentinel = tmp_path / "application-imports"
    recorder.write_text(
        "import builtins, os\n"
        "real_import = builtins.__import__\n"
        "def guarded(name, *args, **kwargs):\n"
        "    if name == 'twobrain_rec_server' or name.startswith('twobrain_rec_server.'):\n"
        "        with open(os.environ['APPLICATION_IMPORT_SENTINEL'], 'a') as output:\n"
        "            output.write(name + '\\n')\n"
        "    return real_import(name, *args, **kwargs)\n"
        "builtins.__import__ = guarded\n",
        encoding="utf-8",
    )
    docker_calls = tmp_path / "docker-calls"
    docker = tmp_path / "docker"
    docker.write_text('#!/bin/sh\nprintf called >> "$DOCKER_CALLS"\nexit 79\n')
    docker.chmod(0o755)
    environment = {
        key: value
        for key, value in os.environ.items()
        if key != "GRAF_F099_ACCEPTANCE_CONTEXT"
    }
    environment.update(
        {
            "PATH": str(tmp_path) + os.pathsep + environment.get("PATH", ""),
            "PYTHONPATH": os.pathsep.join(
                [str(tmp_path), str(SERVER_ROOT), str(SERVER_ROOT / "src")]
            ),
            "APPLICATION_IMPORT_SENTINEL": str(sentinel),
            "DOCKER_CALLS": str(docker_calls),
        }
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(ACCEPTANCE)],
        cwd=SERVER_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode != 0
    assert "explicit F099 supervisor context" in result.stdout + result.stderr
    assert not sentinel.exists()
    assert not docker_calls.exists()


FAKE_CLEANUP_DOCKER = r'''#!{python}
import json, os, sys
from pathlib import Path

mode = os.environ["FAKE_CLEANUP_MODE"]
calls = Path(os.environ["DOCKER_CALLS"])
args = sys.argv[1:]
with calls.open("a") as output:
    output.write(json.dumps(args) + "\n")
token = "b" * 32
image = "sha256:" + "a" * 64
state = Path(os.environ["DOCKER_STATE"])
removed = state.exists()
if args[0] == "inspect":
    if mode == "unknown":
        sys.exit(1)
    if mode == "foreign":
        print("foreign|/container|" + "c" * 32 + "|" + image)
        sys.exit(0)
    if removed:
        sys.exit(1)
    print("container|/container|" + token + "|" + image)
    sys.exit(0)
if args[0] == "ps":
    if mode == "unknown":
        sys.exit(1)
    if mode == "owned" and not removed:
        print("container")
    sys.exit(0)
if args[0] == "rm":
    state.write_text("removed")
    sys.exit(0)
sys.exit(2)
'''


@pytest.fixture
def cleanup_docker(tmp_path):
    docker = tmp_path / "docker"
    docker.write_text(FAKE_CLEANUP_DOCKER.format(python=sys.executable))
    docker.chmod(0o755)
    calls = tmp_path / "calls.jsonl"
    state = tmp_path / "removed"

    def invoke(mode: str):
        sys.path.insert(0, str(SERVER_ROOT / "scripts"))
        try:
            from run_playback_normalization_real_transport import (
                _remove_verified_container,
            )
        finally:
            sys.path.pop(0)
        result = _remove_verified_container(
            [str(docker)],
            name="container",
            run_token="b" * 32,
            image_id="sha256:" + "a" * 64,
            candidate_id="container" if mode in {"owned", "foreign"} else None,
            environment={
                **os.environ,
                "PATH": str(tmp_path) + os.pathsep + os.environ.get("PATH", ""),
                "FAKE_CLEANUP_MODE": mode,
                "DOCKER_CALLS": str(calls),
                "DOCKER_STATE": str(state),
            },
        )
        logged = [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []
        return result, logged

    return invoke


def test_cleanup_refuses_unknown_absence(cleanup_docker):
    result, calls = cleanup_docker("unknown")
    assert result == (False, "lookup_failed")
    assert not any(call[0] == "rm" for call in calls)


def test_cleanup_does_not_remove_a_foreign_container(cleanup_docker):
    result, calls = cleanup_docker("foreign")
    assert result == (False, "foreign_or_mismatched_container")
    assert not any(call[0] == "rm" for call in calls)


def test_cleanup_removes_an_owned_container_by_id(cleanup_docker):
    result, calls = cleanup_docker("owned")
    assert result == (True, "removed")
    assert [call for call in calls if call[0] == "rm"] == [
        ["rm", "--force", "--volumes", "container"]
    ]


def test_process_group_is_terminated_and_escalates_to_kill() -> None:
    sys.path.insert(0, str(SERVER_ROOT / "scripts"))
    try:
        from run_playback_normalization_real_transport import _terminate_process_group
    finally:
        sys.path.pop(0)
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)",
        ],
        start_new_session=True,
    )
    started = __import__("time").monotonic()
    _terminate_process_group(process, term_grace=0.2, kill_grace=2)
    assert process.poll() is not None
    assert __import__("time").monotonic() - started < 5


def test_whole_run_wait_enforces_the_deadline() -> None:
    sys.path.insert(0, str(SERVER_ROOT / "scripts"))
    try:
        from run_playback_normalization_real_transport import _wait_for_child
    finally:
        sys.path.pop(0)
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    started = __import__("time").monotonic()
    output, timed_out = _wait_for_child(process, 0.2)
    assert timed_out is True
    assert output == b""
    assert process.poll() is not None
    assert __import__("time").monotonic() - started < 5


def test_bootstrap_monitor_kills_an_overdue_start(tmp_path) -> None:
    import json as json_module
    import threading
    import time as time_module

    sys.path.insert(0, str(SERVER_ROOT / "scripts"))
    try:
        from run_playback_normalization_real_transport import (
            _monitor_postgres_bootstrap,
        )
    finally:
        sys.path.pop(0)
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        start_new_session=True,
    )
    state = tmp_path / "postgres-state.json"
    state.write_text(json_module.dumps({
        "phase": "starting",
        "started_ms": int(time_module.monotonic() * 1000) - 120_000,
    }))
    timed_out = _monitor_postgres_bootstrap(
        process,
        state,
        threading.Event(),
        limit_ms=1_000,
        term_grace=0.2,
        kill_grace=2,
    )
    assert timed_out is True
    assert process.poll() is not None


def test_bootstrap_monitor_stops_after_ready(tmp_path) -> None:
    import json as json_module
    import threading

    sys.path.insert(0, str(SERVER_ROOT / "scripts"))
    try:
        from run_playback_normalization_real_transport import (
            _monitor_postgres_bootstrap,
        )
    finally:
        sys.path.pop(0)
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        start_new_session=True,
    )
    try:
        state = tmp_path / "postgres-state.json"
        state.write_text(json_module.dumps({"phase": "ready", "started_ms": 0}))
        assert _monitor_postgres_bootstrap(process, state, threading.Event()) is False
    finally:
        process.terminate()
        process.wait(timeout=5)
