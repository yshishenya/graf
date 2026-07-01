# Contract: Refactor Batch

Each future batch in `audit/refactor-roadmap.md` must follow this contract.

```yaml
batch_id: RB-072-00
goal: "Small behavior-preserving outcome"
classification_source:
  - F-072-000
included_paths:
  - exact/repository/path
excluded_paths:
  - exact/repository/path
expected_diff_shape: "move-only, split-only, test-only, docs-only, or spec-first"
validation:
  - "Focused tests or scripts"
  - "Repository gate when needed"
release_policy: no deploy | cd dry-run | cd execute
rollback_note: "How to undo safely if behavior changes"
```

## Rules

- A batch must be small enough to review as one PR.
- A batch cannot mix capture, auth, deletion, processing, and deploy changes
  unless a separate Spec Kit slice explicitly says so.
- `delete now` candidates cannot be deleted until their batch repeats caller
  evidence and focused validation.
- `risky / needs spec` findings cannot be included in a normal split PR.

