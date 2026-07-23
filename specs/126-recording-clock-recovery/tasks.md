# Tasks: Восстановление устойчивой синхронизации записи

**Input**: Design documents from `specs/126-recording-clock-recovery/`

**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md),
[research.md](research.md), [data-model.md](data-model.md),
[contracts/timeline-and-finalization.md](contracts/timeline-and-finalization.md),
[quickstart.md](quickstart.md)

**Risk / validation lane**: High-risk macOS capture, timing, local
finalization and upload gate. Tests are required before behavior changes;
hardware acceptance remains a separate metadata-only gate.

**Format**: `[ID] [P?] [Story] Description`

- **[P]**: different files and no dependency on an incomplete task.
- **[Story]**: user story from [spec.md](spec.md).
- Every task names exact repository paths and a test boundary.

## Phase 1: Tests before implementation

**Purpose**: Make the incident regression and recovery contract executable before
changing the timeline implementation.

- [X] T001 [US1] Add timeline regressions for source PTS without callback observation, callback delivery jitter up to 500 ms, reordered batches and marker position in `apps/macos/Shared/Tests/RecordingAudioTimelineTests.swift`.
- [X] T002 [P] [US1] Add a writer regression with two valid PTS-bearing sources whose callback observations differ by 500 ms; assert complete v5 artifacts and no `timelineMisaligned` in `apps/macos/Shared/Tests/SystemAudioRecordingPackageTests.swift`.
- [X] T003 [US2] Add timeline scenarios for 44.1 kHz/stereo conversion, small long-run PTS drift, known gap, overlap, late batch and bounded gap in `apps/macos/Shared/Tests/RecordingAudioTimelineTests.swift`.
- [X] T004 [US3] Add split-batch metadata coverage and native timestamp boundary assertions in `apps/macos/Shared/Tests/SystemAudioCaptureServiceTests.swift` and `apps/macos/Shared/Tests/RecordingAudioTimelineTests.swift`.
- [X] T005 [US3] Add repeated Stop and incomplete-package upload-gate regressions in `apps/macos/Shared/Tests/SystemAudioRecordingPackageTests.swift` and `apps/macos/Shared/Tests/DesktopUploadQueueV5Tests.swift`.

**Checkpoint**: New tests express the intended behavior and fail only for the
current callback-time clock gate or missing idempotency/metadata behavior.

## Phase 2: User Story 1 — получить запись после нормальной остановки (P1)

**Goal**: Let delayed native callbacks finish on the existing PTS timeline and
publish one complete local package after Stop.

- [X] T006 [US1] Replace callback-time latency/jitter rejection with PTS-authoritative source normalization in `apps/macos/RecApp/Sources/Capture/RecordingAudioTimeline.swift`; keep explicit invalid-domain, route, overflow, gap, late and missing-source failures.
- [X] T007 [US1] Make callback host-time observation optional telemetry at the native extraction boundary while retaining valid CMSampleBuffer PTS in `apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift`.
- [X] T008 [US1] Preserve `observedHostTimeSeconds` when a bounded timestamped batch is split in `apps/macos/RecApp/Sources/Capture/RecordingSampleSources.swift`.
- [X] T009 [US1] Remove obsolete strict source-clock error mapping and make repeated Stop return the already finalized in-process manifest without creating a second directory in `apps/macos/RecApp/Sources/Capture/V5LocalRecordingWriter.swift`.
- [X] T010 [US1] Update timeline/package assertions for the new non-blocking observation contract in `apps/macos/Shared/Tests/RecordingAudioTimelineTests.swift` and `apps/macos/Shared/Tests/SystemAudioRecordingPackageTests.swift`.

**Checkpoint**: Normal Stop with delayed/reordered delivery creates exactly one
complete local v5 package; partial artifacts are never published.

## Phase 3: User Story 2 — сохранить синхронный общий звук (P1)

**Goal**: Prove that the existing common 48 kHz mono timeline remains stable
across formats, gaps, overlap and measured drift.

- [X] T011 [US2] Preserve stateful per-source AVAudioConverter and canonical frame-index behavior while adding the drift/reorder/gap test coverage in `apps/macos/RecApp/Sources/Capture/RecordingAudioTimeline.swift` and `apps/macos/Shared/Tests/RecordingAudioTimelineTests.swift`.
- [X] T012 [US2] Verify native serial callback queue drain and timestamped batch handoff remain bounded and route-neutral in `apps/macos/RecApp/Sources/Capture/MicrophoneCaptureService.swift`, `apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift` and `apps/macos/Shared/Tests/SystemAudioCaptureServiceTests.swift`.
- [X] T013 [US2] Validate that transcription WAV and playback M4A continue to derive from one canonical writer/timeline and keep their existing role/file contract in `apps/macos/Shared/Tests/SystemAudioRecordingPackageTests.swift`.

