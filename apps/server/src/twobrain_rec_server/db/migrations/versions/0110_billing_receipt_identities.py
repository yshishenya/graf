"""Reserve each scoped provider receipt identity on exactly one invoice."""
import sqlalchemy as sa
from alembic import op

revision: str = "0110_billing_receipt_identities"
down_revision: str | None = "0109_reconciliation_observations"
branch_labels = None
depends_on = None

TABLE = "billing_receipt_identities"
ROLE = "twobrain_rec_maintenance"


def upgrade():
    op.execute("LOCK TABLE billing_invoices IN SHARE ROW EXCLUSIVE MODE")
    # Refuse a partial backfill if the migration role cannot see every invoice.
    op.execute("SET LOCAL row_security = off")
    op.create_table(
        TABLE,
        sa.Column("environment", sa.String(32), primary_key=True),
        sa.Column("shop_id", sa.String(160), primary_key=True),
        sa.Column("provider_receipt_id", sa.String(160), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("parent_kind", sa.String(8), nullable=False),
        sa.Column("provider_parent_id", sa.String(160), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id", "invoice_id"], ["billing_invoices.workspace_id", "billing_invoices.id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("parent_kind IN ('payment', 'refund')", name="receipt_identity_parent_kind"),
    )
    op.create_index("ix_billing_receipt_identities_invoice", TABLE, ["workspace_id", "invoice_id"])
    op.execute("""
        DO $$ BEGIN
            INSERT INTO billing_receipt_identities
                (workspace_id, invoice_id, environment, shop_id, provider_receipt_id,
                 parent_kind, provider_parent_id)
            SELECT invoice.workspace_id, invoice.id, fields.environment, fields.shop_id,
                   fields.receipt_id, fields.kind,
                   CASE WHEN jsonb_typeof(entry.value) = 'object'
                        AND jsonb_typeof(entry.value->'environment') = 'string'
                        AND jsonb_typeof(entry.value->'shop_id') = 'string'
                        AND jsonb_typeof(entry.value->'provider_receipt_id') = 'string'
                        AND jsonb_typeof(entry.value->'provider_parent_id') = 'string'
                        AND fields.environment COLLATE "C" ~ '^[a-zA-Z0-9_-]{1,32}$'
                        AND fields.shop_id COLLATE "C" ~ '^[a-zA-Z0-9_.-]{1,160}$'
                        AND fields.receipt_id COLLATE "C" ~ '^[a-zA-Z0-9_.-]{1,160}$'
                        AND fields.parent_id COLLATE "C" ~ '^[a-zA-Z0-9_.-]{1,160}$'
                        AND entry.key = fields.environment || ':' || fields.shop_id || ':' || fields.receipt_id
                        AND operation.provider_id IS NOT NULL AND operation.provider_id <> ''
                        AND (fields.kind = 'payment' AND operation.provider_id = fields.parent_id
                             OR fields.kind = 'refund' AND refund.id IS NOT NULL)
                        AND jsonb_typeof(operation.request_snapshot::jsonb) = 'object'
                        AND (NOT operation.request_snapshot::jsonb ? 'provider_shop_id'
                             OR operation.request_snapshot::jsonb->'provider_shop_id' = to_jsonb(fields.shop_id))
                        AND (NOT operation.request_snapshot::jsonb ? 'provider_environment'
                             OR operation.request_snapshot::jsonb->'provider_environment' = to_jsonb(fields.environment))
                        AND (NOT invoice.plan_snapshot::jsonb ? 'receipt_payment_binding'
                             OR invoice.plan_snapshot::jsonb->'receipt_payment_binding' = jsonb_build_object(
                                'workspace_id', invoice.workspace_id, 'operation_id', operation.id,
                                'payment_id', operation.provider_id, 'environment', fields.environment,
                                'shop_id', fields.shop_id
                             ))
                        THEN fields.parent_id END
            FROM billing_invoices AS invoice
            LEFT JOIN billing_operations AS operation
                ON operation.id = invoice.operation_id AND operation.workspace_id = invoice.workspace_id
            CROSS JOIN LATERAL jsonb_each(
                NULLIF(invoice.plan_snapshot::jsonb->'receipt_observations', 'null'::jsonb)
            ) AS entry
            CROSS JOIN LATERAL (VALUES (
                entry.value->>'environment', entry.value->>'shop_id', entry.value->>'provider_receipt_id',
                entry.value->>'parent_kind', entry.value->>'provider_parent_id'
            )) AS fields(environment, shop_id, receipt_id, kind, parent_id)
            LEFT JOIN observed_provider_refunds AS refund
                ON refund.invoice_id = invoice.id AND refund.workspace_id = invoice.workspace_id
                AND refund.shop_environment = fields.environment AND refund.provider_refund_id = fields.parent_id
                AND fields.kind = 'refund';
            IF EXISTS (
                SELECT 1 FROM billing_receipt_identities WHERE parent_kind = 'payment'
                GROUP BY workspace_id, invoice_id HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION 'Historical receipt identities conflict';
            END IF;
        EXCEPTION WHEN data_exception OR integrity_constraint_violation THEN
            RAISE EXCEPTION 'Historical receipt identities are inconsistent';
        END $$;
    """)
    predicate = f"""session_user = '{ROLE}' AND current_user = '{ROLE}'
        AND current_setting('row_security') = 'on'
        AND rec_context_kind() = 'maintenance' AND rec_maintenance_allowed()
        AND rec_setting('app.maintenance_operation') = 'billing_reconciliation'
        AND rec_setting('app.maintenance_feature_area') = 'billing'"""
    op.execute(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY receipt_identity_read ON {TABLE} FOR SELECT USING ({predicate})")
    op.execute(f"CREATE POLICY receipt_identity_add ON {TABLE} FOR INSERT WITH CHECK ({predicate})")
    op.execute(f"""
        DO $$ BEGIN
            REVOKE ALL ON {TABLE} FROM PUBLIC;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'twobrain_rec_app') THEN
                REVOKE ALL ON {TABLE} FROM twobrain_rec_app;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'twobrain_rec_media') THEN
                REVOKE ALL ON {TABLE} FROM twobrain_rec_media;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ROLE}') THEN
                REVOKE ALL ON {TABLE} FROM {ROLE};
                GRANT SELECT, INSERT ON {TABLE} TO {ROLE};
            END IF;
        END $$;
    """)
    op.execute("SET LOCAL row_security = on")


def downgrade():
    op.drop_table(TABLE)
