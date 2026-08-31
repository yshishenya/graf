#!/usr/bin/env python3
"""Validate the machine-checkable PR contract for a feature branch."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED = (
    "## Feature identity",
    "## Как проверено",
    "## Risk / validation lane",
    "## Issues",
    "## Legacy Impact",
    "## Перед merge",
)
SECTION_RE = re.compile(r"^(## [^\n]+)[ \t]*\n([\s\S]*?)(?=^## |\Z)", re.MULTILINE)
SHA_RE = re.compile(
    r"^[ \t]*(?:[-*][ \t]*)?Exact source SHA\b[^\n:]*:[ \t]*`?([0-9a-fA-F]{40})`?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
CLASSIFICATION_RE = re.compile(
    r"^[ \t]*(?:[-*][ \t]*)?(?:\*\*)?Classification(?:\*\*)?"
    r"[ \t]*:[ \t]*[`']?(remove|retain-with-exception|untouched)[`']?"
    r"[ \t]*[.,;:!?]?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
ISSUE_LINK_RE = re.compile(
    r"\b(?:Refs|Part of|Fixes|Closes|Resolves)[ \t]+#(\d+)\b",
    re.IGNORECASE,
)


def _sections(body: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    for match in SECTION_RE.finditer(body):
        sections.setdefault(match.group(1), []).append(match.group(2))
    return sections


def _has_content(content: str) -> bool:
    return any(line.strip() not in {"", "-", "*", "_"} for line in content.splitlines())


def validate(body: str, feature_id: str, expected_sha: str | None = None) -> list[str]:
    sections = _sections(body)
    errors: list[str] = []
    for section in REQUIRED:
        if section not in sections:
            errors.append(f"missing PR section: {section}")
        elif len(sections[section]) > 1:
            errors.append(f"duplicate PR section: {section}")
        elif not _has_content(sections[section][0]):
            errors.append(f"empty PR section: {section}")
    marker = re.search(r"Feature ID:\s*`?F?(\d{3,})", body)
    if not marker:
        errors.append("Feature ID is required in PR body")
    elif marker.group(1) != feature_id:
        errors.append(f"Feature ID mismatch: expected {feature_id}, got {marker.group(1)}")
    if not re.search(r"Umbrella issue:\s*`?#\d+", body):
        errors.append("umbrella issue is required")
    sha_matches = SHA_RE.findall(body)
    if not sha_matches:
        errors.append("exact source SHA evidence is required")
    elif len(sha_matches) != 1:
        errors.append("exact source SHA evidence must contain exactly one SHA")
    elif expected_sha is not None:
        if not re.fullmatch(r"[0-9a-fA-F]{40}", expected_sha):
            errors.append("expected source SHA must be a full 40-character git SHA")
        elif sha_matches[0].lower() != expected_sha.lower():
            errors.append(
                f"exact source SHA mismatch: expected {expected_sha}, got {sha_matches[0]}"
            )
    if not re.search(r"Spec task IDs:\s*`?T\d{3,}", body):
        errors.append("at least one Spec task ID is required")
    if not ISSUE_LINK_RE.search(body):
        errors.append("at least one explicit issue linkage keyword is required")
    legacy_sections = sections.get("## Legacy Impact", [])
    legacy_section = legacy_sections[0] if len(legacy_sections) == 1 else ""
    classifications = CLASSIFICATION_RE.findall(legacy_section)
    if len(classifications) != 1:
        errors.append("Legacy Impact classification is required")
    return errors


def self_test() -> int:
    sha = "a" * 40
    body = """## Feature identity
- Feature ID: `F216`
- Umbrella issue: `#6090`
- Spec task IDs: `T042`

## Как проверено
- focused test passed
- Exact source SHA: {sha}

## Risk / validation lane
- Lane: significant-feature

## Issues
- Refs #6090

## Legacy Impact
- Classification: `untouched`

## Перед merge
- evidence recorded
""".format(sha=sha)
    assert validate(body, "216", expected_sha=sha) == []
    assert validate(body.replace("F216", "F215"), "216")
    assert validate(body.replace("F216", "F1024").replace("T042", "T1000"), "1024") == []
    assert validate(body, "216", expected_sha="b" * 40)
    assert validate(body.replace("Classification: `untouched`", "Classification: `remove` / `retain-with-exception` / `untouched`"), "216")
    assert validate(body.replace("## Issues\n- Refs #6090", "## Issues\n"), "216")
    assert validate(body.replace("Refs #6090", "Refs #___"), "216")
    print("pr-metadata self-test: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("body", type=Path, nargs="?")
    parser.add_argument("--feature-id")
    parser.add_argument("--expected-sha")
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
    errors = validate(body, args.feature_id, expected_sha=args.expected_sha)
    if errors:
        for error in errors:
            print(f"pr-metadata: ERROR: {error}", file=sys.stderr)
        return 1
    print("pr-metadata: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
