# Tasks: Review M4A Normalization

**Input**: Design documents from `specs/099-review-m4a-normalization/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `checklists/requirements.md`, `checklists/media.md`, `checklists/automation.md`, `checklists/lifecycle.md`

**Tests**: Required. Feature 099 is a high-risk active Spec Kit slice touching untrusted media, accepted-source custody, PostgreSQL/MinIO/Temporal, CPU/disk subprocess work, RLS, deletion, diagnostics, browser playback and production backfill. Test tasks precede implementation in every phase.

**Organization**: Tasks are dependency ordered and grouped by the seven user stories in `spec.md`. P1 stories run before P2 stories. A task is checked `[X]` only after its exact validation receipt exists.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it uses different files and has no dependency on unfinished tasks in the same phase.
- **[Story]**: Maps to `US1`–`US7` in `spec.md`.
- Every task names exact repository paths.
- No task may introduce a user/admin retry, reprocess, repair or backfill control.

## Phase 1: Setup And Baseline

**Purpose**: Anchor the clean 099 worktree, preserve the unrelated dirty detached worktree and create safe synthetic/evidence surfaces.

- [X] T001 Record branch, exact `origin/master` base, clean-worktree ownership, feature anchor and explicit 097 exclusion in `.specify/feature.json` and `specs/099-review-m4a-normalization/validation/baseline.md`
- [X] T002 [P] Add deterministic synthetic media/probe/state builders with no committed raw audio in `apps/server/tests/fixtures/playback_normalization.py` and document fixture hygiene in `apps/server/tests/fixtures/README.md`
- [X] T003 [P] Record the existing ingest/playback/Temporal/Docker/RLS/macOS contract baseline and focused pre-change commands in `specs/099-review-m4a-normalization/validation/baseline.md`
- [X] T004 [P] Create the FR/SC/task evidence ledger and forbidden-content rules in `specs/099-review-m4a-normalization/validation/traceability.md`

---

## Phase 2: Foundational Schema, Media Gate And Isolation

**Purpose**: Add the durable model, strict media primitives and isolated runtime required by every user story.

**⚠️ CRITICAL**: No user-story implementation begins until migration, RLS, media-profile and process-isolation foundations pass.

### Foundation Tests

- [X] T005 [P] Add failing job/attempt/backfill transition, retry-due and reason/profile tests in `apps/server/tests/unit/test_playback_normalization_state.py`
- [X] T006 [P] Add failing probe/BMFF/profile/stream-selection/process-bound tests in `apps/server/tests/unit/test_playback_normalization_profile.py`, `apps/server/tests/unit/test_playback_normalization_bmff.py`, and `apps/server/tests/unit/test_playback_normalization_selection.py`
- [X] T007 [P] Add failing SQLite/PostgreSQL upgrade/reconciliation/downgrade, locking and partial-uniqueness coverage in `apps/server/tests/integration/test_playback_normalization_migrations.py` and `apps/server/tests/integration/test_playback_normalization_postgres.py`
- [X] T008 [P] Add failing PostgreSQL force-RLS/table-inventory/policy/maintenance-operation requirements in `apps/server/tests/contract/test_playback_normalization_rls_contract.py`, `apps/server/tests/contract/test_rls_table_inventory_contract.py`, `apps/server/tests/contract/test_rls_policy_matrix_contract.py`, `apps/server/tests/fixtures/rls.py`, and `apps/server/tests/integration/test_rls_postgres_migrations.py`
- [X] T009 [P] Add failing metadata allowlist and forbidden filename/path/key/stderr/content tests in `apps/server/tests/unit/test_playback_normalization_audit.py` and `apps/server/tests/contract/test_playback_normalization_no_secret_egress.py`

### Foundation Implementation

- [X] T010 Define profile, job/attempt/backfill states, safe reasons, retry classes and typed transitions in `apps/server/src/twobrain_rec_server/normalization/statuses.py`
- [X] T011 Add canonical validation/derivation fields to `TrackArtifact` and create normalization job/attempt/backfill models in `apps/server/src/twobrain_rec_server/db/models/ingest.py`, `apps/server/src/twobrain_rec_server/db/models/normalization.py`, and `apps/server/src/twobrain_rec_server/db/models/__init__.py`
- [X] T012 Implement additive portable migration `0022`, partial canonical uniqueness, force-RLS policies and reversible downgrade in `apps/server/src/twobrain_rec_server/db/migrations/versions/0022_playback_normalization.py`
- [X] T013 Register new tables and narrow `playback_normalization_inventory`/`playback_normalization_dispatch` operations in `apps/server/src/twobrain_rec_server/db/rls_validation.py`, `apps/server/src/twobrain_rec_server/db/tenant_context.py`, `apps/server/tests/fixtures/rls.py`, and `specs/031-rls-hardening/contracts/rls-policy-matrix.md`
- [X] T014 Add immutable attempt/canonical key builders and chunked file-object transfer helpers in `apps/server/src/twobrain_rec_server/storage/object_keys.py` and `apps/server/src/twobrain_rec_server/storage/minio_client.py`
- [X] T015 Implement the strict normalization audit allowlist and safe event receipts in `apps/server/src/twobrain_rec_server/normalization/audit.py`
- [X] T016 Implement bounded no-shell process execution, protocol restriction, cancellation, output caps and typed probe parsing in `apps/server/src/twobrain_rec_server/normalization/media.py`
- [X] T017 Implement stdlib BMFF validation, canonical profile validation and deterministic single-stream/dual-source selection in `apps/server/src/twobrain_rec_server/normalization/media.py`
- [X] T018 Implement strict copy, lossless fast-start remux, AAC-LC transcode, dual-source mix and full-decode output gate in `apps/server/src/twobrain_rec_server/normalization/media.py`
- [X] T019 Add normalization queue, timeouts, limits, cadence and work-directory settings with production validation in `apps/server/src/twobrain_rec_server/config.py`, `apps/server/.env.example`, and `infra/env/rec.production.env.example`
- [X] T020 Add a media-only Debian Bookworm FFmpeg target and non-root 1-CPU/1-GiB/concurrency-1 service definitions in `infra/server/Dockerfile`, `infra/docker-compose.yml`, and `infra/docker-compose.dev.yml`

**Checkpoint**: Schema, RLS, immutable keys, safe audit, strict media engine and isolated media runtime are independently testable.

---

## Phase 3: User Story 1 - New Recording Automatically Gets Playback Audio (Priority: P1) 🎯 MVP

**Goal**: Every accepted first-party recording automatically reaches one validated canonical M4A without waiting for transcript/summary and without user action.

**Independent Test**: Finalize accepted microphone/system tracks with absent, valid and invalid optional playback candidates; prove durable job creation, automatic worker execution, deterministic fallback, full canonical validation, one published artifact and truthful cabinet playback.

### Tests For User Story 1

- [X] T021 [P] [US1] Add failing optional-playback role, checksum, fingerprint-exclusion and accepted-source transaction tests in `apps/server/tests/unit/test_manifest_validation.py`, `apps/server/tests/integration/test_finalize_integrity.py`, and `apps/server/tests/integration/test_playback_normalization_finalize.py`
- [X] T022 [P] [US1] Add failing candidate-copy/remux and microphone/system fallback workflow tests in `apps/server/tests/integration/test_playback_normalization_workflow.py`
- [X] T023 [P] [US1] Add failing immutable-attempt publication, duplicate publisher and one-canonical-artifact tests in `apps/server/tests/integration/test_playback_normalization_idempotency.py`
- [X] T024 [P] [US1] Add failing independent playback status, authorized Range route and cabinet state/render tests in `apps/server/tests/contract/test_playback_status_contract.py`, `apps/server/tests/integration/test_cabinet_playback_route.py`, `apps/server/tests/unit/test_artifact_egress_view_models.py`, `apps/server/tests/unit/test_cabinet_view_models.py`, and `apps/server/tests/unit/test_cabinet_web_shell.py`

### Implementation For User Story 1

- [X] T025 [US1] Accept first-party `manifest+microphone+system` with an optional playback descriptor while preserving manual-media role rules in `apps/server/src/twobrain_rec_server/ingest/manifest.py`, `apps/server/src/twobrain_rec_server/api/schemas.py`, and `apps/server/src/twobrain_rec_server/ingest/sessions.py`
- [X] T026 [US1] Exclude the optional playback derivative from authoritative source fingerprints while retaining its verified candidate digest in `apps/server/src/twobrain_rec_server/ingest/media_revisions.py` and `apps/server/src/twobrain_rec_server/ingest/finalize.py`
- [X] T027 [US1] Persist candidate-as-unvalidated and upsert one normalization job inside the accepted-source finalize transaction in `apps/server/src/twobrain_rec_server/ingest/store.py`, `apps/server/src/twobrain_rec_server/ingest/finalize.py`, and `apps/server/src/twobrain_rec_server/normalization/service.py`
- [X] T028 [US1] Dispatch normalization only after accepted-source commit and keep it independent from MediaScribe enablement/result state in `apps/server/src/twobrain_rec_server/ingest/processing_dispatch.py`, `apps/server/src/twobrain_rec_server/ingest/finalize.py`, and `apps/server/src/twobrain_rec_server/normalization/pickup.py`
- [X] T029 [US1] Implement candidate-first then explicit microphone/system fallback source custody and download staging in `apps/server/src/twobrain_rec_server/normalization/service.py`
- [X] T030 [US1] Implement deterministic Temporal workflow/activity inputs with revision/profile identity and no media/content payloads in `apps/server/src/twobrain_rec_server/workflows/playback_normalization_workflow.py` and `apps/server/src/twobrain_rec_server/workflows/temporal_client.py`
- [X] T031 [US1] Implement the separate capability-gated media worker executable and startup cleanup in `apps/server/src/twobrain_rec_server/normalization/worker.py`
- [X] T032 [US1] Register immutable attempt output, recheck source/lifecycle, publish one canonical `TrackArtifact` and clean losing attempts in `apps/server/src/twobrain_rec_server/normalization/service.py`
- [X] T033 [US1] Derive one durable playback state independent from processing status in `apps/server/src/twobrain_rec_server/cabinet/egress.py`, `apps/server/src/twobrain_rec_server/cabinet/queries.py`, `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, and `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T034 [US1] Restrict playback egress to the validated canonical artifact while preserving bounded single-range streaming in `apps/server/src/twobrain_rec_server/cabinet/egress.py` and `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [X] T035 [US1] Update canonical OpenAPI playback/read schemas with no repair mutation and exact drift coverage in `specs/012-server-ingest-foundation/contracts/openapi.yaml`, `apps/server/tests/contract/test_playback_normalization_contract.py`, and `apps/server/tests/contract/test_openapi_contract_drift.py`
- [X] T036 [US1] Render accessible localized preparing/available/unavailable/deleting/deleted states with no dead player or repair control in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_list.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_detail.html`, and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T037 [US1] Run the US1 finalize/candidate/fallback/publication/status filters and record FR-001–FR-007/FR-038/FR-042 and SC receipts in `specs/099-review-m4a-normalization/validation/us1-first-party.md`

**Checkpoint**: A new first-party accepted source reaches validated playback automatically and independently from transcription.

---

## Phase 4: User Story 2 - Manual Upload Automatically Converts (Priority: P1)

**Goal**: Every supported valid manual audio/video upload with usable audio becomes canonical playback automatically while title/calendar behavior remains stable.

**Independent Test**: Upload every supported container/codec class, canonical/non-fast-start M4A and deterministic multi-stream cases; prove byte-copy/remux/transcode selection, full decode, one playback object, title precedence and no calendar match.

### Tests For User Story 2

- [X] T038 [P] [US2] Add failing manual accepted-source scheduling, title precedence, calendar exclusion and transcript-independent tests in `apps/server/tests/integration/test_manual_media_upload.py`, `apps/server/tests/integration/test_playback_normalization_finalize.py`, and `apps/server/tests/integration/test_no_processing_side_effects.py`
- [X] T039 [P] [US2] Add failing real synthetic WAV/MP3/AAC/FLAC/Ogg/M4A/MP4/MOV/M4V/WebM/MKV matrix and wrong-extension tests in `apps/server/tests/integration/test_playback_normalization_media_matrix.py`
- [X] T040 [P] [US2] Add failing full-canonical copy, non-fast-start lossless-remux and audio-profile transcode cases in `apps/server/tests/integration/test_playback_normalization_reuse.py`
- [X] T041 [P] [US2] Add failing one-usable/unique-default/ambiguous-stream and selected-stream decode-failure cases in `apps/server/tests/integration/test_playback_normalization_media_matrix.py`

### Implementation For User Story 2

- [X] T042 [US2] Schedule normalization from manual accepted-source commit before/independently from processing dispatch in `apps/server/src/twobrain_rec_server/ingest/manual_media_upload.py` and `apps/server/src/twobrain_rec_server/normalization/service.py`
- [X] T043 [US2] Select the accepted manual `media` artifact and enforce byte-inspected supported format/stream rules in `apps/server/src/twobrain_rec_server/normalization/service.py` and `apps/server/src/twobrain_rec_server/normalization/media.py`
- [X] T044 [US2] Preserve user title/file-name fallback and explicit no-calendar-match behavior through normalization/retry in `apps/server/src/twobrain_rec_server/ingest/manual_media_upload.py`, `apps/server/src/twobrain_rec_server/ingest/meetings.py`, and `apps/server/src/twobrain_rec_server/cabinet/queries.py`
- [X] T045 [US2] Add disposable capability and end-to-end media runners with full-decode and zero-residue receipts in `infra/scripts/test-playback-normalization-container.sh` and `infra/scripts/test-playback-normalization-integration.sh`
- [X] T046 [US2] Run the US2 manual/matrix/reuse/remux/transcode/title filters and record FR-003/FR-008/FR-009/FR-038/FR-039/FR-040 receipts in `specs/099-review-m4a-normalization/validation/us2-manual-media.md`

**Checkpoint**: Every supported valid manual source converts automatically; ambiguous or objectively invalid media never produces a guessed artifact.

---

## Phase 5: User Story 3 - Retry, Refresh And Restart Converge Automatically (Priority: P1)

**Goal**: Transient failures recover indefinitely in bounded cycles without source re-upload or user/admin action, and duplicate triggers converge to one job/artifact.

**Independent Test**: Inject dispatch loss, dependency outage, timeout, temp pressure, worker termination, uploaded-object/pre-commit crash, expired lease, duplicate finalize/pickup and multiple browser tabs; prove persisted automatic recovery and one canonical winner.

### Tests For User Story 3

- [X] T047 [P] [US3] Add failing four-attempt, exponential-delay, 15m/1h/6h/24h/daily-cycle and stopping-condition tests in `apps/server/tests/unit/test_playback_normalization_retry.py` and `apps/server/tests/integration/test_playback_normalization_retry.py`
- [X] T048 [P] [US3] Add failing lost-dispatch, restart, expired-lease, startup-orphan and deduplicated-incident recovery tests in `apps/server/tests/integration/test_playback_normalization_restart.py` and `apps/server/tests/integration/test_playback_normalization_incidents.py`
- [X] T049 [P] [US3] Add failing duplicate finalize/workflow/pickup/publication-loss concurrency tests in `apps/server/tests/integration/test_playback_normalization_idempotency.py`
- [X] T050 [P] [US3] Add failing no-repair-endpoint, refresh/two-tab/reconnect and automatic-recovery projection tests in `apps/server/tests/contract/test_playback_status_contract.py` and `apps/server/tests/integration/test_cabinet_meeting_detail.py`

### Implementation For User Story 3

- [X] T051 [US3] Implement atomic due-job lease/pickup, deterministic duplicate reuse and expired-lease recovery in `apps/server/src/twobrain_rec_server/normalization/pickup.py` and `apps/server/src/twobrain_rec_server/normalization/service.py`
- [X] T052 [US3] Implement bounded Temporal attempt retries and persisted long-term automatic cooldown cycles in `apps/server/src/twobrain_rec_server/workflows/playback_normalization_workflow.py` and `apps/server/src/twobrain_rec_server/normalization/service.py`
- [X] T053 [US3] Implement 60-second reconciliation for lost dispatch, restart, missing-ready artifact and unpublished attempt cleanup in `apps/server/src/twobrain_rec_server/normalization/pickup.py` and `apps/server/src/twobrain_rec_server/normalization/worker.py`
- [X] T054 [US3] Deduplicate metadata-only cooldown/escalation incidents without exposing low-level media output in `apps/server/src/twobrain_rec_server/normalization/audit.py` and `apps/server/src/twobrain_rec_server/support/incidents.py`
- [X] T055 [US3] Keep polling/reconnect strictly read-only and render automatic recovery without retry/reprocess/backfill actions in `apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py`, `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T056 [US3] Run the US3 retry/restart/idempotency/concurrency/UI filters and record FR-010–FR-013/FR-023/FR-024/FR-035/FR-040 receipts in `specs/099-review-m4a-normalization/validation/us3-automatic-recovery.md`

