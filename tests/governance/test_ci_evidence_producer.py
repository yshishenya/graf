from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
PRODUCER = ROOT / "scripts/emit-ci-evidence.py"
VALIDATOR = ROOT / "scripts/validate-ci-evidence.py"


def test_producer_writes_atomic_valid_metadata_only_evidence(tmp_path: Path) -> None:
    sha = "a" * 40
    output = tmp_path / ".dev" / "evidence.json"
    command = [
        sys.executable,
        str(PRODUCER),
        "--output",
        str(output),
        "--run-id",
        "ci-full-test",
        "--lane",
        "full",
        "--requested-sha",
        sha,
        "--observed-sha-start",
        sha,
        "--observed-sha-end",
        sha,
        "--status",
        "passed",
        "--started-at",
        "2026-08-31T00:00:00Z",
        "--finished-at",
        "2026-08-31T00:01:00Z",
        "--scope",
        "release candidate",
        "--candidate-id",
        "rc-20260831T000000Z-aaaaaaaaaaaa",
        "--authoritative-full",
        "--component-sha",
        f"repository={sha}",
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    evidence = json.loads(output.read_text(encoding="utf-8"))
    assert evidence["status"] == "passed"
    assert "raw" not in json.dumps(evidence).lower()
    validated = subprocess.run(
        [sys.executable, str(VALIDATOR), str(output)], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert validated.returncode == 0, validated.stderr


def test_producer_requires_name_value_for_component_sha(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(PRODUCER),
            "--output",
            str(tmp_path / "evidence.json"),
            "--run-id",
            "ci-test",
            "--lane",
            "fast",
            "--requested-sha",
            "a" * 40,
            "--observed-sha-start",
            "a" * 40,
            "--observed-sha-end",
            "a" * 40,
            "--status",
            "passed",
            "--started-at",
            "2026-08-31T00:00:00Z",
            "--finished-at",
            "2026-08-31T00:01:00Z",
            "--scope",
            "test",
            "--component-sha",
            "invalid",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "expected NAME=SHA" in result.stderr


def test_producer_hashes_supplied_artifact_bytes(tmp_path: Path) -> None:
    sha = "a" * 40
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"release-bytes")
    output = tmp_path / "evidence.json"
    result = subprocess.run(
        [
            sys.executable, str(PRODUCER), "--output", str(output),
            "--run-id", "ci-fast-artifact", "--lane", "fast",
            "--requested-sha", sha, "--observed-sha-start", sha,
            "--observed-sha-end", sha, "--status", "passed",
            "--started-at", "2026-08-31T00:00:00Z", "--finished-at", "2026-08-31T00:01:00Z",
            "--scope", "test", "--artifact", f"bundle={artifact}",
        ], cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    evidence = json.loads(output.read_text(encoding="utf-8"))
    import hashlib
    expected = "sha256:" + hashlib.sha256(b"release-bytes").hexdigest()
    assert evidence["artifact_digests"]["bundle"] == expected


def test_producer_refuses_overwrite_unless_explicitly_non_authoritative(tmp_path: Path) -> None:
    sha = "a" * 40
    output = tmp_path / "evidence.json"
    command = [
        sys.executable, str(PRODUCER), "--output", str(output),
        "--run-id", "ci-fast-repeat", "--lane", "fast",
        "--requested-sha", sha, "--observed-sha-start", sha,
        "--observed-sha-end", sha, "--status", "passed",
        "--started-at", "2026-08-31T00:00:00Z", "--finished-at", "2026-08-31T00:01:00Z",
        "--scope", "diagnostic",
    ]
    first = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    assert first.returncode == 0, first.stderr
    second = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    assert second.returncode != 0
    assert "refusing to overwrite" in second.stderr

    diagnostic = subprocess.run(command + ["--non-authoritative"], cwd=ROOT, text=True, capture_output=True, check=False)
    assert diagnostic.returncode == 0, diagnostic.stderr
    assert json.loads(output.read_text(encoding="utf-8"))["authoritative"] is False
