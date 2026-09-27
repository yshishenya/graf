"""Versioned storage purchases, immutable quotes and bounded live acceptance."""

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from alembic import op

revision = "0100_billing_purchases"
down_revision = "0099_single_source_revision"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_billing_invoices_workspace_id", "billing_invoices", ["workspace_id", "id"]
    )
    op.create_unique_constraint(
        "uq_billing_grants_workspace_id", "billing_entitlement_grants", ["workspace_id", "id"]
    )
    op.create_unique_constraint(
        "uq_billing_operations_workspace_id", "billing_operations", ["workspace_id", "id"]
    )
    op.add_column(
        "workspace_subscriptions", sa.Column("next_capacity_bytes", sa.BigInteger(), nullable=True)
    )
    op.add_column(
        "workspace_subscriptions",
        sa.Column("next_capacity_version", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "time_credit_ledger_entries",
        sa.Column("capacity_snapshot_bytes", sa.BigInteger(), nullable=True),
    )
    op.create_table(
        "billing_storage_price_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("capacity_bytes", sa.BigInteger(), nullable=False),
        sa.Column("cycle", sa.String(length=16), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("enabled_for_checkout", sa.Boolean(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("policy_snapshot", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "cycle IN ('month', 'year') AND amount_minor > 0 AND currency = 'RUB' AND version > 0",
            name=op.f("ck_billing_storage_price_versions_storage_price_money"),
        ),
        sa.CheckConstraint(
            "capacity_bytes IN (5000000000, 20000000000, 100000000000, 500000000000)",
            name=op.f("ck_billing_storage_price_versions_storage_price_capacity"),
        ),
        sa.CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name=op.f("ck_billing_storage_price_versions_storage_price_window"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_billing_storage_price_versions")),
        sa.UniqueConstraint("capacity_bytes", "cycle", "version", name="uq_storage_price_version"),
    )
    op.create_table(
        "billing_acceptance_budgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("limit_minor", sa.Integer(), nullable=False),
        sa.Column("reserved_minor", sa.Integer(), server_default="0", nullable=False),
        sa.Column("spent_minor", sa.Integer(), server_default="0", nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "limit_minor > 0 AND limit_minor <= 20000 AND reserved_minor >= 0 AND spent_minor >= 0 AND reserved_minor + spent_minor <= limit_minor",
            name=op.f("ck_billing_acceptance_budgets_acceptance_budget_limit"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_billing_acceptance_budgets_workspace_id_workspaces"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_billing_acceptance_budgets")),
        sa.UniqueConstraint("workspace_id", "id", name="uq_acceptance_budget_workspace_id"),
        sa.UniqueConstraint("workspace_id", name="uq_acceptance_budget_workspace"),
    )
    op.create_table(
        "billing_purchase_quotes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("subscription_version", sa.Integer(), nullable=False),
        sa.Column("selection_version", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_operation_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "purpose IN ('initial_checkout', 'storage_upgrade', 'early_renewal', 'storage_schedule', 'resume_renewal')",
            name=op.f("ck_billing_purchase_quotes_purchase_quote_purpose"),
        ),
        sa.CheckConstraint(
            "expires_at > created_at", name=op.f("ck_billing_purchase_quotes_purchase_quote_window")
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["user_identities.id"],
            name=op.f("fk_billing_purchase_quotes_owner_user_id_user_identities"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "consumed_operation_id"],
            ["billing_operations.workspace_id", "billing_operations.id"],
            name=op.f("fk_billing_purchase_quotes_workspace_id_billing_operations"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_billing_purchase_quotes_workspace_id_workspaces"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_billing_purchase_quotes")),
        sa.UniqueConstraint("consumed_operation_id", name="uq_purchase_quote_operation"),
    )
    op.create_index(
        "ix_purchase_quotes_workspace_expiry",
        "billing_purchase_quotes",
        ["workspace_id", "expires_at"],
        unique=False,
    )
    op.create_table(
        "billing_storage_entitlement_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("base_grant_id", sa.Uuid(), nullable=False),
        sa.Column("capacity_bytes", sa.BigInteger(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("catalog_version_id", sa.Uuid(), nullable=False),
        sa.Column("full_period_amount_minor", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "capacity_bytes IN (5000000000, 20000000000, 100000000000, 500000000000)",
            name=op.f("ck_billing_storage_entitlement_grants_storage_grant_capacity"),
        ),
        sa.CheckConstraint(
            "ends_at > starts_at AND full_period_amount_minor > 0",
            name=op.f("ck_billing_storage_entitlement_grants_storage_grant_period_money"),
        ),
        sa.ForeignKeyConstraint(
            ["catalog_version_id"],
            ["billing_storage_price_versions.id"],
            name=op.f(
                "fk_billing_storage_entitlement_grants_catalog_version_id_billing_storage_price_versions"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "base_grant_id"],
            ["billing_entitlement_grants.workspace_id", "billing_entitlement_grants.id"],
            name=op.f(
                "fk_billing_storage_entitlement_grants_workspace_id_billing_entitlement_grants"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "invoice_id"],
            ["billing_invoices.workspace_id", "billing_invoices.id"],
            name=op.f("fk_billing_storage_entitlement_grants_workspace_id_billing_invoices"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_billing_storage_entitlement_grants_workspace_id_workspaces"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_billing_storage_entitlement_grants")),
        sa.UniqueConstraint(
            "workspace_id", "invoice_id", "base_grant_id", name="uq_storage_grant_invoice_period"
        ),
    )
    op.create_index(
        "ix_storage_grants_workspace_period",
        "billing_storage_entitlement_grants",
        ["workspace_id", "starts_at", "ends_at"],
        unique=False,
    )
    op.create_table(
        "billing_acceptance_reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("budget_id", sa.Uuid(), nullable=False),
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.CheckConstraint(
            "amount_minor > 0 AND state IN ('reserved', 'spent', 'released')",
            name=op.f("ck_billing_acceptance_reservations_acceptance_reservation_state"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "budget_id"],
            ["billing_acceptance_budgets.workspace_id", "billing_acceptance_budgets.id"],
            name=op.f("fk_billing_acceptance_reservations_workspace_id_billing_acceptance_budgets"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "operation_id"],
            ["billing_operations.workspace_id", "billing_operations.id"],
            name=op.f("fk_billing_acceptance_reservations_workspace_id_billing_operations"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_billing_acceptance_reservations_workspace_id_workspaces"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_billing_acceptance_reservations")),
        sa.UniqueConstraint("operation_id", name="uq_acceptance_reservation_operation"),
    )
    _seed_catalog()
    _install_policies()


def _seed_catalog() -> None:
    table = sa.table(
        "billing_storage_price_versions",
        sa.column("id", sa.Uuid()),
        sa.column("version", sa.Integer()),
        sa.column("capacity_bytes", sa.BigInteger()),
        sa.column("cycle", sa.String()),
        sa.column("amount_minor", sa.Integer()),
        sa.column("currency", sa.String()),
        sa.column("enabled_for_checkout", sa.Boolean()),
        sa.column("effective_from", sa.DateTime(timezone=True)),
        sa.column("policy_snapshot", sa.JSON()),
    )
    rows = []
    for gb, monthly in ((5, 29000), (20, 79000), (100, 199000), (500, 499000)):
        for cycle, multiplier in (("month", 1), ("year", 10)):
            rows.append(
                {
                    "id": uuid5(NAMESPACE_URL, f"graf:storage:v1:{gb}:{cycle}"),
                    "version": 1,
                    "capacity_bytes": gb * 1000000000,
                    "cycle": cycle,
                    "amount_minor": monthly * multiplier,
                    "currency": "RUB",
                    "enabled_for_checkout": True,
                    "effective_from": datetime(2026, 9, 26, tzinfo=UTC),
                    "policy_snapshot": {
                        "offer_version": "personal-2026-08-21",
                        "capacity_kind": "total",
                    },
                }
            )
    op.bulk_insert(table, rows)


def _install_policies() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in (
        "billing_storage_price_versions",
        "billing_acceptance_budgets",
        "billing_purchase_quotes",
        "billing_storage_entitlement_grants",
        "billing_acceptance_reservations",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        if table == "billing_storage_price_versions":
            op.execute(
                f"CREATE POLICY {table}_read ON {table} FOR SELECT USING (rec_context_kind() IN ('request','worker') OR rec_maintenance_allowed())"
            )
            op.execute(
                f"CREATE POLICY {table}_maintain ON {table} FOR ALL USING (rec_maintenance_allowed()) WITH CHECK (rec_maintenance_allowed())"
            )
        else:
            predicate = "((rec_context_kind() IN ('request','worker') AND workspace_id = rec_current_workspace_id()) OR rec_maintenance_allowed())"
            op.execute(
                f"CREATE POLICY {table}_tenant_isolation ON {table} USING ({predicate}) WITH CHECK ({predicate})"
            )
    op.execute("""
        CREATE FUNCTION rec_check_storage_grant() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM billing_entitlement_grants b
            JOIN billing_storage_price_versions p ON p.id = NEW.catalog_version_id
            WHERE b.id = NEW.base_grant_id AND b.workspace_id = NEW.workspace_id
              AND NEW.starts_at >= b.starts_at AND NEW.ends_at <= b.ends_at
              AND p.capacity_bytes = NEW.capacity_bytes AND p.cycle = b.cycle
              AND p.amount_minor = NEW.full_period_amount_minor
          ) THEN RAISE EXCEPTION 'storage grant does not match purchased period/catalog' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER storage_grant_period BEFORE INSERT OR UPDATE ON billing_storage_entitlement_grants FOR EACH ROW EXECUTE FUNCTION rec_check_storage_grant()"
    )
    op.execute("""
        CREATE FUNCTION rec_storage_grant_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'paid storage grants are append-only' USING ERRCODE = '23514';
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER storage_grant_immutable BEFORE UPDATE OR DELETE ON billing_storage_entitlement_grants FOR EACH ROW EXECUTE FUNCTION rec_storage_grant_immutable()"
    )
    op.execute("""
        CREATE FUNCTION rec_storage_price_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF ROW(NEW.id, NEW.version, NEW.capacity_bytes, NEW.cycle, NEW.amount_minor, NEW.currency)
            IS DISTINCT FROM ROW(OLD.id, OLD.version, OLD.capacity_bytes, OLD.cycle, OLD.amount_minor, OLD.currency)
          THEN RAISE EXCEPTION 'create a new storage price version' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER storage_price_immutable BEFORE UPDATE ON billing_storage_price_versions FOR EACH ROW EXECUTE FUNCTION rec_storage_price_immutable()"
    )

    op.execute("""
        CREATE FUNCTION rec_purchase_quote_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF ROW(NEW.id, NEW.workspace_id, NEW.owner_user_id, NEW.purpose,
                 NEW.subscription_version, NEW.selection_version, NEW.created_at, NEW.expires_at)
             IS DISTINCT FROM ROW(OLD.id, OLD.workspace_id, OLD.owner_user_id, OLD.purpose,
                 OLD.subscription_version, OLD.selection_version, OLD.created_at, OLD.expires_at)
             OR NEW.snapshot::jsonb IS DISTINCT FROM OLD.snapshot::jsonb
             OR (OLD.consumed_operation_id IS NOT NULL AND
                 NEW.consumed_operation_id IS DISTINCT FROM OLD.consumed_operation_id)
          THEN RAISE EXCEPTION 'purchase quote conditions are immutable' USING ERRCODE = '23514';
          END IF;
          RETURN NEW;
        END; $$
    """)
    op.execute(
        "CREATE TRIGGER purchase_quote_immutable BEFORE UPDATE ON billing_purchase_quotes FOR EACH ROW EXECUTE FUNCTION rec_purchase_quote_immutable()"
    )


def downgrade() -> None:
    # A rollback may remove an unused schema, never paid service or its budget.
    bind = op.get_bind()
    for table in (
        "billing_storage_entitlement_grants",
        "billing_acceptance_reservations",
        "billing_purchase_quotes",
        "billing_acceptance_budgets",
    ):
        if bind.scalar(sa.text(f"SELECT count(*) FROM {table}")):
            raise RuntimeError(
                "billing purchase data exists; disable checkout and reconcile before rollback"
            )
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER purchase_quote_immutable ON billing_purchase_quotes")
        op.execute("DROP FUNCTION rec_purchase_quote_immutable()")
        op.execute("DROP TRIGGER storage_grant_immutable ON billing_storage_entitlement_grants")
        op.execute("DROP FUNCTION rec_storage_grant_immutable()")
        op.execute("DROP TRIGGER storage_price_immutable ON billing_storage_price_versions")
        op.execute("DROP FUNCTION rec_storage_price_immutable()")
        op.execute("DROP TRIGGER storage_grant_period ON billing_storage_entitlement_grants")
        op.execute("DROP FUNCTION rec_check_storage_grant()")
    for table in (
        "billing_acceptance_reservations",
        "billing_storage_entitlement_grants",
        "billing_purchase_quotes",
        "billing_acceptance_budgets",
        "billing_storage_price_versions",
    ):
        op.drop_table(table)
    op.drop_column("time_credit_ledger_entries", "capacity_snapshot_bytes")
    op.drop_column("workspace_subscriptions", "next_capacity_version")
    op.drop_column("workspace_subscriptions", "next_capacity_bytes")
    for table, name in (
        ("billing_invoices", "uq_billing_invoices_workspace_id"),
        ("billing_entitlement_grants", "uq_billing_grants_workspace_id"),
        ("billing_operations", "uq_billing_operations_workspace_id"),
    ):
        op.drop_constraint(name, table, type_="unique")