**Checkpoint**: Temporary failures and duplicate triggers converge automatically with no user/admin repair surface.

---

## Phase 6: User Story 7 - Accepted Ingest Remains Authoritative (Priority: P1)

**Goal**: Normalization consumes only accepted recording lineage and never creates a parallel upload/finalize, MediaScribe or native-client source of truth.

**Independent Test**: Attempt normalization from raw/in-flight/unfinalized/unmanaged inputs, duplicate source paths and derivative-only changes; prove rejection, unchanged authoritative revision fingerprint, separate MediaScribe request mapping and unchanged macOS upload behavior.

### Tests For User Story 7

- [X] T057 [P] [US7] Add failing raw-part/unfinalized/unmanaged/source-mismatch custody tests in `apps/server/tests/contract/test_playback_normalization_contract.py` and `apps/server/tests/integration/test_playback_normalization_finalize.py`
- [X] T058 [P] [US7] Add failing no-competing-endpoint and MediaScribe microphone/system/manual-source separation tests in `apps/server/tests/integration/test_mediascribe_submit.py`, `apps/server/tests/unit/test_mediascribe_request_mapping.py`, and `apps/server/tests/contract/test_ingest_openapi_contract.py`
- [X] T059 [P] [US7] Add/extend macOS optional playback descriptor, required source WAV and queue retry contract tests in `apps/macos/Shared/Tests/SystemAudioRecordingPackageTests.swift`, `apps/macos/Shared/Tests/LocalRecordingManifestTests.swift`, `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`, and `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`

