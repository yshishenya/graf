# Data Model: Retention And Deletion Execution

Feature: `018-retention-deletion-execution`
Date: 2026-06-16

This feature adds lifecycle state over meetings and artifacts accepted in
features 014-017. It does not add new private content storage.

## Existing Persistent Sources

- `meetings`: meeting identity, workspace, owner, device, title, status,
  processing status, visibility, share/download policy states.
- `registered_devices`: workspace device identity, platform, trust, and last
  seen state for local purge task targeting.
- `track_artifacts`: server-side audio artifact metadata and server-only object
  keys.
- `upload_sessions`, `upload_parts`, `temporary_upload_objects`,
  `manifest_snapshots`: upload and temporary object state to purge or mark.
- `processing_workflows`, `mediascribe_jobs`, `processing_results`,
  `processing_dependency_states`: workflow/dependency/result state.
- `transcript_segments`, `diarization_segments`: private content rows purged by
  active deletion.
- `meeting_share_grants`, `meeting_artifact_policies`,
  `meeting_egress_audit_events`, `export_packages`: access/share/egress state
  that must be blocked, purged, or retained as metadata-only audit evidence.

## Meeting Lifecycle Columns

Add columns to `meetings`:

- `deletion_state`: enum `none`, `requested`, `deleting`,
  `active_purge_complete`, `pending_backup_expiry`, `complete`,
  `retryable_failed`, `terminal_failed`, `policy_blocked`,
  `local_purge_unverified`.
- `deletion_requested_at`: datetime, nullable.
- `deleted_at`: datetime, nullable.
- `retention_delete_after`: datetime, nullable.
- `retention_policy_state`: enum `not_configured`, `active`, `unsafe`,
  `blocked`, `expired`.

Validation rules:

- `deletion_state != none` blocks normal review/share/download/export.
- `deleted_at` can be set only when active server purge is complete or a
  terminal explicit state explains what remains.
- Normal meeting lists hide `deleting` and `deleted` by default.

## New Persistent Entities

### MeetingDeletionRequest

Lifecycle request for whole-meeting deletion.

Fields:

- `id`: UUID.
- `workspace_id`: UUID, required.
- `meeting_id`: UUID, required.
- `requested_by_user_id`: UUID, nullable for system retention.
- `requested_by_device_id`: UUID, nullable.
- `request_source`: enum `owner`, `admin`, `retention_job`.
- `reason_code`: enum `user_request`, `retention_expired`,
  `policy_blocked`, `retry`.
- `confirmation_boundary`: string, required, bounded deletion copy.
- `state`: same top-level deletion lifecycle state.
- `policy_snapshot_id`: UUID, nullable.
- `created_at`, `accepted_at`, `completed_at`, `failed_at`: datetimes.
- `failure_reason`: safe string, nullable.
- `metadata_json`: metadata-only object.

Validation rules:

- One active request per `(workspace_id, meeting_id)` unless the previous
  request is complete or terminal.
- Request and lifecycle audit must be flushed before destructive action.
- `confirmation_boundary` must not claim universal erasure.

### MeetingDeletionArtifactState

Per-class lifecycle state for controlled, external, backup, local, and
post-egress classes.

Fields:

- `id`: UUID.
- `workspace_id`: UUID.
- `meeting_id`: UUID.
- `deletion_request_id`: UUID.
- `artifact_class`: enum `meeting_row`, `audio_object`, `transcript`,
  `diarization`, `notes_summary`, `export_package`, `share_grant`,
  `upload_temp`, `processing_workflow`, `mediascribe`, `langfuse`,
  `diagnostics`, `backup`, `local_desktop_buffer`, `post_egress_copy`,
  `search_index`.
- `control_scope`: enum `controlled`, `external`, `local_device`,
  `backup`, `post_egress`, `not_applicable`.
- `state`: enum `not_started`, `purge_requested`, `purged`,
  `metadata_retained`, `pending_expiry`, `delete_requested`,
  `delete_confirmed`, `delete_not_supported`, `unknown`, `not_applicable`,
  `retryable_failed`, `terminal_failed`, `local_pending`,
  `local_acknowledged`, `local_unreachable`, `local_expiry_relied_upon`.
- `safe_reason`: string, nullable.
- `attempt_count`: integer.
- `started_at`, `completed_at`, `next_retry_at`, `updated_at`: datetimes.
- `metadata_json`: metadata-only object.

Validation rules:

- `metadata_json` must not contain transcript text, summary text, storage keys,
  signed URLs, dependency payloads, local paths, credentials, or tokens.
- External dependency states can be `unknown` or `delete_not_supported` without
  blocking server purge completion, but reports must show that limitation.

### MeetingDeletionReport

Metadata-only verification report shown after deletion starts.

Fields:

- `id`: UUID.
- `workspace_id`: UUID.
- `meeting_id`: UUID.
- `deletion_request_id`: UUID.
- `overall_state`: top-level deletion lifecycle state.
- `summary_label`: safe display label.
- `bounded_copy`: safe product copy.
- `artifact_summary_json`: list of artifact-class summaries.
- `backup_state`: enum `pending_expiry`, `expiry_complete`,
  `crypto_erased`, `unsupported`, `unknown`, `not_applicable`.
