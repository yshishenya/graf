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
- `auth_rate_limit_buckets`
- `workspace_consent_copy`
- `meetings`
- `media_revisions`
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
- `meeting_share_grants`
- `meeting_artifact_policies`
- `meeting_egress_audit_events`
- `export_packages`
- `meeting_deletion_requests`
- `meeting_deletion_artifact_states`
- `meeting_deletion_reports`
- `retention_policy_snapshots`
- `local_purge_tasks`
- `meeting_lifecycle_audit_events`
- `dispatch_intents`
- `meeting_deletion_fences`
- `meeting_purge_journal`
- `meeting_outcome_sets`
- `meeting_outcome_items`
- `meeting_outcome_generation_attempts`
- `meeting_summary_slots`
- `summary_templates`
- `generation_calls`
- `meeting_share_invitations`
- `meeting_share_rate_limit_buckets`
- `calendar_sources`
- `calendar_credential_envelopes`
- `external_calendars`
- `calendar_event_snapshots`
- `calendar_participants`
- `conference_link_candidates`
- `recording_calendar_match_attempts`
- `recording_calendar_context_links`
- `calendar_reminder_states`
- `calendar_settings_preferences`
- `calendar_audit_events`
- `support_incidents`
- `support_incident_rate_limit_buckets`
- `workspace_join_offers`
- `workspace_quota_policies`
- `workspace_usage_daily`
- `user_usage_daily`
- `admin_audit_events`
- `meeting_target_registry_versions`
- `meeting_detection_telemetry_batches`
- `meeting_detection_target_health_rollups`
- `meeting_detection_candidates`
- `meeting_detection_review_actions`
- `meeting_detection_non_target_rules`
- `meeting_detection_telemetry_rate_limit_buckets`
- `playback_normalization_jobs`
- `playback_normalization_attempts`
- `playback_backfill_runs`
- `meeting_speaker_names`

## Billing And Account Tables

Billing and account tables added after the original RLS baseline remain in the
same authoritative production inventory:

- `workspace_subscriptions`
- `trial_activations`
- `billing_operations`
- `billing_invoices`
- `billing_payment_methods`
- `billing_entitlement_grants`
- `observed_provider_refunds`
- `free_usage_windows`
- `usage_reservations`
- `usage_ledger_entries`
- `storage_reservations`
- `time_credit_ledger_entries`
- `billing_audit_events`
- `billing_notification_deliveries`
- `billing_webhook_events`
- `referral_links`
- `referral_attributions`
- `fair_use_reviews`
- `promotion_redemptions`
- `account_closure_requests`

`billing_notification_preferences` is user-scoped and permits only the current
user or approved maintenance context. `billing_webhook_events` has an explicit
auth-public workspace binding policy. Their rows are still included in
`RLS_COVERED_TABLES` and must be enabled and forced in production.

`fair_use_reviews` is metadata-only. The affected user (or the selected
workspace owner) may read their scoped review, while worker/maintenance
contexts create and resolve review rows. Affected users may only submit the
CSRF-protected appeal transition; evidence references and meeting content never
cross this policy boundary.

Controlled global tables are also covered:

- `billing_plan_versions`
- `billing_launch_gates`
- `promotion_campaigns`

They permit only the documented request/worker or approved maintenance
contexts; they never provide an end-user mutation path for provider secrets or
raw payloads.

`generation_calls` deliberately has no request-context policy. It is visible to
the matching workspace worker and approved maintenance contexts only, so the
retained plaintext model-call ledger cannot become an end-user data surface.

## Maintenance-Only Global Tables

Policy shape:

```text
approved_maintenance_context(operation)
```

Tables:

- `prompt_optimization_runs`
- `prompt_optimization_call_ledger`

These optimizer tables are global operator data, not tenant-owned data. Request
and worker contexts receive no rows; only an approved maintenance context can
read or mutate them.

`workspace_invitations` and `admin_audit_events` use the direct workspace policy
for normal request and worker contexts, and additionally allow `auth_bootstrap` only when
`workspace_id = current_workspace_id()` and the bootstrap workspace belongs to
the current organization. This lets provider callback completion find matching
pending invitations and write the metadata-only completion audit event without
exposing quota, usage, or other admin tables to auth bootstrap contexts.

Feature 099 keeps its two scheduler operations out of the historical global
maintenance predicate. `playback_normalization_inventory` and
`playback_normalization_dispatch` receive normalization-specific `FOR SELECT`
policies only on `playback_normalization_jobs` and `playback_backfill_runs`.
`playback_normalization_attempts`, scheduler DML, and every content/artifact
operation require the exact request/worker workspace predicate.

The deployment-global GEPA optimizer uses the separate
`prompt_optimization` maintenance operation. It is accepted only through the
`twobrain_rec_maintenance` role and the exact transaction-local maintenance
context; ordinary recording workers never mount that role's password.

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
- `meeting_target_registry_entries` through `meeting_target_registry_versions`.

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
