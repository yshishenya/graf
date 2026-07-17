# Tasks: Единый синхронный WAV и playback M4A

**Input**: Design documents from `/specs/106-mixed-wav-recording/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Risk / validation lane**: High-risk capture, storage, external processing, deletion and installed-app UX. Tests are required before each behavior change; the feature is not complete without quickstart, source audit, hardware acceptance and `infra/scripts/ci-local.sh`.

**Organization**: Tasks are grouped by independently testable user story. New v5 work may not use user audio, transcript text, secrets, signed URLs or private paths in git/evidence.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: different file(s), no dependency on an incomplete task.
- **[Story]**: user story from [spec.md](spec.md); omitted only for setup/foundation/polish.
- Every implementation task names exact file paths and its test boundary.

## Phase 1: Setup and Test Fixtures

**Purpose**: Create metadata-only v5 fixture and validation seams before production code changes.

- [X] T001 [P] Add v5 package member/format fixture metadata (no media payload) in `tests/macos/contract/recording-artifact-format.json` and `tests/macos/local-recording/recording-artifact-format-smoke.md`.
- [X] T002 [P] Add a v5 source-kind/role/descriptor fixture to `apps/server/tests/fixtures/processing.py` without audio bytes or transcript text.
- [X] T003 [P] Add expected `initial_mixed_recording` and `single_wav_v1` non-secret contract assertions to `apps/server/tests/contract/test_ingest_openapi_contract.py`.
- [X] T004 Record the exact known-good pre-v5 baseline commit/release and planned metadata-only control-period receipt schema in `qa/macos/release-candidate-checklist.md`.

---

## Phase 2: Foundational Package and Contract Boundaries

**Purpose**: Establish v5 data identities, compatibility rules and tests that block every user story.

**⚠️ CRITICAL**: No v5 capture, upload, processing or cleanup task starts until this phase is green.

- [X] T005 [P] Add failing v3/v4/v5 manifest compatibility and completion tests in `apps/macos/Shared/Tests/CanonicalRecordingManifestTests.swift`.
- [X] T006 [P] Add failing transport-role and byte-weighted progress tests for `media` + required `playback` in `apps/macos/Shared/Tests/DesktopUploadQueueV5Tests.swift` and `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`.
- [X] T007 [P] Add failing source-kind-aware session/finalize role-set and descriptor tests in `apps/server/tests/unit/test_manifest_validation.py` and `apps/server/tests/integration/test_ingest_happy_path.py`.
- [X] T008 [P] Add failing immutable source-fingerprint and source-kind regression tests in `apps/server/tests/unit/test_media_revision_state_machine.py` and `apps/server/tests/integration/test_media_revision_identity.py`.
- [X] T009 Extend `apps/macos/Shared/Sources/Models/AudioStates.swift` with the explicit v5 local/transport roles and non-ASR playback representation, preserving decodability of historical roles.
- [X] T010 Extend `apps/macos/Shared/Sources/Models/AudioModelCore.swift` with `local-recording-manifest.v5`, `single_wav_v1`, `canonical-mix.v1`, v5 completion rules and explicit v3/v4 compatibility reading.
- [X] T011 Refactor `apps/macos/RecApp/Sources/Capture/LocalRecordingStore.swift` and `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift` to identify v5 final filenames without treating historical dual packages as v5.
- [X] T012 Add `media` role support and source-kind request data to `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`, preserving old queued v3/v4 upload descriptors.
- [X] T013 Add `INITIAL_MIXED_RECORDING` and its authoritative `media` role to `apps/server/src/twobrain_rec_server/domain/statuses.py` and `apps/server/src/twobrain_rec_server/ingest/media_revisions.py` without a database migration.
- [X] T014 Make source kind, exact role set and v5 descriptor validation one atomic contract in `apps/server/src/twobrain_rec_server/ingest/manifest.py`, `apps/server/src/twobrain_rec_server/ingest/sessions.py` and `apps/server/src/twobrain_rec_server/ingest/finalize.py`.
- [X] T015 Map the new first-party source kind explicitly through `apps/server/src/twobrain_rec_server/api/schemas.py`, `apps/server/src/twobrain_rec_server/api/ingest.py`, `apps/server/src/twobrain_rec_server/ingest/meetings.py` and `specs/012-server-ingest-foundation/contracts/openapi.yaml`, while retaining the old-client default.
- [X] T016 Update the v5 contract assertions in `apps/macos/Shared/Tools/ContractValidation/ContractValidationV5.swift` and `apps/macos/Scripts/validate-recording-artifact-format.sh`; remove assumptions that new packages contain `mic.wav` or `incoming.wav`.

**Checkpoint**: v5 package identity is unambiguous, current/historic packages remain distinguishable, and no role-only validation can accept an unprocessable revision.

---

## Phase 3: User Story 1 — Получить чистый текст одной встречи (Priority: P1) 🎯 MVP

**Goal**: Produce one timestamped canonical WAV from a continuous conversation and submit exactly it once for one ordered transcript.

**Independent Test**: Deterministic non-private source batches with offset starts, gaps, overlap and a long-run marker sequence create one valid v5 WAV; fake server processing observes one WAV `audio/wav` request and one imported result, with no dual merge or second request after ambiguous delivery.

### Tests for User Story 1

- [X] T017 [P] [US1] Add timeline epoch, PTS comparability, gap, overlap, route-generation, overflow and 60-minute drift tests in `apps/macos/Shared/Tests/RecordingAudioTimelineTests.swift`.
- [X] T018 [P] [US1] Add failing canonical fan-out/flush/partial-finalization tests in `apps/macos/Shared/Tests/LocalRecordingWriterTests.swift` and `apps/macos/Shared/Tests/LocalRecordingWriterSystemAudioTests.swift`.
- [X] T019 [P] [US1] Add final WAV/M4A identity and no-new-dual-artifact tests in `apps/macos/Shared/Tests/SystemAudioRecordingPackageTests.swift`.
- [X] T020 [P] [US1] Add one-v5-WAV multipart filename/content-type and no-playback submission tests in `apps/server/tests/contract/test_mediascribe_client_contract.py` and `apps/server/tests/integration/test_mediascribe_processing_happy_path.py`.
- [X] T021 [P] [US1] Add no-automatic-second-submit tests for timeout/ambiguous response/restart in `apps/server/tests/integration/test_processing_failures.py` and `apps/server/tests/integration/test_processing_worker_restart.py`.

### Implementation for User Story 1

- [X] T022 [US1] Introduce timestamped capture batch, common-epoch and stateful sample-rate conversion primitives in `apps/macos/RecApp/Sources/Capture/RecordingAudioTimeline.swift` using native `AVAudioConverter` only.
- [X] T023 [US1] Preserve source PTS, actual format and explicit discontinuities at the system-audio boundary in `apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift`.
- [X] T024 [US1] Preserve source PTS, actual format and explicit discontinuities at the app-owned microphone boundary in `apps/macos/RecApp/Sources/Capture/MicrophoneCaptureService.swift`.
- [X] T025 [US1] Implement the one-write canonical fan-out with `canonical-mix.v1`, protected partial paths, WAV converter flush and M4A validation in `apps/macos/RecApp/Sources/Capture/CanonicalRecordingWriter.swift`.
- [X] T026 [US1] Remove the legacy `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift` implementation and replace its sample-count FIFO pairing, independent stop padding and active dual WAV creation with the timestamped `apps/macos/RecApp/Sources/Capture/V5LocalRecordingWriter.swift` and one canonical writer.
- [X] T027 [US1] Emit the v5 final artifact descriptors, integrity reasons and `single_wav_v1` readiness in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`.
- [X] T028 [US1] Select `initial_mixed_recording` as a single processing source in `apps/server/src/twobrain_rec_server/processing/store.py` and retain historical dual selection only for accepted historic revisions.
- [X] T029 [US1] Stage v5 `media` only as a verified `.wav` and make one single-track request in `apps/server/src/twobrain_rec_server/processing/submit.py`.
- [X] T030 [US1] Map verified internal `wav-pcm-s16le` to exactly `audio/wav` and a `.wav` multipart filename in `apps/server/src/twobrain_rec_server/mediascribe/client.py`.
- [X] T031 [US1] Make ambiguous v5 submission outcomes terminally safe in `apps/server/src/twobrain_rec_server/processing/submit.py` and `apps/server/src/twobrain_rec_server/processing/lifecycle.py` without adding a duplicate external job.
- [X] T032 [US1] Run the focused macOS and server test groups from `specs/106-mixed-wav-recording/quickstart.md` and record only metadata-safe outcomes in `specs/106-mixed-wav-recording/evidence/us1-synthetic.md`.

