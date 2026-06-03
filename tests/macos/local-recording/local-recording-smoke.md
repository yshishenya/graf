# Local Recording Smoke Matrix

Feature: `008-local-recording-persistence`

## Scope

This matrix records metadata-only evidence that a manual recording produces
local artifacts after `Stop`. It does not validate upload, MediaScribe,
Langfuse, dashboard notes, retention, deletion, encryption, or assisted
auto-start.

## Required Setup

- Fresh app bundle built from `008-local-recording-persistence`.
- `2brain Rec Microphone` selected as meeting microphone.
- `2brain Rec Speaker` selected as meeting speaker.
- Low-resource non-recording passthrough route is valid.
- User presses `Record` manually.
- User presses `Stop` manually.

## Local Artifact Checks

| Artifact | Current 008 Status | Required Evidence |
|---|---|---|
| `manifest.json` | User-confirmed local recording exists after `Record`/`Stop`; metadata contract accepted | Exists, valid JSON, metadata-only, no external egress |
| `local-mic.wav` | User-confirmed local recording exists after `Record`/`Stop` | Exists and non-empty when mic frames are available |
| `remote-speaker.wav` | Truthful saved/degraded status required per manifest | Exists and non-empty when remote speaker frames are available |

## Target Matrix

| Target | Current 008 Status | Required Evidence |
|---|---|---|
| Yandex Telemost | Passed 1-minute local recording persistence smoke on 2026-06-02 | Saved location, manifest, local mic track, remote speaker track or truthful degraded status |
| Chrome | Passed 1-minute local recording persistence smoke on 2026-06-02 | Saved location, manifest, local mic track, remote speaker track or truthful degraded status |
| Opera | Passed 1-minute local recording persistence smoke on 2026-06-02 | Saved location, manifest, local mic track, remote speaker track or truthful degraded status |
| Zoom | Passed 1-minute local recording persistence smoke on 2026-06-02 | Saved location, manifest, local mic track, remote speaker track or truthful degraded status |

## Manual Evidence Log

- 2026-06-02 01:19 MSK: User confirmed that pressing `Record` and then `Stop`
  produced a local recording in the freshly rebuilt `008` app. Treat this as
  accepted local artifact presence smoke only; target-specific meeting smoke
  remains pending.
- 2026-06-02 01:52 MSK: User recorded and checked a 1-minute local recording;
  the recording saves successfully. Treat this as accepted 1-minute local
  artifact persistence smoke. Target-specific meeting smoke remains pending
  until recorded per Telemost, Chrome, Opera, and Zoom.
- 2026-06-02 02:02 MSK: User confirmed the 1-minute recording save check across
  Yandex Telemost, Chrome, Opera, and Zoom. Treat this as accepted target local
  recording persistence smoke for feature `008`. This does not accept upload,
  transcription, MediaScribe, Langfuse, dashboard publication, retention,
  deletion, long-duration recording, or meeting-app mute truth.

Evidence must remain metadata-only and must not include raw audio, transcript
text, meeting content, credentials, tokens, signed URLs, passwords, or live
secret paths.
