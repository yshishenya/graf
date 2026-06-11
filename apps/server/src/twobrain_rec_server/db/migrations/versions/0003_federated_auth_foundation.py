"""federated auth foundation

Revision ID: 0003_federated_auth_foundation
Revises: 0002_access_placeholders
Create Date: 2026-06-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_federated_auth_foundation"
down_revision: str | None = "0002_access_placeholders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_auth_policies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), unique=True, nullable=False),
        sa.Column("allow_yandex", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("allow_vk", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("allow_telegram", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("allow_tid", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("allow_sber_id", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("allow_mts_id", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("allow_esia", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("allow_provider_self_enrollment", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("require_ru_local", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("residency_region_tag", sa.String(length=16), nullable=False, server_default="ru"),
        sa.Column("consent_text_version", sa.String(length=64), nullable=False, server_default="v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "external_identities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_subject", sa.String(length=240), nullable=False),
        sa.Column("provider_username", sa.String(length=160)),
        sa.Column("email", sa.String(length=240)),
        sa.Column("phone", sa.String(length=64)),
        sa.Column("display_name", sa.String(length=240)),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("subject_issued_at", sa.DateTime(timezone=True)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("meta", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("provider", "provider_subject"),
    )

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("device_id", sa.Uuid(), sa.ForeignKey("registered_devices.id")),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("session_token_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claims_fingerprint", sa.String(length=128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("session_token_hash"),
    )

    op.create_table(
        "workspace_provider_link_states",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("initiating_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("source_provider_identity_id", sa.Uuid(), sa.ForeignKey("external_identities.id"), nullable=False),
        sa.Column("target_provider_identity_id", sa.Uuid(), sa.ForeignKey("external_identities.id")),
        sa.Column("candidate_identity_subject", sa.String(length=240)),
        sa.Column("candidate_email", sa.String(length=240)),
        sa.Column("candidate_phone", sa.String(length=64)),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="initiated"),
        sa.Column("resolution", sa.String(length=240)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "auth_callback_states",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("state_nonce", sa.String(length=128), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("requested_redirect", sa.String(length=512)),
        sa.Column("expected_state", sa.String(length=256), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("result", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("error_code", sa.String(length=64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("state_nonce"),
    )

    op.create_table(
        "auth_audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("provider", sa.String(length=64)),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("user_identities.id")),
        sa.Column("actor_ip_hash", sa.String(length=128)),
        sa.Column("request_id", sa.String(length=128)),
        sa.Column("outcome", sa.String(length=32), nullable=False, server_default="success"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "workspace_consent_copy",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False, server_default="ru"),
        sa.Column("version", sa.String(length=32), nullable=False, server_default="v1"),
        sa.Column("content_markdown", sa.String(length=4000), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("workspace_id", "language", "version"),
    )

    op.create_table(
        "auth_session_device_bindings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("auth_session_id", sa.Uuid(), sa.ForeignKey("auth_sessions.id"), nullable=False),
        sa.Column("registered_device_id", sa.Uuid(), sa.ForeignKey("registered_devices.id"), nullable=False),
        sa.Column("device_state", sa.String(length=32), nullable=False, server_default="untrusted"),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("revocation_reason", sa.String(length=240)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    with op.batch_alter_table("registered_devices") as batch_op:
        batch_op.add_column(
            sa.Column("registration_state", sa.String(length=32), nullable=False, server_default="approved"),
        )
        batch_op.add_column(
            sa.Column("trusted_by", sa.Uuid(), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_registered_devices_trusted_by_user_identities",
            "user_identities",
            ["trusted_by"],
            ["id"],
        )
        batch_op.add_column(
            sa.Column("revoked_by", sa.Uuid(), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_registered_devices_revoked_by_user_identities",
            "user_identities",
            ["revoked_by"],
            ["id"],
        )



def downgrade() -> None:
    with op.batch_alter_table("registered_devices") as batch_op:
        batch_op.drop_constraint("fk_registered_devices_revoked_by_user_identities", type_="foreignkey")
        batch_op.drop_column("revoked_by")
        batch_op.drop_constraint("fk_registered_devices_trusted_by_user_identities", type_="foreignkey")
        batch_op.drop_column("trusted_by")
        batch_op.drop_column("registration_state")
    op.drop_table("auth_session_device_bindings")
    op.drop_table("workspace_consent_copy")
    op.drop_table("auth_audit_events")
    op.drop_table("auth_callback_states")
    op.drop_table("workspace_provider_link_states")
    op.drop_table("auth_sessions")
    op.drop_table("external_identities")
    op.drop_table("workspace_auth_policies")