**Checkpoint**: A new recording has one continuous canonical WAV and one revision-bound single-track transcript path; no new package or request uses dual ASR.

---

## Phase 4: User Story 2 — Прослушать именно записанный разговор (Priority: P1)

**Goal**: Deliver a playback M4A from the same source timeline and show truthful byte-weighted upload/playback status without muting or rerouting incoming audio.

**Independent Test**: A v5 package contains a valid same-timeline M4A, normal upload exposes monotonic intermediate whole-package progress, playback normalization reuses the candidate, and an unavailable later playback state does not falsify a valid transcript source.

### Tests for User Story 2

- [X] T033 [P] [US2] Add v5 M4A descriptor, AAC priming/timeline and playback-unavailable truth tests in `apps/macos/Shared/Tests/SystemAudioRecordingPackageTests.swift` and `apps/macos/Shared/Tests/CanonicalRecordingManifestTests.swift`.
- [X] T034 [P] [US2] Add monotonic byte-weighted progress, resume and no-fixed-50-percent tests in `apps/macos/Shared/Tests/DesktopUploadQueueV5Tests.swift` and `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`.
- [X] T035 [P] [US2] Add v5 playback-candidate reuse/source-fingerprint tests in `apps/server/tests/integration/test_playback_normalization_finalize.py` and `apps/server/tests/integration/test_playback_normalization_reuse.py`.
- [X] T036 [P] [US2] Add keyboard/accessibility state contract tests for capture, Stop, progress and safe recovery in `apps/macos/Shared/Tests/CaptureControlV5Tests.swift` and `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`.

