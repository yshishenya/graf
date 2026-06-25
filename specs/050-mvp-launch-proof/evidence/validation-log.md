# Validation Log: 050 MVP Launch Proof

All entries are metadata-only. Do not add raw audio, transcript text, private
meeting titles, account identifiers, cookies, tokens, signed URLs, object keys,
or local private paths.

## 2026-06-25 - Setup Baseline

- Branch baseline:
  - branch: `050-mvp-launch-proof`
  - local HEAD: `ef222bc57b4343ceccfaec1c8cc4a677a2a372d6`
  - origin/master: `ef222bc57b4343ceccfaec1c8cc4a677a2a372d6`
  - production remote branch: `master`
  - production remote HEAD: `ef222bc57b4343ceccfaec1c8cc4a677a2a372d6`
  - worktree has only 050 planning/governance changes at setup time.
- Production health baseline:
  - `https://rec.2brain.pro/api/v1/health/ready` returned `{"status":"ready"}`.
- Spec Kit prerequisites:
  - `SPECIFY_FEATURE_DIRECTORY=specs/050-mvp-launch-proof .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`
  - result: `FEATURE_DIR=specs/050-mvp-launch-proof`
  - available docs: `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `tasks.md`
- Checklist status:
  - `infra.md`: 10/10
  - `requirements.md`: 16/16
  - `security.md`: 10/10
  - `ux.md`: 10/10
- Governance correction:
  - `.specify/memory/constitution.md` amended from `2.0.0` to `2.0.1`.
  - Public Rec URL corrected to `https://rec.2brain.pro`; deployment host remains `2brain.dev`.
  - `docs/agent-guidance/product-gates.md` aligned with the same public URL.
- Spec Kit analyze:
  - read-only pass over `spec.md`, `plan.md`, and `tasks.md`
  - result: no critical or high findings; task ids are sequential T001-T046; no unresolved clarification markers.
- GitHub issue sync:
  - `feature:050` label exists.
  - created GitHub issues `#1707` through `#1752` for tasks T001-T046.
  - mapping written to `specs/050-mvp-launch-proof/issues.md`.
  - `github-issue-canon` ensure/validate result: OK, 46 Spec Kit issues checked.

## 2026-06-25 - Foundational RED/GREEN

- RED command:
  - `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_mvp_launch_proof_readiness.py tests/integration/test_mvp_launch_status_truth.py tests/unit/test_product_gate_url_truth.py`
  - result: expected fail, `4 failed, 1 passed`
  - failures: 050 readiness still inherited old P1 blockers, 050 evidence records were missing, and `docs/current-product-status.md` still described 049 as branch-local/unreleased behavior.
  - URL governance check already passed because T004 corrected `rec.2brain.pro` before the RED run.
- GREEN command:
  - `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_mvp_launch_proof_readiness.py tests/integration/test_mvp_launch_status_truth.py tests/unit/test_product_gate_url_truth.py`
  - result: `5 passed, 1 warning`
- Implemented support:
  - 050 readiness report keeps `pilot_blocked`, bounded claim `infra_smoke_ready`, and remaining P1 gap `production-user-rollout-evidence`.
  - 050 reuses shipped 049 stored-outcome evidence without reopening `notes-action-output`.
  - current product status now describes 049 as merged/released/deployed and 050 as the active MVP launch-proof boundary.

## 2026-06-25 - Owner Journey Contract Harness

- Added `specs/050-mvp-launch-proof/evidence/production-health-check.sh` for public live/ready plus remote deployed SHA checks.
- Added `specs/050-mvp-launch-proof/evidence/installed-app-check.md` for metadata-only installed app identity/runtime checks.
- Contract RED command:
  - `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_mvp_launch_proof_contract.py`
  - result: expected fail, `1 failed, 1 passed`
  - failure: closeout gate table lacked machine-checkable gate ids.
- Contract GREEN command:
  - `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_mvp_launch_proof_contract.py`
  - result: `2 passed, 1 warning`

## 2026-06-25 - Production And Installed App Baseline

- Production health command:
  - `specs/050-mvp-launch-proof/evidence/production-health-check.sh`
  - result: `status=pass`
  - public URL: `https://rec.2brain.pro`
  - live: `{"status":"ok"}`
  - ready: `{"status":"ready"}`
  - local HEAD / origin master / production remote SHA: `ef222bc57b4343ceccfaec1c8cc4a677a2a372d6`
  - production remote branch: `master`
  - note: this proves the pre-050 production baseline is aligned; final 050 release/deploy proof still belongs to T046.
