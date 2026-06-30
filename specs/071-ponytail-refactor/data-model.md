# Data Model: Ponytail Refactor Audit

## AuditCandidate

- `id`: Stable identifier used in tasks or notes.
- `location`: File path and optional symbol/line.
- `tag`: One of `delete`, `stdlib`, `native`, `yagni`, `shrink`, or `retain`.
- `risk_domain`: Server, auth, cabinet, deletion, storage, deployment, macOS capture, macOS UI, audio driver, test, script, dependency, or documentation.
- `evidence`: Caller search, dependency graph, runtime role review, or validation reference.
- `decision`: `remove`, `simplify`, `split-later`, or `retain`.
- `validation_required`: Focused command(s) and repository gate.

## CleanupBatch

- `id`: Batch name such as `Batch A`.
- `scope`: Bounded file/domain list.
- `candidates`: Audit candidates included in the batch.
- `excluded_candidates`: Suspicious items intentionally retained.
- `validation_evidence`: Commands run and outcomes.
- `status`: `planned`, `in_progress`, `validated`, or `blocked`.

## DependencyRecord

- `name`: Declared dependency, package target, Docker image, CLI tool, or runtime package.
- `declaration`: Manifest or compose location.
- `usage_evidence`: Imports, plugin use, CLI entrypoint, framework/runtime role, script reference, or Docker reference.
- `decision`: `keep` or `remove`.
- `lockfile_impact`: Expected lockfile change when removed.

## ValidationEvidence

- `command`: Exact command run.
- `scope`: Focused or repository-level.
- `result`: pass, skip, blocked, or fail.
- `notes`: Warnings, skips, environment limitations, or failure summary.

## State Transitions

```text
AuditCandidate -> CleanupBatch(planned)
CleanupBatch(planned) -> CleanupBatch(in_progress)
CleanupBatch(in_progress) -> CleanupBatch(validated) when focused and repository gates pass
CleanupBatch(in_progress) -> CleanupBatch(blocked) when evidence is missing or a gate fails
AuditCandidate -> RetainedCandidateNote when removal is unsafe or not proven
```
