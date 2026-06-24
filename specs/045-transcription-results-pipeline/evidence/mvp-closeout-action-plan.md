# MVP Closeout Action Plan

**Feature context**: `045-transcription-results-pipeline`
**Date**: 2026-06-24

## Purpose

This plan keeps the full MVP goal explicit after the local `045`
implementation pass. It is intentionally broader than `045`, because a full MVP
claim requires current runtime and production evidence, not only local tests.

## Current Truth

- `045` is locally implementation-ready and closes the recording-to-transcript
  result loop in tests and fixture runtime checks.
- `044` remains the separate real echo/noise suppression track.
- Full MVP is not yet proven because release/deploy, post-deploy production
  behavior, clean low-leakage desktop proof, and product-decision evidence are
  still missing.
- Commit, push, PR, merge, installer replacement, and production deploy execute
  remain approval-gated actions.

## Step-By-Step Closeout Plan

### Step 1: Freeze The 045 Boundary

**Status**: Ready locally.

Required evidence:

- `commit-manifest.md` names the intended 045 include set.
- `pr-readiness.md` confirms 044 and internal agent planning files are excluded
  unless explicitly approved.
- `git status --short --untracked-files=all` has no unexpected paths outside
  the include/exclude boundary.

Exit criteria:

- 045 can be committed without silently mixing `044` AEC/noise work or local
  agent-only planning artifacts.

### Step 2: Revalidate Local Spec Kit Gates

**Status**: Ready locally; rerun after any code change.

Required evidence:

- Spec Kit prerequisites resolve to
  `specs/045-transcription-results-pipeline`.
- All 045 checklists and tasks are complete.
- `git diff --check` passes.
- Focused macOS validation from `quickstart.md` passes.
- Focused server validation from `quickstart.md` passes.
- One-hour orchestration benchmark passes.
- Privacy/secret scan over the proposed 045 include set finds no real
  credentials, signed URLs, raw audio, private meeting content, or private
  transcript content.

Exit criteria:

- No local regression or evidence-format issue remains before PR preparation.

Current safe rechecks:

- Spec Kit prerequisites still resolve to
  `specs/045-transcription-results-pipeline`.
- 045 checklists and tasks remain fully complete.
- `git diff --check` passes.
- Web cabinet fixture runtime was rechecked with bundled Playwright and passed
  list, ready, processing, partial, failed, desktop list/detail, and mobile
  list/detail routes; unauthenticated `/meetings` still returns
  `401 missing_auth_context`.
- Web cabinet Russian-first polish was rechecked with bundled Playwright and
  installed Chrome. The 9-page fixture run passed with no visible legacy English
  launch labels, no `Политика workspace` copy, no horizontal overflow, and no
  clipped status chips. Output:
  `/tmp/2brain-rec-045-web-cabinet-ru-20260624c`.
- Post-desktop-preflight web cabinet focused suite recheck passed:
  `py_compile` passed and the focused cabinet contract/integration/unit suite
  passed, 26 tests, 0 failures, 1 warning.
- Post-evidence-sync web cabinet browser runtime recheck passed: temporary
  fixture server plus bundled Playwright/installed Chrome covered 9 synthetic
  desktop, embedded desktop, and mobile pages with `health=200`,
  unauthenticated `/meetings=401`, no missing required Russian launch/result
  labels, no visible forbidden legacy copy, no horizontal overflow, no clipped
  chips, and `failures=[]`. Output:
  `/tmp/2brain-rec-045-web-cabinet-ru-20260624d`.
- Latest web cabinet browser runtime recheck passed: temporary fixture server
  plus bundled Playwright/installed Chrome covered the same 9 desktop, embedded
  desktop, and mobile pages with `health=200`, unauthenticated
  `/meetings=401`, no missing required Russian labels, no visible forbidden
  legacy copy, no horizontal overflow, no clipped `.chip` or provider pill
  elements, and `failures=[]`. Output:
  `/tmp/2brain-rec-045-web-cabinet-ru-20260624f`; the server was stopped and
  port `8765` was free.
- Focused macOS validation was rechecked and passed, 73 tests, 0 failures.
- Focused server validation plus the synthetic one-hour orchestration benchmark
  was rechecked and passed, 40 tests, 0 failures, 1 deprecation warning.
- After the desktop preflight evidence sync and `git fetch origin --prune`,
  focused macOS validation was rechecked again and passed, 73 tests, 0
  failures.
- After the desktop preflight evidence sync and `git fetch origin --prune`,
  focused server validation plus the synthetic one-hour orchestration benchmark
  was rechecked again and passed, 40 tests, 0 failures, 1 deprecation warning.
