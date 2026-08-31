#!/usr/bin/env python3
"""Fail-closed contract check for the public PR governance workflow."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


FORBIDDEN = (
    "cd-remote.sh",
    "prepare-release.sh",
    "alembic stamp",
    "docker volume rm",
    "gh release",
    "git reset --hard",
    "ci-local.sh --full",
)


def validate(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"cannot read workflow: {exc}"]
    errors: list[str] = []
    required = {
        "name": r"(?m)^name:\s*governance-fast\s*$",
        "pull_request trigger": r"(?m)^\s*pull_request:\s*$",
        "master target": r"(?ms)^\s*branches:\s*(?:\[?master\]?|\n\s*-\s+master\b)",
        "workflow_dispatch trigger": r"(?m)^\s*workflow_dispatch:\s*$",
        "cancel-in-progress": r"(?m)^\s*cancel-in-progress:\s*true\s*$",
        "PR concurrency group": r"github\.event\.pull_request\.number",
        "exact checkout ref": r"(?m)^\s*ref:\s*\$\{\{\s*github\.event\.pull_request\.head\.sha",
        "requested SHA env": r"GRAF_CI_REQUESTED_SHA:\s*\$\{\{",
        "bounded fast lane": r"infra/scripts/ci-local\.sh\s+--fast",
        "evidence validator": r"scripts/validate-ci-evidence\.py",
        "artifact upload": r"actions/upload-artifact@v4",
        "read-only permissions": r"(?ms)^permissions:\s*\n\s*contents:\s*read\s*$",
    }
    for label, pattern in required.items():
        if not re.search(pattern, text):
            errors.append(f"missing workflow invariant: {label}")
    for forbidden in FORBIDDEN:
        if forbidden in text:
            errors.append(f"forbidden command in workflow: {forbidden}")
    validator_at = text.find("scripts/validate-ci-evidence.py")
    upload_at = text.find("actions/upload-artifact@v4")
    if validator_at >= 0 and upload_at >= 0 and validator_at > upload_at:
        errors.append("artifact upload must follow evidence validation")
    if re.search(r"(?mi)^\s*-\s*uses:\s*actions/checkout@v[0-3]\b", text):
        errors.append("checkout action must use v4")
    if re.search(r"(?mi)^\s*-\s*uses:\s*actions/upload-artifact@v[0-3]\b", text):
        errors.append("artifact action must use v4")
    if "if: always()" in text and upload_at >= 0:
        errors.append("artifact upload must not bypass validation with if: always()")
    return errors


def self_test() -> int:
    good = """name: governance-fast
on:
  pull_request:
    branches: [master]
  workflow_dispatch:
permissions:
  contents: read
concurrency:
  group: governance-${{ github.event.pull_request.number || github.run_id }}
  cancel-in-progress: true
jobs:
  governance-fast:
    env:
      GRAF_CI_REQUESTED_SHA: ${{ github.event.pull_request.head.sha || inputs.requested_sha }}
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha || inputs.requested_sha }}
      - run: infra/scripts/ci-local.sh --fast
      - run: python3 scripts/validate-ci-evidence.py .dev/ci-evidence/run.json
      - uses: actions/upload-artifact@v4
"""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="graf-workflow-validator-") as tmp:
        path = Path(tmp) / "workflow.yml"
        path.write_text(good, encoding="utf-8")
        assert validate(path) == []
        path.write_text(good.replace("cancel-in-progress: true", "cancel-in-progress: false"), encoding="utf-8")
        assert any("cancel-in-progress" in item for item in validate(path))
        path.write_text(good.replace("--fast", "--full"), encoding="utf-8")
        assert any("forbidden command" in item for item in validate(path))
    print("governance-workflow self-test: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workflow", type=Path, nargs="?", default=Path(".github/workflows/governance-fast.yml"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    errors = validate(args.workflow)
    if errors:
        for error in errors:
            print(f"governance-workflow: ERROR: {error}")
        return 1
    print("governance-workflow: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