### Implementation For User Story 7

- [X] T060 [US7] Preserve authoritative accepted-role fingerprinting and exclude playback derivatives from MediaScribe source selection in `apps/server/src/twobrain_rec_server/ingest/media_revisions.py`, `apps/server/src/twobrain_rec_server/processing/store.py`, and `apps/server/src/twobrain_rec_server/processing/submit.py`
- [X] T061 [US7] Keep normalization internal to existing finalize/manual flows and prove no new public source/upload mutation in `apps/server/src/twobrain_rec_server/api/ingest.py`, `apps/server/src/twobrain_rec_server/api/processing.py`, and `specs/012-server-ingest-foundation/contracts/openapi.yaml`
- [X] T062 [US7] Run accepted-source/MediaScribe/OpenAPI/macOS regression filters and record FR-026–FR-028/FR-033/SC-013/SC-014 receipts in `specs/099-review-m4a-normalization/validation/us7-ingest-boundary.md`

**Checkpoint**: Playback derivation is a consumer of accepted lineage, never a second ingestion system.

---

## Phase 7: User Story 4 - Legacy Playback Backfills Automatically (Priority: P2)

**Goal**: Every eligible legacy record is inventoried before mutation and then automatically preserves, validates, regenerates or truthfully classifies playback in bounded batches.

