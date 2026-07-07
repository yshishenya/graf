# Manual Upload UI Contract

## Browser And Embedded Entry Points

The meetings workspace exposes a manual upload action when the current user can
perform unsafe cabinet actions.

| Surface | Page | Required entry |
|---|---|---|
| Browser | `/meetings` | Meetings header and first-run/empty state |
| Embedded desktop | `/desktop/meetings` | Meetings header and first-run/empty state when session/CSRF proof is available |

Rules:

- Upload is not a primary sidebar destination.
- Browser-only admin, billing, sharing, export/download, detailed audit, and
  diagnostics are not exposed by the upload sheet.
- Embedded desktop upload must not claim ownership of native Record, Stop,
  active capture, local queue truth, permission recovery, or diagnostics.

## Cabinet Upload Request

The cabinet UI submits one multipart request to a CSRF-protected cabinet upload
boundary.

```http
POST /api/v1/cabinet/media-uploads
Content-Type: multipart/form-data
X-CSRF-Token: <session-bound token>
```

Fields:

| Field | Required | Notes |
|---|---:|---|
| `file` | yes | Exactly one user-owned audio or common meeting/video media file. |
| `duration_seconds` | yes | Positive integer. Derived from media metadata or entered manually. |
| `title` | no | Safe optional meeting title. |
| `local_recording_id` | yes | UI-generated per-draft idempotency identity. |
| `csrf_token` | no | Optional form fallback for non-XHR clients if supported by the route. |

Response:

- Success returns the existing `ManualMediaUploadResponse` shape from `087`.
- Unsafe browser/session uploads without valid CSRF proof fail with `403`.
- Missing or expired sessions fail with existing auth/session problem codes.
- The response must not expose object keys, dependency URLs, MediaScribe job
  ids, raw transcript text, raw media, or private local paths.

## Public API Compatibility

`POST /api/v1/media-uploads` remains the `087` public/device API contract. This
feature must not add cabinet CSRF requirements to that public route in a way
that breaks Bearer/device callers.

## Upload Sheet Contract

Required controls:

- File picker button labeled `Загрузить медиа` or `Выбрать медиа`.
- Optional title input.
- Required positive duration input with metadata-derived autofill when
  available.
- Start upload button.
- Abort/cancel button before server acceptance.
- Detail/list handoff after server acceptance.
- Safe error region with `aria-live`.

Required states:

| State | Meaning | Required copy/action |
|---|---|---|
| `idle` | No file selected | Choose one media file |
| `file_selected` | One file selected | Show safe file name/size and metadata status |
| `duration_needed` | Duration not readable | Require approximate duration |
| `ready_to_upload` | File and duration valid | Enable start upload |
| `uploading` | Transfer in progress | Show progress or indeterminate transfer state |
| `aborted_before_acceptance` | User aborted before acceptance | Say transfer was not confirmed |
| `network_failed_unconfirmed` | Network failed before acceptance | Offer retry |
| `server_rejected` | Server rejected media/limits | Show safe reason and change-file/retry action |
| `auth_required` | Session/CSRF missing or expired | Show sign-in/reload action |
| `accepted` | Server accepted media | Link to detail/list and do not claim transcript |
| `processing_visible` | Meeting list/detail owns processing | Show existing processing status |

## Error Copy Contract

Known problem codes are mapped to safe Russian copy before display. Unknown
server errors use a generic safe message and may include only reviewed
metadata-safe details.

Minimum code groups:

- `csrf_token_missing`, `csrf_token_invalid`
- `auth_session_invalid`, `auth_session_expired`, `auth_session_mismatched`
- `empty_media_upload`
- `upload_part_bytes_exceeded`
- title/duration/form validation errors
- unsupported/corrupt/no usable audio when server can report them safely
- generic network/unconfirmed transfer
- generic processing unavailable after acceptance

## Accessibility And Responsive Contract

- The sheet must be keyboard operable and focus must move into the sheet when
  opened, then return to the triggering upload action when closed.
- The upload progress indicator must expose progressbar semantics when
  determinate and `aria-live` copy when indeterminate.
- Error and accepted states must be announced without relying on color alone.
- Controls and labels must not overlap at browser desktop, compact browser, or
  embedded desktop widths.
- Reduced-motion users must not depend on animation to understand progress or
  accepted/failure state.

## Desktop Boundary Contract

- No native macOS file picker or native upload custody bridge is introduced in
  this slice.
- `/desktop/meetings` remains the embedded upload host route.
- If route policy changes are required, tests must prove browser-only/local
  file/diagnostic routes remain blocked or handed off according to the existing
  route matrix.
- WebView POST/subresource behavior must not be broadened to inject desktop
  headers without a separate approved slice.
