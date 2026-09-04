from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[2]


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(root / "infra/scripts/release-candidate.sh"), *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def _fixture(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "infra/scripts").mkdir(parents=True)
    (root / "infra/release").mkdir(parents=True)
    (root / "scripts").mkdir()
    shutil.copy2(ROOT / "infra/scripts/release-candidate.sh", root / "infra/scripts/release-candidate.sh")
    shutil.copy2(ROOT / "infra/release/train.schema.json", root / "infra/release/train.schema.json")
    shutil.copy2(ROOT / "infra/release/candidate.schema.json", root / "infra/release/candidate.schema.json")
    shutil.copy2(ROOT / "scripts/validate-release-train.py", root / "scripts/validate-release-train.py")
    shutil.copy2(ROOT / "scripts/validate-ci-evidence.py", root / "scripts/validate-ci-evidence.py")
    (root / ".gitignore").write_text(".dev/\n", encoding="utf-8")
    (root / "CHANGELOG.md").write_text("## [2026.09.01.1] - 2026-09-01\n\n- Feature 227\n- Feature 228\n\n## [2026.08.31.1] - 2026-08-31\n\n- Previous release\n", encoding="utf-8")
    for feature_id in ("227", "228"):
        feature_dir = root / "specs" / f"{feature_id}-fixture"
        feature_dir.mkdir(parents=True)
        (feature_dir / "spec.md").write_text(f"# Feature {feature_id}\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Governance Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
    (root / "post-merge-marker").write_text("source\n", encoding="utf-8")
    subprocess.run(["git", "add", "post-merge-marker"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "post-merge source"], cwd=root, check=True)
    subprocess.run(["git", "update-ref", "refs/remotes/origin/master", "HEAD"], cwd=root, check=True)
    return root


def _freeze_args(source: str, output: Path) -> list[str]:
    synthetic = ("d" * 40) if source == "c" * 40 else subprocess.check_output(["git", "rev-parse", f"{source}^"], cwd=output.parents[3], text=True).strip()
    return [
        "train-freeze",
        "--source-sha",
        source,
        "--base-sha",
        source,
        "--synthetic-merge-sha",
        synthetic,
        "--prs",
        "101,102,103",
        "--features",
        "227,228",
        "--merge-groups",
        "mg-1",
        "--pr-receipts",
        "pr-101,pr-102,pr-103",
        "--merge-group-receipts",
        "mg-1",
        "--operator",
        "release-operator",
        "--rollback-target",
        "v2026.08.31.1",
        "--output",
        str(output),
    ]


def test_train_freeze_and_validate_bind_post_merge_sha_and_provenance(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    output = root / ".dev/release/trains/train.json"

    frozen = _run(root, *_freeze_args(source, output))
    assert frozen.returncode == 0, frozen.stderr
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["source_sha"] == source
    assert manifest["base_sha"] == source
    assert manifest["synthetic_merge_sha"] != source
    assert manifest["included_prs"] == [101, 102, 103]
    assert manifest["feature_ids"] == ["227", "228"]
    assert manifest["decision"] == "pending"

    validated = _run(root, "train-validate", str(output), "--current")
    assert validated.returncode == 0, validated.stderr


def test_train_freeze_is_create_once_and_rejects_synthetic_source(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    output = root / ".dev/release/trains/train.json"
    first = _run(root, *_freeze_args(source, output))
    assert first.returncode == 0, first.stderr

    second = _run(root, *_freeze_args(source, output))
    assert second.returncode != 0
    assert "overwrite" in second.stderr or "immutable" in second.stderr

    invalid = _run(root, *_freeze_args("c" * 40, root / ".dev/release/trains/other.json"))
    assert invalid.returncode != 0
    assert "distinct" in invalid.stderr or "HEAD differs" in invalid.stderr


def test_train_freeze_rejects_source_not_on_origin_master(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    (root / "post-merge.txt").write_text("post merge\n", encoding="utf-8")
    subprocess.run(["git", "add", "post-merge.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "post merge"], cwd=root, check=True)
    current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    assert current != source

    result = _run(root, *_freeze_args(current, root / ".dev/release/trains/rejected.json"))
    assert result.returncode != 0
    assert "must match origin/master" in result.stderr


def test_train_validate_current_rejects_changelog_drift(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    output = root / ".dev/release/trains/train.json"
    assert _run(root, *_freeze_args(source, output)).returncode == 0
    (root / "CHANGELOG.md").write_text("changed\n", encoding="utf-8")

    result = _run(root, "train-validate", str(output), "--current")
    assert result.returncode != 0
    assert "changelog digest" in result.stderr


def test_candidate_freeze_rejects_partial_release_train_feature_set(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    train = root / ".dev/release/trains/train.json"
    assert _run(root, *_freeze_args(source, train)).returncode == 0

    result = _run(
        root,
        "freeze",
        "--sha", source,
        "--features", "227",
        "--operator", "release-operator",
        "--train", str(train),
        "--output", str(root / ".dev/release/candidates/partial.json"),
    )
    assert result.returncode != 0
    assert "exactly match the release train feature set" in result.stderr


def test_train_validate_current_rejects_ignored_train_metadata_drift(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    train = root / ".dev/release/trains/train.json"
    assert _run(root, *_freeze_args(source, train)).returncode == 0
    train.write_text(train.read_text(encoding="utf-8").replace('"operator": "release-operator"', '"operator": "tampered-operator"'), encoding="utf-8")

    result = _run(root, "train-validate", str(train), "--current")
    assert result.returncode != 0
    assert "metadata drift detected" in result.stderr


def test_train_attest_binds_authoritative_full_ci_to_candidate(tmp_path: Path, monkeypatch) -> None:
    root = _fixture(tmp_path)
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/example/project.git"],
        cwd=root,
        check=True,
    )
    train = root / ".dev/release/trains/train.json"
    assert _run(root, *_freeze_args(source, train)).returncode == 0
    candidate = root / ".dev/release/candidates/candidate.json"
    frozen = _run(
        root,
        "freeze",
        "--sha",
        source,
        "--features",
        "227,228",
        "--operator",
        "release-operator",
        "--train",
        str(train),
        "--output",
        str(candidate),
    )
    assert frozen.returncode == 0, frozen.stderr
    candidate_data = json.loads(candidate.read_text(encoding="utf-8"))
    assert candidate_data["train_id"].startswith("train-")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/bin/sh
[ "$1" = api ] || exit 1
case "$2" in
  repos/example/project/actions/runs/123)
    printf '%s\\n' '{"name":"release-full","event":"workflow_dispatch","status":"completed","conclusion":"success","head_sha":"'"$TEST_GITHUB_SHA"'","path":".github/workflows/release-full.yml"}'
    ;;
  'repos/example/project/actions/runs/123/artifacts?per_page=100')
    printf '%s\\n' '{"artifacts":[{"name":"graf-full-ci-'"$TEST_GITHUB_CANDIDATE"'","expired":false,"workflow_run":{"id":123}}]}'
    ;;
  *) exit 1 ;;
esac
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("TEST_GITHUB_SHA", source)
    monkeypatch.setenv("TEST_GITHUB_CANDIDATE", candidate_data["candidate_id"])
    evidence = root / ".dev/ci-evidence/evidence.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text(json.dumps({
        "run_id": "github-full-123",
        "lane": "full",
        "requested_sha": source,
        "observed_sha_start": source,
        "observed_sha_end": source,
        "status": "passed",
        "started_at": "2026-08-31T00:00:00Z",
        "finished_at": "2026-08-31T00:01:00Z",
        "commands": ["GitHub Actions release-full: Ubuntu server/infrastructure + macOS Swift"],
        "artifact_digests": {"full-log": "sha256:" + "a" * 64},
        "skipped_gates": [],
        "scope": "release train",
        "candidate_id": candidate_data["candidate_id"],
        "authoritative_full": True,
        "component_shas": {"server": source},
    }), encoding="utf-8")
    train_go = root / ".dev/release/trains/train-go.json"
    attested = _run(root, "train-attest", str(train), "--candidate", str(candidate), "--evidence", str(evidence), "--output", str(train_go))
    assert attested.returncode == 0, attested.stderr
    train_data = json.loads(train_go.read_text(encoding="utf-8"))
    assert train_data["decision"] == "go"
    assert train_data["authoritative_full_ci_receipt"]["target_sha"] == source
    assert train_data["authoritative_full_ci_receipt"]["lane"] == "full"
    assert _run(root, "train-validate", str(train_go), "--current").returncode == 0

    decision = root / "decision.json"
    canonical_evidence = root / ".dev" / "ci-evidence" / f"authoritative-{candidate_data['candidate_id']}.json"
    shutil.copy2(evidence, canonical_evidence)
    second = _run(root, "train-attest", str(train), "--candidate", str(candidate), "--evidence", str(evidence), "--output", str(root / "second-go.json"))
    assert second.returncode != 0
    assert "immutable attestation identity" in second.stderr

    decided = _run(
        root,
        "decide",
        str(candidate),
        "--train",
        str(train_go),
        "--evidence",
        str(canonical_evidence),
        "--calver",
        "2026.09.01.1",
        "--output",
        str(decision),
    )
    assert decided.returncode == 0, decided.stderr
    assert json.loads(decision.read_text(encoding="utf-8"))["status"] == "go"
