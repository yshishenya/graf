from __future__ import annotations

from pathlib import Path
import importlib.util
import hashlib
import json
import os
import shutil
import stat
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


@pytest.mark.parametrize("missing", [
    "all", "PROD_SSH_HOST", "PROD_SSH_USER", "PROD_SSH_KEY",
    "PROD_SSH_KNOWN_HOSTS", None,
])
def test_restore_workflow_stops_without_required_access(tmp_path: Path, missing: str | None) -> None:
    import yaml

    workflow = yaml.load(
        (ROOT / ".github/workflows/backup-restore-rehearsal.yml").read_text(),
        Loader=yaml.BaseLoader,
    )
    steps = workflow["jobs"]["rehearsal"]["steps"]
    index = next(i for i, step in enumerate(steps) if step.get("name") == "Require production host access")
    for step in steps[index + 1:]:
        assert step.get("if", "success()") == "success()"
    names = ("PROD_SSH_HOST", "PROD_SSH_USER", "PROD_SSH_KEY", "PROD_SSH_KNOWN_HOSTS")
    values = {name: f"synthetic-{name}" for name in names}
    summary = tmp_path / "summary"
    environment = {"PATH": os.defpath, "GITHUB_STEP_SUMMARY": str(summary)}
    environment.update({name: value for name, value in values.items() if missing not in ("all", name)})
    result = subprocess.run(
        ["bash", "-c", steps[index]["run"]], env=environment,
        capture_output=True, text=True, timeout=10,
    )
    output = result.stdout + result.stderr + (summary.read_text() if summary.exists() else "")
    assert not any(value in output for value in values.values())
    assert result.returncode == (0 if missing is None else 1), output
    if missing is None:
        assert result.stdout.strip() == "production_host_access_result=configured"
        assert not summary.exists()
    else:
        assert "restore_rehearsal_schedule_result=blocked" in result.stdout
        assert "reason=production_host_ssh_secret_missing" in result.stdout
        expected_missing = names if missing == "all" else (missing,)
        assert f"missing_secrets={','.join(expected_missing)}" in result.stdout
        assert "infra/scripts/rehearse-restore-scheduled.sh --execute" in summary.read_text()
        assert "production_host_access_result=configured" not in result.stdout


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
        if step.get('name') == 'Checkout current workflow tools':
            assert step['if'] == "needs.scope.outputs.text_only == 'true'"
            assert step['uses'] == 'actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1'
            assert step['with']['ref'] == '${{ github.workflow_sha }}'
            assert step['with']['path'] == '.ci-tools'
        elif '--reuse-component' in step.get('run', ''):
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
        'Require valid code scope', 'Checkout exact PR SHA', 'Checkout current workflow tools', 'Resolve event identity',
        'Verify exact SHA', 'Verify existing code proof',
    ]
    subprocess.run(['git', 'init', '-q'], cwd=tmp_path, check=True)
    subprocess.run(['git', '-c', 'user.name=Workflow Contract', '-c', 'user.email=workflow@example.test',
                    'commit', '--allow-empty', '-qm', 'fixture'], cwd=tmp_path, check=True)
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=tmp_path, text=True).strip()
    scripts = tmp_path / '.ci-tools/scripts'
    scripts.mkdir(parents=True)
    shutil.copy2(ROOT / 'scripts/ci-event-identity.py', scripts)
    event = tmp_path / 'event.json'
    event.write_text(json.dumps(dict(action='edited', number=7, changes={'body': {'from': 'previous'}},
                                    pull_request=dict(number=7, head=dict(sha=sha), base=dict(sha=sha)))))
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    shim = bin_dir / 'python3'
    shim.write_text('#!/bin/sh\nif [ "$1" = -I ] && [ "$2" = .ci-tools/scripts/validate-pr-checks.py ]; then\n'
                    '  printf "%s\\n" "$*" > "$REUSE_CALL"\n  exit "$REUSE_STATUS"\nfi\n'
                    'exec "$REAL_PYTHON" "$@"\n')
    shim.chmod(0o755)
    marker = tmp_path / 'reuse-call'
    environment = {**os.environ, 'PATH': str(bin_dir) + os.pathsep + os.environ['PATH'],
                   'REAL_PYTHON': sys.executable, 'REUSE_CALL': str(marker), 'REUSE_STATUS': str(reuse_status),
                   'SCOPE_RESULT': 'success', 'TEXT_ONLY': 'true', 'EVENT_NAME': 'pull_request',
                   'TOOL_ROOT': '.ci-tools',
                   'GRAF_CI_REQUESTED_SHA': sha, 'GITHUB_EVENT_PATH': str(event), 'RUNNER_TEMP': str(tmp_path),
                   'GITHUB_OUTPUT': str(tmp_path / 'outputs'), 'GITHUB_REPOSITORY': 'owner/repo',
                   'GITHUB_RUN_ID': '25', 'GITHUB_RUN_ATTEMPT': '1'}
    for step in selected:
        if 'uses' in step:
            assert step['uses'] == 'actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1'
            if step['name'] == 'Checkout current workflow tools':
                assert step['with']['ref'] == '${{ github.workflow_sha }}'
                assert step['with']['path'] == '.ci-tools'
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
    assert '"reason": f"workflow_{status}_at_terminal_step"' in source
    assert "${{ steps.terminal.outputs.evidence_path }}" in source
    assert "${{ steps.receipt.outputs.path }}" in source
    assert "path: |\n            ${{ steps.terminal.outputs.evidence_path }}" in source


