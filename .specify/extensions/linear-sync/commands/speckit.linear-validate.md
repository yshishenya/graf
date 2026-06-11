---
name: "speckit.linear-sync.validate"
description: "Validate task, GitHub issue, and Linear issue mapping health."
compatibility: "Requires a Spec Kit project and python3"
---

## Outline

1. Locate the repository root from the current working directory.
1. Find this installed extension directory at `.specify/extensions/linear-sync`.
1. Run:

```bash
python3 .specify/extensions/linear-sync/scripts/linear_sync.py validate
```

1. When `LINEAR_API_KEY` is available, run an applied validation to check real
   Linear status and project membership:

```bash
python3 .specify/extensions/linear-sync/scripts/linear_sync.py validate --apply
```

1. Treat missing mappings, duplicate Linear issues, closed GitHub issues with
   open Linear issues, and Linear Done with open `tasks.md` tasks as follow-up
   items that need a clear Russian explanation.
