# Validation: F297

**Date**: 2026-11-17
**Branch**: `codex/297-launch-capture-retention`
**Base**: `e7723baf8a6890fff54956007baa0b29b3047892`

## Current result

Implementation and focused local checks are complete. Hardware QA, live
deployment checks and release gates remain open.

| Check | Result |
|---|---|
| `swift build --package-path apps/macos` | PASS |
| `swift test --package-path apps/macos --filter 'RecordingAudioTimeline\|LocalRecordingWriterSystemAudio'` | PASS: 63 tests, 0 failures |
| `swift test --package-path apps/macos --filter 'CanonicalRecordingManifestTests\|CaptureControlV5Tests'` | PASS: 9 tests, 0 failures |
| Full `apps/macos/Scripts/run-swift-tests.sh` | PASS: 1538 tests, 9 skipped, 0 failures |
| `swift run --package-path apps/macos ContractValidation` | PASS |
| `pytest tests/unit/test_retention_reconciler.py tests/unit/test_referral_landing.py` | PASS: 12 tests |
| `pytest tests/governance/test_prune_rec_backups.py` | PASS: 7 tests |
| `bash apps/server/scripts/run_local_postgres_tests.sh --fast` | PASS: 189 unit tests |
| Postgres focused: migrations, RLS, retention | PASS: 61 tests |
| Postgres focused: fair-use, billing monitoring, backup snapshot | PASS: 277 tests |
| Postgres focused: full `tests/contract` | PASS: 2402 tests, 84 skipped |
| `pytest tests/contract/test_rls_policy_matrix_contract.py tests/contract/test_playback_normalization_rls_contract.py` | PASS: 11 tests |
| `ruff check` on changed Python files | PASS |
| `python -m compileall` on changed Python files | PASS |
| `python3 scripts/validate-legacy-impact.py --feature specs/297-launch-capture-retention/spec.md` | PASS |
| `infra/scripts/ci-local.sh --fast` | BLOCKED on pre-existing `specify 1.2.6` vs lock `1.0.7`; preflight passes |
| `python3 scripts/validate-changelog-fragments.py` | PASS |
| `git diff --check` | PASS |

## Capture behavior implemented

- Short system-reference gap `<= 500 ms` is bridged with bounded silence.
- Gap `500 ms–15 s` is not masked; it raises `renderReferenceMissing` and the writer keeps a truthful partial prefix.
- Gap `> 15 s` still raises `gapExceedsBound`.
- `.routeChanged` rebases the next generation to `lastInputEndFrame`; converter/inputFormat reset supports sample-rate changes.
- Continuity failures with a playable prefix map to `timelineMisaligned` and `partialContinuity=true`; queue upload is allowed with a degraded status.
- Real microphone loss remains fail-closed.

## Retention / backup

- Daily `run_retention_once` loops active workspaces with isolated sessions, bounded limit 100 and metadata-only logging.
- `TWOBRAIN_RETENTION_SCHEDULER_ENABLED` stops the loop.
- Migration `0114_retention_scan_maintenance.py` replaces `rec_maintenance_allowed()` with the exact `retention_scan` operation; no tables/data change. RLS contract tests pass.
- Runtime bootstrap accepts both the 0113 and 0114 helper bodies, so a fresh deploy does not fail the fair-use safety check after the migration.
- `prune-rec-backups.sh` dry-run default; execute removes only exact dated GRAF backup directories older than 30 days, never the newest, symlinks or foreign directories; exit codes 0/2/3.
- systemd service/timer and `docs/runbooks/backup-retention.md` added.

## Public copy / referral

- Offer describes auto-renewal as checked by default and removable before payment.
- Offer/landing state the 4-hour per-recording limit.
- Checkout still has one checked, not-required `recurring_consent`; CSRF/auth/routes unchanged.
- The approved catalog/`offer_version` (`personal-2026-09-27`) and billing sign-off are not changed in F297; the copy correction is part of the postponed billing/legal slice.
- Referral auth shell uses a safe `public_analytics` default and the route passes the real context; unit rendering no longer raises.
- A real database failure during the referral lookup is mapped to the retryable 503 page (`OperationalError`/`InterfaceError`/pool timeout), not to a 500. Unit tests force the outage and cover 410/200; live confirmation remains part of T022.

## Safety fix after council review (2026-11-18)

