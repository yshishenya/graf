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
    if not pointer.is_file():
        print("development-process: no active feature pointer; preflight required before feature work", file=sys.stderr)
        return 1
    if run(root, ["scripts/validate-agent-context.py"]) != 0:
        return 1
    if run(root, ["scripts/validate-changelog-fragments.py"]) != 0:
        return 1
    try:
        data = json.loads(pointer.read_text(encoding="utf-8"))
        feature = Path(data["feature_directory"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"development-process: invalid feature pointer: {exc}", file=sys.stderr)
        return 1
    spec = root / feature / "spec.md"
    if not spec.is_file():
        print(f"development-process: missing {spec}", file=sys.stderr)
        return 1
    if run(root, ["scripts/validate-legacy-impact.py", "--feature", str(spec)]) != 0:
        return 1
    if args.pr_body:
        feature_id = str(data.get("feature_id", ""))
        if run(root, ["scripts/validate-pr-metadata.py", str(args.pr_body), "--feature-id", feature_id]) != 0:
            return 1
    print(f"development-process: OK feature={feature}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
