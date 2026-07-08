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
1. After this hook succeeds, continue `$speckit-taskstoissues` using
   `docs/agent-guidance/github-issue-canon.md` as the authoritative source for
   issue titles, bodies, and labels. Repositories using this canon have one
   valid Spec Kit task issue title shape:
   `[<feature>][<priority>][<area>] T###: <русский результат>`.
   Treat generic `T001: <description>` title instructions as fallback guidance
   only for repositories without a project canon.
