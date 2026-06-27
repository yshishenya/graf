# Admin API Contract

This contract describes the server JSON/action surface for the workspace admin
panel. It is intentionally separate from the existing cabinet API while reusing
cabinet/deletion/auth services behind the boundary.

## Common Rules

- Prefix: `/api/v1/admin`.
- Authentication: current web session or accepted API auth used by the existing
  server.
- Authorization: active `owner` or `admin` workspace membership for all routes
  unless the route explicitly handles invitation completion after provider
  login.
- Workspace scope: every response and action is scoped to the actor workspace.
- Error format: existing product problem response shape.
- Response safety: no raw audio, transcript text, private meeting content,
  storage object keys, signed URLs, local file paths, tokens, passwords, or
  secrets.
- Sensitive actions: role/state changes, invitation creation/revocation, file
  review/download/export/deletion, and denied sensitive attempts must write
  metadata-only audit evidence or fail closed.

## Overview

### GET `/api/v1/admin/overview`

Returns workspace health summary.

Response fields:

- `workspace_id`
- `user_counts`: active, pending, inactive, blocked, revoked
- `usage_summary`: selected period, recording minutes, storage bytes,
  processing jobs, quota risk, freshness
- `file_summary`: server-known meetings, unavailable/deleting/problem states
- `metrics_summary`: available metric families and freshness
- `recent_audit`: latest metadata-only journal entries

Errors:

- `401 unauthenticated`
- `403 admin_forbidden`
- `503 admin_store_unavailable`

## Users And Invitations

### GET `/api/v1/admin/users`

Query:

- `status`
- `role`
- `search`
- `limit` from 1 to 100
- `cursor`

Returns existing members and pending invitations.

### GET `/api/v1/admin/users/{user_id}`

Returns role, status, devices, sessions, files, usage contribution, and recent
audit activity for one workspace user.

Errors:

- `404 admin_user_not_found` when the user is not in the actor workspace.

### POST `/api/v1/admin/invitations`

Request:

- `target_contact`
- `target_provider` optional
- `invited_role`: `owner`, `admin`, or `member`
- `expires_at` optional

Rules:

- Admin actor may create only `member` invitations.
- Owner actor may create Owner/Admin/Member invitations if last-owner safety is
  preserved.
- Duplicate active pending invitation for the same target in a workspace is a
  conflict.

Responses:

- `201` with invitation summary and pending state.

Errors:

- `403 admin_role_authority_forbidden`
- `409 invitation_duplicate_active`
- `422 invalid_invitation_target`
- `503 admin_audit_unavailable`

### POST `/api/v1/admin/invitations/{invitation_id}/revoke`

Request:

- `reason_code` or safe short reason

Rules:

- Actor must still be active Owner/Admin.
- Revocation writes metadata-only audit evidence.

### POST `/api/v1/admin/invitations/{invitation_id}/complete`

Used after allowed provider login completes.

Rules:

- Invitation must be pending and unexpired.
- Login identity must match invitation target.
- Completion creates workspace membership with the invited role when the login
  identity is not yet a member.
- If the login identity already has a workspace membership, completion links
  the invitation but does not change the existing role or status; role/status
  changes stay explicit membership-management actions.
- Completion links invitation to the completed identity and membership.

Errors:

- `404 invitation_not_found`
- `409 invitation_expired`
- `409 invitation_revoked`
- `409 invitation_already_completed`
- `403 invitation_identity_mismatch`

### PATCH `/api/v1/admin/users/{user_id}/membership`

Request:

- `role` optional: `owner`, `admin`, `member`
- `status` optional: `active`, `inactive`, `blocked`, `revoked`
- `reason_code` optional

Rules:

- Owner/Admin actions are rechecked at submission time.
- Admin actor can manage Members only.
- Owner actor can manage roles/statuses if the workspace keeps an active Owner.
- Last active Owner cannot be downgraded, deactivated, blocked, revoked, or
  removed.

