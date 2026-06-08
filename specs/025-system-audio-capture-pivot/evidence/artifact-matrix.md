# Artifact Matrix

Feature: `025-system-audio-capture-pivot`

This matrix is metadata-only. Do not paste raw audio, transcripts, meeting
content, credentials, tokens, signed URLs, or personal contact details.

| Case | Expected Outcome | Required Files | Required Manifest Evidence | Result | Notes |
| --- | --- | --- | --- | --- | --- |
| Both microphone and system audio present | `saved` | `manifest.json`, `mic.wav`, `incoming.wav` | `localMic` source `microphone`; `remoteSpeaker` source `systemAudio`; `externalEgressStarted=false`; `transcriptionStarted=false`; `durationDifferenceSeconds <= 3` | not-tested | Manual controlled run pending |
| Microphone present, incoming/system audio silent | `degraded` or `blocked` | `manifest.json`, `mic.wav`, optional `incoming.wav` | incoming track reason `silent_input` or `no_frames` | not-tested | Manual controlled run pending |
| Incoming/system audio present, microphone missing | `blocked` or `degraded` | `manifest.json`, optional `mic.wav`, `incoming.wav` | microphone permission/failure reason present | not-tested | Manual controlled run pending |
| Protected or blocked incoming/system audio | `blocked` or `degraded` | `manifest.json` plus any safe local files | incoming track reason `protected_audio_blocked` | not-tested | Manual controlled run pending |
| Misaligned tracks | `degraded` | `manifest.json`, `mic.wav`, `incoming.wav` | `timeline_misaligned`; not counted as acceptance | not-tested | Manual controlled run pending |

## Automated Coverage

- `SystemAudioManifestContractTests`: saved/aligned manifest, `remoteSpeaker`
  incoming role, `systemAudio` source metadata, scope/permission/CPU evidence,
  and `durationDifferenceSeconds`.
- `SystemAudioManifestFailureReasonTests`: missing/no-frames incoming audio,
  silent incoming audio, protected/blocked incoming audio, and dropped/degraded
  incoming audio.
- `SystemAudioTrackAlignmentTests`: alignment pass at `<= 3` seconds and failure
  above 3 seconds.

Blocked, failed, degraded, and not-tested rows are not acceptance.

## 2026-06-08 Metadata Validator Run

- Run ID: `20260608T174858Z`
- Timestamp: `2026-06-08T17:48:58Z`
- Commit: `967c381`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--artifact-matrix`
- Validator result: `blocked`
- Reason: Controlled meeting/audio artifact rows are still required before acceptance.
- Safe checks: required rows present; `incoming.wav` remains `remoteSpeaker` with `systemAudio` metadata; blocked/degraded/not-tested rows are not counted as acceptance.
