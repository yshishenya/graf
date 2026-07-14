# Feature 099 PR Closeout

**Feature**: `099-review-m4a-normalization`
**Risk/validation lane**: significant high-risk Spec Kit slice
**Status**: integration approved; exact feature staging and commit authorized

## Exact candidate

- Branch: `codex/099-review-m4a-normalization`.
- Current `HEAD` and `origin/master` base:
  `98d57f7431d302b0d2060fb020fc2b320f854753`.
- Current-master integration receipt: `validation/master-sync.md`.
- Tracked modified files: `102`.
- New untracked feature files: `91`.
- Pre-stage files: `102` tracked modifications plus `91` new feature files.
- Pre-stage staged files: `0`.
- Sorted candidate path-set SHA-256:
  `bce0398319f5af4c582ef56588bd62283fcc3aed7757886c2f396f405c1bd0e2`.
- Authorized staging verification: `193` staged files, `0` unstaged, `0`
  untracked, `0` unmerged; staged path-set SHA-256 matched the candidate digest.
- Staged binary entries: `0`; forbidden media/database/archive/key extensions:
  `0`; secret-token markers: `0`; `git diff --cached --check`: pass.
- Unmerged paths: `0`.
- Binary diff entries: `0`.
- Media/database/archive/key/environment-secret artifacts: `0`.
- Named recovery stash retained until the candidate is committed and verified:
  `0288554b89f7af7b00f4dab9eade284ac581ed14`.

All candidate files belong to feature 099. The unrelated detached worktree is
untouched. The `apps/macos` feature diff contains four regression-test files
only; there is no macOS application-source change or reinstall requirement.

## Proposed PR

Title:

```text
feat(playback): автоматически готовить аудио для просмотра
```

Summary for the Russian PR body:

- every valid retained first-party recording and supported manual upload gets
  one server-owned canonical review M4A automatically;
- canonical reuse, lossless remux and bounded conversion are selected from
  verified media truth, with no user/admin repair or backfill controls;
- retry, restart, inventory-before-mutation backfill and failure truth remain
  automatic and durable;
- canonical playback alone owns Range egress and remains independent from
  transcript/summary readiness;
- additive migration `0022`, isolated non-root media worker, force-RLS,
  deletion precedence, retention, readiness, rollback and cleanup boundaries
  are included;
- current `v2026.07.14.7` cabinet UI and unchanged embedded macOS boundary are
  covered by the final local browser receipt;
- feature 097 and its standalone security scan remain explicitly deferred and
  are not part of this PR.

The PR will close only completed T001-T110 issues and reference T111-T116 as
post-merge release/deploy work. All `116/116` task-backed issues were open at
the pre-creation read-back, there were no duplicate issue numbers, and no
existing PR or remote feature branch was found.

## Final validation

- Focused current-master cabinet integration: `164 passed`.
- Canonical local CI: `ci_local_result=pass`, macOS `643/643`, server
  `1713 passed`, `21 skipped`, Ruff/compile/Compose/evidence scan pass.
- Native disposable PostgreSQL: `23/23`; direct RLS probe pass; residue `0`.
- Post-review PostgreSQL commit-boundary repair: exact regressions `3/3`, full
  normalization PostgreSQL file `12/12`, residue `0`.
- Media container matrix: `14/14`.
- Near-limit package: about 5 GiB, `185.236s`, OOM `0`, residue `0`.
- Authorized local conversion and deletion/race cleanup: pass; originals
  preserved; residue `0`.
- Real Chrome after current-master sync: preparing -> automatic ready,
  Play/Pause/seek, `206 Range`, unavailable truth, responsive/focus/reduced
  motion, visible automatic recovery after `503`/redirect/disconnect, terminal
  deletion with no resurrection and empty warning/error log; residue `0`.
- Embedded derived QA app: Play/Pause/seek and close/relaunch recovery pass;
  installed GRAF app untouched.
- `git diff --check`: pass.

## Review and approval gate

The final independent re-reviews are complete:

- product/spec: approved with no actionable finding; current-base embedded
  progression plus the shared fragment/terminal contract and current Chrome
  deletion proof were accepted as sufficient and honestly scoped;
- code/RLS: approved with no actionable finding; the PostgreSQL P1 is closed,
  transaction-local replay retains pooled-connection isolation, and the three
  exact commit boundaries are covered;
- QA/release: approved after a final read-only residue check reported feature
  temp paths `0`, ports `8099/8100/55499` clear, derived processes `0` and
  Docker feature residue `0`.

The installed `/Applications/GRAF.app` remained separate and running during
the final read-back. The ScreenCaptureKit failure affected only an additional
disposable desktop screenshot and is disclosed in `browser-e2e.md`; it is not
hidden as product success evidence.

On 2026-07-15 the user explicitly authorized the exact integration action:
`Да, разрешаю интеграцию 099: коммит, push, PR и merge`. The approval covers
staging the verified 099 path set, creating the implementation commit, pushing
the branch, opening the PR and merging it only after required CI/review checks
pass. The configured Spec Kit `after_implement` auto-commit hook was checked
and is disabled, so the implementation uses this explicit approval and a
manually reviewed stage/commit boundary.

This approval does not authorize release preparation, tagging, GitHub Release
publication or production deployment. Those actions remain T112-T115 and need
a fresh release/deploy approval after merge and successful deploy dry-run.
