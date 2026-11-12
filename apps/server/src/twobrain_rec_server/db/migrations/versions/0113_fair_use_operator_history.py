"""Protect fair-use transitions and automatically record their bounded history."""
from importlib import import_module

from alembic import op

revision = "0113_fair_use_operator_history"
down_revision = "0112_storage_notifications"
branch_labels = None
depends_on = None

WRITER = "twobrain_rec_fair_use_audit_writer"
RUNTIME = ("twobrain_rec_app", "twobrain_rec_maintenance", "twobrain_rec_media")
AUDIT_COLUMNS = "id,workspace_id,actor_user_id,action,target_kind,target_ref,outcome,reason_code,metadata_json,created_at"
REVIEW_INSERT = "id,workspace_id,subject_user_id,capability,reason_code,evidence_ref,starts_at,review_by,state"
APP_UPDATE = "state,appealed_at,appeal_ref,updated_at"
OPERATOR_UPDATE = "state,resolved_at,resolution_code,updated_at"
# Qualify nested calls without disabling the existing SQL wrappers' inlining.
CONTEXT_HELPERS = {
    "rec_setting_uuid(name text)": ("uuid", """
        WITH value(raw_value) AS (SELECT public.rec_setting(name))
        SELECT CASE WHEN raw_value ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            THEN raw_value::uuid ELSE NULL END FROM value
    """),
    "rec_context_kind()": ("text", "SELECT public.rec_setting('app.context_kind')"),
    "rec_current_organization_id()": ("uuid", "SELECT public.rec_setting_uuid('app.organization_id')"),
    "rec_current_workspace_id()": ("uuid", "SELECT public.rec_setting_uuid('app.workspace_id')"),
    "rec_current_user_id()": ("uuid", "SELECT public.rec_setting_uuid('app.user_id')"),
    "rec_current_device_id()": ("uuid", "SELECT public.rec_setting_uuid('app.device_id')"),
    "rec_auth_session_token_hash()": ("text", "SELECT public.rec_setting('app.auth_session_token_hash')"),
    "rec_auth_callback_state_nonce()": ("text", "SELECT public.rec_setting('app.auth_callback_state_nonce')"),
}
_operations = import_module("twobrain_rec_server.db.migrations.versions.0102_summary_sharing").CURRENT_OPERATIONS
CONTEXT_HELPERS["rec_maintenance_allowed()"] = ("boolean", f"""
    SELECT session_user = 'twobrain_rec_maintenance'
        AND public.rec_setting('app.context_kind') = 'maintenance'
        AND public.rec_setting('app.maintenance_operation') = ANY(ARRAY[{','.join(repr(x) for x in _operations)}])
        AND public.rec_setting('app.maintenance_actor') IS NOT NULL
        AND public.rec_setting('app.maintenance_reason') IS NOT NULL
        AND public.rec_setting('app.maintenance_feature_area') IS NOT NULL
        OR (session_user = 'twobrain_rec_app' AND public.rec_account_merge_context_valid())
""")
OPERATOR = """
    session_user = 'twobrain_rec_maintenance' AND current_user = session_user
    AND current_setting('row_security') = 'on'
    AND public.rec_context_kind() = 'maintenance' AND public.rec_maintenance_allowed()
    AND public.rec_setting('app.maintenance_operation') = 'billing_reconciliation'
    AND public.rec_setting('app.maintenance_feature_area') = 'billing'
    AND EXISTS (SELECT FROM pg_catalog.pg_roles r WHERE r.rolname = current_user
        AND r.rolcanlogin AND NOT (r.rolsuper OR r.rolbypassrls OR r.rolcreatedb
            OR r.rolcreaterole OR r.rolreplication OR r.rolinherit))
"""
READ_SCOPE = """
    (public.rec_context_kind() IN ('request','worker') AND (
        (workspace_id = public.rec_current_workspace_id() AND (
            subject_user_id = public.rec_current_user_id() OR EXISTS (
                SELECT FROM public.workspaces w
                WHERE w.id = fair_use_reviews.workspace_id
                  AND w.owner_user_id = public.rec_current_user_id())))
        OR (public.rec_current_user_lineage_contains(subject_user_id)
            AND public.rec_current_user_owns_lineage_workspace(workspace_id))))
    OR public.rec_maintenance_allowed()
"""
APPEAL_SCOPE = """
    session_user = 'twobrain_rec_app' AND current_user = session_user
    AND current_setting('row_security') = 'on'
    AND public.rec_context_kind() = 'request' AND (
        (workspace_id = public.rec_current_workspace_id()
            AND subject_user_id = public.rec_current_user_id())
        OR (public.rec_current_user_lineage_contains(subject_user_id)
            AND public.rec_current_user_owns_lineage_workspace(workspace_id)))
"""

