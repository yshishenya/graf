"""Fixed local policy/trigger catalog, not a full retention or readiness receipt.

The operator owns this physical source connection and its read-only transaction.
Routine definitions and access metadata are pinned to clean PG17 migrations
and the standard role bootstrap. Lifecycle/data and installed jobs are separate.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

from .activation_fence import ActivationHold, _require
from .legal_basis_lifecycle import LEVEL_RETENTION_CATEGORIES, LOCAL_CATEGORY_TABLES
from .retention import retention_rule

TABLES = LOCAL_CATEGORY_TABLES
# Clean PG17/Alembic head 0107, not a fingerprint supplied by the checked server.
EXPECTED_ROUTINES_SHA256 = '7563a8dc31e36bb32b916667b9c404b04c2eba0e79befd6e58a94923b41881ff'
ROUTINES_FROM = """FROM pg_catalog.pg_proc p
    JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
    JOIN pg_catalog.pg_language l ON l.oid=p.prolang
    WHERE p.oid>=16384 OR (n.nspname<>'information_schema' AND n.nspname !~ '^pg_')"""
# Clean PG17/Alembic head 0107 plus standard runtime-role bootstrap.
EXPECTED_ACCESS_SHA256 = '3b469e7bad18fcc4ecaf12d28f9190abbeb043d74451e28abf073cdb696dfd43'
# Fixed supported metadata only; no recursive schema framework or source-supplied expected.
ACCESS_QUERY = """
WITH tables AS (SELECT c.* FROM pg_catalog.pg_class c
 JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname='public' AND c.relname=ANY($1::text[])),
 constraints AS (SELECT c.* FROM pg_catalog.pg_constraint c
 WHERE c.conrelid IN(SELECT oid FROM tables) OR c.confrelid IN(SELECT oid FROM tables)),
 types AS (SELECT t.* FROM pg_catalog.pg_type t WHERE t.oid IN(SELECT reltype FROM tables)
 OR t.oid IN(SELECT y.typarray FROM pg_catalog.pg_type y WHERE y.oid IN(SELECT reltype FROM tables))),
 triggers AS (SELECT t.* FROM pg_catalog.pg_trigger t WHERE t.tgrelid IN(SELECT oid FROM tables)
 OR t.tgconstraint IN(SELECT oid FROM constraints)),
 roots(classid,objid) AS (
 SELECT 'pg_catalog.pg_class'::regclass,t.oid FROM tables t UNION
 SELECT 'pg_catalog.pg_class'::regclass,i.indexrelid FROM pg_catalog.pg_index i
 WHERE i.indrelid IN(SELECT oid FROM tables) UNION
 SELECT 'pg_catalog.pg_attrdef'::regclass,a.oid FROM pg_catalog.pg_attrdef a
 WHERE a.adrelid IN(SELECT oid FROM tables) UNION
 SELECT 'pg_catalog.pg_constraint'::regclass,c.oid FROM constraints c UNION
 SELECT 'pg_catalog.pg_type'::regclass,t.oid FROM types t UNION
 SELECT 'pg_catalog.pg_trigger'::regclass,t.oid FROM triggers t UNION
 SELECT 'pg_catalog.pg_policy'::regclass,p.oid FROM pg_catalog.pg_policy p
 WHERE p.polrelid IN(SELECT oid FROM tables) UNION
 SELECT 'pg_catalog.pg_rewrite'::regclass,r.oid FROM pg_catalog.pg_rewrite r
 WHERE r.ev_class IN(SELECT oid FROM tables)),
 acl_objects(kind,identity,owner,acl) AS (
 SELECT 'schema',n.nspname::text,n.nspowner,coalesce(n.nspacl,pg_catalog.acldefault('n',n.nspowner))
 FROM pg_catalog.pg_namespace n WHERE n.oid>=16384
 OR (n.nspname<>'information_schema' AND n.nspname !~ '^pg_') UNION ALL
 SELECT 'function',p.oid::regprocedure::text,p.proowner,coalesce(p.proacl,pg_catalog.acldefault('f',p.proowner))
 FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
 WHERE p.oid>=16384 OR (n.nspname<>'information_schema' AND n.nspname !~ '^pg_') UNION ALL
 SELECT 'table',c.oid::regclass::text,c.relowner,coalesce(c.relacl,pg_catalog.acldefault('r',c.relowner)) FROM tables c UNION ALL
 SELECT 'column',c.oid::regclass::text||'.'||pg_catalog.quote_ident(a.attname),c.relowner,coalesce(a.attacl,'{}'::aclitem[])
 FROM tables c JOIN pg_catalog.pg_attribute a ON a.attrelid=c.oid WHERE a.attnum>0 UNION ALL
 SELECT 'database','current_db',d.datdba,coalesce(d.datacl,pg_catalog.acldefault('d',d.datdba))
 FROM pg_catalog.pg_database d WHERE d.datname=current_database() UNION ALL
 SELECT 'language',l.lanname::text,l.lanowner,coalesce(l.lanacl,pg_catalog.acldefault('l',l.lanowner))
 FROM pg_catalog.pg_language l UNION ALL
 SELECT 'type',t.oid::regtype::text,t.typowner,coalesce(t.typacl,pg_catalog.acldefault('T',t.typowner))
 FROM types t UNION ALL
 SELECT 'default:'||d.defaclobjtype::text,coalesce(n.nspname::text,'global'),d.defaclrole,d.defaclacl
 FROM pg_catalog.pg_default_acl d LEFT JOIN pg_catalog.pg_namespace n ON n.oid=d.defaclnamespace),
 objects AS (
 SELECT jsonb_build_array('acl',kind,identity,pg_catalog.pg_get_userbyid(owner),
 ARRAY(SELECT jsonb_build_array(pg_catalog.pg_get_userbyid(a.grantor),
 CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_catalog.pg_get_userbyid(a.grantee)::text END,
 a.privilege_type,a.is_grantable) FROM pg_catalog.aclexplode(CASE WHEN cardinality(acl)>0 THEN acl END) a
 ORDER BY pg_catalog.pg_get_userbyid(a.grantor)::text COLLATE pg_catalog."C",
 CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_catalog.pg_get_userbyid(a.grantee)::text END COLLATE pg_catalog."C",
 a.privilege_type COLLATE pg_catalog."C",a.is_grantable)) AS value FROM acl_objects UNION ALL
 SELECT jsonb_build_array('database',pg_catalog.pg_get_userbyid(d.datdba),d.encoding,d.datlocprovider,
 d.datistemplate,d.datcollate,d.datctype,d.datlocale,d.daticurules,d.datcollversion)
 FROM pg_catalog.pg_database d WHERE d.datname=current_database() UNION ALL
 SELECT jsonb_build_array('table',c.oid::regclass::text,c.relrowsecurity,c.relforcerowsecurity,
 c.relreplident,c.reloptions,c.relchecks,am.amname)
 FROM tables c JOIN pg_catalog.pg_am am ON am.oid=c.relam UNION ALL
 SELECT jsonb_build_array('column',c.oid::regclass::text,a.attnum,a.attname,a.atttypid::regtype::text,
 a.atttypmod,a.attndims,a.attnotnull,a.atthasdef,a.atthasmissing,a.attidentity,a.attgenerated,
 a.attisdropped,a.attislocal,a.attinhcount,a.attlen,a.attbyval,a.attalign,a.attstorage,a.attcompression,
 a.attstattarget,a.attoptions,a.attfdwoptions,a.attmissingval::text,
 cn.nspname,co.collname,co.collprovider,co.collisdeterministic,co.collencoding,co.collcollate,
 co.collctype,co.colllocale,co.collicurules,co.collversion,
 pg_catalog.pg_get_expr(d.adbin,d.adrelid))
 FROM tables c JOIN pg_catalog.pg_attribute a ON a.attrelid=c.oid AND a.attnum>0
 LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
 LEFT JOIN pg_catalog.pg_collation co ON co.oid=a.attcollation
 LEFT JOIN pg_catalog.pg_namespace cn ON cn.oid=co.collnamespace UNION ALL
 SELECT jsonb_build_array('index',i.indrelid::regclass::text,c.relname,n.nspname,
 pg_catalog.pg_get_userbyid(c.relowner),c.relkind,c.relpersistence,c.reloptions,am.amname,
 pg_catalog.pg_get_indexdef(i.indexrelid),i.indnatts,i.indnkeyatts,i.indisunique,i.indnullsnotdistinct,
 i.indisprimary,i.indisexclusion,i.indimmediate,i.indisclustered,i.indisvalid,i.indcheckxmin,
 i.indisready,i.indislive,i.indisreplident,i.indkey::text,i.indoption::text,
 ARRAY(SELECT jsonb_build_array(onsp.nspname,op.opcname) FROM unnest(i.indclass::oid[]) WITH ORDINALITY x(oid,ord)
 JOIN pg_catalog.pg_opclass op ON op.oid=x.oid JOIN pg_catalog.pg_namespace onsp ON onsp.oid=op.opcnamespace ORDER BY x.ord),
 ARRAY(SELECT jsonb_build_array(cn.nspname,co.collname) FROM unnest(i.indcollation::oid[]) WITH ORDINALITY x(oid,ord)
 LEFT JOIN pg_catalog.pg_collation co ON co.oid=x.oid LEFT JOIN pg_catalog.pg_namespace cn ON cn.oid=co.collnamespace ORDER BY x.ord))
 FROM pg_catalog.pg_index i JOIN pg_catalog.pg_class c ON c.oid=i.indexrelid
 JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace JOIN pg_catalog.pg_am am ON am.oid=c.relam
 WHERE i.indrelid IN(SELECT oid FROM tables) UNION ALL
 SELECT jsonb_build_array('constraint',c.conrelid::regclass::text,c.conname,c.contype,
 pg_catalog.pg_get_constraintdef(c.oid),c.condeferrable,c.condeferred,c.convalidated,
 c.conislocal,c.coninhcount,c.connoinherit,c.conparentid=0,c.confmatchtype,c.confupdtype,c.confdeltype,
 c.conkey,c.confkey,c.confdelsetcols)
 FROM constraints c UNION ALL
 SELECT jsonb_build_array('trigger',t.tgrelid::regclass::text,
 CASE WHEN t.tgisinternal THEN NULL ELSE t.tgname::text END,
 c.conrelid::regclass::text,c.conname,t.tgtype,
 CASE WHEN NOT t.tgisinternal AND t.tgenabled='A' THEN 'O'::"char" ELSE t.tgenabled END,
 t.tgfoid::regprocedure::text,
 t.tgconstrrelid::regclass::text,t.tgisinternal,t.tgdeferrable,t.tginitdeferred,t.tgparentid=0,
 t.tgnargs,encode(t.tgargs,'hex'),t.tgattr::text,pg_catalog.pg_get_expr(t.tgqual,t.tgrelid),t.tgoldtable,t.tgnewtable)
 FROM triggers t LEFT JOIN constraints c ON c.oid=t.tgconstraint UNION ALL
 SELECT jsonb_build_array('type',n.nspname,t.typname,pg_catalog.pg_get_userbyid(t.typowner),
 t.typlen,t.typbyval,t.typtype,t.typcategory,t.typispreferred,t.typisdefined,t.typdelim,
 t.typrelid::regclass::text,t.typsubscript::regprocedure::text,t.typelem::regtype::text,t.typarray::regtype::text,
 t.typinput::regprocedure::text,t.typoutput::regprocedure::text,t.typreceive::regprocedure::text,
 t.typsend::regprocedure::text,t.typmodin::regprocedure::text,t.typmodout::regprocedure::text,
 t.typanalyze::regprocedure::text,t.typalign,t.typstorage,t.typnotnull,t.typbasetype::regtype::text,
 t.typtypmod,t.typndims,t.typcollation::regcollation::text,t.typdefaultbin::text,t.typdefault)
 FROM types t JOIN pg_catalog.pg_namespace n ON n.oid=t.typnamespace UNION ALL
 SELECT jsonb_build_array('policy',p.polrelid::regclass::text,p.polname,p.polpermissive,p.polcmd,
 ARRAY(SELECT CASE WHEN role=0 THEN 'PUBLIC' ELSE pg_catalog.pg_get_userbyid(role)::text END
 FROM unnest(p.polroles) role ORDER BY
 (CASE WHEN role=0 THEN 'PUBLIC' ELSE pg_catalog.pg_get_userbyid(role)::text END) COLLATE pg_catalog."C"),
 pg_catalog.pg_get_expr(p.polqual,p.polrelid),pg_catalog.pg_get_expr(p.polwithcheck,p.polrelid))
 FROM pg_catalog.pg_policy p UNION ALL
 SELECT jsonb_build_array('rule',r.ev_class::regclass::text,r.rulename,r.ev_type,r.ev_enabled,
 r.is_instead,pg_catalog.pg_get_ruledef(r.oid))
 FROM pg_catalog.pg_rewrite r JOIN pg_catalog.pg_class c ON c.oid=r.ev_class
 JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
 WHERE r.oid>=16384 OR (n.nspname<>'information_schema' AND n.nspname !~ '^pg_') UNION ALL
 SELECT jsonb_build_array('language',l.lanname,pg_catalog.pg_get_userbyid(l.lanowner),l.lanispl,l.lanpltrusted,
 l.lanplcallfoid::regprocedure::text,l.laninline::regprocedure::text,l.lanvalidator::regprocedure::text)
 FROM pg_catalog.pg_language l UNION ALL
 SELECT jsonb_build_array('role',r.rolname,r.rolsuper,r.rolinherit,r.rolcreaterole,r.rolcreatedb,
 r.rolcanlogin,r.rolreplication,r.rolbypassrls,r.rolconnlimit,r.rolvaliduntil::text)
 FROM pg_catalog.pg_roles r WHERE r.oid>=16384 OR r.rolname='twobrain_rec' UNION ALL
 SELECT jsonb_build_array('membership',pg_catalog.pg_get_userbyid(m.roleid),
 pg_catalog.pg_get_userbyid(m.member),pg_catalog.pg_get_userbyid(m.grantor),
 m.admin_option,m.inherit_option,m.set_option) FROM pg_catalog.pg_auth_members m UNION ALL
 SELECT jsonb_build_array('role_settings',CASE WHEN s.setdatabase=0 THEN 'global' ELSE 'current_db' END,
 CASE WHEN s.setrole=0 THEN 'ALL' ELSE pg_catalog.pg_get_userbyid(s.setrole)::text END,s.setconfig)
 FROM pg_catalog.pg_db_role_setting s WHERE s.setdatabase=0 OR s.setdatabase=
 (SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database()) UNION ALL
 SELECT jsonb_build_array('unsupported',
 (SELECT count(*) FROM pg_catalog.pg_cast WHERE oid>=16384),
 (SELECT count(*) FROM pg_catalog.pg_operator WHERE oid>=16384),
 (SELECT count(*) FROM pg_catalog.pg_opclass WHERE oid>=16384),
 (SELECT count(*) FROM pg_catalog.pg_opfamily WHERE oid>=16384),
 (SELECT count(*) FROM pg_catalog.pg_am WHERE oid>=16384),
 (SELECT count(*) FROM pg_catalog.pg_conversion WHERE oid>=16384),
 (SELECT count(*) FROM pg_catalog.pg_transform WHERE oid>=16384)) UNION ALL
 SELECT jsonb_build_array('toast',c.oid::regclass::text,t.relkind,n.nspname,
 pg_catalog.pg_get_userbyid(t.relowner),t.relpersistence,t.relispartition,t.reloptions)
 FROM tables c JOIN pg_catalog.pg_class t ON t.oid=c.reltoastrelid
 JOIN pg_catalog.pg_namespace n ON n.oid=t.relnamespace UNION ALL
 SELECT jsonb_build_array('edge',d.classid::regclass::text,
 CASE WHEN t.tgisinternal THEN jsonb_build_array('fk_trigger',tc.conrelid::regclass::text,tc.conname,
 t.tgrelid::regclass::text,t.tgtype,t.tgfoid::regprocedure::text)
 WHEN toast.oid IS NOT NULL THEN jsonb_build_array('toast',toast.oid::regclass::text)
 ELSE jsonb_build_array(s.type,s.schema,s.name,s.identity) END,d.objsubid,
 d.refclassid::regclass::text,jsonb_build_array(r.type,r.schema,r.name,r.identity),d.refobjsubid,d.deptype)
 FROM pg_catalog.pg_depend d
 CROSS JOIN LATERAL pg_catalog.pg_identify_object(d.classid,d.objid,d.objsubid) s
 CROSS JOIN LATERAL pg_catalog.pg_identify_object(d.refclassid,d.refobjid,d.refobjsubid) r
 LEFT JOIN triggers t ON d.classid='pg_catalog.pg_trigger'::regclass AND t.oid=d.objid
 LEFT JOIN constraints tc ON tc.oid=t.tgconstraint
 LEFT JOIN tables toast ON d.classid='pg_catalog.pg_class'::regclass AND d.objid=toast.reltoastrelid
 WHERE EXISTS(SELECT FROM roots x WHERE (x.classid=d.classid AND x.objid=d.objid)
 OR (x.classid=d.refclassid AND x.objid=d.refobjid)))
