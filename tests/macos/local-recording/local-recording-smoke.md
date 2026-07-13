# Local Recording Smoke Matrix

Feature baseline: `008-local-recording-persistence`; current architecture:
`102-remove-legacy-audio-driver`.

## Scope

Confirm that manual `Record`/`Stop` persists the current app-owned
microphone and system-audio sources locally. This smoke does not validate
upload, MediaScribe, Langfuse, dashboard, retention, deletion, encryption, or
assisted auto-start.

## Required Setup

- Build and launch the current `GRAF.app`.
- Grant microphone and Screen & System Audio Recording permissions.
- Select an eligible physical microphone.
- Start a controlled system-audio source.
- Press `Record`, confirm the persistent local indicator, and press the
  one-action `Stop`.

## Required Evidence

| Artifact/state | Required result |
|---|---|
| `manifest.json` | Exists, metadata-only, and reports truthful saved/degraded/failed state |
| `mic.wav` | Exists and is non-empty when microphone frames are available |
| `incoming.wav` | Exists and is non-empty when system-audio frames are available |
| UI | Indicator remains visible while active; saved location is exposed after stop |
| Egress | No upload or external processing starts from local finalization |

## Target Matrix

| Target | Cleanup-slice status |
|---|---|
| Yandex Telemost | Fresh current-build smoke required |
| Chrome | Fresh current-build smoke required |
| Opera | Fresh current-build smoke required |
| Zoom | Best-effort; fresh current-build smoke required |
| Yandex Browser | Not accepted until explicitly run |

Historical feature-008 smokes remain evidence for that completed slice, but a
fresh smoke is required before the post-cleanup build is called release-ready.

Evidence must not include raw audio, transcript text, meeting content,
credentials, tokens, signed URLs, passwords, or live secret paths.
