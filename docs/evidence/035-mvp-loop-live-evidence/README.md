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