@pytest.mark.parametrize("job_status", ["success", "failure", "cancelled", "unknown"])
@pytest.mark.parametrize("local_status", [None, "passed", "failed", "stale", "cancelled", "superseded", "ambiguous"])
@pytest.mark.parametrize("discovery", ["configured", "discovered"])
def test_actual_terminal_receipt_preserves_known_job_failure(tmp_path, job_status, local_status, discovery):
    import yaml

    workflow = yaml.load((ROOT / ".github/workflows/governance-fast.yml").read_text(), Loader=yaml.BaseLoader)
    terminal = next(step for step in workflow["jobs"]["governance-fast"]["steps"] if step.get("id") == "terminal")
    sha, base = "a" * 40, "b" * 40
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"number": 7, "pull_request": {"number": 7, "base": {"sha": base}}}))
    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir()
    local = tmp_path / ".dev/ci-evidence/local.json"
    local.parent.mkdir(parents=True)
    original = None
    if local_status is not None:
        local.write_text(json.dumps({
            "run_id": "ci-local-25", "lane": "fast", "status": local_status,
            "requested_sha": sha, "observed_sha_start": sha, "observed_sha_end": sha,
            "started_at": "2026-10-28T00:00:00Z", "finished_at": "2026-10-28T00:00:01Z",
            "commands": ["synthetic fast lane"], "skipped_gates": [], "scope": "synthetic contract",
            "reason": "synthetic_" + local_status, "artifact_digests": {"fixture": "sha256:" + "c" * 64},
            "component_shas": {"repository": sha},
        }))
        original = local.read_bytes()
    output = tmp_path / "outputs"
    result = subprocess.run(
        ["bash", "-c", terminal["run"]], cwd=tmp_path, capture_output=True, text=True, timeout=10,
        env={**os.environ, "GITHUB_EVENT_PATH": str(event), "RUNNER_TEMP": str(runner_temp),
             "GITHUB_OUTPUT": str(output), "EVENT_NAME": "pull_request", "JOB_STATUS": job_status,
             "GRAF_CI_REQUESTED_SHA": sha, "RUN_ID": "25",
             "GRAF_CI_EVIDENCE_PATH": str(local) if discovery == "configured" else "missing.json"},
    )
    assert result.returncode == 0, result.stderr
    selected = tmp_path / dict(line.split("=", 1) for line in output.read_text().splitlines())["evidence_path"]
    receipt = tmp_path / "receipt.json"
    emitted = subprocess.run(
        [sys.executable, str(ROOT / "scripts/emit-ci-receipt.py"),
         "--identity", str(runner_temp / "graf-event-identity.json"), "--evidence", str(selected),
         "--output", str(receipt), "--workflow", "governance-fast", "--run-id", "25", "--run-attempt", "2",
         "--workflow-url", "https://github.com/owner/repo/actions/runs/25"],
        capture_output=True, text=True, timeout=10,
    )
    assert emitted.returncode == 0, emitted.stderr
    value = json.loads(receipt.read_text())
    expected = local_status if job_status == "success" and local_status is not None else "cancelled" if job_status == "cancelled" else "failed"
    assert value["status"] == value["conclusion"] == expected
    assert value["cancellation_state"] == ("cancelled" if expected == "cancelled" else "none")
    assert value["supersession_state"] == ("superseded" if expected == "superseded" else "none")
    assert value["final_cleanliness"] == {"passed": "pass", "failed": "fail", "stale": "stale"}.get(expected, "ambiguous")
    assert value["local_evidence_digest"] == "sha256:" + hashlib.sha256(selected.read_bytes()).hexdigest()
    assert value["target_sha"] == value["requested_sha"] == value["observed_sha_start"] == value["observed_sha_end"] == sha
    assert value["base_sha"] == base and value["pull_request_numbers"] == [7]
    assert value["event_name"] == "pull_request" and value["run_id"] == "25" and value["run_attempt"] == 2
    assert (selected == local) == (job_status == "success" and local_status is not None)
    assert (local.read_bytes() if local.exists() else None) == original
    for script, accepted in [("validate-ci-receipt.py", True), ("validate-ci-evidence.py", expected == "passed")]:
        validation = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script), str(receipt if "receipt" in script else selected)],
            capture_output=True, text=True, timeout=10,
        )
        assert (validation.returncode == 0) == accepted, validation.stdout + validation.stderr


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


