# 092 API Contract: Meeting Detection

**Date**: 2026-07-08

This contract complements:

- `meeting-target-registry.schema.json`
- `meeting-detection-telemetry.schema.json`
- `meeting-detection-admin-review.schema.json`

All endpoints are metadata-only. They must reject forbidden content listed in
`../data-model.md`.

## Desktop Telemetry Upload

```http
POST /api/v1/desktop/meeting-detection/telemetry
Authorization: Bearer <desktop session token>
Idempotency-Key: meeting-detection:<device-id>:<rollup-window>
Content-Type: application/json
```

Request body follows `meeting-detection-telemetry.schema.json`.

Success:

```json
{
  "batch_id": "uuid",
  "dedupe_status": "created",
  "accepted_target_rollup_count": 2,
  "accepted_candidate_count": 1,
  "suppressed_candidate_count": 3,
  "registry_version": "2026.07.08.1",
  "next_upload_after": "2026-07-09T12:00:00Z"
}
```

Status codes:

| Status | Code | Meaning |
| --- | --- | --- |
| 200 | `meeting_detection_telemetry_duplicate` | Same idempotency key and same payload accepted before. |
| 201 | `created` | Batch accepted. |
| 400 | `meeting_detection_telemetry_unsafe_payload` | Forbidden content detected. |
| 401 | `missing_auth_context` | Desktop auth/session missing. |
| 403 | `meeting_detection_telemetry_disabled` | Workspace policy disabled upload. |
| 409 | `meeting_detection_telemetry_idempotency_conflict` | Same key with different payload. |
| 422 | `meeting_detection_telemetry_schema_invalid` | Schema unsupported or invalid. |
| 429 | `meeting_detection_telemetry_rate_limited` | Device/workspace rate limit. |
| 503 | `meeting_detection_store_unavailable` | Server store unavailable. |

Server requirements:

- Apply tenant/device context before any DB write.
- Validate schema before persistence.
- Reject payloads where redacted unknown entries include raw app identity.
- Reject payloads where `server_candidate_upload` has score below `4`.
- Store canonical payload fingerprint.
- Aggregate known target health and VKS candidates.
- Return policy/next-upload hints without blocking manual recording.

## Desktop Registry Fetch

```http
GET /api/v1/desktop/meeting-detection/target-registry
Authorization: Bearer <desktop session token>
If-None-Match: "<etag>"
```

Response body follows `meeting-target-registry.schema.json`.

Status codes:

| Status | Meaning |
| --- | --- |
| 200 | Returns latest published registry for the tenant/global scope. |
| 304 | Client cache is current. |
| 401 | Desktop auth/session missing. |
| 503 | Registry unavailable; client may use last-good cache and otherwise must fail closed. |

Headers:

- `ETag`
- `Cache-Control: private, max-age=86400`
- `X-GRAF-Registry-Version`

Server requirements:

- Never publish a registry that weakens compiled capture safety gates.
- Include non-target suppression rules needed by the client filter.
- Keep Windows entries future-only for macOS clients unless platform support
  exists.

## Admin Review Page

```http
GET /admin/meeting-detection
```

Returns existing admin Jinja shell with three queues:

- VKS candidates;
- known target health;
- registry drafts.

The view model must satisfy `meeting-detection-admin-review.schema.json` before
rendering. The page must not expose raw logs, meeting content, full paths, full
private URLs, passcodes, attendee emails, raw IPs, or secrets.

## Admin Review API

All unsafe actions require authenticated admin/owner context and CSRF for web
requests.

```http
POST /api/v1/admin/meeting-detection/candidates/{candidate_id}/mark-non-target
POST /api/v1/admin/meeting-detection/candidates/{candidate_id}/merge
POST /api/v1/admin/meeting-detection/candidates/{candidate_id}/add-diagnostic-only-draft
POST /api/v1/admin/meeting-detection/candidates/{candidate_id}/request-validation
POST /api/v1/admin/meeting-detection/registry-drafts/{draft_id}/publish
POST /api/v1/admin/meeting-detection/targets/{target_id}/disable
```

Common request body:

```json
{
  "reason_code": "safe_reason_code",
  "comment": "optional safe admin note"
}
```

Additional bodies:

Merge:

```json
{
  "target_id": "yandex_telemost_native_macos",
  "reason_code": "same_bundle_vendor"
}
```

Add diagnostic-only draft:

```json
{
  "target_id": "example_native_macos",
  "display_name": "Example Meet",
  "market": "russia",
  "reason_code": "candidate_runtime_observed"
}
```

Requirements:

- Every action writes `MeetingDetectionReviewAction` and `AdminAuditEvent`.
- `add-diagnostic-only-draft` cannot create `prompt_enabled`.
- `publish` validates full registry schema and safety constraints.
- `mark-non-target` adds/updates a non-target rule included in future registry
  fetches.
- `disable` prevents prompts and detector decisions for that target in future
  registry versions.

## OpenAPI

The public OpenAPI contract must include desktop telemetry and registry endpoints
with problem responses. Admin web routes may remain internal but admin API
actions should be covered by contract tests.