REVIEW_GUARD = f"""
DECLARE
    operator_allowed boolean := ({OPERATOR});
    request_allowed boolean;
    accepted_at timestamptz := pg_catalog.transaction_timestamp();
BEGIN
    IF TG_RELID <> 'public.fair_use_reviews'::regclass OR TG_LEVEL <> 'ROW'
       OR TG_WHEN <> 'BEFORE' OR TG_OP NOT IN ('INSERT','UPDATE','DELETE') THEN
        RAISE EXCEPTION 'fair_use_transition_rejected';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'fair_use_history_protected';
    END IF;
    request_allowed := session_user = 'twobrain_rec_app' AND current_user = session_user
        AND current_setting('row_security') = 'on'
        AND public.rec_context_kind() = 'request' AND (
            (NEW.workspace_id = public.rec_current_workspace_id()
                AND NEW.subject_user_id = public.rec_current_user_id())
            OR (public.rec_current_user_lineage_contains(NEW.subject_user_id)
                AND public.rec_current_user_owns_lineage_workspace(NEW.workspace_id)));
    IF operator_allowed THEN
        IF NOT coalesce(public.rec_setting('app.fair_use_operator_ref') COLLATE "C"
                        ~ '^op-[0-9a-f]{{32}}$', false)
           OR length(public.rec_setting('app.fair_use_operator_ref')) <> 35
           OR public.rec_setting('app.fair_use_evidence_reviewed') IS DISTINCT FROM 'true' THEN
            RAISE EXCEPTION 'fair_use_operator_declaration_rejected';
        END IF;
    ELSIF NOT coalesce(request_allowed, false) OR TG_OP = 'INSERT' THEN
        RAISE EXCEPTION 'fair_use_authority_rejected';
    END IF;
    IF TG_OP = 'INSERT' THEN
        IF NEW.state IS DISTINCT FROM 'notice' OR NEW.capability NOT IN ('server_processing','storage')
           OR NEW.appealed_at IS NOT NULL OR NEW.appeal_ref IS NOT NULL
           OR NEW.resolved_at IS NOT NULL OR NEW.resolution_code IS NOT NULL THEN
            RAISE EXCEPTION 'fair_use_transition_rejected';
        END IF;
        NEW.starts_at := accepted_at;
        NEW.review_by := accepted_at + interval '24 hours';
        NEW.created_at := accepted_at;
        NEW.updated_at := accepted_at;
        RETURN NEW;
    END IF;
    IF (to_jsonb(NEW) - ARRAY['state','appealed_at','appeal_ref','resolved_at','resolution_code','updated_at'])
       IS DISTINCT FROM
       (to_jsonb(OLD) - ARRAY['state','appealed_at','appeal_ref','resolved_at','resolution_code','updated_at']) THEN
        RAISE EXCEPTION 'fair_use_history_protected';
    END IF;
    IF (to_jsonb(NEW) - 'updated_at') = (to_jsonb(OLD) - 'updated_at') THEN
        NEW.updated_at := OLD.updated_at;
        RETURN NEW;
    END IF;
    IF NOT isfinite(OLD.starts_at) OR NOT isfinite(OLD.review_by)
       OR OLD.review_by < OLD.starts_at OR OLD.review_by > OLD.starts_at + interval '24 hours'
       OR OLD.starts_at > accepted_at OR OLD.state NOT IN ('notice','restricted','appealed')
       OR OLD.resolved_at IS NOT NULL OR OLD.resolution_code IS NOT NULL THEN
        RAISE EXCEPTION 'fair_use_transition_rejected';
    END IF;
    IF request_allowed AND OLD.state IN ('notice','restricted') AND NEW.state = 'appealed'
       AND OLD.appealed_at IS NULL AND OLD.appeal_ref IS NULL
       AND NEW.resolved_at IS NULL AND NEW.resolution_code IS NULL THEN
        NEW.appealed_at := accepted_at;
        NEW.appeal_ref := 'appeal:' || left(replace(NEW.id::text, '-', ''), 24);
    ELSIF operator_allowed AND NEW.state IN ('cleared','confirmed')
       AND NEW.appealed_at IS NOT DISTINCT FROM OLD.appealed_at
       AND NEW.appeal_ref IS NOT DISTINCT FROM OLD.appeal_ref
       AND ((NEW.state = 'cleared' AND NEW.resolution_code IN ('not_substantiated','no_longer_applicable'))
            OR (NEW.state = 'confirmed' AND NEW.resolution_code = 'basis_confirmed'))
       AND EXISTS (SELECT FROM public.billing_audit_events a
            WHERE a.workspace_id = OLD.workspace_id AND a.target_ref = OLD.id::text
              AND a.action = 'fair_use.review.created' AND a.target_kind = 'fair_use_review') THEN
        NEW.resolved_at := accepted_at;
    ELSE
        RAISE EXCEPTION 'fair_use_transition_rejected';
    END IF;
    NEW.updated_at := accepted_at;
    RETURN NEW;
END
"""

