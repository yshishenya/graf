from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate-pr-metadata.py"


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=root, text=True, stderr=subprocess.STDOUT,
    ).strip()


def body(sha: str, features: str = "F211") -> str:
    return f"""## Feature identity
- Feature ID: `{features}`
- Umbrella issue: `#6850`
- Spec task IDs: `T038`
## Как проверено
- `pytest -q tests/governance`: passed
- Exact source SHA: `{sha}`
## Risk / validation lane
- Lane: high-risk-product
## Issues
- Refs #6850
## Legacy Impact
- Classification: `untouched`
## Перед merge
- evidence recorded
"""


@pytest.fixture
def snapshot(tmp_path: Path) -> tuple[Path, dict, dict]:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "Metadata Contract")
    git(tmp_path, "config", "user.email", "metadata@example.test")
    script = tmp_path / "scripts/validate-pr-metadata.py"
    script.parent.mkdir()
    shutil.copyfile(SCRIPT, script)
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "base")
    base = git(tmp_path, "rev-parse", "HEAD")
    spec = tmp_path / "specs/211-example/spec.md"
    spec.parent.mkdir(parents=True)
    spec.write_text("example\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "feature")
    head = git(tmp_path, "rev-parse", "HEAD")
    current = {
        "number": 7, "state": "open", "head": {"sha": head},
        "base": {"sha": base, "ref": "master"},
        "title": "[F211] Проверить описание", "body": body(head),
    }
    event = {"number": 7, "pull_request": copy.deepcopy(current)}
    return tmp_path, event, current


def run_event(root: Path, event: object, current: object) -> subprocess.CompletedProcess[str]:
    event_path, current_path = root / "event.json", root / "current-pr.json"
    event_path.write_text(json.dumps(event))
    current_path.write_text(json.dumps(current))
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--event", str(event_path),
         "--current-pr", str(current_path)],
        cwd=root, text=True, capture_output=True,
    )


def test_event_mode_and_old_cli_accept_same_contract(snapshot) -> None:
    root, event, current = snapshot
    result = run_event(root, event, current)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "pr-metadata: OK\n"
    path = root / "body.md"
    path.write_text(current["body"])
    old = subprocess.run(
        [sys.executable, str(SCRIPT), str(path), "--feature-id", "211",
         "--expected-sha", current["head"]["sha"], "--title", current["title"]],
        cwd=root, text=True, capture_output=True,
    )
    assert old.returncode == 0, old.stderr
    assert old.stdout == result.stdout


@pytest.mark.parametrize("field", ["title", "body"])
def test_current_text_wins_in_both_directions(snapshot, field: str) -> None:
    root, event, current = snapshot
    valid = current[field]
    current[field] = "untrusted-current-text"
    rejected = run_event(root, event, current)
    assert rejected.returncode == 1
    assert "untrusted-current-text" not in rejected.stdout + rejected.stderr
    current[field] = valid
    event["pull_request"][field] = "stale-event-text"
    assert run_event(root, event, current).returncode == 0


@pytest.mark.parametrize(("target", "path", "value"), [
    ("event", "number", True),
    ("event", "number", 8),
    ("event", "pull_request", []),
    ("event", "pull_request.number", True),
    ("event", "pull_request.head.sha", "HEAD"),
    ("current", "number", True),
    ("current", "number", 0),
    ("current", "number", 8),
    ("current", "number", "7"),
    ("current", "head", None),
    ("current", "head.sha", "f" * 40),
    ("current", "base.sha", "f" * 40),
    ("current", "base.ref", "other"),
    ("current", "base.ref", []),
    ("current", "state", "closed"),
    ("current", "title", None),
    ("current", "body", {}),
])
def test_invalid_or_changed_identity_fails_closed(snapshot, target, path, value) -> None:
    root, event, current = snapshot
    parent = event if target == "event" else current
    *keys, field = path.split(".")
    for key in keys:
        parent = parent[key]
    parent[field] = value
    result = run_event(root, event, current)
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    if isinstance(current.get("body"), str):
        assert current["body"] not in result.stderr


