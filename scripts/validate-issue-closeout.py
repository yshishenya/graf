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


def _task_state(tasks_text: str) -> dict[str, bool]:
    states: dict[str, bool] = {}
    for line in tasks_text.splitlines():
        match = TASK_RE.search(line)
        if match and re.search(r"- \[[xX]\]", line):
            states[match.group(0)] = True
        elif match:
            states.setdefault(match.group(0), False)
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


def validate(issue: dict[str, object], tasks_text: str) -> list[str]:
    errors: list[str] = []
    task_states = _task_state(tasks_text)
    issue_text = f"{issue.get('title', '')}\n{issue.get('body', '')}"
    issue_tasks = sorted(set(TASK_RE.findall(issue_text)))
    if not issue_tasks:
        return ["issue has no Spec Kit task IDs"]
    missing = [task for task in issue_tasks if not task_states.get(task, False)]
    if missing:
        errors.append("unchecked or missing tasks: " + ", ".join(missing))
    if str(issue.get("state", "")).upper() == "CLOSED":
        comment = _closure_comment(issue)
        if not comment:
            errors.append("closed issue is missing the required Russian closure comment")
        elif not re.search(r"\bPR\s*:?\s*#\d+", comment, re.IGNORECASE):
            errors.append("closure comment must name a PR number")
        elif not any(task in comment for task in issue_tasks):
            errors.append("closure comment must name the closed Spec Kit task")
    return errors


def self_test() -> int:
    issue = {
        "state": "CLOSED",
        "title": "[234][P1][governance] T001: Проверить closeout",
        "body": "Spec tasks: T001",
        "comments": [{"body": ""}],
    }
    assert validate(issue, "- [ ] T001 Проверить\n")
    issue["comments"] = [{"body": """Готово.

Что закрыто:
- T001

Почему это важно:
- Проверяем правду.

Как проверено:
- pytest PASS

Что не входит:
- Legacy cleanup.

Связи:
- Spec task: T001
- PR: #6373
"""}]
    assert validate(issue, "- [X] T001 Проверить\n") == []
    print("issue-closeout self-test: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue-json", type=Path)
    parser.add_argument("--tasks", type=Path)
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
    errors = validate(issue, tasks)
    if errors:
        for error in errors:
            print(f"issue-closeout: ERROR: {error}", file=sys.stderr)
        return 1
    print("issue-closeout: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
