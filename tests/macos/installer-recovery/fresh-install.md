# Fresh Install And Restart-Required Smoke Checklist

## Scope

Validate the US1 installer path before route verification can show `ready`.
This checklist covers only interactive MVP installs and repair-style reruns.
Silent install, MDM deployment, and production notarization release automation
remain out of scope until their dedicated tasks.

## Preconditions

- Apple Silicon Mac running macOS 14.5 or later.
- No active capture session or active call that depends on the current audio
  routing.
- Tester has an admin account available for the interactive installer prompt.
- The build under test does not contain secrets, MediaScribe credentials, raw
  audio, transcripts, or signed URLs.

## Fresh Install

- [ ] Start from a machine where no app-managed `2brain Rec` HAL bundle is
      installed.
- [ ] Run the interactive installer and confirm macOS asks for administrator
      approval instead of installing invisibly.
- [ ] Confirm the installer shows the target product name `2brain Rec` and does
      not imply affiliation with Krisp.
- [ ] Confirm installer failure copy distinguishes permission denial, unsupported
      macOS, incompatible CPU architecture, and generic install failure.
- [ ] Confirm both virtual devices appear after install or after the installer
      explicitly requests restart:
      - `2brain Rec Microphone`
      - `2brain Rec Speaker`
- [ ] Confirm the app does not show route `ready` until both mic and speaker
      synthetic verification pass.

## Restart-Required State

- [ ] When Core Audio does not publish the devices immediately, confirm the app
      reports `requires_restart` instead of `ready`.
- [ ] Restart Core Audio or reboot as instructed by the app/installer.
- [ ] Confirm the app rechecks device visibility automatically after restart.
- [ ] Confirm previous physical input/output selections are not overwritten
      unless the user explicitly chooses the virtual devices.

## Repair Rerun

- [ ] Rerun the installer over the same version.
- [ ] Confirm the installer offers repair/reinstall behavior rather than
      creating duplicate virtual devices.
- [ ] Confirm repair preserves user-visible truth: installed, needs repair,
      requires restart, or failed.
- [ ] Confirm diagnostics created after repair redact local paths, usernames,
      credentials, tokens, signed URLs, raw audio, and transcript text by
      default.

## Acceptance

- [ ] Fresh install result is one of `succeeded`, `requires_restart`, or a
      specific recoverable failure.
- [ ] No virtual-device duplicate remains after install or repair.
- [ ] `ready` remains blocked until both route verifications pass.
- [ ] Any manual cleanup requirement is explicitly reported to the user.
