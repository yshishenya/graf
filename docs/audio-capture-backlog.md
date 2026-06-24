# Audio Capture Backlog

Date: 2026-06-23

This backlog expands the deferred live speakerphone cleanup work left by
`020-speaker-to-mic-leakage` and `025-system-audio-capture-pivot`. It is not a
Spec Kit feature spec yet. Use it as prepared context when creating future
`$speckit-specify` slices.

## Numbering And Feature Registry

This document is the project-owned registry for capture, recording, upload,
transcription, and media-revision feature numbers. Update it before starting a
new Spec Kit feature when the intended number is not already represented here.

Before creating a new feature spec or branch, verify the next number against:

- current `specs/` directories;
- local branches;
- remote branches after `git fetch --all --prune`;
- feature numbers mentioned in committed docs and backlog files;
- historical spec paths in `git log --all --name-only -- specs`.

Do not rely only on the highest visible directory in `specs/`. A number may be
reserved by a branch, backlog, historical draft, or another worktree even when
the spec directory is not present in the current checkout.

If a number is reserved here but not yet implemented, do not reuse it unless the
user explicitly retires or renumbers that reservation.

### Current Allocation

| Number(s) | Status | Source / Notes |
|---|---|---|
| `001`-`008`, `010`-`022`, `025`-`036` | Active or accepted specs | Present in the current Spec Kit line or preserved as accepted/historical feature work. |
| `009` | Superseded / do not reuse casually | Old meeting-mute draft superseded by `022-meeting-mute-truth`. |
| `023`-`024` | Historical draft numbers | Historical spec paths exist in git history. Reuse only after explicit owner decision and registry update. |
| `037` | Implemented | `microphone-sample-graph-foundation`: app-owned mic sample graph before cleanup/AEC work. |
| `038` | Outcome recorded | `apple-voice-processing-spike`: Apple processing remains metadata/guidance evidence only; primary outcome is `defer_to_webrtc_aec3`. |
| `039` | Next reserved backlog | `webrtc-aec3-speakerphone-spike`: WebRTC AEC3 speakerphone cleanup spike. |
| `040` | Reserved backlog | `speakerphone-recording-fallback-decision`: truthful fallback decision if clean built-in speakerphone capture is not proven. |
| `041` | Reserved backlog | `recording-permission-readiness-onboarding`: Mic and Screen/System Audio readiness before recording. |
| `042` | Claimed branch | `recording-sync-transcription-loop`: offline-safe recording upload, server transcription, and transcript display loop. |
| `043` | Active / existing spec branch | `app-zoom-shortcuts`: present in git history/branch after `git fetch --all --prune`; do not reuse. |
| `044` | Active / reserved backlog | `speakerphone-echo-noise-suppression`: real runtime echo cancellation/noise suppression path after the `039` WebRTC AEC3 spike. |
| `045` | Active implementation branch | `transcription-results-pipeline`: product upload/transcription/result loop; imperfect local quality is diagnostic metadata, not an upload blocker. |
| `046` | Candidate follow-up / not created | `meeting-playback-timestamp-seek`: possible MVP review-player slice surfaced by `045`; this is not an audio cleanup/AEC feature. |
| `048` | Reserved backlog | `local-media-trim-revisions`: post-MVP local audio/video trim/edit revisions; see `docs/post-mvp-editing-media-backlog.md`. |
| `049` | Reserved backlog | `online-transcript-edit-sync`: post-MVP online transcript/speaker edit sync and conflict handling; see `docs/post-mvp-editing-media-backlog.md`. |
| `050` | Reserved backlog | `video-capture-package-foundation`: post-MVP video-capable capture package foundation; see `docs/post-mvp-editing-media-backlog.md`. |
| `051` | Reserved backlog | `media-reprocess-replace-flow`: post-MVP replace/reprocess flows that depend on accepted media revision identity; see `docs/post-mvp-editing-media-backlog.md`. |

As of 2026-06-24, `046` is a candidate playback/timestamp-seek follow-up from
`045`, not a speakerphone cleanup number. If the owner accepts that reservation,
the next unreserved candidate after documented reservations is `047`. Re-check
all sources above before creating any new feature.

### Useful Checks

```sh
git fetch --all --prune
find specs -maxdepth 1 -mindepth 1 -type d -print | sort
git branch -a --format='%(refname:short)' | sort
git log --all --name-only --pretty=format: -- specs | rg '^specs/[0-9]{3}-' | sort -u
rg -n '0[0-9]{2}-|feature [0-9]{3}|Feature [0-9]{3}' docs specs AGENTS.md
```

