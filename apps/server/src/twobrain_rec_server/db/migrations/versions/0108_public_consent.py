"""Durable public choice control isolated from measurement (F273/T106)."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0108_public_consent"
down_revision: str | None = "0107_billing_registry"
branch_labels = None
depends_on = None
TABLE = 'public_analytics_choices'


def upgrade():
    op.create_table(
        TABLE,
        sa.Column('consent_digest', sa.String(64), primary_key=True),
        sa.Column('epoch', sa.Uuid(), nullable=False),
        sa.Column('categories', JSONB(), nullable=False),
        sa.Column('copy_version', sa.String(32)),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("consent_digest ~ '^[0-9a-f]{64}$'", name='public_consent_digest'),
        sa.CheckConstraint(
            "jsonb_typeof(categories)='array' AND categories @> '[\"necessary\"]'::jsonb "
            "AND categories <@ '[\"necessary\",\"analytics\",\"advertising_attribution\",\"behavior_replay\"]'::jsonb "
            "AND jsonb_array_length(categories) BETWEEN 1 AND 4", name='public_consent_categories'),
        sa.CheckConstraint(
            "(categories='[\"necessary\"]'::jsonb AND copy_version IS NULL) OR "
            "(jsonb_array_length(categories)>1 AND copy_version IS NOT NULL)", name='public_consent_copy'),
    )
    own = """rec_context_kind()='public_consent'
        AND consent_digest=rec_setting('app.public_consent_digest')"""
    maintenance = """session_user='twobrain_rec_maintenance'
        AND current_user='twobrain_rec_maintenance' AND rec_context_kind()='maintenance'
        AND rec_setting('app.maintenance_operation')='public_consent_control'
        AND rec_setting('app.maintenance_feature_area')='product_analytics'
        AND rec_setting('app.maintenance_actor') IS NOT NULL
        AND rec_setting('app.maintenance_reason') IS NOT NULL"""
    op.execute(f'ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY')
    op.execute(f'CREATE POLICY public_consent_isolation ON {TABLE} USING (({own}) OR ({maintenance})) WITH CHECK (({own}) OR ({maintenance}))')
    for role, privileges in [('twobrain_rec_app', 'SELECT,INSERT,UPDATE'),
                             ('twobrain_rec_maintenance', 'SELECT,UPDATE,DELETE')]:
        op.execute(f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='{role}') THEN GRANT {privileges} ON {TABLE} TO {role}; END IF; END $$")


def downgrade():
    # Forgetting a refusal could make an old grant replayable after rollback.
    op.execute(f'LOCK TABLE {TABLE} IN ACCESS EXCLUSIVE MODE')
    op.execute('SET LOCAL row_security=off')
    op.execute(f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM {TABLE}) THEN RAISE EXCEPTION '0108 downgrade blocked: public choices exist'; END IF; END $$")
    op.drop_table(TABLE)
