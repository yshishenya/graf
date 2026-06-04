---
name: "speckit.github-issue-canon.normalize"
description: "Normalize existing GitHub issues to the project issue canon."
compatibility: "Requires a Spec Kit project, git remote, gh CLI, and python3"
---

## Outline

1. Locate the repository root from the current working directory.
1. Find this installed extension directory at `.specify/extensions/github-issue-canon`.
1. Run:

```bash
python3 .specify/extensions/github-issue-canon/scripts/normalize_issue_canon.py "$ARGUMENTS"
```

1. Use this for existing issues or after task-to-issue sync when issue bodies or
   labels need canonical cleanup.
1. Report every issue number changed.
