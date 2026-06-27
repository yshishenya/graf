# Contract: Support Incident Reporting

## Endpoint

```http
POST /api/v1/desktop/support-incidents
Authorization: Bearer <desktop-session-token>
Idempotency-Key: support-incident:<safe-report-fingerprint>
Content-Type: application/json
```

The endpoint is authenticated with the existing desktop principal, tenant, and
device dependencies. It is a backend API/service endpoint, not a web cabinet
route. The desktop app must not call GitHub directly.

## Request Body

```json
{
  "schema_version": "desktop-support-incident.v1",
  "app_name": "2brain Rec",
  "bundle_id": "pro.2brain.rec",
  "app_version": "2026.06.26",
  "build_version": "1234",
  "macos_version": "15.5",
  "architecture": "arm64",
  "locale": "ru-RU",
  "timezone": "Europe/Moscow",
  "environment_base_url_identity": "rec.2brain.pro",
  "workspace_fingerprint": "ws_fpr_7b2e",
  "user_fingerprint": "usr_fpr_01af",
  "device_fingerprint": "dev_fpr_41dd",
  "safe_device_identifier": "device:dev_fpr_41dd",
  "safe_recording_identity": "local:rec_fpr_18ce",
  "local_recording_id_fingerprint": "rec_fpr_18ce",
  "server_meeting_present": false,
  "server_meeting_fingerprint": "not_applicable",
  "server_media_revision_present": false,
  "server_media_revision_fingerprint": "not_applicable",
  "custody_lifecycle_state": "terminal_undelivered",
  "upload_queue_item_state": "failed",
  "retry_class": "terminal",
  "retry_mode": "not_retryable",
  "normal_user_action": "send_support_report",
  "failure_category": "retention_expired",
  "problem_code": "custody.retention_expired.local_retained",
  "sync_conflict_state": "retention_expired",
  "created_at": "2026-06-26T10:00:00Z",
  "updated_at": "2026-06-26T10:05:00Z",
  "retention_deadline": "2026-06-26T10:00:00Z",
  "server_identity_present": false,
  "local_media_retained": true,
  "data_loss_risk": "possible",
  "server_copy_known": false,
  "upload_attempt_count": 3,
  "last_attempt_at": "2026-06-26T09:58:00Z",
  "next_retry_at": "not_applicable",
  "last_safe_http_status": "unknown",
  "last_safe_problem_code": "retention_expired",
  "upload_session_present": false,
  "upload_session_fingerprint": "not_applicable",
  "expected_parts_count": 0,
  "uploaded_parts_count": 0,
  "range_mismatch_metadata": {
    "has_mismatch": false,
    "missing_range_count": 0
  },
  "local_file_completeness_profile": {
    "manifest_present": true,
    "manifest_schema_version": "local_recording_manifest.v1",
    "audio_files_present": true,
    "missing_file_count": 0,
    "corrupt_file_count": 0,
    "total_size_bucket": "100mb_1gb",
    "duration_bucket": "30m_2h"
  },
  "local_purge_state": "none",
  "local_purge_tasks": [],
  "local_purge_ack_state": "not_applicable",
  "processing_status": "not_submitted",
  "app_queue_schema_version": "desktop-upload-queue.v1",
  "ledger_schema_version": "desktop-upload-ledger.v1",
  "redaction_state": "metadata_only"
}
```

Request rules:

- The desktop payload is untrusted input.
- The server must rebuild a redacted allowlisted report before persistence or
  GitHub issue generation.
- Raw audio, transcript text, raw local paths, credentials, cookies, bearer
  tokens, signed URLs, upload tokens, raw logs, screenshots, human names,
  emails, account labels, meeting titles, raw file names, and private meeting
  content are forbidden.
- Required safe fields stay present in the server-redacted JSON as safe values,
  `unknown`, `not_applicable`, or `redacted_metadata`.

## Success Response

```http
HTTP/1.1 201 Created
Content-Type: application/json
```

```json
{
  "incident_id": "CUST-123",
  "incident_status": "created",
  "github_issue_number": 123,
  "github_issue_url": "https://github.com/yshishenya/crisp/issues/123",
  "dedupe_status": "created",
  "affected_count": 1,
  "copy_fallback_available": true,
  "user_message": "Отчет отправлен. Мы разберемся. Номер: CUST-123"
}
```

Duplicate success uses `200 OK` and returns the same `incident_id` with
`dedupe_status: "updated"` and the updated `affected_count`.

Success rules:

- `incident_id` must be `CUST-{github_issue_number}`.
- Success is allowed only after the private GitHub issue exists or is updated.
- The GitHub issue must be in `yshishenya/crisp` and the repository must be
  confirmed private.
- The stored internal incident and GitHub issue number must match.

