# Contract: Desktop support incident report v2

## Request

`POST /api/v1/desktop/support-incidents`

- Authenticated embedded-cabinet session and existing CSRF/idempotency rules
  remain required.
- New clients send `schema_version: desktop-support-incident.v2` and
  `redaction_state: metadata_only`.
- Server accepts `desktop-support-incident.v1` during migration.
- Unknown fields containing credentials, tokens, cookies, signed URLs, raw
  audio, transcript/content, email/name or paths are rejected before mutation;
  unknown harmless fields are not trusted and are omitted/redacted.
- All IDs crossing the report boundary are opaque fingerprints. The server may
  store scoped identifiers internally but never puts them in the Issue body.

## Response

The existing `SupportIncidentResponse` remains compatible:

```json
{
  "incident_id": "CUST-...",
  "incident_status": "synced|pending_sync",
  "github_issue_number": 123,
  "github_issue_url": "https://github.com/...",
  "dedupe_status": "created|updated",
  "affected_count": 1,
  "copy_fallback_available": true,
  "user_message": "..."
}
```

The URL/number are returned only through the existing authenticated response;
the clipboard fallback remains useful when they are absent.

## Compatibility and bounds

- Missing v2 fields are represented as `unknown` in the server report.
- `retry_history` and `timeline` are limited to five events each; affected
  fingerprints to five; serialized report to 256 KiB.
- The server computes authoritative CUST/fingerprints and does not trust the
  client correlation values for tenant scoping or dedupe.
