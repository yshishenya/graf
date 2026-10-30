"""Fixed local policy/trigger catalog, not a full retention or readiness receipt.

The operator owns this physical source connection and its read-only transaction.
Standalone functions, lifecycle/RLS/data and installed jobs are separate gates.
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
                     triggers=[(row[0:4], hashlib.sha256(repr(tuple(row)).encode()).hexdigest()) for row in rows])
        return hashlib.sha256(json.dumps(proof, sort_keys=True).encode()).hexdigest()
    except Exception:
        raise ActivationHold('activation_operator_retention_catalog_unverified') from None
