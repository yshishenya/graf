# Security And Privacy Checklist: 092 Automatic Meeting Detection

**Date**: 2026-07-08

## Data Minimization

- [x] Requirements prohibit raw audio, transcript text, meeting content, screen
  content, full private URLs, passcodes, attendee emails, raw IPs, credentials,
  tokens, signed URLs, secret paths, full app paths, and user home paths.
- [x] Unknown app identity upload is blocked unless the VKS-candidate filter
  passes.
- [x] Redacted unknown entries are contractually forbidden from including
  `bundleId`, `displayName`, `signingTeamId`, or `version`.
- [x] Browser metadata requirements avoid full private URL storage and require
  service family/pattern class instead.
- [x] Diagnostics and telemetry remain metadata-only by default.

## Egress And Auth

- [x] Desktop telemetry endpoint requires authenticated tenant/device context.
- [x] Registry fetch is authenticated and private-cacheable.
- [x] Telemetry upload failure cannot block manual recording.
- [x] Workspace/admin policy can disable meeting-detection improvement telemetry.
- [x] No MediaScribe credentials, object-storage credentials, or direct audio
  egress are introduced.

## Abuse And Safety

- [x] Idempotency, rate limits, payload size caps, local retention, and backoff
  are required.
- [x] Forbidden-content rejection occurs before persistence.
- [x] Candidate upload does not create prompt-enabled support.
- [x] Admin actions are audited with actor, timestamp, before/after state, reason,
  and linked evidence.
- [x] Remote registry cannot disable visible recording state, one-action Stop,
  prompt/auto-record requirements, or redaction gates.

## Implementation Validation Requirements

- [x] Requirements specify validation for representative forbidden-content
  samples before writing DB rows.
- [x] Requirements specify tenant isolation validation for telemetry batches,
  candidates, registry drafts, and review actions.
- [x] Requirements specify admin template validation against unsafe metadata
  field rendering.
