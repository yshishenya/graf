from __future__ import annotations

from pathlib import Path
import importlib.util
import json
import os
import shutil
import subprocess
import sys
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
        'repo_root="$PWD"\nprintf "selection_started\\n"\n'
        'paths="$(changed_files)" || exit $?\nbehavior_tests "$paths" --plan\n',
    )
    runner.chmod(0o755)
    for relative in (
        "scripts/ci-behavior-tests.py",
        "apps/server/tests/contract/test_cabinet_static_assets_contract.py",
        "apps/server/tests/contract/test_settings_ui_contract.py",
        "apps/server/tests/unit/test_settings_view_models.py",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    git("add", ".")
    git("commit", "-qm", "base")
    event_base = git("rev-parse", "HEAD")
    changed = ("apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js", "apps/macos/Sources/App.swift")
    for name in changed:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
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
    assert result.stdout.splitlines()[0] == "selection_started"
    plan = json.loads(result.stdout.splitlines()[1])
    assert plan["changed_paths"] == ([] if base_kind == "diagnostic" else sorted(changed))
    assert len(plan["tests"]) == (0 if base_kind == "diagnostic" else 3)
    local = subprocess.run(
        ["bash", "-c", 'source "$GRAF_TEST_CI_SOURCE"; repo_root="$PWD"; focused_main --plan'],
        cwd=tmp_path, text=True, capture_output=True,
        env={**os.environ, "GRAF_CI_BASE_REF": bases[base_kind], "GRAF_TEST_CI_SOURCE": str(ROOT / "infra/scripts/ci-local.sh")},
    )
    assert local.returncode == 0, local.stderr
    assert json.loads(local.stdout) == plan
    if base_kind == "valid":
        git("update-ref", "refs/remotes/origin/master", "HEAD~1")
        repeated = selected_paths()
        assert repeated.returncode == 0, repeated.stderr
        assert json.loads(repeated.stdout.splitlines()[1]) == plan


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


def test_governance_workflow_isolates_text_from_required_code_checks() -> None:
    import yaml
    source = (ROOT / ".github/workflows/governance-fast.yml").read_text()
    workflow = yaml.load(source, Loader=yaml.BaseLoader)
    assert "concurrency" not in workflow
    job = workflow["jobs"]["governance-fast"]
    assert job["needs"] == "scope"
    assert job["if"] == "${{ always() }}"
    assert job["name"] == "governance-fast"
    assert "github.run_id" in job["concurrency"]["group"]
    assert "needs.scope.outputs.text_only" in job["concurrency"]["group"]
    assert job["concurrency"]["cancel-in-progress"] == "true"
    assert "scripts/validate-pr-metadata.py" not in source
    assert "retention-days: 90" in source


def test_governance_text_event_cannot_enter_heavy_or_receipt_steps() -> None:
    import yaml
    workflow = yaml.load((ROOT / '.github/workflows/governance-fast.yml').read_text(), Loader=yaml.BaseLoader)
    steps = workflow['jobs']['governance-fast']['steps']
    shared = {'Require valid code scope', 'Checkout exact PR SHA', 'Resolve event identity', 'Verify exact SHA'}
    reuse_steps = []
    for step in steps:
        if step.get('name') in shared:
            continue
        if '--reuse-component' in step.get('run', ''):
            reuse_steps.append(step)
            assert step['if'] == "needs.scope.outputs.text_only == 'true'"
        else:
            assert "needs.scope.outputs.text_only == 'false'" in step.get('if', ''), step.get('name')
    assert len(reuse_steps) == 1
    assert 'continue-on-error' not in reuse_steps[0]


@pytest.mark.parametrize('reuse_status', [0, 1])
def test_actual_governance_text_path_propagates_proof_result_without_new_receipt(tmp_path, reuse_status):
    import yaml

    steps = yaml.load((ROOT / '.github/workflows/governance-fast.yml').read_text(), Loader=yaml.BaseLoader)['jobs']['governance-fast']['steps']
    # These are the actual workflow's simple conditions at text_only=true.
    conditions = {
        '': True,
        "needs.scope.outputs.text_only == 'true'": True,
        "needs.scope.outputs.text_only == 'false'": False,
        "always() && needs.scope.outputs.text_only == 'false'": False,
        "github.event_name == 'merge_group' && needs.scope.outputs.text_only == 'false'": False,
    }
    selected = [step for step in steps if conditions[step.get('if', '').replace('${{', '').replace('}}', '').strip()]]
    assert [step['name'] for step in selected] == [
        'Require valid code scope', 'Checkout exact PR SHA', 'Resolve event identity',
        'Verify exact SHA', 'Verify existing code proof',
    ]
    subprocess.run(['git', 'init', '-q'], cwd=tmp_path, check=True)
    subprocess.run(['git', '-c', 'user.name=Workflow Contract', '-c', 'user.email=workflow@example.test',
                    'commit', '--allow-empty', '-qm', 'fixture'], cwd=tmp_path, check=True)
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=tmp_path, text=True).strip()
    scripts = tmp_path / 'scripts'
    scripts.mkdir()
    shutil.copy2(ROOT / 'scripts/ci-event-identity.py', scripts)
    event = tmp_path / 'event.json'
    event.write_text(json.dumps(dict(action='edited', number=7, changes={'body': {'from': 'previous'}},
                                    pull_request=dict(number=7, head=dict(sha=sha), base=dict(sha=sha)))))
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    shim = bin_dir / 'python3'
    shim.write_text('#!/bin/sh\nif [ "$1" = -I ] && [ "$2" = scripts/validate-pr-checks.py ]; then\n'
                    '  printf "%s\\n" "$*" > "$REUSE_CALL"\n  exit "$REUSE_STATUS"\nfi\n'
                    'exec "$REAL_PYTHON" "$@"\n')
    shim.chmod(0o755)
    marker = tmp_path / 'reuse-call'
    environment = {**os.environ, 'PATH': str(bin_dir) + os.pathsep + os.environ['PATH'],
                   'REAL_PYTHON': sys.executable, 'REUSE_CALL': str(marker), 'REUSE_STATUS': str(reuse_status),
                   'SCOPE_RESULT': 'success', 'TEXT_ONLY': 'true', 'EVENT_NAME': 'pull_request',
                   'GRAF_CI_REQUESTED_SHA': sha, 'GITHUB_EVENT_PATH': str(event), 'RUNNER_TEMP': str(tmp_path),
                   'GITHUB_OUTPUT': str(tmp_path / 'outputs'), 'GITHUB_REPOSITORY': 'owner/repo',
                   'GITHUB_RUN_ID': '25', 'GITHUB_RUN_ATTEMPT': '1'}
    for step in selected:
        if 'uses' in step:
            assert step['uses'] == 'actions/checkout@v4'
            continue  # The fixture above is already checked out at the exact SHA.
        command = step['run'].replace('${{ steps.identity.outputs.target_sha }}', sha)
        result = subprocess.run(['bash', '-c', command], cwd=tmp_path, env=environment, capture_output=True, text=True)
        if step['name'] != 'Verify existing code proof':
            assert result.returncode == 0, result.stderr
        else:
            assert result.returncode == reuse_status, result.stderr
    assert '--reuse-component governance-fast' in marker.read_text()
    assert '--run-id 25 --run-attempt 1' in marker.read_text()
    assert not (tmp_path / '.dev/ci-evidence').exists()


