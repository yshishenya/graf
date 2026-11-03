"""Append-only maintenance observations of actual reconciliation attempts."""
import sqlalchemy as sa
from alembic import op

revision: str = "0109_reconciliation_observations"
down_revision: str | None = "0108_public_consent"
branch_labels = None
depends_on = None

TABLE = "billing_reconciliation_observations"
ROLE = "twobrain_rec_maintenance"


def upgrade():
    op.create_table(
        TABLE,
        sa.Column("namespace", sa.String(255), primary_key=True),
        sa.Column("workflow_id", sa.String(128), primary_key=True),
        sa.Column("workflow_run_id", sa.Uuid(), primary_key=True),
        sa.Column("activity_id", sa.String(255), primary_key=True),
        sa.Column("attempt", sa.Integer(), primary_key=True),
        sa.Column("event_kind", sa.String(16), primary_key=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.clock_timestamp()),
        sa.CheckConstraint("octet_length(namespace) BETWEEN 1 AND 255", name="reconciliation_namespace"),
        sa.CheckConstraint(
            "octet_length(workflow_id) <= 128 AND workflow_id ~ '^billing-reconciliation/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/v1$'",
            name="reconciliation_workflow_id",
        ),
        sa.CheckConstraint("octet_length(activity_id) BETWEEN 1 AND 255", name="reconciliation_activity_id"),
        sa.CheckConstraint("attempt BETWEEN 1 AND 2147483647", name="reconciliation_attempt"),
        sa.CheckConstraint("event_kind IN ('started','succeeded','failed','canceled')", name="reconciliation_event_kind"),
        sa.CheckConstraint("isfinite(observed_at)", name="reconciliation_observed_at"),
    )
    predicate = f"""session_user = '{ROLE}' AND current_user = '{ROLE}'
        AND current_setting('row_security') = 'on'
        AND rec_context_kind() = 'maintenance' AND rec_maintenance_allowed()
        AND rec_setting('app.maintenance_operation') = 'billing_reconciliation'
        AND rec_setting('app.maintenance_feature_area') = 'billing'"""
    op.execute(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY reconciliation_observation_maintenance ON {TABLE} USING ({predicate}) WITH CHECK ({predicate})")
    op.execute("""CREATE FUNCTION rec_reconciliation_observation_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'reconciliation observation history is immutable'; END $$""")
    op.execute(f"CREATE TRIGGER reconciliation_observation_history BEFORE UPDATE OR DELETE ON {TABLE} FOR EACH ROW EXECUTE FUNCTION rec_reconciliation_observation_immutable()")
    op.execute(f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ROLE}') THEN GRANT SELECT,INSERT ON {TABLE} TO {ROLE}; END IF; END $$")


def downgrade():
    op.execute(f"LOCK TABLE {TABLE} IN ACCESS EXCLUSIVE MODE")
    op.execute("SET LOCAL row_security = off")
    op.execute(f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM {TABLE}) THEN RAISE EXCEPTION '0109 downgrade blocked: reconciliation observations exist'; END IF; END $$")
    op.drop_table(TABLE)
    op.execute("DROP FUNCTION rec_reconciliation_observation_immutable()")
