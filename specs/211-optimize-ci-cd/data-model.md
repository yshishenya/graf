# Data Model: CI/CD validation evidence

No application or production database changes are required. These are local operational entities.

## ValidationLane

- `name`: `fast` or `full`; focused validation remains a direct feature command.
- `requested_name`: explicit operator input.
- `effective_name`: identical to the explicit operator request; fast never escalates.
- `components`: unique ordered set of `docs`, `server`, `macos`, `infra`, `unknown`, or `full`.
- `changed_paths`: metadata-safe repository-relative paths used for classification.
- `reason`: stable reason code for selection or coverage limitation.
- `coverage`: `bounded` for fast or `complete` for full.
- `next_gate`: `full_before_release` for fast or `release_ready` after full.
- `result`: `pass` or `fail`.
- `started_at`, `completed_at`, `duration_seconds`.
- `stages`: ordered StageResult list.

Validation rules:

- Missing requested lane is invalid.
- `requested_name=fast` always requires `effective_name=fast` and
  `next_gate=full_before_release`.
- Unknown/shared/high-risk/unresolvable paths add an explicit partial-coverage
  reason and never claim full evidence.
- A result is pass only when every hard stage passes.

## StageResult

- `name`: stable stage label.
- `status`: `pass`, `fail`, `skipped`, or `report_only_fail`.
- `duration_seconds`: non-negative integer.
- `reason`: optional stable reason; never raw secret-bearing command output.

## ReleaseCandidate

- Exact local commit and tree.
- Matching `origin/<branch>` SHA.
- Clean worktree.
- Successful authoritative full inside the same execute flow.
- Existing independent production gates remain attached and follow that full gate.
