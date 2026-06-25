# Validation Log: 052 MVP Live Owner Journey And UI Proof

All entries are metadata-only. Do not add raw audio, transcript text, private
meeting titles, generated private outcome text, account identifiers, cookies,
tokens, signed URLs, storage object keys, or private local paths.

## 2026-06-25T16:30Z - Setup Baseline

- branch: `052-mvp-live-ui-proof`
- local head: `efcbea1c7417761db489d07aef23198e49d8313c`
- origin/master: `efcbea1c7417761db489d07aef23198e49d8313c`
- production branch: `master`
- production deployed SHA: `efcbea1c7417761db489d07aef23198e49d8313c`
- public health live: `ok`
- public health ready: `ready`
- source branch: current `master` after post-deploy closeout release
  `v2026.06.25.8`
- dirty e040 boundary: old `045-transcription-results-pipeline` worktree is
  intentionally not used for 052 because it contains unrelated dirty/stale
  files
- Ponytail rule: reuse accepted 051 readiness/browser/docs patterns first; add
  no new architecture unless a P1 proof requires it
- claim boundary: this baseline proves only `infra_smoke_ready`; it does not
  prove fresh owner journey, production stored outcomes, representative
  timing, or UI parity

## Spec Kit Setup

- active spec: `specs/052-mvp-live-ui-proof/spec.md`
- active plan: `specs/052-mvp-live-ui-proof/plan.md`
- active tasks: `specs/052-mvp-live-ui-proof/tasks.md`
- agent context pointer: `AGENTS.md` points to
  `specs/052-mvp-live-ui-proof/plan.md`
- changelog: `[Unreleased]` includes the initial 052 Russian docs entry

## Checklist And Prerequisites

- prerequisites command:
  `SPECIFY_FEATURE_DIRECTORY=specs/052-mvp-live-ui-proof .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`
- prerequisites result: `pass`
- available docs: `research.md`, `data-model.md`, `contracts/`,
  `quickstart.md`, `tasks.md`
- checklist status:
  - `requirements.md`: `16/16 PASS`
  - `ux.md`: `11/11 PASS`
  - `security.md`: `9/9 PASS`
  - `infra.md`: `10/10 PASS`

## Spec Kit Analyze

- 2026-06-25 read-only analyze:
  - prerequisite command:
    `SPECIFY_FEATURE_DIRECTORY=specs/052-mvp-live-ui-proof .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`
  - prerequisite result: `pass`
  - artifacts reviewed: `spec.md`, `plan.md`, `tasks.md`,
    `.specify/memory/constitution.md`
  - task format validation: `44` sequential tasks, no missing task IDs
  - placeholder scan: no unresolved Spec Kit placeholders or
    `NEEDS CLARIFICATION` markers
  - critical issues: `0`
  - high issues: `0`
  - ambiguity count: `0`
  - duplication count: `0`
  - requirement coverage: FR-001 through FR-015 and SC-001 through SC-007 are
    covered through tasks T001 through T044 by owner-journey, timing,
    interface, closeout, forbidden-content, CI, and deploy phases
  - constitution alignment: `pass`
  - implementation gate: `blocker_free`

## GitHub Issue Sync

- 2026-06-25 issue canon ensure:
  - command:
    `python3 .specify/extensions/github-issue-canon/scripts/ensure_issue_canon.py`
  - result: `pass`
  - summary: `github-issue-canon: active/default feature label feature:052`
- 2026-06-25 taskstoissues:
  - existing `feature:052` issues before sync: `0`
  - created issues: `#1800` through `#1843`
  - mapping file: `specs/052-mvp-live-ui-proof/issues.md`
- 2026-06-25 issue canon validate:
  - command:
    `python3 .specify/extensions/github-issue-canon/scripts/validate_issue_canon.py`
  - result: `pass`
  - summary: `github-issue-canon: OK (89 Spec Kit issue(s) checked)`

## Foundational Validation

- 2026-06-25 052 readiness contracts GREEN:
  - command:
    `cd apps/server && uv run --extra dev pytest -q tests/contract/test_mvp_owner_journey_proof_contract.py tests/unit/test_mvp_owner_journey_readiness.py`
  - result: `pass`
  - summary: `8 passed, 1 warning`
  - coverage: 051/052 owner journey gate contract, 052 launch-gap/readiness
    matrix support, 052 UI reference evidence link, and representative timing
    proof guard

