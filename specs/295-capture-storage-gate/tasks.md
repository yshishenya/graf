# Tasks: Честная проверка локального места

**Input**: `specs/295-capture-storage-gate/spec.md`, `plan.md`
**Issue**: #8049
**Tests**: high-risk lane; behavior tests before or with implementation.

## Phase 1: Измерение и политика

- [X] T001 [P] [US1] Add `LocalRecordingFootprintSnapshot`, `LocalRecordingFootprintMeasurer` in `apps/macos/RecApp/Sources/Buffering/LocalRecordingFootprint.swift`; tests in `apps/macos/Shared/Tests/LocalRecordingFootprintTests.swift`.
- [X] T002 [P] [US1] Add `LocalRecordingFootprintProvider` with single-flight, TTL and generation fence in `apps/macos/RecApp/Sources/Buffering/LocalRecordingFootprintProvider.swift`; tests in `apps/macos/Shared/Tests/LocalRecordingFootprintProviderTests.swift`.
- [X] T003 [US1] Wire `ContentView.meetingDetectionStorageRisk()` and `startManualRecording` to the cached/off-main provider; remove synchronous enumeration and duplicate start measurement.
- [X] T004 [US1] Update `RecordingPrerequisiteSnapshot.allowsRecording` in `apps/macos/Shared/Sources/Models/AudioModelCore.swift` to allow `.warning`; use the shared `allowsRecordingStart` predicate.
- [X] T005 [US1] Update `RecordingPrerequisiteGate` in `apps/macos/RecApp/Sources/Capture/RecordingPrerequisiteGate.swift` to block only `.critical`/`.mustDegradeOrStop`; boundary tests in `RecordingPrerequisiteGateTests.swift`.
- [X] T006 [US1] Verify `MeetingDetectionCapturePrerequisites.allowsRecordingStart` allows warning; tests in `MeetingDetectionPolicyTests.swift`.

## Phase 2: Предупреждение и трей

- [X] T007 [US2] Add non-blocking `storageWarning` to `CaptureControlView`, accessibility identifier and copy; tests in `CaptureControlV5Tests.swift`.
- [X] T008 [US2] Add tray warning row without setting `blockedReason` or `hasActionableProblem`; tests.
- [X] T009 [US2] Hide `GrafRecordingLightView` for `.failed` while keeping `.degraded`/`.stopping` visible; tests in `DesktopCalendarReminderTests.swift`.
- [X] T010 [US2] Show `DesktopControlSnapshot.blocker` as the failed-tray reason; tests for reason row, truncation, safe copy and stale reason clearing.

## Phase 3: Регрессия и проверки

- [X] T011 [US3] Add regression assertions for F284/local-only/deletion paths: `LocalRecordingPlayer`, `localPlaybackURL`, bridge open, local-only list and progress helpers unchanged.
- [X] T012 [US3] Run focused tests, `apps/macos/Scripts/run-swift-tests.sh`, ContractValidation and `python3 scripts/validate-changelog-fragments.py`; record evidence in `validation.md`.
- [X] T013 [US3] Add `quickstart.md`, `checklists/ux.md`, `changes/unreleased/F295.yaml`; run independent checklist review and `$speckit-analyze`.
- [X] T014 [US3] Commit `specs/295-capture-storage-gate/`, create PR, run `governance-fast`, `macos-pr`, `pr-metadata` and `validate-pr-checks.py` on exact SHA.
- [ ] T015 [US4] Prepare release, freeze candidate, run `release-full`, build/notarize/staple/Gatekeeper/Sparkle.
- [ ] T016 [US4] Run `cd-remote.sh --dry-run`, deploy production, verify health/runtime SHA, publish GitHub Release/appcast, close #8049 with Russian evidence.
- [ ] T017 [US3] Run `$speckit-converge` and update `docs/current-product-status.md`.

## Dependencies

- T001-T006 before T007-T010.
- T007-T010 before T011-T013.
- T013 before T014.
- T014 before T015.
- T015 before T016.
- T017 after public artifacts and deploy evidence.

## Out Of Scope

- File deletion or “Освободить место” — F296b.
- Server playback contract, storage/retention fields, tombstones, cache manager, LRU — F296.
- Removing local playback/player/bridge/local-only list — not F295.
- Queue schema changes, SQLite, encryption/backup changes.
