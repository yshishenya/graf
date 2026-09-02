#!/usr/bin/env python3
"""Fail-closed contract check for the release-only GitHub Full CI workflow."""
from __future__ import annotations

import argparse
import re
import tempfile
from pathlib import Path


FORBIDDEN = (
    "cd-remote.sh",
    "gh release",
    "git push",
    "git reset --hard",
    "ci-local.sh --full",
    "continue-on-error: true",
)


def validate(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"cannot read workflow: {exc}"]
    errors: list[str] = []
    required = {
        "workflow name": r"(?m)^name:\s*release-full\s*$",
        "manual trigger": r"(?m)^\s*workflow_dispatch:\s*$",
        "candidate input": r"(?ms)candidate_id:.*?required:\s*true",
        "SHA input": r"(?ms)requested_sha:.*?required:\s*true",
        "read-only contents": r"(?ms)^permissions:\s*\n\s*contents:\s*read\s*$",
        "read-only actions": r"(?ms)^permissions:\s*\n\s*contents:\s*read\s*\n\s*actions:\s*read\s*$",
        "candidate concurrency": r"(?ms)^concurrency:\s*.*?group:.*inputs\.candidate_id",
        "no cancellation": r"(?m)^\s*cancel-in-progress:\s*false\s*$",
        "reservation job": r"(?ms)^\s*reserve:\s*\n.*?actions/upload-artifact@v4",
        "artifact lookup": r"actions/artifacts",
        "server job": r"(?ms)^\s*server-full:\s*\n.*?runs-on:\s*ubuntu-latest",
        "macOS job": r"(?ms)^\s*macos-full:\s*\n.*?runs-on:\s*macos-14",
        "aggregate job": r"(?ms)^\s*aggregate:\s*\n.*?needs:\s*\[?reserve.*?server-full.*?macos-full",
        "exact checkout": r"ref:\s*\$\{\{\s*inputs\.requested_sha\s*\}\}",
        "server full tests": r"run_local_postgres_tests\.sh\s+--full",
        "macOS tests": r"swift\s+test\s+--package-path\s+apps/macos",
        "macOS arm64 assertion": r"uname\s+-m.*arm64",
        "contract validation": r"swift\s+run\s+--package-path\s+apps/macos\s+ContractValidation",
        "evidence producer": r"scripts/emit-ci-evidence\.py",
        "evidence validator": r"scripts/validate-ci-evidence\.py",
        "authoritative flag": r"--authoritative-full",
        "zero skipped gates": r"--skipped-gate(?:\s+)?(?:none|\[\])|[\"']?skipped_gates[\"']?\s*[:=]\s*\[\]",
        "component SHAs": r"--component-sha",
        "download artifact": r"actions/download-artifact@v4",
        "aggregate dependency": r"needs:\s*\[?reserve.*server-full.*macos-full",
        "candidate collision guard": r"candidate_already_reserved",
        "bounded job timeouts": r"(?s)timeout-minutes:\s*10.*timeout-minutes:\s*60.*timeout-minutes:\s*45",
    }
    for label, pattern in required.items():
        if not re.search(pattern, text):
            errors.append(f"missing workflow invariant: {label}")
    if re.search(r"(?m)^\s*pull_request\s*:", text):
        errors.append("release-full must not run on pull_request")
    for forbidden in FORBIDDEN:
        if forbidden in text:
            errors.append(f"forbidden workflow content: {forbidden}")
    if re.search(r"(?m)^\s*(contents|actions|checks|pull-requests):\s*write\s*$", text):
        errors.append("release-full permissions must remain read-only")
    if len(re.findall(r"actions/checkout@v4", text)) < 3:
        errors.append("reserve, server and macOS jobs must checkout exact SHA")
    if re.search(r"(?mi)^\s*[-]?[ ]*uses:\s*actions/(?:checkout|upload-artifact|download-artifact)@v[0-3]\b", text):
        errors.append("GitHub artifact/checkout actions must use v4")
    if "GRAF_CI_CANDIDATE_FILE" in text:
        errors.append("workflow must not depend on a local ignored candidate file")
    if "authoritative_full=true" not in text and "--authoritative-full" not in text:
        errors.append("aggregate must explicitly produce authoritative_full=true")
    return errors


def self_test() -> int:
    good = """name: release-full
on:
  workflow_dispatch:
    inputs:
      candidate_id:
        required: true
      requested_sha:
        required: true
permissions:
  contents: read
  actions: read
concurrency:
  group: graf-${{ inputs.candidate_id }}
  cancel-in-progress: false
jobs:
  reserve:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ inputs.requested_sha }}
      - run: gh api repos/o/r/actions/artifacts
      - run: echo candidate_already_reserved
      - uses: actions/upload-artifact@v4
  server-full:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ inputs.requested_sha }}
      - run: bash apps/server/scripts/run_local_postgres_tests.sh --full
  macos-full:
    runs-on: macos-14
    timeout-minutes: 45
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ inputs.requested_sha }}
      - run: test "$(uname -m)" = arm64
      - run: swift test --package-path apps/macos
      - run: swift run --package-path apps/macos ContractValidation
  aggregate:
    needs: [reserve, server-full, macos-full]
    timeout-minutes: 10
    steps:
      - uses: actions/download-artifact@v4
      - run: python3 scripts/emit-ci-evidence.py --authoritative-full --component-sha server=${{ inputs.requested_sha }} --skipped-gate []
      - run: python3 scripts/validate-ci-evidence.py evidence.json
      - uses: actions/upload-artifact@v4
"""
    with tempfile.TemporaryDirectory(prefix="graf-full-workflow-") as directory:
        path = Path(directory) / "workflow.yml"
        path.write_text(good, encoding="utf-8")
        errors = validate(path)
        assert errors == [], errors
        path.write_text(good.replace("cancel-in-progress: false", "cancel-in-progress: true"), encoding="utf-8")
        assert any("no cancellation" in item for item in validate(path))
        path.write_text(good.replace("swift test", "echo tests"), encoding="utf-8")
        assert any("macOS tests" in item for item in validate(path))
    print("full-ci-workflow self-test: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workflow", type=Path, nargs="?", default=Path(".github/workflows/release-full.yml"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    errors = validate(args.workflow)
    if errors:
        for error in errors:
            print(f"full-ci-workflow: ERROR: {error}")
        return 1
    print("full-ci-workflow: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
