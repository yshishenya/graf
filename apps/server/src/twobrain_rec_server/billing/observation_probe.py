"""One bounded read-only snapshot of the accepted attempt journal (0109)."""
from datetime import UTC

from sqlalchemy import text

from twobrain_rec_server.billing.database import require_billing_maintenance_database
from twobrain_rec_server.billing.observation_alerts import canonical, require, validate_sample


async def collect_probe(db, *, source_profile, source_generation):
    await require_billing_maintenance_database(db)
    protected = (await db.execute(text(
        "SELECT relrowsecurity AND relforcerowsecurity "
        "FROM pg_class WHERE oid='billing_reconciliation_observations'::regclass"
    ))).scalar_one()
    require(protected is True)
    row = (await db.execute(text("""
        SELECT statement_timestamp() AS as_of, count(*) AS event_count,
          count(*) FILTER (WHERE event_kind='failed') AS failed_event_count,
          max(observed_at) AS last_event_at,
          coalesce(bool_and(isfinite(observed_at)),true) AS finite_times,
          (SELECT count(*) FROM (
            SELECT 1 FROM billing_reconciliation_observations
            GROUP BY namespace,workflow_id,workflow_run_id,activity_id,attempt
            HAVING count(*) FILTER (WHERE event_kind<>'started')>1
          ) conflicts) AS conflicting_attempt_count
        FROM billing_reconciliation_observations
    """))).mappings().one()
    require(row["finite_times"] is True)
    result = {"schema_version": 1, "source_profile": source_profile, "source_generation": source_generation,
              "as_of": row["as_of"].astimezone(UTC).isoformat(), "coverage": "partial",
              **{key: row[key] for key in ("event_count", "failed_event_count", "conflicting_attempt_count")},
              "last_event_at": None if row["last_event_at"] is None else row["last_event_at"].astimezone(UTC).isoformat()}
    validate_sample(result)
    require(len(canonical(result)) + 1 <= 16 * 1024)
    return result
