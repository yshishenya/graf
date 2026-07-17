# Contract: desktop support incident API

All routes require an authenticated tenant scope. When authentication is from the web session cookie, the existing `X-CSRF-Token` protection remains required.

## `POST /api/v1/desktop/support-incidents`

Accepts the existing `desktop-support-incident.v1` metadata-only payload and `Idempotency-Key`.

### Synchronized result

`201 Created` for a new report or `200 OK` for a deduplicated update:

```json
{
  "incident_id": "CUST-ABC123",
  "incident_status": "synced",
  "github_issue_number": 123,
  "github_issue_url": "https://github.com/yshishenya/crisp/issues/123",
  "dedupe_status": "created",
  "affected_count": 1,
  "copy_fallback_available": true,
  "user_message": "Запрос принят и передан в поддержку. Номер: CUST-ABC123"
}
```

### Accepted-pending result

`202 Accepted` when redaction, authorization and server persistence succeeded but private Issue synchronization is not confirmed:

```json
{
  "incident_id": "CUST-ABC123",
  "incident_status": "pending_sync",
  "github_issue_number": null,
  "github_issue_url": null,
  "dedupe_status": "created",
  "affected_count": 1,
  "copy_fallback_available": true,
  "user_message": "Запрос принят сервером. Синхронизация с поддержкой ожидает проверки. Номер: CUST-ABC123"
}
```

The body never contains raw provider errors, tokens, URLs signed for access, local paths, recording content, transcript or audio.

## `POST /api/v1/desktop/support-incidents/{incident_id}/sync`

Requests a retry for an already accepted incident. The request body is empty; the server looks up the redacted report by `incident_id` within the authenticated workspace.

- `200 OK` — private Issue is now synchronized.
- `202 Accepted` — incident remains accepted but synchronization is pending.
- `401/403` — caller must authenticate again; no sync claim is made.
- `404` — correlation number is not available in the caller's workspace.

The route must not accept diagnostic payload fields and must not reveal whether another workspace owns an incident.
