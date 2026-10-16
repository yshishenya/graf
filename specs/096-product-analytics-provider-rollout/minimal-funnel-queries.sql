-- HogQL proposals for the existing self-hosted PostHog project 1.
-- Not executed or installed; supported operator login and real ingestion proof required.
-- No meeting/customer content; only explicit categories and pseudonymous distinct_id.
-- Cohort: observed after personal consent, NOT all installs or first-ever launches.

SELECT event, count() AS rows, count(DISTINCT distinct_id) AS consenting_accounts
FROM events
WHERE timestamp >= now() - INTERVAL 30 DAY
  AND event IN ('desktop_first_opened', 'desktop_account_connected',
                'first_recording_completed', 'first_result_viewed',
                'first_value_session_completed')
GROUP BY event
ORDER BY event;

-- One synthetic UUID retry may be multiple raw rows until actual dedupe is verified.
-- A nonzero result blocks acceptance of the delivery contract.
SELECT uuid, count() AS rows
FROM events
WHERE timestamp >= now() - INTERVAL 1 DAY
  AND event IN ('desktop_first_opened', 'desktop_account_connected',
                'first_recording_completed', 'first_result_viewed',
                'first_value_session_completed')
GROUP BY uuid
HAVING count() > 1;

-- Weak client-reported acquisition categories. Unknown is not direct or AI.
-- Use only after checking server category contract and ingestion in project 1.
SELECT properties.utm_source AS reported_source,
       properties.attribution_reliability AS reliability,
       count(DISTINCT distinct_id) AS consenting_activated_accounts
FROM events
WHERE timestamp >= now() - INTERVAL 30 DAY
  AND event = 'first_value_session_completed'
  AND properties.useful_output_present IN ('true', true)
GROUP BY reported_source, reliability;

-- Paid conversion, refunds and D7 return are deliberately outside these five
-- one-time milestones. They require actual server outcome/reconciliation and a
-- separate repeatable retention signal; do not infer them from first launch.
