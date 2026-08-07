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
    for table in _TABLES:
        _replace_policy(table, maintenance_only_write=False)
