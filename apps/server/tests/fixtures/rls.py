from __future__ import annotations

RLS_DIRECT_WORKSPACE_TABLES = {
    "workspaces",
    "workspace_memberships",
    "registered_devices",
    "workspace_auth_policies",
    "auth_sessions",
    "workspace_provider_link_states",
    "auth_callback_states",
    "auth_audit_events",
    "workspace_consent_copy",
    "meetings",
    "upload_sessions",
    "temporary_upload_objects",
    "track_artifacts",
    "manifest_snapshots",
    "ingest_audit_events",
    "processing_placeholders",
    "processing_workflows",
    "mediascribe_jobs",
    "processing_results",
    "transcript_segments",
    "diarization_segments",
    "processing_audit_events",
    "processing_dependency_states",
}

RLS_INHERITED_WORKSPACE_TABLES = {
    "upload_parts",
    "auth_session_device_bindings",
    "external_identities",
}

RLS_ORGANIZATION_TABLES = {
    "organizations",
    "user_identities",
}

RLS_COVERED_TABLES = (
    RLS_DIRECT_WORKSPACE_TABLES
    | RLS_INHERITED_WORKSPACE_TABLES
    | RLS_ORGANIZATION_TABLES
)

RLS_ALLOWED_MAINTENANCE_OPERATIONS = {
    "migration_verification",
    "production_smoke_cleanup",
    "backup_restore_rehearsal",
    "operator_diagnostics",
}
