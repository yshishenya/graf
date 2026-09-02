from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_harness_validators():
    path = ROOT / "harness" / "src" / "dev_harness" / "validators.py"
    spec = importlib.util.spec_from_file_location("harness_validators", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_legacy_validator_rejects_invalid_expiry_without_traceback(tmp_path: Path) -> None:
    validator = load_script("validate-legacy-impact")
    path = tmp_path / "spec.md"
    path.write_text(
        """## Legacy Impact

Classification: `retain-with-exception`
owner: platform
expiry: 2099-02-30
removal trigger: migration complete
retirement task: T217
risk: bounded compatibility risk
validation: focused migration test
reason: required for existing clients
""",
        encoding="utf-8",
    )

    errors = validator.validate(path)

    assert any("invalid ISO expiry date" in error for error in errors)


def test_legacy_validator_requires_exact_classification_and_exception_labels(tmp_path: Path) -> None:
    validator = load_script("validate-legacy-impact")
    path = tmp_path / "spec.md"
    path.write_text(
        """## Legacy Impact

Classification: `retain-with-exception`
ownerish: platform
expiry: 2099-12-31
removal trigger: migration complete
retirement task: T217
risk: bounded compatibility risk
validation: focused migration test
reason: required for existing clients

## Other section
Classification: `untouched`
""",
        encoding="utf-8",
    )

    errors = validator.validate(path)

    assert any("needs owner" in error for error in errors)
    assert not any("exactly one Classification" in error for error in errors)


def test_legacy_exception_requires_risk_validation_and_reason(tmp_path: Path) -> None:
    validator = load_script("validate-legacy-impact")
    path = tmp_path / "spec.md"
    path.write_text(
        """## Legacy Impact

Classification: `retain-with-exception`
owner: platform
expiry: 2099-12-31
removal trigger: migration complete
retirement task: T217
""",
        encoding="utf-8",
    )

    errors = validator.validate(path)

    assert any("needs risk" in error for error in errors)
    assert any("needs validation" in error for error in errors)
    assert any("needs reason" in error for error in errors)


def test_changelog_fragment_rejects_credential_assignment(tmp_path: Path) -> None:
    validator = load_script("validate-changelog-fragments")
    fragment = tmp_path / "changes" / "unreleased" / "F216.yaml"
    fragment.parent.mkdir(parents=True)
    fragment.write_text(
        '''schema_version: 1
feature_id: 216
category: Changed
summary: "Добавлена проверка"
issue: 6090
tasks: T001
compatibility: "нет"
release_notes: "Пароль: password = RealCredential123456"
''',
        encoding="utf-8",
    )

    errors = validator.validate(tmp_path)

    assert any("forbidden secret/private/path token" in error for error in errors)


def test_agent_context_requires_object_branch_and_full_source_sha(tmp_path: Path) -> None:
    validator = load_script("validate-agent-context")
    pointer = tmp_path / ".specify" / "feature.json"
    pointer.parent.mkdir()
    pointer.write_text("[]\n", encoding="utf-8")
    assert any("object" in error for error in validator.validate(tmp_path))

    pointer.write_text(
        json.dumps(
            {
                "feature_directory": "specs/001-example",
                "feature_id": "001",
                "owner": "test",
                "risk_lane": "tiny-low-risk",
                "owned_paths": ["specs/001-example"],
                "branch": "test/001-example",
                "source_sha": "abc1234",
            }
        ),
        encoding="utf-8",
    )
    assert any("full 40-character" in error for error in validator.validate(tmp_path))


def test_agent_context_accepts_four_digit_feature_directory(tmp_path: Path) -> None:
    validator = load_script("validate-agent-context")
    feature = tmp_path / "specs/1000-example"
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text("# Example\n", encoding="utf-8")
    pointer = tmp_path / ".specify" / "feature.json"
    pointer.parent.mkdir()
    pointer.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "feature_directory": "specs/1000-example",
                "feature_id": "1000",
                "owner": "test",
                "risk_lane": "tiny-low-risk",
                "owned_paths": ["specs/1000-example"],
                "branch": "test/1000-example",
                "source_sha": "a" * 40,
            }
        ),
        encoding="utf-8",
    )

    errors = validator.validate(tmp_path)

    assert not any("feature_directory must match" in error for error in errors)


def test_context_updater_target_stays_outside_root_instruction_chain() -> None:
    config = (ROOT / ".specify/extensions/agent-context/agent-context-config.yml").read_text(
        encoding="utf-8"
    )
    assert 'context_file: ".dev/active-feature-context.md"' in config


