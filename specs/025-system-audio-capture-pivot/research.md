# Research: System Audio Capture Pivot

## Decision: Use ScreenCaptureKit For Incoming/System Audio

Use ScreenCaptureKit `SCStream` for incoming/system audio. Configure the stream
with audio capture enabled and attach an audio output that receives
`CMSampleBuffer` audio frames. The MVP should not use HAL virtual-device
publication or HAL runtime probes for acceptance.

**Rationale**: Apple documents ScreenCaptureKit as the macOS framework for
capturing screen content and related audio sample buffers. The
`SCStreamConfiguration.capturesAudio` property controls audio capture, and
ScreenCaptureKit provides native content selection concepts that fit the
clarified app/window/display scope requirement.

**Primary sources**:

- Apple ScreenCaptureKit overview:
  <https://developer.apple.com/documentation/screencapturekit>
- Apple `SCStreamConfiguration.capturesAudio`:
  <https://developer.apple.com/documentation/screencapturekit/scstreamconfiguration/capturesaudio>
- Apple "Capturing screen content in macOS" sample:
  <https://developer.apple.com/documentation/screencapturekit/capturing-screen-content-in-macos>

**Alternatives considered**:

- Continue HAL virtual speaker capture: rejected for MVP because `019`
  validation showed CoreAudio CPU runaway/probe-hang risk.
- Use third-party virtual audio drivers: rejected because it reintroduces the
  driver dependency this pivot removes.
- Use only microphone capture: rejected because dual-track incoming audio is an
  MVP product requirement.

## Decision: Capture Microphone Through A Separate AVFoundation Path

Use a separate microphone capture path based on AVFoundation authorization and
recording/capture APIs. Keep microphone frames and incoming/system frames as
separate sources that feed the dual-track writer.

**Rationale**: Apple requires explicit user permission for microphone access.
Separate microphone capture keeps local speaker audio isolated from incoming
audio, avoids ambiguity in ScreenCaptureKit combined audio behavior, and keeps
the dual-track manifest truthful.

**Primary sources**:

- Apple "Requesting authorization to capture and save media":
  <https://developer.apple.com/documentation/avfoundation/requesting-authorization-to-capture-and-save-media>
- Apple `AVCaptureDevice.requestAccess(for:completionHandler:)`:
  <https://developer.apple.com/documentation/avfoundation/avcapturedevice/requestaccess%28for%3Acompletionhandler%3A%29>

**Alternatives considered**:

- Capture microphone through ScreenCaptureKit together with system audio:
  rejected for the first MVP pivot because it weakens source separation and
  complicates manifest truth.
- Keep existing `AVAudioRecorder` only and read incoming from shared memory:
  rejected because shared memory currently depends on the driver route.

## Decision: Require User-Selected Or User-Confirmed Capture Scope

The MVP must require a user-selected or user-confirmed app/window/display scope
before a recording can be accepted as a meeting recording.

**Rationale**: System audio can contain music, videos, alerts, and unrelated
apps. A scope approval record prevents arbitrary background audio from becoming
a recording trigger or being mislabeled as meeting audio.

**Alternatives considered**:

- Capture all system audio by default: rejected because it violates the
  clarified scope and increases privacy risk.
- Infer the meeting app silently: deferred to a later assisted auto-start
  feature.

## Decision: Keep Existing Local Dual-Track Artifact Shape

Continue producing `manifest.json`, `mic.wav`, and `incoming.wav`. Extend
manifest metadata for capture scope, permission state, system-audio health,
frame evidence, CPU evidence, and no-HAL dependency.

**Rationale**: Existing feature `010-recording-artifact-format` and server
ingest assumptions already align around `mic.wav` and `incoming.wav`. Keeping
the artifact shape reduces downstream churn while allowing truthful degraded
states for system-audio capture.

**Alternatives considered**:

- Create a new package format: rejected because it would unnecessarily churn
  backend/MediaScribe readiness.
- Store a mixed single audio file: rejected because dual-track truth is a core
  MVP requirement.

## Decision: Add CPU And No-HAL Evidence As Release Gates

Validation must collect idle, active, stop, and quit CPU evidence and must prove
that no HAL virtual-device probes are required for MVP acceptance.

**Rationale**: The pivot exists because the driver path overheated/froze the
audio stack. Runtime stability must be a release gate, not a later observation.

**Alternatives considered**:

- Trust short smoke tests: rejected because `019` proved short smoke evidence is
  too weak.
- Keep running HAL probes as a compatibility check: rejected because probes
  themselves contributed to unsafe validation behavior.
