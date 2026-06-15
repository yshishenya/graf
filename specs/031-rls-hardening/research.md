# Research: Backend Tenant Isolation RLS Hardening

## Decision: Use PostgreSQL RLS With Transaction-Local Tenant Settings

Use PostgreSQL row-level security policies driven by transaction-local settings
such as `app.organization_id`, `app.workspace_id`, `app.user_id`,
`app.device_id`, `app.context_kind`, and `app.maintenance_operation`.

**Rationale**: Existing application-level authorization remains necessary, but
RLS catches missing ORM predicates and future query mistakes at the database
boundary. `SET LOCAL` keeps context scoped to a transaction and reduces leakage
risk across pooled connections.

**Alternatives considered**:

- ORM-only filters: rejected because the feature exists to protect against
  missed application predicates.
- Per-tenant schemas: rejected as too heavy for the current MVP schema and not
  aligned with existing migrations.
- Separate database roles per workspace: rejected because workspace count and
  worker contexts would make role management brittle for the MVP.

## Decision: Wrap `current_setting` In Small SQL Helper Functions

Add migration-managed helper functions for current tenant fields and
maintenance checks, using `current_setting('name', true)` so missing settings
fail closed instead of raising unhandled cast errors.

**Rationale**: Policies stay readable, missing context can be tested
consistently, and the implementation can distinguish no-context, mismatched
context, and approved maintenance context.

**Alternatives considered**:

- Inline `current_setting` in every policy: rejected because it duplicates
  casting and missing-value handling.
- Store tenant context in a temporary table: rejected because it is more complex
  with async sessions and pooled connections.

## Decision: Classify Tables By Isolation Shape Before Writing Policies

Use table classes:

- Direct workspace scope: tables with `workspace_id`.
- Inherited workspace scope: tables that inherit through a parent row, such as
  `upload_parts` through `upload_sessions`.
- Organization scope: organizations, workspaces, and user identities bounded by
  explicit membership or approved organization role.
- Identity-link scope: external identities, auth session bindings, and provider
  link rows that inherit from user/session/workspace records.
- Maintenance context: fixed allowlisted operational paths only.

**Rationale**: One generic `workspace_id` policy would miss inherited rows and
identity-link tables. The matrix lets implementation and review verify every
accepted backend table.

**Alternatives considered**:

- Protect only meeting-content tables first: rejected by clarification because
  accepted scope includes auth/session/device/audit/dependency tables.
- Defer identity/session tables: rejected because weak identity isolation can
  undermine meeting isolation.

## Decision: Keep Maintenance Context Outside Product RBAC

Approved maintenance context is an operator/internal-job context, not a product
admin permission. It must be fixed, allowlisted, metadata-logged, and bounded
to operations such as migration verification, smoke cleanup, backup/restore
rehearsal, or explicit diagnostics.

**Rationale**: Product admins should not get a "see all tenant data" switch.
Operational maintenance still needs controlled paths for migrations and smoke
cleanup.

**Alternatives considered**:

- Product RBAC bypass: rejected because it creates a dangerous user-facing
  privilege and contradicts the clarified spec.
- No maintenance context at all: rejected because migrations, smoke cleanup,
  and restore validation need bounded non-request access.

## Decision: Require PostgreSQL Probe Tests For Acceptance

Keep SQLite/local tests for route behavior and faster feedback, but require a
PostgreSQL-backed probe suite for RLS policies and migration validation.

**Rationale**: SQLite cannot enforce PostgreSQL RLS. Accepting this feature
without PostgreSQL probes would leave the main security claim unproven.

**Alternatives considered**:

- Mock RLS in Python: rejected because it tests the mock, not PostgreSQL.
- Production-only validation: rejected because the feature must not touch live
  production enforcement without a separate decision.

## Decision: Preserve Privacy-Preserving API Access Outcomes

Cross-tenant reads return not found or an empty result without confirming a
foreign row exists. Cross-tenant writes/deletes return authorization failure.
Missing tenant context returns an authentication or tenant-context failure.

**Rationale**: Reads should not allow tenant enumeration. Mutations should be
clear enough for clients/operators to diagnose a forbidden operation. Missing
context is a separate implementation/auth wiring failure.

**Alternatives considered**:

- Always return authorization failure: rejected because it can reveal that a
  guessed foreign identifier exists.
- Let each route decide later: rejected because inconsistent behavior would
  weaken future dashboard/share/delete contracts.

## Decision: Live Production Enforcement Is A Separate Operator Decision

Implementation can create code, migrations, validation evidence, and runbooks,
but hard enforcement on live production remains off until a separate explicit
operator decision after gates pass.

**Rationale**: RLS can break legitimate paths if context propagation is wrong.
The safe product effect is a prepared, proven hardening layer without accidental
production outage.

**Alternatives considered**:

- Enable on production automatically after local tests: rejected because it
  skips the clarified production gate.
- Audit-only forever: rejected because the feature's product value is real
  fail-closed isolation.
