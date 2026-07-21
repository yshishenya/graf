# Manual Validation Template

Use this template for each manual QA run.

## Run Metadata

- Date:
- App build:
- macOS version:
- Target:
- Fixture or artifact directory:

## Steps

1. Start a local system-audio recording.
2. Confirm visible active indicator and one-action Stop.
3. Use 2brain Pause.
4. Confirm visible paused indicator and one-action Stop.
5. Resume.
6. Stop.
7. Run `apps/macos/Scripts/validate-meeting-mute-truth.sh --latest-artifact-directory <artifact-dir>`.

## Expected Result

- `privacySegments` contains the pause interval.
- `meetingMuteTruth.decision` is `meeting_mute_unproven`, `unsupported`, `degraded`, or `failed`; never `mute_respecting`.
- `targetMuteCapability.firstMatrixStatus` is explicit.
- No raw audio, transcript, meeting content, credentials, signed URLs, or participant speech appear in diagnostics.

## Run: 2026-06-16 `/Applications` Desktop Runtime

## Run Metadata

- Date: 2026-06-16
- App build: `/Applications/2brain Rec.app` (`pro.2brain.rec`, `0.1.0`)
- macOS version: local QA machine, Europe/Moscow session
- Target: unknown/no active meeting app audio source
- Fixture or artifact directory: `<local-recordings-dir>/<session-id>`

## Steps

1. Started a local system-audio recording from `/Applications/2brain Rec.app`.
2. Confirmed visible active indicator, active meters, Pause, and one-action Stop.
3. Used 2brain Pause.
4. Confirmed visible paused indicator and Stop remained available.
5. Resumed recording.
6. Stopped recording.
7. Ran `apps/macos/Scripts/validate-meeting-mute-truth.sh --latest-artifact-directory`.

## Result

- PASS: latest artifact validation returned OK for the manual desktop recording.
- PASS: `privacySegments` contains one Pause interval.
- PASS: `meetingMuteTruth.decision` is `unsupported`, not `mute_respecting`.
- PASS: Pause segment has `localMicTreatment=redacted`.
- PASS: Stop remained available during Pause.
- NOTE: `remote_speaker` is degraded with `silent_input`, expected for this local QA pass without an active meeting audio source.
