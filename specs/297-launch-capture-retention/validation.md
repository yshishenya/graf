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
| Full `apps/macos/Scripts/run-swift-tests.sh` | PASS: 1545 tests, 9 skipped, 0 failures |
| `swift run --package-path apps/macos ContractValidation` | PASS |
| `pytest tests/unit/test_retention_reconciler.py tests/unit/test_referral_landing.py` | PASS: 17 tests |
| `pytest tests/governance/test_prune_rec_backups.py` | PASS: 9 tests |
| `bash apps/server/scripts/run_local_postgres_tests.sh --fast` | PASS: 2960 pure tests (resource phase needs Docker) |
| Postgres focused: migrations, RLS, retention | PASS: 61 tests |
| Postgres focused: fair-use, billing monitoring, backup snapshot | PASS: 277 tests |
| Postgres focused: full `tests/contract` | 2400 passed, 84 skipped, 2 flaky failures that pass on isolated re-run |
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
- Migration `0116_retention_scan_maintenance.py` replaces `rec_maintenance_allowed()` with the exact `retention_scan` operation; no tables/data change. RLS contract tests pass.
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
| `pytest tests/unit/test_retention_reconciler.py` | PASS: 7 tests |
| `pytest tests/governance/test_prune_rec_backups.py` | PASS: 9 tests |
| `run_local_postgres_tests.sh --focused tests/integration/test_retention_maintenance_rls.py` | PASS: 1 test |
| `run_local_postgres_tests.sh --focused tests/contract/test_analytics_degradation_alerting.py tests/contract/test_auth_contracts.py` | PASS: 196 tests (isolated re-run of the two flakes) |
| `git diff --check` | PASS |

Still open: T010 hardware QA, T019 live render, T022 live referral, T023 convergence, T024 release gates. The fix commits are not yet a release candidate.

## Post-rebase validation (2026-11-19)

After rebasing onto `origin/master` (`80551e1c5`) the branch was re-validated, because
master advanced by 13 commits since the original base:

| Check | Result |
|---|---|
| full `apps/macos/Scripts/run-swift-tests.sh` | PASS: 1545 tests, 9 skipped, 0 failures |
| `swift run --package-path apps/macos ContractValidation` | PASS |
| focused PostgreSQL: `test_retention_reconciler.py`, `test_retention_maintenance_rls.py` | PASS: 8 tests |
| `pytest tests/governance/test_prune_rec_backups.py` | PASS: 9 tests |
| `python3 scripts/validate-legacy-impact.py --feature specs/297-launch-capture-retention/spec.md` | PASS |

## Released server slice (2026-11-20)

T017, T018, T020 and T021 shipped to production in `v2026.11.20.1`
(source `aae5fce2d1897d3cb1722afd7dc49c3183d0dda8`, `release-full` run
44654169494, `deploy_result=pass`, runtime SHA matches, health `ready` 200,
backup `/opt/projects/2brain-rec/backups/20261120T021234Z`).

Verified on production after deploy:

| Check | Result |
|---|---|
| `curl -fsS https://rec.2brain.pro/` | 200; no «без лимита по времени», no «без ограничения длительности»; «до 4 часов» present twice |
| `curl -fsS https://rec.2brain.pro/offer` | 200; 4-hour limit present; «включено по умолчанию» present |
| `curl -fsS https://rec.2brain.pro/privacy` | 200; retention wording «после включения планировщика» present |
| `curl -sS -o /dev/null -w '%{http_code}' https://rec.2brain.pro/r/<unknown>` | 410, not 500 |
| `curl -sS -o /dev/null -w '%{http_code}' https://rec.2brain.pro/referral/<unknown>` | 410, not 500 |
| `curl -sS` on `r1_` + 64 chars | 410, not 500 |
| appcast and site `graf.pkg` | unchanged: `2026.11.17.1`, 10 661 944 bytes |

Public analytics is switched off by owner decision: `..._ENABLED`,
`..._AUTOMATIC_ENABLED` and `..._REPLAY_ENABLED` are `false`, the API was
restarted and the previous `.env` is kept as
`.env.backup-before-analytics-off-20261120T013305Z`. Production verification:
no Metrika counter script, `webvisor_allowed=false`, `yandex_metrica_id=null`.

Still open in this feature: T010 hardware QA, T019 checkout-specific live check
on a billing-enabled stand, T022 valid-200 and DB-unavailable-503 checks, T023
convergence, T024 release gates for the capture and retention slices.

## Checklist and governance

