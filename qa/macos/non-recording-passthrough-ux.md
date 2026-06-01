# Non-Recording Passthrough UX Review

## Purpose

Review status copy for 005 pre-recording hardening. Passthrough may be ready or
active, but recording, transcription, capture, upload, MediaScribe, and Langfuse
must not be implied.

## States

| State | Required copy behavior | Result |
|---|---|---|
| Ready | Says route is ready and explicitly not recording | Passed for current local smoke scope |
| Active | Says passthrough/call audio is active and explicitly not recording | Passed for current local smoke scope |
| Stale | Requires recheck and does not claim route is safe | Passed in modeled/recovery evidence |
| Degraded | Shows degraded route and next action | Passed in modeled/recovery evidence |
| Failed | Shows audio path unavailable or repair action | Passed in modeled/recovery evidence |
| Blocked | Shows blocker before calls | Passed in modeled/recovery evidence |
| Repair | Shows install/repair driver action | Passed in installer/recovery evidence |

## Current Review Note

2026-06-01: non-recording passthrough language is accepted for the local
low-resource smoke scope. This does not accept active recording copy, capture
indicator copy, one-action stop copy, retention copy, deletion copy, upload copy,
or transcription copy; those belong to later feature slices.

## Rules

- Do not use customer-facing recording, transcription, capture-active, or upload
  language for non-recording passthrough.
- Do not present device visibility alone as ready.
- Do not rely on color alone; text and icon must both carry status.
- Use original 2brain Rec wording, not Krisp-like copy or layout language.