- After the desktop preflight evidence sync, canonical local CI was rechecked
  again and passed with `ci_local_result=pass`: server tests passed, 545 tests,
  4 skipped, 90 warnings; server lint, Python compile, production compose
  rendering, and deployment evidence scan passed.
- After the post-evidence-sync web runtime pass, deploy dry-run was rechecked
  and passed with `deploy_result=dry_run`; this did not deploy or mutate
  production.
- After the post-evidence-sync web runtime pass, the 045 include-set patch was
  regenerated relative to `origin/master` from 36 tracked paths plus 25
  untracked include paths, and `git apply --check` passed in a detached
  temporary worktree at `origin/master` `a89cf91`. The temporary worktree was
  removed after the check.
- Remote/tracker state was rechecked after fetch: `origin/master` remained
  `a89cf91`, branch divergence remained `4 0`, no PR exists for the branch, no
  open `feature:045` issues exist, and 52 closed `feature:045` issues remain
  recorded as #1465-#1516.
- Desktop permissioned proof harness `--self-test` passed. This confirms the
  harness parser/metadata validators are ready.
- Current branch desktop non-recording preflight passed after a fresh ad-hoc
  build: packaged app launch was observed, idle and quit phases passed, no
  helper process or HAL probe was observed, no unexpected app process remained,
  and no thermal/performance warning was recorded. This confirms build/launch/
  idle/quit only; current-branch permissioned Record/Stop and artifact proof
  remain approval-gated and unproven.
- Canonical local CI was rechecked and passed with `ci_local_result=pass`:
  server tests, lint, Python compile, production compose rendering, and
  deployment evidence scan passed. RLS hardening used the safe no-Postgres
  default boundary in canonical CI and did not inspect live production.
- Canonical local CI was rechecked again after the playback/product truth sync
  and passed with `ci_local_result=pass`: server tests, lint, Python compile,
  production compose rendering, and deployment evidence scan passed.
- Canonical local CI was rechecked after the Russian-first web cabinet follow-up
  and passed with `ci_local_result=pass`: server tests passed, 545 tests, 4
  skipped, 90 warnings; server lint, Python compile, production compose
  rendering, and deployment evidence scan passed.
- A separate RLS disposable Postgres proof passed on an isolated local
  `postgres:17-alpine` database with `rls_validation_result=pass`,
  `destructive_probe_database=disposable`, `ready_for_production_truth=true`,
  and `probe_suite=direct_sql_rls_probes`.
- Focused cabinet playback/timestamp truth tests passed. They prove timestamp
  labels, speaker/source-role mapping, and playback shell presence, but do not
  prove interactive audio playback, waveform, or transcript-segment seek.
- `playback-timestamp-seek-preflight.md` records the safe handoff for a
  possible `046-meeting-playback-timestamp-seek` slice and explicitly says not
  to start that implementation from the dirty 045 worktree unless the owner
  approves a stacked branch.
- Continuation recheck on 2026-06-24 passed the current safe local gate set:
  Spec Kit prerequisites, completed tasks/checklists, `git diff --check`,
  include/exclude boundary, focused macOS tests, focused server tests plus the
  one-hour orchestration benchmark, focused web cabinet tests, and the
  temporary 9-page Playwright fixture runtime. The fixture server was stopped
  after the browser check.
- Continuation full local CI on 2026-06-24 passed with `ci_local_result=pass`.
  Server tests passed, 545 tests, 4 skipped, 90 warnings; server lint, Python
  compile, production compose rendering, and deployment evidence scan passed.
- Continuation desktop safe preflight on 2026-06-24 passed: manual gate
  `--self-test` passed, packaged app launch/idle/quit passed, and no helper,
  unexpected app process, HAL probe, thermal warning, or performance warning
  was observed. This still did not prove permissioned Record/Stop or package
  creation.
- Permissioned installed-current-branch desktop proof on 2026-06-24, after
  explicit owner approval, proved a real speakerphone/high-leakage class:
  granted microphone and Screen/System Audio permissions, active recording,
  user-requested Stop, saved `local_mic` plus `remote_speaker` tracks, and
  upload queue creation. The manifest was `degraded` with `leakage_unproven`,
  which is expected for speaker playback and does not satisfy the older clean
  `saved` / `ready` artifact gate. Clean low-leakage artifact proof and
  post-deploy 045 auto-start proof remain open.
- Local server replay of that same speakerphone/degraded artifact on
  2026-06-24 proved the current branch accepts the real artifact bytes through
  upload, finalize, and processing dispatch with fake storage and fake Temporal:
  finalize returned `200`, the upload session became `finalized`, and processing
  reached `workflow_started`. This did not use production or live MediaScribe,
  and audio analysis showed the incoming/system track was effectively silent;
  the later fresh production probe superseded that specific system-audio concern
  for one known-audible speakerphone run.
