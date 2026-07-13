# Recording Artifact Format Smoke Matrix

Feature baseline: `010-recording-artifact-format`; current architecture:
`102-remove-legacy-audio-driver`.

## Scope

Confirm that a current manual recording produces a MediaScribe-ready,
metadata-safe dual-track local package. This smoke does not upload content or
accept transcription, dashboard, retention, deletion, or assisted auto-start.

## Required Setup

- Build and launch the current `GRAF.app`.
- Grant microphone and Screen & System Audio Recording permissions.
- Select an eligible physical microphone.
- Use a controlled meeting/system-audio source.
- Press `Record`, observe the persistent indicator, then press `Stop`.

## Local Artifact Checks

| Artifact | Required evidence |
|---|---|
| `manifest.json` | Valid metadata-only JSON; `schemaVersion=local-recording-manifest.v3`; maps `local_mic` to `mic_file` and `remote_speaker` to `incoming_file`; reports truthful status/readiness |
| `mic.wav` | Exists and is non-empty; PCM signed 16-bit little-endian, mono, 16 kHz |
| `incoming.wav` | Exists and is non-empty; PCM signed 16-bit little-endian, mono, 16 kHz |

Also verify:

- both original tracks are timeline-aligned or the manifest is degraded;
- current manifests contain no retired routing lifecycle fields;
- no upload, MediaScribe request, Langfuse trace, or external publication starts;
- the saved path contains no committed private content or secrets.

## Target Matrix

| Target | Cleanup-slice status |
|---|---|
| Yandex Telemost | Fresh current-build smoke required |
| Chrome | Fresh current-build smoke required |
| Opera | Fresh current-build smoke required |
| Zoom | Best-effort; fresh current-build smoke required |
| Yandex Browser | Not accepted until explicitly run |

Previous manual results are historical carry-forward context only. They do not
prove the post-cleanup executable.