## Installed App Evidence

- 2026-06-25 installed app check:
  - app path: `/Applications/2brain Rec.app`
  - version: `2026.06.25.6`
  - bundle identifier: `pro.2brain.rec`
  - codesign verify: `pass`
  - signature: `adhoc`
  - process state: `running`
  - frontmost: `false`
  - window count: `0`
  - active recording media handles: `0`
  - result: `pass`
  - mutation: `none`

## Production Owner Journey Metadata

- 2026-06-25 public owner journey probe:
  - command:
    `python3 specs/052-mvp-live-ui-proof/evidence/production-owner-journey-probe.py`
  - result: `blocked`
  - public health live: `ok`
  - public health ready: `ready`
  - owner review proof: `blocked_without_OWNER_SESSION_COOKIE_and_OWNER_MEETING_ID`
- 2026-06-25 production DB metadata probe:
  - meetings total: `17`
  - media revisions total: `17`
  - processing workflows total: `1`
  - processing results total: `1`
  - transcript segments total: `4`
  - diarization segments total: `3`
  - outcome sets total: `0`
  - outcome items total: `0`
  - processed candidate ref: `6adcee6d4e`
  - processed candidate duration seconds: `31`
  - processed candidate workflow seconds: `8`
  - processed candidate transcript status: `available`
  - processed candidate diarization status: `available`
  - processed candidate speaker count: `2`
  - accepted/not-submitted recordings include `manifest`, `microphone`, and
    `system` track artifacts, so missing dual-track artifacts are not the
    normal-path blocker
- 2026-06-25 production internal health:
  - status: `ready`
  - processing: `disabled`
  - temporal: `not_required`
  - mediascribe: `configured`
  - finding: production `rec-api` is not dispatching processing workflows on
    upload finalize; accepted recordings can remain `not_submitted`

## Normal-Path Blocker Fix

- 2026-06-25 fix:
  - file: `infra/docker-compose.yml`
  - change: production `rec-api` now enables processing, points to
    `rec-temporal:7233`, and starts after Temporal is available
  - secret boundary: `rec-api` does not mount the MediaScribe key; only
    `rec-processing-worker` receives it because the worker performs
    MediaScribe calls
- 2026-06-25 focused validation:
  - command:
    `cd apps/server && uv run --extra dev pytest -q tests/integration/test_mvp_launch_status_truth.py tests/integration/test_compose_hardening.py tests/integration/test_finalize_processing_autostart.py`
  - result: `pass`
  - summary: `18 passed, 1 warning`

## UI Runtime And Reference Evidence

- 2026-06-25 KRISP clean-room reference:
  - inspected existing Chrome tab without recording private transcript content
  - observed custom-controlled audio element with `cross-origin-url` source,
    loaded duration, visible play/pause interaction, persistent bottom player,
    speaker lanes with percentages, speed control, and assign-speakers area
- 2026-06-25 052 browser runtime verifier:
  - command:
    `NODE_PATH="${CODEX_NODE_MODULES:-node_modules}" "${CODEX_NODE_BIN:-node}" specs/052-mvp-live-ui-proof/evidence/browser-runtime-check.cjs`
  - result: `pass`
  - summary: `failures=[]`
  - coverage: web desktop, web mobile, embedded desktop, embedded mobile,
    playback shell, timestamp seek, speaker timeline rows, stored outcomes,
    and overflow guard
- 2026-06-25 production web cabinet live check:
  - `/meetings` page was available in Chrome
  - meeting detail navigation redirected to `/login?error=missing_auth_context`
  - result: owner-review UI proof remains `blocked`
- 2026-06-25 installed macOS app UI check:
  - process restarted with no active recording audio file handles
  - window captured by system window id
  - visible state: local meetings/actions sidebar plus `Нужен вход в кабинет`
    recovery state
  - result: native shell avoids false-green cabinet status, but owner-review
    embedded proof remains blocked by expired/missing auth session
- 2026-06-25 focused UI validation:
  - command:
    `cd apps/server && uv run --extra dev pytest -q tests/unit/test_cabinet_web_shell.py tests/integration/test_mvp_launch_status_truth.py tests/integration/test_compose_hardening.py tests/integration/test_finalize_processing_autostart.py`
  - result: `pass`
  - summary: `30 passed, 1 warning`
  - command:
    `swift test --package-path apps/macos --filter DesktopCabinetWorkspaceTests`
  - result: `pass`
  - summary: `24 tests, 0 failures`

