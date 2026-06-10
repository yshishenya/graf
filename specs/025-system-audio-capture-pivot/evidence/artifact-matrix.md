# Artifact Matrix

Feature: `025-system-audio-capture-pivot`

This matrix is metadata-only. Do not paste raw audio, transcripts, meeting
content, credentials, tokens, signed URLs, or personal contact details.

| Case | Expected Outcome | Required Files | Required Manifest Evidence | Result | Notes |
| --- | --- | --- | --- | --- | --- |
| Both microphone and system audio present | `saved` | `manifest.json`, `mic.wav`, `incoming.wav` | `local_mic` source `microphone`; `remote_speaker` source `systemAudio`; `externalEgressStarted=false`; `transcriptionStarted=false`; `durationDifferenceSeconds <= 3` | not-tested | Manual controlled run pending |
| Microphone present, incoming/system audio silent | `degraded` or `blocked` | `manifest.json`, `mic.wav`, optional `incoming.wav` | incoming track reason `silent_input` or `no_frames` | not-tested | Manual controlled run pending |
| Incoming/system audio present, microphone missing | `blocked` or `degraded` | `manifest.json`, optional `mic.wav`, `incoming.wav` | microphone permission/failure reason present | not-tested | Manual controlled run pending |
| Protected or blocked incoming/system audio | `blocked` or `degraded` | `manifest.json` plus any safe local files | incoming track reason `protected_audio_blocked` | not-tested | Manual controlled run pending |
| Misaligned tracks | `degraded` | `manifest.json`, `mic.wav`, `incoming.wav` | `timeline_misaligned`; not counted as acceptance | not-tested | Manual controlled run pending |

## Automated Coverage

- `SystemAudioManifestContractTests`: saved/aligned manifest, `remote_speaker`
  incoming role, `systemAudio` source metadata, scope/permission/CPU evidence,
  and `durationDifferenceSeconds`.
- `SystemAudioManifestFailureReasonTests`: missing/no-frames incoming audio,
  silent incoming audio, protected/blocked incoming audio, and dropped/degraded
  incoming audio.
- `SystemAudioTrackAlignmentTests`: alignment pass at `<= 3` seconds and failure
  above 3 seconds.

Blocked, failed, degraded, and not-tested rows are not acceptance.

## Manual Controlled Run Procedure

Use the guided metadata-only harness when possible:

```sh
apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh
```

The harness does not click the UI, does not start recording by itself, does not
inspect audio content, does not install the package, and does not run HAL
probes. It reduces manual sequencing mistakes by running the app-only installer
gate, baseline CPU, activeRecording CPU, stop CPU, and latest artifact
validation around the tester's manual Record/Stop actions.

Manual equivalent:

1. Run `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline` before
   launching the packaged app.
2. Record the current manual gate start epoch before building or launching, so
   the latest-artifact validator ignores older completed recordings:
   `export SYSTEM_AUDIO_CAPTURE_PIVOT_MIN_ARTIFACT_MTIME="$(date +%s)"`.
3. Build and launch the packaged app from the repository:
   `TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh`
   and `open -n "apps/macos/RecApp/.build/2brain Rec.app"`.
4. Use a controlled, non-sensitive audio source.
5. Press `Record System Audio`.
6. While recording is active, run
   `apps/macos/Scripts/sample-system-audio-cpu-gate.sh activeRecording`.
7. Press Stop, then run `apps/macos/Scripts/sample-system-audio-cpu-gate.sh stop`.
8. Inspect the newest completed local recording directory with
   `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --latest-artifact-directory`.
9. Run
   `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --validate-latest-artifact`
   to validate that directory metadata-only. To pin a specific directory, use
   `--artifact-directory "$HOME/Library/Application Support/2brain Rec/Recordings/<directory-id>"`.
10. Record only metadata: file presence, manifest status, track roles/source
   kinds, duration difference, permissions, CPU gate result, and failure reasons.
   Do not paste raw audio or meeting content here.

## 2026-06-08 Metadata Validator Run

- Run ID: `20260608T174858Z`
- Timestamp: `2026-06-08T17:48:58Z`
- Commit: `967c381`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--artifact-matrix`
- Validator result: `blocked`
- Reason: Controlled meeting/audio artifact rows are still required before acceptance.
- Safe checks: required rows present; `incoming.wav` remains `remote_speaker` with `systemAudio` metadata; blocked/degraded/not-tested rows are not counted as acceptance.

## 2026-06-08 Metadata Validator Run

- Run ID: `20260608T230809Z`
- Timestamp: `2026-06-08T23:08:09Z`
- Commit: `f7a7454`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--artifact-matrix`
- Validator result: `blocked`
- Reason: Controlled meeting/audio artifact rows are still required before acceptance.
- Safe checks: required rows present; `incoming.wav` remains `remote_speaker` with `systemAudio` metadata; blocked/degraded/not-tested rows are not counted as acceptance.