@pytest.mark.parametrize(("target", "payload"), [
    ("event", b"[]"), ("current", b"[]"), ("event", b"{"),
    ("current", b"{private-response"), ("current", b"\xff"),
    ("current", b"[" * 2000 + b"]" * 2000),
    ("event", None), ("current", None),
])
def test_unreadable_json_has_bounded_diagnostics(snapshot, target, payload) -> None:
    root, event, current = snapshot
    assert run_event(root, event, current).returncode == 0
    path = root / ("event.json" if target == "event" else "current-pr.json")
    if payload is None:
        path.unlink()
    else:
        path.write_bytes(payload)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--event", str(root / "event.json"),
         "--current-pr", str(root / "current-pr.json")],
        cwd=root, text=True, capture_output=True,
    )
    assert result.returncode == 1
    assert "private-response" not in result.stderr
    assert "Traceback" not in result.stderr


def test_bad_metadata_values_do_not_escape_or_leak(snapshot) -> None:
    root, event, current = snapshot
    current["body"] = current["body"].replace("Refs #6850", "Refs #" + "9" * 5000)
    result = run_event(root, event, current)
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    current["body"] = body(current["head"]["sha"])
    current["title"] = "[F" + "9" * 5000 + "]"
    result = run_event(root, event, current)
    assert result.returncode == 1
    assert len(result.stderr) < 500


@pytest.mark.parametrize("kind", ["missing-base", "unrelated-base", "wrong-checkout"])
def test_git_identity_and_history_are_required(snapshot, kind: str) -> None:
    root, event, current = snapshot
    if kind == "wrong-checkout":
        git(root, "checkout", "-q", "--detach", current["base"]["sha"])
    else:
        base = "f" * 40 if kind == "missing-base" else git(root, "commit-tree", "HEAD^{tree}", "-m", "other root")
        event["pull_request"]["base"]["sha"] = current["base"]["sha"] = base
    assert run_event(root, event, current).returncode == 1


def test_real_diff_handles_rename_deletion_and_moving_default(snapshot) -> None:
    root, event, current = snapshot
    deleted = root / "changes/unreleased/F214.yaml"
    deleted.parent.mkdir(parents=True)
    deleted.write_text("retired fragment\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "fragment base")
    base = git(root, "rev-parse", "HEAD")
    deleted.unlink()
    spec = root / "specs/211-example/spec.md"
    destination = root / "specs/212-renamed/spec.md"
    destination.parent.mkdir()
    spec.rename(destination)
    fragment = root / "changes/releases/v2026.09.09.1/F213.yaml"
    fragment.parent.mkdir(parents=True)
    fragment.write_text("release\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "rename and release")
    current["base"]["sha"] = base
    current["head"]["sha"] = git(root, "rev-parse", "HEAD")
    current["body"] = body(current["head"]["sha"], "F211 F212 F213 F214")
    current["title"] = "[F211][F212][F213][F214] Переименовать фичу"
    event["pull_request"] = copy.deepcopy(current)
    for default in (base, current["head"]["sha"]):
        git(root, "update-ref", "refs/remotes/origin/master", default)
        assert run_event(root, event, current).returncode == 0
    current["body"] = body(current["head"]["sha"], "F212 F213 F214")
    assert run_event(root, event, current).returncode == 1
    current["body"] = body(current["head"]["sha"], "F211 F212 F213")
    assert run_event(root, event, current).returncode == 1


def test_scoped_diff_does_not_parse_newlines_as_feature_paths(snapshot) -> None:
    root, event, current = snapshot
    base = git(root, "rev-parse", "HEAD")
    for name in ("notes\nspecs/999-injected/file.txt", "changes/unreleased/F999.yaml\n"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not a feature path\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "scoped")
    current["base"]["sha"] = base
    current["head"]["sha"] = git(root, "rev-parse", "HEAD")
    current["title"] = "docs: Уточнить заметки"
    current["body"] = body(current["head"]["sha"], "scoped")
    event["pull_request"] = copy.deepcopy(current)
    assert run_event(root, event, current).returncode == 0
    path = root / "body.md"
    path.write_text(current["body"])
    old = subprocess.run(
        [sys.executable, str(SCRIPT), str(path), "--feature-id", "scoped", "--scoped",
         "--title", current["title"], "--expected-sha", current["head"]["sha"]],
        cwd=root, text=True, capture_output=True,
    )
    assert old.returncode == 0, old.stderr
    current["title"] = "   "
    assert run_event(root, event, current).returncode == 1
    current["title"] = "docs: Уточнить заметки"
    current["body"] = body(current["head"]["sha"])
    assert run_event(root, event, current).returncode == 1


@pytest.mark.parametrize("options", [
    ["--event", "event.json"], ["--current-pr", "current-pr.json"],
    ["--event", "event.json", "--current-pr", "current-pr.json", "--scoped"],
    ["--event", "event.json", "--current-pr", "current-pr.json", "--self-test"],
])
def test_event_options_cannot_skip_validation(tmp_path, options) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *options], cwd=tmp_path, text=True, capture_output=True,
    )
    assert result.returncode == 2


