#!/usr/bin/env python3
"""Fail closed when a task-backed GitHub issue was closed without evidence."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


TASK_RE = re.compile(r"\bT\d{3,}\b")
CLOSURE_SECTIONS = ("Что закрыто", "Почему это важно", "Как проверено", "Что не входит", "Связи")
SHA_RE = re.compile(r"\b[0-9a-f]{40}\b", re.IGNORECASE)
ISSUE_LINK_RE = re.compile(r"\(Issue\s+#(\d+)\)", re.IGNORECASE)


def _task_state(tasks_text: str) -> dict[str, tuple[bool, set[int]]]:
    states: dict[str, tuple[bool, set[int]]] = {}
    for line in tasks_text.splitlines():
        match = TASK_RE.search(line)
        if not match:
            continue
        checked = bool(re.search(r"- \[[xX]\]", line))
        issues = {int(value) for value in ISSUE_LINK_RE.findall(line)}
        previous = states.get(match.group(0))
        states[match.group(0)] = (checked or (previous[0] if previous else False), issues | (previous[1] if previous else set()))
    return states


def _closure_comment(issue: dict[str, object]) -> str:
    comments = issue.get("comments", [])
    if not isinstance(comments, list):
        return ""
    bodies = [str(item.get("body", "")) for item in comments if isinstance(item, dict)]
    for body in reversed(bodies):
        if all(section in body for section in CLOSURE_SECTIONS):
            return body
    return ""


def validate(issue: dict[str, object], tasks_text: str, expected_sha: str | None = None) -> list[str]:
    errors: list[str] = []
    task_states = _task_state(tasks_text)
    issue_text = f"{issue.get('title', '')}\n{issue.get('body', '')}"
    issue_tasks = sorted(set(TASK_RE.findall(issue_text)))
    if not issue_tasks:
        return ["issue has no Spec Kit task IDs"]
    issue_number = int(issue.get("number", 0) or 0)
    missing = [task for task in issue_tasks if not task_states.get(task, (False, set()))[0]]
    if missing:
        errors.append("unchecked or missing tasks: " + ", ".join(missing))
    for task in issue_tasks:
        linked_issues = task_states.get(task, (False, set()))[1]
        if issue_number and issue_number not in linked_issues:
            errors.append(f"{task} is not linked to issue #{issue_number} in tasks.md")
    comment = _closure_comment(issue)
    if not comment:
        errors.append("issue is missing the required Russian closure comment before close")
    else:
        if not re.search(r"\bPR\s*:?\s*#\d+", comment, re.IGNORECASE):
            errors.append("closure comment must name a PR number")
        if not any(task in comment for task in issue_tasks):
            errors.append("closure comment must name the closed Spec Kit task")
        shas = SHA_RE.findall(comment)
        if not shas:
            errors.append("closure comment must name the exact tested SHA")
        elif expected_sha and expected_sha.lower() not in {sha.lower() for sha in shas}:
            errors.append("closure comment SHA does not match the expected exact SHA")
        if not re.search(r"governance-fast|exact[- ]SHA|actions/runs/\d+", comment, re.IGNORECASE):
            errors.append("closure comment must name authoritative check evidence")
    return errors


def self_test() -> int:
    issue = {
        "state": "OPEN",
        "number": 6373,
        "title": "[234][P1][governance] T001: Проверить closeout",
        "body": "Spec tasks: T001",
        "comments": [{"body": ""}],
    }
    assert validate(issue, "- [ ] T001 Проверить (Issue #6373)\n")
    issue["comments"] = [{"body": """Готово.

Что закрыто:
- T001

Почему это важно:
- Проверяем правду.

Как проверено:
- pytest PASS
- Exact SHA: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
- governance-fast: PASS (https://github.com/yshishenya/graf/actions/runs/1)

Что не входит:
- Legacy cleanup.

Связи:
- Spec task: T001
- PR: #6373
"""}]
    assert validate(issue, "- [X] T001 Проверить (Issue #6373)\n", expected_sha="a" * 40) == []
    assert validate(issue, "- [X] T001 Проверить (Issue #999)\n", expected_sha="a" * 40)
    assert validate(issue, "- [X] T001 Проверить (Issue #6373)\n", expected_sha="b" * 40)
    print("issue-closeout self-test: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue-json", type=Path)
    parser.add_argument("--tasks", type=Path)
    parser.add_argument("--expected-sha")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.issue_json or not args.tasks:
        parser.error("--issue-json and --tasks are required unless --self-test is used")
    try:
        issue = json.loads(args.issue_json.read_text(encoding="utf-8"))
        tasks = args.tasks.read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        print(f"issue-closeout: ERROR: {exc}", file=sys.stderr)
        return 1
    errors = validate(issue, tasks, expected_sha=args.expected_sha)
    if errors:
        for error in errors:
            print(f"issue-closeout: ERROR: {error}", file=sys.stderr)
        return 1
    print("issue-closeout: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
