# Release Train Contract v1

`ReleaseTrainManifest` binds a batch of merged work to exactly one release
candidate.

Required fields:

```text
schema_version
train_id
source_sha
base_sha
synthetic_merge_sha
included_prs
feature_ids
merge_group_ids
pr_receipts
merge_group_receipts
changelog_digest
authoritative_full_ci_receipt
decision
rollback_target
```

`source_sha` must resolve to the actual post-merge `master` commit. Synthetic
merge SHA is provenance only. `decision=go` requires one matching authoritative
Full CI receipt and no stale/superseded receipt. The manifest is immutable after
freeze; correction creates a new train ID.