## Readiness And Status Reconciliation

- 2026-06-25 production baseline recheck:
  - public live: `ok`
  - public ready: `ready`
  - production branch: `master`
  - production SHA: `efcbea1c7417761db489d07aef23198e49d8313c`
  - result: baseline still proves only `infra_smoke_ready`; 052 processing
    dispatcher fix is not deployed yet
- 2026-06-25 readiness report generation:
  - output: `docs/evidence/052-mvp-live-ui-proof/readiness-report.json`
  - output: `docs/evidence/052-mvp-live-ui-proof/readiness-report.md`
  - output: `docs/evidence/052-mvp-live-ui-proof/launch-gap-register.md`
  - outcome: `pilot_blocked`
  - P0/P1 blockers: `3`
  - degraded stages: `meeting-list`,
    `meeting-detail-transcript-playback`, `notes-action-output`,
    `desktop-embedded-cabinet`, `production-deployment-smoke`
  - KRISP comparison result: web list and web review remain `needs_polish`
    because live production owner detail is blocked by missing auth context
- 2026-06-25 readiness truth validation:
  - command:
    `cd apps/server && uv run --extra dev pytest -q tests/unit/test_mvp_owner_journey_readiness.py tests/contract/test_mvp_owner_journey_proof_contract.py tests/integration/test_mvp_loop_readiness_report.py`
  - result: `pass`
  - summary: `18 passed, 1 warning`
  - command:
    `cd apps/server && uv run --extra dev pytest -q tests/unit/test_mvp_owner_journey_readiness.py tests/integration/test_mvp_loop_live_evidence.py tests/integration/test_mvp_loop_readiness_report.py`
  - result: `pass`
  - summary: `25 passed, 1 warning`

## Forbidden Content Scan

- 2026-06-25 quickstart scan:
  - command:
    `rg -n -i 'transcript text|signed url|secret|token|password|cookie|set-cookie|authorization:|object key|/(Users|home)/[^ ]+|private meeting|private outcome' specs/052-mvp-live-ui-proof docs/evidence/052-mvp-live-ui-proof docs/current-product-status.md CHANGELOG.md`
  - result: `reviewed_pass`
  - summary: matches are policy text, schema/contract words, changelog policy
    references, and variable names only; no live cookies, tokens, signed URLs,
    storage keys, raw audio, transcript content, account identifiers, or private
    local paths were found
- 2026-06-25 strict live-value scan:
  - command:
    `rg -n -i 'set-cookie|authorization:|x-amz-|signed_url=|storage_object_key=|/(Users|home)/[^ ]+' specs/052-mvp-live-ui-proof docs/evidence/052-mvp-live-ui-proof docs/current-product-status.md CHANGELOG.md`
  - result: `reviewed_pass`
  - summary: only the literal quickstart scan pattern matched

## Quickstart Focused Gate

- 2026-06-25 prerequisites:
  - command:
    `SPECIFY_FEATURE_DIRECTORY=specs/052-mvp-live-ui-proof .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`
  - result: `pass`
  - summary: feature dir resolved to `specs/052-mvp-live-ui-proof`
- 2026-06-25 focused server tests:
  - command:
    `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_mvp_launch_proof_contract.py tests/integration/test_mvp_loop_readiness_report.py tests/unit/test_mvp_launch_proof_readiness.py tests/integration/test_mvp_launch_status_truth.py tests/unit/test_cabinet_web_shell.py tests/integration/test_cabinet_meeting_outcomes.py tests/integration/test_cabinet_playback_route.py tests/integration/test_cabinet_meeting_detail.py`
  - result: `pass`
  - summary: `55 passed, 1 warning`
- 2026-06-25 production owner journey probe:
  - command:
    `python3 specs/052-mvp-live-ui-proof/evidence/production-owner-journey-probe.py`
  - result: `blocked`
  - summary: public live/ready passed; owner review remains blocked without
    `OWNER_SESSION_COOKIE` and `OWNER_MEETING_ID`
- 2026-06-25 browser runtime UI proof:
  - command:
    `NODE_PATH="${CODEX_NODE_MODULES:-node_modules}" "${CODEX_NODE_BIN:-node}" specs/052-mvp-live-ui-proof/evidence/browser-runtime-check.cjs`
  - result: `pass`
  - summary: `failures=[]`
