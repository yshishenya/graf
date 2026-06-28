# Data Model: Workspace Admin Panel

## Existing Entities Reused

- `UserIdentity`: authenticated product identity with status.
- `WorkspaceMembership`: workspace role and membership status.
- `RegisteredDevice`: device/session administration context.
- `Meeting`, `MediaRevision`, `ProcessingWorkflow`, `ProcessingJob`,
  `ProcessingResult`, `MeetingOutcomeSet`: source data for files, processing,
  usage, and funnel metrics.
- `MeetingShareGrant`, `MeetingEgressAuditEvent`: existing access and egress
  accountability.
- `MeetingDeletionRequest`, `MeetingDeletionArtifactState`,
  `MeetingDeletionReport`, `RetentionPolicySnapshot`, `LocalPurgeTask`,
  `MeetingLifecycleAuditEvent`: deletion truth and lifecycle accounting.
- `AuthAuditEvent`: provider login, session, device, and auth-action audit
  source.

## New Or Extended Entities

### WorkspaceInvitation

Represents a workspace user invite/onboarding request before the target becomes
an active member.

| Field | Notes |
|-------|-------|
| `id` | Stable UUID primary key. |
| `workspace_id` | Tenant boundary. Required for RLS. |
| `target_contact` | Normalized email/handle/login target used for completion matching. |
| `target_provider` | Optional provider constraint when invite is provider-specific. |
| `invited_role` | `owner`, `admin`, or `member`; Admin-created invites can only use `member`. |
| `status` | `pending`, `completed`, `expired`, or `revoked`. |
| `source` | `admin` in v1; future-safe for referral source without referral rewards logic. |
| `created_by_user_id` | Actor who created the invitation. |
| `created_at` | Creation timestamp. |
| `expires_at` | Expiry timestamp. |
| `completed_by_user_id` | Identity that completed login, when completed. |
| `completed_membership_id` | Linked membership after completion. |
| `completed_at` | Completion timestamp. |
| `revoked_by_user_id` | Actor who revoked the invite, when revoked. |
| `revoked_at` | Revocation timestamp. |
| `revocation_reason` | Safe reason code or short safe reason. |
| `metadata_json` | Metadata-only, no tokens, private content, signed URLs, or local paths. |

Validation:

- One active pending invitation per `workspace_id + target_contact`.
- Completion requires status `pending`, unexpired invite, allowed provider
  login, target identity match, and valid invited role.
- Completion creates membership only after login succeeds when the identity is
  not yet a workspace member.
- If the identity already has workspace membership, completion links the
  invitation but does not change the existing role or status.
- Admin-created invitations grant `member` only.
- Owner-created invitations can grant `owner`, `admin`, or `member` only if the
  workspace keeps at least one active Owner.

### WorkspaceQuotaPolicy

Read-only display source for workspace quota/limit state in v1.

| Field | Notes |
|-------|-------|
| `id` | Stable UUID primary key. |
| `workspace_id` | Tenant boundary. Required for RLS. |
| `recording_minutes_limit` | Nullable. Null means not configured. |
| `storage_bytes_limit` | Nullable. Null means not configured. |
| `processing_jobs_limit` | Nullable. Null means not configured. |
| `policy_source` | Safe label such as `seed`, `deployment_config`, or `manual_external`. |
| `status` | `configured`, `partially_configured`, `not_configured`, or `display_only`. |
| `effective_from` | Start timestamp or date. |
| `updated_at` | Last update timestamp. |

Validation:

- V1 admin routes may read but must not mutate quota policy.
- Missing limits must be displayed as not configured, not fabricated.
- Financial fields are not part of this entity.

### WorkspaceUsageDaily

Workspace-level daily rollup for source-backed usage and quota monitoring.

| Field | Notes |
|-------|-------|
| `workspace_id` | Tenant boundary. Required for RLS. |
| `usage_date` | UTC date bucket unless a later task defines workspace timezone. |
| `recording_minutes` | Aggregated accepted/server-known recording duration. |
| `storage_bytes` | Aggregated server-owned artifact bytes where available. |
| `processing_jobs` | Count of processing jobs in the period. |
| `recording_count` | Count of server-known meetings/recordings. |
| `accepted_count` | Count accepted into server custody. |
| `failed_count` | Failed upload/processing count. |
| `deleted_count` | Meetings in deletion/deleted lifecycle during the period. |
| `freshness_state` | `fresh`, `lagging`, `incomplete`, or `unknown`. |
| `source_cutoff_at` | Latest source timestamp included. |

Validation:

- Rollups must reconcile to source tables within documented aggregation
  tolerance.
- Current-day/current-period data can be marked incomplete.

### UserUsageDaily

User-level daily rollup for top consumers and user detail usage contribution.

