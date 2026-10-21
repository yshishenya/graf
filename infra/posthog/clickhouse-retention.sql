-- T109: preserve event history until a separate deletion decision.
-- The migration removes metadata only; it does not DELETE or materialize TTL.
ALTER TABLE posthog.sharded_events REMOVE TTL;