- 2026-06-25 macOS focused tests:
  - command:
    `swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinet|CaptureControl|DesktopUploadQueue|EmbeddedCabinet'`
  - result: `pass`
  - summary: `112 tests, 0 failures`
- 2026-06-25 installed app metadata:
  - app version: `2026.06.25.6`
  - codesign verify: `pass`
  - process state: `running`
- 2026-06-25 production health/deploy truth:
  - live: `ok`
  - ready: `ready`
  - branch: `master`
  - SHA: `efcbea1c7417761db489d07aef23198e49d8313c`

## Full Local Gate

- 2026-06-25 canonical local CI:
  - command:
    `infra/scripts/ci-local.sh`
  - result: `pass`
  - summary: server tests `622 passed, 4 skipped, 90 warnings`; server lint
    passed; Python compile passed; RLS hardening boundary blocked safely
    without `RLS_TEST_DATABASE_URL`; production Compose config rendered;
    deployment evidence scan passed; `ci_local_result=pass`

## Deploy Dry Run

- 2026-06-25 production deploy dry-run:
  - command:
    `infra/scripts/cd-remote.sh --dry-run`
  - result: `pass`
  - summary: `deploy_result=dry_run`; remote host/path resolved; branch
    `052-mvp-live-ui-proof`; planned steps include clean worktree, branch sync,
    pinned SHA, local CI, remote fetch, backup, restore rehearsal, compose
    config secret scan, build/up, runtime secret env scan, production smoke,
    and public health

## Ponytail Diff Review

- 2026-06-25 Ponytail pass:
  - command:
    `git diff --check`
  - result: `pass`
  - summary: no whitespace/style diff errors
  - review result: no extra abstraction kept; production blocker fix stays in
    `infra/docker-compose.yml`; readiness/report/test changes reuse the
    existing readiness generator and mark 052 live owner UI truth as degraded
    instead of adding a separate reporting path
- 2026-06-25 task reconciliation:
  - result: `pass`
  - summary: T019, T020, and T024 remain open because fresh installed-app
    record-to-review, authenticated production owner review counts, and
    representative timing are still unproven; release/deploy tasks remain open
    until PR and production deploy are complete

## PR Draft

- 2026-06-25 PR and release notes draft:
  - file: `specs/052-mvp-live-ui-proof/evidence/pr-draft.md`
  - result: `pass`
  - summary: Russian PR/release draft records processing dispatch fix, 052 UI
    proof evidence, validation, compatibility, and remaining P1 limitations

## Post-Deploy Release Evidence

- 2026-06-25 production fix PR:
  - PR: `#1845`
  - result: `merged`
  - summary: `rec-api` no longer mounts or reads the MediaScribe API key;
    `rec-processing-worker` keeps the key because it performs MediaScribe work
- 2026-06-25 release:
  - tag: `v2026.06.25.10`
  - release: `https://github.com/yshishenya/crisp/releases/tag/v2026.06.25.10`
  - commit: `db1eca18f08d26f6816b2bd88067709d0e57e590`
- 2026-06-25 production deploy:
  - command: `infra/scripts/cd-remote.sh --dry-run --branch master`
  - result: `pass`
  - summary: `deploy_result=dry_run`
  - command: `infra/scripts/cd-remote.sh --execute --branch master`
  - result: `pass`
  - deployed SHA: `db1eca18f08d26f6816b2bd88067709d0e57e590`
  - backup reference: `/opt/projects/2brain-rec/backups/20260625T181921Z`
  - smoke result: `pass`
  - readiness verdict: `infra_smoke_ready`
  - upload smoke status: `ingested_pending_processing`
- 2026-06-25 post-deploy production health:
  - public live: `ok`
  - public ready: `ready`
  - internal checks: `postgres=ok`, `minio=ok`, `processing=enabled`,
    `temporal=configured`, `mediascribe=dispatcher_only`,
    `langfuse=configured`
  - remote SHA: `db1eca18f08d26f6816b2bd88067709d0e57e590`
  - container state: `rec-api` running and healthy; `rec-processing-worker`
    running
- 2026-06-25 task reconciliation after deploy:
  - result: `pass`
  - summary: T044 is closed by release/deploy evidence; T019, T020, and T024
    remain open because fresh installed-app record-to-review, authenticated
    production owner-review counts, and representative timing are still
    unproven

