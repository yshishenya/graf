from __future__ import annotations

from pathlib import Path
import importlib.util


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


def test_governance_workflow_binds_merge_group_identity_and_receipt() -> None:
    source = (ROOT / ".github/workflows/governance-fast.yml").read_text(encoding="utf-8")
    for marker in (
        "merge_group:",
        "github.event.merge_group.head_sha",
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
    assert 'event_path, body_path, feature_id_path = map(Path, sys.argv[1:])' in source
    assert 'pull_request = event.get("pull_request")' in source
    assert 'github.event.pull_request.head.sha' in source
    assert '--expected-sha "$EXPECTED_SHA"' in source
    assert '.specify/feature.json' not in source


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
