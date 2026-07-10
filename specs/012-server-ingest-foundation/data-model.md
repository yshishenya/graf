# Data Model: Server Ingest Foundation

## Entity Overview

### Organization

- `id`: UUID
- `slug`: stable tenant slug for admin/operator references
- `name`: display name
- `created_at`, `updated_at`

Relationships:

- Owns many workspaces.

Validation:

- `slug` is unique and immutable after creation.

### Workspace

- `id`: UUID
- `organization_id`: UUID
- `slug`: stable workspace slug within organization
- `name`
- `created_at`, `updated_at`

Relationships:

- Belongs to one organization.
- Owns meetings, devices, upload sessions, audit events, and object metadata.

Validation:

- `(organization_id, slug)` is unique.
- Every ingest request must resolve to exactly one authorized workspace.

### UserIdentity

Provider-neutral identity context required by 012. Provider implementation belongs to 013.

- `id`: UUID
- `organization_id`: UUID
- `external_subject`: stable subject from auth layer
- `display_name`
- `status`: `active`, `disabled`
- `created_at`, `updated_at`

Relationships:

- Has workspace memberships.
- Creates meetings and upload sessions.

Validation:

- Disabled users cannot create, upload, finalize, abort, or read sessions.

### WorkspaceMembership

- `workspace_id`: UUID
- `user_id`: UUID
- `role`: `owner`, `admin`, `member`
- `status`: `active`, `revoked`

Validation:

- Active membership is required for all 012 operations.

### RegisteredDevice

- `id`: UUID
- `workspace_id`: UUID
- `user_id`: UUID
- `device_public_id`: stable client-visible ID
- `platform`: `macos`
- `client_version`
- `status`: `active`, `revoked`
- `last_seen_at`
- `created_at`, `updated_at`

Relationships:

- Creates upload sessions for meetings.

Validation:

- Device must be active, belong to the request workspace, and match the authenticated user or an explicit workspace device policy.
- 012 does not define the desktop registration UX; it consumes the registered-device contract.

### Meeting

- `id`: UUID
- `workspace_id`: UUID
- `created_by_user_id`: UUID
- `device_id`: UUID
- `local_recording_id`: client-generated idempotency key for a finalized local recording
- `title`: optional
- `started_at`, `ended_at`: timestamps supplied by finalized local artifact
- `duration_seconds`
- `status`: `draft`, `uploading`, `ingested_pending_processing`, `degraded`, `failed`, `aborted`, `expired`
- `processing_status`: `not_submitted`, `pending_processing`
- `created_at`, `updated_at`

Relationships:

- Has one active upload session at a time.
- Has track artifacts after successful finalize.
- Has processing placeholder for later 015 workflow pickup.

Validation:

- `(workspace_id, created_by_user_id, local_recording_id)` is unique for all meeting records, including deleted records.
- `duration_seconds` must be positive and less than or equal to configured maximum.
- Meeting status must never claim transcription, summary, or dashboard readiness in 012.

### UploadSession

- `id`: UUID
- `meeting_id`: UUID
- `workspace_id`: UUID
- `device_id`: UUID
- `created_by_user_id`: UUID
- `upload_strategy`: `server_mediated`
- `status`: `pending`, `uploading`, `retrying`, `finalizing`, `finalized`, `degraded`, `failed`, `aborted`, `expired`
- `idempotency_key`
- `expected_tracks`: list of required track roles
- `max_package_bytes_snapshot`
- `max_track_bytes_snapshot`
- `expires_at`
- `created_at`, `updated_at`, `finalized_at`

Relationships:

- Has many upload parts/ranges.
- Produces track artifacts on finalize.

Validation:

- Only one non-terminal session per meeting.
- Session TTL and size limits are captured at creation so later config changes do not make status ambiguous.
- Terminal sessions cannot accept new parts.

### UploadPart

- `id`: UUID
- `upload_session_id`: UUID
- `track_role`: `microphone`, `system`, `manifest`
- `part_number`
- `byte_offset`
- `byte_length`
- `sha256`
- `storage_object_key`
- `status`: `accepted`, `conflict`, `superseded`
- `created_at`

