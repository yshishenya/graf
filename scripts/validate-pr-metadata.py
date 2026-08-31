#!/usr/bin/env python3
"""Validate the machine-checkable PR contract for a feature branch."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED = ("## Feature identity", "## Как проверено", "## Risk / validation lane", "## Issues", "## Legacy Impact", "## Перед merge")


def validate(body: str, feature_id: str) -> list[str]:
    errors = [f"missing PR section: {section}" for section in REQUIRED if section not in body]
    marker = re.search(r"Feature ID:\s*`?F?(\d{3,})", body)
    if not marker:
        errors.append("Feature ID is required in PR body")
    elif marker.group(1) != feature_id:
        errors.append(f"Feature ID mismatch: expected {feature_id}, got {marker.group(1)}")
    if not re.search(r"Umbrella issue:\s*`?#\d+", body):
        errors.append("umbrella issue is required")
    sha_match = re.search(r"Exact source SHA[^\n]*\b([0-9a-fA-F]{40})\b", body)
    if not sha_match:
        errors.append("exact source SHA evidence is required")
    if not re.search(r"Spec task IDs:\s*`?T\d{3,}", body):
        errors.append("at least one Spec task ID is required")
    if not any(token in body for token in ("Refs #", "Part of #", "Fixes #", "Closes #", "Resolves #")):
        errors.append("at least one explicit issue linkage keyword is required")
    if not re.search(r"Classification:\s*`(?:remove|retain-with-exception|untouched)`", body):
        errors.append("Legacy Impact classification is required")
    return errors


def self_test() -> int:
    body = "\n".join(REQUIRED) + "\nFeature ID: `F216`\nUmbrella issue: `#6090`\nSpec task IDs: `T042`\nExact source SHA: " + "a" * 40 + "\nRefs #6090\nClassification: `untouched`\n"
    assert validate(body, "216") == []
    assert validate(body.replace("F216", "F215"), "216")
    assert validate(body.replace("F216", "F1024").replace("T042", "T1000"), "1024") == []
    print("pr-metadata self-test: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("body", type=Path, nargs="?")
    parser.add_argument("--feature-id")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.body is None:
        parser.error("body is required unless --self-test is used")
    if not args.feature_id:
        parser.error("--feature-id is required unless --self-test is used")
    try:
        body = args.body.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"pr-metadata: ERROR: {exc}", file=sys.stderr)
        return 1
    errors = validate(body, args.feature_id)
    if errors:
        for error in errors:
            print(f"pr-metadata: ERROR: {error}", file=sys.stderr)
        return 1
    print("pr-metadata: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
