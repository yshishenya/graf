#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

echo "apple_voice_processing_spike_validation=started"

swift test --package-path "$ROOT_DIR/apps/macos" --filter 'AppleVoiceProcessingModelsTests|AppleVoiceProcessingEvaluationTests|AppleVoiceProcessingSpikeContractTests|LeakageMeasurementTests/testAppleProcessing|LocalRecordingManifestTests/testManifestServiceThreadsAppleProcessingOutcomeMetadata|LocalRecordingManifestTests/testAppleProcessing|LocalRecordingWriterSystemAudioTests/testWriterAttachesAppleCandidateMetadataWithoutReplacingOriginalTracks|LocalRecordingLeakageFinalizationTests/testAppleCandidateMetadataDoesNotOverrideLeakageTruth|CaptureSessionSafetyTests/testAppleCandidateFailureCannotHideActiveCaptureOrRemoveStop|DiagnosticRedactionTests/testAppleProcessing|LeakageDiagnosticBundleTests/testLocalRecordingBundleIncludesMetadataOnlyAppleProcessingOutcomeForAllStates|RecordingEvidenceTests/testLocalRecordingEvidenceSummaryIsMetadataOnly'

"$ROOT_DIR/apps/macos/Scripts/validate-recording-artifact-format.sh"
"$ROOT_DIR/apps/macos/Scripts/validate-system-audio-capture-pivot.sh" --self-test-artifact-metadata
"$ROOT_DIR/apps/macos/Scripts/validate-system-audio-capture-pivot.sh" --self-test-cpu-evidence

echo "apple_voice_processing_spike_outcome=defer_to_webrtc_aec3"
echo "apple_voice_processing_spike_validation=passed"
