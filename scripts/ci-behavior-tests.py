#!/usr/bin/env python3
"""Select existing cabinet/settings proofs; Git diff remains owned by ci-local.sh."""

from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CABINET = "apps/server/src/twobrain_rec_server/cabinet/"
ASSETS = "tests/contract/test_cabinet_static_assets_contract.py"
RAIL_TEST = "test_cabinet_rail_node_harness_keeps_responsive_defaults_and_manual_state"
GROUPS = {
    "cabinet-shell": (ASSETS,),
    "settings": (
        "tests/contract/test_settings_ui_contract.py",
        "tests/unit/test_settings_view_models.py",
    ),
}


def select_tests(paths: list[str], covered: list[str], root: Path = ROOT) -> dict:
    matches: dict[str, list[str]] = {}
    for path in sorted(set(filter(None, paths))):
        if Path(path).is_absolute() or ".." in Path(path).parts or any(ord(c) < 32 or ord(c) == 127 for c in path):
            raise ValueError("unsupported_changed_path")
        shared = path.startswith((CABINET + "static/", CABINET + "templates/", CABINET + "rendering"))
        settings = path.startswith(CABINET + "view_models") or path == CABINET + "web_routes/settings.py"
        for group, targets in GROUPS.items():
            if shared or (settings and group == "settings") or path in {"apps/server/" + t for t in targets}:
                matches.setdefault(group, []).append(path)
    selected = sorted({target for group in matches for target in GROUPS[group]})
    for target in selected:
        file = root / "apps/server" / target
        if not file.is_file() or not file.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"required_test_file_missing: {target}")
        names = {node.name for node in ast.parse(file.read_text(encoding="utf-8")).body
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")}
        if not names or (target == ASSETS and RAIL_TEST not in names):
            raise ValueError(f"required_test_proof_missing: {target}")
    covered_tests = [target for target in selected if any(
        target == item or target.startswith(item.rstrip("/") + "/") for item in covered
    )]
    return {
        "changed_paths": sorted(set(filter(None, paths))),
        "groups": [{"name": group, "matched_paths": matches[group], "tests": list(GROUPS[group])}
                   for group in sorted(matches)],
        "tests": [target for target in selected if target not in covered_tests],
        "covered_tests": covered_tests,
        "environment": ["prepared server .venv", "Node.js", "no database or Docker"],
        "scope": "working_tree_diagnostic",
        "coverage": "partial",
        "next_gate": "governance-fast_then_release-full",
    }


def check_execution(report: Path, targets: list[str]) -> None:
    cases = ET.parse(report).findall(".//testcase")
    if any(case.find("skipped") is not None for case in cases):
        raise ValueError("required_behavior_test_skipped")
    for target in targets:
        if not any(case.get("classname", "").split(".")[-1] == Path(target).stem for case in cases):
            raise ValueError(f"required_test_file_not_executed: {target}")
    if ASSETS in targets and not any(case.get("name") == RAIL_TEST for case in cases):
        raise ValueError("required_rail_test_not_executed")


def execute(targets: list[str]) -> int:
    interpreter = ROOT / "apps/server/.venv/bin/python"
    if not interpreter.is_file():
        raise ValueError("server_venv_missing: prepare apps/server with uv sync --frozen --extra dev")
    if ASSETS in targets and shutil.which("node") is None:
        raise ValueError("node_missing: cabinet behavior tests require Node.js")
    with tempfile.TemporaryDirectory(prefix="graf-behavior-tests-") as directory:
        report = Path(directory) / "junit.xml"
        result = subprocess.run(
            [str(interpreter), "-m", "pytest", "-q", "-o", "addopts=", "--junitxml", str(report), *targets],
            cwd=ROOT / "apps/server",
            env={**os.environ, "PYTHONPATH": "src", "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_ADDOPTS": ""},
            check=False,
        )
        if result.returncode:
            return result.returncode
        check_execution(report, targets)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--targets", action="store_true")
    parser.add_argument("--covered", action="append", default=[])
    parser.add_argument("--allow-empty", action="store_true")
    parser.add_argument("--diff-unavailable", action="store_true")
    args = parser.parse_args()
    started = time.monotonic()
    status = 2
    try:
        # The runner decodes Git's NUL stream and rejects control characters.
        plan = select_tests(sys.stdin.read().split("\n"), args.covered)
        if args.targets:
            if plan["tests"]:
                print("\n".join(plan["tests"]))
            return 0
        plan.update(
            head_sha=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            base_ref=os.environ.get("GRAF_CI_BASE_REF") or "origin/master",
            dirty_worktree=bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT)),
            diff_available=not args.diff_unavailable,
        )
        print(json.dumps(plan, ensure_ascii=True, sort_keys=True), flush=True)
        if not args.run:
            return 0
        if not plan["tests"]:
            if args.allow_empty:
                print("ci_behavior_selection=not_applicable_or_covered")
                return 0
            raise ValueError("no_focused_tests_selected: use the feature quickstart; this is not a test PASS")
        status = execute(plan["tests"])
    except (OSError, ValueError, SyntaxError, subprocess.CalledProcessError, ET.ParseError) as exc:
        print(f"ci_behavior_error={exc}", file=sys.stderr)
    if args.run:
        print(f"ci_focused_result={'pass' if status == 0 else 'fail'} duration_seconds={time.monotonic() - started:.2f} "
              "scope=working_tree_diagnostic coverage=partial next_gate=governance-fast_then_release-full")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
