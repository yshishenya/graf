# Infrastructure Checklist: CI merge queue и provenance release train

**Purpose**: Reviewer-owned infrastructure gate

- [ ] Event-specific target and base SHA contract is complete.
- [ ] `merge_group` synthetic checkout is fail-closed and traceable to PRs.
- [ ] Concurrency keys cancel only superseded logical targets.
- [ ] Cancellation and stale evidence cannot satisfy a required check.
- [ ] Final tracked/untracked cleanliness runs after all artifact generation.
- [ ] Receipts are metadata-only and schema-validated.
- [ ] Release train separates synthetic SHA from post-merge release SHA.
- [ ] Exactly one authoritative Full CI is accepted per frozen candidate.
- [ ] Actions/branch protection changes remain operator-owned after merge.

Implementation agents MUST NOT mark these boxes complete.