AUDIT_WRITER = f"""
DECLARE
    phase text;
    previous_state text;
    recorded_at timestamptz;
    from_request boolean := false;
BEGIN
    IF current_user <> '{WRITER}' OR current_setting('row_security') <> 'on'
       OR TG_RELID <> 'public.fair_use_reviews'::regclass OR TG_LEVEL <> 'ROW'
       OR TG_WHEN <> 'AFTER' OR TG_OP NOT IN ('INSERT','UPDATE') THEN
        RAISE EXCEPTION 'fair_use_audit_rejected';
    END IF;
    IF TG_OP = 'INSERT' THEN
        phase := 'created'; recorded_at := NEW.starts_at;
    ELSIF NEW.state IS NOT DISTINCT FROM OLD.state THEN
        RETURN NULL;
    ELSIF NEW.state = 'appealed' THEN
        phase := 'appealed'; recorded_at := NEW.appealed_at;
        previous_state := OLD.state; from_request := true;
    ELSIF NEW.state IN ('cleared','confirmed') THEN
        phase := 'resolved'; recorded_at := NEW.resolved_at; previous_state := OLD.state;
    ELSE
        RAISE EXCEPTION 'fair_use_audit_rejected';
    END IF;
    INSERT INTO public.billing_audit_events ({AUDIT_COLUMNS}) VALUES (
        pg_catalog.gen_random_uuid(), NEW.workspace_id,
        CASE WHEN from_request THEN public.rec_current_user_id() ELSE NULL END,
        'fair_use.review.' || phase, 'fair_use_review', NEW.id::text, 'applied',
        CASE WHEN phase = 'resolved' THEN NEW.resolution_code ELSE NULL END,
        jsonb_build_object('version',1,'source',CASE WHEN from_request THEN 'request' ELSE 'maintenance' END,
            'previous_state',previous_state,'state',NEW.state,'db_login',session_user,
            'db_writer',current_user,'declared_operator',
                CASE WHEN from_request THEN NULL ELSE public.rec_setting('app.fair_use_operator_ref') END,
            'external_evidence_reviewed',CASE WHEN from_request THEN NULL::boolean ELSE true END),
        recorded_at);
    RETURN NULL;
END
"""

