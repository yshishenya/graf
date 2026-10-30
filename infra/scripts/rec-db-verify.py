#!/usr/bin/env python3
"""Closed backup checks and source/restore comparison; never changes readiness."""

import ast
import graphlib
import hashlib
import json
import re
import stat
import sys
from pathlib import Path

ARTIFACTS = ('postgres.dump', 'schema.sql', 'inventory.jsonl')
ROLES = ('twobrain_rec_app', 'twobrain_rec_maintenance', 'twobrain_rec_media')
LEDGER = 'product_activation_milestones'
STATES = {'not_requested', 'pending', 'pre_send_retry', 'dispatching', 'submitted',
          'ambiguous', 'confirmed', 'cancelled', 'rejected'}
KEYS = {
    'role': ('name',), 'membership': ('role', 'member', 'grantor'),
    'role_setting': ('role', 'scope', 'name'), 'relation': ('schema', 'name'),
    'constraint': ('schema', 'relation', 'name'), 'policy': ('schema', 'relation', 'name'),
    'index': ('schema', 'name'), 'trigger': ('schema', 'relation', 'name'),
    'revision': ('name',), 'count': ('relation',),
    'activation_states': ('posthog_state', 'yandex_state'), 'ledger_access': ('role',),
    'ledger_column': ('name',),
    'snapshot': (),
    'sequence_state': ('schema', 'name'),
}
FIELDS = {
    'snapshot': 'format_version database role snapshot server_version',
    'role': 'name superuser inherit create_role create_db login replication bypass_rls connection_limit valid_until',
    'membership': 'role member grantor admin inherit set',
    'role_setting': 'role scope name value',
    'relation': 'schema name type persistence owner acl rls force_rls public_access',
    'constraint': 'schema relation name definition validated deferrable deferred type columns index referenced_relation referenced_columns on_delete',
    'policy': 'schema relation name permissive roles command using check',
    'index': 'schema name valid ready live unique primary',
    'trigger': 'schema relation name enabled type function_schema function function_md5 security_definer',
    'revision': 'name', 'count': 'relation rows',
    'activation_states': 'posthog_state yandex_state rows',
    'ledger_access': 'role select insert update delete truncate references trigger maintain grant_option',
    'ledger_column': 'name type not_null default_md5 identity generated acl',
    'sequence_state': 'schema name last_value is_called',
}
POLICY = (
    "(((rec_context_kind() = ANY (ARRAY['request'::text, 'worker'::text, 'auth_bootstrap'::text])) "
    "AND (account_id = rec_current_user_id())) OR ((SESSION_USER = 'twobrain_rec_maintenance'::name) "
    "AND rec_maintenance_allowed()) OR ((SESSION_USER = 'twobrain_rec_maintenance'::name) "
    "AND (rec_context_kind() = 'maintenance'::text) "
    "AND (rec_setting('app.maintenance_operation'::text) = 'activation_milestone_delivery'::text) "
    "AND (rec_setting('app.maintenance_feature_area'::text) = 'product_analytics'::text) "
    "AND (rec_setting('app.maintenance_actor'::text) IS NOT NULL) "
    "AND (rec_setting('app.maintenance_reason'::text) IS NOT NULL)))"
)


def require(condition):
    if not condition:
        raise ValueError('backup_contract_mismatch')


def checksums(root):
    require(not root.is_symlink() and root.is_dir())
    paths = [root / name for name in (*ARTIFACTS, 'checksums.sha256')]
    for path in paths:
        mode = path.lstat()
        require(stat.S_ISREG(mode.st_mode) and mode.st_nlink == 1 and mode.st_size > 0)
    lines = paths[-1].read_text().splitlines()
    require(len(lines) == 3)
    for name, line in zip(ARTIFACTS, lines):
        require(re.fullmatch(r'[0-9a-f]{64}  ' + re.escape(name), line))
        with (root / name).open('rb') as stream:
            require(hashlib.file_digest(stream, 'sha256').hexdigest() == line[:64])


