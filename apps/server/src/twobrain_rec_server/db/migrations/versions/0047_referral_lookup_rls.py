"""Allow token-scoped referral binding and owner-scoped reward reconciliation."""

from collections.abc import Sequence

from alembic import op

revision: str = "0047_referral_lookup_rls"
down_revision: str | None = "0046_billing_promotions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _policy_sql() -> str:
    return (
        "create policy referral_attributions_tenant_isolation on referral_attributions "
        "using ("
        "(rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) "
        "or (rec_context_kind() = 'auth_callback_lookup' and state = 'issued') "
        "or (rec_context_kind() = 'auth_public' and invitee_user_id = ("
        "select billing_owner_id from workspace_subscriptions "
        "where workspace_id = rec_current_workspace_id())) "
        "or rec_maintenance_allowed()) "
        "with check ("
        "(rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) "
        "or rec_context_kind() = 'auth_callback_lookup' "
        "or (rec_context_kind() = 'auth_public' and invitee_user_id = ("
        "select billing_owner_id from workspace_subscriptions "
        "where workspace_id = rec_current_workspace_id())) "
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
        "or rec_maintenance_allowed()) "
        "with check ((rec_context_kind() in ('request', 'worker') and workspace_id = rec_current_workspace_id()) "
        "or rec_maintenance_allowed())"
    )