- `local_purge_state`: enum `not_applicable`, `pending`, `acknowledged`,
  `unreachable`, `failed`, `local_expiry_relied_upon`.
- `external_dependency_state`: enum `not_applicable`, `unknown`,
  `unsupported`, `delete_requested`, `delete_confirmed`, `metadata_only`.
- `generated_at`, `updated_at`: datetimes.

Validation rules:

- Report remains accessible to owner/admin after private content is purged.
- Report may include safe title only if policy allows it after deletion;
  otherwise use generic meeting identity and timestamps.

### RetentionPolicySnapshot

Policy values used for an evaluation or deletion request.

Fields:

- `id`: UUID.
- `workspace_id`: UUID.
- `policy_source`: enum `deployment_default`, `workspace_default`,
  `test_fixture`.
- `meeting_delete_after_days`: integer, nullable.
- `backup_expiry_days`: integer, nullable.
- `local_buffer_expiry_days`: integer, nullable.
- `unsafe_reason`: string, nullable.
- `created_at`: datetime.
- `metadata_json`: metadata-only object.

Validation rules:

- Missing or unsafe policy fails closed and records a non-content reason.
- Snapshots are immutable after creation.

### LocalPurgeTask

Server-issued request for a registered desktop device to purge local meeting
buffers or package artifacts.

Fields:

- `id`: UUID.
- `workspace_id`: UUID.
- `meeting_id`: UUID.
- `deletion_request_id`: UUID.
- `device_id`: UUID.
- `task_type`: enum `purge_local_buffers`, `purge_local_exports`,
  `confirm_local_expiry`.
- `state`: enum `pending`, `claimed`, `acknowledged`, `failed`,
  `unreachable`, `expired`, `local_expiry_relied_upon`.
- `reason_code`: safe string, nullable.
- `created_at`, `claimed_at`, `acknowledged_at`, `expires_at`: datetimes.
- `metadata_json`: metadata-only object.

Validation rules:

- Ack payloads must not include local paths, filenames derived from private
  titles, transcript snippets, hashes of private files, or screenshots.
- Devices can acknowledge only tasks scoped to their workspace and device id.

### MeetingLifecycleAuditEvent

Metadata-only event for deletion, retention, local purge, and dependency
state transitions.

Fields:

- `id`: UUID.
- `workspace_id`: UUID.
- `meeting_id`: UUID, nullable for safe denied cases.
- `deletion_request_id`: UUID, nullable.
- `actor_user_id`: UUID, nullable.
- `device_id`: UUID, nullable.
- `event_type`: string.
- `outcome`: enum `accepted`, `denied`, `completed`, `failed`, `skipped`,
  `blocked`.
- `safe_reason`: string, nullable.
- `metadata_json`: metadata-only object.
- `created_at`: datetime.

Validation rules:

- Allowed metadata keys are limited to lifecycle state, artifact class, control
  scope, dependency name, policy source, outcome, attempt count, and safe reason.
- Audit write failure blocks destructive actions.

## View Models

### DeletionLifecycleState

Fields:

- `state`: deletion lifecycle enum.
- `label`: safe display label.
- `reason`: safe reason, nullable.
- `can_retry`: boolean.
- `can_view_report`: boolean.

### DeletionVerificationReportResponse

Fields:

- `meeting_id`: UUID.
- `request_id`: UUID.
- `overall_state`: deletion lifecycle enum.
- `bounded_copy`: string.
- `artifact_states`: list of artifact report rows.
- `local_purge`: summary state plus per-device rows.
- `backup`: backup expiry state and safe policy label.
- `dependencies`: MediaScribe, Langfuse, workflow/temp, diagnostics states.
- `post_egress_limits`: download/export/share-copy limit rows.
- `activity`: metadata-only lifecycle events.

### LocalPurgeTaskResponse

Fields:

- `tasks`: list of task id, meeting id, task type, safe reason, expiry time,
  and acknowledgement endpoint.

## Relationships

- `MeetingDeletionRequest.meeting_id` maps to `meetings.id`.
- `MeetingDeletionArtifactState.deletion_request_id` maps to
  `meeting_deletion_requests.id`.
- `MeetingDeletionReport.deletion_request_id` maps to the current request.
- `LocalPurgeTask.device_id` maps to `registered_devices.id`.
- `RetentionPolicySnapshot` is referenced by deletion requests and retention
  audit events.

## State Transitions

```text
MeetingDeletionRequest:
  requested -> deleting
  requested -> policy_blocked
  deleting -> active_purge_complete
  deleting -> retryable_failed
  deleting -> terminal_failed
  active_purge_complete -> pending_backup_expiry
  active_purge_complete -> local_purge_unverified
  pending_backup_expiry -> complete
  local_purge_unverified -> complete
  retryable_failed -> deleting

LocalPurgeTask:
  pending -> claimed
  pending -> unreachable
  claimed -> acknowledged
  claimed -> failed
  pending -> expired
  expired -> local_expiry_relied_upon
```

## Privacy And RLS

- New tables use `workspace_id` and tenant RLS policies equivalent to feature
  017, with maintenance context allowed for workers.
- Report and audit metadata must be generated through redaction helpers.
- Object keys may be read only inside server purge code and must not be stored
  in reports or audit metadata.