The council review produced `SAFE WITH CONDITIONS` for audio and retention and found two P0/P1 issues that were fixed in `08b6e4eab`, `59e45fcde`, `51d6b1592` and `70446a715`:

- **Route-change honesty.** A route marker no longer forces the next batch to the previous end frame. The timeline measures the media delta first, then the observed host-clock delta from the **end** of the previous batch when the media clock resets. A gap `<= 500 ms` is bridged with bounded silence; a gap `> 500 ms` produces `renderReferenceMissing` and a truthful partial prefix. PTS continuity wins over callback latency; split batches advance the remainder host time; multiple route changes are allowed; a microphone disconnect is `.sourceStopped`.
- **Partial recordings stay local.** `partialContinuity` is durable in the queue document, F296 eligibility and the manual cleanup candidate policy keep partial WAVs, and server-initiated `purgeLocalBuffers` now also refuses to delete a partial recording.
- **Retention has two keys.** `retention_scheduler_enabled` defaults to `false`, and `retention_scheduler_dry_run_only` defaults to `true`. Even after the operator enables the scheduler, the first passes remain dry-run until the second key is explicitly cleared. The env template keeps both safe defaults.
- **Prune ownership.** A dated directory is deletable only when `backup.passed`, `postgres.dump`, `schema.sql`, `inventory.jsonl`, `checksums.sha256` and `minio-objects/` are present. The newest directory overall and the newest verified backup are both kept, so a minio-stage failure cannot protect itself as the newest verified backup. Output is metadata-only.
- **Maintenance RLS is proven.** A real PostgreSQL test runs the retention scan under `MaintenanceTenantContext(operation_name="retention_scan")` against two workspaces; fake-session-only coverage is no longer the only evidence.

Focused validation for this fix:

| Check | Result |
|---|---|
| `swift build --package-path apps/macos --build-tests` | PASS |
| `swift test --filter 'RecordingAudioTimelineTests\|LocalRecordingWriterTests\|LocalCacheEligibilityTests\|DesktopUploadQueueTests'` | PASS: 185 tests |
| full `apps/macos/Scripts/run-swift-tests.sh` | PASS: 1540 tests, 9 skipped, 0 failures |
| `swift run ContractValidation` | PASS |
| `pytest tests/unit/test_retention_reconciler.py` | PASS: 5 tests |
| `pytest tests/governance/test_prune_rec_backups.py` | PASS: 7 tests |
| `run_local_postgres_tests.sh --focused tests/integration/test_retention_maintenance_rls.py` | PASS: 1 test |
| `git diff --check` | PASS |

Still open: T010 hardware QA, T019 live render, T022 live referral, T023 convergence, T024 release gates. The fix commits are not yet a release candidate.

## Checklist and governance

- Independent reviewer-owned checklist review: PASS 40/40 (audio 10/10, security 10/10, infra 10/10, UX 10/10).
- `python3 scripts/check_spec_kit_governance.py` is blocked by a pre-existing environment drift: installed `specify` is 1.2.6, the frozen lock expects 1.0.7. This is not caused by F297 and was not changed.

## Test stand state

- The shared Dev stand is currently active on SHA `ee58f5fa` (`feature_id: 292`, F292 T042), not on this branch.
- Read-only probes against that stand reproduce the pre-F297 defects: `/referral/unknown-token` and `/r/unknown-token` return 500; `/offer` still contains “Согласие не должно быть заранее отмечено”; `/` still contains “без лимита по времени” and “без ограничения длительности”.
- T019/T022 therefore cannot be closed until F297 is committed, built and promoted in a coordinated stand window; no build, promote, merge, release or deploy was run.

## Not yet validated

- **T010 hardware QA matrix**: AirPods, wired headphones, dock/display, sleep/lid,
  change before first system-audio packet, real short call. Requires the single
  `/Applications/GRAF Dev.app` and a real Mac session.
- **T019 live render/browser**: `/offer`, `/`, `/billing/checkout` on deployed
  server.
- **T022 live referral**: `/r/<unknown>`, `/referral/<unknown>` and DB-unavailable
  503 on deployed server.
- **T023 convergence**: full artifact/task/issue closeout.
- **T024 release gates**: exact-SHA PR checks and one `release-full` on a frozen
  candidate.
- Production retention/prune enablement is an operator action; no production
  deploy was performed in this branch.
