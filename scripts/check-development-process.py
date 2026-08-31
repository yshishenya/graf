#!/usr/bin/env python3
"""Run the bounded project-process checks without loading product history."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run(root: Path, args: list[str]) -> int:
    result = subprocess.run([sys.executable, *args], cwd=root, text=True)
    return result.returncode


def changed_feature_specs(root: Path) -> list[Path] | None:
    """Return feature specs changed against the integration base and locally."""
    commands = [
        ["git", "diff", "--name-only", "origin/master...HEAD", "--", "specs"],
        ["git", "diff", "--name-only", "--", "specs"],
        ["git", "diff", "--cached", "--name-only", "--", "specs"],
        ["git", "ls-files", "--others", "--exclude-standard", "--", "specs"],
    ]
    paths: set[Path] = set()
    for command in commands:
        result = subprocess.run(command, cwd=root, text=True, capture_output=True)
        if result.returncode != 0:
            # A clean release checkout may not have origin/master.  Repository
            # derived checks must still run; use the local parent as a bounded
            # fallback instead of silently skipping Legacy Impact validation.
            if command == commands[0]:
                fallback = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD^", "HEAD", "--", "specs"],
                    cwd=root,
                    text=True,
                    capture_output=True,
                )
                if fallback.returncode == 0:
                    for value in fallback.stdout.splitlines():
                        relative = Path(value.strip())
                        if len(relative.parts) >= 3 and relative.parts[0] == "specs" and relative.name == "spec.md":
                            paths.add(relative)
                    continue
            print(
                "development-process: cannot determine changed paths for Legacy Impact scan: "
                + result.stderr.strip(),
                file=sys.stderr,
            )
            return None
        for value in result.stdout.splitlines():
            relative = Path(value.strip())
            if len(relative.parts) >= 3 and relative.parts[0] == "specs" and relative.name == "spec.md":
                paths.add(relative)
    return sorted(paths)


def scan_changed_legacy(root: Path) -> bool:
    paths = changed_feature_specs(root)
    if paths is None:
        return False
    for relative in paths:
        spec = (root / relative).resolve()
        if root not in spec.parents or not spec.is_file():
            print(f"development-process: changed spec is unavailable: {relative}", file=sys.stderr)
            return False
        if run(root, ["scripts/validate-legacy-impact.py", "--feature", str(spec)]) != 0:
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--pr-body", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    checks = [
        ["scripts/claim-feature.py", "--self-test"],
        ["scripts/validate-agent-context.py", "--self-test"],
        ["scripts/validate-ci-evidence.py", "dummy.json", "--self-test"],
        ["scripts/validate-pr-metadata.py", "dummy.md", "--feature-id", "216", "--self-test"],
    ]
    if args.self_test:
        for command in checks:
            if run(root, command) != 0:
                return 1
        print("development-process self-test: OK")
        return 0
    pointer = root / ".specify" / "feature.json"
    # The pointer is required for feature implementation, but it is not the
    # source of truth for repository-wide checks.  Release/PR checkouts may
    # intentionally omit it; still validate fragments and changed specs.
    if pointer.is_file() and run(root, ["scripts/validate-agent-context.py"]) != 0:
        return 1
    if not pointer.is_file():
        print("development-process: active feature context not present; repository checks continue", file=sys.stderr)
    if run(root, ["scripts/validate-changelog-fragments.py"]) != 0:
        return 1
    data: dict[str, object] = {}
    feature: Path | None = None
    if pointer.is_file():
        try:
            data = json.loads(pointer.read_text(encoding="utf-8"))
            feature = Path(str(data["feature_directory"]))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(f"development-process: invalid feature pointer: {exc}", file=sys.stderr)
            return 1
        spec = root / feature / "spec.md"
        if not spec.is_file():
            print(f"development-process: missing {spec}", file=sys.stderr)
            return 1
        if run(root, ["scripts/validate-legacy-impact.py", "--feature", str(spec)]) != 0:
            return 1
    if not scan_changed_legacy(root):
        return 1
    if args.pr_body:
        if not pointer.is_file():
            print("development-process: PR metadata validation requires active feature pointer", file=sys.stderr)
            return 1
        feature_id = str(data.get("feature_id", ""))
        source_sha = str(data.get("source_sha", ""))
        if run(root, ["scripts/validate-pr-metadata.py", str(args.pr_body), "--feature-id", feature_id, "--expected-sha", source_sha]) != 0:
            return 1
    print(f"development-process: OK feature={feature or 'repository-only'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
