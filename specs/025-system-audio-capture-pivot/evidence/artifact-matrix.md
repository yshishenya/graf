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
- Safe checks: required rows present; `incoming.wav` remains `remoteSpeaker` with `systemAudio` metadata; blocked/degraded/not-tested rows are not counted as acceptance.
