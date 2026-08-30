# Data Model: CI/CD validation evidence

No application or production database changes are required. These are local operational entities.

## ValidationLane

- `name`: `fast` or `full`; focused validation remains a direct feature command.
- `requested_name`: explicit operator input.
- `effective_name`: selected lane after conservative escalation.
- `components`: unique ordered set of `docs`, `server`, `macos`, or `full`.
- `changed_paths`: metadata-safe repository-relative paths used for classification.
- `reason`: stable reason code for selection or escalation.
- `result`: `pass` or `fail`.
- `started_at`, `completed_at`, `duration_seconds`.
- `stages`: ordered StageResult list.

Validation rules:

- Missing requested lane is invalid.
- Unknown/shared/high-risk/unresolvable paths require `effective_name=full`.
- A result is pass only when every hard stage passes.

## StageResult

- `name`: stable stage label.
- `status`: `pass`, `fail`, `skipped`, or `report_only_fail`.
- `duration_seconds`: non-negative integer.
- `reason`: optional stable reason; never raw secret-bearing command output.

## FullCIReceipt (version 2)

- `version`: integer `2`.
- `result`: exactly `pass`.
- `created_at_epoch`, `started_at_epoch`, `duration_seconds`.
- `commit_sha`, `tree_sha`.
- `runner_inputs`: relative path → SHA-256.
- `dependency_inputs`: relative path → SHA-256.
- `test_surface_digest`: SHA-256 of ordered tracked test paths and contents.
- `server_collection_count`, `server_collection_digest`.
- `completed_stages`: exact ordered platform-required full-stage list, attested
  by the runner's private temporary mode-`0600` journal.
- `toolchain`: stable command → normalized version output.

Validation rules:

- Receipt creation requires a clean tracked and untracked worktree, successful
  full result and complete ordered stage journal; direct caller metadata alone
  is insufficient.
- Receipt age must not exceed the configured maximum (default 86,400 seconds).
- Every current field above is recomputed or strictly checked before reuse.
- Missing, malformed, unsupported-version, stale or mismatched receipt is invalid.
- The receipt lives below the Git metadata path, mode `0600`, and is atomically replaced.

State transitions:

```text
absent/invalid -> full running -> full failed -> invalid
absent/invalid -> full running -> full passed on dirty tree -> not reusable
absent/invalid -> full running -> full passed on clean tree -> valid
valid -> input/toolchain/time/worktree change -> invalid
valid -> deploy preflight consumes evidence -> remains valid until an input changes/expires
```

## ReleaseCandidate

- Exact local commit and tree.
- Matching `origin/<branch>` SHA.
- Clean worktree.
- Valid FullCIReceipt or a successful full fallback.
- Existing independent production gates remain attached and are not fields in the receipt.
