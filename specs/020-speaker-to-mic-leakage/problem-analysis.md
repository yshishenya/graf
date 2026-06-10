# Problem Analysis: Speaker-To-Mic Leakage Control

**Created**: 2026-06-04

This analysis supports [spec.md](spec.md). It records what was learned from the
live recording artifact, the current repository, and public internet research.
It intentionally avoids storing raw audio, transcript text, participant speech,
credentials, signed URLs, or full user-local recording paths.

## Live Recording Evidence

Evidence directory id:
`20260604-091621-C705ED72-E352-4522-93F2-1219953177EE`.

Files observed:

- `manifest.json`
- `mic.wav`
- `incoming.wav`

Manifest summary:

- `schemaVersion`: `local-recording-manifest.v2`
- `status`: `degraded`
- `failureReason`: `timeline_misaligned`
- `mediaScribeSourceMode`: `dual`
- `transcriptionReadiness`: `degraded`
- `externalEgressStarted`: `false`
- `transcriptionStarted`: `false`
- `diagnosticSafe`: `true`

Track summary:

| Track | Role | Format | Duration | Frames | Timeline |
| --- | --- | --- | ---: | ---: | --- |
| `mic.wav` | `local_mic` | WAV PCM s16le mono 16 kHz | ~4393.07 s | 70289061 | aligned |
| `incoming.wav` | `remote_speaker` | WAV PCM s16le mono 16 kHz | ~4240.88 s | 67854036 | misaligned |

Key observation:

- The mic track is about 152.19 seconds longer than the incoming track.
- A package with this mismatch cannot be treated as clean dual-track evidence
  for diarization or AEC-style post-analysis without explicit degraded truth.

## Numerical Audio Analysis

Analysis performed:

- WAV header inspection for both tracks.
- Shared-overlap duration comparison.
- 1-second RMS and zero-lag correlation across the shared overlap.
- Lag search on the loudest incoming windows across +/- 2000 ms.

Results:

- Shared overlap: ~4240.88 seconds.
- Extra mic tail: ~152.19 seconds.
- Incoming-active seconds by simple RMS threshold: 3515.
- Strong zero-lag leak candidates with absolute correlation above 0.20: 2
  seconds.
- Median absolute correlation during incoming-active windows: ~0.013.
- 99th percentile absolute correlation during incoming-active windows: ~0.088.
- Loud incoming windows did not show a stable direct digital-copy lag.

Interpretation:

- The evidence does not look like a persistent direct software mix of
  `incoming.wav` into `mic.wav` at zero latency.
- The user's live observation remains credible as acoustic leakage: remote
  audio played through physical speakers can be captured by the physical
  microphone, especially when using laptop speakers or high output volume.
- The track mismatch separately blocks clean AEC/reference analysis and must be
  fixed or represented truthfully.

Limits:

- Correlation is not speech intelligibility analysis.
- Real meeting content was not transcribed or stored in diagnostics.
- Without a controlled far-end reference stimulus, exact echo return loss,
  intelligibility, and double-talk behavior cannot be accepted from this single
  artifact.

## Current Architecture Findings

Current product baseline:

- The HAL component publishes `2brain Rec Microphone` and `2brain Rec Speaker`.
- The app owns manual `Record`/`Stop` and local persistence.
- Recording artifacts use `mic.wav`, `incoming.wav`, and metadata-only
  `manifest.json`.
- Desktop must not call MediaScribe or store MediaScribe credentials.

Relevant code paths:

- `apps/macos/AudioDriver/Sources/Device/VirtualDeviceRegistry.cpp` declares
  separate virtual devices: `2brain Rec Microphone` and `2brain Rec Speaker`.
- `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp` reads
  virtual mic output from shared `mic_buffer` and writes virtual speaker mix
  into both `speaker_buffer` and `capture_buffer`.
- `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift` captures physical
  microphone frames into shared mic memory and plays shared speaker frames to
  the physical output.
