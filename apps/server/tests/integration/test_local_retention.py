"""Real migrated PG17, closed retention catalog; no readiness or product data."""

import asyncio
import importlib

import asyncpg
import pytest
from sqlalchemy.engine import make_url

from twobrain_rec_server.product_analytics.activation_fence import ActivationHold


@pytest.mark.postgres
def test_native_local_retention_catalog(postgres_isolated_cluster_database_url):
    module = importlib.import_module('twobrain_rec_server.product_analytics.local_retention')
    url = make_url(postgres_isolated_cluster_database_url)
    assert url.host == '127.0.0.1' and url.database.startswith('twobrain_rec_test_')

    async def run():
        db = await asyncpg.connect(host=url.host, port=url.port, user=url.username,
                                   password=url.password, database=url.database)
        try:
            async def catalog():
                async with db.transaction(readonly=True):
                    return await module.local_retention_database_catalog(db)

            baseline = await catalog()
            assert len(baseline) == 64
            await db.execute('CREATE ROLE synthetic_retention_owner NOLOGIN')
            with pytest.raises(ActivationHold, match='retention_catalog'):
                await module.local_retention_database_catalog(db)
            async with db.transaction():
                with pytest.raises(ActivationHold, match='retention_catalog'):
                    await module.local_retention_database_catalog(db)
            original = await db.fetchval("SELECT pg_get_functiondef('public.rec_activation_decision_immutable()'::regprocedure)")
            trigger = 'CREATE TRIGGER activation_decision_immutable BEFORE UPDATE ON public.product_activation_milestones FOR EACH ROW EXECUTE FUNCTION public.rec_activation_decision_immutable()'
            alterations = [
                ('missing', 'ALTER TABLE public.anonymous_page_aggregate_buckets RENAME TO synthetic_buckets',
                 'ALTER TABLE public.synthetic_buckets RENAME TO anonymous_page_aggregate_buckets'),
                ('unlogged', 'ALTER TABLE public.anonymous_page_aggregate_buckets SET UNLOGGED',
                 'ALTER TABLE public.anonymous_page_aggregate_buckets SET LOGGED'),
                ('owner', 'ALTER TABLE public.anonymous_page_aggregate_buckets OWNER TO synthetic_retention_owner',
                 'ALTER TABLE public.anonymous_page_aggregate_buckets OWNER TO twobrain_rec'),
                ('view', 'ALTER TABLE public.anonymous_page_aggregate_buckets RENAME TO synthetic_buckets; CREATE VIEW public.anonymous_page_aggregate_buckets AS SELECT * FROM public.synthetic_buckets',
                 'DROP VIEW public.anonymous_page_aggregate_buckets; ALTER TABLE public.synthetic_buckets RENAME TO anonymous_page_aggregate_buckets'),
                ('inheritance', 'CREATE TABLE public.synthetic_child() INHERITS(public.public_visit_attributions)',
                 'DROP TABLE public.synthetic_child'),
                ('inherited', 'CREATE TABLE public.synthetic_parent(LIKE public.public_visit_attributions); ALTER TABLE public.public_visit_attributions INHERIT public.synthetic_parent',
                 'ALTER TABLE public.public_visit_attributions NO INHERIT public.synthetic_parent; DROP TABLE public.synthetic_parent'),
                ('rule', 'CREATE RULE synthetic_rule AS ON INSERT TO public.anonymous_page_aggregate_buckets DO INSTEAD NOTHING',
                 'DROP RULE synthetic_rule ON public.anonymous_page_aggregate_buckets'),
                ('sibling_trigger', 'CREATE TRIGGER synthetic_sibling AFTER DELETE ON public.billing_purchase_quotes FOR EACH ROW EXECUTE FUNCTION public.rec_purchase_quote_immutable()',
                 'DROP TRIGGER synthetic_sibling ON public.billing_purchase_quotes'),
                ('disabled', 'ALTER TABLE public.product_activation_milestones DISABLE TRIGGER activation_decision_immutable',
                 'ALTER TABLE public.product_activation_milestones ENABLE TRIGGER activation_decision_immutable'),
                ('replica_only', 'ALTER TABLE public.product_activation_milestones ENABLE REPLICA TRIGGER activation_decision_immutable',
                 'ALTER TABLE public.product_activation_milestones ENABLE TRIGGER activation_decision_immutable'),
                ('body', "CREATE OR REPLACE FUNCTION public.rec_activation_decision_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$", original),
                ('security', 'ALTER FUNCTION public.rec_activation_decision_immutable() SECURITY DEFINER', original),
                ('function_owner', 'ALTER FUNCTION public.rec_activation_decision_immutable() OWNER TO synthetic_retention_owner',
                 'ALTER FUNCTION public.rec_activation_decision_immutable() OWNER TO twobrain_rec'),
                ('strict', 'ALTER FUNCTION public.rec_activation_decision_immutable() STRICT', original),
                ('parallel', 'ALTER FUNCTION public.rec_activation_decision_immutable() PARALLEL SAFE', original),
                ('config', 'ALTER FUNCTION public.rec_activation_decision_immutable() SET search_path=public', original),
                ('scheduler', 'CREATE SCHEMA cron', 'DROP SCHEMA cron'),
                ('extension', 'CREATE EXTENSION pg_trgm', 'DROP EXTENSION pg_trgm'),
                *[(table, f'ALTER TABLE public.{table} DISABLE TRIGGER registry_history_guard',
                   f'ALTER TABLE public.{table} ENABLE TRIGGER registry_history_guard')
                  for table in ('billing_registry_imports', 'billing_registry_gaps')],
            ]
            for name, change, undo in alterations:
                await db.execute(change)
                try:
                    with pytest.raises(ActivationHold, match='retention_catalog'):
                        await catalog()
                finally:
                    await db.execute(undo)
                assert await catalog() == baseline, name

            for suffix in (
                " AFTER UPDATE ON public.product_activation_milestones FOR EACH ROW EXECUTE FUNCTION public.rec_activation_decision_immutable()",
                " BEFORE UPDATE OF accepted_at ON public.product_activation_milestones FOR EACH ROW EXECUTE FUNCTION public.rec_activation_decision_immutable()",
                " BEFORE UPDATE ON public.product_activation_milestones FOR EACH ROW WHEN(NEW.id IS NOT NULL) EXECUTE FUNCTION public.rec_activation_decision_immutable()",
                " BEFORE UPDATE ON public.product_activation_milestones FOR EACH ROW EXECUTE FUNCTION public.rec_activation_decision_immutable('synthetic')",
                " AFTER UPDATE ON public.product_activation_milestones REFERENCING NEW TABLE AS synthetic_transition FOR EACH STATEMENT EXECUTE FUNCTION public.rec_activation_decision_immutable()",
            ):
                await db.execute('DROP TRIGGER activation_decision_immutable ON public.product_activation_milestones')
                await db.execute('CREATE TRIGGER activation_decision_immutable' + suffix)
                try:
                    with pytest.raises(ActivationHold, match='retention_catalog'):
                        await catalog()
                finally:
                    await db.execute('DROP TRIGGER activation_decision_immutable ON public.product_activation_milestones')
                    await db.execute(trigger)
                assert await catalog() == baseline

            await db.execute('ALTER TABLE public.product_activation_milestones ENABLE ALWAYS TRIGGER activation_decision_immutable')
            assert await catalog() != baseline  # Both accepted states remain bound to their actual bytes.
            await db.execute('ALTER TABLE public.product_activation_milestones ENABLE TRIGGER activation_decision_immutable')
            assert await catalog() == baseline
            await db.execute('DROP ROLE synthetic_retention_owner')

            # Same catalog proof without owner elevation or application row reads.
            await db.execute('CREATE ROLE twobrain_rec_maintenance LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT')
            await db.execute('SET SESSION AUTHORIZATION twobrain_rec_maintenance')
            assert await catalog() == baseline
        finally:
            await db.close()
    asyncio.run(run())


