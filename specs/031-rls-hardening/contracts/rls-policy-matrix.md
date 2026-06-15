# Contract: RLS Policy Matrix

## Policy Requirements

All tenant-owned tables from accepted backend slices must be covered by a
PostgreSQL RLS policy or an explicitly documented inherited policy.

Global rules:

- Enable RLS on every covered table.
- Force RLS where table ownership could otherwise bypass policies.
- Missing context denies or returns no rows.
- Same-tenant request/worker context can read or mutate only its own scope.
- Approved maintenance context is fixed, allowlisted, and metadata logged.
- Policies do not expose transcript text, raw audio, secrets, signed URLs, or
  credential paths in errors or evidence.

## Direct Workspace Tables

Policy shape:

```text
workspace_id = current_workspace_id()
OR approved_maintenance_context(operation)
```

Tables:

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

## Inherited Workspace Tables

Policy shape:

```text
EXISTS parent row visible to current context
OR approved_maintenance_context(operation)
```

Tables:

- `upload_parts` through `upload_sessions`.
- `auth_session_device_bindings` through `auth_sessions` and
  `registered_devices`.
- `external_identities` through `user_identities` plus workspace membership.

## Organization Tables

Policy shape:

```text
organization_id = current_organization_id()
AND membership or approved organization role exists
OR approved_maintenance_context(operation)
```

Tables:

- `organizations`
- `user_identities`

## Mutation Rules

- Insert policies must require new rows to match current tenant context.
- Update policies must require both existing row visibility and new row scope to
  remain within current tenant context.
- Delete policies must require current tenant context or approved maintenance
  context.
- Cross-tenant write/delete probes must fail in 100% of validation runs.

## Coverage Evidence

Implementation must produce a coverage matrix that lists every accepted
tenant-owned table and one of:

- direct workspace policy applied;
- inherited workspace policy applied;
- organization policy applied;
- maintenance-only policy applied;
- explicitly not tenant-owned with rationale.

No current tenant-owned backend table may be left unclassified.