- Installed app baseline:
  - `/Applications/2brain Rec.app` exists.
  - bundle id: `pro.2brain.rec`
  - installed bundle version: `2026.06.25.2`
  - signature: ad-hoc
  - fresh soft quit/open produced process `2brain Rec`.
  - app log recorded `app_launch_finished`, `app_main_window_presented`, `visibleWindowCount=1`, and cabinet auth-required truth (`state=expiredSession`, `routeKind=authLogin`).
  - AX/window capture caveat: AppleScript reported `windows=0`, Codex `screencapture` returned a black frame, and Computer Use returned `cgWindowNotFound`; those automation limits are not committed as product screenshots.
- Focused macOS cabinet support command:
  - `swift test --package-path apps/macos --disable-swift-testing --filter DesktopCabinetWorkspaceTests`
  - result: `20 tests, 0 failures`

## 2026-06-25 - Production Metadata Journey Probe

- Production metadata probe:
  - command class: read-only SQL over the production database on `2brain.dev`
  - committed content: metadata only; no meeting ids, titles, account ids, transcript text, object keys, tokens, cookies, signed URLs, or private paths
  - probe name: `production_metadata_journey_050`
  - candidate count: `1`
  - ready candidate count: `1`
  - outcome-ready candidate count: `0`
- Candidate state:
  - upload status: `finalized`
  - media revision status: `accepted`
  - stored track role count: `3`
  - stored track count: `3`
  - workflow status: `processed`
  - MediaScribe status: `ready`
  - result status: `imported`
  - transcript status: `available`
  - diarization status: `available`
  - transcript segment count: `4`
  - diarization segment count: `3`
- Timings:
  - recording duration: `31` seconds
  - workflow processing duration: `8.129` seconds
  - MediaScribe duration: `5.946` seconds
  - finalize-to-import duration: `381.211` seconds
  - import age: about `10.710` hours at probe time
- Outcome state:
  - outcome status: `missing`
  - outcome item count: `0`
  - outcome latency: unavailable
- Interpretation:
  - production currently proves a finalized/processed candidate with transcript and diarization;
  - production does not yet prove stored outcomes for that candidate;
  - the 31-second candidate does not prove the three-minute-per-hour target;
  - keep `production-user-rollout-evidence` open until a fresh post-049 owner journey or explicit server-side backfill/proof closes outcomes and representative timing.

## 2026-06-25 - Interface And Readiness Proof

- Browser runtime verifier:
  - command: `NODE_PATH=<local-node-modules> <local-node-bin> specs/050-mvp-launch-proof/evidence/browser-runtime-check.cjs`
  - result: `failures=[]`
  - covered surfaces: web desktop, web mobile-width, desktop embedded, embedded mobile-width
  - covered behavior: active transcript/recording tab, persistent bottom playback, timestamp seek, speaker timeline lanes, stored outcomes, no horizontal overflow, no console errors
- Focused server UI/readiness command:
  - `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_cabinet_web_shell.py tests/integration/test_mvp_loop_readiness_report.py tests/integration/test_mvp_launch_status_truth.py tests/unit/test_mvp_launch_proof_readiness.py`
  - result: `25 passed, 1 warning`
  - warning: pytest asyncio event-loop-policy deprecation in test runtime only
- Focused macOS cabinet command:
  - `swift test --package-path apps/macos --disable-swift-testing --filter DesktopCabinetWorkspaceTests`
  - result: `22 tests, 0 failures`
  - added coverage: false-green cabinet state cannot carry across auth-required or server-failure states; HTTP status mapping prevents success state unless an allowed route succeeds.
- Readiness generation:
  - command: `cd apps/server && PYTHONPATH=src uv run python scripts/generate_mvp_loop_readiness.py --feature 050-mvp-launch-proof --output-dir ../../docs/evidence/050-mvp-launch-proof --deployed-commit ef222bc57b4343ceccfaec1c8cc4a677a2a372d6`
  - result: generated `readiness-report.json`, `readiness-report.md`, and `launch-gap-register.md`
  - outcome: `pilot_blocked`
  - remaining P1 gap: `production-user-rollout-evidence`