**Independent Test**: Seed workspaces with valid, non-fast-start, invalid, duplicate, missing-source and zero-eligible records; interrupt every inventory page/dispatch boundary; prove cursor resume, priority, no pre-inventory mutation, no title/transcript change and complete counters.

### Tests For User Story 4

- [X] T063 [P] [US4] Add failing per-workspace zero/nonzero inventory, cursor, action and completion-state tests in `apps/server/tests/integration/test_playback_normalization_backfill.py`
- [X] T064 [P] [US4] Add failing page-100/batch-25/concurrency-1/restart and new-ingest-over-retry-over-backfill priority tests in `apps/server/tests/integration/test_playback_normalization_priority.py`
- [X] T065 [P] [US4] Add failing preserve-valid/validate-candidate/remux/regenerate/missing-source/duplicate-legacy decisions in `apps/server/tests/integration/test_playback_normalization_backfill.py`
- [X] T066 [P] [US4] Add failing bounded global-maintenance-to-exact-worker-tenant transition tests in `apps/server/tests/integration/test_rls_maintenance_context.py` and `apps/server/tests/integration/test_rls_worker_context.py`

### Implementation For User Story 4

- [X] T067 [US4] Implement per-workspace backfill run persistence, cursor/counters and safe decision receipts in `apps/server/src/twobrain_rec_server/normalization/service.py`
- [X] T068 [US4] Implement inventory-first keyset paging with zero-eligible completion and no legacy mutation before `inventory_complete` in `apps/server/src/twobrain_rec_server/normalization/pickup.py`
- [X] T069 [US4] Implement bounded dispatch and strict new-ingest/due-retry/legacy priority under the two maintenance operations in `apps/server/src/twobrain_rec_server/normalization/pickup.py`
- [X] T070 [US4] Resume inventory/dispatch automatically at worker startup and reuse completed profile runs without duplicate work in `apps/server/src/twobrain_rec_server/normalization/worker.py`
- [X] T071 [US4] Expose only aggregate read-only run/backlog/age/reason counters in `apps/server/src/twobrain_rec_server/admin/metrics.py`, `apps/server/src/twobrain_rec_server/admin/view_models.py`, and `apps/server/src/twobrain_rec_server/api/admin.py`
- [X] T072 [US4] Run the US4 inventory/backfill/RLS/priority/restart filters and record FR-014–FR-017/FR-033/FR-034/FR-041 receipts in `specs/099-review-m4a-normalization/validation/us4-backfill.md`

