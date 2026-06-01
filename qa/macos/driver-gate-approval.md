# macOS Driver Gate Approval

## Purpose

Record the approval gates required before implementing the live passthrough
driver slice.

## Required Gates

| Gate | Required Evidence | Status |
|---|---|---|
| Privilege model | HAL bundle and app responsibilities documented | Approved for local MVP proof; production release still requires signed/notarized package review |
| Installer | Interactive installer path builds and reports recovery states | Local package build accepted on 2026-05-31 |
| Signing | Local development signing and production signing plan documented | Local ad-hoc app signing accepted for development; production Developer ID signing pending |
| Notarization | Production notarization owner and validation path documented | Pending for production release |
| Update | Active-call-safe update behavior documented | Accepted by script review; active-call live rehearsal pending |
| Rollback | Rollback script and partial cleanup behavior documented | Accepted by script review; destructive rollback rehearsal pending |
| Repair | Repair script restores driver publication and route state | Accepted by script review; privileged repair rehearsal pending |
| Uninstall | Uninstall removes driver artifacts and reports manual cleanup | Accepted by script review; destructive uninstall rehearsal pending |
| Passthrough failure | App I/O loss fails closed and recovers only after revalidation | App kill/relaunch, low-resource recovery, and fallback evidence accepted for local smoke scope |
| Non-recording UX | Ready/active passthrough copy must not imply recording, transcription, or capture | Accepted for current non-recording smoke scope; recording copy remains future |
| Diagnostics redaction | Release-hardening evidence must be metadata-only | Contract tests and secret/redaction scans accepted for current evidence set |
| QA matrix | Browser, physical-device, Bluetooth, and installer scenarios listed | Telemost, Chrome, Opera, and Zoom smoke accepted; Yandex Browser skipped/not accepted; long-run recording and production installer pilots pending |

## Evidence Recorded 2026-06-01

Owner: local development validation by yshishenya, recorded by Codex.

- Low-resource default-safe runtime proof accepted with both virtual devices
  visible/alive and non-running.
- No-hang/audio settings evidence passed for macOS Sound, Chrome, Opera, Zoom,
  and Yandex Telemost.
- Idle `coreaudiod` CPU gate passed after browser/meeting smoke with peak 8%
  and 0 sustained seconds above threshold.
- Manual smoke passed for Telemost, Chrome, Opera, and Zoom with
  `2brain Rec Microphone` and `2brain Rec Speaker`.
- Recording, transcription, upload, MediaScribe, Langfuse, and dashboard flows
  remain out of scope for this accepted driver/audio-route gate.

## Evidence Recorded 2026-05-31

Owner: local development validation by yshishenya, recorded by Codex.

### Runtime Publication

Command:

```sh
make -C apps/macos/AudioDriver proof-runtime-probe-run
```

Result: accepted. Core Audio listed `2brain Rec Microphone` and
`2brain Rec Speaker` for the current user. Full evidence is recorded in
`apps/macos/AudioDriver/RuntimeProofReport.md`.

### Installer Build

Command:

```sh
TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh
```

Result: accepted for local development. The script built the proof driver,
built `TwoBrainRecApp` in release mode, ad-hoc signed the app because Developer
Tools Security was enabled, staged the HAL driver and app bundle, and produced:

```text
apps/macos/.build/installer/2brain-rec-local.pkg
```

Artifact size observed on 2026-05-31: `599K`.

### Package Signature

Command:

```sh
pkgutil --check-signature apps/macos/.build/installer/2brain-rec-local.pkg
```

Result:

```text
Status: no signature
```

Decision: this is acceptable only for local development. Production release must
provide `DEVELOPER_ID_APPLICATION_IDENTITY` and `DEVELOPER_ID_INSTALLER_IDENTITY`
so the app and product package are Developer ID signed before notarization.

### Installer Script Shape

Observed files:

```text
apps/macos/Installer/Scripts/build-local-installer.sh
apps/macos/Installer/Scripts/update-preflight.sh
apps/macos/Installer/Scripts/repair.sh
apps/macos/Installer/Scripts/rollback.sh
apps/macos/Installer/Scripts/uninstall.sh
```

There is no `apps/macos/Installer/Scripts/install.sh`. This is expected for the
current packaging design: installation is performed by the generated `.pkg`
component package and its postinstall path, not by a standalone manual
`install.sh`.

### Update Preflight

`update-preflight.sh` checks `2BRAIN_REC_CAPTURE_ACTIVE` and
`/var/tmp/2brain-rec-capture-active`. If capture is active, it exits with code
`2` and reports:

```json
{"result":"deferred_active_call","reason":"capture_is_active"}
```

Decision: update safety behavior is documented and acceptable for this feature
gate. A live active-call rehearsal is still required before release readiness.

### Repair, Rollback, And Uninstall

`repair.sh` copies the staged HAL driver into
`/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver`, clears extended attributes,
restarts `coreaudiod`, and writes a JSON report.

`rollback.sh` removes the current HAL driver, restores the latest backup from
`/var/tmp/2brain-rec-driver-backups`, clears extended attributes, restarts
`coreaudiod`, and reports either success or manual cleanup requirements.

`uninstall.sh` removes the HAL driver, application bundle, trace file, and
restart-required marker, clears extended attributes, restarts `coreaudiod`, and
reports either success or partial manual cleanup.

Decision: lifecycle scripts are acceptable by source review for this feature
gate. Privileged destructive rehearsals remain pending and must not be implied
as completed.

## Approval Rule

Implementation may proceed phase by phase only after this file has an owner,
evidence links, and no unaccepted high-risk gap for the tasks being executed.

## Current Approval Decision

Proceed with implementation and non-destructive validation. Do not mark the
feature release-ready until these pending items are completed:

- production Developer ID app and installer signing;
- notarization validation;
- real private app I/O kill/crash/relaunch fail-closed proof;
- browser meeting matrix and backend outage proof;
- Bluetooth/AirPods managed-route pilot proof;
- privileged repair, rollback, and uninstall rehearsals on a disposable local
  install.
- non-recording passthrough UX screenshot review for ready, active, stale,
  degraded, failed, blocked, repair, and recheck states.
