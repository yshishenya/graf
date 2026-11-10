"""Persist anonymous receipt bases independently of invoice retention."""
import sqlalchemy as sa
from alembic import op

revision: str = "0111_receipt_observation_deltas"
down_revision: str | None = "0110_billing_receipt_identities"
branch_labels = None
depends_on = None

TABLE = "billing_receipt_observation_deltas"
WRITER = "twobrain_rec_receipt_observation_writer"
MAINTENANCE = "twobrain_rec_maintenance"
BASES = "public.rec_receipt_observation_bases(jsonb)"
TRIGGER = "public.rec_append_receipt_observation()"
COUNTS = ("canceled", "overdue_confirmed", "overdue_unknown")


def upgrade():
    op.execute("LOCK TABLE public.billing_invoices IN SHARE ROW EXCLUSIVE MODE")
    op.execute("SET LOCAL row_security = off")
    op.execute(f"""
        DO $$ BEGIN
            PERFORM pg_advisory_xact_lock(3273310111);
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{WRITER}') THEN
                BEGIN
                    CREATE ROLE {WRITER} NOLOGIN NOINHERIT;
                EXCEPTION WHEN duplicate_object OR unique_violation THEN
                    -- Roles are cluster-wide; another database can install this concurrently.
                    NULL;
                END;
            END IF;
            IF NOT EXISTS (
                SELECT FROM pg_roles r WHERE r.rolname = '{WRITER}'
                AND NOT (r.rolcanlogin OR r.rolinherit OR r.rolsuper OR r.rolbypassrls
                         OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication)
                AND NOT EXISTS (SELECT FROM pg_auth_members m WHERE r.oid IN (m.roleid, m.member))
                AND NOT has_schema_privilege(r.oid, 'public', 'CREATE')
                AND not exists (
                select from pg_class c join pg_namespace n on n.oid = c.relnamespace
                where n.nspname !~ '^pg_' and n.nspname <> 'information_schema'
                  and case
                    when c.relkind = 'S' then has_sequence_privilege(r.oid, c.oid, 'USAGE,SELECT,UPDATE')
                    when c.relkind in ('r','p','v','m','f') then
                        has_table_privilege(r.oid, c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
                        or has_any_column_privilege(r.oid, c.oid, 'SELECT,INSERT,UPDATE,REFERENCES')
                    else false
                  end
            )
            ) THEN
                RAISE EXCEPTION 'Receipt observation writer role is unsafe';
            END IF;
        END $$;
    """)
    op.create_table(
        TABLE,
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        *(sa.Column(f"{kind}_delta", sa.BigInteger(), nullable=False) for kind in COUNTS),
        sa.CheckConstraint(
            "least(canceled_delta, overdue_confirmed_delta, overdue_unknown_delta) >= 0 "
            "AND greatest(canceled_delta, overdue_confirmed_delta, overdue_unknown_delta) > 0",
            name="receipt_observation_positive_delta",
        ),
    )
    op.execute("""
        CREATE FUNCTION public.rec_receipt_observation_bases(snapshot jsonb)
        RETURNS jsonb LANGUAGE plpgsql SET search_path = pg_catalog AS $$
        DECLARE
            bases jsonb := '{}'::jsonb;
            entry record;
            kind text;
            basis jsonb;
            detected text;
            due text;
            first_pending text;
            freshness text;
            utc_pattern constant text := '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\\.[0-9]{1,6})?(Z|[+]00:00)$';
        BEGIN
            FOR entry IN
                SELECT 'payment' AS key, snapshot->'receipt_registration_timing' AS timing
                UNION ALL
                SELECT 'refund:' || r.key, r.value
                FROM jsonb_each(CASE WHEN jsonb_typeof(snapshot->'receipt_observations') = 'object'
                                     THEN snapshot->'receipt_observations' ELSE '{}'::jsonb END) r
                WHERE r.value->>'parent_kind' = 'refund'
            LOOP
                IF jsonb_typeof(entry.timing) IS DISTINCT FROM 'object' THEN
                    CONTINUE;
                END IF;
                IF entry.key <> 'payment' AND entry.timing ?| ARRAY['canceled','pending_overdue']
                   AND NOT coalesce(
                     jsonb_typeof(entry.timing->'environment') = 'string'
                     AND jsonb_typeof(entry.timing->'shop_id') = 'string'
                     AND jsonb_typeof(entry.timing->'provider_receipt_id') = 'string'
                     AND jsonb_typeof(entry.timing->'provider_parent_id') = 'string'
                     AND entry.timing->>'environment' COLLATE "C" ~ '^[a-zA-Z0-9_-]{1,32}$'
                     AND entry.timing->>'shop_id' COLLATE "C" ~ '^[a-zA-Z0-9_.-]{1,160}$'
                     AND entry.timing->>'provider_receipt_id' COLLATE "C" ~ '^[a-zA-Z0-9_.-]{1,160}$'
                     AND entry.timing->>'provider_parent_id' COLLATE "C" ~ '^[a-zA-Z0-9_.-]{1,160}$'
                     AND entry.key = 'refund:' || concat_ws(':', entry.timing->>'environment',
                         entry.timing->>'shop_id', entry.timing->>'provider_receipt_id'), false) THEN
                    RAISE EXCEPTION 'Receipt observation basis is invalid';
                END IF;
                FOREACH kind IN ARRAY ARRAY['canceled', 'pending_overdue'] LOOP
                    IF NOT entry.timing ? kind THEN
                        CONTINUE;
                    END IF;
                    basis := entry.timing->kind;
                    detected := basis->>'detected_at';
                    due := basis->>'due_at';
                    freshness := basis->>'freshness';
                    first_pending := entry.timing->>'first_confirmed_pending_at';
                    IF jsonb_typeof(basis) IS DISTINCT FROM 'object'
                       OR basis - ARRAY['detected_at','due_at','freshness'] <> '{}'::jsonb
                       OR NOT coalesce(detected ~ utc_pattern AND due ~ utc_pattern
                           AND pg_input_is_valid(detected, 'timestamptz')
                           AND pg_input_is_valid(due, 'timestamptz'), false) THEN
                        RAISE EXCEPTION 'Receipt observation basis is invalid';
                    END IF;
                    IF kind = 'canceled' THEN
                        IF freshness IS DISTINCT FROM 'confirmed' OR due::timestamptz <> detected::timestamptz THEN
                            RAISE EXCEPTION 'Receipt observation basis is invalid';
                        END IF;
                    ELSE
                        IF NOT coalesce(freshness IN ('confirmed', 'unknown') AND first_pending ~ utc_pattern
                            AND pg_input_is_valid(first_pending, 'timestamptz'), false) THEN
                            RAISE EXCEPTION 'Receipt observation basis is invalid';
                        END IF;
                        IF due::timestamptz - first_pending::timestamptz <> interval '72 hours'
                           OR detected::timestamptz < due::timestamptz THEN
                            RAISE EXCEPTION 'Receipt observation basis is invalid';
                        END IF;
                    END IF;
                    bases := bases || jsonb_build_object(entry.key || ':' || kind, basis || jsonb_build_object(
                        'kind', CASE WHEN kind = 'canceled' THEN kind ELSE 'overdue_' || freshness END
                    ));
                END LOOP;
            END LOOP;
            RETURN bases;
        END $$;
    """)
    op.execute(f"REVOKE ALL ON FUNCTION {BASES} FROM PUBLIC")
    op.execute(f"""
        INSERT INTO public.{TABLE} ({", ".join(kind + "_delta" for kind in COUNTS)})
        SELECT {", ".join(f"count(*) FILTER (WHERE b.value->>'kind' = '{kind}')" for kind in COUNTS)}
        FROM public.billing_invoices i
        CROSS JOIN LATERAL jsonb_each(public.rec_receipt_observation_bases(i.plan_snapshot::jsonb)) b
        HAVING count(*) > 0
    """)
    op.execute("SET LOCAL row_security = on")
    op.execute(f"ALTER TABLE public.{TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE public.{TABLE} FORCE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY receipt_observation_read ON public.{TABLE} FOR SELECT USING (
            session_user = '{MAINTENANCE}' AND current_user = '{MAINTENANCE}'
            AND current_setting('row_security') = 'on'
            AND public.rec_context_kind() = 'maintenance' AND public.rec_maintenance_allowed()
            AND public.rec_setting('app.maintenance_operation') = 'billing_reconciliation'
            AND public.rec_setting('app.maintenance_feature_area') = 'billing'
        )
    """)
    op.execute(f"""
        CREATE POLICY receipt_observation_append ON public.{TABLE} FOR INSERT TO {WRITER}
        WITH CHECK (current_user = '{WRITER}' AND current_setting('row_security') = 'on')
    """)
    op.execute(f"""
        CREATE FUNCTION {TRIGGER} RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog SET row_security = on AS $$
        DECLARE
            previous jsonb := '{{}}'::jsonb;
            updated jsonb;
        BEGIN
            IF TG_RELID <> 'public.billing_invoices'::regclass OR TG_WHEN <> 'AFTER'
                OR TG_LEVEL <> 'ROW' OR TG_OP NOT IN ('INSERT', 'UPDATE') THEN
                RAISE EXCEPTION 'Receipt observation trigger scope is invalid';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF OLD.plan_snapshot::jsonb IS NOT DISTINCT FROM NEW.plan_snapshot::jsonb THEN
                    RETURN NULL;
                END IF;
                previous := public.rec_receipt_observation_bases(OLD.plan_snapshot::jsonb);
            END IF;
            updated := public.rec_receipt_observation_bases(NEW.plan_snapshot::jsonb);
            IF NOT updated @> previous THEN
                RAISE EXCEPTION 'Receipt observation basis cannot change';
            END IF;
            INSERT INTO public.{TABLE} ({", ".join(kind + "_delta" for kind in COUNTS)})
            SELECT {", ".join(f"count(*) FILTER (WHERE b.value->>'kind' = '{kind}')" for kind in COUNTS)}
            FROM jsonb_each(updated) b
            WHERE NOT previous ? b.key
            HAVING count(*) > 0;
            RETURN NULL;
        END $$;
    """)
    op.execute(f"CREATE TRIGGER receipt_observation_append AFTER INSERT OR UPDATE OF plan_snapshot ON public.billing_invoices FOR EACH ROW EXECUTE FUNCTION {TRIGGER}")
    op.execute(f"REVOKE ALL ON FUNCTION {TRIGGER} FROM PUBLIC")
    op.execute(f"REVOKE ALL ON public.{TABLE} FROM PUBLIC")
    op.execute(f"REVOKE ALL ON SEQUENCE public.{TABLE}_id_seq FROM PUBLIC")
    op.execute(f"""
        DO $$ DECLARE role_name text; BEGIN
            FOR role_name IN SELECT rolname FROM pg_roles
                WHERE rolname IN ('twobrain_rec_app', 'twobrain_rec_media', '{MAINTENANCE}')
            LOOP
                EXECUTE format('REVOKE ALL ON public.{TABLE} FROM %I', role_name);
                EXECUTE format('REVOKE ALL ON SEQUENCE public.{TABLE}_id_seq FROM %I', role_name);
                EXECUTE format('REVOKE ALL ON FUNCTION {TRIGGER}, {BASES} FROM %I', role_name);
            END LOOP;
            IF EXISTS (SELECT FROM pg_roles WHERE rolname = '{MAINTENANCE}') THEN
                GRANT SELECT ON public.{TABLE} TO {MAINTENANCE};
            END IF;
        END $$;
    """)
    op.execute(f"GRANT USAGE ON SCHEMA public TO {WRITER}")
    op.execute(f"GRANT INSERT ON public.{TABLE} TO {WRITER}")
    op.execute(f"GRANT USAGE ON SEQUENCE public.{TABLE}_id_seq TO {WRITER}")
    op.execute(f"GRANT EXECUTE ON FUNCTION {BASES} TO {WRITER}")
    op.execute(f"ALTER FUNCTION {TRIGGER} OWNER TO {WRITER}")


def downgrade():
    op.execute("LOCK TABLE public.billing_invoices IN SHARE ROW EXCLUSIVE MODE")
    op.execute(f"LOCK TABLE public.{TABLE} IN ACCESS EXCLUSIVE MODE")
    op.execute("SET LOCAL row_security = off")
    op.execute(f"""
        DO $$ BEGIN
            IF EXISTS (SELECT FROM public.{TABLE}) THEN
                RAISE EXCEPTION '0111 downgrade blocked: receipt observation history exists';
            END IF;
        END $$;
    """)
    op.execute("SET LOCAL row_security = on")
    op.execute("DROP TRIGGER receipt_observation_append ON public.billing_invoices")
    op.execute(f"DROP FUNCTION {TRIGGER}")
    op.execute(f"DROP FUNCTION {BASES}")
    op.drop_table(TABLE)
