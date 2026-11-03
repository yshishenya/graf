-- Read-only повторная проверка 16.10.2026, без выгрузки событий и идентификаторов.
-- Последние 28 завершённых UTC дней: [18.09, 16.10).
-- Запускать существующим операторским доступом clickhouse-client --multiquery.
SELECT currentDatabase() AS client_default_database, now() AS checked_at;

SELECT count() AS project_events, min(timestamp) AS first_event, max(timestamp) AS last_event,
 countIf(timestamp >= toDateTime('2026-09-18','UTC') AND timestamp < toDateTime('2026-10-16','UTC')) AS events_last_28_full_days,
 countIf(timestamp < now() - INTERVAL 365 DAY) AS older_than_365_days,
 countIf(notEmpty(JSONExtractString(properties,'$ip'))) AS events_with_nonempty_ip,
 countIf(notEmpty(JSONExtractString(properties,'$geoip_city_name'))) AS events_with_geoip_city
FROM posthog.events WHERE team_id=1
SETTINGS readonly=2,max_execution_time=10,max_rows_to_read=1000000,max_bytes_to_read=104857600,max_memory_usage=268435456;

-- Общий TTL физической таблицы затронет все проекты; общий счётчик не является трафиком ГРАФ.
SELECT count() AS all_project_events, uniqExact(team_id) AS projects_in_table,
 countIf(timestamp < now() - INTERVAL 365 DAY) AS older_than_365_days
FROM posthog.events
SETTINGS readonly=2,max_execution_time=10,max_rows_to_read=1000000,max_bytes_to_read=104857600,max_memory_usage=268435456;

SELECT name,engine,match(create_table_query,'(?i)(^|[[:space:]])TTL[[:space:]]') AS ttl_defined
FROM system.tables WHERE database='posthog' AND name IN ('events','sharded_events','writable_events')
SETTINGS readonly=2,max_execution_time=10,max_rows_to_read=1000000,max_bytes_to_read=104857600,max_memory_usage=268435456;

SELECT count() AS replica_rows,sum(is_readonly) AS readonly_replicas,
 sum(is_session_expired) AS expired_sessions,max(total_replicas) AS configured_replicas,
 max(active_replicas) AS active_replicas
FROM system.replicas WHERE database='posthog' AND table='sharded_events'
SETTINGS readonly=2,max_execution_time=10;

SELECT database,name,engine FROM system.tables WHERE name='sharded_events'
SETTINGS readonly=2,max_execution_time=10;