## Failure Responses

The endpoint returns a `Problem` response using the existing API shape. Desktop
must show the copy fallback for all failures below.

```json
{
  "type": "about:blank",
  "title": "Support incident unavailable",
  "status": 503,
  "code": "support_incident.github_unavailable",
  "detail": "Private support issue could not be created or updated.",
  "custody_owner": "support",
  "retry_class": "not_retryable",
  "normal_user_action": "copy_safe_report",
  "metadata_safety": "metadata_only",
  "custody": {
    "owner": "support",
    "retry_class": "not_retryable",
    "normal_user_action": "copy_safe_report",
    "metadata_safety": "metadata_only"
  }
}
```

Required failures:

- `400 support_incident.unsafe_payload`: forbidden content or malformed unsafe
  values were detected.
- `401 unauthorized`: existing desktop auth failure.
- `403 support_incident.workspace_mismatch`: report scope does not match the
  authenticated workspace/device/user.
- `409 support_incident.idempotency_conflict`: idempotency key conflicts with a
  different safe report fingerprint.
- `422 support_incident.unsupported_schema`: unsupported schema version or
  missing required safe fields.
- `429 support_incident.rate_limited`: rate bucket exceeded.
- `503 support_incident.configuration_invalid`: target repo is not exactly
  `yshishenya/crisp`, repo privacy cannot be confirmed, or required labels are
  missing.
- `503 support_incident.github_unavailable`: GitHub create/update failed,
  timed out, or returned a rate-limit/dependency error.

User-facing failure copy:

```text
Не удалось отправить. Скопируйте отчет и отправьте в поддержку.
```

## GitHub Issue Contract

### Title

```text
[061][{priority}][support/custody] Пользовательская проблема: {human_problem_summary} ({problem_code})
```

Priority rules:

- `P0` only when safe metadata indicates probable data loss at scale or active
  production-wide impact.
- `P1` for a blocked local recording that may affect custody.
- `P2` for retained local media with no immediate data-loss risk and no blocked
  user action.

The title must not include names, emails, raw paths, meeting titles,
transcript text, signed URLs, tokens, raw recording identifiers, or private
content.

### Labels

Required labels:

- `needs-triage`
- `feature:061`
- `type:bug`
- `priority:P0`, `priority:P1`, or `priority:P2`
- `area:macos`
- `area:api`
- `area:privacy`
- `source:user-report`
- `privacy:metadata-only`

Optional labels from the project canon:

- `area:lifecycle`
- `area:observability`
- `gate:pr-blocker`
- `gate:deployment-blocker`
- `gate:pre-merge`
- `gate:backlog`

Missing required labels are configuration failure. Do not create dynamic labels
from `problem_code`, `dedupe_key`, device ids, users, workspaces, or root
causes.

### Body

The body must use the section order from `spec.md`:

1. `Кратко`
2. `Контекст`
3. `Проблема`
4. `Проверенные факты`
5. `Границы задачи`
6. `Критерии приемки`
7. `Что проверить перед закрытием`
8. `Заметки по реализации`
9. `Ссылки`

The body must include the full server-redacted metadata-only report in a fenced
JSON block. Updating a deduped issue must preserve human sections and replace
only generated safe metadata, aggregate counters, timestamps, and safe identity
list.

The full safe metadata-only report remains in the private issue indefinitely
unless a confirmed privacy/security incident or explicit owner-controlled
policy change requires manual redaction.

## Desktop UI Contract

Reportable custody states:

- support-owned `cannot_send`
- admin/access-policy blockers
- terminal/expired states with local media retained
- processing blocked/failed states where support can classify the problem

Primary action:

```text
Отправить отчет
```

Success state:

```text
Отчет отправлен. Мы разберемся. Номер: CUST-{github_issue_number}
```

Failure/offline state:

```text
Не удалось отправить. Скопируйте отчет и отправьте в поддержку.
```

Fallback action:

```text
Скопировать отчет
```

Required human explanations:

- Terminal expired, no server identity, local media retained:
  `Автоматическая отправка уже не выполнится. Локальная копия сохранена на этом Mac. Отправьте отчет, чтобы мы проверили, можно ли помочь.`
- Admin/access issue:
  `Нужна проверка доступа или политики рабочего пространства. Отправьте отчет, мы передадим детали поддержке/администратору.`

The UI must not present internal enum codes as the main explanation. If text
says a report can be copied, the `Скопировать отчет` button must be visible.
The report actions must have accessible names, keyboard/focus reachability
through the existing native custody surface, and status text that remains
readable without overlapping neighboring controls.

## WebView Boundary

This feature must not add native local rows to the server-owned WebView meeting
list and must not require changes in `apps/server/src/twobrain_rec_server/cabinet/web.py`.
