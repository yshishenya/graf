# Quickstart: System Audio Capture Pivot

## Prerequisites

- macOS 14+ on Apple Silicon.
- Full Xcode installed for XCTest execution, or record the local limitation if
  only Command Line Tools are available.
- Microphone permission grant/revoke access.
- Screen/System Audio permission grant/revoke access.
- A controlled meeting/audio source for incoming/system audio.
- Current branch: `025-system-audio-capture-pivot`.

## 1. Static Spec And Contract Checks

```sh
rg -n "NEEDS CLARIFICATION|020-system-audio-capture-pivot|022-system-audio-capture-pivot" \
  specs/025-system-audio-capture-pivot AGENTS.md docs .specify/memory/constitution.md

rg -n "rawAudio|transcriptText|meetingContent|signedUrl|password|apiKey" \
  specs/025-system-audio-capture-pivot apps/macos/Shared/Sources apps/macos/RecApp/Sources
```

Expected:

- no unresolved clarification markers;
- no stale pivot feature number references;
- no diagnostics contract allowing raw content or secrets.

## 2. Swift Build And Tests

```sh
cd apps/macos
swift build
swift test
swift run ContractValidation
```

Expected:

- build succeeds;
- tests run or the local XCTest/toolchain limitation is recorded;
- contract validation passes.

## 3. No-HAL MVP Gate

```sh
cd apps/macos
./Scripts/validate-system-audio-no-hal-probe.sh
```

Expected:

- no HAL runtime probe is executed;
- MVP recording validation does not require virtual device selection;
- driver absent/ignored state is reported as acceptable for system-audio MVP.

## 4. Permission Matrix

Run the app and validate:

1. microphone granted + Screen/System Audio granted;
2. microphone denied + Screen/System Audio granted;
3. microphone granted + Screen/System Audio denied;
4. both denied;
5. permission revoked during recording.

Expected:

- normal accepted recording starts only when both permissions are granted;
- missing permissions block before false success;
- explicit degraded attempts are labelled before start and in `manifest.json`;
- recovery actions are specific and do not mention driver reinstall.

Record each row in `evidence/permission-matrix.md`. Do not reset TCC from a
script and do not paste user-specific meeting names, raw audio, transcripts, or
screen contents into evidence. Use System Settings to grant/revoke permissions
manually, then relaunch the packaged app and press Record only for the row being
tested.

## 5. Controlled Recording Artifact

Start a controlled meeting/audio source, select or confirm the capture scope,
press Record, produce local microphone audio and incoming/system audio, then
press Stop.

Recommended manual run sequence:

1. Confirm `apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline` reports
   the current `coreaudiod` baseline before launching the app.
2. Build and launch the packaged app:

   ```sh
   TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh
   open -n "apps/macos/RecApp/.build/2brain Rec.app"
   ```

3. Start a controlled audio source with non-sensitive synthetic or generic audio.
4. Press `Record System Audio` in the app and confirm macOS permission prompts
   only when they appear naturally.
5. While recording is active, run:

   ```sh
   apps/macos/Scripts/sample-system-audio-cpu-gate.sh activeRecording
   ```

6. Press Stop in the app.
7. Immediately run:

   ```sh
   apps/macos/Scripts/sample-system-audio-cpu-gate.sh stop
   ```

8. Inspect the newest completed local recording directory:

   ```sh
   apps/macos/Scripts/validate-system-audio-capture-pivot.sh \
     --latest-artifact-directory
   ```

9. Validate the newest completed directory metadata-only:

   ```sh
   apps/macos/Scripts/validate-system-audio-capture-pivot.sh \
     --validate-latest-artifact
   ```

10. Record only metadata in `evidence/artifact-matrix.md`: status, file presence,
   track roles/source kinds, duration difference, permission states, and failure
   reasons. Do not copy raw audio or private meeting content into evidence.

Expected package:

```text
manifest.json
mic.wav
incoming.wav
```

To validate a specific directory instead of the newest completed one, run:

```sh
apps/macos/Scripts/validate-system-audio-capture-pivot.sh \
  --artifact-directory "$HOME/Library/Application Support/2brain Rec/Recordings/<directory-id>"
```

Expected manifest:

- `status=saved` only when both tracks are present and aligned;
- `durationDifferenceSeconds <= 3`;
- scope approval is present;
- permissions are granted;
- external egress and transcription are false;
- diagnostics are metadata-only.

## 6. Silent, Protected, And Blocked Incoming Audio

Run controlled cases where incoming/system audio is silent, protected, blocked,
or missing.

Expected:

- no false `saved` status;
- incoming track is `degraded`, `blocked`, or `missing`;
- failure reason is specific;
- UI shows truthful state.

## 7. CPU And Responsiveness Gates

```sh
cd apps/macos
./Scripts/sample-system-audio-cpu-gate.sh baseline
./Scripts/sample-system-audio-cpu-gate.sh idle
./Scripts/sample-system-audio-cpu-gate.sh activeRecording
./Scripts/sample-system-audio-cpu-gate.sh stop
./Scripts/sample-system-audio-cpu-gate.sh quit
```

Expected:

- idle after 10 seconds: `coreaudiod < 5%`, app `< 5%`;
- active recording: no sustained `coreaudiod > 10%`;
- active recording: no sustained app/helper total `> 25%`;
- stop/quit returns below idle gate within 10 seconds;
- app and meeting target remain responsive.

The `baseline` phase is diagnostic-only and does not count as acceptance. It is
used to separate pre-existing `coreaudiod` load from app-caused load. The
accepted phases remain `idle`, `activeRecording`, `stop`, and `quit`.

For CPU gates, `sustained` means at least three consecutive samples above the
threshold at 2-second sampling intervals after the relevant settle window.

## 8. Duration Gates

```sh
cd apps/macos
./Scripts/validate-system-audio-capture-pivot.sh --duration-minutes 30
./Scripts/validate-system-audio-capture-pivot.sh --duration-minutes 75 --manual-release
```

Expected:

- 30-minute development run passes before release run;
- 75-minute manual release run passes before acceptance;
- blocked, failed, degraded, or not-tested rows are not counted as accepted.

## Evidence

Record results under:

```text
specs/025-system-audio-capture-pivot/evidence/
```

Evidence must remain metadata-only.