### Implementation for User Story 2

- [X] T037 [US2] Make v5 `media` and required `playback` artifact completeness/profile data truthful in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`.
- [X] T038 [US2] Calculate and publish whole-package uploaded-byte progress, including resume/retry, in `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift` and `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`.
- [X] T039 [US2] Preserve route/volume-neutral capture controls and expose accessible active/Stop/degraded state semantics in `apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift` and `apps/macos/RecApp/Sources/Capture/CaptureStatusItem.swift`.
- [X] T040 [US2] Reuse the accepted v5 M4A candidate while selecting v5 `media` as the authoritative source in `apps/server/src/twobrain_rec_server/normalization/service.py`.
- [X] T041 [US2] Expose v5 playback/transcript availability independently and truthfully in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html`.
- [X] T042 [US2] Run the US2 focused Swift/server groups and record byte/duration/status-only evidence in `specs/106-mixed-wav-recording/evidence/us2-playback-progress.md`.

**Checkpoint**: Playback is a valid v5 artifact from the same timeline, progress reflects real bytes, and no playback outcome changes the canonical ASR source.

---

## Phase 5: User Story 3 — Безопасно перейти на новый формат (Priority: P1)

**Goal**: Preserve historical records and establish a proven, release-level future-capture rollback without a hidden feature flag or data rewrite.

**Independent Test**: v3/v4 fixtures remain readable/processable, a v5 revision stays immutable through restart/deletion, and the control-period receipt defines a baseline rollback that changes only a subsequent test recording.

### Tests for User Story 3

- [X] T043 [P] [US3] Add historical v3/v4 reader/upload regression fixtures and v5 rejection-of-legacy-write tests in `apps/macos/Shared/Tests/CanonicalRecordingManifestTests.swift` and `apps/macos/Shared/Tests/DesktopUploadQueueV5Tests.swift`.
- [X] T044 [P] [US3] Add v5 deletion/purge/revision-isolation tests in `apps/server/tests/integration/test_processing_deletion_dependency.py` and `apps/server/tests/integration/test_media_revision_migrations.py`.
- [X] T045 [P] [US3] Add release-baseline and no-live-toggle acceptance assertions in `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift` and `qa/macos/release-candidate-checklist.md`.

### Implementation for User Story 3

- [X] T046 [US3] Isolate historical schema decoding and queued dual upload behavior from all v5 writer defaults in `apps/macos/Shared/Sources/Models/AudioModelCore.swift` and `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`.
- [X] T047 [US3] Preserve historic dual processing while making v5 reader/processing additive in `apps/server/src/twobrain_rec_server/processing/store.py`, `apps/server/src/twobrain_rec_server/ingest/manifest.py` and `apps/server/src/twobrain_rec_server/ingest/media_revisions.py`.
- [X] T048 [US3] Add metadata-only baseline/canary/rollback rehearsal instructions and evidence template in `qa/macos/release-candidate-checklist.md` and `specs/106-mixed-wav-recording/evidence/README.md`.
- [ ] T049 [US3] Run v3/v4/v5 compatibility, deletion and rollback-rehearsal checks from `specs/106-mixed-wav-recording/quickstart.md` and record safe results in `specs/106-mixed-wav-recording/evidence/us3-compatibility-rollback.md`.

