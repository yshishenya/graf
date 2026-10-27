"""Durable account-first decisions and two fixed delivery intents (F273/T113)."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0106_activation_milestones"
down_revision = "0105_anonymous_aggregate_region"
branch_labels = None
depends_on = None

TABLE = "product_activation_milestones"
STATES = (
    "not_requested",
    "pending",
    "pre_send_retry",
    "dispatching",
    "submitted",
    "ambiguous",
    "confirmed",
    "cancelled",
    "rejected",
)
REASONS = (
    "not_requested",
    "accepted",
    "technical_pre_send",
    "dispatch_started",
    "http_accepted",
    "transport_ambiguous",
    "http_ambiguous",
    "interrupted_dispatch",
    "readback_confirmed",
    "purpose_withdrawn",
    "basis_unavailable",
    "provider_disabled",
    "payload_rejected",
    "restore_quarantine",
)
EVENTS = (
    "desktop_account_connected",
    "desktop_autorecord_enabled",
    "first_recording_completed",
    "first_result_viewed",
    "first_value_session_completed",
)


def upgrade():
    op.create_table(
        TABLE,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(),
            sa.ForeignKey("user_identities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_name", sa.String(64), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("safe_payload", JSONB(), nullable=False),
        sa.Column("source_kind", sa.String(8), nullable=False),
        *(
            column
            for provider in ("posthog", "yandex")
            for column in (
                sa.Column(
                    f"{provider}_state",
                    sa.String(16),
                    nullable=False,
                    server_default="not_requested",
                ),
                sa.Column(
                    f"{provider}_reason",
                    sa.String(80),
                    nullable=False,
                    server_default="not_requested",
                ),
                sa.Column(f"{provider}_attempt_id", sa.Uuid()),
                sa.Column(f"{provider}_attempted_at", sa.DateTime(timezone=True)),
                sa.Column(f"{provider}_confirmation_ref", sa.String(120)),
                sa.CheckConstraint(
                    f"{provider}_state IN {STATES}", name=f"activation_{provider}_state"
                ),
                sa.CheckConstraint(
                    f"{provider}_reason IN {REASONS}", name=f"activation_{provider}_reason"
                ),
            )
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("account_id", "event_name", name="uq_activation_account_event"),
        sa.CheckConstraint(f"event_name IN {EVENTS}", name="activation_event"),
        sa.CheckConstraint(
            "source_kind IN ('browser', 'desktop', 'server')", name="activation_source"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(safe_payload) = 'object' AND octet_length(convert_to(safe_payload::text, 'UTF8')) <= 16384",
            name="activation_payload_size",
        ),
    )
    for provider in ("posthog", "yandex"):
        op.create_index(
            f"ix_activation_{provider}_pending", TABLE, [f"{provider}_state", "accepted_at"]
        )
    # Freeze the original decision even when a delivery state changes.
    op.execute("""
        CREATE FUNCTION rec_activation_decision_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF ROW(NEW.id,NEW.account_id,NEW.event_name,NEW.event_id,NEW.occurred_at,NEW.accepted_at,NEW.safe_payload,NEW.source_kind)
               IS DISTINCT FROM ROW(OLD.id,OLD.account_id,OLD.event_name,OLD.event_id,OLD.occurred_at,OLD.accepted_at,OLD.safe_payload,OLD.source_kind) THEN
                RAISE EXCEPTION 'activation decision is immutable';
            END IF;
            RETURN NEW;
        END $$;
    """)
    op.execute(f"""CREATE TRIGGER activation_decision_immutable BEFORE UPDATE ON {TABLE}
            FOR EACH ROW EXECUTE FUNCTION rec_activation_decision_immutable();
    """)
    predicate = """(
        (rec_context_kind() IN ('request','worker','auth_bootstrap') AND account_id = rec_current_user_id())
        OR (session_user = 'twobrain_rec_maintenance' AND rec_maintenance_allowed())
        OR (session_user = 'twobrain_rec_maintenance' AND rec_context_kind() = 'maintenance'
            AND rec_setting('app.maintenance_operation') = 'activation_milestone_delivery'
            AND rec_setting('app.maintenance_feature_area') = 'product_analytics'
            AND rec_setting('app.maintenance_actor') IS NOT NULL
            AND rec_setting('app.maintenance_reason') IS NOT NULL)
    )"""
    op.execute(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY activation_account_isolation ON {TABLE} USING ({predicate}) WITH CHECK ({predicate})"
    )
    for role in ("twobrain_rec_app", "twobrain_rec_maintenance"):
        op.execute(
            f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN GRANT SELECT,INSERT,UPDATE,DELETE ON {TABLE} TO {role}; END IF; END $$"
        )


def downgrade():
    # A rollback must not forget first decisions and permit a second delivery.
    op.execute(f"LOCK TABLE {TABLE} IN ACCESS EXCLUSIVE MODE")
    # FORCE RLS can hide all rows from a non-BYPASSRLS table owner. Fail
    # rather than treating that filtered view as proof that the table is empty.
    op.execute("SET LOCAL row_security = off")
    op.execute(
        f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM {TABLE}) THEN RAISE EXCEPTION '0106 downgrade blocked: activation decisions exist'; END IF; END $$"
    )
    op.drop_table(TABLE)
    op.execute("DROP FUNCTION rec_activation_decision_immutable()")