@pytest.mark.postgres
def test_native_routine_catalog(postgres_isolated_cluster_database_url, monkeypatch):
    module = importlib.import_module('twobrain_rec_server.product_analytics.local_retention')
    url = make_url(postgres_isolated_cluster_database_url)
    assert url.host == '127.0.0.1' and url.database.startswith('twobrain_rec_test_')

    async def run():
        db = await asyncpg.connect(host=url.host, port=url.port, user=url.username,
                                   password=url.password, database=url.database)
        queries = []

        class ObservedSource:
            def is_in_transaction(self):
                return db.is_in_transaction()

            async def fetchval(self, query, *args):
                queries.append(query)
                return await db.fetchval(query, *args)

            async def fetch(self, query, *args):
                queries.append(query)
                return await db.fetch(query, *args)

        async def catalog():
            queries.clear()
            async with db.transaction(readonly=True):
                return await module.local_retention_database_catalog(ObservedSource())

        try:
            baseline = await catalog()  # Current migrations must match the pinned constant.
            await db.execute('CREATE ROLE synthetic_routine_owner NOLOGIN')
            original = await db.fetchval("SELECT pg_get_functiondef('public.rec_setting(text)'::regprocedure)")
            changes = [
                ('extra', "CREATE FUNCTION public.synthetic_extra() RETURNS int LANGUAGE sql AS $$ SELECT 1 $$", 'DROP FUNCTION public.synthetic_extra()'),
                ('purge_not_called', 'CREATE FUNCTION public.synthetic_purge() RETURNS void LANGUAGE sql AS $$ DELETE FROM public.anonymous_page_aggregate_buckets $$', 'DROP FUNCTION public.synthetic_purge()'),
                ('overload', 'CREATE FUNCTION public.rec_setting(int) RETURNS int LANGUAGE sql AS $$ SELECT $1 $$', 'DROP FUNCTION public.rec_setting(int)'),
                ('other_schema', 'CREATE SCHEMA synthetic; CREATE FUNCTION synthetic.f() RETURNS int LANGUAGE sql AS $$ SELECT 1 $$', 'DROP SCHEMA synthetic CASCADE'),
                ('pg_catalog', 'CREATE FUNCTION pg_catalog.synthetic_extra() RETURNS int LANGUAGE sql AS $$ SELECT 1 $$', 'DROP FUNCTION pg_catalog.synthetic_extra()'),
                ('body', "CREATE OR REPLACE FUNCTION public.rec_setting(name text) RETURNS text LANGUAGE sql STABLE AS $$ SELECT NULL::text $$", original),
                ('security', 'ALTER FUNCTION public.rec_setting(text) SECURITY DEFINER', original),
                ('config', 'ALTER FUNCTION public.rec_setting(text) SET search_path=public', original),
                ('owner', 'ALTER FUNCTION public.rec_setting(text) OWNER TO synthetic_routine_owner', 'ALTER FUNCTION public.rec_setting(text) OWNER TO twobrain_rec'),
                ('parallel', 'ALTER FUNCTION public.rec_setting(text) PARALLEL SAFE', original),
                ('leakproof', 'ALTER FUNCTION public.rec_setting(text) LEAKPROOF', original),
                ('strict', 'ALTER FUNCTION public.rec_setting(text) STRICT', original),
                ('cost', 'ALTER FUNCTION public.rec_setting(text) COST 222', original),
                ('procedure', 'CREATE PROCEDURE public.synthetic_proc() LANGUAGE sql AS $$ SELECT 1 $$', 'DROP PROCEDURE public.synthetic_proc()'),
                ('aggregate', 'CREATE AGGREGATE public.synthetic_sum(bigint) (SFUNC=pg_catalog.int8pl,STYPE=bigint,INITCOND=0)', 'DROP AGGREGATE public.synthetic_sum(bigint)'),
                ('language', 'CREATE LANGUAGE synthetic_language HANDLER plpgsql_call_handler VALIDATOR plpgsql_validator', 'DROP LANGUAGE synthetic_language'),
                ('fdw', 'CREATE FOREIGN DATA WRAPPER synthetic_fdw NO HANDLER NO VALIDATOR', 'DROP FOREIGN DATA WRAPPER synthetic_fdw'),
                ('server', 'CREATE FOREIGN DATA WRAPPER synthetic_fdw; CREATE SERVER synthetic_server FOREIGN DATA WRAPPER synthetic_fdw', 'DROP SERVER synthetic_server; DROP FOREIGN DATA WRAPPER synthetic_fdw'),
                ('event', "CREATE FUNCTION public.synthetic_event() RETURNS event_trigger LANGUAGE plpgsql AS $$ BEGIN END $$; CREATE EVENT TRIGGER synthetic_event ON ddl_command_end EXECUTE FUNCTION public.synthetic_event()", 'DROP EVENT TRIGGER synthetic_event; DROP FUNCTION public.synthetic_event()'),
                ('search_path', "SET search_path=pg_catalog,public", 'RESET search_path'),
            ]
            for name, change, undo in changes:
                await db.execute(change)
                try:
                    with pytest.raises(ActivationHold, match='retention_catalog'):
                        await catalog()
                    if name in ('procedure', 'aggregate', 'event', 'language', 'search_path'):
                        assert not any('pg_get_functiondef' in q for q in queries), name
                finally:
                    await db.execute(undo)
                assert await catalog() == baseline, name

            # PostgreSQL cannot remove a newly added default with CREATE OR REPLACE.
            # Roll this one DDL change back instead of dropping a shared helper.
            transaction = db.transaction()
            await transaction.start()
            try:
                await db.execute(original.replace('rec_setting(name text)',
                    "rec_setting(name text DEFAULT 'synthetic'::text)"))
                await db.execute('SET TRANSACTION READ ONLY')
                with pytest.raises(ActivationHold, match='retention_catalog'):
                    await module.local_retention_database_catalog(db)
            finally:
                await transaction.rollback()
            assert await catalog() == baseline

            with monkeypatch.context() as patch:
                patch.setattr(module, 'EXPECTED_ROUTINES_SHA256', '0' * 64)
                with pytest.raises(ActivationHold, match='retention_catalog'):
                    await catalog()
            assert await catalog() == baseline
            await db.execute('DROP ROLE synthetic_routine_owner')
            await db.execute('CREATE ROLE twobrain_rec_maintenance LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT')
            await db.execute('SET SESSION AUTHORIZATION twobrain_rec_maintenance')
            assert await catalog() == baseline
        finally:
            await db.close()

    asyncio.run(run())
