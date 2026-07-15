# Release Closeout: Feature 099

**Date**: 2026-07-15

**Risk / validation lane**: release / deploy

**Current verdict**: release candidate prepared; T111–T112 complete, T113–T116 pending

## Scope And Safety Boundary

- Feature 099 implementation is merged into `master`; this file records only
  the release, deployment, production proof, tracker reconciliation and cleanup
  boundary.
- Feature 097 and its resumable standalone Codex Security scan remain deferred
  and untouched. Ordinary feature-099 authorization, RLS, subprocess,
  redaction and lifecycle checks do not complete that scan.
- Evidence is metadata-only. No media, transcript or summary content, object
  keys, credentials, tokens, signed URLs or private runtime paths are recorded.

## T111 — Implementation Merge And Tracker Linkage

- Implementation commit: `ccf039e6128fe763067d84b5ba3566dc766bc389`.
- Feature PR: [#3470](https://github.com/yshishenya/crisp/pull/3470),
  `feat(playback): автоматически готовить аудио для просмотра`.
- PR state: `MERGED` into `master` on 2026-07-14 at 23:42:05 UTC.
- Exact merge SHA: `da8b22ea069202d9d9961f9a4f46dd4192821da3`.
- Fresh ancestry check after `git fetch --prune --tags origin`:
  `git merge-base --is-ancestor da8b22ea... origin/master` returned success;
  fetched `origin/master` equals the merge SHA.
- GitHub task reconciliation after merge: T001–T110 are closed with their
  discovery/validation receipts; exactly six release-closeout issues remain
  open: T111 [#3458](https://github.com/yshishenya/crisp/issues/3458), T112
  [#3459](https://github.com/yshishenya/crisp/issues/3459), T113
  [#3460](https://github.com/yshishenya/crisp/issues/3460), T114
  [#3461](https://github.com/yshishenya/crisp/issues/3461), T115
  [#3462](https://github.com/yshishenya/crisp/issues/3462) and T116
  [#3463](https://github.com/yshishenya/crisp/issues/3463).

## T112 — CalVer And Release Preparation

- Live remote tag and GitHub Release checks found no `v2026.07.15.*` tag or
  release. The latest published product release at selection time was
  `v2026.07.14.7`; therefore the next free Europe/Moscow CalVer is
  `v2026.07.15.1`.
- Command: `./scripts/prepare-release.sh 2026.07.15.1`.
- Result: success. `CHANGELOG.md` now contains a dated
  `[2026.07.15.1] - 2026-07-15` section with the complete feature-099 entries,
  while `[Unreleased]` was reset to the repository placeholders.
- Generated diff at this checkpoint: one file, `CHANGELOG.md`, with 21 added
  lines and no removed lines. No tag or GitHub Release was created by the
  preparation command.
- The clean release branch started from exact `origin/master` SHA
  `da8b22ea069202d9d9961f9a4f46dd4192821da3`; unrelated dirty worktrees were
  not changed.

## Validated Release Candidate Plan

- Release candidate: `v2026.07.15.1`.
- Tag target: the exact `master` merge SHA of the release-preparation PR, which
  must contain the feature merge plus this changelog/evidence update.
- Required migration: Alembic `0022_playback_normalization`.
- Required runtime change: isolated non-root `rec-media-worker` with the
  validated FFmpeg/FFprobe capability and resource limits.
- Deployment sequence: canonical local gate, release PR merge, annotated tag
  and Russian GitHub Release, `infra/scripts/cd-remote.sh --dry-run`, approved
  `--execute`, then production E2E and cleanup.
- Rollback anchor before deploy: currently deployed immutable release and its
  database backup. The exact runtime SHA, backup location and restore rehearsal
  receipt must be captured by T114 before any rollback claim.
- Compatibility: no user action or media re-upload is expected. Existing
  retained sources are inventoried before bounded automatic backfill. Playback
  readiness remains independent from transcript and summary readiness.
- macOS: feature 099 changes server behavior and macOS regression tests, not
  the native app runtime. The user nevertheless explicitly requested a new
  release-version bundle to be built and installed locally after deployment;
  that owner-machine package remains local self-signed validation, not public
  Developer ID/notarized distribution.
- Known limitation: feature 097 security scan remains deferred. This release
  must not claim that scan as completed.

## Fresh Release Gate

- Command: `infra/scripts/ci-local.sh` from the clean release worktree after
  the CalVer, task and status evidence edits.
- Result: `ci_local_result=pass`, exit code `0`.
- macOS: build passed; `643/643` Swift tests passed; contract validation passed.
- Server: `1713 passed, 21 skipped` in `454.71s`; Ruff passed; Python compile
  passed. One third-party Starlette deprecation warning was emitted and did not
  affect the result.
- Compose rendering passed and showed the required non-root media-worker,
  one-activity concurrency, 1 CPU, 1 GiB memory, 128 PID limit, read-only root
  filesystem, private media network and separate media database/storage roles.
- Deployment evidence scan passed for all seven tracked deployment receipts.
- The canonical local script intentionally reported its PostgreSQL RLS boundary
  as `blocked` because no destructive test database URL was supplied. This is
  not treated as live RLS proof. The already-recorded disposable PostgreSQL
  receipts remain `23/23` plus the direct RLS probe with zero cluster residue;
  T114 must additionally capture production migration/RLS truth during deploy.

## Pending Receipts

- T113: annotated tag and Russian GitHub Release on the exact release SHA.
- T114: dry-run, approved deploy, backup/restore, migration, runtime SHA,
  health and smoke evidence.
- T115: production first-party/manual normalization, automatic recovery,
  inventory-before-mutation backfill, Chrome/embedded Range playback,
  transcript independence, worker/migration health and residue-zero cleanup.
- T116: final status update, task/issue closure comments and safe
  branch/worktree/test-artifact cleanup.
