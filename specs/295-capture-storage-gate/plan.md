# Implementation Plan: Честная проверка локального места

**Branch**: `295-capture-storage-gate` | **Date**: 2026-11-14 | **Spec**: [spec.md](./spec.md)

## Summary

F295 — узкий срочный фикс production-блокировки записи. Заменить расчёт занятого места с исторической очереди на фактический размер папки записей; измерять вне MainActor с кэшем и single-flight; разрешить warning для ручного и автоматического старта; блокировать только critical/full/резерв; скрыть красный индикатор в `.failed`; показать безопасную причину в меню-баре.

F295 **не удаляет файлы**, не меняет схему очереди, не трогает `LocalRecordingPlayer`, `localPlaybackURL`, bridge, local-only список и F284 fallback. Серверная библиотека, eviction и очистка — отдельная фича F296.

## Technical Context

**Language**: Swift 6.0.3, macOS 14+.
**UI**: SwiftUI + AppKit.
**Testing**: XCTest, `apps/macos/Scripts/run-swift-tests.sh`, ContractValidation, GitHub `release-full`, notarization/Gatekeeper/Sparkle, production health.
**Risk lane**: high-risk-product (capture, local storage, tray, release).
**Interim policy**: 2 GB, warning 75%, critical 90%, reserve 20 MB. Policy change is F296.

## Constitution Check

- **I. Capture-First MVP Integrity**: PASS. Capture source and stop path unchanged; only pre-start storage false positive fixed.
- **II. Visible Consent And User Control**: PASS. Manual Record/Stop remains visible; warning does not block; failed state no longer looks like active capture.
- **III. Plaintext Observability**: PASS. No raw audio, paths, transcript or secrets added to logs; tray reason is curated copy.
- **IV. Deletion Truth**: PASS. No file deletion, no queue schema change, no purge behavior change.
- **V. Public macOS Distribution**: PASS. Developer ID/notarization/Sparkle gates unchanged.
- **VI. Spec-Driven Delivery**: PASS. F295 spec/plan/tasks/checklist/quickstart and release gates.
- **VII. Reference-Fidelity**: PASS. No visual redesign; warning is a non-blocking notice consistent with existing status notes; warning and failed-reason labels have explicit VoiceOver copy.
- **VIII. Local Cache / Server Library**: N/A for F295; F296 owns it.

## Root Cause

`ContentView.meetingDetectionStorageRisk()` суммирует `artifactProfile.totalUploadBytes` по всей очереди, включая `uploaded` и `terminal_deleted`. У пользователя это 1,53 ГБ при warning-пороге 1,5 ГБ (75% от 2 ГБ). `RecordingPrerequisiteGate` блокирует любой риск, кроме `.healthy`; `RecordingPrerequisiteSnapshot.allowsRecording` и `MeetingDetectionCapturePrerequisites.allowsRecordingStart` также требуют `.healthy`. В результате manual и automatic start блокируются на warning. `GrafRecordingLightView` скрыт только для `.idle`/`.starting`, поэтому в `.failed` горит красный индикатор.

## Design

### 1. Footprint value and measurer

New file: `apps/macos/RecApp/Sources/Buffering/LocalRecordingFootprint.swift`

```text
LocalRecordingFootprintSnapshot
  bytes: Int64
  fileCount: Int
  measuredAt: Date
  rootPath: String
  error: LocalRecordingFootprintError?
```

`LocalRecordingFootprintMeasurer`:

- enumerates `desktopUploadQueueService.recordingsRootURL` (same root as the queue), not a separately constructed store;
- counts regular files only;
- uses `totalFileAllocatedSize` with `fileSize` fallback;
- skips directories, symlinks and nested symlink traversal;
- missing root = 0 bytes, no error;
- permission/enumerator error = fail-closed error;
- overflow-clamped;
- no logging of absolute paths in normal logs.

Keep `LocalBufferService.riskState(usedBytes:freeDiskBytes:policy:)` as the pure policy evaluator. Do not put file enumeration into it.

### 2. Off-main provider

New file: `apps/macos/RecApp/Sources/Buffering/LocalRecordingFootprintProvider.swift`

Dedicated actor `LocalRecordingFootprintProvider` (never MainActor) with:

- single-flight measurement;
- cached snapshot and `measuredAt`;
- TTL (60 seconds), measurement timeout `2 seconds`, and generation/root identity fence;
- `refresh() async -> LocalBufferRiskState`;
- `cachedRisk()` for meeting detection;
- fail-closed when no snapshot or stale beyond max age;
- no file enumeration in SwiftUI body.

Wiring in `ContentView`:

- `@State private var footprintProvider = LocalRecordingFootprintProvider(...)`;
- `meetingDetectionStorageRisk()` reads only the cached risk;
- `startManualRecording` awaits a fresh measurement with a `2 second` timeout before the gate; timeout or error blocks with `storageUnsafe`;
- remove the duplicate synchronous call at the existing start path;
- refresh on app appearance, queue changes, recording completion and explicit start;
- if start measurement times out or fails, block with `storageUnsafe` and a safe reason.

### 3. Policy correction

`RecordingPrerequisiteGate`:

- block only `.critical` and `.mustDegradeOrStop`;
- `.warning` returns `blockedReason = .none`, no recovery action;
- permission/source/indicator/policy branches unchanged.

`RecordingPrerequisiteSnapshot.allowsRecording` (`AudioModelCore.swift`):

- storage condition allows `.healthy` and `.warning`;
- add a computed `storageBlocksRecording` used by both gate and snapshot to avoid divergence.

