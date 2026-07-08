# 092 Data Model: Automatic Meeting Detection

**Date**: 2026-07-08

## Server Entities

### MeetingTargetRegistryVersion

Published or draft registry document version.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Primary key. |
| `workspace_id` | UUID nullable | Null means global registry; workspace-specific override is future/admin-controlled. |
| `registry_version` | string | CalVer-like version, e.g. `2026.07.08.1`. |
| `schema_version` | int | Starts at `1`. |
| `status` | string | `draft`, `published`, `disabled`, `superseded`. |
| `source` | string | `packaged_seed`, `admin`, `migration`, `import`. |
| `published_at` | timestamptz nullable | Set only for published versions. |
| `published_by_user_id` | UUID nullable | Admin actor. |
| `document_json` | JSON | Full validated registry document. |
| `etag` | string | Strong or stable weak ETag for desktop fetch. |
| `created_at` / `updated_at` | timestamptz | Audit timestamps. |

Validation:

- Only one published global registry version is active at a time.
- A draft cannot become published if schema validation fails.
- Publishing records an `AdminAuditEvent`.

### MeetingTargetRegistryEntry

Queryable entry extracted from registry document.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Primary key. |
| `registry_version_id` | UUID | FK to `MeetingTargetRegistryVersion`. |
| `target_id` | string | Stable target id. |
| `display_name` | string | Safe label. |
| `market` | string | `global`, `russia`, `enterprise`, `unknown`. |
| `platform` | string | `macos`, `windows`, `browser`, `cross_platform`. |
| `target_family` | string | `native_app`, `browser_meeting`, `provider`, `manual_only`. |
| `mode` | string | `prompt_enabled`, `diagnostic_only`, `blocked_missing_bundle`, `manual_or_browser_only`, `disabled`. |
| `evidence` | string | `runtime_verified`, `package_verified`, `installed_verified`, etc. |
| `native_bundle_ids` | JSON array | macOS bundle ids. |
| `windows_process_names` | JSON array | Future Windows process/executable names. |
| `browser_service_patterns` | JSON array | Safe service-family pattern classes. |
| `required_signals` | JSON array | Required adapter/signal families. |
| `comments` | string nullable | Internal safe notes only. |

Validation:

- `prompt_enabled` native macOS entries require at least one `native_bundle_id`
  and runtime evidence.
- Browser entries cannot use browser audio ownership as the only required signal.

### MeetingDetectionTelemetryBatch

One bounded client upload.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Primary key. |
| `workspace_id` | UUID | Tenant scope. |
| `user_id` | UUID | Authenticated user. |
| `device_id` | UUID | Registered device. |
| `idempotency_key_fingerprint` | string | Request idempotency. |
| `payload_fingerprint` | string | Canonical payload fingerprint. |
| `schema_version` | int | Starts at `1`. |
| `client_version` | string | Desktop version. |
| `platform` | string | `macos` for first release. |
| `os_version_major` | string | Major OS bucket. |
| `registry_version` | string | Registry used by client. |
| `candidate_filter_version` | string | Scoring/filter version. |
| `rollup_started_at` / `rollup_ended_at` | timestamptz | Bucket boundaries. |
| `policy_json` | JSON | Detection/upload policy summary. |
| `resource_rollup_json` | JSON | CPU/memory/upload counters/buckets. |
| `redaction_result` | string | `accepted`, `rejected_forbidden_content`. |
| `received_at` | timestamptz | Server receive time. |

Validation:

- Reject unsupported schema versions.
- Reject payloads with forbidden strings/patterns.
- Duplicate idempotency with same payload returns existing result; same key with
  different payload returns conflict.

### MeetingDetectionTargetHealthRollup

Aggregated known-target behavior from telemetry.

| Field | Type | Notes |
| --- | --- | --- |
| `workspace_id` | UUID | Tenant scope. |
| `target_id` | string | Known registry target id. |
| `platform` | string | macOS first. |
| `registry_version` | string | Registry version. |
| `client_version_bucket` | string | Optional bucket. |
| `os_version_major` | string | OS bucket. |
| `rollup_date` | date | Daily aggregate. |
| `support_mode` | string | Registry mode. |
| `signal_families_json` | JSON | Observed signal families. |
| `outcomes_json` | JSON | Counts for observed/prompted/skipped/etc. |
| `duration_buckets_json` | JSON | Duration buckets. |
| `reason_codes_json` | JSON | Safe reason codes. |

Primary key may be `(workspace_id, target_id, platform, registry_version,
rollup_date, os_version_major)`.

### MeetingDetectionCandidate

Aggregated unknown likely-VKS app candidate for admin review.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Primary key. |
| `workspace_id` | UUID | Tenant scope; global aggregate may be future-only. |
| `platform` | string | `macos`. |
| `candidate_kind` | string | `unknown_native_app`. |
| `state` | string | `new`, `reviewing`, `non_target`, `merged`, `diagnostic_only_draft`, `validation_needed`, `ready_for_prompt_review`, `published`, `disabled`. |
| `bundle_id` | string nullable | Present only for server-candidate uploads. |
| `display_name` | string nullable | Safe app display name. |
| `signing_team_id` | string nullable | Team ID when provided. |
| `version_samples_json` | JSON array | Bounded samples. |
| `candidate_score` | int | Max observed or aggregate score. |
| `candidate_reasons_json` | JSON array | Reason codes. |
| `suppression_reasons_json` | JSON array | If suppressed. |
| `stable_observation_count` | int | Aggregate count. |
| `reporting_installation_count` | int | Distinct devices/installations. |
| `manual_record_nearby_count` | int | Strong signal count. |
| `calendar_or_join_hint_count` | int | Safe hint count. |
| `first_seen_bucket` / `last_seen_bucket` | date | Bucketed dates. |
| `proposed_target_id` | string nullable | For draft registry entry. |
| `merged_target_id` | string nullable | Existing target if merged. |
| `last_batch_id` | UUID nullable | FK to latest telemetry batch. |
| `created_at` / `updated_at` | timestamptz | Audit timestamps. |