@pytest.mark.parametrize("workflow_name,job_name", [
    ("release-full", "server-parallel"), ("release-full", "server-phases"),
    ("governance-fast", "governance-fast"),
])
@pytest.mark.parametrize("tools_state", [
    "working", "missing-ffmpeg", "missing-ffprobe", "update-failed", "install-failed",
    "broken-ffmpeg", "broken-ffprobe", "non-server", "helper-change", "other-infra", "mirror-failed", "npm-failed", "browser-failed",
    "write-failed", "replace-failed", "readback-failed", "changed-source",
    "unknown-mirror", "duplicate-mirror", "missing-mirror", "bad-source", "missing-source",
    "crlf-mirror", "mirror-symlink", "source-symlink", "second-source", "continued-source",
    "disabled-source", "duplicate-source", "multiple-stanzas", "mixed-suites", "security-only",
    "deb-src", "wide-fields", "optional-fields", "canonical", "diag-direct", "diag-unknown", "diag-credential",
    "diag-backslash", "diag-nul", "diag-empty-port", "diag-long", "diag-multi", "diag-query", "diag-fragment",
    "bad-os", "bad-version", "bad-codename", "bad-arch", "foreign-arch", "self-hosted",
    "source-owner", "source-mode", "parent-owner", "parent-mode", "parent-symlink",
    "key-owner", "key-mode", "key-symlink", "key-missing", "key-empty", "key-oversize",
    "source-empty", "source-oversize", "non-ascii", "del-source", "unknown-field", "trusted",
    "bad-type", "duplicate-type", "bad-suite", "duplicate-suite", "bad-component", "duplicate-component",
    "bad-signed-by", "bad-architecture", "duplicate-field", "malformed", "empty-uri",
    "known-key", "unknown-key", "known-key-bad-source", "known-key-mode", "known-key-owner", "known-key-group",
    "key-parent-owner", "key-parent-mode", "key-parent-symlink", "key-write-failed", "key-replace-failed",
    "key-readback-failed", "changed-key", "changed-key-parent", "key-open-writer",
    "key-parent-safe-key", "key-parent-safe-open-writer", "key-parent-safe-unknown", "key-parent-unknown", "key-parent-bad-source",
    "key-parent-other-mode", "key-parent-group", "key-ancestor-owner", "key-ancestor-mode",
    "key-ancestor-symlink", "key-ancestor-upper-mode", "key-parent-open-changed", "key-parent-chmod-failed",
    "key-parent-chmod-noop", "key-parent-sync-failed", "key-parent-path-changed",
    "key-parent-key-changed", "key-parent-source-changed",
])
def test_actual_media_resource_preparation(tmp_path, workflow_name, job_name, tools_state):
    import yaml

    workflow = yaml.load((ROOT / f".github/workflows/{workflow_name}.yml").read_text(), Loader=yaml.BaseLoader)
    step = next(step for step in workflow["jobs"][job_name]["steps"]
                if "browser" in step.get("name", "").lower() and "resources" in step["name"])
    runner = tmp_path / "infra/scripts/ci-local.sh"
    runner.parent.mkdir(parents=True)
    runner.write_text('source "$CI_SOURCE"\nchanged_files() { printf "%s\\n" "$CHANGED_PATH"; }\n')
    browser = tmp_path / "apps/server/tests/browser/node_modules/.bin/playwright"
    browser.parent.mkdir(parents=True)
    browser.write_text('#!/bin/sh\nprintf "browser\\n" >> "$PREP_EVENTS"\n[ "$TOOLS_STATE" != browser-failed ]\n')
    browser.chmod(0o755)
    apt = tmp_path / "apt"
    parent = apt / "sources.list.d"
    parent.mkdir(parents=True)
    parent.chmod(0o755)
    key_parent = tmp_path / "keyrings"
    key_parent.mkdir(mode=0o755)
    key = key_parent / "ubuntu-archive-keyring.gpg"
    known_key = b"fixture-keyring" + b"x" * (3607 - len(b"fixture-keyring"))
    key_cases = {"known-key", "unknown-key", "known-key-bad-source", "known-key-mode", "known-key-owner", "known-key-group",
                 "key-parent-owner", "key-parent-mode", "key-parent-symlink", "key-write-failed", "key-replace-failed",
                 "key-readback-failed", "changed-key", "changed-key-parent", "key-open-writer"}
    directory_cases = {"key-parent-mode", "key-parent-safe-key", "key-parent-safe-open-writer", "key-parent-safe-unknown", "key-parent-unknown",
                       "key-parent-bad-source", "key-parent-other-mode", "key-parent-group", "key-ancestor-owner",
                       "key-ancestor-mode", "key-ancestor-symlink", "key-ancestor-upper-mode", "key-parent-open-changed",
                       "key-parent-chmod-failed", "key-parent-chmod-noop", "key-parent-sync-failed",
                       "key-parent-path-changed", "key-parent-key-changed", "key-parent-source-changed"}
    key_cases |= directory_cases
    key.write_bytes(b"fixture-keyring")
    source = parent / "ubuntu.sources"
    source_text = ("Types: deb\nURIs: mirror+file:/etc/apt/apt-mirrors.txt\n"
                   "Suites: noble noble-updates noble-backports\nComponents: main universe restricted multiverse\n"
                   "Architectures: amd64\nSigned-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n")
    source.write_text(source_text.replace("/etc/apt", str(apt)))
    third_party = parent / "third-party.list"
    third_party.write_text("deb [signed-by=/some/key.gpg] https://example.invalid/packages stable main\n")
    mirror = apt / "apt-mirrors.txt"
    original = ("http://azure.archive.ubuntu.com/ubuntu/\tpriority:1\n"
                "https://archive.ubuntu.com/ubuntu/\tpriority:2\n"
                "https://security.ubuntu.com/ubuntu/\tpriority:3\n")
    mirror.write_text(original)
    platform_file = tmp_path / "os-release"
    platform_file.write_text('ID=ubuntu\nVERSION_ID="24.04"\nVERSION_CODENAME=noble\n')
    diagnostic_uris = {
        "diag-direct": "https://archive.ubuntu.com/ubuntu/",
        "diag-unknown": "https://fixture-private-value.invalid/ubuntu/",
        "diag-credential": "https://fixture-private-value:fixture-only@archive.ubuntu.com/ubuntu/",
        "diag-backslash": r"https://fixture-private-value\.ubuntu.com/ubuntu/",
        "diag-nul": "https://fixture-private-value\0.ubuntu.com/ubuntu/",
        "diag-empty-port": "https://archive.ubuntu.com:/ubuntu/",
        "diag-long": "https://archive.ubuntu.com/ubuntu/?" + "fixture-private-value" * 250,
        "diag-multi": f"mirror+file:{apt}/apt-mirrors.txt https://archive.ubuntu.com/ubuntu/",
        "diag-query": "https://archive.ubuntu.com/ubuntu/?fixture-private-value",
        "diag-fragment": "https://archive.ubuntu.com/ubuntu/#fixture-private-value",
    }
    replacements = {
        "bad-source": ("mirror+file:", "file:"), "continued-source": ("\nSuites:", "\n continued\nSuites:"),
        "security-only": ("noble noble-updates noble-backports", "noble-security"),
        "mixed-suites": ("noble noble-updates noble-backports", "noble noble-security noble-updates"),
        "deb-src": ("Types: deb", "Types: deb deb-src"), "bad-type": ("Types: deb", "Types: rpm"),
        "duplicate-type": ("Types: deb", "Types: deb deb"), "bad-suite": ("Suites: noble", "Suites: jammy"),
        "duplicate-suite": ("Suites: noble", "Suites: noble noble"),
        "bad-component": ("Components: main", "Components: private"),
        "duplicate-component": ("Components: main", "Components: main main"),
        "bad-signed-by": ("Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg", "Signed-By: /other/key.gpg"),
        "bad-architecture": ("Architectures: amd64", "Architectures: arm64"),
        "optional-fields": ("Architectures: amd64\n", "Enabled: yes\n"),
        "empty-uri": (f"URIs: mirror+file:{apt}/apt-mirrors.txt", "URIs:"),
        "canonical": (f"URIs: mirror+file:{apt}/apt-mirrors.txt", "URIs: https://archive.ubuntu.com/ubuntu/"),
    }
    if tools_state in diagnostic_uris:
        source.write_text(source.read_text().replace(f"mirror+file:{apt}/apt-mirrors.txt", diagnostic_uris[tools_state]))
    elif tools_state == "wide-fields":
        source.write_text(source.read_text().replace("Types: deb", "Types: deb" + " " * 5000 + "deb-src")
                          .replace("noble noble-updates noble-backports", "noble noble-updates noble-backports noble-security"))
        assert source.stat().st_size < 16384
    elif tools_state in replacements:
        source.write_text(source.read_text().replace(*replacements[tools_state]))
    elif tools_state == "unknown-mirror":
        mirror.write_text(original + "https://other.invalid/ubuntu/\tpriority:1\n")
    elif tools_state == "duplicate-mirror":
        mirror.write_text(original + original)
    elif tools_state == "missing-mirror":
        mirror.unlink()
    elif tools_state in {"second-source", "multiple-stanzas"}:
        extra = source.read_text()
        if tools_state == "multiple-stanzas":
            extra = extra.replace("noble noble-updates noble-backports", "noble-security")
        source.write_text(source.read_text() + "\n" + extra)
    elif tools_state in {"disabled-source", "duplicate-source", "unknown-field", "trusted", "duplicate-field", "malformed", "del-source", "non-ascii"}:
        source.write_text(source.read_text() + {
            "disabled-source": "Enabled: no\n", "duplicate-source": "URIs: https://other.invalid/ubuntu/\n",
            "unknown-field": "Check-Valid-Until: no\n", "trusted": "Trusted: yes\n",
            "duplicate-field": "types: deb\n", "malformed": "broken line\n", "del-source": "#\x7f\n",
            "non-ascii": "# пример\n",
        }[tools_state])
    elif tools_state in {"missing-source", "key-missing"}:
        (source if tools_state == "missing-source" else key).unlink()
    elif tools_state == "crlf-mirror":
        mirror.write_bytes(original.replace("\n", "\r\n").encode())
    elif tools_state in {"source-empty", "source-oversize", "key-empty", "key-oversize"}:
        target = source if tools_state.startswith("source-") else key
        target.write_bytes(b"" if tools_state.endswith("empty") else b"x" * (16385 if target == source else 1048577))
    elif tools_state in {"source-mode", "parent-mode", "key-mode"}:
        {"source-mode": source, "parent-mode": parent, "key-mode": key}[tools_state].chmod(0o777)
    elif tools_state in {"mirror-symlink", "source-symlink", "parent-symlink", "key-symlink"}:
        target = {"mirror-symlink": mirror, "source-symlink": source, "parent-symlink": parent, "key-symlink": key}[tools_state]
        saved = target.with_suffix(".saved")
        target.rename(saved)
        target.symlink_to(saved)
    elif tools_state in {"bad-os", "bad-version", "bad-codename"}:
        platform_file.write_text(platform_file.read_text().replace(*{
            "bad-os": ("ubuntu", "debian"), "bad-version": ("24.04", "26.04"), "bad-codename": ("noble", "jammy"),
        }[tools_state]))
    if tools_state in key_cases:
        key.write_bytes(known_key if tools_state not in {"unknown-key", "key-parent-unknown", "key-parent-safe-unknown"} else known_key[:-1] + b"y")
        key.chmod(0o666 if tools_state == "known-key-mode" else 0o777)
        if tools_state in {"known-key-bad-source", "key-parent-bad-source"}:
            source.write_text(source.read_text() + "broken line\n")
        elif tools_state == "key-parent-symlink":
            saved_parent = key_parent.with_suffix(".saved")
            key_parent.rename(saved_parent)
            key_parent.symlink_to(saved_parent)
        if tools_state in directory_cases:
            key_parent.chmod(0o775 if tools_state == "key-parent-other-mode" else 0o777)
        if tools_state in {"key-parent-safe-key", "key-parent-safe-open-writer", "key-parent-safe-unknown"}:
            key.chmod(0o644)
    key_parent_mode_before = key_parent.lstat().st_mode
    key_before = key.read_bytes() if key.exists() else None
    key_stat_before = key.stat() if key.exists() else None
    source_before = source.read_bytes() if source.exists() else None
    mirror_before = mirror.read_bytes() if mirror.exists() else None
    third_before = third_party.read_bytes()
    mode_before = source.stat().st_mode if source.exists() else None
    helper = ROOT / "infra/scripts/prepare-ci-apt.sh"
    (runner.parent / helper.name).write_text(helper.read_text().replace("/etc/apt", str(apt))
        .replace("/usr/lib/os-release", str(platform_file))
        .replace("Path('/usr/share/keyrings/ubuntu-archive-keyring.gpg')", f"Path({str(key)!r})")
        .replace("80a36b0a6de2f69f49d2df75ef473ccde121e9e190b9ea01d20a4f63778d5c31", hashlib.sha256(known_key).hexdigest()))
    # Explicit local model of root metadata; the security branches still execute.
    model = tmp_path / "root-model.py"
    model.write_text(r'''
import os, sys, types
from pathlib import Path
from unittest.mock import patch
state = os.environ["TOOLS_STATE"]
source, parent, key = map(Path, (os.environ["APT_SOURCE"], os.environ["APT_PARENT"], os.environ["APT_KEY"]))
real_lstat, real_fstat = Path.lstat, os.fstat
inodes = {p.stat().st_ino: label for p, label in ((source, "source"), (parent, "parent"), (key, "key"), (key.parent, "key-parent")) if p.exists()}
inodes[key.parent.parent.stat().st_ino] = "key-ancestor"
inodes[key.parent.parent.parent.stat().st_ino] = "key-ancestor-upper"
def root_stat(value):
    attrs = {n: getattr(value, n) for n in dir(value) if n.startswith("st_")}
    label = inodes.get(value.st_ino)
    attrs.update(st_uid=1 if state == f"{label}-owner" or label == "key" and state == "known-key-owner" else 0,
                 st_gid=1 if label == "key" and state == "known-key-group" or label == "key-parent" and state == "key-parent-group" else 0)
    if label in {"key-ancestor", "key-ancestor-upper"} and state == f"{label}-mode":
        attrs['st_mode'] = stat.S_IFDIR | 0o777
    if label == "key-ancestor" and state == "key-ancestor-symlink":
        attrs['st_mode'] = stat.S_IFLNK | 0o755
    return types.SimpleNamespace(**attrs)
patch.object(Path, "lstat", lambda p: root_stat(real_lstat(p))).start()
patch("os.fstat", lambda fd: root_stat(real_fstat(fd))).start()
patch("os.fchown", lambda fd, uid, gid: None).start()
import stat
if state in {"key-parent-chmod-failed", "key-parent-chmod-noop"}:
    real_fchmod = os.fchmod
    def directory_chmod(fd, mode):
        if stat.S_ISDIR(real_fstat(fd).st_mode):
            if state.endswith('failed'):
                raise PermissionError('fixture directory chmod failed')
            return
        real_fchmod(fd, mode)
    patch('os.fchmod', directory_chmod).start()
if state == 'key-parent-open-changed':
    real_open = os.open
    def directory_open(path, flags, *args, **kwargs):
        if Path(path) == key.parent:
            key.parent.chmod(0o755)
        return real_open(path, flags, *args, **kwargs)
    patch('os.open', directory_open).start()
if state in {'key-parent-sync-failed', 'key-parent-path-changed', 'key-parent-key-changed', 'key-parent-source-changed'}:
    real_fsync = os.fsync
    def directory_sync(fd):
        if stat.S_ISDIR(real_fstat(fd).st_mode):
            if state == 'key-parent-sync-failed':
                raise PermissionError('fixture directory sync failed')
            if state == 'key-parent-path-changed':
                key.parent.chmod(0o777)
            else:
                target = source if state == 'key-parent-source-changed' else key
                target.write_bytes(target.read_bytes() + b'# fixture changed\n')
        real_fsync(fd)
    patch('os.fsync', directory_sync).start()
if state in {"write-failed", "key-write-failed"}:
    patch("os.fsync", side_effect=PermissionError("fixture write failure")).start()
if state in {"replace-failed", "key-replace-failed"}:
    patch("os.replace", side_effect=PermissionError("fixture replace failure")).start()
if state in {"changed-source", "changed-key", "changed-key-parent"}:
    real_fsync = os.fsync
    def changed(fd):
        real_fsync(fd)
        if state == "changed-key-parent":
            key.parent.chmod(0o777)
        else:
            target = source if state == "changed-source" else key
            target.write_bytes(target.read_bytes() + b"# fixture changed\n")
    patch("os.fsync", changed).start()
if state in {"readback-failed", "key-readback-failed"}:
    real_replace = os.replace
    def corrupt(src, dst):
        real_replace(src, dst)
        Path(dst).write_bytes(b"# fixture failed readback\n")
    patch("os.replace", corrupt).start()
if state in {"key-open-writer", "key-parent-safe-open-writer"}:
    old_key_fd = os.open(key, os.O_WRONLY)
    real_replace = os.replace
    def old_writer(src, dst):
        real_replace(src, dst)
        if Path(dst) == key:
            os.write(old_key_fd, b"fixture-private-value")
    patch("os.replace", old_writer).start()
exec(compile(sys.stdin.read(), "prepare-ci-apt.sh", "exec"))
''')
    dpkg = tmp_path / "bin/dpkg"
    dpkg.parent.mkdir()
    dpkg.write_text('#!/bin/sh\ncase "$1" in\n--print-architecture) if [ "$TOOLS_STATE" = bad-arch ]; then echo arm64; else echo amd64; fi;;\n--print-foreign-architectures) if [ "$TOOLS_STATE" = foreign-arch ]; then echo arm64; fi;;\n*) exit 91;;\nesac\n')
    dpkg.chmod(0o755)
    events = tmp_path / "events"
    harness = r'''
installed=0
command() {
  if [[ "${1:-}" == -v && ( "${2:-}" == ffmpeg || "${2:-}" == ffprobe ) ]]; then
    [[ "$installed" == 1 || ( "$TOOLS_STATE" != "missing-$2" && "$TOOLS_STATE" != install-failed && "$TOOLS_STATE" != update-failed ) ]]
  else builtin command "$@"; fi
}
sudo() {
  if [[ "$1" == python3 ]]; then
    printf 'mirror\n' >> "$PREP_EVENTS"
    [[ "$TOOLS_STATE" != mirror-failed ]] || return 23
    builtin command python3 "$ROOT_MODEL"
    return
  fi
  [[ "$1" == apt-get ]] || return 99
  ! grep -q azure "$APT_SOURCE" || return 98
  printf '%s\n' "$*" >> "$PREP_EVENTS"
  [[ "$TOOLS_STATE" != update-failed || "$2" != update ]] || return 23
  [[ "$TOOLS_STATE" != install-failed || "$2" != install ]] || return 23
  if [[ "$2" == install ]]; then installed=1; fi
}
npm() { printf 'npm\n' >> "$PREP_EVENTS"; [[ "$TOOLS_STATE" != npm-failed ]]; }
ffmpeg() { printf 'ffmpeg\n' >> "$PREP_EVENTS"; [[ "$TOOLS_STATE" != broken-ffmpeg ]]; }
ffprobe() { printf 'ffprobe\n' >> "$PREP_EVENTS"; [[ "$TOOLS_STATE" != broken-ffprobe ]]; }
'''
    env = {**os.environ, "CI_SOURCE": str(ROOT / "infra/scripts/ci-local.sh"),
           "CHANGED_PATH": {"non-server": "README.md", "helper-change": "infra/scripts/prepare-ci-apt.sh",
                            "other-infra": "infra/scripts/ci-local.sh"}.get(tools_state, "apps/server/src/example.py"),
           "TOOLS_STATE": tools_state, "PREP_EVENTS": str(events), "ROOT_MODEL": str(model),
           "APT_SOURCE": str(source), "APT_PARENT": str(parent), "APT_KEY": str(key),
           "GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux",
           "RUNNER_ENVIRONMENT": "self-hosted" if tools_state == "self-hosted" else "github-hosted",
           "PATH": str(dpkg.parent) + os.pathsep + os.environ["PATH"]}
    result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", harness + step["run"]],
                            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10)
    rows = events.read_text().splitlines() if events.exists() else []
    if workflow_name == "governance-fast" and tools_state in {"non-server", "other-infra"}:
        assert result.returncode == 0 and not rows, result.stderr
        return
    helper_failures = {
        "mirror-failed", "write-failed", "replace-failed", "readback-failed", "changed-source",
        "missing-source", "source-symlink", "second-source", "continued-source", "disabled-source",
        "duplicate-source", "diag-nul", "bad-os", "bad-version", "bad-codename", "bad-arch", "foreign-arch",
        "self-hosted", "source-owner", "source-mode", "parent-owner", "parent-mode", "parent-symlink",
        "key-owner", "key-mode", "key-symlink", "key-missing", "key-empty", "key-oversize", "source-empty",
        "source-oversize", "non-ascii", "del-source", "unknown-field", "trusted", "bad-type", "duplicate-type",
        "bad-suite", "duplicate-suite", "bad-component", "duplicate-component", "bad-signed-by",
        "bad-architecture", "duplicate-field", "malformed", "empty-uri",
        "unknown-key", "known-key-bad-source", "known-key-mode", "known-key-owner", "known-key-group",
        "key-parent-owner", "key-parent-symlink", "key-write-failed", "key-replace-failed",
        "key-readback-failed", "changed-key", "changed-key-parent",
    }
    directory_success = {"key-parent-mode", "key-parent-safe-key", "key-parent-safe-open-writer"}
    helper_failures |= directory_cases - directory_success
    later_failures = {"update-failed", "install-failed", "broken-ffmpeg", "broken-ffprobe", "npm-failed", "browser-failed"}
    failed = tools_state in helper_failures | later_failures
    assert (result.returncode != 0) == failed, result.stdout + result.stderr
    assert rows == ([] if tools_state == "self-hosted" else ["mirror"]) if tools_state in helper_failures else rows[0] == "mirror"
    assert "fixture-private-value" not in result.stdout + result.stderr
    if tools_state in {"key-parent-owner", "key-parent-symlink"}:
        metadata = key_parent.lstat()
        uid = 1 if tools_state == "key-parent-owner" else 0
        assert result.stderr.strip() == (
            f"CI APT preparation: unsafe keyring-directory metadata type={stat.S_IFMT(metadata.st_mode)} "
            f"uid={uid} gid=0 mode={stat.S_IMODE(metadata.st_mode):o} size={metadata.st_size}"
        )
    if tools_state in {"source-owner", "source-mode", "source-symlink", "source-empty", "source-oversize",
                       "key-owner", "key-mode", "key-symlink", "key-empty", "key-oversize"}:
        label = "source" if tools_state.startswith("source-") else "keyring"
        metadata = (source if label == "source" else key).lstat()
        uid = 1 if tools_state.endswith("owner") else 0  # Explicit root model above.
        assert result.stderr.strip() == (
            f"CI APT preparation: unsafe {label} metadata type={stat.S_IFMT(metadata.st_mode)} "
            f"uid={uid} gid=0 mode={stat.S_IMODE(metadata.st_mode):o} size={metadata.st_size}"
        )
    assert (mirror.read_bytes() if mirror.exists() else None) == mirror_before
    assert third_party.read_bytes() == third_before
    if tools_state not in {"changed-key", "key-readback-failed", "key-parent-key-changed"}:
        assert (key.read_bytes() if key.exists() else None) == key_before
    if tools_state in {"known-key", "key-open-writer"} | directory_success:
        assert key.stat().st_ino != key_stat_before.st_ino
        assert stat.S_IMODE(key.stat().st_mode) == 0o644
    elif tools_state in key_cases - {"key-readback-failed"}:
        assert key.stat().st_ino == key_stat_before.st_ino
        assert key.stat().st_mode == key_stat_before.st_mode
    if tools_state in directory_success:
        assert stat.S_IMODE(key_parent.stat().st_mode) == 0o755
    elif tools_state in directory_cases - {"key-parent-open-changed", "key-parent-sync-failed", "key-parent-path-changed",
                                            "key-parent-key-changed", "key-parent-source-changed"}:
        assert key_parent.lstat().st_mode == key_parent_mode_before
    if tools_state in helper_failures:
        if tools_state not in {"changed-source", "readback-failed", "key-parent-source-changed"}:
            assert (source.read_bytes() if source.exists() else None) == source_before
    else:
        def tuples(data):
            sections = [dict(line.split(":", 1) for line in section.splitlines() if line and not line.startswith("#"))
                        for section in data.decode().strip().split("\n\n")]
            return {suite: {k: tuple(v.split()) for k, v in fields.items() if k not in {"URIs", "Suites"}}
                    for fields in sections for suite in fields["Suites"].split()}
        after = source.read_bytes()
        assert tuples(after) == tuples(source_before)
        for section in after.decode().strip().split("\n\n"):
            fields = dict(line.split(":", 1) for line in section.splitlines())
            expected = "security" if fields["Suites"].strip() == "noble-security" else "archive"
            assert fields["URIs"].strip() == f"https://{expected}.ubuntu.com/ubuntu/"
        assert source.stat().st_mode == mode_before
        before = (source.read_bytes(), source.stat().st_mtime_ns)
        key_repeat_before = (key.read_bytes(), key.stat().st_ino, key.stat().st_mode, key.stat().st_mtime_ns)
        repeat = subprocess.run(["bash", "-e", "-c", harness + "source infra/scripts/prepare-ci-apt.sh"],
                                cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10)
        assert repeat.returncode == 0, repeat.stderr
        assert (source.read_bytes(), source.stat().st_mtime_ns) == before
        assert (key.read_bytes(), key.stat().st_ino, key.stat().st_mode, key.stat().st_mtime_ns) == key_repeat_before
    assert not list(parent.glob(".ubuntu.sources-*"))
    assert not list(key_parent.glob(".ubuntu-keyring-*"))
    installs = [row for row in rows if row.startswith("apt-get")]
    if tools_state in {"missing-ffmpeg", "missing-ffprobe", "install-failed"}:
        assert len(installs) == 2 and installs[0] == "apt-get update"
        assert installs[1].endswith("ffmpeg")
    elif tools_state == "update-failed":
        assert installs == ["apt-get update"]
    else:
        assert installs == []
    if tools_state in helper_failures | {"update-failed", "install-failed", "broken-ffmpeg", "broken-ffprobe"}:
        assert "npm" not in rows and "browser" not in rows
    elif tools_state == "npm-failed":
        assert "browser" not in rows
    if not failed:
        assert rows.count("ffmpeg") == rows.count("ffprobe") == rows.count("npm") == rows.count("browser") == 1