def test_issue_canon_pr_template_keeps_feature_and_legacy_gates() -> None:
    template = (ROOT / ".specify/extensions/github-issue-canon/templates/github/pull_request_template.md").read_text(
        encoding="utf-8"
    )
    for marker in ("## Feature identity", "Exact source SHA", "## Legacy Impact"):
        assert marker in template


def test_changelog_required_fields_must_be_top_level(tmp_path: Path) -> None:
    validator = load_script("validate-changelog-fragments")
    directory = tmp_path / "changes" / "unreleased"
    directory.mkdir(parents=True)
    (directory / "F217.yaml").write_text(
        """metadata:
  feature_id: 217
  schema_version: 1
  category: Changed
  summary: "Русское описание"
  issue: 1
  tasks: [T001]
  compatibility: "нет"
  release_notes: "Русские заметки"
""",
        encoding="utf-8",
    )

    errors = validator.validate(tmp_path)

    assert any("missing schema_version" in error for error in errors)
    assert any("feature_id" in error for error in errors)


def test_changelog_empty_required_field_is_rejected(tmp_path: Path) -> None:
    validator = load_script("validate-changelog-fragments")
    directory = tmp_path / "changes" / "unreleased"
    directory.mkdir(parents=True)
    (directory / "F217.yaml").write_text(
        """schema_version: 1
feature_id:
category: Changed
summary: "Русское описание"
issue: 1
tasks: [T001]
compatibility: "нет"
release_notes: "Русские заметки"
""",
        encoding="utf-8",
    )

    errors = validator.validate(tmp_path)

    assert any("missing feature_id" in error for error in errors)


def test_changelog_malformed_feature_id_is_rejected(tmp_path: Path) -> None:
    validator = load_script("validate-changelog-fragments")
    directory = tmp_path / "changes" / "unreleased"
    directory.mkdir(parents=True)
    (directory / "F217.yaml").write_text(
        """schema_version: 1
feature_id: F217
category: Changed
summary: "Русское описание"
issue: 1
tasks: [T001]
compatibility: "нет"
release_notes: "Русские заметки"
""",
        encoding="utf-8",
    )

    errors = validator.validate(tmp_path)

    assert any("feature_id must be numeric" in error for error in errors)