- Independent reviewer-owned checklist review: PASS 40/40 (audio 10/10, security 10/10, infra 10/10, UX 10/10).
- `python3 scripts/check_spec_kit_governance.py` is blocked by a pre-existing environment drift: installed `specify` is 1.2.6, the frozen lock expects 1.0.7. This is not caused by F297 and was not changed.

## Test stand state

- Before the F297 promotion the shared Dev stand was on SHA `ee58f5fa` (`feature_id: 292`, F292 T042).
- Read-only probes against that pre-F297 stand reproduced the defects: `/referral/unknown-token` and `/r/unknown-token` returned 500; `/offer` contained “Согласие не должно быть заранее отмечено”; `/` contained “без лимита по времени” and “без ограничения длительности”.
- F297 was then built and promoted on the same single stand (see the Dev stand evidence section). No production build, promote, merge, release or deploy was run.

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

## Dev stand live evidence (exact PR SHA, 2026-11-19)

- F297 is built and promoted on the single Dev stand at the exact PR SHA: manifest `dev-bf96b8034dc0`, source `bf96b8034dc0fb0bf27533bfb11cc1d10a172168`, migration head `0116_retention_scan_maintenance`. An earlier docs/test-only candidate `dev-a7d2b1a565cb` was the rollback target.
- `dev-harness.sh smoke --json --live`: pass; all 13 checks pass, including app identity/presentation, exact SHA, backend, database, migration, storage, Temporal, processing/media workers.
- `GET /`, `/offer`, `/privacy`: 200. `/offer` renders «Одна запись — до 4 часов (14 400 секунд)» and «Автопродление включено по умолчанию… его можно снять»; the phrases «без ограничения длительности» and «Согласие не должно быть заранее отмечено» are absent. `/` renders «до 4 часов». `/privacy` renders «удаление встреч, срок которых истек, после включения планировщика и разрешения удаления оператором».
- `GET /r/unknown-token`, `/referral/unknown-token` and a token-shaped unknown token: 410 with the «Ссылка недействительна» page and no 500 (browser-verified).
- `GET /billing/checkout` after Dev login redirects to the tariff page because the Dev runtime intentionally has `TWOBRAIN_BILLING_CHECKOUT_ENABLED=false`; the live checkout checkbox cannot be exercised there. The checkout checkbox/routes are covered by contract tests.
- Valid referral 200 and DB-unavailable 503 require a billing-enabled stand; they are covered by unit tests but remain live T022 checks after a billing-enabled deployment.
- T010 hardware QA remains blocked: the Mac currently exposes only built-in speakers, Krisp virtual devices and a multi-output device; no AirPods, wired headphones or dock. Screen capture permission is unavailable to the agent, so the Dev menu-bar UI cannot be driven for the manual route/sleep/lid matrix.

## Test-gap closure (2026-11-19)

An independent test-gap review found several safety claims without covering tests. All were closed:

- `RecordingAudioTimelineTests.testRouteChangeHostGapAtBridgeBoundaryIsAcceptedAndJustOverIsNot` — route-change host gap exactly 500 ms is bridged; 500.1 ms gives `renderReferenceMissing` and keeps the prefix.
- `LocalRecordingWriterSystemAudioTests.testSourceStoppedAfterPrefixPublishesPartialUploadableRecording` — `.sourceStopped` after a published prefix becomes `timelineMisaligned` with `partialContinuity=true` and an uploadable profile.
- `DesktopUploadQueueTests.testPartialContinuityRecordingRefusesServerLocalPurgeAndKeepsArtifacts` — a partial recording is never purged by the server task; ack is `failed`/`local_purge_failed` and artifacts stay.
- `DesktopUploadQueueTests.testScanRefreshKeepsPartialContinuityWhenManifestNoLongerCarriesIt` — a later scan cannot erase the durable partial marker.
- `LocalCacheSurfaceTests.testCleanupCandidatePolicyKeepsPartialContinuityRecording` — the manual cleanup policy refuses a partial recording.
- `test_retention_reconciler.py::test_retention_once_uses_destructive_mode_only_after_second_key` — destructive mode is used only when the second key is cleared.
- `test_retention_reconciler.py::test_bootstrap_accepts_both_0113_and_0114_maintenance_helper_bodies` — the 0114 module reproduces the exact 0113 helper body for pre-migration stands.
- `test_prune_rec_backups.py::test_incomplete_owned_backup_is_never_deleted` and `test_deletion_failure_returns_three` — full-contract ownership and exit code 3.
- `test_referral_landing.py` — `InterfaceError`/pool timeout map to 503, and a mid-request outage keeps an already-resolved valid page.