def schema(root):
    value = (root / 'schema.sql').read_text()
    # pg_dump 17.6+ inserts one random, paired psql restriction token.
    prefix = '--\n-- PostgreSQL database dump\n--\n\n'
    suffix = '--\n-- PostgreSQL database dump complete\n--\n\n'
    require(value.startswith(prefix))
    match = re.match(r'\\restrict ([A-Za-z0-9]+)\n\n', value[len(prefix):])
    if match:
        tail = suffix + '\\unrestrict ' + match[1] + '\n\n'
        require(value.endswith(tail))
        # Only remove wrapper positions; never rewrite SQL or a function body.
        value = prefix + value[len(prefix) + match.end():-len(tail)] + suffix
    require(value.endswith(suffix) and re.search(r'^-- Dumped by pg_dump version 17\.[0-9]+$', value, re.M))
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def inventory(root, expected_db, *, schema_only=False):
    require(not root.is_symlink() and stat.S_IMODE(root.stat().st_mode) == 0o700)
    for name in ('schema.sql', 'inventory.jsonl'):
        info = (root / name).lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and info.st_size > 0 and stat.S_IMODE(info.st_mode) == 0o600)
    rows = {}
    for line in (root / 'inventory.jsonl').read_text().splitlines():
        row = json.loads(line, object_pairs_hook=unique_object)
        require(isinstance(row, dict) and row.get('kind') in KEYS)
        kind = row['kind']
        require(set(row) == {'kind', *FIELDS[kind].split()})
        key = (kind, *(row[field] for field in KEYS[kind]))
        require(key not in rows)
        rows[key] = row
    header = rows.pop(('snapshot',))
    require(set(header) == {'kind', 'format_version', 'database', 'role', 'snapshot', 'server_version'})
    require(header['format_version'] == 2 and header['database'] == expected_db
            and header['role'] == 'twobrain_rec' and re.fullmatch(r'17[0-9]{4}', header['server_version'])
            and re.fullmatch(r'[0-9A-F]+-[0-9A-F]+-[0-9]+', header['snapshot']))
    for role in ROLES:
        row = rows[('role', role)]
        require(row['login'] is True and row['connection_limit'] == -1
                and row['valid_until'] in (None, 'infinity'))
        require(all(row[field] is False for field in
                    ('superuser', 'inherit', 'create_role', 'create_db', 'replication', 'bypass_rls')))
        require(rows[('role_setting', role, 'global', 'row_security')]['value'] == 'on')
    require(not any(row['role'] in ROLES or row['member'] in ROLES
                    for row in rows.values() if row['kind'] == 'membership'))
    relations = [row for row in rows.values() if row['kind'] == 'relation']
    require(relations and all(row['type'] in ('r', 'p', 'i', 'I', 'v', 'S') for row in relations))
    sequences = [row for row in rows.values() if row['kind'] == 'sequence_state']
    require({(r['schema'], r['name']) for r in sequences} ==
            {(r['schema'], r['name']) for r in relations if r['type'] == 'S'})
    require(all(type(r['last_value']) is int and type(r['is_called']) is bool for r in sequences))
    counts = {row['relation']: row['rows'] for row in rows.values() if row['kind'] == 'count'}
    require(set(counts) == {r['schema'] + '.' + r['name'] for r in relations if r['type'] in ('r', 'p')})
    require(all(type(number) is int and number >= 0 for number in counts.values()))
    ledger = rows[('relation', 'public', LEDGER)]
    require(ledger['type'] == 'r' and ledger['persistence'] == 'p' and ledger['owner'] == 'twobrain_rec'
            and ledger['rls'] is True and ledger['force_rls'] is True and ledger['public_access'] is False)
    for role in ROLES:
        row = rows[('ledger_access', role)]
        require(all(row[action] is (role != 'twobrain_rec_media')
                    for action in ('select', 'insert', 'update', 'delete')))
        require(all(row[action] is False for action in ('truncate', 'references', 'trigger', 'maintain', 'grant_option')))
    columns = {'id': ('uuid', True), 'account_id': ('uuid', True),
               'event_id': ('uuid', True), 'event_name': ('character varying(64)', True),
               'occurred_at': ('timestamp with time zone', True),
               'accepted_at': ('timestamp with time zone', True), 'safe_payload': ('jsonb', True),
               'source_kind': ('character varying(8)', True), 'updated_at': ('timestamp with time zone', True)}
    defaults = {'updated_at': 'now()'}
    for provider in ('posthog', 'yandex'):
        for suffix, kind, not_null in (
                ('state', 'character varying(16)', True), ('reason', 'character varying(80)', True),
                ('attempt_id', 'uuid', False), ('attempted_at', 'timestamp with time zone', False),
                ('confirmation_ref', 'character varying(120)', False)):
            columns[provider + '_' + suffix] = (kind, not_null)
        for suffix in ('state', 'reason'):
            defaults[provider + '_' + suffix] = "'not_requested'::character varying"
    require({r['name'] for r in rows.values() if r['kind'] == 'ledger_column'} == set(columns))
    for name, (kind, not_null) in columns.items():
        row = rows[('ledger_column', name)]
        default_hash = hashlib.md5(defaults[name].encode()).hexdigest() if name in defaults else None
        require(row['type'] == kind and row['not_null'] is not_null and row['default_md5'] == default_hash
                and row['identity'] == row['generated'] == '' and row['acl'] is None)
    for row in rows.values():
        if row['kind'] == 'index':
            require(row['valid'] is True and row['ready'] is True and row['live'] is True)
        if row['kind'] == 'role_setting':
            require(row['name'] == 'row_security' and row['value'] == 'on')
    constraints = [r for r in rows.values() if r['kind'] == 'constraint'
                   and r['schema'] == 'public' and r['relation'] == LEDGER]
    require(all(r['validated'] is True for r in constraints))
    for columns in (['id'], ['event_id'], ['account_id', 'event_name']):
        expected_type = 'p' if columns == ['id'] else 'u'
        matches = [r for r in constraints if r['type'] == expected_type and r['columns'] == columns]
        require(len(matches) == 1)
        index = rows[('index', 'public', matches[0]['index'])]
        require(index['unique'] is True and index['primary'] is (expected_type == 'p')
                and matches[0]['deferrable'] is False)
    require(any(r['type'] == 'f' and r['columns'] == ['account_id']
                and r['referenced_relation'] == 'public.user_identities'
                and r['referenced_columns'] == ['id'] and r['on_delete'] == 'c' for r in constraints))
    policy = rows[('policy', 'public', LEDGER, 'activation_account_isolation')]
    require(policy['command'] == 'ALL' and policy['permissive'] == 'PERMISSIVE'
            and policy['roles'] == ['public'] and policy['using'] == policy['check'] == POLICY)
    require(sum(r['kind'] == 'policy' and r['schema'] == 'public' and r['relation'] == LEDGER
                for r in rows.values()) == 1)
    trigger = rows[('trigger', 'public', LEDGER, 'activation_decision_immutable')]
    require(trigger['enabled'] in ('O', 'A') and trigger['type'] == 19
            and trigger['function_schema'] == 'public'
            and trigger['function'] == 'rec_activation_decision_immutable'
            and trigger['security_definer'] is False)
    migrations = Path(__file__).resolve().parents[2] / 'apps/server/src/twobrain_rec_server/db/migrations/versions'
    revisions = {}
    for path in migrations.glob('*.py'):
        metadata = {}
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if not isinstance(target, ast.Name) or target.id not in ('revision', 'down_revision'):
                        continue
                    require(target.id not in metadata)
                    metadata[target.id] = ast.literal_eval(node.value)
        require(set(metadata) == {'revision', 'down_revision'}
                and isinstance(metadata['revision'], str) and metadata['revision'] not in revisions)
        parent = metadata['down_revision']
        revisions[metadata['revision']] = {parent} if isinstance(parent, str) else set(parent or ())
    parents = set().union(*revisions.values())
    require(parents <= revisions.keys() and len(revisions.keys() - parents) == 1)
    list(graphlib.TopologicalSorter(revisions).static_order())  # Reject cycles, including detached ones.
    current = next(iter(revisions.keys() - parents))
    supported = {current}
    while current != '0106_activation_milestones':
        require(len(revisions[current]) == 1)
        current = next(iter(revisions[current]))
        supported.add(current)
    saved = {r['name'] for r in rows.values() if r['kind'] == 'revision'}
    require(not saved if schema_only else len(saved) == 1 and saved <= supported)
    require(not schema_only or all(number == 0 for number in counts.values()))
    migration = ast.parse((migrations / '0106_activation_milestones.py').read_text())
    constants = {n.targets[0].id: ast.literal_eval(n.value) for n in migration.body
                 if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                 and n.targets[0].id in ('EVENTS', 'STATES', 'REASONS')}
    allowed = {'event_name': constants['EVENTS'], 'source_kind': ('browser', 'desktop', 'server')}
    for provider in ('posthog', 'yandex'):
        allowed[provider + '_state'] = constants['STATES']
        allowed[provider + '_reason'] = constants['REASONS']
    for column, values in allowed.items():
        suffix = {'event_name': 'event', 'source_kind': 'source'}.get(column, column)
        row = rows[('constraint', 'public', LEDGER, 'ck_' + LEDGER + '_activation_' + suffix)]
        # Exactly the two native PG17 deparse forms proved by the migrated roundtrip test.
        source_array = '(ARRAY[' + ', '.join("'" + v + "'::character varying" for v in values) + '])::text[]'
        restored_array = 'ARRAY[' + ', '.join("('" + v + "'::character varying)::text" for v in values) + ']'
        require(row['type'] == 'c' and row['columns'] == [column] and row['definition'] in {
            f'CHECK ((({column})::text = ANY ({array})))' for array in (source_array, restored_array)})
    payload = rows[('constraint', 'public', LEDGER, 'ck_' + LEDGER + '_activation_payload_size')]
    require(payload['type'] == 'c' and payload['columns'] == ['safe_payload'] and payload['definition'] ==
            "CHECK (((jsonb_typeof(safe_payload) = 'object'::text) AND (octet_length(convert_to((safe_payload)::text, 'UTF8'::name)) <= 16384)))")
    bodies = [n.value for n in ast.walk(migration) if isinstance(n, ast.Constant)
              and isinstance(n.value, str) and 'CREATE FUNCTION rec_activation_decision_immutable()' in n.value]
    require(len(bodies) == 1)
    require(trigger['function_md5'] == hashlib.md5(bodies[0].split('$$')[1].encode()).hexdigest())
    states = [row for row in rows.values() if row['kind'] == 'activation_states']
    require(all(row['posthog_state'] in STATES and row['yandex_state'] in STATES
                and type(row['rows']) is int and row['rows'] > 0 for row in states))
    require(sum(row['rows'] for row in states) == counts['public.' + LEDGER])
    return header, rows


