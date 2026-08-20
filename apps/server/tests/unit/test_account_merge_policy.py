from uuid import uuid4

import pytest

from twobrain_rec_server.auth.account_merge import (
    AccountMergeError,
    MergeEntityCounts,
    build_merge_preview,
    ensure_preview_confirmable,
)
from twobrain_rec_server.db.base import Base
from twobrain_rec_server.db.models import AccountMergeIntent, Workspace

USER_IDENTITY_FK_DISPOSITIONS = {
    ("account_closure_requests", "requested_by_user_id"): "blocking",
    ("account_merge_intents", "source_user_id"): "historical_only",
    ("account_merge_intents", "survivor_user_id"): "historical_only",
    ("account_merge_journals", "source_user_id"): "historical_only",
    ("account_merge_journals", "survivor_user_id"): "historical_only",
    ("admin_audit_events", "actor_user_id"): "historical_only",
    ("auth_audit_events", "actor_user_id"): "historical_only",
    ("auth_audit_events", "user_id"): "historical_only",
    ("auth_sessions", "user_id"): "revoked",
    ("billing_audit_events", "actor_user_id"): "historical_only",
    ("billing_notification_deliveries", "recipient_id"): "historical_only",
    ("billing_notification_preferences", "user_id"): "transfer_or_deduplicate",
    ("billing_payment_methods", "owner_user_id"): "blocking",
    ("calendar_audit_events", "actor_user_id"): "historical_only",
    ("calendar_settings_preferences", "owner_user_id"): "transfer_or_deduplicate",
    ("calendar_sources", "owner_user_id"): "blocking",
    ("export_packages", "requested_by_user_id"): "blocking",
    ("external_identities", "user_id"): "transfer_or_deduplicate",
    ("fair_use_reviews", "subject_user_id"): "lineage_aware",
    ("ingest_audit_events", "actor_user_id"): "historical_only",
    ("meeting_artifact_policies", "updated_by_user_id"): "historical_only",
    ("meeting_deletion_requests", "requested_by_user_id"): "blocking",
    ("meeting_detection_non_target_rules", "created_by_user_id"): "historical_only",
    ("meeting_detection_review_actions", "actor_user_id"): "historical_only",
    ("meeting_detection_telemetry_batches", "user_id"): "historical_only",
    ("meeting_detection_telemetry_rate_limit_buckets", "user_id"): "historical_only",
    ("meeting_egress_audit_events", "actor_user_id"): "historical_only",
    ("meeting_lifecycle_audit_events", "actor_user_id"): "historical_only",
    ("meeting_outcome_generation_attempts", "requested_by_user_id"): "historical_only",
    ("meeting_outcome_sets", "accepted_by_user_id"): "historical_only",
    ("meeting_outcome_sets", "requested_by_user_id"): "historical_only",
    ("meeting_share_grants", "created_by_user_id"): "historical_only",
    ("meeting_share_grants", "grantee_user_id"): "transfer_or_deduplicate",
    ("meeting_share_grants", "revoked_by_user_id"): "historical_only",
    ("meeting_share_invitations", "invited_by_user_id"): "historical_only",
    ("meeting_share_invitations", "resolved_user_id"): "historical_only",
    ("meeting_share_rate_limit_buckets", "user_id"): "historical_only",
    ("meeting_speaker_names", "updated_by_user_id"): "historical_only",
    ("meeting_target_registry_versions", "published_by_user_id"): "historical_only",
    ("meetings", "created_by_user_id"): "transfer_or_deduplicate",
    ("playback_normalization_jobs", "requested_by_user_id"): "historical_only",
    ("processing_audit_events", "actor_user_id"): "historical_only",
    ("recording_calendar_match_attempts", "owner_user_id"): "historical_only",
    ("referral_attributions", "invitee_user_id"): "lineage_aware",
    ("referral_attributions", "inviter_user_id"): "lineage_aware",
    ("referral_links", "inviter_user_id"): "historical_only",
    ("registered_devices", "revoked_by"): "historical_only",
    ("registered_devices", "trusted_by"): "historical_only",
    ("registered_devices", "user_id"): "revoked",
    ("summary_templates", "owner_user_id"): "transfer_or_deduplicate",
    ("support_incident_rate_limit_buckets", "reporter_user_id"): "historical_only",
    ("support_incidents", "reporter_user_id"): "historical_only",
    ("trial_activations", "user_id"): "lineage_aware",
    ("upload_sessions", "created_by_user_id"): "blocking",
    ("user_identities", "merged_into_user_id"): "historical_only",
    ("user_usage_daily", "user_id"): "lineage_aware",
    ("workspace_invitations", "completed_by_user_id"): "historical_only",
    ("workspace_invitations", "created_by_user_id"): "historical_only",
    ("workspace_invitations", "revoked_by_user_id"): "historical_only",
    ("workspace_join_offers", "user_id"): "transfer_or_deduplicate",
    ("workspace_memberships", "user_id"): "transfer_or_deduplicate",
    ("workspace_provider_link_states", "initiating_user_id"): "historical_only",
    ("workspace_subscriptions", "billing_owner_id"): "blocking",
    ("workspaces", "owner_user_id"): "transfer_or_deduplicate",
}


