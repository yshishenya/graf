#!/usr/bin/env python3
from __future__ import annotations

from issue_canon_common import is_speckit_issue, list_open_issues, repo_root, repo_slug, validate_issue


def main() -> int:
    root = repo_root()
    slug = repo_slug(root)
    issues = [issue for issue in list_open_issues(slug) if is_speckit_issue(issue)]
    failures: list[tuple[int, list[str]]] = []
    for issue in issues:
        errors = validate_issue(issue)
        if errors:
            failures.append((issue["number"], errors))

    if not failures:
        print(f"github-issue-canon: OK ({len(issues)} Spec Kit issue(s) checked)")
        return 0

    print("github-issue-canon: validation failed")
    for number, errors in failures:
        print(f"  #{number}")
        for error in errors:
            print(f"    - {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
