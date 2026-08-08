"""Keep billing catalog rows readable but writable only by maintenance."""

from collections.abc import Sequence

from alembic import op

revision: str = "0056_billing_catalog_write_rls"
down_revision: str | None = "0055_referral_owner_lookup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("billing_plan_versions", "promotion_campaigns")


def _replace_policy(table: str, *, maintenance_only_write: bool) -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    policy = f"{table}_global_access"
    op.execute(f"drop policy if exists {policy} on {table}")
    # 0044 named the first catalog policy `<table>_tenant_isolation`. Drop it
    # as well; PostgreSQL combines permissive policies with OR, so leaving the
    # old policy would silently bypass the maintenance-only write check.
    if table == "billing_plan_versions":
        op.execute(f"drop policy if exists {table}_tenant_isolation on {table}")
    if maintenance_only_write:
        op.execute(
            f"create policy {policy} on {table} "
            "using (rec_context_kind() in ('request', 'worker') or rec_maintenance_allowed()) "
            "with check (rec_maintenance_allowed())"
        )
    else:
        op.execute(
            f"create policy {policy} on {table} "
            "using (rec_context_kind() in ('request', 'worker') or rec_maintenance_allowed()) "
            "with check (rec_context_kind() in ('request', 'worker') or rec_maintenance_allowed())"
        )


def upgrade() -> None:
    for table in _TABLES:
        _replace_policy(table, maintenance_only_write=True)


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    # Restore the exact policies owned by 0044/0046 rather than leaving the
    # post-0056 global policy names behind after a rollback.
    op.execute("drop policy if exists billing_plan_versions_global_access on billing_plan_versions")
    op.execute("drop policy if exists billing_plan_versions_tenant_isolation on billing_plan_versions")
    op.execute(
        "create policy billing_plan_versions_tenant_isolation on billing_plan_versions "
        "using (rec_context_kind() in ('request', 'worker') or rec_maintenance_allowed()) "
        "with check (rec_context_kind() in ('request', 'worker') or rec_maintenance_allowed())"
    )
    op.execute("drop policy if exists promotion_campaigns_global_access on promotion_campaigns")
    op.execute("drop policy if exists promotion_campaigns_tenant_isolation on promotion_campaigns")
    op.execute(
        "create policy promotion_campaigns_global_access on promotion_campaigns "
        "using (rec_context_kind() in ('request', 'worker') or rec_maintenance_allowed()) "
        "with check (rec_context_kind() in ('request', 'worker') or rec_maintenance_allowed())"
    )
