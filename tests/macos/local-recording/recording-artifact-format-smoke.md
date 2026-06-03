# Recording Artifact Format Smoke Matrix

Feature: `010-recording-artifact-format`

## Scope

This matrix records metadata-only evidence that a manual recording produces a
MediaScribe-ready dual-track local artifact package. It does not validate
upload, MediaScribe job submission, polling, result import, dashboard notes,
retention, deletion, encryption, or assisted auto-start.

## Required Setup

- Fresh app bundle built from `010-recording-artifact-format`.
- `2brain Rec Microphone` selected as meeting microphone.
- `2brain Rec Speaker` selected as meeting speaker.
- Low-resource non-recording passthrough route is valid.
- User presses `Record` manually.
- User presses `Stop` manually.

## Local Artifact Checks

| Artifact | Current 010 Status | Required Evidence |
|---|---|---|
| `manifest.json` | Passed | Exists, valid JSON, metadata-only, maps `local_mic` to `mic_file` and `remote_speaker` to `incoming_file`; `schemaVersion=local-recording-manifest.v2`, `status=saved`, `transcriptionReadiness=ready`, `mediaScribeSourceMode=dual` |
| `mic.wav` | Passed | Exists, WAV PCM signed 16-bit little-endian, mono, 16000 Hz |
| `incoming.wav` | Passed | Exists, WAV PCM signed 16-bit little-endian, mono, 16000 Hz |

## Optional Target Matrix

The 010 acceptance gate is the local artifact package contract after manual
`Record`/`Stop`, not per-browser meeting support. Browser-specific recording
smoke remains useful as carry-forward evidence, but pending rows below do not
block the accepted 010 local artifact-format status.

| Target | Current 010 Status | Required Evidence |
|---|---|---|
| Yandex Telemost | Pending | Saved location, manifest, `mic.wav`, `incoming.wav`, readiness or truthful degraded status |
| Chrome | Pending | Saved location, manifest, `mic.wav`, `incoming.wav`, readiness or truthful degraded status |
| Opera | Pending | Saved location, manifest, `mic.wav`, `incoming.wav`, readiness or truthful degraded status |
| Zoom | Pending | Saved location, manifest, `mic.wav`, `incoming.wav`, readiness or truthful degraded status |
| Yandex Browser | Not accepted in current cycle | Run only if explicitly added back to smoke scope |

## Manual Evidence Log

Evidence must remain metadata-only and must not include raw audio, transcript
text, meeting content, credentials, tokens, signed URLs, passwords, full
MediaScribe keys, or live secret paths.

### 2026-06-04 MSK - Fresh Workspace Bundle Smoke

- App bundle: fresh workspace build at `apps/macos/RecApp/.build/2brain Rec.app`.
- Observed UI state: after restart, `Record` appeared; during active capture,
  the capture row showed `Recording active` and the one-action `Stop` button.
- Post-stop UI expectation: after `Stop`, the saved package path remains visible
  and the `Record` button is available again for the next manual capture.
- Route status: `Ready for audio routing`; readiness check passed for microphone
  and speaker route.
- Saved package directory ID:
  `20260603-221149-0148659F-0741-45D0-B631-C8EE79D8D729`.
- Saved files: `manifest.json`, `mic.wav`, `incoming.wav`.
- Header checks: `incoming.wav` reported as RIFF/WAVE Microsoft PCM, 16-bit,
  mono, 16000 Hz; manifest reports both tracks as `wav-pcm-s16le`, 16000 Hz,
  one channel, 16 bits per sample.
- Manifest mapping: `local_mic` maps to `mic_file`; `remote_speaker` maps to
  `incoming_file`.
- Readiness: `transcriptionReadiness=ready`,
  `mediaScribeSourceMode=dual`, both tracks `timelineStartMs=0`,
  `timelineAligned=true`, `status=saved`.
- Egress: no upload, MediaScribe request, Langfuse trace, or external publication
  was performed.