**Checkpoint**: Marker positions are determined by PTS/frame index, both output
artifacts share one timeline, and known integrity violations remain truthful.

## Phase 4: User Story 3 — понять и безопасно восстановить нештатный результат (P1)

**Goal**: Keep fail-closed manifest/upload behavior and avoid duplicate finalization
while distinguishing delivery jitter from true capture integrity failure.

- [X] T014 [US3] Assert missing source, dropped/overflow, route change, invalid clock domain, converter/finalization failure and incomplete artifact states remain blocked before server session creation in `apps/macos/Shared/Tests/SystemAudioRecordingPackageTests.swift` and `apps/macos/Shared/Tests/DesktopUploadQueueV5Tests.swift`.
- [X] T015 [US3] Preserve bounded metadata-only failure reason, counters and diagnostic redaction contract in `apps/macos/RecApp/Sources/Capture/V5LocalRecordingWriter.swift`, `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleCoreService.swift` and `apps/macos/Shared/Tests/DiagnosticRedactionV5Tests.swift`.
- [X] T016 [US3] Verify repeated Stop, queue refresh and relaunch-compatible manifest scanning do not create duplicate local package/server/ASR identities in `apps/macos/Shared/Tests/SystemAudioRecordingPackageTests.swift` and `apps/macos/Shared/Tests/DesktopUploadQueueV5Tests.swift`.

**Checkpoint**: A true integrity failure stays unusable and metadata-only; a
transport delay no longer enters that failure path; upload remains idempotent.

## Phase 5: Documentation and validation

- [X] T017 Update the `[Unreleased]` Russian entry with the capture-clock and
  finalization fix in `CHANGELOG.md`, without incident content or private data.
- [X] T018 Run focused Swift tests from `specs/126-recording-clock-recovery/quickstart.md`, then full `swift test` from `apps/macos`; record only pass/fail, counts and bounded reason codes in the task closeout.
- [X] T019 Run `infra/scripts/ci-local.sh`, classify any baseline/environment
  failures, run `git diff --check`, and verify no raw audio/transcript/secrets/
  signed URLs/live paths entered the diff.
- [X] T020 Run a final source-surface audit for removed routing/AEC assumptions,
  confirm the T063 hardware gate remains open, and reconcile task checkboxes with
  test evidence and GitHub issues in `specs/126-recording-clock-recovery/tasks.md`.
- [X] T021 Run Ponytail review over the complete diff and remove any unjustified
  abstraction, dependency or duplicate timing policy while preserving the
  capture, privacy and upload gates.

## Dependencies and execution order

- Phase 1 precedes all implementation tasks; T001–T005 may run in parallel only
  where they touch separate test files.
- T006–T009 depend on the Phase 1 tests; T010 updates those tests after the
  implementation contract is fixed.
- Phase 3 consumes the timeline contract from Phase 2 and must not introduce a
  second recorder, routing path or converter strategy.
- Phase 4 depends on complete/fail-closed package behavior from Phases 2–3.
- T017–T021 run only after focused tests pass; full CI is the closeout gate.

## MVP and release boundary

The MVP is T001–T010: delayed normal Stop must produce one complete local v5
package. No task authorizes production deploy, installer distribution, release
tag, data deletion or automatic hardware acceptance. Implementation commits
require explicit user approval after validation.

## Validation evidence

Дата: 2026-07-23. Evidence содержит только результаты и bounded metadata.

- Focused Swift: `RecordingAudioTimelineTests` 14/14, `SystemAudioRecordingPackageTests` 8/8, `SystemAudioCaptureServiceTests` 15/15.
- Full macOS `swift test`: 614 passed, 0 failures.
- `infra/scripts/ci-local.sh`: `ci_local_result=pass`; macOS contract validation, server parallel phase 2216 passed/1 skipped, strict PostgreSQL phase 41 passed/1 skipped, lint and Python compile passed.
- `git diff --check`: pass. Source audit не нашёл legacy strict source-clock symbols, virtual audio driver/routing daemon/AEC surface или content-bearing diagnostics в изменённых capture/test files.
- Ponytail review: `Lean already. Ship.` Новых зависимостей, recorder/pipeline, unbounded queue или дублирующей timing policy нет.
- Hardware boundary: live Zoom/device acceptance не выполнялась в этой среде; T063 остаётся открытым и synthetic tests не заменяют hardware evidence.
