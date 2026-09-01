from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
UPDATER = ROOT / ".specify/extensions/agent-context/scripts/python/update_agent_context.py"


def load_updater():
    spec = importlib.util.spec_from_file_location("agent_context_updater", UPDATER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_config(root: Path) -> None:
    config = root / ".specify/extensions/agent-context/agent-context-config.yml"
    config.parent.mkdir(parents=True)
    config.write_text("context_file: AGENTS.md\n", encoding="utf-8")


def test_resolver_fails_closed_without_active_pointer(tmp_path: Path) -> None:
    updater = load_updater()
    specs = tmp_path / "specs"
    (specs / "001-old").mkdir(parents=True)
    (specs / "001-old/plan.md").write_text("old\n", encoding="utf-8")

    assert updater._resolve_plan_path(str(tmp_path)) == ""


def test_resolver_ignores_plan_mtime_and_uses_feature_pointer(tmp_path: Path) -> None:
    updater = load_updater()
    old = tmp_path / "specs/001-old"
    active = tmp_path / "specs/216-active"
    old.mkdir(parents=True)
    active.mkdir(parents=True)
    (old / "plan.md").write_text("old\n", encoding="utf-8")
    (active / "plan.md").write_text("active\n", encoding="utf-8")
    pointer = tmp_path / ".specify/feature.json"
    pointer.parent.mkdir(parents=True)
    pointer.write_text(
        json.dumps({"feature_directory": "specs/216-active"}), encoding="utf-8"
    )

    assert updater._resolve_plan_path(str(tmp_path)) == "specs/216-active/plan.md"


def test_resolver_rejects_external_plan_path(tmp_path: Path) -> None:
    updater = load_updater()
    outside = tmp_path.parent / "external-plan-root"
    outside.mkdir()
    (outside / "plan.md").write_text("external\n", encoding="utf-8")
    pointer = tmp_path / ".specify/feature.json"
    pointer.parent.mkdir(parents=True)
    pointer.write_text(json.dumps({"feature_directory": str(outside)}), encoding="utf-8")

    assert updater._resolve_plan_path(str(tmp_path)) == ""


def test_cli_does_not_modify_context_without_active_pointer(tmp_path: Path) -> None:
    _write_config(tmp_path)
    context = tmp_path / "AGENTS.md"
    original = "stable instructions\n"
    context.write_text(original, encoding="utf-8")
    specs = tmp_path / "specs/001-old"
    specs.mkdir(parents=True)
    (specs / "plan.md").write_text("old\n", encoding="utf-8")

    result = subprocess.run(
        ["python3", str(UPDATER)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "refusing timestamp-based" in result.stderr
    assert context.read_text(encoding="utf-8") == original
