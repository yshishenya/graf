from __future__ import annotations

from pathlib import Path
import importlib.util
import os
import subprocess
import textwrap

import pytest


ROOT = Path(__file__).resolve().parents[2]


def load_validator():
    path = ROOT / "scripts" / "validate-governance-workflow.py"
    spec = importlib.util.spec_from_file_location("validate_governance_workflow", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_governance_workflow_contract() -> None:
    validator = load_validator()
    assert validator.validate(ROOT / ".github/workflows/governance-fast.yml") == []


@pytest.mark.parametrize(
    ("event_name", "base_kind"),
    [
        ("pull_request", "valid"),
        ("merge_group", "valid"),
        ("workflow_dispatch", "diagnostic"),
        ("pull_request", "missing"),
        ("merge_group", "missing"),
        ("pull_request", "invalid"),
        ("merge_group", "invalid"),
        ("pull_request", "unavailable"),
        ("merge_group", "unavailable"),
        ("pull_request", "unrelated"),
        ("merge_group", "unrelated"),
    ],
)
def test_fast_workflow_uses_the_event_base_for_real_diff(
    tmp_path: Path, event_name: str, base_kind: str,
) -> None:
    source = (ROOT / ".github/workflows/governance-fast.yml").read_text()
    step = source.split("- name: Run bounded fast lane\n", 1)[1].split("\n      - ", 1)[0]
    assert "GRAF_CI_BASE_REF: ${{ steps.identity.outputs.base_sha }}" in step
    assert "EVENT_NAME: ${{ github.event_name }}" in step
    command = textwrap.dedent(step.split("run: |\n", 1)[1])

    def git(*args: str) -> str:
        return subprocess.check_output(
            ["git", *args], cwd=tmp_path, text=True, stderr=subprocess.STDOUT,
        ).strip()

    git("init", "-q")
    git("config", "user.name", "CI Contract")
    git("config", "user.email", "ci-contract@example.test")
    runner = tmp_path / "infra/scripts/ci-local.sh"
    runner.parent.mkdir(parents=True)
    # Execute the real selection helper, but never run product tests or emit CI evidence.
    runner.write_text(
        '#!/usr/bin/env bash\nsource "$GRAF_TEST_CI_SOURCE"\n'
        'repo_root="$PWD"\nprintf "selection_started\\n"\nchanged_files\n',
    )
    runner.chmod(0o755)
    git("add", ".")
    git("commit", "-qm", "base")
    event_base = git("rev-parse", "HEAD")
    for name in ("server.txt", "macos.txt"):
        (tmp_path / name).write_text(name + "\n")
        git("add", name)
        git("commit", "-qm", name)
    git("update-ref", "refs/remotes/origin/master", "HEAD")
    bases = {"valid": event_base, "diagnostic": "", "missing": "", "invalid": "origin/master", "unavailable": "f" * 40}
    if base_kind == "unrelated":
        bases[base_kind] = git("commit-tree", "HEAD^{tree}", "-m", "unrelated root")

    def selected_paths() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", "-c", command], cwd=tmp_path, text=True, capture_output=True,
            env={**os.environ, "EVENT_NAME": event_name, "GRAF_CI_BASE_REF": bases[base_kind],
                 "GRAF_TEST_CI_SOURCE": str(ROOT / "infra/scripts/ci-local.sh")},
        )

    result = selected_paths()
    if base_kind not in {"valid", "diagnostic"}:
        assert result.returncode != 0
        assert "selection_started" not in result.stdout
        return
    assert result.returncode == 0, result.stderr
    expected = ["selection_started"] if base_kind == "diagnostic" else ["selection_started", "macos.txt", "server.txt"]
    assert result.stdout.split() == expected
    if base_kind == "valid":
        git("update-ref", "refs/remotes/origin/master", "HEAD~1")
        repeated = selected_paths()
        assert repeated.returncode == 0, repeated.stderr
        assert repeated.stdout.split() == expected


@pytest.mark.parametrize("fragment", [
    "GRAF_CI_BASE_REF: ${{ steps.identity.outputs.base_sha }}",
    'git merge-base HEAD "$GRAF_CI_BASE_REF" >/dev/null',
])
def test_governance_validator_rejects_unbound_or_unchecked_base(tmp_path: Path, fragment: str) -> None:
    source = (ROOT / ".github/workflows/governance-fast.yml").read_text()
    assert fragment in source
    path = tmp_path / "workflow.yml"
    path.write_text(source.replace(fragment, "# base protection removed"))
    assert any("base" in error for error in load_validator().validate(path))


