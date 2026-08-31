#!/usr/bin/env python3
"""Validate the explicit per-worktree Spec Kit context pointer."""
from __future__ import annotations

import argparse
import json
import subprocess
import re
import sys
from pathlib import Path


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    pointer = root / ".specify" / "feature.json"
    if not pointer.is_file():
        return ["missing .specify/feature.json; refusing mtime-based feature selection"]
    try:
        data = json.loads(pointer.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid .specify/feature.json: {exc}"]
    if not isinstance(data, dict):
        return ["invalid .specify/feature.json: top-level value must be an object"]
    required = (
        "feature_directory",
        "feature_id",
        "owner",
        "risk_lane",
        "owned_paths",
        "branch",
        "source_sha",
    )
    for key in required:
        if key not in data or data[key] in (None, "", []):
            errors.append(f"missing required context field: {key}")
    feature_dir = data.get("feature_directory")
    if not isinstance(feature_dir, str) or not re.fullmatch(r"specs/\d{3}-[a-z0-9][a-z0-9-]*", feature_dir):
        errors.append("feature_directory must match specs/NNN-slug")
    else:
        path = (root / feature_dir).resolve()
        if root.resolve() not in path.parents or not (path / "spec.md").is_file():
            errors.append("feature_directory must point to a spec.md inside this worktree")
        else:
            expected = path.name.split("-", 1)[0]
            if str(data.get("feature_id", "")) != expected:
                errors.append("feature_id must match the spec directory prefix")
    branch = data.get("branch")
    if not isinstance(branch, str) or not branch.strip():
        errors.append("branch must be a non-empty string")
    if isinstance(branch, str) and branch.strip():
        try:
            actual = subprocess.run(["git", "branch", "--show-current"], cwd=root, text=True, capture_output=True, check=True).stdout.strip()
            if not actual:
                errors.append("checkout must have an active branch")
            elif actual != branch:
                errors.append(f"branch mismatch: pointer={branch!r}, checkout={actual!r}")
        except (OSError, subprocess.CalledProcessError) as exc:
            errors.append(f"cannot read current branch: {exc}")
    source_sha = data.get("source_sha")
    if not isinstance(source_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        errors.append("source_sha must be a full 40-character git SHA")
    if isinstance(source_sha, str) and re.fullmatch(r"[0-9a-f]{40}", source_sha):
        try:
            actual_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True).stdout.strip()
            if actual_sha != source_sha:
                errors.append("source_sha does not match current HEAD; refresh context before changing files")
        except (OSError, subprocess.CalledProcessError) as exc:
            errors.append(f"cannot read current HEAD: {exc}")
    base_sha = data.get("base_sha")
    if base_sha is not None and (
        not isinstance(base_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", base_sha)
    ):
        errors.append("base_sha must be a full 40-character git SHA when provided")
    if not isinstance(data.get("owned_paths"), list) or not all(isinstance(item, str) and item for item in data["owned_paths"]):
        errors.append("owned_paths must be a non-empty list of relative paths")
    elif any(Path(item).is_absolute() or ".." in Path(item).parts for item in data["owned_paths"]):
        errors.append("owned_paths must stay relative to this worktree")
    else:
        owned = [Path(item) for item in data["owned_paths"]]
        changed: set[str] = set()
        commands = []
        diff_base = "origin/master"
        if isinstance(base_sha, str) and re.fullmatch(r"[0-9a-f]{40}", base_sha):
            if subprocess.run(["git", "rev-parse", "--verify", f"{base_sha}^{{commit}}"], cwd=root, capture_output=True).returncode == 0:
                diff_base = base_sha
            else:
                errors.append("base_sha does not resolve to a commit")
        if subprocess.run(["git", "rev-parse", "--verify", f"{diff_base}^{{commit}}"], cwd=root, capture_output=True).returncode == 0:
            commands.append(["git", "diff", "--name-only", f"{diff_base}...HEAD"])
        commands.extend([
            ["git", "diff", "--name-only", "HEAD"],
            ["git", "diff", "--cached", "--name-only"],
            ["git", "ls-files", "--others", "--exclude-standard"],
        ])
        for command in commands:
            try:
                result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=True)
            except (OSError, subprocess.CalledProcessError) as exc:
                errors.append(f"cannot determine changed paths for owned-path check: {exc}")
                break
            changed.update(line.strip() for line in result.stdout.splitlines() if line.strip())
        outside = []
        for value in sorted(changed):
            path = Path(value)
            if not any(path == prefix or prefix in path.parents for prefix in owned):
                outside.append(value)
        if outside:
            errors.append("changed paths outside active feature ownership: " + ", ".join(outside))
    agents = (root / "AGENTS.md").read_text(encoding="utf-8", errors="ignore") if (root / "AGENTS.md").is_file() else ""
    if re.search(r"at specs/\d{3}-[^\s`]+/plan\.md", agents):
        errors.append("root AGENTS.md contains a dynamic plan pointer")
    return errors


def self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="graf-context-") as tmp:
        root = Path(tmp)
        (root / ".specify").mkdir()
        (root / "specs/001-x").mkdir(parents=True)
        (root / "specs/001-x/spec.md").write_text("# x\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "checkout", "-qb", "test/001-x"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Context Test"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
        source_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()
        (root / ".specify/feature.json").write_text(
            json.dumps(
                {
                    "feature_directory": "specs/001-x",
                    "feature_id": "001",
                    "branch": "test/001-x",
                    "source_sha": "",
                    "owner": "test",
                    "risk_lane": "significant-feature",
                    "owned_paths": ["specs/001-x", ".specify"],
                }
            ),
            encoding="utf-8",
        )
        assert validate(root)
        (root / ".specify/feature.json").write_text(
            json.dumps(
                {
                    "feature_directory": "specs/001-x",
                    "feature_id": "001",
                    "branch": "test/001-x",
                    "source_sha": source_sha,
                    "owner": "test",
                    "risk_lane": "significant-feature",
                    "owned_paths": ["specs/001-x", ".specify"],
                }
            ),
            encoding="utf-8",
        )
        assert validate(root) == []
        (root / ".specify/feature.json").write_text("[]\n", encoding="utf-8")
        assert any("object" in error for error in validate(root))
        (root / ".specify/feature.json").write_text('{"feature_directory":"specs/002-y"}\n', encoding="utf-8")
        assert validate(root)
    print("agent-context self-test: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    errors = validate(args.root.resolve())
    if errors:
        for error in errors:
            print(f"agent-context: ERROR: {error}", file=sys.stderr)
        return 1
    print("agent-context: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