When these checks disagree, stop and reconcile this registry before creating
the new feature.

## Current Problem In Plain Language

When the user records a meeting through Mac speakers, the physical microphone
hears the speakers. As a result, `mic.wav` contains the local speaker plus some
remote participant audio from the room. This is acoustic speaker-to-mic leakage.

Current accepted behavior:

- `025` records separate `mic.wav` and `incoming.wav` with system-audio capture.
- `020` analyzes saved evidence after `Stop`.
- If `mic.wav` is contaminated, unproven, or not measurable, the package fails
- If `mic.wav` is contaminated, unproven, or not measurable, local package truth
  records failed/degraded transcription readiness. Feature `045` makes that
  quality truth diagnostic for upload/transcription eligibility when required
  files, consent, permissions, and integrity are valid.

Current missing behavior:

- The app does not clean the microphone live.
- Built-in Mac microphone plus built-in Mac speakers are not accepted as clean
  dual-track speakerphone recording.
- Apple/WebRTC/AEC cleanup remains future gated work under `044`; it is not
  required for the `045` results pipeline to process imperfect source audio.

## External Research Summary

### Apple Voice Processing

Apple exposes native voice-processing paths that are relevant to echo
cancellation and voice isolation:

- `AVAudioIONode.setVoiceProcessingEnabled(_:)` enables voice processing on an
  I/O node.
- Apple's WWDC19 AVAudioEngine session says voice processing supports echo
  cancellation use cases and that echo cancellation requires the input and
  output nodes to run in voice-processing mode.
- `kAudioUnitSubType_VoiceProcessingIO` is Apple's lower-level voice-processing
  I/O audio unit.
- `AVCaptureDevice.MicrophoneMode.voiceIsolation` is a system microphone mode
  that processes microphone audio to isolate voice and attenuate other signals.

Important risk for 2brain Rec:

- Apple voice processing may need the app to own both microphone input and the
  output signal used as the echo reference.
- In the current system-audio MVP, the meeting app or browser usually owns the
  speaker playback, not 2brain Rec.
- Therefore Apple processing is a spike candidate, not an automatic solution.

### WebRTC AEC3

WebRTC AEC3 is the more controllable software echo-cancellation path. Public
source shows the core model:

- feed render/far-end audio into AEC analysis;
- feed capture/near-end microphone audio into capture analysis/processing;
- process small realtime frames;
- handle delay, clock alignment, double-talk, residual echo, clipping, route
  changes, CPU, and latency.

Important risk for 2brain Rec:

- The system-audio stream from ScreenCaptureKit must be close enough to the
  real speaker signal to serve as the AEC render reference.
- If the reference and microphone clocks drift or are delayed too much, AEC and
  leakage measurement can become unreliable.
- Bad AEC can damage local speech, especially during double-talk.

### Parrot Reference

The reviewed Parrot repository uses a simple and useful capture shape:

- ScreenCaptureKit for system audio.
- AVAudioEngine for microphone capture.
- no virtual audio driver requirement.

It does not appear to implement live AEC, WebRTC AEC3, Apple voice processing,
or a package-level leakage gate. Treat it as a clean-room architecture reference
for capture shape, not as a solution to speaker-to-mic leakage.

## Feature 037: Microphone Sample Graph Foundation

### Purpose

Create an app-owned microphone sample graph so future cleanup can process mic
frames before writing `mic.wav`.

Today, normal recording uses `AVAudioRecorder` when no custom microphone sample
source is provided. That writes the physical microphone signal directly to
`mic.wav`. It is simple, but it gives the app little control over the samples
before they are persisted.

### User Value

This does not promise echo cleanup yet. It gives the product the control needed
to clean, measure, align, and compare microphone audio safely in later features.

### Scope

- Replace or supplement the `AVAudioRecorder` microphone path with an
  `AVAudioEngine`-backed sample source.
- Feed microphone samples into the existing `LocalRecordingWriter` through
  `microphoneSampleSourceFactory`.
- Preserve the existing `mic.wav`, `incoming.wav`, and `manifest.json` package
  contract.
- Preserve existing permission gates, visible Record/Stop, one-action Stop,
  no-content diagnostics, and leakage finalization.
- Keep the current `AVAudioRecorder` path as a fallback until the new graph is
  validated or explicitly removed by a later spec.

### Out Of Scope

- No Apple voice processing acceptance.
- No WebRTC AEC3.
- No claim that built-in speakerphone is clean.
- No MediaScribe, upload, server, or Langfuse changes.

### Key Questions For Spec

