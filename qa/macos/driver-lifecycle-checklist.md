# macOS Driver Lifecycle Checklist

## Purpose

Validate driver lifecycle behavior for live passthrough.

## Scenarios

- [x] Fresh install publishes `2brain Rec Microphone` and `2brain Rec Speaker`.
- [x] Update does not interrupt an active call without explicit recovery state.
- [x] Rollback restores the previous known-good driver or reports manual action.
- [x] Repair restores missing driver files and requires revalidation.
- [x] Uninstall removes virtual devices or reports remaining manual cleanup.
- [ ] Desktop app crash makes public devices hidden or unavailable within 5 seconds.
- [ ] Relaunch restores public devices only after route recovery and revalidation.
- [x] Diagnostics for each lifecycle failure contain no raw audio or secrets.

## Evidence

Record command output, app state, and runtime probe observations in
`apps/macos/AudioDriver/RuntimeProofReport.md` and
`qa/macos/release-candidate-checklist.md`.

### 2026-05-31 Local Evidence

Fresh install publication: accepted. Runtime probe from an interactive Terminal
found both expected Core Audio devices:

```text
Expected device visibility:
- 2brain Rec Microphone: FOUND
- 2brain Rec Speaker: FOUND
Runtime Core Audio publication proof: ACCEPTED
```

Local installer build: accepted for development. Command:

```sh
TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh
```

Resulting package:

```text
apps/macos/.build/installer/2brain-rec-local.pkg
```

Observed size: `599K`.

Package signature: local package is unsigned:

```text
Status: no signature
```

Decision: acceptable only for local development. Production lifecycle approval
requires Developer ID signing and notarization.

Update behavior: source review accepted. `update-preflight.sh` detects active
capture through `2BRAIN_REC_CAPTURE_ACTIVE=1` or
`/var/tmp/2brain-rec-capture-active`, then exits with code `2` and reports
`deferred_active_call`. This proves the intended active-call-safe gate exists;
a real active-call update rehearsal remains pending.

Repair behavior: source review accepted. `repair.sh` restores the HAL driver to
`/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver`, clears extended attributes,
restarts `coreaudiod`, and writes JSON evidence. Privileged repair rehearsal is
pending.

Rollback behavior: source review accepted. `rollback.sh` restores the newest
backup from `/var/tmp/2brain-rec-driver-backups` or reports manual action when
no backup is available. Destructive rollback rehearsal is pending.

Uninstall behavior: source review accepted. `uninstall.sh` removes the HAL
driver, app bundle, trace file, and restart marker, restarts `coreaudiod`, and
reports manual cleanup if any artifact remains. Destructive uninstall rehearsal
is pending.

Diagnostics safety: accepted for generated lifecycle reports because scripts
write status, paths, and cleanup actions only. They do not write raw audio,
transcripts, credentials, tokens, or signed URLs.

Pending lifecycle proof:

- desktop app crash makes public devices hidden or unavailable within 5 seconds;
- app relaunch restores devices only after route recovery and revalidation;
- active-call update rehearsal with a real capture/call state;
- privileged repair, rollback, and uninstall rehearsals on a disposable local
  install.
