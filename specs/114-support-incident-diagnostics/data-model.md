# Data Model: Детальный metadata-only отчёт поддержки

## Support Incident Report v2

JSON object `desktop-support-incident.v2`, передаваемый macOS в
`POST /api/v1/desktop/support-incidents`.

| Group | Fields | Rules |
| --- | --- | --- |
| Contract | `schema_version`, `redaction_state` | schema is v2 for new clients; server accepts v1/v2; safety must be `metadata_only` |
| Correlation | `client_report_fingerprint`, `client_dedupe_key`, `safe_recording_identity`, `local_recording_id_fingerprint`, server/media/session fingerprints, workspace/user/device fingerprints | opaque prefixes and hex fingerprints only; server recomputes authoritative `safe_report_fingerprint`, `dedupe_key`, CUST and affected identity |
| Runtime | app/bundle/version/build/macOS/architecture/locale/timezone/environment identity | bounded allowlisted strings; environment reduced to hostname; no channel/secret/path |
| Canonical state | `canonical_stage`, `custody_lifecycle_state`, `custody_owner`, `upload_queue_item_state`, `upload_state`, `processing_status`, `deletion_state`, `local_copy_state`, `server_copy_state`, `data_loss_risk`, `normal_user_action`, `retry_class` | stage precedence is server deletion/access/conflict, then local custody; `server_copy_known` is true only when state is confirmed |
| Failure | `failure_category`, `problem_code`, `sync_conflict_state`, `last_safe_problem_code`, `last_safe_http_status`, `server_conflict_reason`, `server_next_action` | safe code grammar; raw failure reason never leaves client |
| Server truth | `server_deletion_state`, `server_access_state`, `server_status`, `server_upload_status`, `server_processing_status`, `server_review_available`, `server_review_status`, `last_reconciled_at` | decoded from existing sync-state; workflow IDs, URLs and content are excluded |
| Time | `created_at`, `updated_at`, `retention_deadline`, `last_attempt_at`, `next_retry_at`, `timeline` | ISO-8601 UTC; timeline contains bounded event code/time/source |
| Retry | `upload_attempt_count`, `retry_history` | at most five latest events; each event has attempt number, states, category, safe problem code, numeric HTTP status and timestamps |
| Artifact | `range_mismatch_metadata`, `local_file_completeness_profile`, expected/uploaded counts, safe track role/profile buckets | counts/buckets/booleans only; no file name/path/audio/checksum bytes |
| Lifecycle | local purge state/tasks/ack, queue/ledger versions, `redaction_state`, affected count/identities | purge task values must match server allowlist; affected identities max five |

## State rules

1. If server truth says deletion/access blocked, `canonical_stage` and
   `server_copy_state` reflect that even when the old local item is `uploaded`
   or has `finalizedAt`.
2. If sync-state is unavailable, server fields are `unknown`; this is not proof
   that a server copy is absent.
3. `data_loss_risk` is `low` only for confirmed server copy, `possible` when
   local data is retained but server copy is deleted/unknown, and `elevated`
   when neither copy is confirmed.
4. `local_purge_tasks` uses allowlisted enum values (`pending` or a known task
   type), never a client-only label such as `local_purge_pending`.

## Timeline event

```text
{
  "event": "created|attempt_started|attempt_finished|reconciled|finalized|retention_deadline",
  "at": "ISO-8601 UTC",
  "source": "local_queue|server_truth"
}
```

Maximum five most useful events after deterministic sorting.

## Retry event

```text
{
  "attempt_number": 3,
  "started_at": "ISO-8601 UTC",
  "finished_at": "ISO-8601 UTC|not_applicable",
  "state_before": "uploading",
  "state_after": "blocked",
  "failure_category": "network",
  "problem_code": "support_incident.github_unavailable",
  "http_status": "503|unknown",
  "next_retry_at": "ISO-8601 UTC|not_applicable"
}
```

The original failure reason and accepted-byte map are not serialized inside the
event; aggregate safe counts remain in the top-level report.

## Server redacted report

The server copies the allowlisted v1/v2 fields, replaces missing/invalid values
with `unknown` or `redacted_metadata`, and appends `received_at`,
`server_redaction_version`, `redaction_result`, `forbidden_field_count`,
`safe_report_fingerprint`, `dedupe_key` and `affected_identity_fingerprint`.
The stored JSON is the latest safe report for the existing support incident
record; it is not a second source of raw logs.

## Relationships

```text
DesktopUploadQueueItem
  -> DesktopUploadCustodyProjection
  -> DesktopSupportIncidentReport v2
  -> server redacted report + CUST
  -> one private GitHub Issue (create/update by dedupe key)
```
