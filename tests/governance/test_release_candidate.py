from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "infra/scripts/release-candidate.sh"
EVIDENCE_VALIDATOR = ROOT / "scripts/validate-ci-evidence.py"
SCHEMA = ROOT / "infra/release/candidate.schema.json"


def run(script: Path, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(script), *args], cwd=cwd, text=True, capture_output=True)


def fixture(tmp_path: Path) -> Path:
    shutil.copytree(ROOT / "infra/scripts", tmp_path / "infra/scripts")
    (tmp_path / "infra/release").mkdir(parents=True)
    shutil.copy2(SCHEMA, tmp_path / "infra/release/candidate.schema.json")
    (tmp_path / "scripts").mkdir()
    shutil.copy2(EVIDENCE_VALIDATOR, tmp_path / "scripts/validate-ci-evidence.py")
    (tmp_path / "CHANGELOG.md").write_text("## [Unreleased]\n\n- Feature 216\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Governance Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=tmp_path, check=True)
    return tmp_path


def test_freeze_validate_and_decide_are_immutable(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    script = root / "infra/scripts/release-candidate.sh"
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    frozen = root / "candidate.json"

    result = run(script, "freeze", "--sha", sha, "--features", "216,217", "--operator", "release", "--output", str(frozen), cwd=root)
    assert result.returncode == 0, result.stderr
    candidate = json.loads(frozen.read_text(encoding="utf-8"))
    assert candidate["status"] == "frozen"
    assert run(script, "validate", str(frozen), "--current", cwd=root).returncode == 0

    evidence = {
        "run_id": "full-216",
        "lane": "full",
        "requested_sha": sha,
        "observed_sha_start": sha,
        "observed_sha_end": sha,
        "status": "passed",
        "started_at": "2026-08-31T00:00:00Z",
        "finished_at": "2026-08-31T00:01:00Z",
        "commands": ["infra/scripts/ci-local.sh --full"],
        "artifact_digests": {"full-log": "sha256:" + "a" * 64},
        "skipped_gates": [],
        "scope": "release candidate",
        "candidate_id": candidate["candidate_id"],
        "authoritative_full": True,
        "component_shas": {"server": sha},
    }
    evidence_path = root / "evidence.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    decision = root / "decision.json"
    result = run(script, "decide", str(frozen), "--evidence", str(evidence_path), "--calver", "2026.08.31.1", "--output", str(decision), cwd=root)
    assert result.returncode == 0, result.stderr
    assert json.loads(decision.read_text(encoding="utf-8"))["status"] == "go"
    assert json.loads(frozen.read_text(encoding="utf-8"))["status"] == "frozen"

    again = run(script, "decide", str(frozen), "--evidence", str(evidence_path), "--calver", "2026.08.31.1", "--output", str(decision), cwd=root)
    assert again.returncode != 0
    assert "immutable" in again.stderr


def test_validate_current_rejects_changed_changelog(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    script = root / "infra/scripts/release-candidate.sh"
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    frozen = root / "candidate.json"
    result = run(script, "freeze", "--sha", sha, "--feature-id", "216", "--operator", "release", "--output", str(frozen), cwd=root)
    assert result.returncode == 0, result.stderr
    (root / "CHANGELOG.md").write_text("changed\n", encoding="utf-8")
    result = run(script, "validate", str(frozen), "--current", cwd=root)
    assert result.returncode != 0
    assert "changelog digest" in result.stderr


def test_decide_rejects_impossible_calver_date(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    script = root / "infra/scripts/release-candidate.sh"
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    frozen = root / "candidate.json"
    result = run(
        script,
        "freeze",
        "--sha",
        sha,
        "--feature-id",
        "216",
        "--operator",
        "release",
        "--output",
        str(frozen),
        cwd=root,
    )
    assert result.returncode == 0, result.stderr
    evidence = {
        "run_id": "full-216",
        "lane": "full",
        "requested_sha": sha,
        "observed_sha_start": sha,
        "observed_sha_end": sha,
        "status": "passed",
        "started_at": "2026-08-31T00:00:00Z",
        "finished_at": "2026-08-31T00:01:00Z",
        "commands": ["infra/scripts/ci-local.sh --full"],
        "artifact_digests": {"full-log": "sha256:" + "a" * 64},
        "skipped_gates": [],
        "scope": "release candidate",
        "candidate_id": json.loads(frozen.read_text(encoding="utf-8"))["candidate_id"],
        "authoritative_full": True,
        "component_shas": {"server": sha},
    }
    evidence_path = root / "evidence.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    result = run(
        script,
        "decide",
        str(frozen),
        "--evidence",
        str(evidence_path),
        "--calver",
        "2026.02.31.1",
        cwd=root,
    )
    assert result.returncode != 0
    assert "date does not exist" in result.stderr
