"""Allow anonymous referral landing to validate one token without identity data."""

from collections.abc import Sequence

from alembic import op

revision: str = "0061_referral_landing_lookup_rls"
down_revision: str | None = "0060_referral_user_history_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "create policy referral_links_landing_lookup on referral_links "
            "for select using (rec_context_kind() = 'referral_landing_lookup' "
            "and token_hash = rec_setting('app.referral_token_hash') "
            "and state = 'active' "
            "and (expires_at is null or expires_at > now()))"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("drop policy if exists referral_links_landing_lookup on referral_links")