`MeetingDetectionCapturePrerequisites.allowsRecordingStart`:

- inherits the corrected `allowsRecording`; add a test that warning permits automatic start.

### 4. Warning presentation

Add a separate non-blocking notice, not `RecordingBlockerPresentation`:

- `CaptureControlView` gets `storageWarning: String?`;
- `StatusNoteView` card with amber icon and copy;
- accessibility identifier `systemAudio.storage.warning`;
- warning does not set `blockedReason`, `recordingBlocker`, `hasActionableProblem`, and does not suppress idle state;
- accessibility label: «Мало места на Mac. Запись разрешена. Освободите место, чтобы следующая запись не остановилась.»
- tray menu gets an informational warning row while recording starts/active;
- copy: «Мало места на Mac. Запись начнётся, но старые локальные записи скоро нужно будет удалить.»

### 5. Failed tray truth

`CalendarTray.swift`:

- `GrafRecordingLightView.update` hides the light for `.failed`;
- `.recording`, `.paused`, `.degraded`, `.stopping` remain visible;
- do not change `GrafTrayRecordingState.resolve` or `statusIcon`;
- `CalendarTrayModel` gets `failureDetail: String?`;
- `CalendarTrayController.showRecordingState(_:failureDetail:)` stores it and shows a second informational row under «Повторить запись»;
- truncate visible title, full text in tooltip;
- accessibility label for the reason row is the full safe reason;
- test `.failed` while the local writer is still finalizing, plus `.degraded`/`.stopping` remaining visible.

`AppLifecycleDelegate`:

- `updateTrayRecordingState(_:failureDetail:)` stores and forwards;
- clears detail when state is not `.failed`.

`ContentView`:

- passes `recordingBlocker?.message` on state and blocker changes;
- fallback when blocker is nil: «Запись не началась. Повторите попытку.»
- detail is curated copy only; no raw errors/paths.

### 6. No relief action in F295

F295 deletes no files. The earlier “Освободить место” idea is deferred to F296b because it requires:

- server `archive_audio`/playback proof;
- a partial-eviction ledger;
- support/custody reporting for a missing WAV;
- user confirmation and migration dry run.

F295 acceptance does not require file deletion.

### 7. Tests

- `LocalRecordingFootprintTests`: actual bytes, missing root, error fail-closed, symlink/dir ignore, overflow.
- `LocalRecordingFootprintProviderTests`: TTL, single-flight, stale fail-closed, generation fence, and proof that measurement runs off the main thread.
- `RecordingPrerequisiteGateTests`: warning allows, critical/must-degrade blocks.
- `MeetingDetectionPolicyTests`: warning allows automatic start; critical suppresses.
- `CaptureControlV5Tests`: warning copy, `hasActionableProblem == false`.
- `DesktopCalendarReminderTests`: `.failed` hides light, detail row; `.failed` with finalizing writer; `.degraded`/`.stopping` visible; active stop+timer.
- `AppShellBehaviorTests`/`InterfacePerformanceContractTests`: no file enumeration in render path.
- F284/local-only/deletion regression tests unchanged and green.
- SC-001 automated fixture: synthetic 1.5+ GB queue metadata with ~1.1 GB actual root, start allowed.

### 8. Validation and release

- `swift build --package-path apps/macos`
- `apps/macos/Scripts/run-swift-tests.sh`
- `swift run --package-path apps/macos ContractValidation`
- `python3 scripts/validate-changelog-fragments.py`
- PR checks: `governance-fast`, `macos-pr`, `pr-metadata` on exact SHA
- `release-full` on frozen candidate
- Developer ID, notarization, staple, Gatekeeper, Sparkle/live appcast
- `cd-remote.sh --dry-run`, production deploy, health, runtime SHA
- `specs/295-capture-storage-gate/validation.md` evidence
- `changes/unreleased/F295.yaml`
- `docs/current-product-status.md` update

## Project Structure

```text
specs/295-capture-storage-gate/
├── spec.md
├── plan.md
├── tasks.md
├── quickstart.md
├── validation.md
├── analysis-server-library-local-cache.md
└── checklists/
    ├── requirements.md
    ├── ux.md
    └── review-2026-11-14.md

apps/macos/RecApp/Sources/Buffering/
├── LocalRecordingFootprint.swift
├── LocalRecordingFootprintProvider.swift
└── LocalBufferService.swift

apps/macos/RecApp/Sources/AppShell/
├── ContentView.swift
└── AppLifecycleDelegate.swift

apps/macos/RecApp/Sources/Capture/
├── CaptureControlViewCore.swift
└── RecordingPrerequisiteGate.swift

apps/macos/RecApp/Sources/Calendar/CalendarTray.swift
apps/macos/Shared/Sources/Models/AudioModelCore.swift
apps/macos/Shared/Sources/Models/SystemAudioCaptureCoreModels.swift
apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionPolicy.swift
```

## Complexity Tracking

| Change | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Off-main footprint provider | Avoid UI stall and stale queue metadata | Sync enumeration on MainActor was explicitly removed from render path |
| Warning policy in snapshot + gate | Gate alone leaves `allowsRecording` false | Two independent conditions would diverge again |
| Separate warning presentation | Blocker would look like an error and suppress idle/auto-record | Reusing `RecordingBlockerPresentation` breaks UX and meeting detection |
| Failure detail in tray | «Повторить запись» without reason is confusing | Keeping only «Нужна помощь» hides the actual storage cause |
| Defer relief to F296b | No server playback/archive proof in current contract | Deleting WAV now risks losing the only source |
