# Quickstart: Microphone Sample Graph Foundation

## Goal

Validate that `037` records the local microphone through an app-owned selected
or default input stream while preserving the current dual-track local package and
leakage truth.

## Automated Checks

Run from the repository root after implementation:

```sh
cd apps/macos
swift test --filter MicrophoneCaptureServiceTests
swift test --filter LocalRecordingWriterSystemAudioTests
swift test --filter LocalRecordingManifestTests
swift test --filter LocalRecordingLeakageFinalizationTests
swift test --filter DiagnosticRedactionTests
```

Run focused validators:

```sh
cd apps/macos
Scripts/validate-recording-artifact-format.sh
Scripts/validate-system-audio-capture-pivot.sh --self-test-artifact-metadata
Scripts/validate-system-audio-capture-pivot.sh --self-test-cpu-evidence
Scripts/sample-system-audio-cpu-gate.sh idle
```

Run the repository local gate before claiming implementation completion:

```sh
infra/scripts/ci-local.sh
```

## Manual Runtime Matrix

Record evidence in `specs/037-microphone-sample-graph-foundation/evidence/`
when tasks create the evidence template.

| Scenario | Expected Result |
|----------|-----------------|
| No explicit recording microphone selected | Recording uses current macOS default input and stores `macOSDefaultFallback` metadata. |
| Native recording microphone selected | Recording uses selected input and stores `userSelected` metadata. |
| Selected microphone unplugged before Record | Start is blocked or fails closed with `device_unavailable`; no clean success claim. |
| 2brain virtual microphone selected | Selection is rejected before capture with self-routing recovery metadata. |
| Microphone permission denied | Start is blocked with permission recovery copy; no partial accepted package. |
| Microphone frames stop or remain silent | Manifest records `no_frames`, `silent_input`, degraded, failed, or unproven truth. |
| Speakerphone leakage present | `020` leakage finalization remains authoritative and does not mark clean without evidence. |
| Stop while recording | Mic graph stops, package finalizes, active indicator clears, no invisible capture remains. |
| App quit while recording | Capture resources release and final truth is bounded, not clean by default. |

## Package Inspection

For every accepted controlled recording:

1. Confirm the package contains `mic.wav`, `incoming.wav`, and `manifest.json`.
2. Confirm `manifest.json` has exactly one `localMic` and one `remoteSpeaker`
   original track.
3. Confirm `durationDifferenceSeconds <= 3`.
4. Confirm microphone selection metadata names either the selected input or the
   macOS default fallback.
5. Confirm microphone stream metadata proves app-owned sample source capture
   for graph readiness.
6. Confirm diagnostics and evidence contain no raw audio, transcript text,
   credentials, tokens, signed URLs, private meeting content, live local paths,
   or participant identifiers.

## Out Of Scope For This Quickstart

- Apple voice processing acceptance.
- WebRTC AEC3 acceptance.
- Speakerphone clean fallback decision.
- Recording-readiness onboarding UX beyond basic native selection.
- MediaScribe, upload, server, or Langfuse changes.

## Latest Implementation Evidence

Recorded on 2026-06-18:

- Focused SwiftPM sweep passed:
  `swift test --filter 'MicrophoneCaptureServiceTests|RecordingMicrophoneSelectionTests|LocalRecordingWriterSystemAudioTests|CaptureControlTests|CaptureSessionSafetyTests|LocalRecordingManifestTests|LocalRecordingLeakageFinalizationTests|DesktopUploadQueueTests|MicrophoneSampleGraphContractTests|DiagnosticRedactionTests|LeakageDiagnosticBundleTests|RecordingEvidenceTests'`
  executed 112 tests with 0 failures.
- `Scripts/validate-recording-artifact-format.sh` passed. The helper ran the
  macOS package tests, contract validation, and audio realtime safety checks.
- `Scripts/validate-system-audio-capture-pivot.sh --self-test-artifact-metadata`
  passed.
- `Scripts/validate-system-audio-capture-pivot.sh --self-test-cpu-evidence`
  passed.
- `Scripts/sample-system-audio-cpu-gate.sh idle` was run twice and failed
  because `/Applications/2brain Rec.app` was already running in the user
  environment and `coreaudiod` stayed above the idle threshold. Treat this as a
  blocked manual idle-gate rerun: quit the installed app and rerun the command
  before accepting release CPU evidence.
- `infra/scripts/ci-local.sh` passed with `ci_local_result=pass`.
