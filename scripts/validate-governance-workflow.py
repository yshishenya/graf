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
    for invariant in (
        "scripts/ci-pr-scope.py",
        "needs: scope",
        "name: governance-fast\n    needs: scope\n    if: ${{ always() }}",
        "needs.scope.outputs.text_only != 'false' && format('text-or-unresolved-{0}', github.run_id)",
        '[[ "$SCOPE_RESULT" == success && ( "$TEXT_ONLY" == true || "$TEXT_ONLY" == false ) ]]',
        "--reuse-component governance-fast",
        "actions: read",
        "retention-days: 90",
        "if: steps.scope.outputs.text_only == 'true'",
        "name: graf-code-scope-${{ github.run_id }}-${{ github.run_attempt }}",
        "path: ${{ runner.temp }}/code-scope.json",
    ):
        if invariant not in text:
            errors.append(f"missing code/text isolation invariant: {invariant}")
    if re.search(r"(?m)^concurrency:", text):
        errors.append("text events must not enter workflow-level code concurrency")
    if "scripts/validate-pr-metadata.py" in text or "PR_METADATA_OUTCOME" in text:
        errors.append("combined metadata must be retired after protected cutover")
    fast_match = re.search(r"(?ms)^      - name: Run bounded fast lane\n(.*?)(?=^      - |\Z)", text)
    fast_step = fast_match.group(1) if fast_match else ""
    for invariant in (
        "GRAF_CI_BASE_REF: ${{ steps.identity.outputs.base_sha }}",
        "EVENT_NAME: ${{ github.event_name }}",
        'if [[ "$EVENT_NAME" != "workflow_dispatch" ]]; then',
        '[[ "$GRAF_CI_BASE_REF" =~ ^[0-9a-f]{40}$ ]]',
        'git merge-base HEAD "$GRAF_CI_BASE_REF" >/dev/null',
    ):
        if invariant not in fast_step:
            errors.append(f"missing workflow event-base invariant: {invariant}")
    for forbidden in FORBIDDEN:
        if forbidden in text:
            errors.append(f"forbidden command in workflow: {forbidden}")
    if ".specify/feature.json" in text:
        errors.append("workflow must not depend on ignored .specify/feature.json")
    if re.search(r"(?mi)^\s*continue-on-error:\s*true\s*$", text):
        errors.append("governance workflow must not make a gate advisory with continue-on-error")
    code_job = text.partition("\n  governance-fast:\n")[2]
    shared = {"Require valid code scope", "Checkout exact PR SHA", "Resolve event identity", "Verify exact SHA"}
    for step in re.split(r"(?m)^      - ", code_job)[1:]:
        name = re.match(r"name: (.+)", step)
        if name and name.group(1) in shared:
            continue
        if name and name.group(1) == "Verify existing code proof":
            if "if: needs.scope.outputs.text_only == 'true'" not in step or "--reuse-component governance-fast" not in step:
                errors.append("text proof must execute only for verified text scope")
        elif "needs.scope.outputs.text_only == 'false'" not in step:
            errors.append("heavy/evidence step must be restricted to code scope")
    validator_at = code_job.find("scripts/validate-ci-evidence.py")
    upload_at = code_job.find("actions/upload-artifact@v4")
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
    good = (Path(__file__).resolve().parents[1] / ".github/workflows/governance-fast.yml").read_text()
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
