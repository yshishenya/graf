# Финальный анализ Feature 211

**Дата**: 2026-08-30
**Lane**: high-risk infrastructure / validation governance
**Результат**: локальная реализация и проверки завершены; commit, PR, release и deploy не выполнялись.

## Spec Kit consistency

Повторный read-only `$speckit-analyze` после устранения performance-gap:

- требований: `23` (`FR-001`–`FR-014`, `SC-001`–`SC-009`);
- задач: `28`;
- покрытие требований задачами: `23/23` (`100%`);
- CRITICAL: `0`;
- HIGH: `0`;
- ambiguity: `0`;
- duplication: `0`;
- constitution conflicts: `0`;
- unmapped tasks: `0`.

Опциональные before/after analyze git-commit hooks не выполнялись: implementation
commit требует отдельного разрешения пользователя.

## Coverage summary

| Requirement | Tasks | Evidence |
|---|---|---|
| FR-001–FR-004 | T004, T007–T010, T015, T018 | explicit lane, component union/escalation, timing and failure contracts |
| FR-005–FR-008 | T005, T011–T014, T027–T028 | exact-input receipt, dirty/stale/mismatch rejection, deploy reuse/fallback, preserved gates |
| FR-009 | T006, T016–T018 | report/required performance boundary and related-path selection |
| FR-010–FR-012 | T002, T019–T023, T027–T028 | active docs/code consistency with historical evidence excluded |
| FR-013–FR-014 | T001, T019–T020, T023, T028 | release batching guidance; immutable-image pipeline explicitly out of scope |
| SC-001–SC-008 | T004–T027 | executable CLI/receipt/deploy contracts plus real fast/full repository gates |
| SC-009 | T003, T025, T028 | baseline `1406.36s`; server-only fast runs `86/71/70s`, p50 `71s` |

## Code, contract and documentation audit

Resolved during the final audit:

1. The original EXIT trap lost function-local state and could fail while printing
   the final result. `main` now runs in a subshell, and the negative contract
   proves exactly one final failure with no receipt.
2. Explicit `--full` originally did not select the required performance gate for
   related calendar paths. Full and fast now inspect the same diff for that gate.
3. macOS dependency manifests and CI/release governance paths now fail closed to
   full rather than entering a component-only lane.
4. Receipt validation now checks consistent start/create/duration timestamps and
   rejects future or internally inconsistent evidence.
5. Active-document enforcement now covers root/operator guidance recursively and
   rejects inline as well as standalone bare CI commands.
6. The AGENTS plan marker was corrected from Feature 210 to 211. The real tracked
   PR-template path is lowercase and all code/docs/tests use
   `.github/pull_request_template.md`, so Linux does not depend on macOS
   case-insensitive path behavior.
7. The first real gate failed closed on two Ruff findings in the new test. They
   were fixed, focused checks repeated, and both subsequent repository gates
   passed; the failed run is not counted as PASS.
8. PR review found that fast calendar changes selected `required` but passed a
   hardcoded `report` to the server runner. The selected gate is now forwarded
   and covered by an executable contract.
9. PR review also found that collection count/digest alone could call receipt
   creation. Version 2 now requires the exact ordered platform full-stage list
   from the runner's private mode-`0600` temporary journal; incomplete or
   caller-only evidence fails with `evidence_invalid`.
10. Follow-up review bound receipt issuance to the clean snapshot captured
    before the first stage, made synchronized-master full runs require the
    performance threshold, and stopped masking non-timing performance failures.
11. Deployment evidence and high-risk backend/API paths now escalate to full,
    while any tracked-diff command failure propagates into the documented
    `diff_unavailable` fallback.

No production remote step was changed below the local preflight boundary.
Backup/restore, migration/RLS, secret, runtime readiness, smoke, cleanup, lock,
public health and rollback gates remain delegated to the unchanged remote runtime
script. `--skip-local-ci` remains an explicit incident-only exception.

## Validation evidence

- shell syntax, Python compile, Ruff and `git diff --check`: PASS;
- focused CI/CD contracts after follow-up review corrections: `52 passed`;
- active bare CI commands: `0`;
- fast request on this infrastructure diff: `effective=full`, PASS in `950s`;
- explicit full before the final path correction: PASS in `1216s`; final full
  on frozen runtime code: PASS in `693s`;
- both repository runs: macOS `769/769`; server collection `3808`, digest
  `94b79743f937f9a9f04fde2a62b97041467e7525e66d8bcf3e7052a7bcc04a31`;
- server parallel `3753 passed, 1 skipped`; performance `1 passed`; strict RLS
  `52 passed, 1 skipped`; lint/compile/Compose/evidence/docs PASS;
- dirty-worktree receipt boundary: correctly skipped; clean create/reuse and all
  invalid cases: PASS in disposable-repository contracts;
- server-only fast p50: `71s`, about `94.95%` below the pre-change full baseline;
- CD dry-run: PASS with `valid_full_receipt_or_full_fallback`; production execute
  was not run.

## Release boundary

- The worktree also contains a broad `.specify/.agents` bootstrap/skill diff not
  named by the Feature 211 implementation tasks. It remains preserved in the
  original worktree and is not part of the clean release branch or PR.
- PR [#6004](https://github.com/yshishenya/graf/pull/6004) carries the scoped
  implementation from a clean checkout of synchronized `origin/master`.
- Exact merge, tag, release, runtime SHA and production gate truth are recorded
  in the PR/GitHub release/deployment output. This analysis does not infer them
  from an implementation worktree.

## Conclusion

The executable contract, active documentation and validation evidence now agree.
There are no unresolved CRITICAL/HIGH implementation or specification findings.
Any production rollout still requires the normal clean-tree, synchronized-master,
exact-SHA, full receipt and unchanged remote release gates.
