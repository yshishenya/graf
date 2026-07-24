"""durable unauthenticated auth rate limits"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0037_auth_rate_limit_buckets"
down_revision: str | None = "0036_share_inv_auth_lookup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUTH_RATE_LIMIT_POLICY = (
    "rec_context_kind() in ('auth_public', 'auth_bootstrap') "
    "and workspace_id = rec_current_workspace_id()"
)

AUTH_RATE_LIMIT_TABLES = {"auth_rate_limit_buckets"}


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _create_policy() -> None:
    if not _is_postgresql():
        return
    policy_expression = f"({AUTH_RATE_LIMIT_POLICY} or rec_maintenance_allowed())"
    op.execute("alter table auth_rate_limit_buckets enable row level security")
    op.execute("alter table auth_rate_limit_buckets force row level security")
    op.execute(
        f"""
        create policy auth_rate_limit_buckets_isolation
            on auth_rate_limit_buckets
            using ({policy_expression})
            with check ({policy_expression});
        """
    )


def _drop_policy() -> None:
    if not _is_postgresql():
        return
    op.execute(
        "drop policy if exists auth_rate_limit_buckets_isolation "
        "on auth_rate_limit_buckets"
    )
    op.execute("alter table auth_rate_limit_buckets no force row level security")
    op.execute("alter table auth_rate_limit_buckets disable row level security")


def upgrade() -> None:
    op.create_table(
        "auth_rate_limit_buckets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("scope_hash", sa.String(length=128), nullable=False),
        sa.Column("action_key", sa.String(length=64), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "workspace_id",
            "scope_hash",
            "action_key",
            name="uq_auth_rate_limit_scope",
        ),
    )
    op.create_index(
        "ix_auth_rate_limit_blocked_until",
        "auth_rate_limit_buckets",
        ["blocked_until"],
    )
    _create_policy()


def downgrade() -> None:
    _drop_policy()
    op.drop_index("ix_auth_rate_limit_blocked_until", table_name="auth_rate_limit_buckets")
    op.drop_table("auth_rate_limit_buckets")
