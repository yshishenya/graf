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
    checkout_refs: list[str] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not re.search(r"uses:\s*actions/checkout@v4\s*$", line):
            continue
        step_indent = len(line) - len(line.lstrip())
        for following in lines[index + 1:]:
            indent = len(following) - len(following.lstrip())
            if following.strip().startswith("-") and indent <= step_indent:
                break
            ref_match = re.match(r"^\s*ref:\s*(.*)$", following)
            if ref_match:
                checkout_refs.append(ref_match.group(1).strip())
                break
    exact_identity = (
        bool(checkout_refs)
        and any("github.event.pull_request.head.sha" in value for value in checkout_refs)
        and any("github.event.merge_group.head_sha" in value for value in checkout_refs)
        and any("inputs.requested_sha" in value for value in checkout_refs)
    )
    required = {
        "name": r"(?m)^name:\s*governance-fast\s*$",
        "pull_request trigger": r"(?m)^\s*pull_request:\s*$",
        "master target": r"(?ms)^\s*branches:\s*(?:\[?master\]?|\n\s*-\s+master\b)",
        "workflow_dispatch trigger": r"(?m)^\s*workflow_dispatch:\s*$",
        "cancel-in-progress": r"(?m)^\s*cancel-in-progress:\s*true\s*$",
        "PR concurrency group": r"github\.event\.pull_request\.number",
        # The workflow resolves PR, merge-group, and manual events to one
        # exact SHA expression. Keep the PR head SHA as a required branch of
        # that expression rather than accepting an unbound ref.
        "exact checkout ref": r"(?m)^\s*ref:\s*\$\{\{",
        "requested SHA env": r"GRAF_CI_REQUESTED_SHA:\s*\$\{\{",
        "bounded fast lane": r"infra/scripts/ci-local\.sh\s+--fast",
        "PR metadata gate": r"(?ms)name:\s*Validate pull request metadata.*?if:\s*\$\{\{\s*github\.event_name\s*==\s*'pull_request'\s*\}\}.*?scripts/validate-pr-metadata\.py",
        "PR metadata exact SHA": r"(?ms)name:\s*Validate pull request metadata.*?--expected-sha\s+\"\$EXPECTED_SHA\"",
        "PR metadata title": r"(?ms)name:\s*Validate pull request metadata.*?--title\s+\"\$PR_TITLE\"",
        "PR title event binding": r"PR_TITLE:\s*\$\{\{\s*github\.event\.pull_request\.title\s*\}\}",
        "mandatory outcome assertion": r"(?ms)name:\s*Assert mandatory governance outcomes.*?exit 1",
        "evidence validator": r"scripts/validate-ci-evidence\.py",
        "authoritative merge-group API mapping": r"gh\s+api\s+--paginate\s+--slurp",
        "authoritative response passed to verifier": r"--authoritative-response\s+\"?\$RUNNER_TEMP/graf-merge-group-api\.json",
        "artifact upload": r"actions/upload-artifact@v4",
        "read-only permissions": r"(?ms)^permissions:\s*\n\s*contents:\s*read\s*$",
    }
    for label, pattern in required.items():
        if not re.search(pattern, text):
            errors.append(f"missing workflow invariant: {label}")
    if not exact_identity:
        errors.append("checkout ref must bind pull-request, merge-group, and manual exact SHA identities")
    for forbidden in FORBIDDEN:
        if forbidden in text:
            errors.append(f"forbidden command in workflow: {forbidden}")
    if ".specify/feature.json" in text:
        errors.append("workflow must not depend on ignored .specify/feature.json")
    if re.search(r"(?mi)^\s*continue-on-error:\s*true\s*$", text):
        errors.append("governance workflow must not make a gate advisory with continue-on-error")
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
  merge_group:
    types: [checks_requested]
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
          ref: ${{ github.event.pull_request.head.sha || github.event.merge_group.head_sha || inputs.requested_sha }}
      - run: gh api --paginate --slurp repos/o/r/commits/$GRAF_CI_REQUESTED_SHA/pulls
      - run: python3 scripts/verify-merge-group-mapping.py --authoritative-response "$RUNNER_TEMP/graf-merge-group-api.json"
      - name: Validate pull request metadata
        if: ${{ github.event_name == 'pull_request' }}
        env:
          PR_TITLE: ${{ github.event.pull_request.title }}
        run: |
          python3 scripts/validate-pr-metadata.py "$RUNNER_TEMP/graf-pr-body.md" --feature-id "$FEATURE_ID" --expected-sha "$EXPECTED_SHA" --title "$PR_TITLE"
      - run: infra/scripts/ci-local.sh --fast
      - run: python3 scripts/validate-ci-evidence.py .dev/ci-evidence/run.json
      - name: Assert mandatory governance outcomes
        if: ${{ always() }}
        run: |
          test "$VALIDATION_OUTCOME" = success || exit 1
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