AUDIT_GUARD = f"""
DECLARE
    old_reserved boolean := false;
    new_reserved boolean := false;
    meta jsonb;
    request_event boolean;
BEGIN
    IF TG_RELID <> 'public.billing_audit_events'::regclass OR TG_LEVEL <> 'ROW'
       OR TG_WHEN <> 'BEFORE' OR TG_OP NOT IN ('INSERT','UPDATE','DELETE') THEN
        RAISE EXCEPTION 'fair_use_audit_rejected';
    END IF;
    IF TG_OP <> 'INSERT' THEN
        old_reserved := left(OLD.action,9) = 'fair_use.' OR OLD.target_kind = 'fair_use_review';
    END IF;
    IF TG_OP <> 'DELETE' THEN
        new_reserved := left(NEW.action,9) = 'fair_use.' OR NEW.target_kind = 'fair_use_review';
    END IF;
    IF TG_OP <> 'INSERT' AND (old_reserved OR new_reserved) THEN
        RAISE EXCEPTION 'fair_use_history_protected';
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    IF NOT new_reserved THEN
        IF current_user = '{WRITER}' THEN RAISE EXCEPTION 'fair_use_audit_rejected'; END IF;
        RETURN NEW;
    END IF;
    IF current_user <> '{WRITER}' OR current_setting('row_security') <> 'on' THEN
        RAISE EXCEPTION 'fair_use_audit_rejected';
    END IF;
    meta := NEW.metadata_json::jsonb;
    request_event := NEW.action = 'fair_use.review.appealed';
    IF NEW.id IS NULL OR NEW.workspace_id IS NULL
       OR NEW.target_kind IS DISTINCT FROM 'fair_use_review' OR NEW.outcome IS DISTINCT FROM 'applied'
       OR NOT coalesce(NEW.target_ref COLLATE "C" ~ '^[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}$',false)
       OR NEW.created_at IS NULL OR NOT isfinite(NEW.created_at)
       OR jsonb_typeof(meta) IS DISTINCT FROM 'object'
       OR NOT coalesce(meta ?& ARRAY['version','source','previous_state','state','db_login','db_writer','declared_operator','external_evidence_reviewed'],false)
       OR meta - ARRAY['version','source','previous_state','state','db_login','db_writer','declared_operator','external_evidence_reviewed'] <> '{{}}'::jsonb
       OR jsonb_typeof(meta->'version') IS DISTINCT FROM 'number' OR meta->'version' <> '1'::jsonb
       OR meta->'db_writer' IS DISTINCT FROM to_jsonb(current_user::text)
       OR meta->'db_login' IS DISTINCT FROM to_jsonb(session_user::text) THEN
        RAISE EXCEPTION 'fair_use_audit_rejected';
    END IF;
    IF request_event THEN
        IF session_user <> 'twobrain_rec_app' OR NEW.actor_user_id IS NULL
           OR NEW.actor_user_id IS DISTINCT FROM public.rec_current_user_id()
           OR NEW.reason_code IS NOT NULL OR meta->>'source' IS DISTINCT FROM 'request'
           OR meta->>'state' IS DISTINCT FROM 'appealed'
           OR NOT coalesce(meta->>'previous_state' IN ('notice','restricted'),false)
           OR meta->'declared_operator' IS DISTINCT FROM 'null'::jsonb
           OR meta->'external_evidence_reviewed' IS DISTINCT FROM 'null'::jsonb THEN
            RAISE EXCEPTION 'fair_use_audit_rejected';
        END IF;
    ELSE
        IF session_user <> 'twobrain_rec_maintenance' OR NEW.actor_user_id IS NOT NULL
           OR meta->>'source' IS DISTINCT FROM 'maintenance'
           OR jsonb_typeof(meta->'declared_operator') IS DISTINCT FROM 'string'
           OR NOT coalesce(meta->>'declared_operator' COLLATE "C" ~ '^op-[0-9a-f]{{32}}$',false)
           OR length(meta->>'declared_operator') <> 35
           OR meta->'external_evidence_reviewed' IS DISTINCT FROM 'true'::jsonb THEN
            RAISE EXCEPTION 'fair_use_audit_rejected';
        END IF;
        IF NEW.action = 'fair_use.review.created' THEN
            IF meta->>'state' IS DISTINCT FROM 'notice' OR NEW.reason_code IS NOT NULL
               OR meta->'previous_state' IS DISTINCT FROM 'null'::jsonb THEN
                RAISE EXCEPTION 'fair_use_audit_rejected';
            END IF;
        ELSIF NEW.action = 'fair_use.review.resolved' THEN
            IF NOT coalesce(meta->>'previous_state' IN ('notice','restricted','appealed'),false)
               OR NOT coalesce((meta->>'state' = 'cleared' AND NEW.reason_code IN ('not_substantiated','no_longer_applicable'))
                   OR (meta->>'state' = 'confirmed' AND NEW.reason_code = 'basis_confirmed'),false) THEN
                RAISE EXCEPTION 'fair_use_audit_rejected';
            END IF;
        ELSE
            RAISE EXCEPTION 'fair_use_audit_rejected';
        END IF;
    END IF;
    RETURN NEW;
END
"""