def test_feature_claim_rejects_corrupt_shared_state_and_keeps_offline_draft_explicit() -> None:
    validator = load_script("claim-feature")
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Governance Test"], cwd=root, check=True)
        (root / ".keep").write_text("fixture\n", encoding="utf-8")
        subprocess.run(["git", "add", ".keep"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
        common = Path(
            subprocess.check_output(["git", "rev-parse", "--git-common-dir"], cwd=root, text=True).strip()
        )
        if not common.is_absolute():
            common = root / common
        claims = common / "feature-claims.json"
        claims.write_text('{"216": []}\n', encoding="utf-8")
        try:
            validator._local_claim_records(root)
        except SystemExit as exc:
            assert "shared claim state is corrupt" in str(exc)
        else:
            raise AssertionError("corrupt shared claim state was accepted")

        claims.unlink()
        draft = validator.claim(root, 216, issue_number=None, branch="draft/216-x", slug="x", offline=True)
        assert draft["status"] == "draft"


def test_feature_claim_can_upgrade_matching_offline_draft(monkeypatch) -> None:
    validator = load_script("claim-feature")
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Governance Test"], cwd=root, check=True)
        (root / ".keep").write_text("fixture\n", encoding="utf-8")
        subprocess.run(["git", "add", ".keep"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
        validator.claim(root, 216, issue_number=None, branch="draft/216-x", slug="x", offline=True)
        monkeypatch.setattr(validator, "_github_ids", lambda *args, **kwargs: set())
        monkeypatch.setattr(validator, "_github_umbrella", lambda *args, **kwargs: None)
        upgraded = validator.claim(root, 216, issue_number=6090, branch="draft/216-x", slug="x", offline=False)
        assert upgraded["status"] == "reserved"
        assert upgraded["issue_number"] == 6090
        assert validator._local_claim_records(root)["216"]["issue_number"] == 6090


def test_feature_claim_requires_feature_label_on_github_umbrella(monkeypatch, tmp_path: Path) -> None:
    validator = load_script("claim-feature")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args[0],
            0,
            stdout=json.dumps(
                {
                    "number": 6090,
                    "state": "OPEN",
                    "title": "[216] Development governance harness",
                    "body": "Feature ID: 216",
                    "labels": [],
                }
            ),
        )

    monkeypatch.setattr(validator.subprocess, "run", fake_run)
    try:
        validator._github_umbrella(tmp_path, 6090, 216)
    except SystemExit as exc:
        assert "must have label feature:216" in str(exc)
    else:
        raise AssertionError("umbrella without feature label was accepted")


def test_feature_claim_validates_umbrella_before_collision(monkeypatch, tmp_path: Path) -> None:
    validator = load_script("claim-feature")
    calls: list[tuple[int, int]] = []

    monkeypatch.setattr(validator, "_assert_clean_worktree", lambda _root: None)
    monkeypatch.setattr(validator, "_github_umbrella", lambda _root, issue, feature: calls.append((issue, feature)))
    monkeypatch.setattr(validator, "_git_refs", lambda _root, strict=False: [])
    monkeypatch.setattr(validator, "_local_claim_records", lambda _root: {})
    monkeypatch.setattr(validator, "_github_ids", lambda *args, **kwargs: {216})

    try:
        validator.claim(
            tmp_path,
            216,
            issue_number=6090,
            branch="codex/216-x",
            slug="x",
            offline=False,
        )
    except SystemExit as exc:
        assert "collision" in str(exc)
    else:
        raise AssertionError("feature collision was accepted")
    assert calls == [(6090, 216)]


def test_feature_claim_github_timeout_fails_closed(monkeypatch, tmp_path: Path) -> None:
    validator = load_script("claim-feature")

    def fake_run(command, **kwargs):
        if command[:2] == ["git", "config"]:
            return subprocess.CompletedProcess(command, 0, stdout="https://github.com/example/project.git\n")
        raise subprocess.TimeoutExpired(command, kwargs.get("timeout", 0))

    monkeypatch.setattr(validator.subprocess, "run", fake_run)
    try:
        validator._github_ids(tmp_path, strict=True)
    except SystemExit as exc:
        assert "cannot inspect complete GitHub issue/PR history" in str(exc)
        assert "use --offline" in str(exc)
    else:
        raise AssertionError("GitHub timeout was not treated as a fail-closed error")


def test_feature_claim_bounded_lookup_uses_exact_candidate_search(monkeypatch, tmp_path: Path) -> None:
    validator = load_script("claim-feature")
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[:2] == ["git", "config"]:
            return subprocess.CompletedProcess(command, 0, stdout="https://github.com/example/project.git\n")
        assert "--paginate" not in command
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"total_count": 0, "items": []}))

    monkeypatch.setattr(validator.subprocess, "run", fake_run)
    assert validator._github_ids(tmp_path, strict=True, candidates={234}) == set()
    assert len(calls) == 4  # remote lookup plus three exact marker queries
    assert all("234" in " ".join(call) for call in calls[1:])


def test_feature_claim_excludes_requested_branch_from_collision_refs() -> None:
    validator = load_script("claim-feature")
    refs = [
        "codex/234-process-closeout",
        "origin/codex/234-process-closeout",
        "origin/codex/235-other",
    ]
    assert validator._refs_without_requested_branch(refs, "codex/234-process-closeout") == [
        "origin/codex/235-other"
    ]


def test_package_safety_allows_documentation_examples_but_rejects_credentials(tmp_path: Path) -> None:
    validator = load_harness_validators()
    (tmp_path / "README.md").write_text("Use `secret:` and `password =` as field names.\n", encoding="utf-8")
    assert validator.package_safety(tmp_path) == []

    (tmp_path / "config.py").write_text('password = "not-a-real-but-long-value"\n', encoding="utf-8")
    errors = validator.package_safety(tmp_path)
    assert any("forbidden secret/private content" in error for error in errors)

    (tmp_path / "env.py").write_text(
        "GITHUB_" + "TOKEN=abcdefghijk\n"
        "SIGNED_" + "URL=https://example.invalid/path\n",
        encoding="utf-8",
    )
    errors = validator.package_safety(tmp_path)
    assert any("forbidden secret/private content" in error for error in errors)


def _context_pointer(feature_directory: str = "specs/001-example", feature_id: str = "001") -> dict[str, object]:
    return {
        "schema_version": 1,
        "feature_directory": feature_directory,
        "feature_id": feature_id,
        "branch": "test/001-example",
        "source_sha": "a" * 40,
        "owner": "test",
        "risk_lane": "tiny-low-risk",
        "owned_paths": [feature_directory],
    }


