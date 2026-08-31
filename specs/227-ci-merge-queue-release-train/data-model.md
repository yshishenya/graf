# Data Model: CI merge queue и provenance release train

## EventIdentity

- `event_name`: `pull_request`, `merge_group` or `workflow_dispatch`.
- `target_sha`: exact 40-character commit checked out by the run.
- `base_sha`: exact comparison base; required for PR and merge group.
- `pull_request_numbers`: sorted unique PR numbers when available.
- `merge_group_id`: GitHub merge-group identity when available.
- `workflow`, `run_id`, `run_attempt`, `workflow_url`.

## CIReceipt

- `schema_version`.
- `status`: `passed`, `failed`, `cancelled`, `superseded`, `stale` or
  `ambiguous`.
- `event_identity`.
- `requested_sha`, `observed_sha_start`, `observed_sha_end`.
- `local_evidence_digest` and artifact digests.
- `final_cleanliness`: `pass` or terminal non-pass with bounded reason.
- `created_at`, `finished_at`.

## ReleaseTrainManifest

- `schema_version`, `train_id`, `created_at`, `operator`.
- `source_sha`: actual post-merge SHA selected for release.
- `base_sha`, `synthetic_merge_sha`.
- `included_prs`, `feature_ids`, `merge_group_ids`.
- `pr_receipts`, `merge_group_receipts`.
- `changelog_digest`.
- `authoritative_full_ci_receipt`.
- `decision`, `calver`, `rollback_target`.

## Invariants

1. Every receipt target SHA equals its checked-out HEAD.
2. A release train `source_sha` is not inferred from synthetic merge SHA.
3. Every included PR and Feature ID has a matching receipt or explicit
   fail-closed reason.
4. A cancelled, superseded, stale or ambiguous receipt cannot satisfy release
   readiness.
5. Receipt payloads remain metadata-only.
