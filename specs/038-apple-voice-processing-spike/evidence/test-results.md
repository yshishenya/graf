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
- 2026-06-22: US2 red check,
  `swift test --package-path apps/macos --filter
  'LocalRecordingManifestTests/testAppleProcessingLineageLabelsRoundTripWithoutChangingOriginalTracks|LocalRecordingWriterSystemAudioTests/testWriterAttachesAppleCandidateMetadataWithoutReplacingOriginalTracks|LocalRecordingLeakageFinalizationTests/testAppleCandidateMetadataDoesNotOverrideLeakageTruth|AppleVoiceProcessingSpikeContractTests/testManifestFixtureWithAppleCandidateMetadataDecodesWithoutRawAudio'`,
  failed as expected before implementation on missing package lineage labels,
  missing writer `appleProcessingOutcome` threading, and a contract fixture
  helper/type inference issue in the new tests.
- 2026-06-22: US2 focused rerun,
  `swift test --package-path apps/macos --filter
  'LocalRecordingManifestTests/testAppleProcessingLineageLabelsRoundTripWithoutChangingOriginalTracks|LocalRecordingWriterSystemAudioTests/testWriterAttachesAppleCandidateMetadataWithoutReplacingOriginalTracks|LocalRecordingLeakageFinalizationTests/testAppleCandidateMetadataDoesNotOverrideLeakageTruth|AppleVoiceProcessingSpikeContractTests/testManifestFixtureWithAppleCandidateMetadataDecodesWithoutRawAudio'`,
  passed with 4 tests, 0 failures. Evidence: Apple candidate metadata
  round-trips in manifests, writer keeps `mic.wav` and `incoming.wav` as
  original tracks, fixture metadata stays content-free, and leakage
  finalization remains authoritative.
- 2026-06-22: US3 red check,
  `swift test --package-path apps/macos --filter
  'AppleVoiceProcessingEvaluationTests/testFailClosedRowsCoverUnavailableControlledReferenceAndTopologyFailures|AppleVoiceProcessingEvaluationTests/testAppleCandidateLifecycleCoordinatorReleasesOnStopFailedStartAndAppQuit|CaptureSessionSafetyTests/testAppleCandidateFailureCannotHideActiveCaptureOrRemoveStop|LeakageDiagnosticBundleTests/testLocalRecordingBundleIncludesMetadataOnlyAppleProcessingOutcomeForAllStates|DiagnosticRedactionTests/testAppleProcessingRouteLineageCpuAndFailureFieldsStayBounded|CaptureControlTests/testAppleProcessingStatusCopyForGuidanceBlockedAndUnprovenDoesNotClaimCleanRecording'`,
  failed as expected before implementation on missing Apple failure reason
  vocabulary, fail-closed row normalization, lifecycle coordinator, diagnostic
  bundle fields, redaction allowlist fields, and capture-control Apple status
  copy.
- 2026-06-22: US3 focused rerun,
  `swift test --package-path apps/macos --filter
  'AppleVoiceProcessingEvaluationTests/testFailClosedRowsCoverUnavailableControlledReferenceAndTopologyFailures|AppleVoiceProcessingEvaluationTests/testAppleCandidateLifecycleCoordinatorReleasesOnStopFailedStartAndAppQuit|CaptureSessionSafetyTests/testAppleCandidateFailureCannotHideActiveCaptureOrRemoveStop|LeakageDiagnosticBundleTests/testLocalRecordingBundleIncludesMetadataOnlyAppleProcessingOutcomeForAllStates|DiagnosticRedactionTests/testAppleProcessingRouteLineageCpuAndFailureFieldsStayBounded|CaptureControlTests/testAppleProcessingStatusCopyForGuidanceBlockedAndUnprovenDoesNotClaimCleanRecording'`,
  passed with 6 tests, 0 failures. Evidence: Apple failures fail closed with
  bounded reason codes, lifecycle release is recorded for Stop/failed
  start/app quit, active capture cannot hide Stop, diagnostics remain
  metadata-only, and capture copy avoids clean-recording claims.
- 2026-06-22: US4 red check,
  `swift test --package-path apps/macos --filter
  'AppleVoiceProcessingEvaluationTests/testFinalOutcomeSummaryKeepsExactlyOnePrimaryOutcomeAndMapsNextStep|AppleVoiceProcessingSpikeContractTests/testSummariesCannotClaimCleanSpeakerphoneWithoutAcceptedBuiltinGates'`,
  failed as expected before implementation on missing final outcome summary
  generation.
- 2026-06-22: US4 focused rerun,
  `swift test --package-path apps/macos --filter
  'AppleVoiceProcessingEvaluationTests/testFinalOutcomeSummaryKeepsExactlyOnePrimaryOutcomeAndMapsNextStep|AppleVoiceProcessingSpikeContractTests/testSummariesCannotClaimCleanSpeakerphoneWithoutAcceptedBuiltinGates'`,
  passed with 2 tests, 0 failures. Evidence: final summaries keep exactly one
  primary outcome, normalize next-step recommendation, and do not emit clean
  speakerphone claims when accepted built-in gates are not proven. Decision
  record outcome: `defer_to_webrtc_aec3`.
- 2026-06-22: Post-review fix rerun,
  `swift test --package-path apps/macos --filter
  'AppleVoiceProcessingEvaluationTests/testAppleCandidateLifecycleCoordinatorReleasesOnStopFailedStartAndAppQuit|LocalRecordingManifestTests/testAppleProcessingLineageLabelsRoundTripWithoutChangingOriginalTracks|CaptureControlTests/testAppleProcessingStatusCopyForGuidanceBlockedAndUnprovenDoesNotClaimCleanRecording|LeakageMeasurementTests/testAppleProcessing'`,
  passed with 5 tests, 0 failures. Evidence: release snapshots preserve the
  released candidate id, idle release is a no-op, all lineage labels
  round-trip, Apple status copy stays claim-safe, and Apple leakage comparison
  tests remain covered.

## Package Inspection

- 2026-06-22: `apps/macos/Scripts/validate-apple-voice-processing-spike.sh`
  passed. The helper ran the 038 focused SwiftPM suite with 27 tests and 0
  failures, then ran `apps/macos/Scripts/validate-recording-artifact-format.sh`;
  artifact-format validation passed with the full macOS SwiftPM package at
  529 tests and 0 failures, `ContractValidation: PASS`, and
  `audio-rt-safety-check: ACCEPTED`.

## Diagnostics Redaction

- 2026-06-22: `apps/macos/Scripts/validate-apple-voice-processing-spike.sh`
  passed Apple diagnostic bundle/redaction coverage. Evidence covers
  `appleProcessingOutcome`, validation rows, route class, lineage, CPU,
  latency, lifecycle, failure fields, and forbidden raw-content fields.

## CPU And Resource Gates

- 2026-06-22:
  `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-artifact-metadata`
  passed inside the 038 helper.
- 2026-06-22:
  `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-cpu-evidence`
  passed inside the 038 helper.

## Manual Runtime Evidence

- 2026-06-22: Manual runtime hardware rows are recorded as blocked/deferred in
  `manual-runtime-matrix.md`. No accepted live Apple processing route was
  claimed; the primary outcome remains `defer_to_webrtc_aec3`.

## Local CI

- 2026-06-22: Final post-review `infra/scripts/ci-local.sh` passed. Evidence summary:
  server tests `530 passed, 4 skipped`, server lint passed, Python compile
  passed, RLS hardening validation remained inside the expected blocked
  `postgres_test_database_required` boundary, production compose config
  rendered, deployment evidence scan passed, and final result was
  `ci_local_result=pass`.
