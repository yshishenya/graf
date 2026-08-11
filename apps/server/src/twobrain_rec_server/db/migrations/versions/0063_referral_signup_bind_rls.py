"""Permit the anonymous-token signup binder to finalize legacy issued rows."""

from collections.abc import Sequence

from alembic import op

revision: str = "0063_referral_signup_bind_rls"
down_revision: str | None = "0062_referral_reward_linkage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        "create policy referral_attributions_signup_insert on referral_attributions "
        "for insert with check ("
        "rec_context_kind() = 'auth_referral_lookup' "
        "and token_hash = rec_setting('app.referral_token_hash') "
        "and referral_link_id::text = rec_setting('app.referral_link_id') "
        "and state = 'registered' and invitee_user_id = rec_current_user_id() "
        "and workspace_id = (select workspace_id from referral_links "
        "where id = referral_attributions.referral_link_id) "
        "and inviter_user_id = (select inviter_user_id from referral_links "
        "where id = referral_attributions.referral_link_id)"
        ")"
    )
    op.execute(
        "create policy referral_attributions_signup_bind on referral_attributions "
        "for update using ("
        "rec_context_kind() = 'auth_referral_lookup' "
        "and token_hash = rec_setting('app.referral_token_hash') "
        "and (rec_setting('app.referral_link_id') is null "
        "or referral_link_id::text = rec_setting('app.referral_link_id')) "
        "and state = 'issued' and invitee_user_id is null"
        ") with check ("
        "rec_context_kind() = 'auth_referral_lookup' "
        "and referral_link_id::text = rec_setting('app.referral_link_id') "
        "and state = 'registered' and invitee_user_id = rec_current_user_id() "
        "and workspace_id = (select workspace_id from referral_links "
        "where id = referral_attributions.referral_link_id) "
        "and inviter_user_id = (select inviter_user_id from referral_links "
        "where id = referral_attributions.referral_link_id)"
        ")"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("drop policy if exists referral_attributions_signup_insert on referral_attributions")
        op.execute("drop policy if exists referral_attributions_signup_bind on referral_attributions")