Errors:

- `403 admin_role_authority_forbidden`
- `409 last_owner_protection`
- `503 admin_audit_unavailable`

## Files And Meetings

### GET `/api/v1/admin/files`

Query:

- `owner_user_id`
- `type`
- `date_from`
- `date_to`
- `processing_state`
- `deletion_state`
- `retention_state`
- `min_size`
- `max_size`
- `min_duration`
- `max_duration`
- `limit` from 1 to 100
- `cursor`

Returns metadata-safe meeting/file rows for the actor workspace.

### GET `/api/v1/admin/files/{meeting_id}`

Returns admin review summary and available actions for a server-known meeting
in the actor workspace.

Rules:

- Same-workspace active Owner/Admin can open non-owned meetings.
- Missing artifacts, deleting/deleted state, retention/lifecycle blocks, and
  post-egress limits are truthful unavailable states, not permission bypasses.

### POST `/api/v1/admin/files/{meeting_id}/review-access`

Records metadata-only audit evidence before returning a review handoff or
server-rendered review state.

### GET `/api/v1/admin/files/{meeting_id}/downloads/{artifact_class}`

Downloads an allowed artifact through the existing egress path.

Rules:

- Must reuse existing egress policy and audit behavior.
- Must not expose storage identifiers or signed URLs.

### POST `/api/v1/admin/files/{meeting_id}/exports`

Starts an allowed export through existing egress/export behavior.

### POST `/api/v1/admin/files/{meeting_id}/deletion-requests`

Request:

- `confirm`: true
- `reason_code` or safe short reason

Rules:

- Whole-meeting deletion everywhere `2brain Rec` controls.
- Normal destructive confirmation plus required reason.
- No typed phrase required.
- Reuse existing deletion service and bounded deletion report.

Errors:

- `409 deletion_already_active`
- `409 deletion_blocked_by_policy`
- `503 deletion_audit_unavailable`
- `503 deletion_storage_unavailable`

### GET `/api/v1/admin/files/{meeting_id}/deletion-report`

Returns bounded deletion report. The report distinguishes controlled purge,
local desktop purge, backup expiry, external dependency limits, diagnostics,
and post-egress limits.

## Usage And Quotas

### GET `/api/v1/admin/usage`

Query:

- `date_from`
- `date_to`
- `group_by`: `workspace` or `user`
- `limit` from 1 to 100

Returns recording minutes, storage bytes, processing jobs, top consumers,
freshness, and quota risk.

Rules:

- Missing quota policy is displayed as not configured.
- V1 does not edit limits.
- Financial balance, invoices, debt, payments, credits, tariffs, and billing
  integrations are not returned.

### GET `/api/v1/admin/quota-policy`

Returns configured, partially configured, display-only, or not configured
limits for minutes, storage, and processing jobs.

No mutation route exists in v1.

## Metrics

### GET `/api/v1/admin/metrics`

Query:

- `family`: optional `adoption`, `usage`, `funnel`, `reliability`, `governance`
- `date_from`
- `date_to`

Returns source-backed KPI cards with:

- metric id
- label
- definition
- denominator
- source category
- date window
- freshness state
- value
- drill-down path

Rules:

- No fake or sample-only production numbers.
- Current or lagging periods are marked incomplete.
- Unavailable source-backed metrics are absent or explicitly unavailable.

## Audit Journal

### GET `/api/v1/admin/audit`

Query:

- `date_from`
- `date_to`
- `user_id`
- `action`
- `object_kind`
- `object_id`
- `outcome`
- `limit` from 1 to 100
- `cursor`

Returns normalized product audit journal entries across auth, admin actions,
egress, deletion, quota views, and metric/admin sensitive events.

Rules:

- Metadata-only details.
- Deleted/private objects display safe unavailable/deleted labels.
- The journal remains the admin-facing product accountability source even if a
  future export to owner-controlled observability/log systems is added.