## Metadata Validator Run

- Run ID: `20260609T012803Z`
- Timestamp: `2026-06-09T01:28:03Z`
- Commit: `6395360`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--artifact-matrix`
- Validator result: `blocked`
- Reason: Controlled meeting/audio artifact rows are still required before acceptance.
- Safe checks: required rows present; `incoming.wav` remains `remote_speaker` with `systemAudio` metadata; blocked/degraded/not-tested rows are not counted as acceptance.

## Metadata Validator Run

- Run ID: `20260609T043348Z`
- Timestamp: `2026-06-09T04:33:48Z`
- Commit: `716f3be`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--artifact-matrix`
- Validator result: `blocked`
- Reason: Controlled meeting/audio artifact rows are still required before acceptance.
- Safe checks: required rows present; `incoming.wav` remains `remote_speaker` with `systemAudio` metadata; blocked/degraded/not-tested rows are not counted as acceptance.

## Metadata Validator Run

- Run ID: `20260609T052529Z`
- Timestamp: `2026-06-09T05:25:29Z`
- Commit: `62616bb`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--artifact-matrix`
- Validator result: `blocked`
- Reason: Controlled meeting/audio artifact rows are still required before acceptance.
- Safe checks: required rows present; `incoming.wav` remains `remote_speaker` with `systemAudio` metadata; blocked/degraded/not-tested rows are not counted as acceptance.

## Artifact Directory Validator Run

- Run ID: `20260610T093356Z`
- Timestamp: `2026-06-10T09:33:56Z`
- Commit: `c09e9f6`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--validate-latest-artifact`
- Directory ID: `20260610-093247-F2645A5B-6479-4E7F-AE32-34870B5AFAAE`
- Manifest status: `saved`
- Duration difference seconds: `0`
- Validator result: `blocked`
- Reason: artifact directory did not satisfy accepted controlled-recording metadata.
- Findings:
  - manifest must contain exactly one numeric durationMs for local_mic and remote_speaker
  - durationDifferenceSeconds must equal the absolute mic/incoming duration difference and be <= 3
  - tracks must contain local_mic and remote_speaker
  - local_mic track must be saved microphone wav-pcm-s16le metadata
  - remote_speaker track must be saved systemAudio wav-pcm-s16le metadata
  - mic.wav manifest byteCount must be an unsigned integer
  - incoming.wav manifest byteCount must be an unsigned integer

## Artifact Directory Validator Run

- Run ID: `20260610T093510Z`
- Timestamp: `2026-06-10T09:35:10Z`
- Commit: `c09e9f6`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--validate-latest-artifact`
- Directory ID: `20260610-093247-F2645A5B-6479-4E7F-AE32-34870B5AFAAE`
- Manifest status: `saved`
- Duration difference seconds: `0`
- Validator result: `blocked`
- Reason: artifact directory did not satisfy accepted controlled-recording metadata.
- Findings:
  - mic.wav WAV header must contain fmt chunk
  - mic.wav WAV header must contain data chunk at byte 36
  - mic.wav WAV audio format must be PCM
  - mic.wav WAV sampleRate must equal manifest sampleRate
  - mic.wav WAV channelCount must equal manifest channelCount
  - mic.wav WAV bitsPerSample must equal manifest bitsPerSample
  - mic.wav WAV blockAlign must match manifest format
  - mic.wav WAV byteRate must match manifest format
  - mic.wav WAV RIFF byte count must match file size
  - mic.wav WAV fmt chunk size must be 16 for PCM
  - mic.wav WAV data byte count must match manifest frameCount
  - mic.wav file size must equal 44-byte header plus manifest data bytes

## Artifact Directory Validator Run

- Run ID: `20260610T093609Z`
- Timestamp: `2026-06-10T09:36:09Z`
- Commit: `c09e9f6`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--validate-latest-artifact`
- Directory ID: `20260610-093247-F2645A5B-6479-4E7F-AE32-34870B5AFAAE`
- Manifest status: `saved`
- Duration difference seconds: `0`
- Validator result: `blocked`
- Reason: artifact directory did not satisfy accepted controlled-recording metadata.
- Findings:
  - mic.wav WAV RIFF byte count must match file size
  - mic.wav WAV data byte count must match manifest frameCount
  - mic.wav file size must equal WAV data chunk end
