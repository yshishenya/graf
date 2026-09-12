# Data Model: CI/CD validation evidence

No application or production database changes are required. These are local operational entities.

## BehaviorTestPlan (A3, transient diagnostic only)

- `changed_paths`, `head_sha`, `base_ref`, `dirty_worktree`: input identity from the existing diff and current checkout. Local snapshots are diagnostic, not exact-SHA evidence.
- `groups`: named groups with matching input paths and mandatory existing test files.
- `tests`, `covered_tests`: ordered union to execute and targets already selected by this fast run's unit stage, never a cache of old results. Mapped contract files execute in the behavior stage and are excluded from the later changed-file stage.
- `environment`, `coverage=partial`, `next_gate`, `scope=working_tree_diagnostic`: resource requirements and limits. Missing mandatory files, empty test modules or removed named rail proof are errors.
- No schema change for CI evidence/receipt; `--plan` and `--focused` never produce those records.

## PRMetadataSnapshot (A2, temporary only)

- Event: positive integer PR number; head/base full commit SHAs; nonempty base ref.
- Current API object: same number/head/base/ref, state=open, nonempty title/body; head repository may be a fork.
- Checkout HEAD equals event head. Base/head share history; changed paths are computed from their merge base with NUL delimiters and without rename collapsing.
- Current title/body are authoritative for this check even when event text differs. Unknown/invalid JSON shapes and changed identity fail. This is snapshot validation, not a new persistent receipt, cache or atomic merge authorization.
- No full response/body/title is written into logs or Git. A failed fetch never falls back to event text. Only the temporary runner file holds the API response.

## ValidationLane

- `name`: `fast` or `full` for CI evidence; A3 adds a diagnostic focused command and read-only plan outside this evidence model.
- `requested_name`: explicit operator input.
- `effective_name`: identical to the explicit operator request; fast never escalates.
- `components`: unique ordered set of `docs`, `server`, `macos`, `infra`, `unknown`, or `full`.
- `changed_paths`: metadata-safe repository-relative paths used for classification.
- `base_sha`: full event base for PR/MG, the same identity recorded in receipt and used through `GRAF_CI_BASE_REF` for merge-base selection. Missing/invalid/unavailable event base blocks remote CI before tests. Manual dispatch keeps a null base and diagnostic default; no schema change.
- `reason`: stable reason code for selection or coverage limitation.
- `coverage`: `bounded` for reviewed low-risk component fast, `partial` for
  shared/high-risk/unknown/unresolvable fast, or `complete` for full.
- `next_gate`: `full_before_release` for fast, `full_in_progress` while full is
  running, `full_diagnostic_only` after a passing local full, or `full_failed` after a
  failing full.
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
- Successful authoritative GitHub `release-full` for the immutable candidate, verified and reused by execute; a local full is not release evidence.
- Existing independent production gates remain attached and follow that full gate.