ACTION_PINS = {
    'actions/checkout': '3d3c42e5aac5ba805825da76410c181273ba90b1',
    'actions/cache': '55cc8345863c7cc4c66a329aec7e433d2d1c52a9',
    'actions/setup-node': '949feb2413d6458794dcd2491c4babbbce0c15c1',
    'actions/setup-python': '5fda3b95a4ea91299a34e894583c3862153e4b97',
    'actions/upload-artifact': 'cf430e030ddbb5b0abf93d22962f4752f3646cd9',
    'actions/download-artifact': '9000827ccba6bdab643e8b6fd33ac0654aef8333',
}


def test_actions_use_reviewed_node24_pins_and_preserve_artifact_contract():
    import yaml

    found = set()
    for path in (ROOT / '.github/workflows').glob('*.yml'):
        workflow = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
        for job in workflow['jobs'].values():
            for step in job.get('steps', []):
                if 'uses' not in step:
                    continue
                action, pin = step['uses'].split('@')
                assert pin == ACTION_PINS[action], (path.name, action, pin)
                found.add(action)
                inputs = step.get('with', {})
                if action == 'actions/checkout':
                    assert inputs['persist-credentials'] == 'false'
                elif action == 'actions/setup-node':
                    assert inputs['package-manager-cache'] == 'false'
                    assert inputs['node-version'] == '22.23.4'
                elif action == 'actions/upload-artifact':
                    assert inputs['archive'] == 'true'
                    assert inputs['name']
                elif action == 'actions/download-artifact':
                    assert inputs.get('skip-decompress', 'false') == 'false'
                    assert inputs.get('digest-mismatch', 'error') == 'error'
        assert 'ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION' not in path.read_text()
        assert 'FORCE_JAVASCRIPT_ACTIONS_TO_NODE' not in path.read_text()
    assert found == set(ACTION_PINS)