- Fresh production probe on 2026-06-24 proved a stronger speakerphone class:
  a v3 `failed` / `leakage_detected` package with meaningful microphone and
  incoming/system audio uploaded and finalized in production, then reached
  live MediaScribe-backed `processed` review after a targeted manual processing
  pickup. Production was still on `master` commit `e312d25`, not 045, so this
  does not prove 045 auto-start/reuse after finalize. The live result also
  exposed segment-level speaker/source-role misalignment; the current branch
  now has a regression fix that matches transcript and diarization by
  normalized `(sequence, source_role)`, but that fix still needs post-deploy
  production proof before MVP-quality diarization can be claimed.
- Code-level audit follow-up on 2026-06-24 corrected the desktop sync contract
  for processing failed/blocked states: those states now keep review links
  available so web and desktop review can show the same safe failed/blocked
  truth, while transcript/diarization content remains unavailable. The old
  recording-sync conflict expectation was updated, and focused server,
  recording-sync/cabinet contract, focused macOS, and full local CI gates
  passed after the fix.
- Latest MVP closeout continuation recheck passed focused macOS validation
  (73 tests), focused server validation including the source-role regression
  suite (44 tests), the one-hour orchestration benchmark, the 9-page web cabinet
  browser fixture runtime (`/tmp/2brain-rec-045-web-cabinet-ru-20260624g`),
  desktop manual-gate self-test, repeat non-recording desktop preflight, canonical
  local CI (`546 passed`, `4 skipped`, `90 warnings`), and deploy dry-run. The
  first desktop preflight attempt stopped on a pre-launch `coreaudiod` baseline
  CPU blocker and passed on repeat after the environment quieted. Latest boundary
  check at that point was 65 included / 21 excluded / 0 unexpected.
- Post-evidence-sync closeout recheck kept the branch approval-ready locally:
  boundary 65 included / 21 excluded / 0 unexpected, `git diff --check`,
  `github-issue-canon`, cabinet/source-role regression tests, focused macOS
  tests, canonical local CI, and deploy dry-run all passed. GitHub still has no
  PR for this branch and no open `feature:045` issues.
- Local metadata-only recording manifest scan on 2026-06-24 found old `v2`
  `saved` / `ready` packages from 2026-06-10 but no fresh/current-branch `v3`
  clean low-leakage `saved` / `ready` package. The low-leakage/headphones proof
  therefore still needs a new trusted current-branch recording or explicit MVP
  deferral.
- Runtime continuation recheck passed the web cabinet 9-page browser fixture
  suite again (`/tmp/2brain-rec-045-web-cabinet-ru-20260624h`) and passed desktop
  safe non-recording preflight again. This strengthens local interface/runtime
  confidence but does not close production deploy, post-deploy e2e, or clean
  low-leakage recording proof.
- Metadata-only desktop app UI inspection launched the installed app, observed
  one frontmost standard `2brain Rec` window plus a menu bar through
  Accessibility, and confirmed clean quit. Pixel screenshot evidence remains
  intentionally absent because the safe capture path was not reliable enough for
  committed evidence.
- Goal continuation on 2026-06-24 rechecked the web cabinet fixture runtime
  again: bundled Playwright/installed Chrome covered 9 desktop, embedded
  desktop, and mobile pages with `health=200`, unauthenticated
  `/meetings=401`, and `failures=[]`. Desktop manual-gate `--self-test`
  passed, while two safe `--preflight` attempts stopped before app launch on
  `baselineCoreaudiodCpuGate`; no app runtime failure or Record/Stop claim is
  made from those blocked attempts. A fresh remote apply rehearsal over
  `origin/master` `a89cf91` passed with 67 included / 21 excluded / 0
  unexpected and patch size 501236 bytes.
- Post-goal-continuation full local gate on 2026-06-24 passed canonical
  `infra/scripts/ci-local.sh` with 546 server tests, 4 skipped, 90 warnings,
  lint/compile/compose/evidence scan green, followed by a non-mutating
  `infra/scripts/cd-remote.sh --dry-run` pass for branch
  `045-transcription-results-pipeline`. This strengthens local PR readiness but
  still does not replace commit/PR/merge/deploy approval or post-deploy
  production e2e proof.

### Step 3: Prove Current-Branch Desktop Runtime

**Status**: Partially proven locally; more proof required.

Required evidence:

- Follow `desktop-permissioned-runtime-proof-plan.md`.
- Prove the current branch app, with granted microphone and Screen/System Audio
  permission, enters active recording and stops with one action across the two
  product-relevant classes:
  - low-leakage/headphones: clean `saved` / `ready` package;
  - speakerphone/high-leakage: structurally valid uploadable package with
    truthful `degraded` or `failed` quality state and meaningful known system
    audio in the incoming/system track.
- Prove the current-branch speaker/source-role alignment fix on production so
  review surfaces do not confuse local microphone vs incoming/system
  attribution.
- Capture only metadata-safe evidence: fresh start/stop events, active
  indicator observation, local recording package metadata, upload queue state,
  and safe blocker codes if anything fails.

Exit criteria:

- The current branch, not only the previously installed app, proves manual
  Record/Stop and package creation for both low-leakage and speakerphone
  operating classes, or the owner explicitly accepts a narrower MVP proof
  matrix.
- A post-deploy 045 production run proves finalize-triggered auto-start/reuse
  without manual processing pickup.

### Step 4: Commit, PR, Review, And Merge 045

**Status**: Approval required.

Required evidence:

- Commit includes only the 045 include set.
- Branch is integrated with current `origin/master`.
- `docs/current-product-status.md` keeps both the newer 036 owner proof and the
  045 pipeline status.
- PR body uses Russian text and `Refs`, not closing keywords, for the
  already-closed `feature:045` issues.
- Focused validations and `git diff --check` are rerun after integration.

Exit criteria:

- Reviewed 045 changes are merged into the release branch without losing the
  source-of-truth status from newer master commits.

### Step 5: Release And Production Deploy

**Status**: Dry-run preflight recorded; approval required for release prep,
push/tag, and deploy execute.

Required evidence:

- `infra/scripts/cd-remote.sh --dry-run` records the intended remote host,
  path, branch, and production gate list.
- `infra/scripts/cd-remote.sh --execute` runs only after approval and only from
  the intended clean branch/ref.
- Deploy evidence is metadata-only and includes pinned SHA, backup reference,
  restore rehearsal, compose/secret scans, production smoke, and live/ready
  health checks.

Exit criteria:

- Production environment is running the intended 045 commit and reports
  `infra_smoke_ready` or stronger metadata-safe proof.

Current safe preflight:

- `infra/scripts/cd-remote.sh --dry-run`: passed locally and reported branch
  `045-transcription-results-pipeline`, remote host `2brain.dev`, remote path
  `/opt/projects/2brain-rec`, local CI required, and production gates for clean
  worktree, branch sync, pinned SHA, remote fetch, backup, restore rehearsal,
  compose secret scan, build/up, runtime secret scan, smoke, and public health.

### Step 6: Prove Production Upload-To-Transcript-To-Review

**Status**: Approval required for production mutation.

Required evidence:

- Follow `production-e2e-proof-plan.md`.
- Use a controlled, non-sensitive test recording.
- Prove upload/finalize, one processing attempt, MediaScribe submission/result
  import, transcript availability, diarization availability, and matching web
  plus desktop review state.
- Record timing metadata for the one-hour processing budget when using an
  approved long recording.

Exit criteria:

- The product value loop is proven in the target environment without exposing
  raw audio, transcript text, credentials, signed URLs, or private meeting
  content.

### Step 7: Make MVP Product Decisions Explicit

**Status**: Decision required.

Required decisions:

- Decide whether PRD-level interactive audio playback with transcript timestamp
  seek is required before the MVP claim, or explicitly defer it from a narrower
  pilot. If required, use `playback-timestamp-seek-preflight.md` as the
  starting handoff for a separate Spec Kit slice after 045 lands.
- Decide whether launchable AI notes/actions are required for MVP or explicitly
  deferred from the MVP claim.
- Decide whether `044` real AEC/noise suppression is required for MVP quality,
  or whether MVP accepts best-available transcription from imperfect recordings
  with truthful quality labels.
- Decide whether signed/notarized production installer evidence is required for
  this MVP milestone or a pilot-only installer is acceptable.

Exit criteria:

- No hidden product promise remains ambiguous in `docs/current-product-status.md`
  or release notes.

### Step 8: Final MVP Completion Audit

**Status**: Not ready.

Required evidence:

- Update `full-mvp-completion-audit.md` after Steps 3-7.
- Every MVP requirement must be `PROVEN` or intentionally deferred with an
  explicit owner decision and follow-up tracking.
- Web cabinet and desktop app must be rechecked on the production or approved
  target environment.

Exit criteria:

- Full MVP can be claimed only when the audit proves the actual product goal,
  not merely the local `045` implementation.