Closing counts: full Swift suite 1545 tests (9 skipped), retention/referral unit 17, prune 9, contract 2400 passed plus 2 isolated re-runs.

## Exact-SHA PR gates (2026-11-19)

Head `bf96b8034dc0fb0bf27533bfb11cc1d10a172168`, base `7dbcdfc3e3d75351c2abcbea973b6780e770d2c8`.

| Gate | Result |
|---|---|
| `governance-fast` | PASS (run 44562895000) |
| `macos-pr` (native build + full Swift suite + ContractValidation) | PASS (run 44562895511, `Swift build and tests` 7m9s) |
| `pr-metadata` | PASS (run 44563194569) |
| `scripts/validate-pr-checks.py --pr 8134 --expected-sha bf96b8034…` | PASS, complete proof with digests |

A text-only `edited` rerun initially failed with «current run has no verified text scope» because it raced the still-running code job; a full rerun of that workflow (attempt 3) passed. This is a scheduling artefact of the repo's text-only reuse design, not a code defect.

## Remaining launch blockers (honest state)

- **T010** hardware QA: still blocked. This Mac exposes only built-in speakers, Krisp virtual devices and a multi-output device; no AirPods, wired headphones or dock. Screen-recording permission is unavailable to the agent, so the Dev menu-bar UI cannot be driven for the route/sleep/lid matrix.
- **T019** `/billing/checkout`: the Dev adapter forces `TWOBRAIN_BILLING_CHECKOUT_ENABLED=false`, so the live checkout page cannot be exercised there; the checked/not-required `recurring_consent` and unchanged routes/CSRF are covered by contract tests only. Requires a billing-enabled stand.
- **T022** valid-token 200 and DB-unavailable 503: require a billing-enabled stand and an outage drill; covered by unit tests (200/410/503) but not live-verified.
- **T023** convergence and **T024** `release-full`: not done; `release-full` needs the post-merge master SHA.
- Production retention/prune: not enabled; two-key operator gate documented in `docs/runbooks/backup-retention.md`.

## Coordination with the parallel release chat (2026-11-20)

- `origin/master` is `f167f7ee36e12f2ee58b387a890dd27ecce29c12`; PR #8139 shipped the public-copy and referral slice of F297 to master.
- The six files it touches are byte-identical between this branch and master, so the branch merges cleanly; the branch keeps only capture continuity, retention, backup prune, migration `0114` and feature docs.
- Consequences: T017/T018 equivalence and the unknown/expired referral 410 are already delivered by #8139; T019/T022 live checks for checkout and valid-token/503 still need a billing-enabled stand, and the production deploy of that slice is owned by the other chat.
- Do not force-push this branch and do not ship `0114` from another chat; details in `coordination.md`.

## Convergence (2026-11-22)

- Branch merged with `origin/master` `359f12cc9` as a merge commit; history not rewritten.
- `validate-legacy-impact.py`: PASS, single `retain-with-exception`, expiry `2027-06-30` (future), retirement task F297/T010/#8123 → `expired_exceptions=0`.
- `validate-agent-context.py`: PASS → `unowned_legacy=0`, no new legacy alias/fallback/flag paths.
- Spec/plan/contracts now match the code: master-owned text (`backup.passed`, real route-gap rule) is authoritative; the branch keeps capture continuity, retention, prune, `0114`.
- Dev stand at exact head `16c37ceab`: manifest `dev-16c37ceabb0d`, `0114`, smoke 13/13 pass.
- Open acceptance items are recorded honestly in `tasks.md`: T010 hardware, T019 checkout, T022 valid-token/503.

## Migration renumbering (2026-11-22)

Master now contains `0114_f200_calendar_upload_pin` and `0115_f200_strict_upload_journal` (F200 Windows), so the F297 migration was renumbered to `0116_retention_scan_maintenance` with `down_revision = "0115_f200_strict_upload_journal"`. The RLS helper body and the `retention_scan` operation are unchanged; bootstrap accepts the 0113, 0114, 0115 and 0116 heads.

Verified after the merge (Postgres 17, real roles):

- `tests/integration/test_postgres_migrations.py` + `tests/unit/test_playback_normalization_worker.py` — 31 passed;
- `tests/integration/test_rls_postgres_policies.py` + fair-use + billing monitoring + RLS contract — 328 passed, after the marker parametrization was extended to 0116;
- `tests/integration/test_deployment_backup_snapshot.py` — 7 passed;
- Swift suite 1545, retention/referral unit 17, prune 9.