@pytest.mark.parametrize('workflow_name,job_name', [
    ('macos-pr', 'native'), ('release-full', 'macos-full'), ('macos-diagnostic', 'macos-diagnostic'),
])
def test_native_jobs_pin_supported_image_and_developer(workflow_name, job_name):
    import yaml

    workflow = yaml.load((ROOT / f'.github/workflows/{workflow_name}.yml').read_text(), Loader=yaml.BaseLoader)
    job = workflow['jobs'][job_name]
    assert job['runs-on'] == 'macos-15'
    assert job['env']['DEVELOPER_DIR'] == '/Applications/Xcode_16.2.app/Contents/Developer'


@pytest.mark.parametrize('workflow_name', ['macos-pr', 'release-full', 'macos-diagnostic'])
@pytest.mark.parametrize('scenario', [
    'valid', 'missing-swift', 'missing-swiftc', 'wrong-swift', 'wrong-swiftc',
    'prefix-version', 'swift-error', 'swiftc-error', 'sdk-error', 'sdk-drift', 'developer-drift',
    'wrong-arch', 'arch-error', 'missing-env', 'wrong-env', 'wrong-developer',
    'developer-error', 'empty-developer', 'empty-sdk', 'sdk-outside',
    'sdk-version', 'sdk-version-error', 'sdk-version-drift',
])
def test_actual_native_toolchain_selection(tmp_path, workflow_name, scenario):
    import yaml

    workflow = yaml.load((ROOT / f'.github/workflows/{workflow_name}.yml').read_text(), Loader=yaml.BaseLoader)
    steps = [step for job in workflow['jobs'].values() for step in job.get('steps', [])]
    selectors = [step for step in steps if step.get('name') == 'Select installed Swift 6.0.3']
    assert len(selectors) == 1, 'must replace Node20 setup-swift with guarded native selection'
    command = selectors[0]['run']
    assert 'DEVELOPER_DIR=' not in command and 'SDKROOT=' not in command
    assert 'xcode-select --switch' not in command and 'TOOLCHAINS=' not in command
    developer = tmp_path / 'Xcode_16.2.app/Contents/Developer'
    sdk = developer / 'Platforms/MacOSX.platform/Developer/SDKs/MacOSX15.2.sdk'
    toolchain = developer / 'Toolchains/XcodeDefault.xctoolchain/usr/bin'
    toolchain.mkdir(parents=True)
    for tool in ('swift', 'swiftc'):
        if scenario == f'missing-{tool}':
            continue
        version = '6.0.31' if scenario == 'prefix-version' else '6.0.2' if scenario == f'wrong-{tool}' else '6.0.3'
        executable = toolchain / tool
        executable.write_text(f'#!/bin/sh\nprintf "Apple Swift version {version} (swiftlang-test)\\n"\nexit {1 if scenario == tool+"-error" else 0}\n')
        executable.chmod(0o755)
    for tool, initial, changed in [('xcrun', str(sdk), '/synthetic/OtherSDK'), ('xcode-select', str(developer), '/synthetic/OtherDeveloper')]:
        if scenario == 'wrong-developer' and tool == 'xcode-select':
            initial = '/synthetic/OtherDeveloper'
        if scenario == 'sdk-outside' and tool == 'xcrun':
            initial = '/synthetic/OtherSDK'
        if scenario == ('empty-sdk' if tool == 'xcrun' else 'empty-developer'):
            initial = ''
        executable = tmp_path / tool
        counter = tmp_path / f'{tool}-called'
        drift = scenario == ('sdk-drift' if tool == 'xcrun' else 'developer-drift')
        executable.write_text(
            '#!/bin/sh\n' +
            (f'if [ "$3" = --show-sdk-version ]; then\n'
             f'  [ "{scenario}" != sdk-version-error ] || exit 1\n'
             f'  if [ -f "{tmp_path / "sdk-version-called"}" ]; then printf "%s\\n" "{"15.3" if scenario == "sdk-version-drift" else "15.2"}"; '
             f'else touch "{tmp_path / "sdk-version-called"}"; printf "%s\\n" "{"15.3" if scenario == "sdk-version" else "15.2"}"; fi\n'
             '  exit 0\nfi\n' if tool == 'xcrun' else '') +
            ('exit 1\n' if scenario == ('sdk-error' if tool == 'xcrun' else 'developer-error') else
             f'if [ -f "{counter}" ]; then printf "%s\\n" "{changed if drift else initial}"; else touch "{counter}"; printf "%s\\n" "{initial}"; fi\n')
        )
        executable.chmod(0o755)
    uname = tmp_path / 'uname'
    uname.write_text(f'#!/bin/sh\nprintf "%s\\n" "{"x86_64" if scenario == "wrong-arch" else "arm64"}"\nexit {1 if scenario == "arch-error" else 0}\n')
    uname.chmod(0o755)
    github_path = tmp_path / 'github-path'
    github_path.write_text('existing-entry\n')
    # Execute the actual YAML shell; only the three platform filesystem roots
    # are replaced, so no installed compiler or developer directory is changed.
    command = command.replace('/Applications/Xcode_16.2.app/Contents/Developer', str(developer))
    command = command.replace('/usr/bin/xcrun', str(tmp_path / 'xcrun')).replace('/usr/bin/xcode-select', str(tmp_path / 'xcode-select'))
    env = {**os.environ, 'GITHUB_PATH': str(github_path), 'DEVELOPER_DIR': str(developer), 'PATH': f'{tmp_path}:{os.environ["PATH"]}'}
    if scenario == 'missing-env':
        env.pop('DEVELOPER_DIR')
    elif scenario == 'wrong-env':
        env['DEVELOPER_DIR'] = '/synthetic/OtherDeveloper'
    result = subprocess.run(['bash', '-c', command], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10)
    if scenario == 'valid':
        assert result.returncode == 0, result.stderr
        assert github_path.read_text() == f'existing-entry\n{toolchain}\n'
        assert str(sdk) in result.stdout
    else:
        assert result.returncode != 0, result.stdout
        assert github_path.read_text() == 'existing-entry\n'


@pytest.mark.parametrize('workflow_name', ['governance-fast', 'release-full'])
@pytest.mark.parametrize('replacement', ['v4', 'v99', '0' * 40])
def test_workflow_validators_reject_unreviewed_action_pin(tmp_path, workflow_name, replacement):
    validator_path = ROOT / f'scripts/validate-{"governance" if workflow_name == "governance-fast" else "full-ci"}-workflow.py'
    spec = importlib.util.spec_from_file_location('action_pin_validator', validator_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = (ROOT / f'.github/workflows/{workflow_name}.yml').read_text()
    path = tmp_path / 'workflow.yml'
    path.write_text(source.replace('actions/checkout@' + ACTION_PINS['actions/checkout'], 'actions/checkout@' + replacement, 1))
    assert module.validate(path), 'a single unreviewed checkout must fail even when other checkouts match'
