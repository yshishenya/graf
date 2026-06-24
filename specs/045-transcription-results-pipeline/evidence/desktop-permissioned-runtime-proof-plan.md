# Desktop Permissioned Runtime Proof Plan

**Feature**: `045-transcription-results-pipeline`
**Date**: 2026-06-24

## Purpose

The current branch proves the desktop UI, embedded cabinet shell, and
system-audio no-permission fail-closed path. It does not yet prove current
branch recording start/stop with granted macOS Screen/System Audio permission.

This plan records the safest path to collect that missing proof after explicit
owner approval.

## Why Approval Is Required

macOS privacy permissions are tied to app identity and code signing state. The
worktree ad-hoc app has a different code hash from the already-installed
`/Applications/2brain Rec.app`, so the installed app's permission does not
prove the worktree app.

Any proof that changes the installed app, prompts for system-audio permission,
or changes macOS privacy state must be explicitly approved before execution.

## Existing Harness

Use the existing metadata-only manual harness:

```sh
apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh
```

The harness:

- launches a chosen app bundle;
- prompts the tester to press Record and Stop manually;
- waits for fresh `recording.started` and stop/local-recording log events;
- samples CPU around baseline/active/stop;
- validates the newest local recording artifact metadata;
- does not click UI by itself;
- does not inspect audio content;
- does not reset TCC;
- does not install the pkg by itself;
- does not run HAL probes.

Preflight status:

- `apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh --self-test`
  passed on 2026-06-24. This only validates harness parser and metadata
  validator behavior; it does not launch the app, record audio, install
  anything, inspect audio content, or touch macOS privacy/TCC state.
- `TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh
  apps/macos/Installer/Scripts/build-local-installer.sh` passed on 2026-06-24
  and rebuilt the current branch app bundle plus local pkg with ad-hoc
  development signing.
- `SYSTEM_AUDIO_MANUAL_GATE_ASSUME_CLEAN_BASELINE=1
  apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh --preflight`
  passed on 2026-06-24. This launched the packaged app, sampled idle and quit
  CPU/resource state, observed no helper process, no unexpected app process, no
  HAL probe, and no thermal/performance warning. Scope was
  `non_recording_only`; it still does not prove Record/Stop, system-audio
  permission, recording artifacts, upload, transcription, or review.

## Recommended Proof Path After Approval

1. Build the current branch app without changing the installed app:

   ```sh
   TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 \
     sh apps/macos/Installer/Scripts/build-local-installer.sh
   ```

2. Launch the exact built app bundle and grant macOS Screen/System Audio
   permission when macOS prompts. If macOS does not prompt, open the macOS
   privacy pane manually and grant the app permission for Screen/System Audio
   recording.

3. Quit and relaunch the exact same built bundle. Do not rebuild between
   granting permission and running the proof, because ad-hoc builds can change
   code identity.

4. Run the harness against that exact app bundle:

   ```sh
   SYSTEM_AUDIO_MANUAL_GATE_APP_BUNDLE="$PWD/apps/macos/RecApp/.build/2brain Rec.app" \
     apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh
   ```

5. During the harness prompts:

   - keep private meetings closed;
   - use controlled non-sensitive audio only;
   - press Record manually in the app;
   - confirm the local recording indicator is active;
   - press Stop manually;
   - let the harness validate metadata-only artifacts.

## Alternate Proof Path After Approval

If macOS will not grant/reuse permission for the worktree app, install the
current branch package over the installed app only after explicit approval:

```sh
TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 \
  sh apps/macos/Installer/Scripts/build-local-installer.sh

sudo installer -pkg apps/macos/.build/installer/2brain-rec-local.pkg -target /

SYSTEM_AUDIO_MANUAL_GATE_APP_BUNDLE="/Applications/2brain Rec.app" \
  apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh
```

This replaces the installed product app, so it is not the default path.

## Evidence Required

Record only metadata-safe facts:

- build command and result;
- app bundle used;
- signing mode;
- fresh `recording.started` log event after the harness prompt;
- fresh stop/local-recording log event after the stop prompt;
- visible active recording indicator observed;
- newest artifact metadata validation result;
- whether upload queue state changed;
- any blocker code, if recording fails.
- whether the run represents a low-leakage/headphones case or a
  speakerphone/high-leakage case.
- for speakerphone/high-leakage cases, whether both original tracks are present
  and uploadable even when the manifest quality state is `degraded` or `failed`.

Do not record:

- raw audio;
- transcript text;
- private meeting content;
- screenshots with private account or meeting text;
- credentials, signed URLs, tokens, or private filesystem paths.

## Acceptance For Closing The Current Desktop Gap

The desktop current-branch start/stop gap has two proof classes because real
users will record both with headphones and through speakers:

- **Low-leakage/headphones proof**: the same current branch bundle produces a
  `saved` / `ready` local recording package.
- **Speakerphone/high-leakage proof**: the same current branch bundle records
  both original tracks and produces an uploadable structurally valid package
  even when the quality truth is `degraded`, `failed`, `leakage_unproven`, or
  `leakage_detected`.

The desktop current-branch start/stop gap can be marked proven for a proof
class only when the same current branch bundle:

1. has granted microphone and Screen/System Audio permission;
2. enters active recording after manual Record;
3. exposes one-action Stop while active;
4. records fresh `recording.started` and stop/local-recording events;
5. creates either a clean `saved` package for the low-leakage class or a
   structurally valid uploadable degraded/failed package for the speakerphone
   class;
6. leaves no stale active recording process after Stop.

The old feature-025 `--validate-latest-artifact` acceptance validator still
requires a clean `saved` / `ready` artifact and is expected to reject
speakerphone/high-leakage packages. That rejection does not by itself mean the
045 MVP pipeline failed; for 045, the important speakerphone question is
whether structurally valid local packages are queued, uploaded, processed on
the server, and shown truthfully to the user with quality warnings.

If any step fails, keep the gap open and record the safe failure reason.
