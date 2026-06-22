# Quickstart: WebRTC AEC3 Speakerphone Spike

## Goal

Validate whether WebRTC AEC3 can truthfully become the main
recording/transcription microphone candidate for built-in Mac microphone plus
built-in Mac speakers without breaking original package truth, local speech,
alignment, visible Stop, rollback, app status, licensing, or metadata-only
diagnostics.

## Automated Checks

Run focused macOS tests from the repository root after implementation:

```sh
swift test --package-path apps/macos --filter 'WebRTCAEC3ModelsTests|WebRTCAEC3EvaluationTests|WebRTCAEC3ValidationCorpusTests|WebRTCAEC3SpikeContractTests|CaptureControlTests|LocalRecordingManifestTests|LocalRecordingWriterSystemAudioTests|RecordingEvidenceTests|DesktopUploadQueueTests|DiagnosticRedactionTests|LeakageDiagnosticBundleTests'
```

Run package and validation tooling:

```sh
bash apps/macos/Scripts/validate-webrtc-aec3-speakerphone-spike.sh --self-test-corpus
bash apps/macos/Scripts/validate-webrtc-aec3-speakerphone-spike.sh --self-test-contracts
bash apps/macos/Scripts/validate-webrtc-aec3-speakerphone-spike.sh --self-test-status
bash apps/macos/Scripts/validate-webrtc-aec3-speakerphone-spike.sh --self-test-diagnostics
bash apps/macos/Scripts/validate-webrtc-aec3-speakerphone-spike.sh --self-test-rollback
bash apps/macos/Scripts/validate-webrtc-aec3-speakerphone-spike.sh --self-test-stop-quit
bash apps/macos/Scripts/validate-webrtc-aec3-speakerphone-spike.sh --self-test-decision
apps/macos/Scripts/validate-recording-artifact-format.sh
apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-artifact-metadata
apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-cpu-evidence
```

Use `bash` for the 039 helper script so local macOS extended attributes cannot
block direct script execution.

Run the repository local gate before implementation closeout:

```sh
infra/scripts/ci-local.sh
```

## Lab-Grade Corpus Gate

Record metadata-only evidence under
`specs/039-webrtc-aec3-speakerphone-spike/evidence/`.

Before running corpus validation, declare the versioned acceptance-threshold
profile for residual leakage, speech preservation, double-talk, timing drift,
clipping/dropout, CPU/no-hang behavior, Stop/quit behavior, diagnostics safety,
app-status consistency, and rollback triggers. If the profile changes, rerun the
affected promotion rows before using them for any immediate-promotion decision.

| Scenario Family | Required Result |
|---|---|
| Far-end-only leakage | At least ten files, five slices per file, full-file validation for every file, and no residual leakage critical failure. |
| Near-end-only local speech | Local speech preserved; no suppression, gating, or unintelligible result. |
| Double-talk | Local speech preservation and residual leakage both classified. |
| Loud-speaker/clipping stress | Candidate blocks or rolls back if clipping invalidates evidence. |
| Route-change/timing stress | Unsafe delay, jitter, call ordering, or drift blocks promotion or triggers rollback. |
| Unsafe-reference negative control | Missing, late, protected, silent, clipped, or non-representative reference fails closed. |

Each scenario family must include at least two 20 minute or longer full-file
runs, at least two room/acoustic conditions, at least two Mac/device profiles,
and at least three speaker-volume levels before immediate promotion is allowed.

## Controlled Real-Hardware App Recording Matrix

Use consented test signals or synthetic fixtures. Do not commit raw audio or
private meeting content.

| Scenario | Required Result |
|---|---|
| Built-in mic plus built-in speakers, far-end only | Candidate and original microphone truth recorded; no clean-recording claim unless all gates pass. |
| Built-in mic plus built-in speakers, near-end only | Local speech remains usable. |
| Built-in mic plus built-in speakers, double-talk | Leakage and speech preservation both pass. |
| Loud built-in speakers | Clipping blocks promotion or records safe rollback. |
| Route/reference change during recording | Original microphone truth restored and app status shows rollback/problem. |
| Stop while AEC3 is evaluating or promoted | Active indicator clears; Stop is not blocked; no hidden processing remains. |
| App status | Candidate, blocked, rollback, and fallback-relevant states appear in calm local copy. |
| Rollback visibility | Original microphone truth is restored, the clean-recording claim is removed, and app status explains the rollback without noisy alerts. |
| Diagnostics export | Metadata only; no raw audio, transcripts, credentials, signed URLs, private paths, or meeting content. |

## Supporting Route Evidence

Collect supporting rows when hardware is available:

- built-in mic plus wired headphones;
- USB headset;
- Bluetooth or AirPods-class route;
- at least one browser meeting target.

Supporting rows can narrow or explain the decision but cannot broaden the `039`
promotion scope beyond built-in Mac microphone plus built-in Mac speakers.

## Package Inspection

For every accepted candidate run:

1. Confirm original `mic.wav`, `incoming.wav`, and `manifest.json` remain
   traceable.
2. Confirm candidate evidence labels original, candidate, derived, promoted,
   rolled-back, unproven, or blocked state without contradiction.
3. Confirm every promoted row uses the declared acceptance-threshold profile.
4. Confirm app status matches package truth.
5. Confirm rollback restores original microphone truth and removes the
   clean-recording claim when runtime evidence becomes unsafe.
6. Confirm existing leakage finalization remains authoritative unless
   immediate-promotion and package-readiness gates both pass.
7. Confirm diagnostics remain metadata-only after redaction.

## Outcome Decision

At closeout, select exactly one primary outcome:

- `accepted_for_immediate_promotion`
- `accepted_for_derived_candidate_only`
- `accepted_for_guidance_only`
- `blocked_route_topology`
- `blocked_quality`
- `blocked_stability`
- `defer_to_fallback_decision`

If the outcome is not `accepted_for_immediate_promotion`, identify whether the
next feature should be `040-speakerphone-recording-fallback-decision`,
route-specific validation, guidance/onboarding work, or dependency packaging
work.

## Out Of Scope For This Quickstart

- Broad clean-recording claims for Bluetooth, AirPods, USB, wired, browser, or
  external display/output routes.
- Production rollout claim.
- Direct desktop upload to MediaScribe.
- Content-bearing Langfuse traces.
- Committing raw corpus audio, real meeting transcripts, private meeting
  screenshots, signed URLs, credentials, or private local paths.
