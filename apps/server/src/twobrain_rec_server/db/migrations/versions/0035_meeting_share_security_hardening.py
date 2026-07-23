"""meeting share rate limits and one-time login continuation"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035_meeting_share_security"
down_revision: str | None = "0034_share_grant_token_replay"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SHARE_RATE_LIMIT_POLICY = (
    "rec_context_kind() = 'request' "
    "and workspace_id = rec_current_workspace_id()"
)

CONTENT_WORKSPACE_POLICIES = {
    "meeting_share_rate_limit_buckets": SHARE_RATE_LIMIT_POLICY,
}


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _create_policy() -> None:
    if not _is_postgresql():
        return
    op.execute("alter table meeting_share_rate_limit_buckets enable row level security")
    op.execute("alter table meeting_share_rate_limit_buckets force row level security")
    op.execute(
        "drop policy if exists meeting_share_rate_limit_buckets_isolation "
        "on meeting_share_rate_limit_buckets"
    )
    op.execute(
        "create policy meeting_share_rate_limit_buckets_isolation "
        "on meeting_share_rate_limit_buckets using ("
        f"(({SHARE_RATE_LIMIT_POLICY}) or rec_maintenance_allowed())"
        ") with check ("
        f"(({SHARE_RATE_LIMIT_POLICY}) or rec_maintenance_allowed())"
        ")"
    )


def _drop_policy() -> None:
    if not _is_postgresql():
        return
    op.execute(
        "drop policy if exists meeting_share_rate_limit_buckets_isolation "
        "on meeting_share_rate_limit_buckets"
    )
    op.execute("alter table meeting_share_rate_limit_buckets no force row level security")
    op.execute("alter table meeting_share_rate_limit_buckets disable row level security")


def upgrade() -> None:
    op.add_column(
        "meeting_share_invitations",
        sa.Column("continuation_nonce", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "meeting_share_invitations",
        sa.Column("continuation_token_ciphertext", sa.String(), nullable=True),
    )
    op.add_column(
        "meeting_share_invitations",
        sa.Column("continuation_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "meeting_share_invitations",
        sa.Column("continuation_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "meeting_share_rate_limit_buckets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user_identities.id"), nullable=False),
        sa.Column("device_id", sa.Uuid(), sa.ForeignKey("registered_devices.id"), nullable=False),
        sa.Column("action_key", sa.String(length=64), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "workspace_id",
            "user_id",
            "device_id",
            "action_key",
            name="uq_meeting_share_rate_limit_scope",
        ),
    )
    op.create_index(
        "ix_meeting_share_rate_limit_blocked_until",
        "meeting_share_rate_limit_buckets",
        ["blocked_until"],
    )
    _create_policy()


def downgrade() -> None:
    _drop_policy()
    op.drop_index(
        "ix_meeting_share_rate_limit_blocked_until",
        table_name="meeting_share_rate_limit_buckets",
    )
    op.drop_table("meeting_share_rate_limit_buckets")
    op.drop_column("meeting_share_invitations", "continuation_used_at")
    op.drop_column("meeting_share_invitations", "continuation_expires_at")
    op.drop_column("meeting_share_invitations", "continuation_token_ciphertext")
    op.drop_column("meeting_share_invitations", "continuation_nonce")
