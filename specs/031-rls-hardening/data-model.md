# Data Model: Backend Tenant Isolation RLS Hardening

## Tenant Context

Represents the active database access scope.

Fields:

- `organization_id`: UUID for the active organization.
- `workspace_id`: UUID for the active workspace when the operation is
  workspace-scoped.
- `user_id`: UUID for the authenticated user or operator automation identity.
- `device_id`: UUID for the registered device when applicable.
- `auth_session_id`: UUID for the auth session when applicable.
- `upload_session_id`: UUID for upload-scoped operations when applicable.
- `context_kind`: one of `request`, `worker`, `maintenance`.
- `maintenance_operation`: fixed allowlisted operation name for maintenance
  context.

Validation rules:

- Missing tenant context fails closed.
- Stale or revoked session/device context fails before tenant-owned rows are
  read or mutated.
- Client-supplied titles, filenames, request bodies, and guessed identifiers do
  not define tenant context.
- Maintenance context is outside product UI and cannot be granted through
  product RBAC.

## Access Outcome

API-facing result category for tenant-isolation decisions.

Values:

- `same_tenant_success`
- `cross_tenant_read_not_found_or_empty`
- `cross_tenant_mutation_forbidden`
- `missing_context_auth_or_context_error`
- `approved_maintenance_result`
- `blocked_maintenance_result`

Validation rules:

- Cross-tenant reads do not disclose whether a foreign row exists.
- Cross-tenant writes and deletes produce an authorization failure.
- Missing tenant context is not reported as a successful empty result.
- Evidence for denied outcomes is metadata-only.

## Hardening Evidence

Metadata-only proof that rollout and access gates were evaluated.

Fields:

- `environment`: `local`, `postgres_test`, `production_like`, or `live_production`.
- `feature_area`: auth, ingest, upload, meeting, processing, transcript, audit,
  dependency, migration, backup, restore, smoke cleanup, or diagnostics.
- `operation_name`: request route, worker operation, migration check, or
  maintenance operation name.
- `actor_or_automation`: user/operator/automation identifier without secrets.
- `context_kind`: request, worker, or maintenance.
- `reason_category`: same tenant, cross tenant, missing context, stale context,
  revoked context, maintenance allowed, or maintenance blocked.
- `outcome`: pass, blocked, halt, rollback, or manual investigation.
- `created_at`: timestamp.

Content restrictions:

- No raw audio.
- No transcript text.
- No credentials, tokens, signed URLs, passwords, or live secret paths.
- No customer meeting content in logs, traces, diagnostics, or spec evidence.

## Table Isolation Classifications

### Direct Workspace Scope

Rows contain `workspace_id` and must match active workspace context unless an
approved maintenance context applies.

- `workspaces`
- `workspace_memberships`
- `registered_devices`
- `workspace_auth_policies`
- `auth_sessions`
- `workspace_provider_link_states`
- `auth_callback_states`
- `auth_audit_events`
- `workspace_consent_copy`
- `meetings`
- `upload_sessions`
- `temporary_upload_objects`
- `track_artifacts`
- `manifest_snapshots`
- `ingest_audit_events`
- `processing_placeholders`
- `processing_workflows`
- `mediascribe_jobs`
- `processing_results`
- `transcript_segments`
- `diarization_segments`
- `processing_audit_events`
- `processing_dependency_states`

### Inherited Workspace Scope

Rows do not carry a direct workspace column or require parent consistency
checks.

- `upload_parts`: inherits workspace through `upload_sessions`.
- `auth_session_device_bindings`: inherits through `auth_sessions` and
  `registered_devices`.
- `external_identities`: inherits organization/user visibility through
  `user_identities` and membership.

### Organization Scope

Rows are organization-owned and visible only through explicit membership or
approved organization-level context.

- `organizations`
- `user_identities`

### Future Table Requirement

Every new tenant-owned table must declare:

- isolation class;
- owner column or parent relationship;
- allowed context kinds;
- read access outcome;
- mutation access outcome;
- metadata-only evidence behavior.

No future tenant-owned table may merge without this classification.

## State Transitions

Tenant context:

```text
unset -> request_context -> cleared_at_transaction_end
unset -> worker_context -> cleared_at_transaction_end
unset -> maintenance_context -> cleared_at_transaction_end
```

Rollout:

```text
draft_migration -> local_validation -> postgres_validation -> production_like_validation
production_like_validation -> ready_for_operator_decision
ready_for_operator_decision -> live_enforcement_enabled (separate explicit decision only)
any_validation_failure -> halt_or_rollback
```

## Relationships

- `Tenant Context.workspace_id` constrains direct workspace tables.
- `Tenant Context.organization_id` constrains organization and identity rows.
- `Tenant Context.user_id` constrains owner/member identity rules.
- Inherited rows must join to parent tables without bypassing parent RLS.
- Maintenance context may bypass ordinary tenant matching only for allowlisted
  operations and must produce hardening evidence.