## Production-Safe Hour Timing Proof

- 2026-06-25 synthetic production-safe one-hour candidate:
  - result: `pass`
  - audio duration: `3600s`
  - upload_seconds: `3`
  - workflow_start_to_imported_seconds: `36`
  - mediascribe_submit_to_ready_seconds: `28`
  - created_to_imported_seconds: `37`
  - transcript_segments: `210`
  - diarization_segments: `210`
  - outcome_sets: `1`
  - outcome_items: `5`
  - summary: non-sensitive synthetic production candidate stayed under the
    180-seconds-per-hour target and produced transcript, diarization, playback,
    speaker timeline, and stored outcome counts
- 2026-06-25 readiness regeneration:
  - command:
    `cd apps/server && uv run --extra dev python scripts/generate_mvp_loop_readiness.py --feature 052-mvp-live-ui-proof --output-dir ../../docs/evidence/052-mvp-live-ui-proof --deployed-commit db1eca18f08d26f6816b2bd88067709d0e57e590`
  - result: `pass`
  - summary: `processing-time-target-evidence` removed from the 052 P1 launch
    gap register; T019 and T020 remain open because fresh installed-app
    record-to-review and stored outcomes on that current candidate are still
    unproven
- 2026-06-25 focused validation after timing evidence update:
  - command:
    `cd apps/server && uv run --extra dev pytest -q tests/unit/test_mvp_owner_journey_readiness.py tests/contract/test_mvp_owner_journey_proof_contract.py tests/integration/test_mvp_loop_readiness_report.py tests/integration/test_mvp_launch_status_truth.py`
  - result: `pass`
  - summary: `25 passed, 1 warning`
  - command:
    `cd apps/server && uv run --extra dev pytest -q tests/unit/test_mvp_loop_readiness_matrix.py tests/contract/test_mvp_loop_readiness_contract.py tests/contract/test_mvp_launch_proof_contract.py tests/integration/test_mvp_loop_live_evidence.py`
  - result: `pass`
  - summary: `36 passed, 1 warning`
  - command:
    `python3 -m json.tool docs/evidence/052-mvp-live-ui-proof/readiness-report.json >/tmp/052-readiness-json-ok && git diff --check`
  - result: `pass`
  - command:
    `rg -n -i 'set-cookie|authorization:|x-amz-|signed_url=|storage_object_key=|/Users/|/home/|/var/folders/' specs/052-mvp-live-ui-proof docs/evidence/052-mvp-live-ui-proof docs/current-product-status.md CHANGELOG.md || true`
  - result: `pass`
  - summary: matches were only the documented scan command patterns in
    `quickstart.md` and this validation log; no live private values found

## Current Release And Installed-App Recheck

- 2026-06-25 production release/deploy recheck:
  - latest release: `v2026.06.25.14`
  - deployed SHA: `1580988f7c9bf00f9c6d9c74037b145cd902b913`
  - public live: `ok`
  - public ready: `ready`
  - deploy result: `pass`
  - readiness verdict: `infra_smoke_ready`
  - smoke cleanup: `pass`
  - summary: production is current and healthy, but this remains infrastructure
    smoke readiness, not MVP owner-journey readiness
- 2026-06-25 synthetic timing cleanup:
  - result: `pass`
  - database records removed: `458`
  - object keys removed: `3`
  - residue: `none`
  - summary: the production-safe one-hour timing candidate was removed after
    cleanup gained meeting outcome dependency coverage
- 2026-06-25 installed app recheck:
  - app path: `/Applications/2brain Rec.app`
  - app version: `2026.06.25.14`
  - codesign verify: `pass`
  - process state: `running`
  - active recording media handles: `0`
  - queue state: `15 uploaded`, `6 blocked`
  - current auth blocker: `http_status_401:missing_auth_context`
  - cabinet state: `expiredSession`
  - fresh post-deploy recording: `none`
  - summary: installed app identity is current, but T019/T020 remain open until
    the user signs in inside the app and creates a fresh recording candidate
- 2026-06-25 readiness regeneration:
  - command:
    `cd apps/server && uv run --extra dev python scripts/generate_mvp_loop_readiness.py --feature 052-mvp-live-ui-proof --output-dir ../../docs/evidence/052-mvp-live-ui-proof --deployed-commit 1580988f7c9bf00f9c6d9c74037b145cd902b913`
  - result: `pass`
  - summary: readiness docs now point at the current deployed commit while the
    outcome remains `pilot_blocked`
