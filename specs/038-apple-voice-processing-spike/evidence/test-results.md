# Test Results: Apple Voice Processing Spike

Record command outputs and validation summaries here. Keep all evidence
metadata-only.

## 2026-06-22 Setup Evidence

- Branch: `038-apple-voice-processing-spike`
- Feature directory: `specs/038-apple-voice-processing-spike`
- GitHub issue sync: `feature:038` scoped canon passed for 48 issues,
  #1343-#1390.
- Repository-wide issue-canon validator: currently blocked by legacy open issue
  body formatting outside `feature:038`; no `feature:038` failures were found.
- Checklists: `audio-capture.md`, `requirements.md`, `security.md`, and
  `ux.md` all complete.
- Evidence safety: this directory is metadata-only; raw audio, transcripts,
  meeting content, credentials, signed URLs, live paths, and participant
  identifiers are forbidden.

## Focused Test Runs

- 2026-06-22: T005/T006 red check,
  `swift test --package-path apps/macos --filter
  'AppleVoiceProcessingModelsTests|AppleVoiceProcessingSpikeContractTests'`,
  failed as expected before implementation on missing `AppleProcessingCandidate`,
  `AppleProcessingValidationRow`, `ProcessedMicrophoneEvidence`,
  `AppleProcessingOutcome`, `AppleProcessingOutcomeState`, and manifest
  `appleProcessingOutcome`.
- 2026-06-22: T005-T008 focused rerun,
  `swift test --package-path apps/macos --filter
  'AppleVoiceProcessingModelsTests|AppleVoiceProcessingSpikeContractTests'`,
  passed with 7 tests, 0 failures.
- 2026-06-22: T009/T010 red check,
  `swift test --package-path apps/macos --filter
  'LocalRecordingManifestTests/testManifestServiceThreadsAppleProcessingOutcomeMetadata|DiagnosticRedactionTests/testAppleProcessingEvidenceKeepsMetadataAndRemovesForbiddenFields'`,
  failed as expected before implementation on missing
  `appleProcessingOutcome` service threading.
- 2026-06-22: T009/T010 focused rerun,
  `swift test --package-path apps/macos --filter
  'LocalRecordingManifestTests/testManifestServiceThreadsAppleProcessingOutcomeMetadata|DiagnosticRedactionTests/testAppleProcessingEvidenceKeepsMetadataAndRemovesForbiddenFields'`,
  passed with 2 tests, 0 failures.
- 2026-06-22: Phase 2 foundation sweep,
  `swift test --package-path apps/macos --filter
  'AppleVoiceProcessingModelsTests|AppleVoiceProcessingSpikeContractTests|LocalRecordingManifestTests|DiagnosticRedactionTests'`,
  passed with 39 tests, 0 failures.
- 2026-06-22: US1 red check,
  `swift test --package-path apps/macos --filter
  'AppleVoiceProcessingModelsTests|AppleVoiceProcessingEvaluationTests|LeakageMeasurementTests/testAppleProcessing'`,
  failed as expected before implementation on missing
  `AppleVoiceProcessingEvaluationService`; the red run also caught a test
  fixture typo that used `.unintelligible` instead of the existing
  `.notIntelligible` enum case.
- 2026-06-22: US1 focused rerun,
  `swift test --package-path apps/macos --filter
  'RecordingEvidenceTests/testLocalRecordingEvidenceSummaryIsMetadataOnly|AppleVoiceProcessingModelsTests|AppleVoiceProcessingEvaluationTests|LeakageMeasurementTests/testAppleProcessing'`,
  passed with 11 tests, 0 failures.
- 2026-06-22: Full macOS SwiftPM package,
  `swift test --package-path apps/macos` passed with 517 tests, 0 failures.

## Package Inspection

- Pending: `apps/macos/Scripts/validate-recording-artifact-format.sh`.

## Diagnostics Redaction

- Pending: diagnostic bundle and redaction focused checks for Apple processing
  metadata keys and forbidden raw-content fields.

## CPU And Resource Gates

- Pending:
  `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-artifact-metadata`.
- Pending:
  `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-cpu-evidence`.

## Manual Runtime Evidence

- Pending: `manual-runtime-matrix.md`.

## Local CI

- Pending: `infra/scripts/ci-local.sh`.
