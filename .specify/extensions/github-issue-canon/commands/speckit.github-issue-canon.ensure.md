---
name: "speckit.github-issue-canon.ensure"
description: "Install or refresh GitHub issue canon files and labels before task-to-issue sync."
compatibility: "Requires a Spec Kit project, git remote, gh CLI, and python3"
---

## Outline

1. Locate the repository root from the current working directory.
1. Find this installed extension directory at `.specify/extensions/github-issue-canon`.
1. Run:

```bash
python3 .specify/extensions/github-issue-canon/scripts/ensure_issue_canon.py
```

1. If the script exits non-zero, stop and report the error before continuing
   with `$speckit-taskstoissues`.
1. Do not patch globally installed Spec Kit skills. This extension is the
   upstream-clean enforcement layer.
