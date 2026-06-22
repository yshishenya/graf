# Quickstart: Apple Voice Processing Spike

## Goal

Validate whether Apple native voice processing can truthfully reduce built-in
speaker-to-mic leakage for 2brain Rec without breaking package truth, local
speech, alignment, visible Stop, or metadata-only diagnostics.

## Automated Checks

Run from the repository root after implementation:

```sh
swift test --package-path apps/macos --filter 'MicrophoneCaptureServiceTests|LocalRecordingWriterSystemAudioTests|LocalRecordingManifestTests|LocalRecordingLeakageFinalizationTests|DiagnosticRedactionTests|LeakageDiagnosticBundleTests|RecordingEvidenceTests'
```

Run package and realtime-safety validators:

```sh
apps/macos/Scripts/validate-apple-voice-processing-spike.sh
apps/macos/Scripts/validate-recording-artifact-format.sh
apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-artifact-metadata
apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-cpu-evidence
```

Run the repository local gate before implementation closeout:

```sh
infra/scripts/ci-local.sh
```

## Manual Runtime Matrix

Record metadata-only evidence under
`specs/038-apple-voice-processing-spike/evidence/`.

| Scenario | Required Result |
|---|---|
| Built-in mic plus built-in speakers, far-end only | Baseline and candidate leakage summaries recorded; no clean claim unless leakage gate passes. |
| Built-in mic plus built-in speakers, near-end only | Local speech preserved; no half-duplex or heavy suppression. |
| Built-in mic plus built-in speakers, double-talk | Local speech preservation and residual leakage both classified. |
| Loud speaker / clipping | Candidate fails closed if clipping invalidates evidence. |
| Route change before/during recording | Candidate records stable, blocked, degraded, or unproven route truth. |
| Built-in mic plus wired headphones | Confirms clean/headset route remains separate from speakerphone acceptance. |
| USB headset | Confirms headset-class route behavior and avoids false Apple dependency. |
| Browser meeting target | Confirms evidence is not synthetic-only. |
| Stop while candidate processing is active | Active indicator clears; capture stops; no hidden processing remains. |
| Diagnostics export | Metadata only; no raw audio, transcripts, credentials, signed URLs, private paths, or meeting content. |

Bluetooth or AirPods-class route evidence is useful when hardware is available
but not required for the first built-in speakerphone decision.

## Package Inspection

For every accepted candidate run:

1. Confirm original `mic.wav`, `incoming.wav`, and `manifest.json` remain
   traceable.
2. Confirm candidate evidence labels original, processed, guidance-only,
   unproven, or blocked state without contradiction.
3. Confirm `durationDifferenceSeconds <= 3` or the accepted current tolerance.
4. Confirm existing leakage finalization remains authoritative for clean status.
5. Confirm local speech preservation is recorded for near-end-only and
   double-talk intervals.
6. Confirm diagnostics remain metadata-only after redaction.

## Outcome Decision

At closeout, select exactly one primary outcome:

- `accepted_for_builtin_speakerphone`
- `accepted_for_guidance_only`
- `accepted_for_headset_routes_only`
- `blocked_route_topology`
- `blocked_quality`
- `blocked_stability`
- `defer_to_webrtc_aec3`

If the outcome is not `accepted_for_builtin_speakerphone`, identify whether the
next feature should be `039-webrtc-aec3-speakerphone-spike`, `040` fallback
decision, or guidance/onboarding work.

## Out Of Scope For This Quickstart

- WebRTC AEC3 implementation.
- Automatic mixed-audio fallback.
- Production rollout claim.
- Direct desktop upload to MediaScribe.
- Content-bearing Langfuse traces.