def test_governance_workflow_binds_merge_group_identity_and_receipt() -> None:
    source = (ROOT / ".github/workflows/governance-fast.yml").read_text(encoding="utf-8")
    for marker in (
        "merge_group:",
        "github.event.merge_group.head_sha",
        "format('merge-group-{0}', github.event.merge_group.head_sha || github.sha)",
        "scripts/ci-event-identity.py",
        "scripts/emit-ci-receipt.py",
        "scripts/validate-ci-receipt.py",
        "scripts/verify-merge-group-mapping.py",
        "Verify authoritative merge-group mapping",
        "gh api --paginate --slurp",
        "--authoritative-response",
        "graf-merge-group-api.json",
        "github.run_attempt",
    ):
        assert marker in source


def test_governance_workflow_validates_pr_metadata_against_event_sha() -> None:
    source = (ROOT / ".github/workflows/governance-fast.yml").read_text(encoding="utf-8")
    assert "name: Validate pull request metadata" in source
    assert "if: ${{ github.event_name == 'pull_request' }}" in source
    assert 'event_path, body_path, feature_id_path = map(Path, sys.argv[1:4])' in source
    assert 'git", "diff", "--name-only"' in source
    assert 'changes/(?:unreleased|releases/v[^/]+)/F(\\d{3,})\\.yaml' in source
    assert 'feature_id_path.write_text(",".join(feature_ids) if feature_ids else "scoped"' in source
    assert '--scoped' in source
    assert 'pull_request = event.get("pull_request")' in source
    assert 'github.event.pull_request.head.sha' in source
    assert '--expected-sha "$EXPECTED_SHA"' in source
    assert '.specify/feature.json' not in source
    assert "types: [opened, synchronize, reopened, ready_for_review, edited]" in source


def test_governance_workflow_has_fail_closed_terminal_validators() -> None:
    source = (ROOT / ".github/workflows/governance-fast.yml").read_text(encoding="utf-8")
    assert "continue-on-error: true" not in source
    assert "name: Assert mandatory governance outcomes" in source
    assert "PR_METADATA_OUTCOME" in source
    assert "TERMINAL_OUTCOME" in source
    assert "RECEIPT_VALIDATION_OUTCOME" in source
    assert "if: ${{ always() }}" in source
    assert "name: Upload metadata-only evidence" in source


def test_governance_workflow_does_not_require_pr_body_for_non_pr_events() -> None:
    source = (ROOT / ".github/workflows/governance-fast.yml").read_text(encoding="utf-8")
    gate = source.split("- name: Validate pull request metadata", 1)[1]
    gate = gate.split("- name: Run bounded fast lane", 1)[0]
    assert "if: ${{ github.event_name == 'pull_request' }}" in gate
    assert "merge_group" not in gate
    assert "workflow_dispatch" not in gate


def test_governance_workflow_emits_terminal_receipt_after_failure_or_cancel() -> None:
    source = (ROOT / ".github/workflows/governance-fast.yml").read_text(encoding="utf-8")
    assert source.count("if: ${{ always() }}") >= 5
    assert "Prepare terminal metadata-only evidence and identity" in source
    assert '"reason": f"workflow_{status}_before_ci_evidence"' in source
    assert "${{ steps.terminal.outputs.evidence_path }}" in source
    assert "${{ steps.receipt.outputs.path }}" in source
    assert "path: |\n            ${{ steps.terminal.outputs.evidence_path }}" in source


def test_governance_workflow_rejects_production_and_stale_bypasses(tmp_path: Path) -> None:
    validator = load_validator()
    source = (ROOT / ".github/workflows/governance-fast.yml").read_text(encoding="utf-8")
    bad = source.replace("cancel-in-progress: true", "cancel-in-progress: false") + "\nrun: infra/scripts/cd-remote.sh --execute\n"
    path = tmp_path / "bad.yml"
    path.write_text(bad, encoding="utf-8")
    errors = validator.validate(path)
    assert any("cancel-in-progress" in item for item in errors)
    assert any("forbidden command" in item for item in errors)


def test_governance_workflow_self_test() -> None:
    assert load_validator().self_test() == 0