def test_governance_workflow_has_fail_closed_terminal_validators() -> None:
    source = (ROOT / ".github/workflows/governance-fast.yml").read_text(encoding="utf-8")
    assert "continue-on-error: true" not in source
    assert "name: Assert mandatory governance outcomes" in source
    assert "PR_METADATA_OUTCOME" not in source
    assert "TERMINAL_OUTCOME" in source
    assert "RECEIPT_VALIDATION_OUTCOME" in source
    assert "if: ${{ always() }}" in source
    assert "name: Upload metadata-only evidence" in source


@pytest.mark.parametrize("scope,text,expected", [("success", "false", 0), ("success", "true", 0), ("failure", "", 1), ("cancelled", "false", 1)])
def test_actual_scope_failure_stops_before_expensive_code(scope, text, expected) -> None:
    import os
    import yaml
    workflow = yaml.load((ROOT / ".github/workflows/governance-fast.yml").read_text(), Loader=yaml.BaseLoader)
    first = workflow["jobs"]["governance-fast"]["steps"][0]
    assert first["name"] == "Require valid code scope"
    result = subprocess.run(["bash", "-c", first["run"]], env={**os.environ, "SCOPE_RESULT":scope, "TEXT_ONLY":text})
    assert result.returncode == expected


def test_governance_workflow_emits_terminal_receipt_after_failure_or_cancel() -> None:
    source = (ROOT / ".github/workflows/governance-fast.yml").read_text(encoding="utf-8")
    assert source.count("if: ${{ always() && needs.scope.outputs.text_only == 'false' }}") >= 5
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
