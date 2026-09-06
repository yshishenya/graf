#!/usr/bin/env python3
"""Fail closed when a task-backed GitHub issue was closed without evidence."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path


TASK_RE = re.compile(r"\bT\d{3,}\b")
TASK_CHECKBOX_ROW_RE = re.compile(
    r"^[ \t]*-[ \t]+\[(?P<state>[xX ])\][ \t]+(?P<task>T\d{3,})\b"
)
TASK_MAPPING_ROW_RE = re.compile(
    r"^[ \t]*-[ \t]+(?P<task>T\d{3,})[ \t]+\(Issue\s+#\d+\b",
    re.IGNORECASE,
)
CLOSURE_SECTIONS = ("Что закрыто", "Почему это важно", "Как проверено", "Что не входит", "Связи")
SHA_RE = re.compile(r"\b[0-9a-f]{40}\b", re.IGNORECASE)
# The opening parenthesis is part of the canonical mapping syntax.  Requiring
# it prevents ``umbrella issue #N`` prose from becoming task ownership.
TASK_ISSUE_LINK_RE = re.compile(r"\(\s*Issue\s+#(\d+)\b", re.IGNORECASE)
TITLE_TASK_RE = re.compile(r"\b(T\d{3,})\s*:", re.IGNORECASE)
SPEC_TASK_FIELD_RE = re.compile(
    r"(?im)^[ \t]*(?:[-*][ \t]*)?Spec(?: Kit)? tasks?(?: IDs?)?[ \t]*:[ \t]*([^\n]+)$"
)
AUTHORITATIVE_PASS_RE = re.compile(
    r"\bgovernance-fast[ \t]*:[ \t]*pass\b[^\n]*"
    r"https://github\.com/(?P<repo>[^/\s]+/[^/\s]+)/actions/runs/(?P<run>[0-9]+)",
    re.IGNORECASE,
)
RELEASE_FULL_PASS_RE = re.compile(
    r"\brelease-full[ \t]*:[ \t]*pass\b[^\n]*"
    r"https://github\.com/(?P<repo>[^/\s]+/[^/\s]+)/actions/runs/(?P<run>[0-9]+)",
    re.IGNORECASE,
)
PR_SHA_RE = re.compile(r"(?im)^[ \t]*(?:[-*][ \t]*)?PR SHA[ \t]*:[ \t]*`?([0-9a-f]{40})`?")
CANDIDATE_SHA_RE = re.compile(
    r"(?im)^[ \t]*(?:[-*][ \t]*)?Candidate SHA[ \t]*:[ \t]*`?([0-9a-f]{40})`?"
)
PR_NUMBER_RE = re.compile(r"\bPR\s*:?\s*#(\d+)", re.IGNORECASE)
PR_ISSUE_LINK_RE = re.compile(
    r"(?i)\b(?:Fixes|Closes|Resolves|Refs|Part[ \t]+of)[ \t]+#(\d+)"
)


def _task_state(tasks_text: str) -> dict[str, tuple[bool, set[int]]]:
    """Read checked state and Issue links from each logical task row.

    Task metadata may wrap onto indented continuation lines.  Aggregate those
    lines before extracting the task-backed Issue link so wrapped rows remain
    traceable without treating unrelated prose as ownership.
    """
    states: dict[str, tuple[bool, set[int]]] = {}
    row: list[str] = []

    def row_match(line: str) -> re.Match[str] | None:
        return TASK_CHECKBOX_ROW_RE.search(line) or TASK_MAPPING_ROW_RE.search(line)

    def consume(logical_row: list[str]) -> None:
        if not logical_row:
            return
        match = row_match(logical_row[0])
        if not match:
            return
        task = match.group("task")
        checkbox = TASK_CHECKBOX_ROW_RE.search(logical_row[0])
        checked = bool(checkbox and checkbox.group("state").lower() == "x")
        # Only the canonical task-backed ``Issue #N`` link proves ownership.
        # An ``umbrella #N`` reference is intentionally informational and must
        # never make an umbrella issue look like the task's owner.
        issues = {
            int(value)
            for line in logical_row
            for value in TASK_ISSUE_LINK_RE.findall(line)
        }
        previous = states.get(task)
        states[task] = (
            checked or (previous[0] if previous else False),
            issues | (previous[1] if previous else set()),
        )

    for line in tasks_text.splitlines():
        if row_match(line):
            consume(row)
            row = [line]
        elif row and (not line.strip() or line.startswith((" ", "\t"))):
            row.append(line)
        else:
            consume(row)
            row = []
    consume(row)
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


def _empty_closure_sections(comment: str) -> list[str]:
    return [
        section
        for section in CLOSURE_SECTIONS
        if not re.search(rf"(?m)^{re.escape(section)}:[ \t]*\n[ \t]*-[ \t]*\S", comment)
    ]


def _owned_task_ids(issue: dict[str, object]) -> list[str]:
    """Read ownership only from the canonical title and task field.

    Ordinary references in context, dependencies, implementation notes, or
    links must not turn into task ownership claims.
    """
    title = str(issue.get("title", ""))
    body = str(issue.get("body", ""))
    owned = set(TITLE_TASK_RE.findall(title))
    for field in SPEC_TASK_FIELD_RE.findall(body):
        owned.update(TASK_RE.findall(field))
    return sorted(owned)


def validate(
    issue: dict[str, object],
    tasks_text: str,
    expected_sha: str | None = None,
    *,
    require_release_full: bool = False,
) -> list[str]:
    errors: list[str] = []
    task_states = _task_state(tasks_text)
    issue_tasks = _owned_task_ids(issue)
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
        empty_sections = _empty_closure_sections(comment)
        if empty_sections:
            errors.append("closure comment has empty sections: " + ", ".join(empty_sections))
        if not re.search(r"\bPR\s*:?\s*#\d+", comment, re.IGNORECASE):
            errors.append("closure comment must name a PR number")
        if not any(task in comment for task in issue_tasks):
            errors.append("closure comment must name the closed Spec Kit task")
        shas = SHA_RE.findall(comment)
        if not shas:
            errors.append("closure comment must name the exact tested SHA")
        elif expected_sha and expected_sha.lower() not in {sha.lower() for sha in shas}:
            errors.append("closure comment SHA does not match the expected exact SHA")
        if expected_sha is None:
            errors.append("expected exact SHA is required")
        elif not re.fullmatch(r"[0-9a-f]{40}", expected_sha, re.IGNORECASE):
            errors.append("expected exact SHA must be a full 40-character git SHA")
        if not AUTHORITATIVE_PASS_RE.search(comment):
            errors.append("closure comment must include governance-fast PASS with a run URL")
        if require_release_full and not RELEASE_FULL_PASS_RE.search(comment):
            errors.append("closure comment must include release-full PASS with a run URL")
        if require_release_full:
            candidate = CANDIDATE_SHA_RE.search(comment)
            if not candidate:
                errors.append("closure comment must name Candidate SHA explicitly")
            elif expected_sha and candidate.group(1).lower() != expected_sha.lower():
                errors.append("closure comment Candidate SHA does not match the expected exact SHA")
    return errors


def _closed_at(issue: dict[str, object]) -> dt.datetime | None:
    value = issue.get("closedAt")
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def validate_feature(
    issues: list[dict[str, object]],
    tasks_text: str,
    expected_sha: str,
    umbrella_issue: int,
    *,
    allow_open_umbrella: bool = False,
    require_release_full: bool = False,
) -> list[str]:
    errors: list[str] = []
    task_states = _task_state(tasks_text)
    task_rows = [
        match.group("task")
        for line in tasks_text.splitlines()
        if (match := TASK_CHECKBOX_ROW_RE.search(line))
    ]
    for task in sorted(set(task_rows)):
        if task_rows.count(task) > 1:
            errors.append(f"tasks.md contains duplicate checkbox rows for {task}")
    issues_by_number = {int(issue.get("number", 0) or 0): issue for issue in issues}
    umbrella = issues_by_number.get(umbrella_issue)
    if umbrella is None:
        errors.append(f"umbrella issue #{umbrella_issue} is missing from the feature inventory")

    owners: dict[str, list[dict[str, object]]] = {task: [] for task in task_states}
    child_issues: list[dict[str, object]] = []
    for issue in issues:
        number = int(issue.get("number", 0) or 0)
        if number == umbrella_issue:
            continue
        owned = _owned_task_ids(issue)
        if not owned:
            errors.append(f"issue #{number} has no canonical Spec Kit task ownership")
            continue
        child_issues.append(issue)
        for task in owned:
            if task not in task_states:
                errors.append(f"issue #{number} is orphaned: {task} is missing from tasks.md")
                continue
            owners[task].append(issue)

    for task, task_owners in sorted(owners.items()):
        if not task_owners:
            errors.append(f"{task} has no task-backed issue in the feature inventory")
            continue
        if len(task_owners) > 1:
            numbers = ", ".join(f"#{int(issue.get('number', 0) or 0)}" for issue in task_owners)
            errors.append(f"{task} has duplicate issue owners: {numbers}")
            continue
        issue = task_owners[0]
        number = int(issue.get("number", 0) or 0)
        if str(issue.get("state", "")).upper() != "CLOSED":
            errors.append(f"issue #{number} for {task} is still open")
        for error in validate(
            issue,
            tasks_text,
            expected_sha=expected_sha,
            require_release_full=require_release_full,
        ):
            errors.append(f"issue #{number}: {error}")

    if umbrella is not None:
        umbrella_state = str(umbrella.get("state", "")).upper()
        if umbrella_state != "CLOSED":
            if not allow_open_umbrella:
                errors.append(f"umbrella issue #{umbrella_issue} is still open")
        else:
            if "T000" in str(umbrella.get("title", "")).upper():
                errors.append(
                    f"umbrella issue #{umbrella_issue} cannot be closed with temporary T000 ownership"
                )
            comment = _closure_comment(umbrella)
            if not comment:
                errors.append(f"umbrella issue #{umbrella_issue} is missing the required Russian closure comment")
            else:
                empty_sections = _empty_closure_sections(comment)
                if empty_sections:
                    errors.append(
                        f"umbrella issue #{umbrella_issue} has empty closure sections: "
                        + ", ".join(empty_sections)
                    )
                if not re.search(r"\bPR\s*:?\s*#\d+", comment, re.IGNORECASE):
                    errors.append(f"umbrella issue #{umbrella_issue} closure comment must name a PR number")
                if expected_sha.lower() not in {sha.lower() for sha in SHA_RE.findall(comment)}:
                    errors.append(f"umbrella issue #{umbrella_issue} closure comment SHA does not match the expected exact SHA")
                if not AUTHORITATIVE_PASS_RE.search(comment):
                    errors.append(f"umbrella issue #{umbrella_issue} must include governance-fast PASS with a run URL")
                if require_release_full and not RELEASE_FULL_PASS_RE.search(comment):
                    errors.append(f"umbrella issue #{umbrella_issue} must include release-full PASS with a run URL")
                if require_release_full:
                    candidate = CANDIDATE_SHA_RE.search(comment)
                    if not candidate or candidate.group(1).lower() != expected_sha.lower():
                        errors.append(f"umbrella issue #{umbrella_issue} must name the expected Candidate SHA")
            umbrella_closed = _closed_at(umbrella)
            if umbrella_closed is None:
                errors.append(f"umbrella issue #{umbrella_issue} has no valid closedAt timestamp")
            else:
                for child in child_issues:
                    child_closed = _closed_at(child)
                    number = int(child.get("number", 0) or 0)
                    if str(child.get("state", "")).upper() == "CLOSED" and child_closed is None:
                        errors.append(f"closed child issue #{number} has no valid closedAt timestamp")
                    elif child_closed and child_closed >= umbrella_closed:
                        errors.append(f"umbrella issue #{umbrella_issue} was closed before child issue #{number}")
    return errors


def _github_run(repo: str, run_id: str) -> dict[str, object]:
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/actions/runs/{run_id}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"GitHub run {run_id} lookup failed")
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise ValueError(f"GitHub run {run_id} must be a JSON object")
    pull_requests = value.get("pull_requests", [])
    if not isinstance(pull_requests, list):
        raise ValueError(f"GitHub run {run_id} pull_requests must be an array")
    return {
        "databaseId": value.get("id"),
        "headSha": value.get("head_sha"),
        "conclusion": value.get("conclusion"),
        "workflowName": value.get("name"),
        "workflowPath": value.get("path"),
        "url": value.get("html_url"),
        "event": value.get("event"),
        "pullRequestNumbers": [
            item.get("number") for item in pull_requests if isinstance(item, dict)
        ],
    }


def _github_pr(repo: str, number: str) -> dict[str, object]:
    result = subprocess.run(
        [
            "gh", "pr", "view", number, "--repo", repo, "--json",
            "number,state,mergedAt,headRefOid,url,body",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"gh pr view {number} failed")
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise ValueError(f"GitHub PR {number} must be a JSON object")
    return value


def _github_commit_pull_requests(repo: str, sha: str) -> list[int]:
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/commits/{sha}/pulls"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"GitHub commit {sha} PR lookup failed")
    value = json.loads(result.stdout)
    if not isinstance(value, list):
        raise ValueError(f"GitHub commit {sha} pull requests must be an array")
    return [
        int(item["number"])
        for item in value
        if isinstance(item, dict) and isinstance(item.get("number"), int)
    ]


def verify_feature_runs(
    repo: str,
    issues: list[dict[str, object]],
    expected_sha: str,
    *,
    require_release_full: bool = False,
) -> list[str]:
    errors: list[str] = []
    cache: dict[str, dict[str, object]] = {}
    pr_cache: dict[str, dict[str, object]] = {}
    commit_pr_cache: dict[str, list[int]] = {}

    def verify(
        *, issue_number: int, match: re.Match[str], workflow: str, expected_run_sha: str,
        expected_event: str, expected_path: str, expected_pr_number: int | None = None,
    ) -> None:
        if match.group("repo").lower() != repo.lower():
            errors.append(f"issue #{issue_number} {workflow} URL points to another repository")
            return
        run_id = match.group("run")
        try:
            if run_id not in cache:
                cache[run_id] = _github_run(repo, run_id)
            run = cache[run_id]
        except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"issue #{issue_number} cannot verify GitHub run {run_id}: {exc}")
            return
        if run.get("conclusion") != "success":
            errors.append(f"issue #{issue_number} GitHub run {run_id} did not conclude success")
        if run.get("workflowName") != workflow:
            errors.append(f"issue #{issue_number} GitHub run {run_id} is not workflow {workflow}")
        if run.get("event") != expected_event:
            errors.append(f"issue #{issue_number} GitHub run {run_id} is not a {expected_event} run")
        if run.get("workflowPath") != expected_path:
            errors.append(f"issue #{issue_number} GitHub run {run_id} is not workflow path {expected_path}")
        run_pr_numbers = run.get("pullRequestNumbers", [])
        if expected_pr_number is not None:
            if not run_pr_numbers:
                try:
                    if expected_run_sha not in commit_pr_cache:
                        commit_pr_cache[expected_run_sha] = _github_commit_pull_requests(repo, expected_run_sha)
                    run_pr_numbers = commit_pr_cache[expected_run_sha]
                except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
                    errors.append(f"issue #{issue_number} cannot verify PRs for GitHub run {run_id}: {exc}")
            if run_pr_numbers != [expected_pr_number]:
                errors.append(
                    f"issue #{issue_number} GitHub run {run_id} is not uniquely bound to PR #{expected_pr_number}"
                )
        if str(run.get("headSha", "")).lower() != expected_run_sha.lower():
            errors.append(f"issue #{issue_number} GitHub run {run_id} SHA does not match {workflow} evidence")

    for issue in issues:
        number = int(issue.get("number", 0) or 0)
        comment = _closure_comment(issue)
        if not comment:
            continue
        governance = AUTHORITATIVE_PASS_RE.search(comment)
        pr_sha = PR_SHA_RE.search(comment)
        pr_number = PR_NUMBER_RE.search(comment)
        if pr_number and pr_sha:
            number_text = pr_number.group(1)
            try:
                if number_text not in pr_cache:
                    pr_cache[number_text] = _github_pr(repo, number_text)
                pr = pr_cache[number_text]
            except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"issue #{number} cannot verify GitHub PR {number_text}: {exc}")
            else:
                if not pr.get("mergedAt") or pr.get("state") != "MERGED":
                    errors.append(f"issue #{number} PR #{number_text} is not merged")
                if str(pr.get("headRefOid", "")).lower() != pr_sha.group(1).lower():
                    errors.append(f"issue #{number} PR #{number_text} head SHA does not match closure evidence")
                linked_issues = {int(value) for value in PR_ISSUE_LINK_RE.findall(str(pr.get("body", "")))}
                if number not in linked_issues:
                    errors.append(f"issue #{number} is not explicitly linked from PR #{number_text}")
        if governance and pr_sha:
            verify(
                issue_number=number,
                match=governance,
                workflow="governance-fast",
                expected_run_sha=pr_sha.group(1),
                expected_event="pull_request",
                expected_path=".github/workflows/governance-fast.yml",
                expected_pr_number=int(pr_number.group(1)) if pr_number else None,
            )
        elif governance:
            errors.append(f"issue #{number} must name PR SHA for governance-fast verification")
        if require_release_full:
            release = RELEASE_FULL_PASS_RE.search(comment)
            candidate = CANDIDATE_SHA_RE.search(comment)
            if release and candidate:
                verify(
                    issue_number=number,
                    match=release,
                    workflow="release-full",
                    expected_run_sha=expected_sha,
                    expected_event="workflow_dispatch",
                    expected_path=".github/workflows/release-full.yml",
                )
            elif release:
                errors.append(f"issue #{number} must name Candidate SHA for release-full verification")
    return errors


def _github_feature_issues(repo: str, feature: str) -> list[dict[str, object]]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("--repo must be owner/name")
    if not re.fullmatch(r"\d+", feature):
        raise ValueError("--feature must be numeric")
    limit = 1000
    result = subprocess.run(
        [
            "gh", "issue", "list", "--repo", repo, "--state", "all",
            "--label", f"feature:{feature}", "--limit", str(limit), "--json",
            "number,title,state,body,comments,closedAt",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "gh issue list failed")
    value = json.loads(result.stdout)
    if not isinstance(value, list) or not all(isinstance(issue, dict) for issue in value):
        raise ValueError("GitHub feature issue inventory must be a JSON array")
    if len(value) >= limit:
        raise ValueError(f"GitHub feature issue inventory reached the fail-closed limit of {limit}")
    return value


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
- release-full: PASS (https://github.com/yshishenya/graf/actions/runs/2)

Что не входит:
- Legacy cleanup.

Связи:
- Spec task: T001
- PR: #6373
"""}]
    assert validate(issue, "- [X] T001 Проверить (Issue #6373)\n", expected_sha="a" * 40) == []
    assert validate(issue, "- [ ] T001 Проверить (Issue #6373)\n", expected_sha="a" * 40)
    assert validate(
        issue,
        "- [X] T001 Проверить\n"
        "  (Issue #6373; umbrella #6385).\n",
        expected_sha="a" * 40,
    ) == []
    assert validate(
        issue,
        "- [X] T001 Проверить\n"
        "\n"
        "## GitHub issue links\n"
        "- T001 (Issue #6373)\n",
        expected_sha="a" * 40,
    ) == []
    assert validate(
        issue,
        "- [X] T001 Проверить\n"
        "  (umbrella #6373).\n",
        expected_sha="a" * 40,
    )
    assert validate(
        issue,
        "- [X] T001 Проверить\n"
        "  (umbrella issue #6373).\n",
        expected_sha="a" * 40,
    )
    assert validate(issue, "- [X] T001 Проверить (Issue #999)\n", expected_sha="a" * 40)
    assert validate(issue, "- [X] T001 Проверить (Issue #6373)\n", expected_sha="b" * 40)
    child = dict(issue, state="CLOSED", closedAt="2026-09-04T10:00:00Z")
    umbrella = {
        "number": 6415,
        "title": "[236][P1][governance] T017: Завершить фичу",
        "state": "CLOSED",
        "closedAt": "2026-09-04T10:01:00Z",
        "comments": issue["comments"],
    }
    assert validate_feature(
        [child, umbrella],
        "- [X] T001 Проверить (Issue #6373)\n",
        "a" * 40,
        6415,
    ) == []
    print("issue-closeout self-test: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue-json", type=Path)
    parser.add_argument("--tasks", type=Path)
    parser.add_argument("--expected-sha")
    parser.add_argument("--repo")
    parser.add_argument("--feature")
    parser.add_argument("--umbrella", type=int)
    parser.add_argument("--allow-open-umbrella", action="store_true")
    parser.add_argument("--require-release-full", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.tasks:
        parser.error("--tasks is required unless --self-test is used")
    if not args.expected_sha:
        parser.error("--expected-sha is required unless --self-test is used")
    try:
        tasks = args.tasks.read_text(encoding="utf-8")
        if args.repo or args.feature or args.umbrella:
            if not args.repo or not args.feature or not args.umbrella:
                parser.error("--repo, --feature and --umbrella are required together")
            issues = _github_feature_issues(args.repo, args.feature)
            errors = validate_feature(
                issues,
                tasks,
                args.expected_sha,
                args.umbrella,
                allow_open_umbrella=args.allow_open_umbrella,
                require_release_full=args.require_release_full,
            )
            errors.extend(
                verify_feature_runs(
                    args.repo,
                    issues,
                    args.expected_sha,
                    require_release_full=args.require_release_full,
                )
            )
        else:
            if not args.issue_json:
                parser.error("--issue-json is required outside feature mode")
            issue = json.loads(args.issue_json.read_text(encoding="utf-8"))
            errors = validate(
                issue,
                tasks,
                expected_sha=args.expected_sha,
                require_release_full=args.require_release_full,
            )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"issue-closeout: ERROR: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"issue-closeout: ERROR: {error}", file=sys.stderr)
        return 1
    if args.repo:
        print("feature-closeout: OK (live GitHub PR/run verification)")
    else:
        print("issue-closeout: OK (structural pre-close check only; final authority requires live feature mode)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