**Checkpoint**: v5 can be safely rolled back for future capture without breaking or altering historical/v5 accepted records.

---

## Phase 6: User Story 4 — Не нести старую сложность дальше (Priority: P2)

**Goal**: Remove active dual/AEC/echo-cleanup code from the new path while retaining only intentional historical compatibility until retention permits retirement.

**Independent Test**: Source/package scans find no v5 path that creates dual source files, routes M4A to ASR, uses AEC/echo cleanup or merges transcripts; historic records remain readable through isolated compatibility code.

### Tests for User Story 4

- [X] T050 [P] [US4] Add v5 no-AEC/no-dual/no-text-merge product-surface assertions in `apps/macos/Shared/Tests/NoAECProductSurfaceTests.swift` and `apps/macos/Shared/Tools/ContractValidation/ContractValidationV5.swift`.
- [X] T051 [P] [US4] Add v5 no-dual-dispatch/no-playback-ASR assertions in `apps/server/tests/contract/test_processing_no_secret_content_egress.py` and `apps/server/tests/integration/test_mediascribe_processing_happy_path.py`.
- [X] T052 [P] [US4] Add active-v5 versus historical-compatibility documentation assertions in `apps/server/tests/contract/test_ingest_openapi_contract.py` and `docs/integrations/mediascribe-dual-track-api.md`.

### Implementation for User Story 4

- [X] T053 [US4] Remove active local dual-track writers, leakage finalization/measurement and obsolete active-path references from `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`, `apps/macos/RecApp/Sources/Capture/LeakageFinalizationService.swift`, `apps/macos/RecApp/Sources/Capture/LeakageMeasurementService.swift` and `apps/macos/RecApp/Sources/Capture/LeakageWAVReader.swift`.
- [X] T054 [US4] Remove Apple voice-processing, WebRTC AEC and echo-cleanup evaluation/diagnostic/UI/test surfaces no longer reachable from v5 in `apps/macos/RecApp/Sources/Capture/AppleVoiceProcessingEvaluationService.swift`, `apps/macos/RecApp/Sources/Capture/WebRTCAEC3EvaluationService.swift`, `apps/macos/Shared/Tests/AppleVoiceProcessingEvaluationTests.swift` and `apps/macos/Shared/Tests/WebRTCAEC3EvaluationTests.swift`.
- [X] T055 [US4] Remove legacy fixtures, validation tools and package/docs assertions that describe dual source files as the active recording contract in `apps/macos/Shared/Tools/LeakageValidation/main.swift`, `tests/macos/contract/local-recording-package-leakage.json`, `docs/audio-capture-backlog.md` and `docs/prd-voice-layer-final.md`.
- [X] T056 [US4] Update the active integration documentation, status and release notes to describe v5 single-WAV processing and isolated historical compatibility in `docs/integrations/mediascribe-dual-track-api.md`, `docs/current-product-status.md` and `CHANGELOG.md`.
- [X] T057 [US4] Keep historic dual MediaScribe endpoints/workers behind historical source-kind handling only, document their drain/retirement condition in `apps/server/src/twobrain_rec_server/processing/store.py` and `docs/integrations/mediascribe-dual-track-api.md`, and do not remove them until retention evidence exists.
- [X] T058 [US4] Run source/package/docs legacy audit commands and record only counts/path classes in `specs/106-mixed-wav-recording/evidence/us4-legacy-audit.md`.

**Checkpoint**: New normal recording has no legacy tail; only bounded historical compatibility remains, with a documented later retirement condition.

---

## Phase 7: Polish, Full Validation and Autonomous Closeout

**Purpose**: Prove the complete pipeline, preserve release boundaries and reconcile all task evidence.

