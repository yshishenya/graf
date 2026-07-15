# Release Closeout: Feature 099

**Date**: 2026-07-15

**Risk / validation lane**: release / deploy

**Current verdict**: `v2026.07.15.2` published but not deployed; both rollout
attempts ended in verified rollback; runtime-secret readability hotfix is
validated and awaits integration approval; T111–T113 complete, T114–T116
pending

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
- Approved hotfix commit:
  `1073abf81f0632b9f4a4f19dec00674edd8e48f6`. PR
  [#3472](https://github.com/yshishenya/crisp/pull/3472) merged into `master`
  at exact SHA `9081a942040d19819119feb6cf043c603514e401`; the commit is an
  ancestor of the fetched `origin/master`.
- T114 remains open. A new free CalVer, fresh deploy dry-run and successful
  production execute are still required before migration, worker or
  conversion readiness is claimed.

## T114 — Hotfix Release Candidate

- Live remote tag and GitHub Release checks found only stable
  `v2026.07.15.1`; no `v2026.07.15.2` tag or Release existed. The next free
  Europe/Moscow product CalVer is therefore `v2026.07.15.2`.
- The clean release worktree started from exact hotfix merge SHA
  `9081a942040d19819119feb6cf043c603514e401`; unrelated dirty worktrees were
  not changed.
- Command: `./scripts/prepare-release.sh 2026.07.15.2`.
- Result: success. The verified hotfix entries moved from `[Unreleased]` into
  `[2026.07.15.2] - 2026-07-15`; no tag or GitHub Release was created by the
  preparation command.
- Fresh canonical release-candidate gate:
  `infra/scripts/ci-local.sh` returned `ci_local_result=pass`; macOS build,
  `643/643` tests and contract validation passed; server
  `1716 passed, 21 skipped` in `589.76s`; Ruff, Python compile, production
  Compose rendering and the seven-file deployment evidence scan passed. The
  expected local PostgreSQL boundary remained
  `postgres_test_database_required` and did not claim live production truth.
- The tag target will be the exact merge SHA of the release-preparation PR.
  Deployment still requires a fresh dry-run followed by the already approved
  execute path and production receipts.

## T113 — Published Hotfix Release `v2026.07.15.2`

- Release-preparation PR: [#3473](https://github.com/yshishenya/crisp/pull/3473),
  merged into `master` at exact SHA
  `13fe923421df60da77a0b936a8b04cd63db6f891`.
- Annotated tag object:
  `cfb0762433d71e6e2802b26cac4a21d5d9912c16`; its peeled commit is exactly the
  release-preparation merge SHA above.
- Stable GitHub Release:
  [v2026.07.15.2](https://github.com/yshishenya/crisp/releases/tag/v2026.07.15.2),
  title `v2026.07.15.2 - безопасный первый запуск media-worker`.
- The release is published but not production-deployed. The immutable
  `v2026.07.15.1` and `v2026.07.15.2` tags were not moved after either failed
  rollout.

## T114 — Second Deploy Attempt And Verified Rollback

- Deploy branch `codex/deploy-v202607152-099` and dry-run were anchored to exact
  release SHA `13fe923421df60da77a0b936a8b04cd63db6f891`.
- Approved `--execute` reran the complete local gate successfully: macOS
  `643/643`; server `1716 passed, 21 skipped` in `593.62s`; Ruff, compile,
  Compose rendering and deployment evidence passed.
- Runtime database and media-storage secret provisioning passed. Backup
  `20260715T113447Z` and restore rehearsal passed; images, media capability and
  profile contract passed.
- Migration `0022_playback_normalization` completed, but the one-shot runtime
  database-role bootstrap could not read the first newly generated non-root
  credential. It failed closed with the safe reason
  `runtime database role secret is unreadable`; automatic dispatch had not
  opened.
- Staged rollback downgraded schema to `0021_calendar_auto_context_match`,
  removed feature-specific storage/role state, restored production runtime SHA
  `e77f942bf178862905ee98b27488d87e469c3e26`, and recorded
  `feature_truth_count=0` plus `dispatch_stopped=true`.
- Read-only recovery verification found a clean production worktree, API,
  MinIO and PostgreSQL healthy, processing worker and Temporal running, and
  public live/ready endpoints returning `200`. The failed bootstrap container
  remained only as an exited diagnostic container; it did not hold work or
  mutate feature truth.
- This is safe rollback evidence, not deployment or feature closeout. No new
  desktop application was installed because production still runs the previous
  release.

## Runtime-Secret Readability Root Cause And Hotfix Boundary

- The deploy creates new runtime database and media-storage credentials as
  owner-only regular files. Production Compose uses file-backed secrets, which
  are bind-mounted with their host ownership.
- The long-syntax `uid`, `gid` and `mode` declarations did not change those
  mounts. This matches the
  [Docker Compose services reference](https://docs.docker.com/reference/compose-file/services/):
  remapping is not implemented for a `file` secret source.
- A tempting environment-backed replacement was rejected after an executable
  production probe: Compose `5.0.2` materialized it for a writable fixture but
  rejected both read-only variants. Long-running media/maintenance services
  therefore keep their required read-only root filesystems.
- The bounded fix keeps file-backed secrets, changes only the five generated
  credentials to owner/private-group mode `0640`, and gives that private group
  only to the six non-root services that consume them. Before changing a file,
  deploy requires the configured GID to equal the deploy user's private primary
  group, resolve to exactly one primary account, and contain no foreign member.
- The exact helper ran on production against a disposable non-sensitive file:
  owner/group/mode/link facts were `1001:1001:640:1`; result `pass`; residue
  `0`. A separate read-only, no-network, cap-dropped container probe confirmed
  `uid=100`, primary `gid=101`, supplemental private group access and residue
  `0`.
- Negative executable regressions reject a system GID, a GID different from
  the deploy user's primary group, a group with a foreign member, a group shared
  by two primary accounts, and a non-numeric value.
- Hotfix worktree:
  `codex/hotfix-099-runtime-secret-readability`, base
  `13fe923421df60da77a0b936a8b04cd63db6f891`. Feature-104 commit `b0b1a240` is
  an ancestor of that base; unfinished feature-103 commit `ad5992ea` is not and
  is not transferred. Detached/dirty worktrees and feature 100 remain
  untouched.

## Runtime-Secret Hotfix Validation

- Focused deployment/Compose/product-boundary regression set: `58 passed`;
  the only warning is the pre-existing Starlette `httpx` deprecation warning.
- Shell and configuration gates: Ruff, `bash -n`, ShellCheck with the two
  repository-known informational exclusions, `git diff --check`, and Compose
  rendering for the `operations` profile all passed.
- Fresh canonical `infra/scripts/ci-local.sh` on the final code diff passed:
  macOS build and contract validation, `643/643` macOS tests, server
  `1724 passed, 21 skipped` in `556.48s`, Ruff, Python compile, production
  Compose rendering, and deployment-evidence scan.
- Independent read-only review reported no P0-P3 findings. It confirmed the
  private-group fail-closed checks, owner/hard-link validation before mutation,
  preserved non-root/read-only/capability boundaries, and guarded rollback.
- Remaining portability limitation: this production-targeted helper depends on
  GNU/Linux `getent` and `stat -c`. Supporting a macOS or minimal BusyBox deploy
  host would require a separate adaptation; the current production host meets
  the validated contract.