def test_workflow_is_additive_read_only_and_bounded() -> None:
    source = (ROOT / ".github/workflows/pr-metadata.yml").read_text()
    for marker in (
        "name: pr-metadata", "pull_request:", "branches: [master]",
        "types: [opened, synchronize, reopened, ready_for_review, edited]",
        "contents: read", "pull-requests: read", "timeout-minutes: 5",
        "group: graf-pr-metadata-${{ github.event.pull_request.number }}",
        "cancel-in-progress: true", "fetch-depth: 0", "persist-credentials: false",
        "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "ref: ${{ github.event.pull_request.head.sha }}",
    ):
        assert marker in source
    for forbidden in (
        "pull_request_target:", "merge_group:", "workflow_dispatch:", "paths:",
        "paths-ignore:", "if:", "continue-on-error:", "secrets.", ": write",
        "ci-local.sh", "pytest", "specify", "pip install", "upload-artifact",
        "github.event.pull_request.title", "github.event.pull_request.body",
    ):
        assert forbidden not in source
    assert source.count("uses:") == 1
    assert source.count("run: |") == 2
    fetch = source.split("- name: Fetch current PR\n", 1)[1].split("\n      - ", 1)[0]
    assert "GH_TOKEN: ${{ github.token }}" in fetch
    assert "PR_NUMBER: ${{ github.event.pull_request.number }}" in fetch
    assert source.count("GH_TOKEN:") == 1


@pytest.mark.parametrize("mode", ["valid", "api-error", "malformed", "invalid-number", "injection"])
def test_actual_workflow_shell_with_current_api_and_fork(snapshot, mode) -> None:
    root, event, current = snapshot
    source = (ROOT / ".github/workflows/pr-metadata.yml").read_text()
    current["head"]["repo"] = {"full_name": "contributor/fork"}
    event["pull_request"]["head"]["repo"] = {"full_name": "contributor/fork"}
    event["pull_request"]["body"] = "stale event text"
    if mode == "injection":
        payload = "$(touch injected); `touch injected`; ::error::private-text"
        current["title"] += " " + payload
        current["body"] += payload
    (root / "event.json").write_text(json.dumps(event))
    response = root / "response.json"
    response.write_text("{private-response" if mode == "malformed" else json.dumps(current))
    gh = root / "bin/gh"
    gh.parent.mkdir()
    gh.write_text(
        '#!/usr/bin/env bash\nset -euo pipefail\n'
        '[[ "$*" == "api repos/example/project/pulls/7" ]] || exit 90\n'
        'if [[ "$FAKE_API_MODE" == "api-error" ]]; then\n'
        '  printf "private-response" >&2; exit 1\nfi\n'
        'cat "$FIXTURE_RESPONSE"\n'
    )
    gh.chmod(0o755)
    env = {**os.environ, "PATH": str(gh.parent) + os.pathsep + os.environ["PATH"],
           "GITHUB_REPOSITORY": "example/project", "PR_NUMBER": "7",
           "GITHUB_EVENT_PATH": str(root / "event.json"), "RUNNER_TEMP": str(root),
           "FAKE_API_MODE": mode, "FIXTURE_RESPONSE": str(response)}
    if mode == "invalid-number":
        env["PR_NUMBER"] = "7; touch injected"
    outputs = ""
    for name in ("Fetch current PR", "Validate current PR metadata"):
        step = source.split(f"- name: {name}\n", 1)[1].split("\n      - ", 1)[0]
        command = textwrap.dedent(step.split("run: |\n", 1)[1])
        result = subprocess.run(["bash", "-c", command], cwd=root, env=env, text=True, capture_output=True)
        outputs += result.stdout + result.stderr
        if result.returncode:
            break
    assert (result.returncode == 0) == (mode in {"valid", "injection"}), outputs
    assert not (root / "injected").exists()
    assert "private-response" not in outputs
    assert "private-text" not in outputs
    assert "Traceback" not in outputs
