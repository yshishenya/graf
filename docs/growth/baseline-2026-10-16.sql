-- Только агрегаты. Снимок 15 октября UTC / 16 октября по времени пользователя.
-- Окно: [2026-09-17,2026-10-15) UTC, последние 28 завершённых UTC дней на момент проверки.
-- requests != sessions != people. Порог отчёта >=5; отсутствие строки не означает 0.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '10s';
SELECT count(*) AS buckets, sum(visits) AS requests, min(bucket_date), max(bucket_date)
FROM anonymous_page_aggregate_buckets;
SELECT surface,traffic_class,referrer_category,sum(visits) AS requests
FROM anonymous_page_aggregate_buckets
WHERE bucket_date >= DATE '2026-09-17' AND bucket_date < DATE '2026-10-15'
GROUP BY surface,traffic_class,referrer_category HAVING sum(visits)>=5
ORDER BY surface,traffic_class,referrer_category;
SELECT count(*) AS attributed_visits,count(*) FILTER (WHERE source IS NOT NULL) AS with_source
FROM public_visit_attributions;
SELECT count(*) AS acquisition_rows,count(*) FILTER (WHERE graf_attribution_id IS NOT NULL) AS with_bridge
FROM client_acquisition_attributes;
SELECT count(*) AS account_identities,max(created_at) AS last_created FROM user_identities;
SELECT count(*) AS processing_results FROM processing_results;
ROLLBACK;