- [X] T059 [P] Verify checked-in v5 OpenAPI/generated-contract parity and server contract coverage in `specs/012-server-ingest-foundation/contracts/openapi.yaml` and `apps/server/tests/contract/test_ingest_openapi_contract.py`.
- [X] T060 [P] Update selected risk/validation lane, test commands and no-content evidence controls in `specs/106-mixed-wav-recording/quickstart.md` and `specs/106-mixed-wav-recording/evidence/README.md`.
- [X] T061 Run `bash -n apps/macos/Scripts/validate-recording-artifact-format.sh`, `docker compose -f infra/docker-compose.yml config`, focused Swift tests, focused pytest/Ruff and `git diff --check`; record non-secret results in `specs/106-mixed-wav-recording/evidence/validation.md`.
- [X] T062 Run `infra/scripts/ci-local.sh` from the clean v5 branch and resolve every feature-caused failure before marking validation complete in `specs/106-mixed-wav-recording/evidence/validation.md`.
- [ ] T063 Build the macOS candidate with the existing local installer workflow, perform the non-private 60-minute installed-app route/volume/timeline package check, and record metadata-only verdicts in `specs/106-mixed-wav-recording/evidence/hardware-acceptance.md`.
- [ ] T064 Exercise an approved synthetic end-to-end package through desktop upload, server finalize, single MediaScribe-compatible result import, cabinet state, deletion and rollback rehearsal; record hashes/counts/statuses only in `specs/106-mixed-wav-recording/evidence/e2e-acceptance.md`.
- [X] T065 Run a final source/fixture/diagnostic secret-and-legacy audit across `apps/macos`, `apps/server`, `docs/` and `specs/106-mixed-wav-recording`, then mark only evidence-backed tasks `[X]` in this file.
- [X] T066 Reconcile every completed task with its GitHub issue, add Russian validation/closure comments where fully satisfied, and leave unmet release/deploy work explicitly open in `specs/106-mixed-wav-recording/tasks.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1**: starts immediately and creates safe test/evidence scaffolding.
- **Phase 2**: depends on Phase 1 and blocks all user stories because package/revision identity must be unambiguous first.
- **US1 (Phase 3)**: starts after Phase 2; it is the functional MVP and establishes one canonical source/ASR path.
- **US2 (Phase 4)**: depends on v5 fan-out/identity from US1, but has independent playback/progress acceptance.
- **US3 (Phase 5)**: depends on v5 identity and validates compatibility/rollback independently of a live runtime toggle.
- **US4 (Phase 6)**: depends on stable v5 and historical compatibility proof; it removes only active legacy, not retention-needed historic behavior.
- **Phase 7**: depends on all desired stories; it is the high-risk closeout gate and includes no deploy/release execution.

### User Story Dependencies

- **US1 (P1)**: no dependency on another user story after foundation; it is the minimum safe v5 vertical slice.
- **US2 (P1)**: consumes US1's canonical fan-out but preserves independently testable playback/progress behavior.
- **US3 (P1)**: consumes package/source identity but is independently testable using v3/v4/v5 fixtures and release receipt metadata.
- **US4 (P2)**: runs only after US1–US3 prove what compatibility remains necessary.

### Parallel Opportunities

- T001–T004, T005–T008, T017–T021, T033–T036, T043–T045 and T050–T052 touch separate test/fixture files and can run in parallel after their prerequisites.
- Server enum/validation work (T013–T015) and macOS model/queue work (T009–T012) may proceed in parallel once their corresponding tests exist.
- Hardware and synthetic end-to-end tasks remain sequential after complete focused validation; neither may use private recording content.

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1, including the no-duplicate single-WAV synthetic vertical slice.
3. Run its focused tests and safe evidence gate before changing playback/UX or cleanup.

### Incremental Delivery

1. Add US2 for product-quality playback and real progress.
2. Add US3 for compatibility/rollback proof.
3. Add US4 to remove active legacy after compatibility is isolated.
4. Complete Phase 7 only when every acceptance metric and required evidence is green.

### Release Boundary

No task here authorizes production deployment, public rollout, tag, GitHub Release or a destructive user-data action. Those remain separately approved release/deploy actions after the local feature evidence is complete.

---

## Phase 8: Convergence

- [X] T067 [US1] Normalize each native capture PTS against a callback-observed host-time reference and reject unstable or unobservable source-clock mapping in `apps/macos/RecApp/Sources/Capture/RecordingAudioTimeline.swift` and `apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift`; add deterministic mapping/drift tests in `apps/macos/Shared/Tests/RecordingAudioTimelineTests.swift` (FR-002, plan: one timestamped capture timeline, partial).
