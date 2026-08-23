# GitHub Issue Sync: Automatic Recording Reliability

**Feature**: `193-automatic-recording-reliability`
**Created**: 2026-08-23
**Source of truth**: [tasks.md](tasks.md)

## Mapping

| Tasks | Issue | State | Scope |
|---|---:|---|---|
| `T001-T003` | [#5610](https://github.com/yshishenya/graf/issues/5610) | OPEN | Independent source state and candidate lifecycle |
| `T004-T007` | [#5611](https://github.com/yshishenya/graf/issues/5611) | OPEN | Current authorization gate and consumer acknowledgement |
| `T008-T010` | [#5612](https://github.com/yshishenya/graf/issues/5612) | OPEN | Snapshot/live observer recovery and wake |
| `T011-T013` | [#5614](https://github.com/yshishenya/graf/issues/5614) | OPEN | Same-origin web/native auth reconciliation |
| `T014-T016` | [#5613](https://github.com/yshishenya/graf/issues/5613) | OPEN | Metadata-only diagnostics and validation evidence |

## Validation

- Duplicate search for `feature:193` found no prior task issues before creation.
- All five Feature 193 issues pass the repository `validate_issue()` canon check.
- The global wrapper currently also inspects pre-existing issue `#5472` and
  reports its missing `Spec tasks: T001` context; Feature 193 did not modify that
  unrelated issue.
- The configured remote `yshishenya/crisp` redirects on GitHub to
  `yshishenya/graf`; canonical issue URLs therefore use the current repository
  name returned by GitHub.
