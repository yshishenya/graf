# Tasks: F296 — proof, manual cleanup, automatic WAV eviction

**Input**: `specs/296-server-cache-proof/spec.md`, `plan.md`
**Umbrella issue**: #8063
**Tests**: high-risk lane; behavior tests are written with or before implementation.

## Phase 0: Feature umbrella

- [X] T000 [US6] Зарезервировать Feature 296, создать branch/pointer и вести umbrella #8063; evidence: `specs/296-server-cache-proof/`, `.specify/feature.json`, issue #8063. — Issue #8063

## Phase 1: Server proof contract

- [ ] T001 [P] [US1] Add `DesktopPlaybackProof`, `DesktopSyncRetentionState`, `DesktopStorageStatusResponse` and additive sync-state fields, including `playback.local_media_revision_id` and a separate `finalized_upload` object, in `apps/server/src/twobrain_rec_server/api/schemas.py`; contract assertions in `tests/contract/test_desktop_status_contract.py` and `test_recording_sync_contract.py`. — Issue https://github.com/yshishenya/graf/issues/8064
- [ ] T002 [P] [US1] Add `FinalizedUploadCustody` and `finalized_upload_custody_for_revision()` in `apps/server/src/twobrain_rec_server/ingest/store.py`; delegate `archive_audio_for_revision`; tests in `tests/integration/test_desktop_sync_custody_fields.py`, including a pinned older playback revision whose archive differs from the newer meeting revision, and an active newer session plus finalized older custody with no field mixing. — Issue https://github.com/yshishenya/graf/issues/8065
- [ ] T003 [US1] Add `desktop_playback_proof()` in `apps/server/src/twobrain_rec_server/cabinet/egress.py` with actual playback revision, archive gate, object stat/size verification and fail-closed mapping; tests in `tests/contract/test_desktop_playback_proof_contract.py`, including missing object, size mismatch, bounded-read failure and pinned older revision. — Issue https://github.com/yshishenya/graf/issues/8066
- [ ] T004 [P] [US1] Add `retention_projection()` in `apps/server/src/twobrain_rec_server/deletion/retention.py`; tests in `tests/contract/test_desktop_retention_projection_contract.py`. — Issue https://github.com/yshishenya/graf/issues/8067
- [ ] T005 [US1] Wire `settings`/`storage` into `get_desktop_recording_sync_state()` in `apps/server/src/twobrain_rec_server/ingest/desktop_sync.py` and the route in `apps/server/src/twobrain_rec_server/api/ingest.py`; preserve conflict precedence, pass the resolved playback revision to custody, expose `finalized_upload` with both server and local revision IDs, and add `Cache-Control: no-store`. — Issue https://github.com/yshishenya/graf/issues/8068
- [ ] T006 [P] [US1] Add `billing/storage_status.py` and `GET /api/v1/desktop/storage/status` with owner/admin/member rules, RLS-safe session and no-5xx projection failure; tests in `tests/contract/test_desktop_storage_status_contract.py` for personal owner, corporate owner/admin, member, unknown role, projection failure and server quota not blocking capture. — Issue https://github.com/yshishenya/graf/issues/8069
- [ ] T007 [US1] Update `specs/012-server-ingest-foundation/contracts/openapi.yaml` and pass `tests/contract/test_openapi_contract_drift.py`. — Issue https://github.com/yshishenya/graf/issues/8070
- [ ] T008 [P] [US1] Add secret-egress assertions for the new fields in `tests/contract/test_recording_sync_no_secret_egress.py`. — Issue https://github.com/yshishenya/graf/issues/8071

## Phase 2: Client proof decoding

- [ ] T009 [P] [US1] Add `DesktopServerProof` with `playback.local_media_revision_id` and a separate `finalized_upload` decode, tolerant `ServerTimestamp`; wire into `DesktopUploadClient` sync-state decoding, 404 mapping and `.reloadIgnoringLocalCacheData`; tests in `DesktopUploadClientTests.swift` with different server UUID/local revision strings. — Issue https://github.com/yshishenya/graf/issues/8072
- [ ] T010 [US1] Extend `DesktopUploadReconciliation` with `proof`/`fetchedAt` and `finalizedUpload` without changing `ServerTruthFingerprint.finalizedAt` or persisting proof in the queue; tests for old server/old queue compatibility. — Issue https://github.com/yshishenya/graf/issues/8073

## Phase 3: Eligibility predicate and dry run

- [ ] T011 [P] [US3] Add pure `LocalCacheEligibility` and reason codes in `apps/macos/Shared/Sources/Models/LocalCacheEligibility.swift`; compare playback/`finalized_upload` local IDs to the item and require matching server UUIDs; full fail-closed matrix in `LocalCacheEligibilityTests.swift`. — Issue https://github.com/yshishenya/graf/issues/8074
- [ ] T012 [P] [US3] Add `LocalCacheEvictionReport` model matching `contracts/dry-run-report.schema.json`; tests in `LocalCacheEvictionReportTests.swift`. — Issue https://github.com/yshishenya/graf/issues/8075
- [ ] T013 [US3] Add read-only queue snapshot, lossy item decode, bounded off-main footprint probe and `LocalCacheEvictionDryRunService` in `apps/macos/RecApp/Sources/Upload/`; no-mutation tests in `LocalCacheEvictionDryRunTests.swift`, including a synthetic 1.5+ GB historical queue with ~1.1 GB actual files proving the actual footprint wins (the missing F295 SC-001 equivalent). — Issue https://github.com/yshishenya/graf/issues/8076
- [ ] T014 [US3] Add diagnostics-only entry point (`GRAF_RUN_CACHE_EVICTION_DRY_RUN=1`) and sanitized `AppLog` summary; tests that no UI/render path calls it. — Issue https://github.com/yshishenya/graf/issues/8077

