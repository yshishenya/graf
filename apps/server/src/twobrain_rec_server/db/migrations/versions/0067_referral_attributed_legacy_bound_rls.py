"""Allow legacy bound referral rows to enter the checkout lifecycle."""

from collections.abc import Sequence

from alembic import op

revision: str = "0067_referral_bound_attributed"
down_revision: str | None = "0066_referral_attributed_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("drop policy if exists referral_attributions_checkout_attributed on referral_attributions")
    op.execute(
        "create policy referral_attributions_checkout_attributed on referral_attributions "
        "for update using ("
        "rec_context_kind() = 'auth_referral_user_lookup' "
        "and invitee_user_id = rec_current_user_id() "
        "and state in ('bound', 'registered')"
        ") with check ("
        "rec_context_kind() = 'auth_referral_user_lookup' "
        "and invitee_user_id = rec_current_user_id() "
        "and state = 'attributed'"
        ")"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("drop policy if exists referral_attributions_checkout_attributed on referral_attributions")