- 2026-06-25 safe UI/probe recheck:
  - command:
    `python3 specs/052-mvp-live-ui-proof/evidence/production-owner-journey-probe.py`
  - result: `blocked`
  - summary: public live/ready passed; owner review proof still requires a
    real `OWNER_SESSION_COOKIE` and `OWNER_MEETING_ID`
  - command:
    `NODE_PATH=<codex-runtime-node-modules> <codex-runtime-node> specs/052-mvp-live-ui-proof/evidence/browser-runtime-check.cjs`
  - result: `pass`
  - summary: `failures=[]`; web and embedded fixture checks show one playback
    shell, timestamp seek, three speaker timeline lanes, stored outcome rows,
    and no horizontal overflow across desktop/mobile viewports

## 2026-06-25 Upload Contract Recheck

- fresh installed-app candidate:
  - session: `FDE7D402-EF68-4272-92E8-9F886B157C0F`
  - initial upload blocker: `http_status_409:ambiguous_track_parts`
  - root cause: macOS client split ordinary WAV tracks into multiple 5 MB
    parts while server finalize expected one accepted object per track role
  - follow-up state after retry: `uploaded`
  - processing status after reconciliation: `processed`
- 1 GiB upload contract update:
  - server default `max_upload_part_bytes`: `1073741824`
  - macOS default upload part size: `1073741824`
  - env templates updated: server local and production examples
  - larger-than-1-GiB tracks: outside the current MVP upload contract
- focused validation:
  - command:
    `cd apps/server && uv run --extra dev pytest -q tests/unit/test_config_validation.py -q`
  - result: `pass`
  - summary: `24 passed`
  - command:
    `swift test --package-path apps/macos --disable-swift-testing --filter DesktopUploadClientTests`
  - result: `pass`
  - summary: `9 tests passed`
- full local validation:
  - command:
    `git diff --check && infra/scripts/ci-local.sh`
  - result: `pass`
  - summary: `627 passed, 4 skipped`; server lint, python compile, production
    compose rendering, and deployment evidence scan passed
  - production config proof: rendered compose includes
    `TWOBRAIN_MAX_UPLOAD_PART_BYTES=1073741824`
- final local app rebuild:
  - command:
    `TWO_BRAIN_REC_VERSION=2026.06.26.3 TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh`
  - result: `pass`
  - installed app: `/Applications/2brain Rec.app`
  - installed version: `2026.06.26.3`
  - codesign verify: `pass`

## 2026-06-25 Proxy Limit Recheck

- production deploy:
  - deployed sha: `6c1b2f2ffa2545ee3a2f5bc5af734b0f19bcbd1e`
  - deploy result: `pass`
  - public Rec live/ready: `pass`
- Rec ingress proxy:
  - host: `2brain.dev`
  - enabled config: `/etc/nginx/sites-enabled/rec.2brain.pro.conf`
  - `client_max_body_size`: `6g`
  - `proxy_request_buffering`: `off`
  - `proxy_buffering`: `off`
  - `proxy_read_timeout` / `proxy_send_timeout`: `3600s`
  - header-only large request probes to Rec returned app-level `405`, not
    proxy `413`, for `600 MiB` and `1100 MiB` content lengths
- MediaScribe proxy:
  - domain: `mediascribe.2brain.pro`
  - observed server: `openresty`
  - DNS differs from Rec (`rec.2brain.pro` and `mediascribe.2brain.pro` are on
    separate machines)
  - local access to MediaScribe host: unavailable
  - header-only probes returned `413 Request Entity Too Large` for `600 MiB`
    and `1100 MiB` content lengths before any body upload
  - interpretation: not a blocker for the 1 GiB Rec upload contract when Rec is
    used to store video/package data and MediaScribe receives smaller extracted
    or retained audio
  - conditional risk: if real combined `mic_file` + `incoming_file` audio sent
    to MediaScribe approaches the proxy ceiling, processing may fail with
    `mediascribe_payload_too_large`
- conditional follow-up:
  - only if large audio processing hits this ceiling, raise MediaScribe
    OpenResty/nginx `client_max_body_size`, keep request buffering off and long
    send/read timeouts, validate/reload the proxy, then repeat the header-only
    probes and a non-sensitive large-audio processing check
