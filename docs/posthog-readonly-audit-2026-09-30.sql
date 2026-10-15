-- Исправленная методика от 15 октября; повторно в production не запускалась.
-- Только агрегаты project 1 за фиксированное окно [2026-07-01, 2026-10-01) UTC.
-- Никаких значений person/distinct identifiers, IP, JSON или содержимого встреч.
-- Каждый SELECT ограничен временем, чтением и памятью; превышение = ошибка,
-- не частичный результат. Не увеличивать лимиты на production ради отчёта.
-- Между SELECT нет общего снимка ClickHouse: возможны поздние записи/мутации.
SELECT count() AS events, min(timestamp), max(timestamp), uniqExact(uuid) AS unique_uuid
FROM posthog.events WHERE team_id=1 AND timestamp>=toDateTime('2026-07-01', 'UTC') AND timestamp<toDateTime('2026-10-01', 'UTC') SETTINGS max_execution_time=10, timeout_overflow_mode='throw', max_rows_to_read=1000000, max_bytes_to_read=104857600, read_overflow_mode='throw', max_memory_usage=268435456;
SELECT event, count() AS events, min(timestamp), max(timestamp)
FROM posthog.events WHERE team_id=1 AND timestamp>=toDateTime('2026-07-01', 'UTC') AND timestamp<toDateTime('2026-10-01', 'UTC') GROUP BY event ORDER BY events DESC SETTINGS max_execution_time=10, timeout_overflow_mode='throw', max_rows_to_read=1000000, max_bytes_to_read=104857600, read_overflow_mode='throw', max_memory_usage=268435456;
-- Наличие TTL не доказывает его срок или фактическое удаление.
SELECT name, match(create_table_query,'(?i)(^|[[:space:]])TTL[[:space:]]') AS ttl_defined
FROM system.tables WHERE database='posthog' AND name IN ('events','sharded_events') SETTINGS max_execution_time=10, timeout_overflow_mode='throw', max_rows_to_read=1000000, max_bytes_to_read=104857600, read_overflow_mode='throw', max_memory_usage=268435456;
-- Только три точных ключа верхнего уровня, НЕ проверка приватности.
-- Ноль не означает отсутствие других полей, вложенных данных или PII в значениях.
-- Полная проверка: существующий рекурсивный forbidden_fields.py и его тесты
-- на синтетических данных; содержимое production properties не выгружать.
SELECT count() AS total,
       countIf(JSONHas(properties,'$ip')) AS ip_key_present,
       countIf(JSONHas(properties,'email') OR JSONHas(properties,'transcript')
               OR JSONHas(properties,'meeting_title')) AS three_top_level_keys_present
FROM posthog.events WHERE team_id=1 AND timestamp>=toDateTime('2026-07-01', 'UTC') AND timestamp<toDateTime('2026-10-01', 'UTC') SETTINGS max_execution_time=10, timeout_overflow_mode='throw', max_rows_to_read=1000000, max_bytes_to_read=104857600, read_overflow_mode='throw', max_memory_usage=268435456;
-- Список соответствует PRODUCT_ACTIVATION_EVENT_NAMES / FIRST_MILESTONE_EVENTS.
-- Это дубли в пределах окна по provider distinct_id, не доказательство
-- дедупликации аккаунтов между устройствами или за всю историю.
SELECT event, count() AS duplicated_identities, sum(n-1) AS extra_events
FROM (
 SELECT event,distinct_id,count() AS n FROM posthog.events
 WHERE team_id=1 AND timestamp>=toDateTime('2026-07-01', 'UTC') AND timestamp<toDateTime('2026-10-01', 'UTC')
 AND event IN ('desktop_first_opened','desktop_account_connected','desktop_autorecord_enabled',
 'first_recording_completed','first_result_viewed','first_value_session_completed')
 GROUP BY event,distinct_id HAVING n>1
) GROUP BY event SETTINGS max_execution_time=10, timeout_overflow_mode='throw', max_rows_to_read=1000000, max_bytes_to_read=104857600, read_overflow_mode='throw', max_memory_usage=268435456;
-- Сентябрьское окно фиксировано; null/пустая метка не считается известной.
SELECT count() AS september_events,
 countIf(JSONExtractBool(properties,'bridge_present')) AS bridge_present_events,
 countIf(JSONExtractString(properties,'campaign_label_state')='known'
         AND notEmpty(trimBoth(JSONExtractString(properties,'utm_source')))) AS events_with_source_label
FROM posthog.events WHERE team_id=1 AND timestamp>=toDateTime('2026-09-01', 'UTC') AND timestamp<toDateTime('2026-10-01', 'UTC') SETTINGS max_execution_time=10, timeout_overflow_mode='throw', max_rows_to_read=1000000, max_bytes_to_read=104857600, read_overflow_mode='throw', max_memory_usage=268435456;
