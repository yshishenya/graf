# Operational Readiness Requirements Checklist: Быстрый и доказуемый CI/CD

**Created**: 2026-08-30

This checklist records the original `v2026.08.30.1` requirements review.
CHK002 and CHK011 are superseded for the 2026-08-31 follow-up by
[`fast-lane.md`](fast-lane.md); the release/deploy full gate is unchanged.

## Requirement completeness and clarity

- [x] CHK001 Focused, fast and full are distinct evidence levels.
- [x] CHK002 Shared, unknown, high-risk and unresolvable diffs fail closed to full.
- [x] CHK003 Production execute order is measurable: clean → sync → full → remote.
- [x] CHK004 A hard full-stage failure blocks all remote production actions.
- [x] CHK005 Active instructions are separated from immutable historical evidence.
- [x] CHK006 Bare CI exits before tests with an explicit-lane usage message.
- [x] CHK007 Stage and total timing are defined for success and failure.
- [x] CHK008 Only the load-sensitive p95 threshold may be report-only.
- [x] CHK009 Batching is guidance and does not remove the hotfix path.

## Consistency and acceptance

- [x] CHK010 Spec, research, model, contract and tasks agree on one full inside execute.
- [x] CHK011 Component-aware fast remains fail-closed at trust boundaries.
- [x] CHK012 Clean-tree, remote-sync and exact-SHA checks precede full.
- [x] CHK013 Immutable-image delivery remains out of scope.
- [x] CHK014 Contract tests can prove no stage runs for a bare command.
- [x] CHK015 Contract tests can prove clean → sync → full → remote ordering.
- [x] CHK016 Documentation consistency is measurable without rewriting history.
- [x] CHK017 The acceleration target uses the measured `1406.36s` baseline.

## Security and operations

- [x] CHK018 Local receipt reuse is rejected because it lacks independent provenance.
- [x] CHK019 No new service, package, credential or persistent evidence is added.
- [x] CHK020 `--skip-local-ci` remains an explicit incident-only exception.
- [x] CHK021 Backup/restore, RLS, secrets, health, smoke, lock and rollback remain intact.
- [x] CHK022 Commit, push, PR, merge, release and production deploy are explicitly authorized.
- [x] CHK023 No unresolved clarification, placeholder or conflicting full-gate rule remains.
