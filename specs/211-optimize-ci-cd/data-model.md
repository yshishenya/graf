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

## ReleaseCandidate

- Exact local commit and tree.
- Matching `origin/<branch>` SHA.
- Clean worktree.
- Successful authoritative full inside the same execute flow.
- Existing independent production gates remain attached and follow that full gate.
