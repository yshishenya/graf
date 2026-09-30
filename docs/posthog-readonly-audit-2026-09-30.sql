-- Только read-only агрегаты project 1. Выполнено через существующий ClickHouse.
-- Никаких person/distinct identifiers, IP values, payload или meeting content.
SELECT count() AS events, min(timestamp), max(timestamp), uniqExact(uuid) AS unique_uuid
FROM posthog.events WHERE team_id=1;
SELECT event, count() AS events, min(timestamp), max(timestamp)
FROM posthog.events WHERE team_id=1 GROUP BY event ORDER BY events DESC;
SELECT name, position(create_table_query,' TTL ')>0 AS ttl_defined
FROM system.tables WHERE database='posthog' AND name IN ('events','sharded_events');
SELECT arrayJoin(JSONExtractKeys(properties)) AS property_key, count()
FROM posthog.events WHERE team_id=1 GROUP BY property_key ORDER BY property_key;
SELECT count() AS total,
       countIf(JSONHas(properties,'$ip')) AS ip_present,
       countIf(JSONHas(properties,'email') OR JSONHas(properties,'transcript')
               OR JSONHas(properties,'meeting_title')) AS forbidden_field_present
FROM posthog.events WHERE team_id=1;
SELECT event, count() AS duplicated_identities, sum(n-1) AS extra_events
FROM (
 SELECT event,distinct_id,count() AS n FROM posthog.events
 WHERE team_id=1 AND event IN ('desktop_first_opened','desktop_account_connected',
 'first_recording_completed','first_result_viewed','first_value_session_completed')
 GROUP BY event,distinct_id HAVING n>1
) GROUP BY event;
SELECT count() AS recent_events,
 countIf(JSONExtractBool(properties,'bridge_present')) AS bridge_present_events,
 countIf(JSONHas(properties,'utm_source')) AS events_with_source_label
FROM posthog.events WHERE team_id=1 AND timestamp>=now()-INTERVAL 30 DAY;
