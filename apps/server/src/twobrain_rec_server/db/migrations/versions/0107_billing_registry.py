"""Atomic, maintenance-only metadata receipts for operator registry import."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0107_billing_registry"
down_revision = "0106_activation_milestones"
branch_labels = None
depends_on = None

IMPORTS = "billing_registry_imports"
GAPS = "billing_registry_gaps"
ROLE = "twobrain_rec_maintenance"


def _scope():
    return [sa.Column("environment", sa.String(10), nullable=False),
            sa.Column("shop_id", sa.String(32), nullable=False),
            sa.Column("report_date", sa.Date(), nullable=False),
            sa.CheckConstraint("environment IN ('test','production')", name="registry_environment"),
            sa.CheckConstraint("shop_id ~ '^[0-9]{1,32}$'", name="registry_shop")]


def upgrade():
    op.create_table(
        IMPORTS, sa.Column("id", sa.BigInteger(), primary_key=True), *_scope(),
        sa.Column("profile", sa.String(64), nullable=False),
        sa.Column("config_fingerprint", sa.String(64), nullable=False),
        sa.Column("input_digest", sa.String(64)),
        sa.Column("parts", JSONB(), nullable=False),
        sa.Column("expected_empty", JSONB(), nullable=False),
        sa.Column("accepted", sa.Boolean(), nullable=False),
        sa.Column("files_complete", sa.Boolean(), nullable=False),
        sa.Column("result_code", sa.String(64), nullable=False),
        sa.Column("previous_accepted_id", sa.BigInteger(), sa.ForeignKey(f"{IMPORTS}.id")),
        sa.Column("operator", sa.String(64), nullable=False),
        sa.Column("reason_code", sa.String(32), nullable=False),
        sa.Column("session_identity", sa.String(64), nullable=False, server_default=sa.text("session_user")),
        sa.Column("current_identity", sa.String(64), nullable=False, server_default=sa.text("current_user")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.clock_timestamp()),
        sa.CheckConstraint("config_fingerprint ~ '^[a-f0-9]{64}$' AND (input_digest IS NULL OR input_digest ~ '^[a-f0-9]{64}$')", name="registry_digest"),
        sa.CheckConstraint("NOT accepted OR input_digest IS NOT NULL", name="registry_accepted_digest"),
        sa.CheckConstraint("NOT files_complete OR accepted", name="registry_complete"),
        sa.CheckConstraint("operator ~ '^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$'", name="registry_operator"),
        sa.CheckConstraint("jsonb_typeof(parts) = 'array' AND jsonb_array_length(parts) <= 64 AND octet_length(parts::text) <= 32768", name="registry_parts_bound"),
        sa.CheckConstraint("jsonb_typeof(expected_empty) = 'array' AND jsonb_array_length(expected_empty) <= 2", name="registry_empty_bound"),
        sa.CheckConstraint(f"session_identity = '{ROLE}' AND current_identity = '{ROLE}'", name="registry_identity"),
    )
    scope = ["environment", "shop_id", "report_date"]
    op.create_index("ix_registry_import_scope", IMPORTS, [*scope, "id"])
    op.create_index("uq_registry_accepted_digest", IMPORTS, [*scope, "profile", "config_fingerprint", "input_digest"], unique=True, postgresql_where=sa.text("accepted"))
    op.create_table(
        GAPS, sa.Column("id", sa.BigInteger(), primary_key=True), *_scope(),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("part_index", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(64), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("owner", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(4), nullable=False, server_default="high"),
        sa.Column("containment", sa.String(24), nullable=False, server_default="report_unverified"),
        sa.Column("state", sa.String(8), nullable=False, server_default="detected"),
        sa.Column("detected_receipt_id", sa.BigInteger(), sa.ForeignKey(f"{IMPORTS}.id"), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closing_receipt_id", sa.BigInteger(), sa.ForeignKey(f"{IMPORTS}.id")),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolution_code", sa.String(32)),
        sa.Column("resolved_by", sa.String(64)),
        sa.UniqueConstraint(*scope, "kind", "part_index", "reason", "generation", name="uq_registry_gap_generation"),
        sa.CheckConstraint("kind IN ('payments','refunds','input') AND part_index BETWEEN 0 AND 64 AND generation > 0", name="registry_gap_key"),
        sa.CheckConstraint("owner ~ '^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$' AND severity = 'high' AND containment = 'report_unverified'", name="registry_gap_owner"),
        sa.CheckConstraint("checked_at >= detected_at AND deadline_at >= detected_at AND deadline_at <= detected_at + interval '24 hours'", name="registry_gap_deadline"),
        sa.CheckConstraint("(state = 'detected' AND closing_receipt_id IS NULL AND resolved_at IS NULL AND resolution_code IS NULL AND resolved_by IS NULL) OR (state = 'resolved' AND closing_receipt_id IS NOT NULL AND resolved_at IS NOT NULL AND resolved_at >= detected_at AND resolution_code IS NOT NULL AND resolved_by IS NOT NULL AND resolved_by ~ '^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$')", name="registry_gap_resolution"),
    )
    op.create_index("uq_registry_open_gap", GAPS, [*scope, "kind", "part_index", "reason"], unique=True, postgresql_where=sa.text("state = 'detected'"))
    op.execute("""CREATE FUNCTION rec_registry_history_guard() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' OR TG_TABLE_NAME = 'billing_registry_imports' THEN
                RAISE EXCEPTION 'registry history is immutable';
            END IF;
            IF OLD.state = 'resolved' OR
                ROW(NEW.id,NEW.environment,NEW.shop_id,NEW.report_date,NEW.kind,NEW.part_index,NEW.reason,NEW.generation,NEW.owner,NEW.severity,NEW.containment,NEW.detected_receipt_id,NEW.detected_at,NEW.deadline_at)
                IS DISTINCT FROM ROW(OLD.id,OLD.environment,OLD.shop_id,OLD.report_date,OLD.kind,OLD.part_index,OLD.reason,OLD.generation,OLD.owner,OLD.severity,OLD.containment,OLD.detected_receipt_id,OLD.detected_at,OLD.deadline_at) THEN
                RAISE EXCEPTION 'registry gap history is immutable';
            END IF;
            IF NEW.state = 'resolved' AND NOT EXISTS
                (SELECT 1 FROM billing_registry_imports r WHERE r.id = NEW.closing_receipt_id AND r.accepted
                 AND r.environment = NEW.environment AND r.shop_id = NEW.shop_id AND r.report_date = NEW.report_date) THEN
                RAISE EXCEPTION 'registry resolution requires accepted receipt';
            END IF;
            RETURN NEW;
        END $$""")
    predicate = f"""session_user = '{ROLE}' AND current_user = '{ROLE}'
        AND current_setting('row_security') = 'on'
        AND rec_context_kind() = 'maintenance' AND rec_maintenance_allowed()
        AND rec_setting('app.maintenance_operation') = 'billing_reconciliation'
        AND rec_setting('app.maintenance_feature_area') = 'billing'"""
    for table in (IMPORTS, GAPS):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY registry_maintenance ON {table} USING ({predicate}) WITH CHECK ({predicate})")
        op.execute(f"CREATE TRIGGER registry_history_guard BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION rec_registry_history_guard()")
        op.execute(f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ROLE}') THEN GRANT SELECT,INSERT,UPDATE ON {table} TO {ROLE}; GRANT USAGE ON SEQUENCE {table}_id_seq TO {ROLE}; END IF; END $$")


def downgrade():
    op.execute(f"LOCK TABLE {IMPORTS}, {GAPS} IN ACCESS EXCLUSIVE MODE")
    op.execute("SET LOCAL row_security = off")
    op.execute(f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM {IMPORTS}) OR EXISTS (SELECT 1 FROM {GAPS}) THEN RAISE EXCEPTION '0107 downgrade blocked: registry history exists'; END IF; END $$")
    op.drop_table(GAPS)
    op.drop_table(IMPORTS)
    op.execute("DROP FUNCTION rec_registry_history_guard()")
