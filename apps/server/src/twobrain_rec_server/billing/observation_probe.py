"""One bounded read-only snapshot of attempts and anonymous receipt deltas."""
from datetime import UTC

from sqlalchemy import text

from twobrain_rec_server.billing.database import require_billing_maintenance_database
from twobrain_rec_server.billing.observation_alerts import (
    COUNTERS,
    RECEIPT_COUNTERS,
    canonical,
    require,
    validate_sample,
)

# PostgreSQL's deparsed form of the policy installed by 0111. Check visibility
# before accepting zero: FORCE RLS alone can hide an entire nonempty source.
_RECEIPT_READ_POLICY = (
    "((SESSION_USER = 'twobrain_rec_maintenance'::name) AND "
    "(CURRENT_USER = 'twobrain_rec_maintenance'::name) AND "
    "(current_setting('row_security'::text) = 'on'::text) AND "
    "(rec_context_kind() = 'maintenance'::text) AND rec_maintenance_allowed() AND "
    "(rec_setting('app.maintenance_operation'::text) = 'billing_reconciliation'::text) AND "
    "(rec_setting('app.maintenance_feature_area'::text) = 'billing'::text))"
)


async def collect_probe(db, *, source_profile, source_generation):
    await require_billing_maintenance_database(db)
    protected = (await db.execute(text("""
        SELECT count(*) = 2 AND bool_and(relrowsecurity AND relforcerowsecurity)
        FROM pg_class WHERE oid IN ('public.billing_reconciliation_observations'::regclass,
                                    'public.billing_receipt_observation_deltas'::regclass)
    """))).scalar_one()
    require(protected is True)
    receipt_policies = (await db.execute(text("""
        SELECT polname, polcmd::text, polpermissive, polroles = ARRAY[0::oid],
               replace(pg_get_expr(polqual, polrelid), 'public.rec_', 'rec_')
        FROM pg_policy WHERE polrelid = 'public.billing_receipt_observation_deltas'::regclass
            AND polcmd IN ('r', '*')
    """))).all()
    require(receipt_policies == [("receipt_observation_read", "r", True, True, _RECEIPT_READ_POLICY)])
    row = (await db.execute(text("""
        WITH attempts AS (
          SELECT statement_timestamp() AS as_of, count(*) AS event_count,
            count(*) FILTER (WHERE event_kind='failed') AS failed_event_count,
            max(observed_at) AS last_event_at,
            coalesce(bool_and(isfinite(observed_at)),true) AS finite_times,
            (SELECT count(*) FROM (
              SELECT 1 FROM public.billing_reconciliation_observations
              GROUP BY namespace,workflow_id,workflow_run_id,activity_id,attempt
              HAVING count(*) FILTER (WHERE event_kind<>'started')>1
            ) conflicts) AS conflicting_attempt_count
          FROM public.billing_reconciliation_observations
        ), receipts AS (
          SELECT coalesce(sum(canceled_delta), 0)::bigint AS receipt_canceled_count,
                 coalesce(sum(overdue_confirmed_delta), 0)::bigint AS receipt_overdue_confirmed_count,
                 coalesce(sum(overdue_unknown_delta), 0)::bigint AS receipt_overdue_unknown_count
          FROM public.billing_receipt_observation_deltas
        )
        SELECT attempts.*, receipts.* FROM attempts CROSS JOIN receipts
    """))).mappings().one()
    require(row["finite_times"] is True)
    result = {"schema_version": 2, "source_profile": source_profile, "source_generation": source_generation,
              "as_of": row["as_of"].astimezone(UTC).isoformat(), "coverage": "partial",
              **{key: row[key] for key in (*COUNTERS, *RECEIPT_COUNTERS.values())},
              "last_event_at": None if row["last_event_at"] is None else row["last_event_at"].astimezone(UTC).isoformat()}
    validate_sample(result)
    require(len(canonical(result)) + 1 <= 16 * 1024)
    return result
