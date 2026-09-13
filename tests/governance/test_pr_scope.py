from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ci-pr-scope.py"


def load_scope():
    spec = importlib.util.spec_from_file_location("ci_pr_scope", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_only_known_text_edit_shape_can_skip_code():
    scope = load_scope()
    for changes in ({"body": {"from": "old"}}, {"title": {"from": "old"}, "body": {"from": None}}):
        event = {"action": "edited", "changes": changes}
        assert scope.text_only(event)
        assert not scope.text_only({**event, "action": "synchronize"})
    for changes in ({}, None, [], {"base": {"ref": {"from": "other"}}},
                    {"body": {}}, {"body": {"from": 7}}, {"body": {"from": "x", "extra": 1}},
                    {"body": {"from": "x"}, "unknown": {}}):
        assert not scope.text_only({"action": "edited", "changes": changes})


def test_native_scope_uses_exact_git_diff_and_both_rename_sides(tmp_path):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()

    git("init", "-q")
    git("config", "user.name", "Scope Contract")
    git("config", "user.email", "scope@example.test")
    source = tmp_path / "apps/macos/old.swift"
    source.parent.mkdir(parents=True)
    source.write_text("unchanged contents\n")
    git("add", ".")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    source.rename(tmp_path / "notes.md")
    git("add", ".")
    git("commit", "-qm", "rename native to documentation")
    head = git("rev-parse", "HEAD")
    event = {"number": 7, "action": "synchronize", "pull_request": {
        "number": 7, "head": {"sha": head}, "base": {"sha": base}}}

    def run(value):
        path = tmp_path / "event.json"
        path.write_text(json.dumps(value))
        return subprocess.run([sys.executable, str(SCRIPT), str(path), "--event-name", "pull_request"],
                              cwd=tmp_path, text=True, capture_output=True)

    for default in (base, head):
        git("update-ref", "refs/remotes/origin/master", default)
        result = run(event)
        assert result.returncode == 0, result.stderr
        value = json.loads(result.stdout)
        assert value["native_required"] is True
        assert value["base_sha"] == base and value["target_sha"] == head
    bad = copy.deepcopy(event)
    bad["pull_request"]["base"]["sha"] = "f" * 40
    assert run(bad).returncode != 0


def test_native_scope_fails_conservatively_for_shared_and_unknown_paths():
    scope = load_scope()
    for path in ("apps/macos/foo.swift", "apps/server/src/twobrain_rec_server/api/v1/users.py",
                 "apps/server/src/twobrain_rec_server/outcomes/meeting_minutes.md", "apps/macos/Resources/prompt.md",
                 "apps/server/src/twobrain_rec_server/cabinet/routes.py", "scripts/tool.py", "new-system/config",
                 ".github/workflows/governance-fast.yml", "docs/fake.md\napps/macos/source.swift"):
        assert scope.native_required([path]), path
    for path in ("docs/release.md", "specs/211-example/tasks.md", "changes/unreleased/F211.yaml",
                 "apps/server/tests/unit/test_billing.py", "apps/server/src/twobrain_rec_server/billing/usage.py"):
        assert not scope.native_required([path]), path
    assert scope.native_required([])


@pytest.mark.parametrize(("scope_result", "required", "native_result", "code"), [
    ("success", "false", "skipped", 0), ("success", "true", "success", 0),
    ("failure", "false", "skipped", 1), ("success", "true", "skipped", 1),
    ("success", "true", "cancelled", 1), ("success", "", "skipped", 1),
])
def test_actual_native_terminal_shell_rejects_missing_execution(scope_result, required, native_result, code):
    import yaml

    workflow = yaml.safe_load((ROOT / ".github/workflows/macos-pr.yml").read_text())
    final = workflow["jobs"]["result"]
    assert "macos-pr-text-change" in final["name"]
    assert "macos-pr'" in final["name"]
    command = final["steps"][0]["run"]
    result = subprocess.run(["bash", "-c", command], text=True, capture_output=True,
                            env={**os.environ, "SCOPE_RESULT": scope_result,
                                 "NATIVE_REQUIRED": required, "NATIVE_RESULT": native_result,
                                 "TEXT_ONLY": "false"})
    assert result.returncode == code, result.stdout + result.stderr
