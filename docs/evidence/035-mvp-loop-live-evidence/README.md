# Evidence: 035 MVP Loop Live Evidence

Feature: `035-mvp-loop-live-evidence`

This directory stores metadata-safe evidence for the validation-only MVP loop
slice. It proves, blocks, or bounds the current product claim after the accepted
022 mute-truth closeout.

## Evidence Boundary

Allowed evidence:

- installed `/Applications/2brain Rec.app` runtime path proof;
- metadata-safe desktop screenshots of idle, active, paused, resumed, and
  stopped states;
- safe web owner review evidence or explicit blocker notes;
- readiness reports, launch gaps, validation logs, and clean-room reference
  notes.

Forbidden evidence:

- raw audio, transcript text, private meeting content, private emails, account
  identifiers, credentials, tokens, signed URLs, provider payloads, or private
  Krisp/reference screenshots.

## Current Strongest Claim

`pilot_blocked` with bounded `infra_smoke_ready` evidence remains the strongest
truthful claim until all P0/P1 launch gaps are closed or explicitly deferred
with accepted owner guardrails.

## Files

- `validation-log.md`: command and manual walkthrough evidence.
- `readiness-report.json`: structured readiness report for this slice.
- `readiness-report.md`: reviewer-facing readiness summary.
- `launch-gap-register.md`: current blocker register.
- `clean-room-reference.md`: allowed Krisp/reference lessons and brand-distance
  checks.
- `screenshots/`: metadata-safe screenshots or markdown blocker notes only.

## Installed Desktop Evidence

Runtime proof:

- Accepted app path: `/Applications/2brain Rec.app`.
- Staged bundle comparison: `rsync -naci --delete` from the staged installer app
  to `/Applications/2brain Rec.app` returned no differences.
- Code signature check: `codesign --verify --deep --strict` passed.
- Active process path: `/Applications/2brain Rec.app`.

Screenshot evidence:

- `screenshots/2026-06-16-desktop-idle-ready-applications.png`
- `screenshots/2026-06-16-desktop-active-recording-applications.png`
- `screenshots/2026-06-16-desktop-paused-recording-applications.png`
- `screenshots/2026-06-16-desktop-resumed-recording-applications.png`
- `screenshots/2026-06-16-desktop-stopped-list-applications.png`

Latest local artifact validation:

- Validator: `apps/macos/Scripts/validate-meeting-mute-truth.sh --latest-artifact-directory`
  returned PASS.
- Local artifact directory id:
  `20260616-163553-91CF43DD-71DA-45BA-9995-0C0788D49D7F`.
- Manifest schema: `local-recording-manifest.v3`.
- Overall status: `degraded`.
- Permissions: microphone `granted`, system audio `granted`.
- External egress: `false`.
- Transcription: `not started`; readiness `degraded`.
- Tracks:
  - `local_mic`: `saved`, timeline aligned, original evidence role.
  - `remote_speaker`: `degraded` with `silent_input`, timeline not aligned.
- Privacy segments: one `pause` segment with local microphone treatment
  `redacted`.
- Meeting mute truth: `unsupported` with reason `unsupported_target`; no
  meeting-app mute-respecting claim is allowed.

Limitations:

- This evidence proves the installed local capture controls and manifest truth,
  not production rollout readiness.
- The current desktop UI remains a local-mode operational surface and still
  needs product-quality alignment work before any broad launch claim.
- The artifact is intentionally not copied into the repository; only metadata
  and screenshots are committed.
