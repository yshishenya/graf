# Contract: Access Outcomes

## Purpose

Blocked access must be safe for users and useful for operators without leaking
foreign tenant existence, meeting content, transcript text, raw audio, object
keys, credentials, tokens, signed URLs, passwords, or live secret paths.

## API Outcomes

| Scenario | API result | Evidence |
|----------|------------|----------|
| Same-tenant read | Success | Optional metadata-only success evidence |
| Same-tenant write/delete | Success | Optional metadata-only success evidence |
| Cross-tenant read by guessed ID | `404 not_found` or empty collection | Metadata-only denied evidence |
| Cross-tenant write/delete | `403 forbidden` | Metadata-only denied evidence |
| Missing tenant context | Auth/context problem, preferably `403` or existing unavailable-context status when infrastructure is unavailable | Metadata-only missing-context evidence |
| Stale or revoked session/device | `403 forbidden` with existing safe code | Metadata-only denied evidence |
| Maintenance context allowed | Operation-specific success | Metadata-only maintenance evidence |
| Maintenance context blocked | `403 forbidden` or rollout halt | Metadata-only blocked evidence |

## Problem Detail Rules

Problem responses use the existing `application/problem+json` shape:

```json
{
  "type": "about:blank",
  "title": "Forbidden",
  "status": 403,
  "code": "tenant_scope_denied",
  "request_id": "metadata-only-request-id"
}
```

Allowed new or reused safe codes:

- `tenant_context_missing`
- `tenant_scope_denied`
- `tenant_mutation_denied`
- `tenant_resource_not_found`
- existing device/session denial codes when they are already content-safe

Response bodies must not include:

- foreign organization/workspace/user/meeting IDs;
- transcript or diarization text;
- object keys or signed URLs;
- live credential paths;
- raw SQL policy text containing secret settings.

## Validation Outcomes

Validation must prove:

- 100% cross-tenant read probes do not reveal foreign-row existence.
- 100% cross-tenant write/delete probes return authorization failure.
- 100% missing-context API probes return auth/context failure or equivalent
  infrastructure-unavailable context error.
- 100% evidence payloads are metadata-only.