def test_dataful_merge_preview_preserves_fingerprint() -> None:
    preview = build_merge_preview(
        survivor_user_id=uuid4(),
        source_user_id=uuid4(),
        counts=MergeEntityCounts(meetings=2, recordings=2),
    )

    ensure_preview_confirmable(preview, fingerprint=preview.fingerprint)


def test_empty_duplicate_preview_has_no_blockers() -> None:
    preview = build_merge_preview(survivor_user_id=uuid4(), source_user_id=uuid4())

    assert preview.blocker_codes == ()


def test_blocker_and_stale_preview_fail_closed() -> None:
    preview = build_merge_preview(
        survivor_user_id=uuid4(),
        source_user_id=uuid4(),
        billing_conflict=True,
    )

    with pytest.raises(AccountMergeError, match="billing_conflict"):
        ensure_preview_confirmable(preview, fingerprint=preview.fingerprint)
    clear = build_merge_preview(survivor_user_id=uuid4(), source_user_id=uuid4())
    with pytest.raises(AccountMergeError, match="merge_preview_stale"):
        ensure_preview_confirmable(clear, fingerprint="0" * 64)


def test_workspace_kind_and_personal_owner_index_include_linked_without_broadening() -> None:
    kind_constraint = next(
        constraint
        for constraint in Workspace.__table__.constraints
        if constraint.name and constraint.name.endswith("ck_workspaces_kind")
    )
    constraint_sql = str(kind_constraint.sqltext).lower()
    personal_owner_index = next(
        index
        for index in Workspace.__table__.indexes
        if index.name == "uq_workspaces_personal_owner"
    )
    index_where = str(personal_owner_index.dialect_options["postgresql"]["where"]).lower()

    assert all(kind in constraint_sql for kind in ("personal", "corporate", "linked"))
    assert [column.name for column in personal_owner_index.columns] == [
        "organization_id",
        "owner_user_id",
    ]
    assert personal_owner_index.unique is True
    assert "kind = 'personal'" in index_where
    assert "linked" not in index_where


def test_account_merge_proof_columns_are_nullable_foreign_keys() -> None:
    expected_targets = {
        "initiating_auth_session_id": "auth_sessions.id",
        "source_external_identity_id": "external_identities.id",
        "proof_callback_state_id": "auth_callback_states.id",
        "provider_link_state_id": "workspace_provider_link_states.id",
    }

    for column_name, target in expected_targets.items():
        column = AccountMergeIntent.__table__.columns[column_name]
        assert column.nullable is True
        assert {foreign_key.target_fullname for foreign_key in column.foreign_keys} == {target}


def test_user_identity_foreign_key_disposition_inventory_is_complete() -> None:
    actual_inventory = {
        (table.name, foreign_key.parent.name)
        for table in Base.metadata.tables.values()
        for foreign_key in table.foreign_keys
        if foreign_key.target_fullname == "user_identities.id"
    }

    assert actual_inventory == set(USER_IDENTITY_FK_DISPOSITIONS)
    assert set(USER_IDENTITY_FK_DISPOSITIONS.values()) == {
        "transfer_or_deduplicate",
        "lineage_aware",
        "blocking",
        "revoked",
        "historical_only",
    }