**Checkpoint**: Legacy records converge automatically in bounded, restart-safe, tenant-safe batches.

---

## Phase 8: User Story 5 - Impossible Media Fails Clearly, System Failures Keep Recovering (Priority: P2)

**Goal**: Corrupt, unsupported, no-audio, encrypted, ambiguous and over-limit sources terminate truthfully, while dependency/resource/generated-output failures remain automatic recovery states.

**Independent Test**: Exercise every source/system failure class and prove deterministic durable reason, no partial playback, no forbidden diagnostics and no user/admin repair instruction.

### Tests For User Story 5

- [X] T073 [P] [US5] Add failing empty/corrupt/encrypted/no-audio/ambiguous/unsupported/stream-limit/duration-limit/source-missing/source-mismatch matrix in `apps/server/tests/integration/test_playback_normalization_media_matrix.py`
- [X] T074 [P] [US5] Add failing safe RU/EN copy, reason precedence, transcript/playback independence and no-repair-affordance tests in `apps/server/tests/contract/test_playback_status_contract.py`, `apps/server/tests/unit/test_cabinet_view_models.py`, and `apps/server/tests/unit/test_cabinet_web_shell.py`
- [X] T075 [P] [US5] Add failing temp-pressure/dependency/timeout/output-cap/generated-output-invalid classification and cleanup tests in `apps/server/tests/integration/test_playback_normalization_failures.py`

### Implementation For User Story 5

