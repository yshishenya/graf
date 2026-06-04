"""ingest foundation

Revision ID: 0001_ingest_foundation
Revises:
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_ingest_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("slug", sa.String(length=120), nullable=False, unique=True),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "slug"),
    )
    op.create_table(
        "user_identities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("external_subject", sa.String(length=240), nullable=False),
        sa.Column("display_name", sa.String(length=240)),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "workspace_memberships",
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), primary_key=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
    )
    op.create_table(
        "registered_devices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("device_public_id", sa.String(length=160), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False, server_default="macos"),
        sa.Column("client_version", sa.String(length=80)),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "meetings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("device_id", sa.Uuid(), sa.ForeignKey("registered_devices.id"), nullable=False),
        sa.Column("local_recording_id", sa.String(length=240), nullable=False),
        sa.Column("title", sa.String(length=500)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="draft"),
        sa.Column("processing_status", sa.String(length=64), nullable=False, server_default="not_submitted"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "local_recording_id"),
    )
    op.create_table(
        "processing_placeholders",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="not_submitted"),
        sa.Column("meeting_status", sa.String(length=64), nullable=False, server_default="draft"),
        sa.Column("workflow_id", sa.String(length=240)),
        sa.Column("mediascribe_job_id", sa.String(length=240)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "upload_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("device_id", sa.Uuid(), sa.ForeignKey("registered_devices.id"), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("upload_strategy", sa.String(length=64), nullable=False, server_default="server_mediated"),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="pending"),
        sa.Column("processing_status", sa.String(length=64), nullable=False, server_default="not_submitted"),
        sa.Column("idempotency_key", sa.String(length=240)),
        sa.Column("expected_track_roles", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("expected_track_sizes", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("max_package_bytes_snapshot", sa.BigInteger(), nullable=False),
        sa.Column("max_track_bytes_snapshot", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finalized_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "upload_parts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("upload_session_id", sa.Uuid(), sa.ForeignKey("upload_sessions.id"), nullable=False),
        sa.Column("track_role", sa.String(length=64), nullable=False),
        sa.Column("part_number", sa.Integer(), nullable=False),
        sa.Column("byte_offset", sa.BigInteger(), nullable=False),
        sa.Column("byte_length", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_object_key", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="accepted"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("upload_session_id", "track_role", "part_number"),
    )
    op.create_table(
        "temporary_upload_objects",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("upload_session_id", sa.Uuid(), sa.ForeignKey("upload_sessions.id"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("storage_object_key", sa.String(length=1000), nullable=False),
        sa.Column("byte_length", sa.BigInteger(), nullable=False),
        sa.Column("object_role", sa.String(length=64), nullable=False, server_default="accepted_part"),
        sa.Column("cleanup_status", sa.String(length=64), nullable=False, server_default="pending"),
        sa.Column("failure_reason", sa.String(length=240)),
        sa.Column("last_error", sa.String(length=500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "track_artifacts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("track_role", sa.String(length=64), nullable=False),
        sa.Column("codec", sa.String(length=120), nullable=False),
        sa.Column("sample_rate_hz", sa.Integer(), nullable=False),
        sa.Column("channel_count", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("byte_length", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_object_key", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="stored"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "manifest_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("manifest_sha256", sa.String(length=64), nullable=False),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "ingest_audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id")),
        sa.Column("upload_session_id", sa.Uuid(), sa.ForeignKey("upload_sessions.id")),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("device_id", sa.Uuid(), sa.ForeignKey("registered_devices.id")),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    for table in [
        "ingest_audit_events",
        "manifest_snapshots",
        "track_artifacts",
        "temporary_upload_objects",
        "upload_parts",
        "upload_sessions",
        "processing_placeholders",
        "meetings",
        "registered_devices",
        "workspace_memberships",
        "user_identities",
        "workspaces",
        "organizations",
    ]:
        op.drop_table(table)
