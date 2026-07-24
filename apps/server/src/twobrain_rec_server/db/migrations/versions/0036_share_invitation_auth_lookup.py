"""allow exact invitation continuation lookup under forced RLS"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036_share_inv_auth_lookup"
down_revision: str | None = "0035_meeting_share_security"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SHARE_INVITATION_BASE_POLICY = (
    "(rec_context_kind() in ('request', 'worker') "
    "and workspace_id = rec_current_workspace_id())"
)
SHARE_INVITATION_LOOKUP_POLICY = (
    "(rec_context_kind() = 'share_invitation_lookup' "
    "and workspace_id = rec_current_workspace_id() "
    "and continuation_nonce = rec_share_invitation_continuation_nonce())"
)


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _create_policy() -> None:
    if not _is_postgresql():
        return
    using_expression = (
        f"({SHARE_INVITATION_BASE_POLICY} or {SHARE_INVITATION_LOOKUP_POLICY} "
        "or rec_maintenance_allowed())"
    )
    check_expression = f"({SHARE_INVITATION_BASE_POLICY} or rec_maintenance_allowed())"
    op.execute(
        """
        create or replace function rec_share_invitation_continuation_nonce()
        returns text language sql stable
        as $$ select rec_setting('app.share_invitation_continuation_nonce') $$;
        """
    )
    op.execute("alter table meeting_share_invitations enable row level security")
    op.execute("alter table meeting_share_invitations force row level security")
    op.execute(
        "drop policy if exists meeting_share_invitations_isolation "
        "on meeting_share_invitations"
    )
    op.execute(
        f"""
        create policy meeting_share_invitations_isolation
            on meeting_share_invitations
            using ({using_expression})
            with check ({check_expression})
        """
    )


def _restore_policy() -> None:
    if not _is_postgresql():
        return
    base_policy = (
        "rec_context_kind() in ('request', 'worker') "
        "and workspace_id = rec_current_workspace_id()"
    )
    op.execute(
        "drop policy if exists meeting_share_invitations_isolation "
        "on meeting_share_invitations"
    )
    op.execute(
        f"""
        create policy meeting_share_invitations_isolation
            on meeting_share_invitations
            using (({base_policy}) or rec_maintenance_allowed())
            with check (({base_policy}) or rec_maintenance_allowed())
        """
    )
    op.execute(
        "drop function if exists rec_share_invitation_continuation_nonce()"
    )


def upgrade() -> None:
    op.create_index(
        "ix_meeting_share_invitations_token_hash",
        "meeting_share_invitations",
        ["workspace_id", "token_hash"],
    )
    op.create_index(
        "ix_meeting_share_invitations_continuation_nonce",
        "meeting_share_invitations",
        ["workspace_id", "continuation_nonce"],
        postgresql_where=sa.text("continuation_nonce IS NOT NULL"),
    )
    _create_policy()


def downgrade() -> None:
    _restore_policy()
    op.drop_index(
        "ix_meeting_share_invitations_continuation_nonce",
        table_name="meeting_share_invitations",
    )
    op.drop_index(
        "ix_meeting_share_invitations_token_hash",
        table_name="meeting_share_invitations",
    )
