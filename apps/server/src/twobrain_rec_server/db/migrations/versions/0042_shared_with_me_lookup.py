"""allow recipients to discover their active direct meeting shares

Revision ID: 0042_shared_with_me_lookup
Revises: 0041_share_account_created_email
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0042_shared_with_me_lookup"
down_revision: str | None = "0041_share_account_created_email"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

POLICY_NAME = "meeting_share_grants_shared_with_me_lookup"
INDEX_NAME = "ix_meeting_share_grants_shared_with_me_lookup"
LOOKUP_PREDICATE = """
    rec_context_kind() = 'shared_with_me_lookup'
    and audience_type = 'user'
    and grantee_user_id = rec_current_user_id()
    and status = 'active'
    and (expires_at is null or expires_at > now())
"""


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    op.create_index(
        INDEX_NAME,
        "meeting_share_grants",
        ["grantee_user_id", "created_at"],
        postgresql_where=sa.text("audience_type = 'user' AND status = 'active'"),
    )
    if not _is_postgresql():
        return
    op.execute(
        f"""
        create policy {POLICY_NAME}
            on meeting_share_grants
            for select
            using ({LOOKUP_PREDICATE})
        """
    )


def downgrade() -> None:
    if _is_postgresql():
        op.execute(f"drop policy if exists {POLICY_NAME} on meeting_share_grants")
    op.drop_index(INDEX_NAME, table_name="meeting_share_grants")
