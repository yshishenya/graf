# Test Results: WebRTC AEC3 Speakerphone Spike

Date: 2026-06-22

This file records metadata-only validation evidence. It intentionally excludes
raw audio, transcripts, local private paths, signed URLs, credentials, and
unbounded debug logs.

## Automated Results

| Check | Result | Notes |
| --- | --- | --- |
| `swift test --package-path apps/macos --filter 'WebRTCAEC3ModelsTests|WebRTCAEC3EvaluationTests|WebRTCAEC3ValidationCorpusTests|WebRTCAEC3SpikeContractTests|CaptureControlTests|LocalRecordingManifestTests|LocalRecordingWriterSystemAudioTests|RecordingEvidenceTests|DesktopUploadQueueTests|DiagnosticRedactionTests|LeakageDiagnosticBundleTests'` | Pass | 125 tests, 0 failures |
| `bash apps/macos/Scripts/validate-webrtc-aec3-speakerphone-spike.sh --self-test-corpus` | Pass | `full_files=60`, `slices=300`, `controlled_rows=10` |
| `bash apps/macos/Scripts/validate-webrtc-aec3-speakerphone-spike.sh --self-test-contracts` | Pass | `primaryOutcome=blocked_route_topology` |
| `bash apps/macos/Scripts/validate-webrtc-aec3-speakerphone-spike.sh --self-test-status` | Pass | AEC3 status copy, priority, and no-noisy-alert checks |
| `bash apps/macos/Scripts/validate-webrtc-aec3-speakerphone-spike.sh --self-test-diagnostics` | Pass | `removed=6` forbidden diagnostic fields |
| `bash apps/macos/Scripts/validate-webrtc-aec3-speakerphone-spike.sh --self-test-rollback` | Pass | `trigger=referenceUnsafe` |
| `bash apps/macos/Scripts/validate-webrtc-aec3-speakerphone-spike.sh --self-test-stop-quit` | Pass | Stop/quit uncertainty stays blocked and visible |
| `bash apps/macos/Scripts/validate-webrtc-aec3-speakerphone-spike.sh --self-test-decision` | Pass | `primaryOutcome=defer_to_fallback_decision`, `fallbackFeature=040-speakerphone-recording-fallback-decision` |
| `swift test --package-path apps/macos` | Pass | 559 tests, 0 failures |
| `apps/macos/Scripts/validate-recording-artifact-format.sh --help` | Pass | Script executed full validation: recording artifact format passed |
| `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-artifact-metadata` | Pass | Existing package-truth metadata gate passed |
| `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-cpu-evidence` | Pass | Existing CPU evidence gate passed |
| `apps/macos/Scripts/validate-low-resource-no-hang.sh` | Pass | Metadata-safe no-hang gate completed; UI no-hang variant was not accepted because the opt-in environment flag was not set |
| `infra/scripts/ci-local.sh` | Pass | 530 server tests passed, 4 skipped; lint, compile, compose config, and deployment evidence scan passed |

## Checklist Review

Final implementation was reviewed against:

- `checklists/audio-capture.md`
- `checklists/security-privacy.md`
- `checklists/ux-status.md`

Review result: pass.

Implementation evidence:

- App status states are visible in the capture UI through calm status notes,
  including blocked, rollback, fallback-relevant, and user-attention states.
- Active capture and Stop remain visible while AEC3 status is present.
- Blocked and unproven copy is guarded against clean-recording claim words in
  English and Russian.
- Diagnostics keep AEC3 evidence metadata-only and remove raw audio,
  transcripts, private paths, credentials, signed URLs, and unbounded logs.
- Diagnostic bundles include fallback planning, supporting-route counts, and
  no-broadened-scope flags as bounded metadata.
- Supporting USB, wired, Bluetooth, AirPods, and browser rows remain evidence
  only and cannot broaden the 039 built-in speakerphone promotion scope.
