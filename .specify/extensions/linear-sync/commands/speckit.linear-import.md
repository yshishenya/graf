---
name: "speckit.linear-sync.import"
description: "Import existing Linear/GitHub issue mappings before creating new Linear issues."
compatibility: "Requires a Spec Kit project, python3, and optionally LINEAR_API_KEY"
---

## Outline

1. Locate the repository root from the current working directory.
1. Find this installed extension directory at `.specify/extensions/linear-sync`.
1. Run a dry import first:

```bash
python3 .specify/extensions/linear-sync/scripts/linear_sync.py import
```

1. If the report looks correct and `LINEAR_API_KEY` is available, apply:

```bash
python3 .specify/extensions/linear-sync/scripts/linear_sync.py import --apply
```

1. Do not create duplicate Linear issues. Match existing work by feature number,
   task ID, GitHub issue URL, and title before creating anything.
1. All issue text and comments must be in Russian and easy to understand.
