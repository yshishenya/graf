-- Только агрегаты, без distinct_id, person, properties и содержимого встреч.
SELECT count() AS events,min(timestamp),max(timestamp),
 countIf(timestamp>=toDateTime('2026-09-17','UTC') AND timestamp<toDateTime('2026-10-15','UTC')) AS last_28d
FROM posthog.events WHERE team_id=1
SETTINGS max_execution_time=10,max_rows_to_read=1000000,max_bytes_to_read=104857600,max_memory_usage=268435456;
SELECT name,match(create_table_query,'(?i)(^|[[:space:]])TTL[[:space:]]') AS ttl_defined
FROM system.tables WHERE database='posthog' AND name IN ('events','sharded_events')
SETTINGS max_execution_time=10,max_rows_to_read=1000000,max_bytes_to_read=104857600,max_memory_usage=268435456;
