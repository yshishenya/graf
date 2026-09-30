-- Агрегированная сверка. Не выбирать PII, содержимое JSON payload, аудио/тексты.
-- Запуск: psql --set=ON_ERROR_STOP=1 --file=docs/organic-measurement-audit-2026-09-30.sql
-- Соединение задаёт оператор через существующий защищённый способ.
-- READ ONLY запрещает изменения; результаты не являются provider reconciliation.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '10s';
SELECT 'anonymous_requests' AS metric, count(*) AS buckets,
       coalesce(sum(visits), 0) AS requests,
       min(bucket_date) AS first_date, max(bucket_date) AS last_date
FROM anonymous_page_aggregate_buckets;
-- Общее окно с прочитанным отчётом Метрики: 30 августа–29 сентября.
-- Числа остаются requests, их нельзя делить на Metрика sessions как consent rate.
SELECT surface, traffic_class, sum(visits) AS requests
FROM anonymous_page_aggregate_buckets
WHERE bucket_date BETWEEN DATE '2026-08-30' AND DATE '2026-09-29'
GROUP BY surface, traffic_class HAVING sum(visits) >= 5
ORDER BY surface, traffic_class;
SELECT 'visit_attribution' AS metric, count(*) AS rows,
       count(*) FILTER (WHERE source IS NOT NULL) AS with_source
FROM public_visit_attributions;
SELECT 'acquisition' AS metric, count(*) AS rows,
       count(*) FILTER (WHERE graf_attribution_id IS NOT NULL) AS with_bridge
FROM client_acquisition_attributes;
SELECT 'account_baseline' AS metric, count(*) AS accounts,
       min(created_at) AS first_created, max(created_at) AS last_created
FROM user_identities;
SELECT 'result_baseline' AS metric, count(*) AS results FROM processing_results;
SELECT status, count(*) AS workflows FROM processing_workflows
GROUP BY status HAVING count(*) >= 5 ORDER BY status;
SELECT 'billing_keys_only' AS metric, count(*) AS operations,
       count(DISTINCT idempotency_key) AS unique_keys FROM billing_operations;
SELECT 'webhook_keys_only' AS metric, count(*) AS webhooks,
       count(DISTINCT provider_event_id) AS unique_keys FROM billing_webhook_events;
ROLLBACK;
