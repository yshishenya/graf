# Contract: Tenant Context

## Purpose

Every request, worker, and maintenance operation that touches tenant-owned
backend rows must set explicit tenant context before database access. Database
policies fail closed when context is missing or mismatched.

## Context Kinds

All context kinds are fixed values. Unknown strings must fail before database
settings are applied.

### Request Context

Required fields:

- `organization_id`
- `workspace_id`
- `user_id`
- `device_id` when a registered desktop device is part of the operation
- `auth_session_id` when an auth session is available

Allowed use:

- FastAPI request handlers.
- Auth/session/device checks.
- Ingest/upload/meeting/status routes.

### Auth Public And Bootstrap Context

Allowed values:

- `auth_public`
- `auth_bootstrap`

Required fields:

- `workspace_id`
- `organization_id` when the workspace has been resolved
- `user_id` only after the auth bootstrap flow has identified or created the
  user

Allowed use:

- Public provider and consent reads for the requested workspace.
- Bounded callback/bootstrap operations for the current workspace.
- Creating a self-enrolled user only inside the resolved workspace
  organization.

Forbidden use:

- Content table access.
- Product/admin bypass.
- Organization-wide browsing without the current workspace bootstrap bound.

### Auth Lookup Context

Allowed values:

- `auth_session_lookup`
- `auth_callback_lookup`

Required fields:

- `auth_session_lookup`: session token hash only.
- `auth_callback_lookup`: callback state nonce only.

Allowed use:

- Finding one auth session by token hash.
- Finding one callback state by nonce.

Forbidden use:

- Maintenance operations.
- Meeting/content/processing table access.
- Unbounded user, organization, or workspace queries.

### Worker Context

Required fields:

- `organization_id`
- `workspace_id`
- `user_id` or internal automation identity
- operation name
- meeting or workflow identifier when the worker is meeting-scoped

Allowed use:

- Processing pickup.
- Processing status updates.
- MediaScribe result import.
- Metadata-only dependency/audit updates.

### Maintenance Context

Required fields:

- `context_kind=maintenance`
- fixed `maintenance_operation`
- actor or automation identity
- reason category
- target feature area

Allowed operations:

- migration verification;
- bounded creation of one deterministic synthetic production-smoke identity by
  the dedicated maintenance runtime;
- production smoke cleanup;
- backup/restore rehearsal;
- explicit operator diagnostics.

Forbidden operations:

- product UI bypass;
- product RBAC "see all tenant data" permission;
- dashboard/share/download/delete behavior;
- ad hoc unbounded data browsing.

`production_smoke_setup` is limited to the synthetic organization, workspace,
user, membership, and device derived from the current smoke run ID. AuthSession
issuance and upload continue under the ordinary exact request context; the
application runtime cannot use maintenance setup or cleanup operations.

## Database Session Contract

The implementation must provide a single helper for setting context on an
`AsyncSession` transaction.

Required behavior:

- Use transaction-local PostgreSQL settings.
- Clear settings automatically at transaction end.
- Reject missing required fields before tenant-owned queries run.
- Produce metadata-only evidence for missing, denied, and maintenance outcomes.
- Keep SQLite fallback behavior explicit: SQLite may validate helper calls but
  cannot satisfy PostgreSQL RLS acceptance.

## PostgreSQL Setting Names

Planned setting names:

- `app.organization_id`
- `app.workspace_id`
- `app.user_id`
- `app.device_id`
- `app.auth_session_id`
- `app.upload_session_id`
- `app.context_kind`
- `app.auth_session_token_hash`
- `app.auth_callback_state_nonce`
- `app.maintenance_operation`
- `app.maintenance_actor`
- `app.maintenance_reason`
- `app.maintenance_feature_area`

## Failure Contract

- Missing context: auth/context failure.
- Cross-tenant read: not found or empty.
- Cross-tenant write/delete: authorization failure.
- Maintenance operation not allowlisted: blocked maintenance result.
- Any failure evidence: metadata only.