- Forbidden-content scan:
  - command class: quickstart forbidden-content scan plus focused checks for real home paths, auth headers, cookie values, bearer/API-key-like values, token/password assignments, signed URL values, object-key values, and secret values
  - broad policy-term matches: `71`
  - real home path matches: `0`
  - real high-risk value matches: `0`
  - result: `pass`
  - note: remaining broad matches are forbidden-class policy text in docs/changelog/quickstart, not committed private content.

## 2026-06-25 - Final Pre-PR Gates

- Quickstart prerequisites:
  - command: `SPECIFY_FEATURE_DIRECTORY=specs/050-mvp-launch-proof .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`
  - result: `FEATURE_DIR=specs/050-mvp-launch-proof`
- Quickstart focused server readiness and cabinet tests:
  - command: `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_mvp_loop_readiness_matrix.py tests/integration/test_mvp_loop_readiness_report.py tests/unit/test_cabinet_web_shell.py tests/integration/test_cabinet_meeting_outcomes.py tests/integration/test_cabinet_playback_route.py tests/integration/test_cabinet_meeting_detail.py`
  - result: `58 passed, 1 warning`
- Quickstart browser runtime UI proof:
  - command: `CODEX_NODE_MODULES=<local-node-modules> CODEX_NODE_BIN=<local-node-bin> NODE_PATH=<local-node-modules> <local-node-bin> specs/050-mvp-launch-proof/evidence/browser-runtime-check.cjs`
  - result: `failures=[]`
- Quickstart macOS focused tests:
  - command: `swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinet|CaptureControl|DesktopUploadQueue|EmbeddedCabinet'`
  - result: `110 tests, 0 failures`
- Quickstart production health and deployment truth:
  - public live: `{"status":"ok"}`
  - public ready: `{"status":"ready"}`
  - production remote branch: `master`
  - production remote SHA before 050 merge: `ef222bc57b4343ceccfaec1c8cc4a677a2a372d6`
- Full local CI:
  - first run result: `610 passed, 4 skipped, 90 warnings`, then Ruff failed on import ordering in three new tests
  - remediation: `cd apps/server && uv run --extra dev ruff check --fix tests/contract/test_mvp_launch_proof_contract.py tests/integration/test_mvp_launch_status_truth.py tests/unit/test_product_gate_url_truth.py`
  - final run result: `ci_local_result=pass`
  - final run included: `610 passed, 4 skipped, 90 warnings`, Ruff pass, Python compile pass, compose config rendering, deployment evidence scan pass
- Deploy dry-run:
  - command: `infra/scripts/cd-remote.sh --dry-run`
  - result: `deploy_result=dry_run`
  - remote host/path: `2brain.dev` / `/opt/projects/2brain-rec`
  - branch: `050-mvp-launch-proof`
  - planned steps: clean worktree, branch sync, pinned SHA, local CI, remote fetch, backup, restore rehearsal, compose secret scan, build/up, runtime secret env scan, production smoke, public health.

## 2026-06-25 - Release And Production Deploy

- PR:
  - `https://github.com/yshishenya/crisp/pull/1753`
  - state: merged
  - merge commit: `cf54c6dc5116bc1e164ab150fe345875b4cc944b`
- Release:
  - tag: `v2026.06.25.5`
  - GitHub Release: `https://github.com/yshishenya/crisp/releases/tag/v2026.06.25.5`
  - release commit: `bb711e134380442230857989e51c0b366582199c`
- Production deploy:
  - command: `infra/scripts/cd-remote.sh --execute`
  - result: `deploy_result=pass`
  - branch: `master`
  - deployed SHA: `bb711e134380442230857989e51c0b366582199c`
  - backup reference: `/opt/projects/2brain-rec/backups/20260625T025027Z`
  - restore rehearsal: `pass`
  - production smoke: `smoke_result=pass`
  - readiness verdict: `infra_smoke_ready`
  - RLS validation: `pass` on disposable database
  - smoke cleanup: `pass`
- Public health after deploy:
  - live: `{"status":"ok"}`
  - ready: `{"status":"ready"}`
  - production remote branch: `master`
  - production remote SHA: `bb711e134380442230857989e51c0b366582199c`
- Final claim:
  - keep `pilot_blocked`
  - keep `production-user-rollout-evidence` open until fresh live owner journey, stored outcomes on a production candidate, and representative one-hour timing proof pass.
