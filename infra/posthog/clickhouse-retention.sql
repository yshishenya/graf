-- Forced row lifetime for measurement events (FR-036, SC-011).
--
-- Measurement levels 2 and 3 (registered-user data and consent-based
-- measurement) live in ClickHouse inside PostHog. Their retention is applied as
-- a row TTL on the MergeTree table that stores them, so expired rows are
-- removed by ClickHouse merges without a per-row delete loop.
--
-- `events` and `writable_events` are Distributed tables over `sharded_events`;
-- a distributed table cannot carry a TTL, so the TTL belongs on
-- `sharded_events`, which every insert path reaches.
--
-- Apply with `infra/scripts/apply-posthog-event-ttl.sh --execute`, which
-- substitutes {{RETENTION_DAYS}} and verifies the resulting TTL. The statement
-- is idempotent: re-applying the same interval is a no-op.
--
-- Never edit the interval here to a value shorter than the approved term:
-- the readiness check compares the enforced TTL with the approved 365 days and
-- blocks the analytics readiness claim when it is lower.

ALTER TABLE sharded_events
    MODIFY TTL toDateTime(timestamp) + toIntervalDay({{RETENTION_DAYS}});