TRUNCATE_GUARD = """
BEGIN
    IF TG_WHEN <> 'BEFORE' OR TG_OP <> 'TRUNCATE' OR TG_LEVEL <> 'STATEMENT'
       OR TG_RELID NOT IN ('public.fair_use_reviews'::regclass,'public.billing_audit_events'::regclass)
       OR session_user <> current_user OR NOT EXISTS (
           SELECT FROM pg_catalog.pg_class c WHERE c.oid = TG_RELID
             AND c.relowner = (SELECT oid FROM pg_catalog.pg_roles WHERE rolname = current_user)) THEN
        RAISE EXCEPTION 'fair_use_history_protected';
    END IF;
    RETURN NULL;
END
"""

FUNCTIONS = {
    "rec_guard_fair_use_review": REVIEW_GUARD,
    "rec_append_fair_use_audit": AUDIT_WRITER,
    "rec_guard_fair_use_audit": AUDIT_GUARD,
    "rec_guard_fair_use_truncate": TRUNCATE_GUARD,
}
TRIGGERS = (
    ("fair_use_reviews", "fair_use_review_guard", "rec_guard_fair_use_review", "BEFORE INSERT OR UPDATE OR DELETE", 31),
    ("fair_use_reviews", "fair_use_audit_append", "rec_append_fair_use_audit", "AFTER INSERT OR UPDATE", 21),
    ("billing_audit_events", "fair_use_audit_guard", "rec_guard_fair_use_audit", "BEFORE INSERT OR UPDATE OR DELETE", 31),
    ("fair_use_reviews", "fair_use_review_truncate_guard", "rec_guard_fair_use_truncate", "BEFORE TRUNCATE", 34),
    ("billing_audit_events", "fair_use_audit_truncate_guard", "rec_guard_fair_use_truncate", "BEFORE TRUNCATE", 34),
)

