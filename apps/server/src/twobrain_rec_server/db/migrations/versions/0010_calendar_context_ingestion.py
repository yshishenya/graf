"""calendar context ingestion

Revision ID: 0010_calendar_context_ingestion
Revises: 0009_meeting_outcomes_mvp
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_calendar_context_ingestion"
down_revision: str | None = "0009_meeting_outcomes_mvp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CALENDAR_TABLES = (
    "calendar_sources",
    "calendar_credential_envelopes",
    "external_calendars",
    "calendar_event_snapshots",
    "calendar_participants",
    "conference_link_candidates",
    "recording_calendar_context_links",
    "calendar_reminder_states",
    "calendar_audit_events",
)
CONTENT_WORKSPACE_POLICIES = CALENDAR_TABLES
POLICY_NAMES = {table: f"{table}_tenant_isolation" for table in CALENDAR_TABLES}


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _create_all_policy(table_name: str) -> None:
    table = _q(table_name)
    policy = _q(POLICY_NAMES[table_name])
    predicate = "((rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) or rec_maintenance_allowed())"
    op.execute(f"alter table {table} enable row level security")
    op.execute(f"alter table {table} force row level security")
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(f"create policy {policy} on {table} using ({predicate}) with check ({predicate})")


def _drop_policy(table_name: str) -> None:
    table = _q(table_name)
    policy = _q(POLICY_NAMES[table_name])
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(f"alter table {table} no force row level security")
    op.execute(f"alter table {table} disable row level security")


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    op.create_table(
        "calendar_sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("provider_family", sa.String(length=80), nullable=False),
        sa.Column("provider_label", sa.String(length=160)),
        sa.Column("auth_mode", sa.String(length=64), nullable=False),
        sa.Column("credential_state", sa.String(length=64), nullable=False, server_default="pending"),
        sa.Column("connection_state", sa.String(length=64), nullable=False, server_default="active"),
        sa.Column("sync_state", sa.String(length=64), nullable=False, server_default="never_synced"),
        sa.Column("sync_horizon_start", sa.DateTime(timezone=True)),
        sa.Column("sync_horizon_end", sa.DateTime(timezone=True)),
        sa.Column("last_sync_started_at", sa.DateTime(timezone=True)),
        sa.Column("last_sync_finished_at", sa.DateTime(timezone=True)),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True)),
        sa.Column("last_safe_error_code", sa.String(length=120)),
        sa.Column("capabilities_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("selected_calendar_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("disconnected_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_calendar_sources_workspace_owner", "calendar_sources", ["workspace_id", "owner_user_id"])
    op.create_index("ix_calendar_sources_sync_state", "calendar_sources", ["workspace_id", "sync_state"])

    op.create_table(
        "calendar_credential_envelopes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("calendar_source_id", sa.Uuid(), sa.ForeignKey("calendar_sources.id"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("secret_kind", sa.String(length=80), nullable=False),
        sa.Column("sealed_payload", sa.LargeBinary(), nullable=False),
        sa.Column("key_version", sa.String(length=80), nullable=False),
        sa.Column("secret_fingerprint_sha256", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("purged_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_calendar_credential_envelopes_source",
        "calendar_credential_envelopes",
        ["workspace_id", "calendar_source_id"],
    )

    op.create_table(
        "external_calendars",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("calendar_source_id", sa.Uuid(), sa.ForeignKey("calendar_sources.id"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("provider_calendar_id", sa.String(length=500), nullable=False),
        sa.Column("display_label", sa.String(length=240), nullable=False),
        sa.Column("owner_email_hash", sa.String(length=80)),
        sa.Column("owner_display_name", sa.String(length=240)),
        sa.Column("color", sa.String(length=40)),
        sa.Column("visibility", sa.String(length=64), nullable=False, server_default="available"),
        sa.Column("sync_token", sa.String(length=500)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("calendar_source_id", "provider_calendar_id", name="uq_external_calendars_source_provider_id"),
    )
    op.create_index("ix_external_calendars_source_visibility", "external_calendars", ["workspace_id", "calendar_source_id", "visibility"])

    op.create_table(
        "calendar_event_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("calendar_source_id", sa.Uuid(), sa.ForeignKey("calendar_sources.id"), nullable=False),
        sa.Column("external_calendar_id", sa.Uuid(), sa.ForeignKey("external_calendars.id"), nullable=False),
        sa.Column("provider_event_id", sa.String(length=500)),
        sa.Column("ical_uid", sa.String(length=500)),
        sa.Column("recurring_series_id", sa.String(length=500)),
        sa.Column("recurrence_instance_id", sa.String(length=500)),
        sa.Column("original_start", sa.DateTime(timezone=True)),
        sa.Column("source_version", sa.String(length=240)),
        sa.Column("source_status", sa.String(length=64), nullable=False, server_default="unknown"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("timezone", sa.String(length=80)),
        sa.Column("original_start_timezone", sa.String(length=80)),
        sa.Column("original_end_timezone", sa.String(length=80)),
        sa.Column("all_day", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("floating_time", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("transparency", sa.String(length=64)),
        sa.Column("recurrence_rule_json", sa.JSON()),
        sa.Column("recurrence_exceptions_json", sa.JSON()),
        sa.Column("title", sa.String(length=500)),
        sa.Column("description", sa.String(length=4000)),
        sa.Column("location", sa.String(length=1000)),
        sa.Column("privacy_class", sa.String(length=64), nullable=False, server_default="unknown"),
        sa.Column("conference_summary_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("attachments_metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("provider_extras_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("safe_to_show_in_list", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("safe_to_use_as_title", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sensitivity_reasons_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("source_created_at", sa.DateTime(timezone=True)),
        sa.Column("source_updated_at", sa.DateTime(timezone=True)),
        sa.Column("source_deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_calendar_event_snapshots_future", "calendar_event_snapshots", ["workspace_id", "starts_at"])
    op.create_index("ix_calendar_event_snapshots_identity", "calendar_event_snapshots", ["workspace_id", "calendar_source_id", "provider_event_id"])

    op.create_table(
        "calendar_participants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("calendar_event_snapshot_id", sa.Uuid(), sa.ForeignKey("calendar_event_snapshots.id"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("participant_kind", sa.String(length=80), nullable=False),
        sa.Column("response_status", sa.String(length=64), nullable=False, server_default="unknown"),
        sa.Column("email", sa.String(length=320)),
        sa.Column("email_hash", sa.String(length=80)),
        sa.Column("display_name", sa.String(length=240)),
        sa.Column("provider_user_id", sa.String(length=240)),
        sa.Column("workspace_relation", sa.String(length=64), nullable=False, server_default="unknown"),
        sa.Column("recipient_candidate_class", sa.String(length=64), nullable=False, server_default="unknown"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_calendar_participants_event", "calendar_participants", ["workspace_id", "calendar_event_snapshot_id"])

    op.create_table(
        "conference_link_candidates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("calendar_event_snapshot_id", sa.Uuid(), sa.ForeignKey("calendar_event_snapshots.id"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("source_field", sa.String(length=64), nullable=False),
        sa.Column("provider_family", sa.String(length=80), nullable=False),
        sa.Column("url_hash", sa.String(length=80), nullable=False),
        sa.Column("redacted_url_preview", sa.String(length=240)),
        sa.Column("contains_passcode", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sensitivity_class", sa.String(length=80), nullable=False, server_default="meeting_link"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_conference_link_candidates_event", "conference_link_candidates", ["workspace_id", "calendar_event_snapshot_id"])

    op.create_table(
        "recording_calendar_context_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("calendar_event_snapshot_id", sa.Uuid(), sa.ForeignKey("calendar_event_snapshots.id"), nullable=False),
        sa.Column("context_confidence", sa.String(length=64), nullable=False, server_default="none"),
        sa.Column("context_reasons_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("title_source", sa.String(length=64), nullable=False, server_default="generic"),
        sa.Column("roster_source", sa.String(length=64), nullable=False, server_default="none"),
        sa.Column("manual_override_state", sa.String(length=80), nullable=False, server_default="none"),
        sa.Column("linked_at", sa.DateTime(timezone=True)),
        sa.Column("unlinked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_recording_calendar_context_links_meeting", "recording_calendar_context_links", ["workspace_id", "meeting_id"])

    op.create_table(
        "calendar_reminder_states",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("calendar_event_snapshot_id", sa.Uuid(), sa.ForeignKey("calendar_event_snapshots.id"), nullable=False),
        sa.Column("device_id", sa.Uuid(), sa.ForeignKey("registered_devices.id"), nullable=False),
        sa.Column("join_prompt_due_at", sa.DateTime(timezone=True)),
        sa.Column("record_prompt_due_at", sa.DateTime(timezone=True)),
        sa.Column("join_prompt_state", sa.String(length=64), nullable=False, server_default="not_due"),
        sa.Column("record_prompt_state", sa.String(length=64), nullable=False, server_default="not_due"),
        sa.Column("last_client_seen_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_calendar_reminder_states_due", "calendar_reminder_states", ["workspace_id", "device_id", "join_prompt_due_at"])

    op.create_table(
        "calendar_audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("calendar_source_id", sa.Uuid(), sa.ForeignKey("calendar_sources.id")),
        sa.Column("calendar_event_snapshot_id", sa.Uuid(), sa.ForeignKey("calendar_event_snapshots.id")),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id")),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("device_id", sa.Uuid(), sa.ForeignKey("registered_devices.id")),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("outcome", sa.String(length=64), nullable=False),
        sa.Column("safe_reason_code", sa.String(length=120)),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_calendar_audit_events_workspace_created", "calendar_audit_events", ["workspace_id", "created_at"])

    if _is_postgresql():
        for table_name in CALENDAR_TABLES:
            _create_all_policy(table_name)


def downgrade() -> None:
    if _is_postgresql():
        for table_name in CALENDAR_TABLES:
            _drop_policy(table_name)
    op.drop_index("ix_calendar_audit_events_workspace_created", table_name="calendar_audit_events")
    op.drop_table("calendar_audit_events")
    op.drop_index("ix_calendar_reminder_states_due", table_name="calendar_reminder_states")
    op.drop_table("calendar_reminder_states")
    op.drop_index("ix_recording_calendar_context_links_meeting", table_name="recording_calendar_context_links")
    op.drop_table("recording_calendar_context_links")
    op.drop_index("ix_conference_link_candidates_event", table_name="conference_link_candidates")
    op.drop_table("conference_link_candidates")
    op.drop_index("ix_calendar_participants_event", table_name="calendar_participants")
    op.drop_table("calendar_participants")
    op.drop_index("ix_calendar_event_snapshots_identity", table_name="calendar_event_snapshots")
    op.drop_index("ix_calendar_event_snapshots_future", table_name="calendar_event_snapshots")
    op.drop_table("calendar_event_snapshots")
    op.drop_index("ix_external_calendars_source_visibility", table_name="external_calendars")
    op.drop_table("external_calendars")
    op.drop_index("ix_calendar_credential_envelopes_source", table_name="calendar_credential_envelopes")
    op.drop_table("calendar_credential_envelopes")
    op.drop_index("ix_calendar_sources_sync_state", table_name="calendar_sources")
    op.drop_index("ix_calendar_sources_workspace_owner", table_name="calendar_sources")
    op.drop_table("calendar_sources")
