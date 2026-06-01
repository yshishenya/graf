# Non-Recording Passthrough UX Review

## Purpose

Review status copy for 005 pre-recording hardening. Passthrough may be ready or
active, but recording, transcription, capture, upload, MediaScribe, and Langfuse
must not be implied.

## States

| State | Required copy behavior | Result |
|---|---|---|
| Ready | Says route is ready and explicitly not recording | Pending |
| Active | Says passthrough/call audio is active and explicitly not recording | Pending |
| Stale | Requires recheck and does not claim route is safe | Pending |
| Degraded | Shows degraded route and next action | Pending |
| Failed | Shows audio path unavailable or repair action | Pending |
| Blocked | Shows blocker before calls | Pending |
| Repair | Shows install/repair driver action | Pending |

## Rules

- Do not use customer-facing recording, transcription, capture-active, or upload
  language for non-recording passthrough.
- Do not present device visibility alone as ready.
- Do not rely on color alone; text and icon must both carry status.
- Use original 2brain Rec wording, not Krisp-like copy or layout language.
