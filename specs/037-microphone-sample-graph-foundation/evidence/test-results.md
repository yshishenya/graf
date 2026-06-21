# Test Results: Microphone Sample Graph Foundation

Record command outputs and manual validation summaries here. Keep all evidence
metadata-only.

## 2026-06-18 Setup Evidence

- Branch: `037-microphone-sample-graph-foundation`
- Feature directory: `specs/037-microphone-sample-graph-foundation`
- GitHub issue sync: `feature:037` scoped canon passed for 48 issues,
  #1294-#1341.
- Checklists: `audio-capture.md`, `requirements.md`, `security.md`, and
  `ux.md` all complete.
- Ignore setup: `.gitignore` already covers Swift/Xcode build outputs, local
  secrets, Spec Kit runtime state, and private evidence captures; `.dockerignore`
  exists.

## Focused Test Runs

- 2026-06-18: TDD red check, `cd apps/macos && swift test --filter
  MicrophoneCaptureServiceTests`, failed as expected before implementation on
  missing `RecordingMicrophoneSelection`, `AppOwnedMicrophoneStreamSession`,
  `MicrophoneStreamHealth`, `MicrophoneStreamKind`,
  `FutureProcessingReadiness`, and manifest microphone metadata fields.
- 2026-06-18: `cd apps/macos && swift test --filter
  MicrophoneCaptureServiceTests` passed, 5 tests, 0 failures.
- 2026-06-18: `cd apps/macos && swift test --filter
  LocalRecordingManifestTests` passed, 16 tests, 0 failures.
- 2026-06-18: `cd apps/macos && swift test --filter
  MicrophoneSampleGraphContractTests` passed, 2 tests, 0 failures.
- 2026-06-18: US1 TDD red check, `cd apps/macos && swift test --filter
  MicrophoneCaptureServiceTests`, failed as expected before implementation on
  missing recording input provider, rejection reason enum, writer
  `microphoneSelection` parameter, and capture-control microphone copy helpers.
- 2026-06-18: US1 focused rerun:
  `cd apps/macos && swift test --filter MicrophoneCaptureServiceTests &&
  swift test --filter RecordingMicrophoneSelectionTests && swift test --filter
  LocalRecordingWriterSystemAudioTests && swift test --filter
  CaptureControlTests && swift test --filter LocalRecordingManifestTests &&
  swift test --filter MicrophoneSampleGraphContractTests` passed:
  7 + 2 + 11 + 18 + 16 + 2 tests, 0 failures.
- 2026-06-18: US2 TDD red check, `cd apps/macos && swift test --filter
  MicrophoneCaptureServiceTests`, failed as expected before implementation on
  missing `blockedMicrophoneStreamEvidence`; follow-up writer run exposed a
  real silent-tail bug where Stop privacy suppression could be misread as
  `silent_input`.
- 2026-06-18: US2 focused rerun:
  `cd apps/macos && swift test --filter MicrophoneCaptureServiceTests &&
  swift test --filter RecordingMicrophoneSelectionTests && swift test --filter
  LocalRecordingWriterSystemAudioTests && swift test --filter
  CaptureSessionSafetyTests && swift test --filter LocalRecordingManifestTests`
  passed: 8 + 3 + 13 + 6 + 17 tests, 0 failures.
- 2026-06-18: US3 TDD red checks:
  `cd apps/macos && swift test --filter
  'SystemAudioRecordingPackageTests|LocalRecordingLeakageFinalizationTests|DesktopUploadQueueTests|MicrophoneSampleGraphContractTests'`
  first failed on test fixture/API mismatches (`DesktopUploadClient` type name,
  descriptor URL field, `AudioTrackRole` raw values, missing track
  `channelCount`, and unrelated `meetingMuteTruth.reason` in the fixture).
- 2026-06-18: US3 focused rerun:
  `cd apps/macos && swift test --filter
  'SystemAudioRecordingPackageTests|LocalRecordingLeakageFinalizationTests|DesktopUploadQueueTests|MicrophoneSampleGraphContractTests'`
  passed: 20 + 3 + 3 + 5 tests, 0 failures. Coverage proves optional
  microphone graph metadata preserves `mic.wav`, `incoming.wav`,
  `manifest.json`, upload descriptors, and leakage truth.
- 2026-06-18: US4 TDD red check:
  `cd apps/macos && swift test --filter
  'DiagnosticRedactionTests|LeakageDiagnosticBundleTests|RecordingEvidenceTests'`
  failed as expected before implementation because microphone selection,
  stream, and stream-health top-level diagnostic keys were not allowed and the
  local recording bundle/evidence summary did not expose graph readiness.
- 2026-06-18: US4 focused rerun:
  `cd apps/macos && swift test --filter
  'DiagnosticRedactionTests|LeakageDiagnosticBundleTests|RecordingEvidenceTests'`
  passed: 12 + 3 + 5 plus matched system-audio diagnostic test, 0 failures.
  Coverage proves selected/default microphone truth and graph readiness remain
  metadata-only in redaction, diagnostic bundles, and recording evidence.

