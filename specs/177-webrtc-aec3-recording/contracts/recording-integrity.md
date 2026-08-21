# Contract: Recording Integrity And Package Surface

## Normal package

A normal new recording is publishable only when:

- every emitted microphone frame was successfully processed by the pinned AEC3;
- health state is `completed` with no failure reason or process error;
- the system component was not processed or gain-adjusted by AEC;
- the package has one `meeting-transcription.wav`, one `meeting-review.m4a` and
  one manifest;
- the existing canonical timeline and `canonical-mix.v1` conditions pass;
- no raw microphone or render-reference artifact exists.

## Failure package

If AEC/reference integrity fails after start:

1. Stop accepting or emitting new timeline frames.
2. Do not invoke a salvage path that can reprocess queued raw microphone data.
3. Finalize only the already-written, successfully cleaned prefix when non-empty.
4. Persist an explicit degraded/failed manifest with a bounded reason.
5. Do not enqueue it as transcription-ready or upload-ready.
6. Keep Pause/Resume state truthful and preserve one-action Stop.

Failure before the first cleaned frame creates no normal audio artifact.

## Route/source truth

Mic and system producers publish monotonic route generations and terminal
runtime failures. A route generation change, device disconnect, ScreenCaptureKit
stop error or AVFoundation runtime error is not normalized to silence and is
not hidden from the recording controller.

## Diagnostics

Allowed: dependency version/commit, bounded state/reason, counts, timing
summaries, delay/ERL/ERLE and route class/generation.

Forbidden: raw frames, debug audio files, WebRTC AecDump, transcript text,
participant/title content, credentials, private paths and unbounded native logs.

## Compatibility

- Optional AEC fields do not change manifest schema version.
- Historical v3/v4 packages and pre-feature v5 packages remain decodable.
- Historical readers do not start legacy capture runtime.
- Removed Features 038/039/106 runtime, drivers and fallback selectors remain
  absent.

## Distribution

The final app statically includes the vendored archive and required notices.
No WebRTC or Abseil dylib/framework may be embedded or loaded. The normal
Developer ID, hardened runtime, notarization, stapling, Gatekeeper and Sparkle
release gates remain mandatory for publication.
