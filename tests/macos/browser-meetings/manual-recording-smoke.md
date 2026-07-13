# Current Manual Recording Smoke Matrix

Feature: `102-remove-legacy-audio-driver`

## Scope

Validate the supported desktop recording graph: the app captures incoming
system audio through ScreenCaptureKit, captures the selected physical
microphone through the app-owned microphone source, and writes the two original
tracks through `LocalRecordingWriter`.

## Required Setup

- Microphone and Screen & System Audio permissions are granted to GRAF.
- A supported physical microphone is selected in GRAF.
- The user approves the intended display, window, or application capture scope.
- The user presses Record manually.
- Active recording remains visibly indicated and exposes one-action Stop.
- The user presses Stop manually.

## Target Matrix

| Target | Status after architecture cleanup | Required evidence |
|---|---|---|
| Yandex Telemost | Pending current-path revalidation | Manual start, visible indicator, one-action stop, `mic.wav`, `incoming.wav`, manifest |
| Chrome meeting | Pending current-path revalidation | Same current-path evidence |
| Opera meeting | Pending current-path revalidation | Same current-path evidence |
| Zoom | Pending current-path revalidation | Same current-path evidence |

Evidence from a superseded recording architecture is historical and does not
count as current-path acceptance.

## Pass Criteria

- Recording starts only after both current permissions and scope approval pass.
- `mic.wav` is sourced from the app-owned microphone source.
- `incoming.wav` is sourced from ScreenCaptureKit system audio.
- Both tracks are non-empty, aligned, and represented truthfully in the current
  manifest.
- The visible recording state and one-action Stop remain available throughout
  active capture.
- No upload, transcription, MediaScribe, Langfuse, or dashboard activity starts
  as a side effect of this smoke.
- Evidence remains metadata-only and contains no raw audio, transcript text,
  meeting content, credentials, tokens, signed URLs, passwords, or live paths.