POLICIES = {
    "fair_use_reviews": {
        "fair_use_review_read": f"FOR SELECT USING ({READ_SCOPE})",
        "fair_use_review_create": f"FOR INSERT WITH CHECK ({OPERATOR})",
        "fair_use_review_update": f"FOR UPDATE USING ({READ_SCOPE}) WITH CHECK (({OPERATOR}) OR ({APPEAL_SCOPE}))",
    },
    "billing_audit_events": {
        "billing_audit_events_tenant_isolation": "USING ((public.rec_context_kind() IN ('request','worker') AND workspace_id=public.rec_current_workspace_id()) OR public.rec_maintenance_allowed()) WITH CHECK ((public.rec_context_kind() IN ('request','worker') AND workspace_id=public.rec_current_workspace_id()) OR public.rec_maintenance_allowed())",
        "fair_use_audit_append": f"FOR INSERT TO {WRITER} WITH CHECK (current_user='{WRITER}' AND current_setting('row_security')='on')",
    },
}
INDEX = "uq_fair_use_audit_transition"
INDEX_DEFINITION = "(workspace_id,target_ref,action) WHERE left(action,9)='fair_use.' OR target_kind='fair_use_review'"


def runtime_grants(role):
    columns = ",".join((REVIEW_INSERT, "appealed_at,appeal_ref,resolved_at,resolution_code,created_at,updated_at"))
    statements = [
        f"REVOKE ALL ON public.fair_use_reviews FROM {role}",
        f"REVOKE ALL ({columns}) ON public.fair_use_reviews FROM {role}",
        f"REVOKE ALL ON FUNCTION {','.join('public.'+name+'()' for name in FUNCTIONS)} FROM {role}",
        f"REVOKE SET ON PARAMETER session_replication_role FROM {role}",
    ]
    if role in RUNTIME[:2]:
        statements += [f"GRANT SELECT ON public.fair_use_reviews TO {role}",
                       f"GRANT UPDATE ({APP_UPDATE if role == RUNTIME[0] else OPERATOR_UPDATE}) ON public.fair_use_reviews TO {role}"]
    if role == RUNTIME[1]:
        statements += [f"GRANT INSERT ({REVIEW_INSERT}) ON public.fair_use_reviews TO {role}"]
    return statements


