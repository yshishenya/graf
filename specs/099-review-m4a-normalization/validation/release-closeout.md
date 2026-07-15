# Release Closeout: Feature 099

**Date**: 2026-07-15

**Risk / validation lane**: release / deploy

**Current verdict**: `v2026.07.15.1` published; first deploy safely rolled back
before migration; image-resolution hotfix in validation; T111–T113 complete,
T114–T116 pending

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

- T114: dry-run, approved deploy, backup/restore, migration, runtime SHA,
  health and smoke evidence.
- T115: production first-party/manual normalization, automatic recovery,
  inventory-before-mutation backfill, Chrome/embedded Range playback,
  transcript independence, worker/migration health and residue-zero cleanup.
- T116: final status update, task/issue closure comments and safe
  branch/worktree/test-artifact cleanup.

## T113 — Published Release

- Release-preparation PR: [#3471](https://github.com/yshishenya/crisp/pull/3471),
  merged into `master` at exact SHA
  `619c6ce3600d2d56e3461b69d523c4240ec8767a`.
- Annotated tag: `v2026.07.15.1`; the peeled tag commit exactly matches the
  release-preparation merge SHA above.
- Stable GitHub Release:
  [v2026.07.15.1](https://github.com/yshishenya/crisp/releases/tag/v2026.07.15.1).
  Its Russian notes contain changes, validation, migration and compatibility
  impact, limitations, rollback guidance, PR/issues and the deferred feature
  097 boundary.

## T114 — First Deploy Attempt And Safe Recovery

- `infra/scripts/cd-remote.sh --dry-run --branch
  codex/deploy-v202607151-099` passed for exact release SHA
  `619c6ce3600d2d56e3461b69d523c4240ec8767a`.
- The explicitly approved `--execute` reran the canonical local gate
  successfully: macOS `643/643`; server `1713 passed, 21 skipped`; Ruff,
  compile, Compose rendering and deployment evidence passed.
- Runtime secret provisioning, media-storage provisioning, database backup
  `20260715T004551Z` and restore rehearsal passed. The media-worker image was
  built, but the deploy gate then stopped with
  `reason=media_worker_image_missing` before migration or runtime mutation.
- The staged rollback restored the previous production source SHA
  `e77f942bf178862905ee98b27488d87e469c3e26`; a read-only follow-up confirmed
  that SHA, a clean production worktree and the successfully built worker
  image.
- Root cause: `docker compose images -q rec-media-worker` lists images attached
  to existing containers, so a first rollout returns no image ID even after a
  successful build. The hotfix resolves the generated image reference through
  `docker compose config --images` and validates the built ID with
  `docker image inspect`, without creating or starting a probe container.
- This receipt proves safe recovery only. T114 remains open until a new
  hotfix release passes the full deployment, migration, health and smoke gates.

## Image-Resolution Hotfix Validation

- The hotfix changes only the post-build image lookup: it reads the generated
  `rec-media-worker` reference from `docker compose config --images`, resolves
  the built image ID with `docker image inspect`, and retains the existing
  fail-closed `media_worker_image_missing` gate.
- The regression executes the actual extracted deployment block under
  `set -euo pipefail`. It passes when a matching image and image ID exist and
  blocks with the exact reason when the Compose list has no match or image
  inspection fails. Focused result: `21 passed`; Ruff, `bash -n`, ShellCheck
  with the existing sourced-env exception and `git diff --check` passed.
- The real rendered Compose image list resolves exactly
  `twobrain-rec-rec-media-worker` in the validation worktree.
- Two read-only review passes by an independent reviewer found no remaining
  findings or blockers; the second pass covered the executable three-scenario
  regression and the no-early-SIGPIPE AWK form.
- Fresh canonical `infra/scripts/ci-local.sh` result after the final
  code-affecting edit: `ci_local_result=pass`; macOS `643/643`; server
  `1716 passed, 21 skipped`; Ruff, Python compile, Compose rendering and the
  seven-file deployment evidence scan passed. The expected local RLS boundary
  remained `postgres_test_database_required`; it did not claim live production
  database truth.
- T114 remains open. The hotfix requires an approved integration PR, a new
  free CalVer, a fresh deploy dry-run and a successful production execute
  before migration, worker or conversion readiness is claimed.
