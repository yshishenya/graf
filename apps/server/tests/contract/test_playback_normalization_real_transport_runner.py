from __future__ import annotations

import ast
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