def test_portable_context_requires_existing_spec_and_matching_feature_id(tmp_path: Path) -> None:
    validator = load_harness_validators()
    pointer = tmp_path / ".specify" / "feature.json"
    pointer.parent.mkdir()
    pointer.write_text(json.dumps(_context_pointer()), encoding="utf-8")

    errors = validator.context(tmp_path)

    assert any("feature_directory and spec.md must exist" in error for error in errors)

    feature_dir = tmp_path / "specs/001-example"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Example\n", encoding="utf-8")
    pointer.write_text(json.dumps(_context_pointer(feature_id="002")), encoding="utf-8")

    errors = validator.context(tmp_path)

    assert any("feature_id must match feature_directory" in error for error in errors)


def test_portable_context_binds_branch_and_head_when_checkout_is_git(tmp_path: Path) -> None:
    validator = load_harness_validators()
    (tmp_path / "specs/001-example").mkdir(parents=True)
    (tmp_path / "specs/001-example/spec.md").write_text("# Example\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Governance Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=tmp_path, check=True)
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=tmp_path, text=True).strip()
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    pointer = tmp_path / ".specify" / "feature.json"
    pointer.parent.mkdir()
    pointer.write_text(json.dumps(_context_pointer() | {"branch": branch, "source_sha": sha}), encoding="utf-8")

    assert validator.context(tmp_path) == []
    pointer.write_text(json.dumps(_context_pointer() | {"branch": "wrong/branch", "source_sha": sha}), encoding="utf-8")
    assert any("branch mismatch" in error for error in validator.context(tmp_path))
    pointer.write_text(json.dumps(_context_pointer() | {"branch": branch, "source_sha": "b" * 40}), encoding="utf-8")
    assert any("does not match current HEAD" in error for error in validator.context(tmp_path))


def test_portable_context_rejects_feature_directory_symlink_escape(tmp_path: Path) -> None:
    validator = load_harness_validators()
    outside = tmp_path.parent / "outside-feature"
    outside.mkdir()
    (outside / "spec.md").write_text("# Outside\n", encoding="utf-8")
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs/001-example").symlink_to(outside, target_is_directory=True)
    pointer = tmp_path / ".specify" / "feature.json"
    pointer.parent.mkdir()
    pointer.write_text(json.dumps(_context_pointer()), encoding="utf-8")

    errors = validator.context(tmp_path)

    assert any("remain inside the consumer root" in error for error in errors)


def test_ci_evidence_binds_source_revision_digest_to_observed_sha() -> None:
    validator = load_harness_validators()
    sha = "a" * 40
    evidence = {
        "run_id": "run-1",
        "lane": "fast",
        "requested_sha": sha,
        "observed_sha_start": sha,
        "observed_sha_end": sha,
        "status": "passed",
        "started_at": "2026-08-31T00:00:00Z",
        "finished_at": "2026-08-31T00:01:00Z",
        "commands": ["ci --fast"],
        "skipped_gates": [],
        "scope": "test",
        "artifact_digests": {
            "source-revision": "sha256:" + ("b" * 64),
        },
    }

    errors = validator.ci_evidence(evidence)

    assert any("source-revision artifact digest" in error for error in errors)


def test_ci_evidence_requires_ordered_rfc3339_utc_timestamps() -> None:
    validator = load_harness_validators()
    sha = "a" * 40
    evidence = {
        "run_id": "run-1",
        "lane": "fast",
        "requested_sha": sha,
        "observed_sha_start": sha,
        "observed_sha_end": sha,
        "status": "passed",
        "started_at": "2026-08-31T00:01:00Z",
        "finished_at": "2026-08-31T00:00:00Z",
        "commands": ["ci --fast"],
        "skipped_gates": [],
        "scope": "test",
        "artifact_digests": {"log": "sha256:" + "b" * 64},
    }

    errors = validator.ci_evidence(evidence)

    assert any("finished_at must be after started_at" in error for error in errors)
    errors = validator.ci_evidence(dict(evidence, started_at="2026-08-31T00:00:00+05:00"))
    assert any("RFC3339 UTC" in error for error in errors)