def without_expressions(rows):
    # Only the native schema-only roundtrip compares these expression strings.
    return {key: {field: value for field, value in row.items()
                  if (row['kind'], field) not in {
                      ('constraint', 'definition'), ('policy', 'using'), ('policy', 'check')}}
            for key, row in rows.items()}


def main():
    try:
        require(len(sys.argv) in (2, 3, 6))
        require(len(sys.argv) != 3 or sys.argv[2] == '--inventory')
        source = Path(sys.argv[1])
        checksums(source)
        if len(sys.argv) > 2:
            require(all(stat.S_IMODE((source / name).stat().st_mode) == 0o600
                        for name in (*ARTIFACTS, 'checksums.sha256')))
            first, expected = inventory(source, 'twobrain_rec')
            schema(source)
            if len(sys.argv) > 3:
                target, target_db = Path(sys.argv[2]), sys.argv[3]
                canonical, canonical_db = Path(sys.argv[4]), sys.argv[5]
                require(re.fullmatch(r'rec_restore_rehearsal_[0-9a-f]{32}', target_db))
                require(re.fullmatch(r'rec_restore_schema_[0-9a-f]{32}', canonical_db))
                second, actual = inventory(target, target_db)
                third, schema_rows = inventory(canonical, canonical_db, schema_only=True)
                require(first['server_version'] == second['server_version'] == third['server_version'])
                require(without_expressions(expected) == without_expressions(actual))
                # Reference has schema only; source data/state is ALWAYS compared above.
                require({k: r for k, r in actual.items() if k[0] not in ('count', 'activation_states', 'revision', 'sequence_state')}
                        == {k: r for k, r in schema_rows.items() if k[0] not in ('count', 'activation_states', 'revision', 'sequence_state')})
                require(schema(canonical) == schema(target))
        return 0
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        print('postgres_verification=failed', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
