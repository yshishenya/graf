# Installed App Final Walkthrough Evidence

Feature: `036-owner-review-live-polish`
Task: `T047`
Issue: `#1153`
Date: 2026-06-22
App: `/Applications/2brain Rec.app`

## Safety Boundary

Only cropped native right-inspector screenshots are committed. Full-window
captures were used for local inspection only and were not committed because the
main workspace can contain meeting names, local file paths, or other private
context.

The committed crops do not include cookies, request headers, account
identifiers, transcript text, raw audio, signed URLs, or local home paths.

## Walkthrough Result

| State | Evidence | Verified signal |
|-------|----------|-----------------|
| Idle | `installed-app-final-idle-2026-06-22.png` | Native inspector shows local control, recording stopped, Start button, and meters waiting for recording. |
| Active | `installed-app-final-active-2026-06-22.png` | Native inspector shows active recording, Pause and Stop controls, local recording in progress, and microphone/meeting level activity. |
| Paused | `installed-app-final-paused-2026-06-22.png` | Native inspector shows recording paused, Resume and Stop controls, and explicit copy that stop remains available. |
| Resumed | `installed-app-final-resumed-2026-06-22.png` | Native inspector returns to active recording after Resume with recording levels visible. |
| Stopped | `installed-app-final-stopped-2026-06-22.png` | Native inspector shows recording stopped, Start button restored, local copy saved with limitations, and meters waiting for the next recording. |

## Cabinet-State Coverage

The same installed runtime preserves the earlier cabinet-state evidence:

- `installed-app-missing-auth-recovery.png` proves the missing-auth recovery
  path with native local recording controls still visible.
- `installed-app-embedded-login.png` proves the embedded production login
  surface inside the native shell.
- The final idle, active, paused, resumed, and stopped crops prove the
  configured local-control surface and local-only recording truth from the
  installed `/Applications` app.

## Decision

`T047` is complete: the installed app walkthrough now covers idle, active,
paused, resumed, stopped, configured, missing-auth, and local-only states with
metadata-safe committed evidence. This closes the stale
`desktop-runtime-walkthrough-evidence` readiness gap without changing the
remaining live owner-review, notes/action output, production rollout, signed
installer, or broad pilot claims.