def upgrade():
    op.execute("LOCK TABLE public.fair_use_reviews, public.billing_audit_events IN ACCESS EXCLUSIVE MODE")
    for signature, (returns, body) in CONTEXT_HELPERS.items():
        op.execute(f"CREATE OR REPLACE FUNCTION public.{signature} RETURNS {returns} LANGUAGE sql STABLE SECURITY INVOKER AS $function${body}$function$")
    op.execute("SET LOCAL row_security = off")
    op.execute(f"""
        DO $$ BEGIN
            PERFORM pg_advisory_xact_lock(3273310113);
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{WRITER}') THEN
                BEGIN CREATE ROLE {WRITER} NOLOGIN NOINHERIT;
                EXCEPTION WHEN duplicate_object OR unique_violation THEN NULL; END;
            END IF;
            IF NOT EXISTS (SELECT FROM pg_roles r WHERE r.rolname = '{WRITER}'
                AND NOT (r.rolcanlogin OR r.rolinherit OR r.rolsuper OR r.rolbypassrls
                    OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication)
                AND NOT EXISTS (SELECT FROM pg_auth_members m WHERE r.oid IN (m.roleid,m.member))
                AND NOT has_schema_privilege(r.oid,'public','CREATE')
                AND NOT EXISTS (SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname !~ '^pg_' AND n.nspname <> 'information_schema' AND (
                        c.relowner=r.oid OR CASE WHEN c.relkind='S' THEN has_sequence_privilege(r.oid,c.oid,'USAGE,SELECT,UPDATE')
                        WHEN c.relkind IN ('r','p','v','m','f') THEN has_table_privilege(r.oid,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
                            OR has_any_column_privilege(r.oid,c.oid,'SELECT,INSERT,UPDATE,REFERENCES') ELSE false END))
                AND NOT EXISTS (SELECT FROM pg_proc p WHERE p.proowner=r.oid)) THEN
                RAISE EXCEPTION 'fair_use_writer_unsafe';
            END IF;
            IF EXISTS (SELECT FROM public.billing_audit_events
                WHERE left(action,9)='fair_use.' OR target_kind='fair_use_review') THEN
                RAISE EXCEPTION 'fair_use_legacy_audit_conflict';
            END IF;
        END $$;
    """)
    op.execute("SET LOCAL row_security = on")
    op.execute("DROP POLICY fair_use_reviews_tenant_isolation ON public.fair_use_reviews")
    for table, policies in POLICIES.items():
        for name, definition in policies.items():
            if name != "billing_audit_events_tenant_isolation":
                op.execute(f"CREATE POLICY {name} ON public.{table} {definition}")
    op.execute(f"CREATE UNIQUE INDEX {INDEX} ON public.billing_audit_events {INDEX_DEFINITION}")
    for name, body in FUNCTIONS.items():
        security = "SECURITY DEFINER" if name == "rec_append_fair_use_audit" else "SECURITY INVOKER"
        op.execute(f"CREATE FUNCTION public.{name}() RETURNS trigger LANGUAGE plpgsql {security} SET search_path=pg_catalog,pg_temp SET row_security=on AS $function${body}$function$")
        op.execute(f"REVOKE ALL ON FUNCTION public.{name}() FROM PUBLIC")
    op.execute(f"GRANT USAGE ON SCHEMA public TO {WRITER}")
    op.execute(f"GRANT INSERT ({AUDIT_COLUMNS}) ON public.billing_audit_events TO {WRITER}")
    op.execute(f"ALTER FUNCTION public.rec_append_fair_use_audit() OWNER TO {WRITER}")
    for table, name, function, events, flags in TRIGGERS:
        level = "ROW" if flags & 1 else "STATEMENT"
        op.execute(f"CREATE TRIGGER {name} {events} ON public.{table} FOR EACH {level} EXECUTE FUNCTION public.{function}()")
        op.execute(f"ALTER TABLE public.{table} ENABLE ALWAYS TRIGGER {name}")
    for statement in runtime_grants("PUBLIC"):
        op.execute(statement)
    for role in RUNTIME:
        op.execute(f"""DO $$ BEGIN IF EXISTS (SELECT FROM pg_roles WHERE rolname='{role}') THEN
            {'; '.join(runtime_grants(role))}; END IF; END $$""")


def downgrade():
    op.execute("LOCK TABLE public.fair_use_reviews, public.billing_audit_events IN ACCESS EXCLUSIVE MODE")
    op.execute("SET LOCAL row_security = off")
    op.execute("""DO $$ BEGIN IF EXISTS (SELECT FROM public.billing_audit_events
        WHERE left(action,9)='fair_use.' OR target_kind='fair_use_review') THEN
        RAISE EXCEPTION 'fair_use_downgrade_history_protected'; END IF; END $$""")
    op.execute("SET LOCAL row_security = on")
    for table, name, *_ in reversed(TRIGGERS):
        op.execute(f"DROP TRIGGER {name} ON public.{table}")
    for name in FUNCTIONS:
        op.execute(f"DROP FUNCTION public.{name}()")
    op.execute("DROP INDEX public.uq_fair_use_audit_transition")
    op.execute("DROP POLICY fair_use_audit_append ON public.billing_audit_events")
    op.execute(f"REVOKE ALL ({AUDIT_COLUMNS}) ON public.billing_audit_events FROM {WRITER}")
    for name in ("fair_use_review_read", "fair_use_review_create", "fair_use_review_update"):
        op.execute(f"DROP POLICY {name} ON public.fair_use_reviews")
    previous = import_module("twobrain_rec_server.db.migrations.versions.0074_linked_workspace_and_merge_proofs")
    op.execute(previous.FAIR_USE_LINEAGE_POLICY)
    for role in RUNTIME[:2]:
        op.execute(f"""DO $$ BEGIN IF EXISTS (SELECT FROM pg_roles WHERE rolname='{role}') THEN
            GRANT SELECT,INSERT,UPDATE,DELETE ON public.fair_use_reviews TO {role}; END IF; END $$""")