- `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift` currently
  records `mic.wav` via app-side microphone recording and writes `incoming.wav`
  from shared captured speaker frames.
- `apps/macos/RecApp/App/TwoBrainRecApp.swift` starts manual recording after
  route prerequisite checks and writes the local recording directory path to
  local UI state.

Important architectural risk:

- The virtual speaker path is intentionally mirrored into the incoming capture
  track.
- The physical speaker output can acoustically reach the physical microphone.
- Unless the mic path is echo-controlled or route-gated, the local mic track may
  contain remote speaker audio while the incoming track also contains that same
  remote speaker audio.
- The current local writer can produce correctly formatted WAV files while still
  producing semantically contaminated dual tracks.

Recent emergency-fix context:

- Auto-passthrough was disabled by default after a live distortion/hiss report.
- That change reduces surprise route activation risk but does not solve
  speaker-to-mic acoustic leakage during an active meeting route.

## Public Research Summary

Krisp public documentation describes a clean category pattern:

- Krisp Microphone and Krisp Speaker are virtual devices.
- The product places an additional local layer between physical
  microphone/speaker and the communication app.
- Krisp recommends selecting genuine physical devices inside the app and does
  not operate with other virtual microphones.

Public AEC sources agree on the core problem:

- Acoustic echo happens when far-end speech plays through a loudspeaker and is
  picked up by the microphone.
- Browsers often include AEC, but AEC can be disabled or fail when delay,
  double-talk, route changes, or reference mismatch exceed what the filter can
  handle.
- Headphones are the fastest user mitigation because headphone playback does not
  leak into the microphone.
- Production AEC needs a far-end reference, near-end capture, delay estimation,
  double-talk handling, residual echo suppression, and careful routing so the
  reference matches what is actually played.

Clean-room implication for 2brain Rec:

- We should copy no Krisp proprietary details.
- The product requirement is category-level: local virtual devices, physical
  device selection, no virtual self-routing, local processing, clean mic path,
  and dual-track truth.
- Implementation should later evaluate platform AEC, WebRTC AEC3, or another
  licensed/offline echo-control component only through a planning gate.

## Recommended Problem Framing

This feature should be treated as three related gates:

1. **Live route gate**: remote audio must not be sent back through
   `2brain Rec Microphone` during calls.
2. **Recording cleanliness gate**: `mic.wav` must not be marked clean if it
   contains remote speaker leakage above threshold.
3. **Timeline/reference gate**: `mic.wav` and `incoming.wav` must be aligned
   enough to support leakage measurement and future MediaScribe dual-track
   transcription.

## Open Planning Questions

These should be resolved during `$speckit-clarify` and `$speckit-plan`:

- What exact leakage threshold is accepted for MVP: ERLE dB, correlation,
  intelligibility proxy, ASR duplicate-speaker detection, or a combined gate?
- Is the first accepted mitigation route-gating and truthful degradation only,
  or must it include active AEC before broader recording acceptance?
- Which routes are required for MVP acceptance: built-in speaker/mic, wired
  headphones, USB headset, Bluetooth/AirPods, aggregate/multi-output?
- Should app-side local recording source for `mic.wav` use the same cleaned
  virtual mic path that meeting apps receive, or a separate physical capture
  path plus post-processing?
- How will controlled stimuli be generated without storing meeting content in
  diagnostics?

## Source Links

- Krisp Help: <https://help.krisp.ai/hc/en-us/articles/4402174576402-How-Krisp-Microphone-and-Krisp-Speaker-work>
- Krisp AEC article: <https://krisp.ai/blog/acoustic-echo-cancellation/>
- rtcStats AEC note: <https://www.rtcstats.com/kb/observation-aecdisabled>
- Microsoft echo troubleshooting: <https://learn.microsoft.com/en-us/azure/communication-services/resources/troubleshooting/voice-video-calling/audio-issues/echo-issue>
- Switchboard AEC3 explainer: <https://switchboard.audio/hub/how-webrtc-aec3-works/>