Relationships:

- Belongs to one upload session.

Validation:

- `(upload_session_id, track_role, part_number)` is unique for accepted parts.
- Replaying the same part with matching byte length and checksum is idempotent.
- Replaying a part with conflicting checksum returns conflict and does not replace accepted bytes.

### TrackArtifact

- `id`: UUID
- `meeting_id`: UUID
- `workspace_id`: UUID
- `track_role`: `microphone`, `system`, `manifest`
- `codec`
- `sample_rate_hz`
- `channel_count`
- `duration_seconds`
- `byte_length`
- `sha256`
- `storage_object_key`
- `status`: `stored`, `quarantined`, `deleted`
- `created_at`, `updated_at`

Relationships:

- Belongs to a finalized meeting.

Validation:

- Required microphone and system tracks must be present for normal success.
- Manifest checksum must match client-supplied metadata.
- Object keys must be tenant/workspace/meeting scoped.

### IngestAuditEvent

- `id`: UUID
- `workspace_id`: UUID
- `meeting_id`: UUID, nullable until meeting creation succeeds
- `upload_session_id`: UUID, nullable
- `actor_user_id`: UUID
- `device_id`: UUID
- `event_type`: `meeting_created`, `session_created`, `part_accepted`, `part_conflict`, `finalize_started`, `finalized`, `degraded`, `failed`, `aborted`, `expired`, `access_denied`
- `metadata`: JSON object with safe metadata only
- `created_at`

Validation:

- Metadata must not include audio content, transcript text, bearer tokens, MinIO credentials, signed URLs, or raw secrets.

### ProcessingPlaceholder

- `id`: UUID
- `meeting_id`: UUID
- `workspace_id`: UUID
- `status`: `not_submitted`, `pending_processing`
- `workflow_id`: nullable and must remain null in 012
- `mediascribe_job_id`: nullable and must remain null in 012
- `created_at`, `updated_at`

Validation:

- 012 may create or update only placeholder statuses.
- Any non-null workflow/job identifier is out of scope for 012 and belongs to 015.

## State Transitions

### UploadSession

```text
pending
  -> uploading
  -> retrying
  -> uploading
  -> finalizing
  -> finalized

pending|uploading|retrying -> aborted
pending|uploading|retrying -> expired
uploading|retrying|finalizing -> failed
finalizing -> degraded
```

Rules:

- `finalized`, `aborted`, `expired`, `failed`, and `degraded` are terminal for part upload.
- `degraded` is allowed only when accepted data is safely stored but required completeness or metadata truth prevents normal processing readiness.

### Meeting

```text
draft -> uploading -> ingested_pending_processing
draft|uploading -> aborted
draft|uploading -> expired
uploading -> degraded
uploading -> failed
```

Rules:

- `ingested_pending_processing` means objects and metadata are durable enough for future 015 processing, not that processing started.
- Meeting status must be tenant-scoped and visible only to authorized users/devices.

### ProcessingPlaceholder

```text
not_submitted -> pending_processing
```

Rules:

- In 012, `pending_processing` is a pickup marker only.
- No Temporal workflow ID and no MediaScribe job ID are written in 012.

## Tenant Isolation Rules

- Every table that stores meeting, upload, object, or audit data includes `workspace_id`.
- Application authorization checks must verify organization, workspace, user membership, and device status before reads or writes.
- Cross-tenant reads return not found or forbidden according to the API contract without revealing existence of foreign resources.
- PostgreSQL RLS is deferred as `RLS-hardening`; it must be added before broad external customer exposure or explicitly risk-accepted.

## Deletion Truth Hooks

- Track artifacts record object keys and statuses so later deletion can state which owner-controlled objects were deleted or retained.
- Audit events record lifecycle metadata without content.
- Processing placeholders preserve the fact that 012 has not sent data to MediaScribe or Temporal.
- Later deletion work must include MinIO objects, Postgres metadata, local buffers, backups, Temporal payloads, MediaScribe, Langfuse, and diagnostics in user-facing truth copy.
