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
LANE_RE = re.compile(
    r"^[ \t]*(?:[-*][ \t]*)?Lane[ \t]*:[ \t]*(?!$|___|<[^>]+>)([^\n]+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
EVIDENCE_COMMAND_RE = re.compile(r"`[^`\n]+`", re.MULTILINE)
EVIDENCE_STATUS_RE = re.compile(
    r"\b(?:pass(?:ed)?|ok|fail(?:ed)?|blocked|skipped|not[ \t]+run|не[ \t]+запускал|не[ \t]+запущен)\b",
    re.IGNORECASE,
)
TITLE_PREFIX_RE = re.compile(r"^((?:\[F\d{3,}\])+)(?:\s|$)")
TITLE_FEATURE_RE = re.compile(r"\[F(\d{3,})\]")
FEATURE_ID_RE = re.compile(r"\bF(\d{3,})\b")


def _sections(body: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    for match in SECTION_RE.finditer(body):
        sections.setdefault(match.group(1), []).append(match.group(2))
    return sections


def _has_content(content: str) -> bool:
    return any(line.strip() not in {"", "-", "*", "_"} for line in content.splitlines())


def _expected_feature_ids(value: str) -> set[str]:
    return {match.group(1) for match in re.finditer(r"\bF?(\d{3,})\b", value)}


def _declared_feature_ids(body: str, sections: dict[str, list[str]]) -> set[str]:
    # Restrict the declaration to the dedicated identity section so that a
    # reference to another feature in release notes cannot change ownership.
    identity = "\n".join(
        sections.get("## Feature identity", []) + sections.get("## Feature IDs", [])
    )
    declared = set(FEATURE_ID_RE.findall(identity))
    if declared:
        return declared
    marker = re.search(r"Feature ID:\s*`?F?(\d{3,})", body)
    return {marker.group(1)} if marker else set()


def validate(
    body: str,
    feature_id: str,
    expected_sha: str | None = None,
    title: str | None = None,
) -> list[str]:
    sections = _sections(body)
    errors: list[str] = []
    expected_feature_ids = _expected_feature_ids(feature_id)
    if not expected_feature_ids:
        errors.append("expected Feature ID is required")
    title_match = TITLE_PREFIX_RE.match((title or "").strip())
    if not title_match:
        errors.append("PR title must start with [F<feature-id>]")
    elif not expected_feature_ids.issubset(set(TITLE_FEATURE_RE.findall(title_match.group(1)))):
        errors.append(
            f"PR title Feature ID mismatch: expected {sorted('F' + value for value in expected_feature_ids)}, got {title_match.group(1)}"
        )
    for section in REQUIRED:
        if section == "## Feature identity" and "## Feature IDs" in sections:
            continue
        if section not in sections:
            errors.append(f"missing PR section: {section}")
        elif len(sections[section]) > 1:
            errors.append(f"duplicate PR section: {section}")
        elif not _has_content(sections[section][0]):
            errors.append(f"empty PR section: {section}")
    declared_feature_ids = _declared_feature_ids(body, sections)
    if not declared_feature_ids:
        errors.append("Feature ID is required in PR body")
    elif declared_feature_ids != expected_feature_ids:
        errors.append(
            "Feature ID mismatch: expected "
            + ", ".join(sorted("F" + value for value in expected_feature_ids))
            + ", got "
            + ", ".join(sorted("F" + value for value in declared_feature_ids))
        )
    umbrella_match = re.search(r"Umbrella issue:\s*`?#([1-9]\d*)\b", body)
    if not umbrella_match:
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
    issue_section = sections.get("## Issues", [])
    linked_issue_numbers = (
        [int(number) for number in ISSUE_LINK_RE.findall(issue_section[0])]
        if len(issue_section) == 1
        else []
    )
    if not linked_issue_numbers or not any(number > 0 for number in linked_issue_numbers):
        errors.append("at least one explicit issue linkage keyword is required")
    elif umbrella_match and int(umbrella_match.group(1)) not in linked_issue_numbers:
        errors.append("issue linkage must include the declared umbrella issue")
    risk_section = sections.get("## Risk / validation lane", [])
    if len(risk_section) == 1 and not LANE_RE.search(risk_section[0]):
        errors.append("concrete validation lane is required")
    evidence_section = sections.get("## Как проверено", [])
    if len(evidence_section) == 1 and (
        not EVIDENCE_COMMAND_RE.search(evidence_section[0])
        or not EVIDENCE_STATUS_RE.search(evidence_section[0])
    ):
        errors.append("concrete validation evidence is required")
    legacy_sections = sections.get("## Legacy Impact", [])
    legacy_section = legacy_sections[0] if len(legacy_sections) == 1 else ""
    classifications = CLASSIFICATION_RE.findall(legacy_section)
    if len(classifications) != 1:
        errors.append("Legacy Impact classification is required")
    return errors


def self_test() -> int:
    sha = "a" * 40
    title = "[F216] Перестроить процесс"
    body = """## Feature identity
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
""".format(sha=sha)
    assert validate(body, "216", expected_sha=sha, title=title) == []
    assert validate(body.replace("F216", "F215"), "216", title=title)
    assert validate(body.replace("F216", "F1024").replace("T042", "T1000"), "1024", title="[F1024] Перестроить процесс") == []
    assert validate(body, "216", expected_sha="b" * 40, title=title)
    assert validate(body.replace("Classification: `untouched`", "Classification: `remove` / `retain-with-exception` / `untouched`"), "216", title=title)
    assert validate(body.replace("## Issues\n- Refs #6090", "## Issues\n"), "216", title=title)
    assert validate(body.replace("Refs #6090", "Refs #___"), "216", title=title)
    assert validate(body.replace("Refs #6090", "Refs #999"), "216", title=title)
    assert validate(body, "216", title="Перестроить процесс")
    assert validate(body, "216", title="[F215] Перестроить процесс")
    print("pr-metadata self-test: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("body", type=Path, nargs="?")
    parser.add_argument("--feature-id")
    parser.add_argument("--expected-sha")
    parser.add_argument("--title")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.body is None:
        parser.error("body is required unless --self-test is used")
    if not args.feature_id:
        parser.error("--feature-id is required unless --self-test is used")
    if args.title is None:
        parser.error("--title is required unless --self-test is used")
    try:
        body = args.body.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"pr-metadata: ERROR: {exc}", file=sys.stderr)
        return 1
    errors = validate(body, args.feature_id, expected_sha=args.expected_sha, title=args.title)
    if errors:
        for error in errors:
            print(f"pr-metadata: ERROR: {error}", file=sys.stderr)
        return 1
    print("pr-metadata: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
