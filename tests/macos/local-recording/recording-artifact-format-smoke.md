# Recording Artifact Format Smoke Matrix

Feature baseline: `106-mixed-wav-recording`; current architecture: one
timestamped canonical timeline with one WAV ASR source and one M4A playback
copy.

## Scope

Confirm that a current manual recording produces a MediaScribe-ready,
metadata-safe v5 package. This smoke does not upload content or accept
transcription, dashboard, retention, deletion, or assisted auto-start.

## Required Setup

- Build and launch the current `GRAF.app`.
- Grant microphone and Screen & System Audio Recording permissions.
- Select an eligible physical microphone.
- Use a controlled meeting/system-audio source.
- Press `Record`, observe the persistent indicator, then press `Stop`.

## Local Artifact Checks

| Artifact | Required evidence |
|---|---|
| `manifest.json` | Valid metadata-only JSON; `schemaVersion=local-recording-manifest.v5`; `mediaScribeSourceMode=single_wav_v1`; reports truthful integrity/status/readiness |
| `meeting-transcription.wav` | Exists and is non-empty; PCM signed 16-bit little-endian, mono, 16 kHz; only ASR source |
| `meeting-review.m4a` | Exists and is non-empty; AAC-LC M4A, mono, 48 kHz; playback only |

Also verify:

- exactly these three final members exist; no `mic.wav`, `incoming.wav`, raw
  source or `.partial` file is discoverable;
- the WAV and M4A share the canonical timeline or the manifest is degraded;
- current manifests contain no retired routing lifecycle fields;
- no upload, MediaScribe request, Langfuse trace, or external publication starts;
- the saved path contains no committed private content or secrets.

## Timing and Playback Safety

- Use a non-private signal with markers near the start, middle and end of the
  controlled run; record only timing/count verdicts.
- Verify route is unchanged and incoming playback level differs by no more than
  1 dB while capture is active.
- Do not archive audio, marker text, transcript content, device names or local
  paths as evidence.

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