## Phase 4: Manual WAV cleanup

- [ ] T015 [US2] Add `LocalCacheCleanupService` in `apps/macos/RecApp/Sources/Upload/` with fresh revalidation, path/symlink checks, review/manifest preservation, account/deletion generation fence, idempotency and `CleanupReceipt`; tests in `LocalCacheCleanupTests.swift`, including pending-intent crash/retry, symlink swap, idempotency and only-WAV deletion. — Issue https://github.com/yshishenya/graf/issues/8078
- [ ] T016 [US2] Add «Освободить место» to the existing local recordings surface in `ContentView`/`DesktopMeetingShellView` with confirmation, space amount, safe copy, accessibility labels and no new library; tests in `CaptureControlV5Tests` or `DesktopCalendarReminderTests`. — Issue https://github.com/yshishenya/graf/issues/8079
- [ ] T017 [US2] Add regression tests for cleanup followed by full purge, local playback, local-only mode, failed/unsent items and queue identity preservation. — Issue https://github.com/yshishenya/graf/issues/8080

## Phase 5: Automatic WAV eviction

- [ ] T018 [P] [US5] Replace the interim local buffer policy with the PRD baseline (5 GB / 80% / 95% / `min(10 GB, 10%)` / 7 days) in `LocalBufferService`/`LocalBufferPolicy`; tests for reserve, thresholds, capture gate and that server quota is not a capture gate. — Issue https://github.com/yshishenya/graf/issues/8081
- [ ] T019 [US5] Add `LocalCacheEvictionScheduler`/coordinator with single-flight, bounded off-main runs, oldest verified WAV first, stop at warning, kill switch and receipts; tests in `LocalCacheEvictionSchedulerTests.swift`, including pending-intent crash/retry, oldest-first order, stop at warning and no double delete. — Issue https://github.com/yshishenya/graf/issues/8082
- [ ] T020 [US5] Add cache status, explanation and kill-switch toggle to the existing settings/local cache surface with accessibility; tests for copy, toggle, operator override, immediate effect without restart and no false error styling; use `contracts/ux-copy.md`. — Issue https://github.com/yshishenya/graf/issues/8083
- [ ] T021 [US5] Add the full automatic fail-closed matrix: proof missing/stale, archive false, retention unsafe, deletion/purge open, account switch, review missing, kill switch, no double delete. — Issue https://github.com/yshishenya/graf/issues/8084

## Phase 6: Gates and release

- [ ] T022 [US1] Run focused server pytest, OpenAPI drift and full server contract lane; record evidence. — Issue https://github.com/yshishenya/graf/issues/8085
- [ ] T023 [US1] Run full `apps/macos/Scripts/run-swift-tests.sh`, ContractValidation and `python3 scripts/validate-changelog-fragments.py`; align the F295 meeting-detection freshness window with the provider TTL (60 s) and add a regression test; record evidence. — Issue https://github.com/yshishenya/graf/issues/8086
- [ ] T024 [US1] Start the independent reviewer-owned checklist review **before implementation**; reviewer may edit only `checklists/*` and its report, must mark `[x]` only with evidence, and must reread/report totals. — Issue https://github.com/yshishenya/graf/issues/8087
- [ ] T025 [US1] Run `$speckit-analyze` until 0 CRITICAL/HIGH findings; record the result. — Issue https://github.com/yshishenya/graf/issues/8088
- [ ] T026 [US1] Run `$speckit-taskstoissues`, create canonical child issues, link every task to its issue and keep #8063 as umbrella. — Issue https://github.com/yshishenya/graf/issues/8089
- [ ] T027 [US6] Open a PR with exact-SHA evidence, `governance-fast`, `macos-pr`, `pr-metadata`, and `validate-pr-checks.py`. — Issue https://github.com/yshishenya/graf/issues/8090
- [ ] T028 [US6] Freeze the candidate, run `release-full`, Developer ID/notarization/staple/Gatekeeper/Sparkle/live appcast, `cd-remote.sh --dry-run`, production deploy, health/runtime SHA. — Issue https://github.com/yshishenya/graf/issues/8091
- [ ] T029 [US6] Run a production dry run; verify zero file/queue mutation and zero false eligibility. Enable Phase B, then Phase C only if evidence is clean; otherwise keep Phase C disabled. — Issue https://github.com/yshishenya/graf/issues/8092
- [ ] T030 [US6] Update `validation.md`, `changes/unreleased/F296.yaml`, `docs/current-product-status.md`; run `$speckit-converge`; run `scripts/validate-issue-closeout.py` for each child issue and #8063, then close them with Russian evidence. — Issue https://github.com/yshishenya/graf/issues/8093

## Dependencies

- T001–T008 before T009–T010.
- T009–T010 before T011–T014.
- T011–T014 before T015–T017.
- T015–T017 before T018–T021.
- T018–T021 before T022–T023.
- T024–T026 before implementation starts.
- T027 before T028; T028 before T029; T029 before T030.

## Out Of Scope

- Deleting review audio, manifest, the recording directory or queue rows.
- New queue schema, `cached`/`evicted` enum cases, SQLite, app-level encryption, backup policy.
- Pin/offline, arbitrary budget formulas outside PRD, admin limits.
- Repairing terminal `storage_capacity_exceeded` jobs and upgrade flows.
- Changing server quota, tariffs or retention defaults.
