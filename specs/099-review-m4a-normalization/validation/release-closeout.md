# Release Closeout: Feature 099

**Date**: 2026-07-16

**Risk / validation lane**: release / deploy

**Current verdict**: immutable `v2026.07.16.4` is published and deployed at
the tagged SHA with automatic dispatch open. T114 is complete. T115 remains
open for the outstanding post-deploy recovery, backfill and browser/embedded
user-path receipts; T116 remains open for final tracker reconciliation and
cleanup. The standalone feature 097 security scan remains deferred.

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

## Runtime-Secret Hotfix Integration And Release Candidate

- Approved and verified exact hotfix commit:
  `801e4cde4d8903e50c7652b29a4a7db123b0b70b`.
- Hotfix PR: [#3474](https://github.com/yshishenya/crisp/pull/3474), merged into
  `master` at exact SHA
  `f0fbd18bb7cf18410da16bda2f6ca7177b40ce98` on 2026-07-15 at 14:29:30 UTC.
- Fresh fetch and ancestry checks confirm both the hotfix commit and merge SHA
  are ancestors of `origin/master`. No duplicate commit, branch or PR was
  created after the repeated integration approval.
- Live tag and GitHub Release checks found no `v2026.07.16.*` release. The next
  free Europe/Moscow CalVer is `v2026.07.16.1`.
- The clean release worktree started from exact `origin/master` SHA
  `e63cd9394ba449bd5e1424a3dfe90de9b8d98cb6`; unrelated detached and dirty
  worktrees were not changed.
- That master SHA also contains merged PR #3475 after the hotfix. Its path set
  is limited to `.specify/` bootstrap/managed metadata and agent guidance; it
  has no `apps/` or production-runtime `infra/` diff. The release changelog
  names this tooling-only scope instead of silently omitting it.
- Command: `./scripts/prepare-release.sh 2026.07.16.1`.
- Result: success. The runtime-secret hotfix entries moved from `[Unreleased]`
  into `[2026.07.16.1] - 2026-07-16`; no commit, tag or GitHub Release was
  created by the preparation command.
- Tag target will be the exact `master` merge SHA of the release-preparation
  PR. Production deploy was blocked until explicit approval for this validated
  candidate; that approval is now recorded below. PR merge, publication and
  the approved execute path remain as separate gates.
- Focused current-master deployment and Compose regression command:
  `cd apps/server && uv run --extra dev pytest -q tests/integration/test_compose_hardening.py tests/integration/test_deployment_readiness_gates.py`.
  Result: `51 passed, 1 warning` in `2.38s`; the warning is the pre-existing
  Starlette `httpx` deprecation warning.
- Fresh canonical candidate gate: `infra/scripts/ci-local.sh` returned
  `ci_local_result=pass`; macOS build, `643/643` tests and contract validation
  passed; server `1724 passed, 21 skipped` in `444.78s`; Ruff, Python compile,
  production Compose rendering and the seven-file deployment evidence scan
  passed.
- The local PostgreSQL RLS boundary remained truthfully blocked with
  `reason=postgres_test_database_required`; it does not claim live production
  enforcement. The production migration, role identity and RLS receipts remain
  required during T114/T115.
- Independent read-only review found no Critical/High defect. It confirmed the
  fail-closed private-group checks and preserved non-root/read-only/capability
  boundaries. Production execute must still prove real filesystem access,
  consumer group identity and absence of unexpected ACLs before closeout.
- Deployment plan command:
  `infra/scripts/cd-remote.sh --dry-run --branch codex/release-v202607161-099-runtime-secret-readability`.
  Result: `deploy_result=dry_run`, `local_ci=required`; the plan includes clean
  worktree/branch/SHA checks, backup and restore rehearsal, the new
  `runtime_secret_group` gate, migration/role/image/worker gates, guarded
  rollback, smoke, public health and required post-deploy receipts. No remote
  or production state was changed by this command.
- Fresh read-only production baseline before approval: runtime SHA
  `e77f942bf178862905ee98b27488d87e469c3e26`, clean worktree, five of five
  Compose services running with zero unhealthy, migration
  `0021_calendar_auto_context_match`, and public live/ready HTTP `200`.
  Production reports deploy GID `1001`, the required GNU host tools and a
  private primary-group shape accepted by the new fail-closed gate. No runtime,
  schema, secret file or remote Git state was changed by this inspection.

## Explicit Release Approval And Preparation PR

- On 2026-07-16 the user explicitly authorized the exact validated action:
  `выпускай v2026.07.16.1 и выкатывай на production`.
- Release-preparation commit:
  `1c2627765589b72b0e9b52ecbcbd27fa428d7f61`; it contains only
  `CHANGELOG.md`, `docs/current-product-status.md` and this append-only release
  evidence. `git diff --cached --check` passed before commit.
- The commit was pushed to
  `codex/release-v202607161-099-runtime-secret-readability` and opened as
  [PR #3476](https://github.com/yshishenya/crisp/pull/3476) against `master`.
  The initial GitHub read-back reports exact head `1c262776...`, three changed
  files and a clean merge state.
- PR #3476 references T114–T116 without closing them. Those tasks remain open
  until deployment, production user-path proof and cleanup receipts exist.

## `v2026.07.16.2` Smoke-RLS Blocker And Safe State

- Release `v2026.07.16.2` was published from exact release-preparation merge
  SHA `378ee2c142f210f708763a79d2c50c4171b419b8` after the restricted media-role
  schema-read hotfix merged through PR #3522.
- The approved deploy applied additive migration `0022_playback_normalization`,
  validated the media runtime and started the worker, then stopped while
  production smoke tried to create its synthetic organization through the
  ordinary API database role. Strict RLS correctly denied that maintenance
  write.
- Compatibility rollback kept the `.2` source and additive schema, disabled
  normalization capability and automatic dispatch, removed the media worker,
  and preserved public live/ready HTTP `200`. Read-back reported zero feature
  dispatch and zero smoke residue. This was a safe incomplete rollout, not
  production acceptance.

## Smoke-RLS Hotfix Validation And Integration

- The bounded fix adds migration `0023_production_smoke_setup`. Only the
  dedicated maintenance role may create the deterministic smoke identity;
  AuthSession issuance and upload remain under `twobrain_rec_app` with the
  exact request tenant context.
- The smoke session TTL is 600 seconds. Its token is created atomically as a
  private `0600` file and is not sent through stdout, environment variables or
  command arguments.
- Cleanup discovers partial-upload rows from the deterministic identity,
  removes related normalization/data rows and the entire synthetic workspace
  MinIO prefix, then verifies database and object residue. Production smoke now
  completes cleanup while automatic dispatch is closed; dispatch opens only
  after the smoke command succeeds.
- Final canonical gate on the exact hotfix diff:
  `infra/scripts/ci-local.sh` returned `ci_local_result=pass`; macOS `643/643`,
  server `1727 passed, 24 skipped`, contract validation, Ruff, Python compile,
  Compose rendering and deployment-evidence scan passed.
- A disposable PostgreSQL 17 run passed the RLS/migration/normalization suite
  `25/25` with cluster residue zero. Focused smoke/RLS/cleanup tests passed;
  `bash -n` and `git diff --check` passed.
- Independent review found and then verified the closure of one worker/cleanup
  race. Its final verdict was PASS with no remaining actionable findings.
- Approved hotfix commit:
  `8c10c2dda49ed49fcbac567aeb82bda0b2d12f25`. PR
  [#3524](https://github.com/yshishenya/crisp/pull/3524) merged into `master`
  at exact SHA `ff34413994d8e15f64149e7470db6539f2d7180c` on 2026-07-16.

## `v2026.07.16.3` Release Candidate

- The user explicitly authorized the full action on 2026-07-16:
  `сделать commit, push, PR и merge hotfix 099 деплой в прод`.
- Local/remote tag, GitHub Release and release-branch checks confirmed that
  `v2026.07.16.3` and
  `codex/release-v202607163-099-production-smoke` were free.
- The clean release worktree started from exact fetched `origin/master` SHA
  `ff34413994d8e15f64149e7470db6539f2d7180c`; unrelated dirty worktrees were
  not modified.
- Command: `./scripts/prepare-release.sh 2026.07.16.3`.
- Result: success. Concrete smoke-RLS hotfix entries moved from `[Unreleased]`
  into `[2026.07.16.3] - 2026-07-16`. The command created no commit, tag or
  GitHub Release.
- Deployment plan command:
  `infra/scripts/cd-remote.sh --dry-run --branch codex/release-v202607163-099-production-smoke`.
  Result: `deploy_result=dry_run`, `local_ci=required`, remote path
  `/opt/projects/2brain-rec`. The generated order keeps production smoke before
  `automatic_dispatch_open` and retains branch/SHA sync, backup, restore,
  secret, migration, role, image, worker, rollback, health and post-deploy
  evidence gates. Dry-run changed no production state.
- T114–T116 remain open. The release PR, immutable tag/Release, production
  execute, E2E and cleanup receipts are still required before feature closeout.

## `v2026.07.16.3` Production Blocker And Safe Recovery

- Release-preparation PR
  [#3525](https://github.com/yshishenya/crisp/pull/3525) merged at exact SHA
  `c235cdd1bee6b706b9df49239e9da8d390a014c5`. Immutable release
  [v2026.07.16.3](https://github.com/yshishenya/crisp/releases/tag/v2026.07.16.3)
  targets that SHA.
- The approved execute path completed its local gate and remote backup at
  `/opt/projects/2brain-rec/backups/20260716T030558Z`, then reached additive
  schema `0023_production_smoke_setup`.
- The disposable RLS probe stopped with `reason=rls_probe_command_failed` and
  `error_type=ProgrammingError`: the verifier tried to create the already
  existing cluster-wide `twobrain_rec_maintenance` role. The guarded
  compatibility rollback passed before automatic dispatch opened. Runtime
  remained at exact SHA `c235cdd1...`, normalization dispatch remained closed,
  and the media worker remained absent.
- Recovery inspection found two additional readiness faults. The processing
  worker could not read the mode-`0600` MediaScribe file-backed secret as its
  non-root UID, and dual-network Temporal had selected only its media-network
  address, so the processing worker received connection refusals.
- The bounded recovery changed no secret values: it verified the MediaScribe
  secret inode/owner/hard-link metadata, assigned the already validated private
  runtime group with mode `0640`, disconnected the current Temporal container
  from the media network, restarted Temporal, and recreated the processing
  worker. Production returned to a safe closed state.
- Fresh read-only verification on 2026-07-16 reported exact runtime SHA
  `c235cdd1...`; Temporal and processing worker both `running`, restart count
  `0`; `temporal operator cluster health --address rec-temporal:7233` returned
  `SERVING`; the processing task queue had an active workflow poller; and
  public live/ready returned HTTP `200`. The current `.3` container still
  refuses `127.0.0.1:7233`, which is direct evidence for the new explicit
  all-interface bind and loopback health gate. This is recovery evidence, not
  successful deployment or T114–T116 closeout.

## `v2026.07.16.4` Hotfix Validation Before Integration

- Clean hotfix worktree branch:
  `codex/hotfix-099-rls-temporal-production`, based on exact
  `c235cdd1bee6b706b9df49239e9da8d390a014c5`. Unrelated dirty worktrees remain
  untouched.
- The RLS verifier now accepts the existing maintenance role only when owner
  and probe URLs identify the same `twobrain_rec_rls_*` disposable database.
  Static URL/class/role checks and cluster-role attribute/membership checks run
  before Alembic. Membership is rejected in both directions. Runtime passwords
  are read by the verifier from mounted regular files and are not passed
  through Docker or shell arguments, or inherited from the parent shell.
- A real disposable PostgreSQL regression first grants the maintenance role to
  another role and proves rejection before the Alembic table exists. It then
  removes that unsafe membership, runs the complete direct-SQL RLS verifier,
  and passes. Exact role OID, password hash, role configuration, attributes and
  both membership directions are unchanged; the scratch database residue is
  zero. The synchronized runtime-role bootstrap reverse-membership regression
  also passes.
- Every pre-existing runtime, PostgreSQL and MinIO file-backed secret now goes
  through the same fail-closed owner/regular-file/single-hard-link/private-group
  gate. The gate enforces mode `0640` and rejects the extended-ACL marker before
  mutation. Generated database/media credentials continue through the same
  helper. All non-root consumers, including `rec-migrate`, receive the numeric
  private group explicitly.
- Temporal explicitly binds `0.0.0.0` across both isolated Compose networks.
  Temporal must be healthy before API/workers start; the processing worker is
  healthy only when its exact bounded identity has both workflow and activity
  pollers. Deploy compares restart counts with the pre-deploy baseline, checks
  both Temporal networks, and repeats the full readiness check immediately
  before final success and during compatibility rollback.
- Compatibility rollback first proves the current hotfix runtime healthy with
  dispatch closed. If that runtime cannot recover, a previous-SHA fallback is
  allowed only when the previous, expected and live schema heads are identical.
  It builds the previous images before stopping any running service, restores
  single-network Temporal, proves cluster health plus exact workflow/activity
  pollers, and recreates the API with dispatch closed. Executable regressions
  cover both successful fallback and rejection when schemas are incompatible.
- Focused contract/integration/unit suite: `78 passed, 11 skipped`; only the
  pre-existing Starlette/httpx deprecation warning remains. Separate real
  PostgreSQL 14 existing-role and bootstrap regressions each passed. An
  isolated Temporal dev server executable proof registered the exact identity
  `graf-processing:hotfix-099-temporal-proof` as both workflow and activity
  poller and returned `pass`.
- Ruff, Ruff formatting, Python/shell syntax, ShellCheck with the two
  repository-known remote-source exclusions, production/development Compose
  rendering and `git diff --check` passed.
- Final canonical `infra/scripts/ci-local.sh` returned
  `ci_local_result=pass`: macOS build, `643/643` tests and contract validation;
  server `1741 passed, 25 skipped` in `401.97s`; Ruff, Python compile,
  production Compose rendering and the seven-file deployment-evidence scan all
  passed. The local RLS boundary truthfully remained blocked with
  `reason=postgres_test_database_required`; the separate disposable
  PostgreSQL receipt above supplies the destructive local proof, while the
  remote deploy must still prove production truth.
- Final independent review inspected the complete tracked diff and both new
  files. Verdict: `APPROVED`, with `0` Critical, `0` High and `0` Medium
  findings; all earlier rollback findings are closed.
- Material pre-integration limitation: the local Docker daemon is unresponsive,
  so the exact pinned `temporalio/auto-setup:1.27.2` dual-network container was
  not booted locally. It was not restarted because that could disrupt unrelated
  user containers. Compose rendering, the isolated Temporal API proof and the
  read-only production incident receipts cover the code path; the remote deploy
  remains fail-closed and must prove the exact pinned container, both networks,
  loopback health and both pollers before it can report success.
- Integration approval, PR checks and the separate release/deploy gate remain
  required. No commit, push, PR, merge or production mutation has been made by
  this hotfix worktree yet.

## `v2026.07.16.4` Release Candidate

- Approved hotfix commit `480c771434a778a415eaef80bebcad25766d8272` was merged
  through [PR #3526](https://github.com/yshishenya/crisp/pull/3526) into
  `master` at exact SHA `4e462893f1c546b6bb17d5e274d6f29e60b0c770`.
  A fresh fetch confirmed the hotfix commit is an ancestor of that fetched
  `origin/master`.
- Local and remote tag checks found no `v2026.07.16.4`; the new clean release
  worktree branch `codex/release-v202607164-099-rls-temporal` starts from exact
  merged SHA `4e462893...`. Unrelated dirty worktrees remain untouched.
- Command: `./scripts/prepare-release.sh 2026.07.16.4`. Result: pass; the
  verified hotfix entries moved from `[Unreleased]` into the dated CalVer
  section. No commit, tag, GitHub Release, remote runtime or production state
  was changed.
- The exact hotfix code gate immediately before integration passed: macOS
  `643/643`; server `1741 passed, 25 skipped`; Ruff, Python compile, Compose
  rendering and deployment-evidence scan passed. The release-prep diff is
  documentation-only.
- Command: `infra/scripts/cd-remote.sh --dry-run --branch
  codex/release-v202607164-099-rls-temporal`. Result: `deploy_result=dry_run`,
  `local_ci=required`; it enumerates clean-worktree/SHA sync, backup and
  restore, secret permissions, RLS, Temporal/processing worker readiness,
  production smoke, dispatch, guarded rollback and post-deploy proof gates.
  The dry-run changed no remote or production state.
- A separate fresh release/deploy approval remains mandatory before committing
  the release-prep branch, merging it, creating immutable `v2026.07.16.4` and
  running `--execute`.

## T114 — `v2026.07.16.4` Published Production Deploy

- The user explicitly authorized the release and production deployment on
  2026-07-16, including subsequent closeout actions without additional
  confirmation.
- Release-preparation commit
  `954b44b9fa42c19daff32d8a9b9efc5249d833a8` was merged through
  [PR #3527](https://github.com/yshishenya/crisp/pull/3527) at exact SHA
  `221a717ebc2c031e0fdc678705d50d8ee6592740`.
- Annotated tag `v2026.07.16.4` peels to that exact merge SHA. The stable
  Russian GitHub Release is
  [v2026.07.16.4](https://github.com/yshishenya/crisp/releases/tag/v2026.07.16.4).
- `infra/scripts/cd-remote.sh --dry-run --branch
  codex/deploy-v202607164-099` passed before execution and changed no
  production state.
- The approved `--execute` path reran the canonical local gate successfully:
  macOS `643/643`; server `1741 passed, 25 skipped`; Ruff, Python compile,
  Compose rendering and the deployment-evidence scan passed. The local RLS
  boundary remained truthfully blocked without a disposable PostgreSQL URL;
  the production deploy ran its separate disposable RLS proof.
- Production result: `deploy_result=pass`, deployed/runtime SHA
  `221a717ebc2c031e0fdc678705d50d8ee6592740`, readiness
  `infra_smoke_ready`, and metadata-only backup reference
  `20260716T050517Z`.
- The remote gate passed runtime secret/readability checks, backup and restore
  rehearsal, migration head `0023_production_smoke_setup`, runtime database
  and media identities, disposable RLS direct-SQL probes, Temporal and both
  processing/media worker readiness checks, synthetic smoke plus residue-zero
  cleanup, and automatic dispatch opening. The worker capability matrix and
  full-decode gate also passed.
- Read-only post-deploy confirmation found the exact tagged SHA, all required
  API, PostgreSQL, MinIO, Temporal, processing-worker and media-worker
  services healthy, and public `/api/v1/health/live` and
  `/api/v1/health/ready` passing.
- Docker Compose emitted its known informational warning that file-secret
  `uid`, `gid` and `mode` declarations are not applied to bind-mounted files.
  The deployment uses the separately validated private runtime group and
  host-file permission gate; no secret value or path is recorded here.
- This completes T114. It does not substitute for T115 production user-path
  evidence, and it does not complete deferred feature 097.
