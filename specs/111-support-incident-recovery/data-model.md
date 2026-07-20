# Data Model: support incident recovery

## Server `SupportIncident`

Existing table: `support_incidents`.

| Field | Meaning after this feature | Privacy boundary |
|---|---|---|
| `incident_number` | Stable `CUST-*` correlation identifier assigned after redaction and before GitHub sync. | Random/non-content identifier only. |
| `latest_safe_report_json` | Current server-redacted metadata-only report. | Existing allowlist/redactor remains authoritative. |
| `status` | `synced` when private Issue is linked; `pending_github` when report is accepted but external synchronization is not complete. | No external error text. |
| `github_issue_*` | Private Issue linkage once synchronized. | No token or credential. |
| `github_failure_code` | Bounded safe operational category for pending sync. | No provider response body or secret. |

No migration is required: the existing nullable correlation/link fields and status string support the new truthful lifecycle. Previously synchronized numeric `CUST-*` identifiers remain valid.

## API result

| Field | `synced` | `pending_sync` |
|---|---|---|
| `incident_id` | Required `CUST-*` number | Required `CUST-*` number |
| `incident_status` | `synced` | `pending_sync` |
| `github_issue_number` / URL | Present | `null` |
| HTTP status | `201` on new intake, `200` on update/recheck | `202` |
| User meaning | Server accepted report and Issue exists | Server accepted report; Issue has not yet been confirmed |

## Desktop durable state

`DesktopSupportIncidentSubmissionState` gains `pending_sync`.

| State | Stored facts | UI meaning |
|---|---|---|
| `sending` | safe report fingerprint, dedupe key | Request is in flight. |
| `sent` | `CUST-*`, private Issue number | Server and Issue synchronized. |
| `pending_sync` | `CUST-*`, safe report fingerprint, dedupe key | Server accepted safe report; user may check synchronization without sending report data again. |
| `failed_with_copy_fallback` | safe fingerprint/dedupe/error category only | Report was not accepted; safe clipboard summary remains available. |

The local queue never persists cookie, CSRF, bearer token, Issue token, raw report body beyond its existing bounded diagnostics, audio, transcript or local path.

## State transitions

```text
not_sent -> sending -> sent
                   -> pending_sync -> sent
                   -> pending_sync  (safe sync still unavailable)
                   -> failed_with_copy_fallback
```

`pending_sync -> sent` calls the server sync action with only `incident_id`; the server reads its own retained redacted report.
