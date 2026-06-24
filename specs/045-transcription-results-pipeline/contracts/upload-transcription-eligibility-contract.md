# Contract: Upload And Transcription Eligibility

## Purpose

Define which conditions block upload/transcription and which conditions are
diagnostic-only for feature `045`.

## Local Package Eligibility

### Must Allow

A package is eligible for upload and server transcription when all required
package files exist and are readable, consent and permissions allow recording,
and no lifecycle/access policy blocks the meeting, even if any of these local
signals are degraded, failed, inconclusive, or unavailable:

- transcription readiness;
- leakage detection;
- leakage not measured;
- leakage unproven;
- insufficient reference;
- echo or speakerphone contamination;
- silence or low audible input;
- timeline/duration mismatch;
- local cleanup/AEC not available;
- derived cleanup not registered or not selected.

The product may label this as `eligible_with_quality_warnings`, but must not
block upload/transcription solely because of these quality signals.

### Must Block

A package must remain blocked before transcription when any of these conditions
apply:

- recording consent was not accepted for the meeting scope;
- microphone or system-audio permission does not allow accepted recording;
- required manifest, microphone, or incoming/system audio file is missing or
  unreadable;
- the user deleted the meeting or access was revoked before processing;
- the package was already terminally purged or lifecycle-blocked;
- upload retry would duplicate a completed terminal egress without idempotent
  server state;
- server finalization detects missing roles, duplicate roles, swapped role
  mapping, ambiguous parts, byte-length mismatch, checksum mismatch, expected
  size mismatch, or immutable media revision fingerprint conflict.

## Server Finalization Boundary

Server finalization must keep these checks as hard gates:

- required roles: manifest, microphone, incoming/system audio;
- exactly one finalized object per required role;
- uploaded roles match expected session roles;
- descriptor byte length matches stored object byte length;
- descriptor digest matches stored object digest;
- manifest digest matches the manifest track;
- accepted media revision fingerprint is immutable.

Server finalization must not add audio-content, echo, leakage, silence, or
quality scoring as a pre-transcription blocker in this feature.

## Status Contract

Eligibility outcomes must map to user-safe status:

| Outcome | User-safe meaning | Can transcribe? |
|---|---|---|
| `eligible` | Package is accepted for upload and transcription | Yes |
| `eligible_with_quality_warnings` | Package is imperfect but can still produce the best available transcript | Yes |
| `blocked_privacy_or_permission` | Recording cannot be uploaded under current consent or permission truth | No |
| `blocked_missing_or_unreadable_file` | Required package files are unavailable | No |
| `blocked_integrity` | Package identity or checksum truth failed | No |
| `blocked_lifecycle` | Deletion, access, or lifecycle state prevents processing | No |

## Evidence Rules

Committed evidence may include status names, reason codes, object counts,
durations, byte counts, checksums only when non-secret, and pass/fail summaries.
Committed evidence must not include raw audio, transcript text, private meeting
content, credentials, signed URLs, secret paths, or private local paths.
