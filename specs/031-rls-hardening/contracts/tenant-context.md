# Contract: Tenant Context

## Purpose

Every request, worker, and maintenance operation that touches tenant-owned
backend rows must set explicit tenant context before database access. Database
policies fail closed when context is missing or mismatched.

## Context Kinds

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
- production smoke cleanup;
- backup/restore rehearsal;
- explicit operator diagnostics.

Forbidden operations:

- product UI bypass;
- product RBAC "see all tenant data" permission;
- dashboard/share/download/delete behavior;
- ad hoc unbounded data browsing.

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
- `app.maintenance_operation`

## Failure Contract

- Missing context: auth/context failure.
- Cross-tenant read: not found or empty.
- Cross-tenant write/delete: authorization failure.
- Maintenance operation not allowlisted: blocked maintenance result.
- Any failure evidence: metadata only.
