# Research: Process Closeout And Issue Truth

## Findings

1. `scripts/claim-feature.py` previously paginated every repository issue before
   allocation. The public repository is large enough for that call to exceed
   the 30-second fail-closed timeout.
2. The allocator was invoked after creating the requested branch, so its own
   `codex/234-process-closeout` ref appeared to occupy Feature 234.
3. The issue canon already defines Russian closure comments, but no validator
   or closeout task made the rule operational; F233 was closed with no comment
   and unchecked tasks.
4. GitHub Actions and `governance-fast` are already the authoritative gate on
   current `master`; templates still need the same wording to prevent agents
   from treating local CI as the merge gate.

## Decisions

- Use exact GitHub Search queries for only the candidate marker during online
  claims. Keep full pagination only as an explicit legacy/test path.
- Exclude the requested branch and its origin ref from the local collision set.
- Keep issue closure human/owner controlled, but make the task/issue/evidence
  invariant executable in the feature checklist and closeout runbook.
- Reconcile F233 explicitly rather than silently changing its history.