- Which sample rate enters the app graph: hardware rate, 48 kHz, or 16 kHz?
- Where does sample-rate conversion happen?
- Does `mic.wav` stay 16 kHz PCM s16le?
- How is the microphone stream timestamped relative to `incoming.wav`?
- What happens on mic route change, permission revoke, sleep/wake, or device
  removal?
- Is the `AVAudioRecorder` fallback allowed in accepted MVP recording after
  the graph is introduced?

### Acceptance Gates

- A controlled recording still produces `mic.wav`, `incoming.wav`, and
  `manifest.json`.
- Existing `020` leakage gates still run after `Stop`.
- Existing `025` system-audio capture behavior is unchanged.
- Local mic samples are observable through metadata-only counters and levels.
- Timeline alignment does not regress against current `durationDifference`
  gates.
- Stop/quit releases audio resources and does not leave the app recording.
- No raw samples, transcript text, or meeting content are written to diagnostics.

### Likely Code Areas

- `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`
- `apps/macos/RecApp/Sources/Capture/MicrophoneCaptureService.swift`
- `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- `apps/macos/Shared/Sources/Models/AudioModels.swift`
- `apps/macos/Shared/Tests/LocalRecordingWriterSystemAudioTests.swift`
- new tests for an `AVAudioEngine` microphone sample source

### What This Gives Us

- A real mic stream we can process before file write.
- The foundation for Apple voice processing or WebRTC AEC3.
- Better alignment and measurement opportunities.
- Less dependence on opaque recorder behavior.

## Feature 038: Apple Voice Processing Spike

### Purpose

Test whether Apple's native voice-processing stack can reduce speaker-to-mic
leakage enough for built-in Mac microphone plus built-in Mac speakers to become
clean or closer to clean.

### Current Result

As of 2026-06-22, the recorded primary outcome is
`defer_to_webrtc_aec3`.

What 038 proved:

- Apple candidate evidence can be represented as metadata-only manifest and
  diagnostic data.
- Candidate metadata cannot overwrite original `mic.wav`, `incoming.wav`, or
  `manifest.json` truth.
- Existing `020` leakage finalization remains authoritative.
- Apple candidate failures fail closed with bounded reason codes and visible
  Stop/capture controls.
- User-facing and release-facing summaries do not claim clean speakerphone
  behavior unless all accepted built-in speakerphone gates pass.

What 038 did not prove:

- No accepted Apple built-in speakerphone route.
- No accepted live Apple DSP path for persisted package truth.
- No Apple-based clean dual-track speakerphone claim.

Next step: continue with `039-webrtc-aec3-speakerphone-spike`.

### User Value

If this works, it is the lowest-maintenance path to cleaner built-in speaker
recordings. The user can record normally without wearing headphones and without
understanding audio routing.

### Scope

- Build on `037` so microphone audio flows through an app-owned graph.
- Try `AVAudioIONode.setVoiceProcessingEnabled(_:)` on the relevant input and
  output nodes.
- Evaluate `kAudioUnitSubType_VoiceProcessingIO` only if AVAudioEngine cannot
  prove the needed route.
- Observe or guide system Mic Mode / Voice Isolation only as a diagnostic or UX
  helper unless app ownership is proven.
- Compare processed mic evidence against current unprocessed mic behavior.
- Keep original evidence and leakage finalization truth.

### Out Of Scope

- No production acceptance merely because the API is available.
- No hidden system setting changes.
- No browser/meeting-app dependency assumptions.
- No WebRTC AEC3 implementation.
- No automatic mixed-audio fallback.

### Key Questions For Spec

- Can Apple processing see the same far-end signal that reaches the speakers?
- Does the cleaned near-end signal feed both the live microphone path and
  persisted `mic.wav`?
- Does Apple processing preserve local speech during double-talk?
- Does it change sample rate, channel count, AGC/noise behavior, or route
  topology?
- What happens when the user changes microphone, output, volume, or Mic Mode?
- Does it work for built-in speakers only, or also wired/USB/Bluetooth routes?
- How do we clearly label evidence as original, processed, or unproven?

### Required Validation Matrix

- Built-in mic plus built-in speakers.
- Built-in mic plus wired headphones.
- USB headset.
- Bluetooth or AirPods-class route if available, but not required for initial
  acceptance unless the spec expands scope.
- At least one browser meeting target.
- Far-end-only interval: remote speech plays, local user silent.
- Near-end-only interval: local user speaks, remote silent.
- Double-talk interval: both sides speak.
- Loud speaker / clipping case.
- Route change during or between recordings.

### Acceptance Gates

- Leakage status improves versus the unprocessed baseline.
- `mic.wav` can be marked clean only if `020` finalization passes.
- Double-talk does not mute or heavily damage local speech.
- `incoming.wav` and `mic.wav` remain aligned.
- CPU and latency stay within the explicit spec budget.
- Stop/quit does not hang Core Audio or leave capture active.
- Failures are truthful: `leakage_detected`, `unproven`, or `not_measured`, not
  false clean.

### Likely Code Areas

- new app-owned microphone graph from `037`
- `apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift`
- `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`
- `apps/macos/RecApp/Sources/Capture/LeakageMeasurementService.swift`
- `apps/macos/Shared/Tests/LeakageMeasurementTests.swift`
- `apps/macos/Shared/Tests/LocalRecordingLeakageFinalizationTests.swift`
- new manual validation script under `apps/macos/Scripts/`

### What This Gives Us

- A real answer to whether Apple can solve our built-in speaker leakage.
- If yes: a simpler product path than custom WebRTC AEC.
- If no: evidence to justify moving to WebRTC AEC3 or fallback architecture.

## Feature 039: WebRTC AEC3 Speakerphone Spike

### Purpose

Prototype app-owned WebRTC AEC3 using:

- `incoming.wav` / ScreenCaptureKit system audio as the render/far-end
  reference;
- the app-owned microphone stream from `037` as the capture/near-end input;
- a cleaned mic output as a derived or candidate persisted microphone track.

### User Value

If Apple processing cannot prove clean built-in speakerphone behavior, WebRTC
AEC3 is the most controllable path to real speakerphone support.

### Scope

- Add a native processing component around WebRTC AEC3 or an approved wrapper.
- Feed render/far-end reference frames before or in sync with capture frames.
- Process mic capture frames into a cleaned near-end stream.
- Write cleaned output as a derived track or candidate `mic.wav` only when the
  spec explicitly allows it.
- Preserve original `mic.wav` and `incoming.wav` as evidence unless a later spec
  changes artifact semantics.
- Record CPU, latency, delay, residual leakage, double-talk, and failure truth.

### Out Of Scope

- No silent replacement of original evidence.
- No HAL callback file I/O, allocation, logging, network calls, or unbounded
  waits.
- No production rollout until licensing, packaging, notarization, CPU, and crash
  gates pass.
- No claim that browser WebRTC AEC alone solves the issue.

### Key Questions For Spec

- Which WebRTC dependency source is approved: vendored libwebrtc, system
  package, wrapper library, or internal bridge?
- What is the license and redistribution obligation?
- What frame size and sample rate do we use?
- How do we align ScreenCaptureKit system audio with microphone capture?
- How is delay estimation initialized and updated?
- What happens if system-audio reference is late, silent, protected, or missing?
- Is cleaned output a derived track or allowed to become the main mic track?
- What residual leakage threshold promotes a cleaned track to transcription
  readiness?

### Acceptance Gates

- Far-end-only leakage is reduced below the accepted threshold in controlled
  built-in speakerphone tests.
- Near-end-only speech remains intelligible and not over-suppressed.
- Double-talk preserves local speech and avoids filter divergence.
- Route changes fail closed without hanging capture.
- CPU and memory stay within an explicit budget for at least 30 minutes.
- End-to-end latency remains bounded and does not break recording UX.
- Original evidence and derived cleaned output are both traceable in
  `manifest.json`.
- Diagnostics remain metadata-only.

### Likely Code Areas

- `apps/macos/RecApp/Sources/Capture/`
- `apps/macos/Shared/Sources/Models/AudioModels.swift`
- `apps/macos/Shared/Tests/LeakageMeasurementTests.swift`
- `apps/macos/Shared/Tests/LocalRecordingLeakageFinalizationTests.swift`
- `apps/macos/Shared/Tools/LeakageValidation/main.swift`
- build/package configuration for the approved WebRTC dependency

### What This Gives Us

- A path to real acoustic echo cancellation controlled by 2brain Rec.
- Better long-term speakerphone support than an opaque OS-only path.
- A much bigger implementation and validation surface, so it must remain a
  separate feature.

## Feature 040: Speakerphone Recording Fallback Decision

### Purpose

Decide what the product does if clean dual-track built-in speakerphone capture
cannot be proven through Apple processing or WebRTC AEC3.

### User Value

The product must not lie. If the mic track contains speaker audio and cannot be
cleaned reliably, users should still get the most useful truthful recording and
transcription behavior possible.

### Scope

- Use evidence from `038` and `039`.
- Choose one or more accepted fallback modes:
  - headset-first clean dual-track acceptance;
  - built-in speakerphone pilot-only with quality-warning transcription;
  - single mixed meeting audio track;
  - original dual evidence plus derived cleaned track;
  - explicit unsupported route state.
- Define MediaScribe input shape for fallback modes.
- Define transcript/diarization confidence semantics.
- Define user-visible copy for degraded or mixed recordings.

### Out Of Scope

- No new AEC algorithm.
- No deletion/retention changes unless new derived artifacts are accepted.
- No public rollout claim without 034-style readiness evidence.

### Key Questions For Spec

- Is mixed audio more truthful than polluted dual-track in common speakerphone
  cases?
- Can MediaScribe accept a single mixed track for this product path, or do we
  need a separate contract?
- How do we label speaker attribution confidence?
- Does playback expose original evidence, derived cleaned output, or mixed
  audio?
- What does the user see immediately after `Stop`?
- How should review label confidence and speaker attribution for
  `leakage_detected`, `unproven`, or mixed packages now that feature `045`
  makes structurally valid imperfect packages upload/transcription eligible?
- How does deletion truth account for derived/mixed artifacts?

### Acceptance Gates

- The fallback never marks polluted mic audio as clean local speech.
- User-facing copy is truthful and understandable.
- MediaScribe submission rules are explicit.
- Playback/review surfaces do not hide uncertainty.
- Local/server lifecycle accounting includes any new derived or mixed artifact.
- The decision is backed by controlled evidence from Apple/WebRTC spikes or
  explicitly states why those paths are not available.

### What This Gives Us

- A product-safe answer even if perfect speakerphone cleanup is not feasible.
- A clear path to internal pilot without pretending the mic track is clean.
- A boundary between "recording is useful" and "recording is clean dual-track."

## Feature 041: Recording Permission And Readiness Onboarding

### Purpose

Make microphone and Screen/System Audio permissions visible before the user
tries to record.

### User Value

The user should not discover missing permissions only after pressing Record or
during a meeting. A clear readiness screen reduces setup confusion and support
load.

### Scope

- Add a native readiness/onboarding surface for microphone permission,
  Screen/System Audio permission, selected scope, visible indicator, and storage
  readiness.
- Explain missing permission states in simple language.
- Open the correct macOS settings path where possible.
- Keep active Record/Stop controls native and visible.

### Out Of Scope

- No capture cleanup.
- No AEC.
- No auto-start.
- No broad redesign of the web cabinet.

### Acceptance Gates

- The user can see required capture permissions before recording.
- Permission prompts and blocked states match actual macOS status.
- Record remains blocked when required permissions are missing.
- No hidden recording starts from the onboarding surface.
- Accessibility and localization-safe copy are covered.

### What This Gives Us

- Less confusion during first run.
- Cleaner separation between setup problems and audio-quality problems.
- A safer UX before testing more complex speakerphone cleanup.

## Source Links

- Apple `AVAudioIONode.setVoiceProcessingEnabled(_:)`:
  <https://developer.apple.com/documentation/avfaudio/avaudioionode/setvoiceprocessingenabled%28_%3A%29>
- Apple WWDC19 "What's New in AVAudioEngine":
  <https://developer.apple.com/videos/play/wwdc2019/510/>
- Apple WWDC23 "What's new in voice processing":
  <https://developer.apple.com/videos/play/wwdc2023/10235/>
- Apple `kAudioUnitSubType_VoiceProcessingIO`:
  <https://developer.apple.com/documentation/audiotoolbox/kaudiounitsubtype_voiceprocessingio>
- Apple `AVCaptureDevice.MicrophoneMode.voiceIsolation`:
  <https://developer.apple.com/documentation/avfoundation/avcapturedevice/microphonemode/voiceisolation>
- Apple echo-cancelled input preference:
  <https://developer.apple.com/documentation/avfaudio/avaudiosession/setprefersechocancelledinput%28_%3A%29>
- WebRTC AEC3 source:
  <https://chromium.googlesource.com/external/webrtc/+/master/modules/audio_processing/aec3/echo_canceller3.h>
- WebRTC Audio Processing module source:
  <https://webrtc.googlesource.com/src/+/refs/heads/main/modules/audio_processing/>
- Switchboard WebRTC AEC3 explainer:
  <https://switchboard.audio/hub/how-webrtc-aec3-works/>
- Microsoft echo troubleshooting:
  <https://learn.microsoft.com/en-us/azure/communication-services/resources/troubleshooting/voice-video-calling/audio-issues/echo-issue>