- [X] T076 [US5] Map source-objective failures to terminal reasons and system/resource/output failures to retryable ownership in `apps/server/src/twobrain_rec_server/normalization/statuses.py` and `apps/server/src/twobrain_rec_server/normalization/service.py`
- [X] T077 [US5] Prevent partial/truncated/failed/unvalidated output publication and preserve cleanup ownership in `apps/server/src/twobrain_rec_server/normalization/media.py` and `apps/server/src/twobrain_rec_server/normalization/service.py`
- [X] T078 [US5] Project safe localized terminal/preparing reasons with no retry/re-upload/contact-admin instruction in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, and `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T079 [US5] Persist one deduplicated safe operational incident for impossible legacy/source and system cooldown escalation cases in `apps/server/src/twobrain_rec_server/support/incidents.py` and `apps/server/src/twobrain_rec_server/normalization/audit.py`
- [X] T080 [US5] Run the US5 terminal/retryable/status/privacy filters and record FR-011–FR-013/FR-021/FR-031/FR-037/FR-039/FR-040 receipts in `specs/099-review-m4a-normalization/validation/us5-failure-truth.md`

**Checkpoint**: Impossible inputs terminate honestly; recoverable system problems continue automatically.

---

## Phase 9: User Story 6 - Lifecycle, Privacy And Operations Stay Truthful (Priority: P2)

**Goal**: Publication cannot race past deletion/retention, all media/temp objects are accounted, tenants remain isolated and rollout/rollback evidence is exact.

**Independent Test**: Race deletion/purge against every job/attempt state, force worker/storage/database failures, cross tenant boundaries, roll migration/runtime forward and back, and prove deletion wins, cleanup ownership, safe reports, RLS and no content leakage.

### Tests For User Story 6

- [X] T081 [P] [US6] Add failing queued/running/uploaded/publishing/retry deletion-race and orphan-cleanup tests in `apps/server/tests/integration/test_playback_normalization_deletion.py`
- [X] T082 [P] [US6] Add failing retention/report/canonical/candidate/attempt/temp accounting tests in `apps/server/tests/contract/test_retention_deletion_contract.py`, `apps/server/tests/integration/test_retention_policy_execution.py`, and `apps/server/tests/integration/test_meeting_deletion_workflow.py`
- [X] T083 [P] [US6] Add failing tenant-access, force-RLS, maintenance-boundary and forbidden-content tests in `apps/server/tests/contract/test_playback_normalization_rls_contract.py`, `apps/server/tests/integration/test_rls_postgres_policies.py`, and `apps/server/tests/contract/test_playback_normalization_no_secret_egress.py`
- [X] T084 [P] [US6] Add failing media-worker readiness, non-root/resource, additive rolling-version and compatibility-rollback tests in `apps/server/tests/integration/test_playback_normalization_readiness.py`, `apps/server/tests/integration/test_compose_hardening.py`, and `apps/server/tests/unit/test_deployment_rollback_decisions.py`

### Implementation For User Story 6

- [X] T085 [US6] Serialize publish against meeting lifecycle, make deletion win and clean registered attempts/local work in `apps/server/src/twobrain_rec_server/normalization/service.py`, `apps/server/src/twobrain_rec_server/deletion/service.py`, and `apps/server/src/twobrain_rec_server/deletion/local_purge.py`
- [X] T086 [US6] Add candidate/canonical/job/attempt/backfill lifecycle truth to retention execution and deletion reports in `apps/server/src/twobrain_rec_server/deletion/retention.py`, `apps/server/src/twobrain_rec_server/deletion/report.py`, and `apps/server/src/twobrain_rec_server/deletion/policy.py`
- [X] T087 [US6] Enforce exact request/worker/maintenance RLS context on every normalization query and object action in `apps/server/src/twobrain_rec_server/normalization/service.py`, `apps/server/src/twobrain_rec_server/normalization/pickup.py`, and `apps/server/src/twobrain_rec_server/db/tenant_context.py`
- [X] T088 [US6] Add capability-only ready/degraded/blocked media-worker evidence and safe aggregate metrics in `apps/server/src/twobrain_rec_server/readiness/default_evidence.py`, `apps/server/src/twobrain_rec_server/readiness/feature_ids.py`, `apps/server/src/twobrain_rec_server/readiness/matrix.py`, and `apps/server/src/twobrain_rec_server/admin/metrics.py`
- [X] T089 [US6] Stop the existing processing worker root override unless evidenced, keep the media worker non-root and validate exact compose resources in `infra/docker-compose.yml`, `infra/docker-compose.dev.yml`, and `apps/server/tests/integration/test_compose_hardening.py`
- [X] T090 [US6] Extend deployment dry-run/execute gates for migration, image/profile capability, media worker, retry, backfill, Range and cleanup evidence in `infra/scripts/cd-remote.sh`, `apps/server/src/twobrain_rec_server/deployment.py`, and `apps/server/tests/integration/test_deployment_readiness_gates.py`
- [X] T091 [US6] Implement additive-version ordering and guarded rollback decisions that never re-enable unvalidated legacy playback in `apps/server/src/twobrain_rec_server/deployment.py` and `apps/server/tests/unit/test_deployment_rollback_decisions.py`
- [X] T092 [US6] Run the US6 deletion/retention/RLS/readiness/rolling-rollback filters and record FR-018–FR-020/FR-030/FR-036/FR-037 receipts in `specs/099-review-m4a-normalization/validation/us6-lifecycle.md`

**Checkpoint**: Media derivation is lifecycle-accounted, tenant-safe, resource-isolated and rollback-safe.

---

## Phase 10: Cross-Cutting Validation And PR Readiness

**Purpose**: Prove the complete automatic-conversion guarantee, simplify the diff, update product truth and prepare an evidence-backed PR without touching feature 097.

- [X] T093 Run the exact media-container capability gate from `specs/099-review-m4a-normalization/quickstart.md` through `infra/scripts/test-playback-normalization-container.sh` and record version/capabilities/full-decode/zero-residue evidence in `specs/099-review-m4a-normalization/validation/media-capability.md`
- [X] T094 Run the real synthetic supported/failure matrix through `infra/scripts/test-playback-normalization-integration.sh` and record per-format safe results in `specs/099-review-m4a-normalization/validation/media-matrix.md`
- [X] T095 Run all focused unit/contract/integration suites from `specs/099-review-m4a-normalization/quickstart.md` and record exact counts in `specs/099-review-m4a-normalization/validation/implementation-evidence.md`
- [X] T096 [P] Run focused Ruff/type/import checks for every changed server module and record exact output in `specs/099-review-m4a-normalization/validation/implementation-evidence.md`
- [X] T097 Run SQLite upgrade/downgrade and disposable PostgreSQL migration/partial-uniqueness/RLS/concurrency suites and record cleanup truth in `specs/099-review-m4a-normalization/validation/migration-evidence.md`
- [X] T098 [P] Run unchanged macOS manifest/package/upload/queue regressions and record whether an app rebuild/install is actually required in `specs/099-review-m4a-normalization/validation/macos-regression.md`
- [X] T099 Run authorized working-copy `test-rec` first-party candidate/remux/fallback and manual conversion E2E with full decode and cleanup in `specs/099-review-m4a-normalization/validation/local-e2e.md`
- [X] T100 Run real Chrome and embedded macOS cabinet preparing/available/unavailable/play/seek/two-tab/accessibility parity and record safe screenshots/results in `specs/099-review-m4a-normalization/validation/browser-e2e.md`
- [X] T101 Race deletion and execute feature temp/object/test-record cleanup, proving residue zero in `specs/099-review-m4a-normalization/validation/cleanup.md`
- [X] T102 Run the near-limit 1-CPU/1-GiB/6-GiB benchmark within the 6-hour activity gate and record duration/resource buckets without media paths in `specs/099-review-m4a-normalization/validation/performance.md`
- [X] T103 Reconcile all 80/80 requirement-quality checklist items and every FR/SC against final code/evidence in `specs/099-review-m4a-normalization/checklists/requirements.md`, `specs/099-review-m4a-normalization/checklists/media.md`, `specs/099-review-m4a-normalization/checklists/automation.md`, `specs/099-review-m4a-normalization/checklists/lifecycle.md`, and `specs/099-review-m4a-normalization/validation/traceability.md`
- [X] T104 [P] Add user-visible/architecture/QA/operations/release-readiness changes under `[Unreleased]` in `CHANGELOG.md`
- [X] T105 [P] Update implemented/not-released/backfill/app-impact/deferred-097 truth in `docs/current-product-status.md`
- [X] T106 Review the final diff against `docs/agent-guidance/ponytail-upstream.md` and record simplification/debt decisions in `specs/099-review-m4a-normalization/validation/ponytail-review.md`
- [X] T107 Run ordinary authorization/RLS/subprocess/redaction/deletion acceptance gates and state explicitly that they do not complete the deferred 097 Codex Security scan in `specs/099-review-m4a-normalization/validation/implementation-evidence.md`
- [X] T108 Run `infra/scripts/ci-local.sh` once after the last code-affecting fix and record exact SHA/result/counts/known limits in `specs/099-review-m4a-normalization/validation/implementation-evidence.md`
- [X] T109 Reconcile every completed task with its GitHub issue and exact evidence receipt in `specs/099-review-m4a-normalization/tasks.md` and `specs/099-review-m4a-normalization/validation/traceability.md`
- [X] T110 Prepare the Russian PR closeout, obtain explicit user approval for the implementation commit, and stage only 099-owned files with branch/status evidence in `specs/099-review-m4a-normalization/validation/pr-closeout.md`

---

## Phase 11: Release, Deploy And Production Closeout

**Purpose**: Complete the goal’s release obligation only after validated PR merge and fresh release/deploy approval.

- [X] T111 Merge the approved 099 PR and record exact PR/merge SHA plus task/issue linkage in `specs/099-review-m4a-normalization/validation/release-closeout.md`
- [X] T112 Choose the next free CalVer and run `./scripts/prepare-release.sh YYYY.MM.DD.N`, recording the generated diff in `specs/099-review-m4a-normalization/validation/release-closeout.md`
- [X] T113 Publish the matching tag and Russian GitHub Release notes with changes, validation, migration/compatibility, known limitations, PR/issues and deferred 097 in `specs/099-review-m4a-normalization/validation/release-closeout.md`
- [X] T114 Run `infra/scripts/cd-remote.sh --dry-run`, obtain fresh explicit release/deploy approval, then run `infra/scripts/cd-remote.sh --execute` only when every gate passes and record backup/rollback/deployed SHA in `specs/099-review-m4a-normalization/validation/release-closeout.md`
- [ ] T115 Prove production new first-party/manual automatic conversion, transient recovery, inventory-before-mutation backfill, Chrome/embedded Range playback, transcript independence, migration/worker health and residue-zero cleanup in `specs/099-review-m4a-normalization/validation/release-closeout.md`
- [ ] T116 Close task-backed GitHub issues only after evidence comments, update product status, verify branch/worktree cleanup and record feature 097/scan still deferred in `specs/099-review-m4a-normalization/validation/release-closeout.md`

---

## Phase 12: Worker-Interrupted Startup Recovery Hotfix

**Purpose**: Repair the observed production gap without changing normal retry policy or requiring a user/admin action.

- [X] T117 [P] [US3] Add an integration regression proving worker-start reconciliation immediately dispatches a future-dated `worker_interrupted` retry-wait job and leaves a different future-dated retry reason deferred in `apps/server/tests/integration/test_playback_normalization_restart.py`
- [X] T118 [US3] Admit only `worker_interrupted` retry-wait jobs during the initial worker reconciliation and reuse the existing transition, audit, lease and dispatch path in `apps/server/src/twobrain_rec_server/normalization/pickup.py`, `apps/server/src/twobrain_rec_server/normalization/service.py`, and `apps/server/src/twobrain_rec_server/normalization/worker.py`
- [X] T119 [US3] Run the focused restart-recovery regression and relevant static checks, record the exact no-user-action and normal-backoff evidence in `specs/099-review-m4a-normalization/validation/hotfix-worker-recovery.md`, then update `specs/099-review-m4a-normalization/validation/traceability.md`
- [ ] T120 [US3] Run canonical local CI, ponytail diff review and release/deploy closeout; prove the existing production job automatically converges after the worker restart without exposing private media/transcript content in `specs/099-review-m4a-normalization/validation/release-closeout.md`

---

## Phase 13: Active Attempt Cleanup Hotfix

**Purpose**: Prevent the maintenance cleanup loop from deleting the temporary
output of a still-owned normalization attempt.

- [X] T121 [P] [US3] Add SQLite and PostgreSQL regressions that retain a `local_preparing` attempt while its parent job has an unexpired `running` lease in `apps/server/tests/integration/test_playback_normalization_restart.py` and `apps/server/tests/integration/test_playback_normalization_postgres.py`
- [X] T122 [US3] Exclude active leased attempts from the cleanup selector in the SQLite path and PostgreSQL maintenance helper migration `0026_skip_active_normalization_cleanup.py` without changing expired-attempt cleanup in `apps/server/src/twobrain_rec_server/normalization/pickup.py`
- [ ] T123 [US3] Run canonical CI, review and production closeout for the cleanup hotfix; prove the affected job reaches canonical playback-ready state without user action in `specs/099-review-m4a-normalization/validation/release-closeout.md`
- [X] T124 [US3] Keep migration `0026` within Alembic's 32-character revision limit, update exact worker schema-head tests, then rerun canonical CI before release in `apps/server/src/twobrain_rec_server/db/migrations/versions/0026_skip_active_normalization_cleanup.py` and `apps/server/tests/unit/test_playback_normalization_worker.py`

---

## Dependencies And Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Starts from the validated `origin/master` snapshot and preserves the unrelated dirty detached worktree.
- **Foundation (Phase 2)**: Depends on Setup and blocks every user story.
- **US1 (Phase 3)**: Depends on Foundation and creates the first-party automatic playback path.
- **US2 (Phase 4)**: Depends on the US1 job/publication path and independently proves manual conversion.
- **US3 (Phase 5)**: Depends on US1 job/workflow truth and owns automatic long-term recovery.
- **US7 (Phase 6)**: Depends on US1/US2 source integration and closes the authoritative-ingest boundary before backfill.
- **US4 (Phase 7)**: Depends on US1/US3/US7 job, recovery and custody truth.
- **US5 (Phase 8)**: Depends on US2 media classification and US3 recovery ownership; it can be completed alongside US4 after shared states stabilize.
- **US6 (Phase 9)**: Depends on publication/backfill/failure states from all prior stories.
- **PR Readiness (Phase 10)**: Depends on all seven user stories.
- **Release/Deploy (Phase 11)**: Depends on approved commit, validated PR merge and a fresh release/deploy gate.

### User Story Dependency Graph

```text
Setup -> Foundation -> US1 -> US2
                         ├──> US3
                         └──> US7
