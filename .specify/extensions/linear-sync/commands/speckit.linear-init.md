---
name: "speckit.linear-sync.init"
description: "Create or refresh project Linear sync configuration."
compatibility: "Requires a Spec Kit project and python3"
---

## Outline

1. Locate the repository root from the current working directory.
1. Find this installed extension directory at `.specify/extensions/linear-sync`.
1. Run:

```bash
python3 .specify/extensions/linear-sync/scripts/linear_sync.py init
```

1. Keep secrets out of `.specify/linear.yml`. Use `LINEAR_API_KEY` and other
   environment variables for credentials.
1. All generated instructions, issues, and comments must be in Russian and
   written in simple language.
