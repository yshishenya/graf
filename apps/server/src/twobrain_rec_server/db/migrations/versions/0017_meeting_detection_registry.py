"""meeting detection registry telemetry

Revision ID: 0017_meeting_detection
Revises: 0016_single_track_media_upload
Create Date: 2026-07-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_meeting_detection"
down_revision: str | None = "0016_single_track_media_upload"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MEETING_DETECTION_TABLES = (
    "meeting_target_registry_versions",
    "meeting_target_registry_entries",
    "meeting_detection_telemetry_batches",
    "meeting_detection_target_health_rollups",
    "meeting_detection_candidates",
    "meeting_detection_review_actions",
    "meeting_detection_non_target_rules",
    "meeting_detection_telemetry_rate_limit_buckets",
)

WORKSPACE_OR_GLOBAL_TABLES = {
    "meeting_target_registry_versions",
    "meeting_detection_non_target_rules",
}

WORKSPACE_COLUMN_TABLES = {
    "meeting_detection_telemetry_batches",
    "meeting_detection_target_health_rollups",
    "meeting_detection_candidates",
    "meeting_detection_review_actions",
    "meeting_detection_telemetry_rate_limit_buckets",
}


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _policy_predicate(table_name: str) -> str:
    if table_name in WORKSPACE_OR_GLOBAL_TABLES:
        return (
            "((rec_context_kind() in ('request', 'worker') "
            "and (workspace_id is null or workspace_id = rec_current_workspace_id())) "
            "or rec_maintenance_allowed())"
        )
    if table_name in WORKSPACE_COLUMN_TABLES:
        return (
            "((rec_context_kind() in ('request', 'worker') "
            "and workspace_id = rec_current_workspace_id()) "
            "or rec_maintenance_allowed())"
        )
    return (
        "exists (select 1 from meeting_target_registry_versions parent "
        f"where parent.id = {table_name}.registry_version_id "
        "and ((rec_context_kind() in ('request', 'worker') "
        "and (parent.workspace_id is null or parent.workspace_id = rec_current_workspace_id())) "
        "or rec_maintenance_allowed()))"
    )


def _create_policy(table_name: str) -> None:
    table = _q(table_name)
    policy = _q(f"{table_name}_tenant_isolation")
    predicate = _policy_predicate(table_name)
    op.execute(f"alter table {table} enable row level security")
    op.execute(f"alter table {table} force row level security")
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(f"create policy {policy} on {table} using ({predicate}) with check ({predicate})")


def _drop_policy(table_name: str) -> None:
    table = _q(table_name)
    policy = _q(f"{table_name}_tenant_isolation")
    op.execute(f"drop policy if exists {policy} on {table}")
    op.execute(f"alter table {table} no force row level security")
    op.execute(f"alter table {table} disable row level security")


def upgrade() -> None:
    op.create_table(
        "meeting_target_registry_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id")),
        sa.Column("registry_version", sa.String(length=80), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="admin"),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("published_by_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("document_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("etag", sa.String(length=160)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_meeting_target_registry_versions_workspace_status",
        "meeting_target_registry_versions",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_meeting_target_registry_versions_version",
        "meeting_target_registry_versions",
        ["registry_version"],
    )

    op.create_table(
        "meeting_target_registry_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("registry_version_id", sa.Uuid(), sa.ForeignKey("meeting_target_registry_versions.id"), nullable=False),
        sa.Column("target_id", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("market", sa.String(length=40), nullable=False),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("target_family", sa.String(length=40), nullable=False),
        sa.Column("mode", sa.String(length=40), nullable=False),
        sa.Column("evidence", sa.String(length=80), nullable=False),
        sa.Column("native_bundle_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("windows_process_names", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("browser_service_patterns", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("required_signals", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("comments", sa.String(length=500)),
    )
    op.create_index("ix_meeting_target_registry_entries_version", "meeting_target_registry_entries", ["registry_version_id"])
    op.create_index("ix_meeting_target_registry_entries_target", "meeting_target_registry_entries", ["target_id"])
    op.create_index("ix_meeting_target_registry_entries_mode", "meeting_target_registry_entries", ["mode"])

    op.create_table(
        "meeting_detection_telemetry_batches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("device_id", sa.Uuid(), sa.ForeignKey("registered_devices.id"), nullable=False),
        sa.Column("idempotency_key_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("payload_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("client_version", sa.String(length=80), nullable=False),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("os_version_major", sa.String(length=40), nullable=False),
        sa.Column("registry_version", sa.String(length=80), nullable=False),
        sa.Column("candidate_filter_version", sa.String(length=80), nullable=False),
        sa.Column("rollup_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rollup_ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("policy_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("resource_rollup_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("redaction_result", sa.String(length=80), nullable=False, server_default="accepted"),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "uq_meeting_detection_telemetry_idempotency",
        "meeting_detection_telemetry_batches",
        ["workspace_id", "device_id", "idempotency_key_fingerprint"],
        unique=True,
    )
    op.create_index(
        "ix_meeting_detection_telemetry_workspace_received",
        "meeting_detection_telemetry_batches",
        ["workspace_id", "received_at"],
    )

    op.create_table(
        "meeting_detection_target_health_rollups",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("target_id", sa.String(length=80), nullable=False),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("registry_version", sa.String(length=80), nullable=False),
        sa.Column("client_version_bucket", sa.String(length=80)),
        sa.Column("os_version_major", sa.String(length=40), nullable=False),
        sa.Column("rollup_date", sa.Date(), nullable=False),
        sa.Column("support_mode", sa.String(length=40), nullable=False),
        sa.Column("signal_families_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("outcomes_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("duration_buckets_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("reason_codes_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.create_index(
        "ix_meeting_detection_target_health_workspace_target",
        "meeting_detection_target_health_rollups",
        ["workspace_id", "target_id", "rollup_date"],
    )
    op.create_index(
        "ix_meeting_detection_target_health_registry",
        "meeting_detection_target_health_rollups",
        ["registry_version"],
    )

    op.create_table(
        "meeting_detection_candidates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("candidate_kind", sa.String(length=80), nullable=False, server_default="unknown_native_app"),
        sa.Column("state", sa.String(length=60), nullable=False, server_default="new"),
        sa.Column("bundle_id", sa.String(length=200)),
        sa.Column("display_name", sa.String(length=80)),
        sa.Column("signing_team_id", sa.String(length=20)),
        sa.Column("version_samples_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("candidate_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candidate_reasons_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("suppression_reasons_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("stable_observation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reporting_installation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("manual_record_nearby_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("calendar_or_join_hint_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_seen_bucket", sa.Date()),
        sa.Column("last_seen_bucket", sa.Date()),
        sa.Column("proposed_target_id", sa.String(length=80)),
        sa.Column("merged_target_id", sa.String(length=80)),
        sa.Column("last_batch_id", sa.Uuid(), sa.ForeignKey("meeting_detection_telemetry_batches.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_meeting_detection_candidates_workspace_state", "meeting_detection_candidates", ["workspace_id", "state"])
    op.create_index("ix_meeting_detection_candidates_bundle", "meeting_detection_candidates", ["platform", "bundle_id"])
    op.create_index(
        "uq_meeting_detection_candidates_workspace_bundle",
        "meeting_detection_candidates",
        ["workspace_id", "platform", "bundle_id"],
        unique=True,
    )
    op.create_index("ix_meeting_detection_candidates_score", "meeting_detection_candidates", ["candidate_score"])

    op.create_table(
        "meeting_detection_review_actions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), sa.ForeignKey("meeting_detection_candidates.id")),
        sa.Column("registry_version_id", sa.Uuid(), sa.ForeignKey("meeting_target_registry_versions.id")),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("previous_state", sa.String(length=60)),
        sa.Column("next_state", sa.String(length=60)),
        sa.Column("reason_code", sa.String(length=120)),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_meeting_detection_review_actions_workspace_created",
        "meeting_detection_review_actions",
        ["workspace_id", "created_at"],
    )
    op.create_index("ix_meeting_detection_review_actions_candidate", "meeting_detection_review_actions", ["candidate_id"])

    op.create_table(
        "meeting_detection_non_target_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id")),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("rule_kind", sa.String(length=80), nullable=False),
        sa.Column("rule_value", sa.String(length=240), nullable=False),
        sa.Column("reason_code", sa.String(length=120), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index(
        "ix_meeting_detection_non_target_rules_workspace",
        "meeting_detection_non_target_rules",
        ["workspace_id", "platform", "rule_kind"],
    )
    op.create_index(
        "ix_meeting_detection_non_target_rules_value",
        "meeting_detection_non_target_rules",
        ["rule_kind", "rule_value"],
    )
    op.create_index(
        "uq_meeting_detection_non_target_rules_workspace_rule",
        "meeting_detection_non_target_rules",
        ["workspace_id", "platform", "rule_kind", "rule_value"],
        unique=True,
    )

    op.create_table(
        "meeting_detection_telemetry_rate_limit_buckets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("device_id", sa.Uuid(), sa.ForeignKey("registered_devices.id"), nullable=False),
        sa.Column("bucket_key", sa.String(length=120), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked_until", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "uq_meeting_detection_rate_limit_bucket",
        "meeting_detection_telemetry_rate_limit_buckets",
        ["workspace_id", "user_id", "device_id", "bucket_key"],
        unique=True,
    )

    if _is_postgresql():
        for table_name in MEETING_DETECTION_TABLES:
            _create_policy(table_name)


def downgrade() -> None:
    if _is_postgresql():
        for table_name in reversed(MEETING_DETECTION_TABLES):
            _drop_policy(table_name)
    op.drop_index("uq_meeting_detection_rate_limit_bucket", table_name="meeting_detection_telemetry_rate_limit_buckets")
    op.drop_table("meeting_detection_telemetry_rate_limit_buckets")
    op.drop_index("uq_meeting_detection_non_target_rules_workspace_rule", table_name="meeting_detection_non_target_rules")
    op.drop_index("ix_meeting_detection_non_target_rules_value", table_name="meeting_detection_non_target_rules")
    op.drop_index("ix_meeting_detection_non_target_rules_workspace", table_name="meeting_detection_non_target_rules")
    op.drop_table("meeting_detection_non_target_rules")
    op.drop_index("ix_meeting_detection_review_actions_candidate", table_name="meeting_detection_review_actions")
    op.drop_index("ix_meeting_detection_review_actions_workspace_created", table_name="meeting_detection_review_actions")
    op.drop_table("meeting_detection_review_actions")
    op.drop_index("ix_meeting_detection_candidates_score", table_name="meeting_detection_candidates")
    op.drop_index("uq_meeting_detection_candidates_workspace_bundle", table_name="meeting_detection_candidates")
    op.drop_index("ix_meeting_detection_candidates_bundle", table_name="meeting_detection_candidates")
    op.drop_index("ix_meeting_detection_candidates_workspace_state", table_name="meeting_detection_candidates")
    op.drop_table("meeting_detection_candidates")
    op.drop_index("ix_meeting_detection_target_health_registry", table_name="meeting_detection_target_health_rollups")
    op.drop_index("ix_meeting_detection_target_health_workspace_target", table_name="meeting_detection_target_health_rollups")
    op.drop_table("meeting_detection_target_health_rollups")
    op.drop_index("ix_meeting_detection_telemetry_workspace_received", table_name="meeting_detection_telemetry_batches")
    op.drop_index("uq_meeting_detection_telemetry_idempotency", table_name="meeting_detection_telemetry_batches")
    op.drop_table("meeting_detection_telemetry_batches")
    op.drop_index("ix_meeting_target_registry_entries_mode", table_name="meeting_target_registry_entries")
    op.drop_index("ix_meeting_target_registry_entries_target", table_name="meeting_target_registry_entries")
    op.drop_index("ix_meeting_target_registry_entries_version", table_name="meeting_target_registry_entries")
    op.drop_table("meeting_target_registry_entries")
    op.drop_index("ix_meeting_target_registry_versions_version", table_name="meeting_target_registry_versions")
    op.drop_index("ix_meeting_target_registry_versions_workspace_status", table_name="meeting_target_registry_versions")
    op.drop_table("meeting_target_registry_versions")