## 2026-06-22 Post-Review Regression Pass

- Review fixes:
  - selected/default microphone sample source now binds the runtime capture
    session to the resolved native `AVCaptureDevice.uniqueID` instead of
    implicitly reading the current macOS default input;
  - app-owned microphone stream health now records metadata-only `lastLevel`
    and `lastLevelAt`;
  - product Pause/stopping suppression no longer counts suppressed microphone
    samples as app-owned graph readiness evidence;
  - a stale Swift test warning in shared audio memory compatibility coverage was
    removed.
- TDD red checks:
  `swift test --package-path apps/macos --filter
  MicrophoneCaptureServiceTests/testAppOwnedMicrophoneSampleSourceBindsResolvedSelectedInputDevice`
  first failed on missing selected-device sample-source binding;
  `swift test --package-path apps/macos --filter
  'LocalRecordingWriterSystemAudioTests/testWriterUsesInjectedAppOwnedMicrophoneSourceForMicTrackLevelsAndMetadata|LocalRecordingWriterSystemAudioTests/testPausedMicrophoneSamplesDoNotProveAppOwnedGraphReadiness'`
  first failed on missing `lastLevel` evidence and Pause-suppressed samples
  incorrectly proving graph readiness.
- Focused rerun:
  `swift test --package-path apps/macos --filter
  'MicrophoneCaptureServiceTests|RecordingMicrophoneSelectionTests|LocalRecordingWriterSystemAudioTests|CaptureControlTests|CaptureSessionSafetyTests|LocalRecordingManifestTests|LocalRecordingLeakageFinalizationTests|DesktopUploadQueueTests|MicrophoneSampleGraphContractTests|DiagnosticRedactionTests|LeakageDiagnosticBundleTests|RecordingEvidenceTests'`
  passed with 114 tests, 0 failures.
- Full macOS SwiftPM package:
  `swift test --package-path apps/macos` passed with 502 tests, 0 failures.
- Hygiene:
  `git diff --check` passed with no whitespace errors.

## Package Inspection

- 2026-06-18: `cd apps/macos &&
  Scripts/validate-recording-artifact-format.sh` passed. The helper completed
  macOS package tests with 500 tests and 0 failures, `ContractValidation: PASS`,
  `audio-rt-safety-check: ACCEPTED`, and
  `recording_artifact_format_validation=passed`.
- 2026-06-22: `cd apps/macos &&
  Scripts/validate-recording-artifact-format.sh` passed. The helper completed
  macOS package tests with 502 tests and 0 failures, `ContractValidation: PASS`,
  `audio-rt-safety-check: ACCEPTED`, and
  `recording_artifact_format_validation=passed`.

## Diagnostics Redaction

- 2026-06-18: Diagnostic redaction focused checks are covered by the US4
  focused rerun and final focused sweep. New microphone selection, stream, and
  stream-health top-level fields remain allowed metadata while nested raw
  audio, transcript text, signed URLs, credentials, and private path fields are
  removed.

## CPU And Resource Gates

- 2026-06-18: `cd apps/macos &&
  Scripts/validate-system-audio-capture-pivot.sh --self-test-artifact-metadata`
  passed with `system_audio_capture_pivot_validation=passed`.
- 2026-06-18: `cd apps/macos &&
  Scripts/validate-system-audio-capture-pivot.sh --self-test-cpu-evidence`
  passed with `system_audio_capture_pivot_validation=passed`.
- 2026-06-18: `cd apps/macos &&
  Scripts/sample-system-audio-cpu-gate.sh idle` was run twice and failed with
  `failureReason=unexpectedAppProcessRunning`; `/Applications/2brain Rec.app`
  was already running in the user environment and `coreaudiod` stayed above the
  idle threshold. This is recorded as a blocked manual idle-gate rerun, not a
  passing CPU acceptance.

## Local CI

- 2026-06-18: `infra/scripts/ci-local.sh` passed with `ci_local_result=pass`.
  Server tests reported 530 passed, 4 skipped, 8 warnings; server lint passed;
  Python compile passed; production compose config rendered; deployment
  evidence scan passed.
- 2026-06-22: `infra/scripts/ci-local.sh` passed with `ci_local_result=pass`.
  Server tests reported 530 passed, 4 skipped, 8 warnings; server lint passed;
  Python compile passed; production compose config rendered; deployment
  evidence scan passed.
- 2026-06-18: GitHub issue reconciliation for `feature:037` completed. Issues
  #1294-#1340 are closed; #1341 is the final reconciliation issue. The
  repository-wide issue-canon validator still fails on legacy non-037 issues
  (#1286 and older) that are outside this feature slice.