| Field | Notes |
|-------|-------|
| `workspace_id` | Tenant boundary. Required for RLS. |
| `user_id` | Workspace user identity. |
| `usage_date` | Date bucket aligned with `WorkspaceUsageDaily`. |
| `recording_minutes` | User-owned recording minutes. |
| `storage_bytes` | User-owned storage contribution where available. |
| `processing_jobs` | User-owned processing job count. |
| `file_count` | Server-known meetings/files owned by the user. |
| `freshness_state` | `fresh`, `lagging`, `incomplete`, or `unknown`. |
| `source_cutoff_at` | Latest source timestamp included. |

Validation:

- User rows must always be scoped by workspace and not leak cross-workspace
  identities.
- Unknown owner or missing membership must display as unavailable/stale rather
  than being assigned to the current admin.

### AdminAuditEvent

Admin-specific metadata-only audit event for actions not already covered by
auth, egress, deletion, ingest, or processing audit sources.

| Field | Notes |
|-------|-------|
| `id` | Stable UUID primary key. |
| `workspace_id` | Tenant boundary. Required for RLS. |
| `actor_user_id` | User who attempted the action, nullable for unauthenticated denied attempts when safe. |
| `actor_role` | Role at action time. |
| `action` | Safe action code such as `invite_created`, `role_change_denied`, `quota_viewed`. |
| `target_kind` | `user`, `invitation`, `meeting`, `quota`, `metric`, `audit`, or `admin_page`. |
| `target_id` | UUID/string target identifier when safe. |
| `outcome` | `allowed`, `denied`, `failed`, or `completed`. |
| `reason_code` | Safe reason code for denial/failure/destructive reason. |
| `source_table` | Optional source table for normalized journal back-reference. |
| `source_event_id` | Optional source event id for normalized journal back-reference. |
| `metadata_json` | Metadata-only safe details. No private content. |
| `created_at` | Event timestamp. |

Validation:

- Sensitive admin actions fail closed if the required event cannot be written.
- Audit entries must not contain raw audio, transcript text, meeting content,
  object keys, signed URLs, tokens, secrets, or local paths.
- Audit evidence required for accountability may survive meeting deletion, but
  only as metadata-only identifiers, action codes, timestamps, outcome, actor,
  target kind/id, and safe reasons.
- Admin UI must not allow normal product users to alter or delete audit history.

### AdminAuditJournalEntry

Read model, not necessarily a stored table. It normalizes existing and new audit
sources for the admin product journal.

Fields:

- `event_id`
- `source`
- `workspace_id`
- `actor_user_id`
- `actor_label`
- `action`
- `object_kind`
- `object_id`
- `outcome`
- `reason_code`
- `created_at`
- `metadata_safe_summary`
- `drill_down_path`

Validation:

- Journal filters: period, user, action, object, outcome.
- Entries with deleted/private objects must show safe unavailable/deleted state
  rather than private content.
- If an underlying source is unavailable, the journal must report incomplete
  freshness rather than backfilling fake data.

## Permission Concepts

### AdminPermissionDecision

Computed at render/action time. Inputs:

- request authentication state;
- active workspace membership;
- actor role;
- target workspace;
- action type;
- target role/status when user management is involved;
- last-owner safety check when Owner authority can be changed.

Outcomes:

- `allowed`
- `denied_unauthenticated`
- `denied_member`
- `denied_cross_workspace`
- `denied_admin_cannot_manage_owner_admin`
- `denied_last_owner`
- `denied_inactive_membership`
- `denied_audit_unavailable`

### AdminFileAccessDecision

Computed before file review/download/export/deletion.

Inputs:

- active Owner/Admin in target workspace;
- target meeting belongs to same workspace;
- artifact/lifecycle/egress/deletion state from existing services;
- audit persistence state.

Outcomes:

- `allowed`
- `denied_cross_workspace`
- `denied_not_admin`
- `unavailable_missing_artifact`
- `unavailable_deletion_active`
- `unavailable_retention_or_lifecycle_block`
- `unavailable_post_egress_limit`
- `denied_audit_unavailable`

## State Transitions

### Invitation

```text
pending -> completed
pending -> expired
pending -> revoked
expired -> pending      # only by creating a new invite record
revoked -> pending      # only by creating a new invite record
completed -> terminal
```

### Membership Role/Status

- Owner can grant/revoke Owner/Admin/Member authority if the workspace keeps at
  least one active Owner.
- Admin can manage Members within policy, but cannot grant or revoke Owner/Admin
  authority.
- Member cannot access admin pages or actions.
- Last active Owner cannot be removed, downgraded, blocked, revoked, or
  deactivated.

### Admin Deletion

Admin deletion reuses whole-meeting deletion lifecycle:

```text
available -> confirmation_with_reason -> deleting -> report states
```

No typed phrase is required in v1. The reason must be stored as a safe reason
code or safe short reason. The report must preserve deletion truth and
post-egress limits.

## Data Retention And Privacy Notes

- Product audit metadata may outlive meeting deletion for accountability.
- Audit metadata must not preserve raw meeting title/content when that would
  retain private meeting content after deletion. Use safe identifiers and
  object kind labels.
- Usage rollups are aggregate metadata and must remain workspace-scoped.
- No external log/audit platform receives admin data in v1.