SELECT value::text FROM objects
"""
# table, name, type, UPDATE OF columns, function, final body migration.
TRIGGERS = (
    ('meeting_outcome_generation_attempts', 'trg_bump_summary_slot_state_version', 17,
     ('status', 'failure_code', 'failure_reason', 'outcome_set_id', 'metadata_json', 'ended_at'),
     'rec_bump_summary_slot_state_version', '0079_summary_state_versions'),
    ('promotion_redemptions', 'promotion_redemptions_sync_campaign_counter', 21, ('state',),
     'rec_sync_promotion_reservation_counter', '0081_secure_promotion_counter_function'),
    ('billing_storage_entitlement_grants', 'storage_grant_period', 23, (),
     'rec_check_storage_grant', '0100_billing_purchases'),
    ('billing_storage_entitlement_grants', 'storage_grant_immutable', 27, (),
     'rec_storage_grant_immutable', '0100_billing_purchases'),
    ('billing_storage_price_versions', 'storage_price_immutable', 19, (),
     'rec_storage_price_immutable', '0100_billing_purchases'),
    ('billing_purchase_quotes', 'purchase_quote_immutable', 19, (),
     'rec_purchase_quote_immutable', '0100_billing_purchases'),
    ('product_activation_milestones', 'activation_decision_immutable', 19, (),
     'rec_activation_decision_immutable', '0106_activation_milestones'),
    ('billing_registry_imports', 'registry_history_guard', 27, (),
     'rec_registry_history_guard', '0107_billing_registry'),
    ('billing_registry_gaps', 'registry_history_guard', 27, (),
     'rec_registry_history_guard', '0107_billing_registry'),
)
FUNCTION_SQL = re.compile(
    r'\bcreate\s+(?:or\s+replace\s+)?function\s+(\w+)\s*\(\s*\)'
    r'\s+returns\s+trigger\b.*?\bas\s+(\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$)(.*?)(?-i:\2)',
    re.IGNORECASE | re.DOTALL,
)


def _expected_bodies():
    directory = Path(__file__).resolve().parents[1] / 'db/migrations/versions'
    result = {}
    for migration in sorted({row[5] for row in TRIGGERS}):
        tree = ast.parse((directory / (migration + '.py')).read_text())
        upgrades = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'upgrade']
        _require(len(upgrades) == 1, 'retention_catalog_migration')
        definitions = upgrades
        if migration == '0100_billing_purchases':
            definitions = [node for node in tree.body
                           if isinstance(node, ast.FunctionDef) and node.name == '_install_policies']
            calls = [node.value for node in upgrades[0].body if isinstance(node, ast.Expr)
                     and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
                     and node.value.func.id == '_install_policies']
            _require(len(definitions) == len(calls) == 1 and not calls[0].args and not calls[0].keywords,
                     'retention_catalog_migration')
        found = {}
        for node in ast.walk(definitions[0]):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for match in FUNCTION_SQL.finditer(node.value):
                    name, _, body = match.groups()
                    _require(name not in found, 'retention_catalog_migration')
                    found[name] = body
        _require(set(found) == {row[4] for row in TRIGGERS if row[5] == migration},
                 'retention_catalog_migration')
        result.update(found)
    return result


async def local_retention_database_catalog(source):
    """Query the actual catalog; return only a digest, never authorise a writer."""
    try:
        categories = [category for level in ('anonymous_aggregate', 'attribution_profiles')
                      for category in LEVEL_RETENTION_CATEGORIES[level]]
        _require(len(categories) == len(TABLES) and set(categories) == set(TABLES),
                 'retention_catalog_categories')
        policies = []
        for category in sorted(categories):
            rule = retention_rule(category)
            _require(rule.category == category and rule.storage == 'graf_postgres'
                     and rule.enforcement == 'decision_required' and rule.retention_mode == 'until_decision'
                     and rule.minimum_retention_days is None and rule.maximum_retention_days is None,
                     'retention_catalog_policy')
            policies.append(rule.as_dict())
        bodies = _expected_bodies()
        _require(source.is_in_transaction() and await source.fetchval('SHOW transaction_read_only') == 'on',
                 'retention_catalog_transaction')
        _require(170000 <= int(await source.fetchval('SHOW server_version_num')) < 180000
                 and await source.fetchval('SHOW search_path') == '"$user", public',
                 'retention_catalog_environment')
        _require([row[0] for row in await source.fetch(
            'SELECT lanname::text FROM pg_catalog.pg_language ORDER BY lanname')]
            == ['c', 'internal', 'plpgsql', 'sql'] and await source.fetchval("""
                SELECT NOT EXISTS(SELECT FROM pg_catalog.pg_event_trigger)
                    AND NOT EXISTS(SELECT FROM pg_catalog.pg_foreign_data_wrapper)
                    AND NOT EXISTS(SELECT FROM pg_catalog.pg_foreign_server)
            """) is True, 'retention_catalog_executables')
        # Deparser rejects aggregates; refuse every unsupported kind before calling it.
        _require(await source.fetchval("SELECT count(*)=32 AND coalesce(bool_and(p.prokind='f'),false) "
                                       + ROUTINES_FROM) is True, 'retention_catalog_routine_kind')
        routines = [tuple(row) for row in await source.fetch("""
            SELECT n.nspname::text,p.proname::text,
                pg_catalog.pg_get_function_identity_arguments(p.oid),
                pg_catalog.pg_get_functiondef(p.oid),pg_catalog.pg_get_userbyid(p.proowner)::text,
                l.lanname::text,p.prokind::text,p.proleakproof,p.proisstrict,p.proretset,
                p.provolatile::text,p.proparallel::text,p.probin IS NULL,
                p.prosupport::oid::bigint,p.prosqlbody IS NULL
        """ + ROUTINES_FROM + """
            ORDER BY n.nspname COLLATE pg_catalog."C",p.proname COLLATE pg_catalog."C",
                pg_catalog.pg_get_function_identity_arguments(p.oid) COLLATE pg_catalog."C"
        """)]
        routine_digest = hashlib.sha256(json.dumps(routines, sort_keys=True).encode()).hexdigest()
        _require(routine_digest == EXPECTED_ROUTINES_SHA256, 'retention_catalog_routines')
        relations = [tuple(row) for row in await source.fetch("""
            SELECT c.relname::text,c.relkind::text,c.relpersistence::text,
                pg_catalog.pg_get_userbyid(c.relowner)::text,
                EXISTS(SELECT FROM pg_catalog.pg_inherits i WHERE i.inhrelid=c.oid OR i.inhparent=c.oid),
                c.relispartition,EXISTS(SELECT FROM pg_catalog.pg_rewrite r WHERE r.ev_class=c.oid)
            FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relname=ANY($1::text[]) ORDER BY c.relname
        """, list(TABLES.values()))]
        _require(relations == [(name, 'r', 'p', 'twobrain_rec', False, False, False)
                               for name in sorted(TABLES.values())], 'retention_catalog_relations')
        extensions = [row[0] for row in await source.fetch('SELECT extname::text FROM pg_catalog.pg_extension ORDER BY extname')]
        _require(extensions == ['plpgsql'] and not await source.fetchval("""
            SELECT EXISTS(SELECT FROM pg_catalog.pg_namespace
                WHERE nspname IN ('cron','pgagent','timescaledb') OR nspname LIKE '\\_timescaledb%')
        """), 'retention_catalog_scheduler')
        rows = await source.fetch("""
            SELECT n.nspname::text,c.relname::text,t.tgname::text,t.tgtype::int,t.tgenabled::text,
                ARRAY(SELECT a.attname::text FROM unnest(t.tgattr::smallint[]) WITH ORDINALITY x(num,ord)
                    JOIN pg_catalog.pg_attribute a ON a.attrelid=c.oid AND a.attnum=x.num ORDER BY ord),
                t.tgnargs::int,t.tgargs,t.tgqual IS NULL,t.tgconstraint::bigint,t.tgconstrrelid::bigint,
                t.tgdeferrable,t.tginitdeferred,t.tgparentid::bigint,t.tgoldtable,t.tgnewtable,
                pn.nspname::text,p.proname::text,pg_catalog.pg_get_userbyid(p.proowner)::text,
                l.lanname::text,p.prorettype='pg_catalog.trigger'::regtype,p.pronargs::int,
                p.pronargdefaults::int,p.provariadic::bigint,p.proallargtypes IS NULL,
                p.proargmodes IS NULL,p.proargnames IS NULL,p.prokind::text,p.prosecdef,
                p.proleakproof,p.proisstrict,p.proretset,p.provolatile::text,p.proparallel::text,
                p.proconfig,p.probin IS NULL,p.prosupport::oid::bigint,p.prosqlbody IS NULL,p.prosrc
            FROM pg_catalog.pg_trigger t JOIN pg_catalog.pg_class c ON c.oid=t.tgrelid
            JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
            JOIN pg_catalog.pg_proc p ON p.oid=t.tgfoid
            JOIN pg_catalog.pg_namespace pn ON pn.oid=p.pronamespace
            JOIN pg_catalog.pg_language l ON l.oid=p.prolang
            WHERE NOT t.tgisinternal ORDER BY n.nspname,c.relname,t.tgname
        """)
        expected = []
        for table, name, kind, columns, function, _ in sorted(TRIGGERS):
            promotion = function == 'rec_sync_promotion_reservation_counter'
            expected.append(('public', table, name, kind, list(columns), 0, b'', True, 0, 0,
                False, False, 0, None, None, 'public', function, 'twobrain_rec', 'plpgsql',
                True, 0, 0, 0, True, True, True, 'f', promotion, False, False, False, 'v', 'u',
                ['search_path=pg_catalog, pg_temp', 'row_security=off'] if promotion else None,
                True, 0, True, bodies[function]))
        _require(len(rows) == len(expected) and all(row[4] in ('O', 'A') for row in rows)
                 and [tuple(row[:4]) + tuple(row[5:]) for row in rows] == expected,
                 'retention_catalog_triggers')
        # No function bodies, SQL, identifiers or rows leave this internal reader.
        proof = dict(policy=policies, relations=relations, extensions=extensions,
                     routines_sha256=routine_digest,
                     triggers=[(row[0:4], hashlib.sha256(repr(tuple(row)).encode()).hexdigest()) for row in rows])
        return hashlib.sha256(json.dumps(proof, sort_keys=True).encode()).hexdigest()
    except Exception:
        raise ActivationHold('activation_operator_retention_catalog_unverified') from None


async def local_retention_database_access(source):
    """Physical catalog metadata only; return a digest without SQL or user data."""
    try:
        _require(source.is_in_transaction() and await source.fetchval('SHOW transaction_read_only') == 'on',
                 'retention_access_transaction')
        _require(170000 <= int(await source.fetchval('SHOW server_version_num')) < 180000
                 and await source.fetchval('SHOW search_path') == '"$user", public',
                 'retention_access_environment')
        rows = sorted([json.loads(row[0]) for row in await source.fetch(ACCESS_QUERY, list(TABLES.values()))],
                      key=lambda row: json.dumps(row, sort_keys=True))
        digest = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
        _require(digest == EXPECTED_ACCESS_SHA256, 'retention_access_metadata')
        return digest
    except Exception:
        raise ActivationHold('activation_operator_retention_access_unverified') from None
