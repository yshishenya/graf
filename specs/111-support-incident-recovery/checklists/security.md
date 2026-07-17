# Security and privacy requirements checklist

**Purpose**: Validate the completeness of auth, CSRF, secret, egress and diagnostic requirements before implementation.

## Authentication and CSRF

- [x] The report route states which authenticated principal and tenant scope may submit or retry an incident.
- [x] The route keeps CSRF protection for cookie-authenticated browser requests and does not introduce a bypass.
- [x] The requirements explicitly reject legacy production headers as a recovery mechanism.
- [x] The bridge requirements distinguish an authenticated same-origin cabinet from login, external and absent surfaces.
- [x] The retry operation is scoped to the caller's workspace and cannot reveal whether another workspace owns an incident number.

## Secrets and external egress

- [x] The GitHub token remains server-only and no desktop/server contract exposes it.
- [x] The design does not distribute the existing GitHub secret to a worker or new service.
- [x] Configuration/readiness feedback is observable internally without returning token values or provider response bodies.
- [x] Private Issue synchronization has bounded safe failure categories and timeout behaviour.

## Diagnostic data

- [x] Allowed report fields are metadata-only and the existing server redactor remains the storage/Issue authority.
- [x] Prohibited classes explicitly include audio, transcript, AI output, tokens, cookies, signed URLs, local paths, names, email, meeting title and private meeting content.
- [x] The requirement covers every persistence and evidence surface: desktop queue, server record, Issue, logs and tests.
- [x] The detailed Issue requirement is bounded by stable safe fields and a maximum affected-identity set.

## Abuse and recovery

- [x] Intake and retry requirements preserve idempotency and bounded rate limiting.
- [x] A server-accepted report has a correlation number before external egress, so GitHub failure cannot erase the recovery reference.
- [x] The retry contract sends only the correlation number and does not require a new diagnostic body.

## Notes

All security requirements are implementation-neutral and trace to FR-001, FR-003, FR-006, FR-007 and FR-008.
