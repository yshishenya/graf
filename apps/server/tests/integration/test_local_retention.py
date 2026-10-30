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