US1 + US2 + US3 + US7 -> US4
US2 + US3 -------------> US5
US1 + US3 + US4 + US5 -> US6
All stories -> PR Readiness -> Release/Deploy
```

### Parallel Opportunities

- T002–T004 use separate fixture/evidence files.
- T005–T009 are independent failing-test surfaces and can be authored before foundational implementation.
- Within each story, `[P]` test tasks can run in parallel before implementation.
- US4 inventory and US5 failure-copy work can proceed in parallel after shared job/reason contracts stabilize.
- T096, T098, T104 and T105 use separate validation/doc surfaces after the implementation diff stabilizes.
- T100 requires both server rendering and the unchanged embedded macOS surface; it is not parallel with unfinished UI work.

## Parallel Examples

### User Story 1

```text
T021 finalize/role/fingerprint tests
T022 candidate/fallback workflow tests
T023 publication/idempotency tests
T024 status/Range/cabinet tests
```

### User Stories 4 And 5

```text
US4: T063–T066 inventory/priority/RLS tests
US5: T073–T075 failure/status/resource tests
```

## Implementation Strategy

### Safe MVP First

1. Complete Setup and Foundation.
2. Complete US1 first-party automatic playback.
3. Complete US2 manual conversion.
4. Complete US3 automatic recovery and US7 accepted-source boundary.
5. Stop and validate all four P1 stories before any rollout.

US1 alone is an independently testable increment, but it is not a production-ready promise. The usable MVP gate is US1+US2+US3+US7 because “100% automatic” requires manual media, crash recovery and authoritative-source custody together.

### Incremental Completion

1. P1: first-party normalization, manual conversion, automatic recovery, ingest boundary.
2. P2: legacy backfill, truthful impossible-input outcomes, lifecycle/operations.
3. Full media matrix, real local/browser E2E, near-limit resource proof and canonical local CI.
4. User-approved commit/PR/merge.
5. Freshly approved release/deploy, production backfill/user-path proof and cleanup.
