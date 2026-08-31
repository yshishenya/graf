# Data model: Dev migration repair

All records are metadata-only JSON. Values are immutable after publication;
updates create a new record with a new operation id.

## MigrationDriftSnapshot

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `operation_id` | string | yes | Unique probe operation. |
| `source_sha` | 40-hex string | yes | Exact source revision inspected. |
| `current_revision` | string/null | yes | Revision reported by the target. |
| `code_heads` | string[] | yes | Heads resolved from the checked-out graph. |
| `graph_mismatch` | boolean | yes | Whether target and graph differ. |
| `boundary` | enum | yes | `dev-isolated`, `dev-existing`, or `rejected`. |
| `schema_fingerprint` | string | yes | Digest of schema metadata, never rows. |
| `created_at` | RFC3339 | yes | UTC creation time. |

For `boundary=dev-existing`, the record also contains `database_probe` with
`status`, `reason_code`, and `current_revision` (or `null` when the local
metadata read is blocked). It does not contain a connection URL, credentials,
stderr, or application/user rows.

## RepairDecision

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `decision_id` | string | yes | Stable decision identifier. |
| `owner` | string | yes | Human operator accountable for execution. |
| `reason` | string | yes | Plain-language cause and intended result. |
| `affected_boundary` | string | yes | Explicit Dev target, never production. |
| `backup_evidence` | string | yes | Digest and restore rehearsal reference. |
| `rollback_target` | string | yes | Exact recoverable target. |
| `abort_conditions` | string[] | yes | Conditions that force a blocked state. |
| `approved_by` | string | yes | Reviewer identity. |
| `approved_at` | RFC3339 | yes | Approval timestamp. |
| `target_sha` | 40-hex string | yes | SHA to which evidence is bound. |

## RepairEvidence

Contains `decision_id`, `operation_id`, backup and restored fingerprints,
`expected_head`, `current_revision`, `upgrade_runs` (exactly two), readiness and
smoke verdicts, component SHAs, rollback status, and `status` (`pass`, `blocked`,
`failed`). It MUST NOT contain database rows, credentials, transcript text,
tokens, raw logs, or private URLs.
