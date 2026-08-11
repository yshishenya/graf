"""Bound referral links and allow the authenticated owner to issue one."""

from collections.abc import Sequence

from alembic import op

revision: str = "0059_referral_expiry_owner_write"
down_revision: str | None = "0058_referral_link_invitees"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "update referral_links set expires_at = issued_at + interval '30 days' "
            "where expires_at is null"
        )
        op.execute(
            "create unique index if not exists uq_referral_attributions_invitee "
            "on referral_attributions (invitee_user_id) where invitee_user_id is not null"
        )
        op.execute(
            "alter policy referral_links_tenant_isolation on referral_links "
            "with check ("
            "(rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) "
            "or (rec_context_kind() = 'auth_public' and workspace_id = rec_current_workspace_id() "
            "and inviter_user_id = rec_current_user_id()) "
            "or rec_maintenance_allowed())"
        )
    else:
        op.execute(
            "update referral_links set expires_at = datetime(issued_at, '+30 days') "
            "where expires_at is null"
        )
        op.execute(
            "create unique index if not exists uq_referral_attributions_invitee "
            "on referral_attributions (invitee_user_id) where invitee_user_id is not null"
        )


def downgrade() -> None:
    op.execute("drop index if exists uq_referral_attributions_invitee")
