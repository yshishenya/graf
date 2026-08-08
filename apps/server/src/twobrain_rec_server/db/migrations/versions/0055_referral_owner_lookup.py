"""Allow an authenticated user to read only their own referral attribution."""

from collections.abc import Sequence

from alembic import op

revision: str = "0055_referral_owner_lookup"
down_revision: str | None = "0054_promo_reservation_counter"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _policy_sql() -> str:
    return (
        "create policy referral_attributions_tenant_isolation on referral_attributions "
        "using ("
        "(rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) "
        "or (rec_context_kind() = 'auth_callback_lookup' and state = 'issued') "
        "or (rec_context_kind() = 'auth_public' and (invitee_user_id = rec_current_user_id() "
        "or inviter_user_id = rec_current_user_id())) "
        "or (rec_context_kind() = 'auth_referral_lookup' "
        "and token_hash = rec_setting('app.referral_token_hash') "
        "and state in ('issued', 'bound') "
        "and (invitee_user_id is null or invitee_user_id = rec_current_user_id())) "
        "or rec_maintenance_allowed()) "
        "with check ("
        "(rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) "
        "or rec_context_kind() = 'auth_callback_lookup' "
        "or (rec_context_kind() = 'auth_public' and (invitee_user_id = rec_current_user_id() "
        "or inviter_user_id = rec_current_user_id())) "
        "or (rec_context_kind() = 'auth_referral_lookup' "
        "and token_hash = rec_setting('app.referral_token_hash') "
        "and state = 'bound' and invitee_user_id = rec_current_user_id()) "
        "or rec_maintenance_allowed())"
    )


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("drop policy if exists referral_attributions_tenant_isolation on referral_attributions")
    op.execute(_policy_sql())


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("drop policy if exists referral_attributions_tenant_isolation on referral_attributions")
    op.execute(
        "create policy referral_attributions_tenant_isolation on referral_attributions "
        "using ((rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) "
        "or (rec_context_kind() = 'auth_callback_lookup' and state = 'issued') "
        "or (rec_context_kind() = 'auth_public' and invitee_user_id = ("
        "select billing_owner_id from workspace_subscriptions where workspace_id = rec_current_workspace_id())) "
        "or rec_maintenance_allowed()) "
        "with check ((rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) "
        "or rec_context_kind() = 'auth_callback_lookup' "
        "or (rec_context_kind() = 'auth_public' and invitee_user_id = ("
        "select billing_owner_id from workspace_subscriptions where workspace_id = rec_current_workspace_id())) "
        "or rec_maintenance_allowed())"
    )