def test_ci_evidence_rejects_path_like_artifact_identity() -> None:
    validator = load_harness_validators()
    sha = "a" * 40
    evidence = {
        "run_id": "run-1",
        "lane": "fast",
        "requested_sha": sha,
        "observed_sha_start": sha,
        "observed_sha_end": sha,
        "status": "passed",
        "started_at": "2026-08-31T00:00:00Z",
        "finished_at": "2026-08-31T00:01:00Z",
        "commands": ["ci --fast"],
        "skipped_gates": [],
        "scope": "test",
        "artifact_digests": {"../release": "sha256:" + ("b" * 64)},
    }

    errors = validator.ci_evidence(evidence)

    assert any("invalid artifact name" in error for error in errors)


def _valid_pr_body(sha: str = "a" * 40) -> str:
    return f"""## Feature identity
- Feature ID: `F216`
- Umbrella issue: `#6090`
- Spec task IDs: `T042`

## Как проверено
- `pytest -q tests/governance`: passed
- Exact source SHA: {sha}

## Risk / validation lane
- Lane: significant-feature

## Issues
- Refs #6090

## Legacy Impact
- Classification: `untouched`

## Перед merge
- evidence recorded
"""


def test_pr_metadata_requires_concrete_issue_link_and_expected_sha() -> None:
    validator = load_script("validate-pr-metadata")
    sha = "a" * 40
    body = _valid_pr_body(sha)

    assert validator.validate(body, "216", expected_sha=sha) == []
    assert validator.validate(body.replace("Classification: `untouched`", "Classification: `untouched`."), "216", expected_sha=sha) == []
    assert any("mismatch" in error for error in validator.validate(body, "216", expected_sha="b" * 40))
    assert any("issue linkage" in error for error in validator.validate(body.replace("Refs #6090", "Refs #___"), "216"))
    wrong_umbrella_link = body.replace("Refs #6090", "Refs #999")
    assert any("declared umbrella issue" in error for error in validator.validate(wrong_umbrella_link, "216"))


def test_pr_metadata_rejects_placeholder_legacy_and_empty_sections() -> None:
    validator = load_script("validate-pr-metadata")
    body = _valid_pr_body()

    placeholder = body.replace(
        "Classification: `untouched`",
        "Classification: `remove` / `retain-with-exception` / `untouched`",
    )
    assert any("Legacy Impact classification" in error for error in validator.validate(placeholder, "216"))

    empty = body.replace("## Issues\n- Refs #6090", "## Issues\n")
    assert any("empty PR section: ## Issues" in error for error in validator.validate(empty, "216"))

    for heading, content in (
        ("## Как проверено", "- `pytest -q tests/governance`: passed\n- Exact source SHA: " + "a" * 40),
        ("## Risk / validation lane", "- Lane: significant-feature"),
    ):
        empty_section = body.replace(f"{heading}\n{content}", f"{heading}\n")
        assert any(f"empty PR section: {heading}" in error for error in validator.validate(empty_section, "216"))


def test_pr_metadata_requires_machine_readable_lane_and_evidence() -> None:
    validator = load_script("validate-pr-metadata")
    body = _valid_pr_body()
    weak = body.replace("- `pytest -q tests/governance`: passed", "- validation will happen later")
    weak = weak.replace("- Lane: significant-feature", "- lane TBD")
    errors = validator.validate(weak, "216")
    assert any("validation lane" in error for error in errors)
    assert any("validation evidence" in error for error in errors)


def test_process_changed_legacy_scan_collects_committed_and_worktree_specs(tmp_path: Path) -> None:
    checker = load_script("check-development-process")
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Process Test"], cwd=tmp_path, check=True)
    committed = tmp_path / "specs" / "001-old" / "spec.md"
    committed.parent.mkdir(parents=True)
    committed.write_text("# Old\n", encoding="utf-8")
    subprocess.run(["git", "add", "specs"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=tmp_path, check=True)
    subprocess.run(["git", "branch", "-M", "master"], cwd=tmp_path, check=True)
    subprocess.run(["git", "update-ref", "refs/remotes/origin/master", "HEAD"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-qb", "codex/002-process"], cwd=tmp_path, check=True)
    committed.write_text("# Old changed\n", encoding="utf-8")
    untracked = tmp_path / "specs" / "002-new" / "spec.md"
    untracked.parent.mkdir(parents=True)
    untracked.write_text("# New\n", encoding="utf-8")

    assert checker.changed_feature_specs(tmp_path) == [
        Path("specs/001-old/spec.md"),
        Path("specs/002-new/spec.md"),
    ]