Validation:

- Candidates with `state=published` must have a linked registry version.
- Candidate state changes require `MeetingDetectionReviewAction`.
- Raw identity is accepted only if telemetry schema says
  `uploadEligibility=server_candidate_upload` and score is at least `4`.

### MeetingDetectionReviewAction

Audited admin action on a candidate or registry draft.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Primary key. |
| `workspace_id` | UUID | Tenant scope. |
| `candidate_id` | UUID nullable | Candidate target. |
| `registry_version_id` | UUID nullable | Registry target. |
| `actor_user_id` | UUID | Admin actor. |
| `action` | string | `mark_non_target`, `merge_existing_target`, `add_diagnostic_only_draft`, `request_package_validation`, `request_runtime_validation`, `mark_ready_for_prompt_review`, `publish_registry_version`, `disable_target`. |
| `previous_state` / `next_state` | string nullable | State transition. |
| `reason_code` | string nullable | Safe reason. |
| `metadata_json` | JSON | Safe details only. |
| `created_at` | timestamptz | Audit timestamp. |

Also writes an `AdminAuditEvent` so the existing admin audit journal can show
registry-impacting actions.

### MeetingDetectionNonTargetRule

Server-managed denylist/suppression rule.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Primary key. |
| `workspace_id` | UUID nullable | Global or workspace rule. |
| `platform` | string | `macos`, `windows`, `browser`. |
| `rule_kind` | string | `bundle_id`, `bundle_prefix`, `display_name_token`, `category`. |
| `rule_value` | string | Safe rule value. |
| `reason_code` | string | `browser_bundle`, `audio_utility`, `system_service`, etc. |
| `created_by_user_id` | UUID nullable | Admin actor. |
| `created_at` | timestamptz | Audit timestamp. |
| `active` | bool | Whether clients should suppress. |

Rules are exported in registry metadata so clients suppress non-targets before
upload.

### MeetingDetectionTelemetryRateLimitBucket

Per-device rate limiting for telemetry.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Primary key. |
| `workspace_id` | UUID | Tenant scope. |
| `user_id` | UUID | User scope. |
| `device_id` | UUID | Device scope. |
| `bucket_key` | string | e.g. `daily_rollup` or `high_score_candidate`. |
| `window_started_at` | timestamptz | Window boundary. |
| `attempt_count` | int | Attempts in window. |
| `blocked_until` | timestamptz nullable | Backoff/limit state. |

## macOS Local Documents

### MeetingTargetRegistryCache

Path:

```text
~/Library/Application Support/GRAF/MeetingDetection/target-registry.json
```

Fields mirror `meeting-target-registry.schema.json`, plus local cache metadata:

- `downloadedAt`
- `etag`
- `source`: `remote_cache`
- `validationResult`

Invalid cache is quarantined and replaced by previous good cache or packaged
seed.

### Packaged Seed Registry

Path:

```text
apps/macos/RecApp/Resources/meeting-target-registry.seed.json
```

Generated from the reviewed registry seed and shipped with the app. It must
contain only `prompt_enabled` targets with verified runtime evidence and
`diagnostic_only`/manual targets for broader coverage.

### MeetingDetectionTelemetryRollupDocument

Path:

```text
~/Library/Application Support/GRAF/MeetingDetection/telemetry-rollups/YYYY-MM-DD.json
```

Fields follow `meeting-detection-telemetry.schema.json`. Raw unified-log lines
are never stored. Unknown app identity remains redacted unless the local
VKS-candidate filter allows `server_candidate_upload`.

### MeetingDetectionSettings

Local user/workspace settings cache:

- `detectionMode`: `disabled`, `detect_only`, `detect_and_ask`
- `telemetryUploadMode`: `automatic_candidate_upload`, `local_only`
- `targetScopedAutoRecord`: map from scoped identity to enabled/disabled
- `suppressionRules`: local skip/stop cooldowns

Workspace policy from server can narrow behavior but cannot disable compiled
safety gates.

## State Transitions

### Candidate Review

```text
new
  -> reviewing
  -> non_target
  -> merged
  -> diagnostic_only_draft
  -> validation_needed
  -> ready_for_prompt_review
  -> published
  -> disabled
```

`published` prompt-capable state requires separate registry publishing and QA
evidence. Telemetry alone cannot reach `prompt_enabled`.

### Registry Version

```text
draft -> published -> superseded
draft -> disabled
```

Only validated documents can publish. Publishing updates the remote registry
ETag.

## Retention And Deletion

- Local telemetry rollups retain 14 days or 1 MB, whichever comes first.
- Server telemetry batches retain bounded payloads for operational improvement;
  detailed retention period must be configured before production telemetry
  enablement.
- Candidate review items retain aggregate metadata and admin audit history.
- No meeting content is stored in detection telemetry. Deletion copy must not
  imply this removes third-party VKS app logs or OS logs outside GRAF control.

## Forbidden Content

Every server write path and local diagnostic/export path must reject or redact:

- raw unified-log lines;
- raw audio, transcript text, summary text, screen content, or meeting content;
- full private URLs, meeting IDs, passcodes, invite links, attendee emails,
  agenda text, private calendar titles;
- raw remote IP addresses, credentials, tokens, signed URLs, passwords, secret
  paths;
- full local app paths and user home paths.
