"""Allow an invitee to read only their own referral lifecycle row."""

from collections.abc import Sequence

from alembic import op

revision: str = "0060_referral_user_history_rls"
down_revision: str | None = "0059_referral_expiry_owner_write"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "create policy referral_attributions_user_history on referral_attributions "
            "for select using (rec_context_kind() = 'auth_referral_user_lookup' "
            "and invitee_user_id = rec_current_user_id())"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("drop policy if exists referral_attributions_user_history on referral_attributions")
