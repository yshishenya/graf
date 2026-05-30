# Contract: Passthrough Diagnostics

## Purpose

Provide actionable local diagnostics for route and passthrough failures without
exporting meeting content or secrets.

## Allowed Fields

- event name
- timestamp
- readiness status
- route path
- failure reason
- device class
- virtual device visibility
- route invalidation reason
- dropout count
- alignment metric
- redaction status
- recovery action

## Forbidden Fields

- raw audio
- audio snippets
- transcript text
- meeting notes
- credentials
- tokens
- signed URLs
- secret file paths
- hidden recording artifacts

## Required Events

- `readiness_check_started`
- `readiness_check_passed`
- `readiness_check_failed`
- `readiness_invalidated`
- `passthrough_started`
- `passthrough_degraded`
- `passthrough_stopped`
- `track_evidence_created`
- `track_evidence_degraded`
- `diagnostic_bundle_created`

## Redaction Rule

Any diagnostic payload containing a forbidden field must replace it with
redaction metadata before writing logs or bundles.
