---
name: "speckit.github-issue-canon.validate"
description: "Validate GitHub issues against the project issue canon after task-to-issue sync."
compatibility: "Requires a Spec Kit project, git remote, gh CLI, and python3"
---

## Outline

1. Locate the repository root from the current working directory.
1. Find this installed extension directory at `.specify/extensions/github-issue-canon`.
1. Run:

```bash
python3 .specify/extensions/github-issue-canon/scripts/validate_issue_canon.py
```

1. If validation fails, report the invalid issues and do not claim
   `$speckit-taskstoissues` is complete.
1. If project config enables normalization, run
   `$speckit-github-issue-canon-normalize` only after user approval or when the
   project explicitly treats normalization as automatic.
