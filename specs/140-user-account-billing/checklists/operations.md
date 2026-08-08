# Чек-лист качества требований: эксплуатация и launch

- [x] CHK001 Webhook, poller, API/list и daily registry reconciliation определены. [FR-087]
- [x] CHK002 Stale object и gap всегда имеют owner/status/resolution, silent final state запрещён. [FR-087, SC-008]
- [x] CHK003 Stop-all-charges scope сохраняет history/cancel/product availability. [FR-088]
- [x] CHK004 Метрики покрывают money lifecycle без private payload. [FR-089]
- [x] CHK005 Test-shop matrix включает success/failure/race/outage/refund/receipt. [FR-090]
- [x] CHK006 Real-shop canary завершает полный payment/refund/registry цикл. [FR-091]
- [x] CHK007 Notification dedupe/delivery failure входит в operational truth. [FR-070–FR-072, SC-011]
- [x] CHK008 Manual correction/refund требует actor/reason/audit/four-eyes. [FR-056, FR-079]
- [x] CHK009 Legal/finance/security/QA/product/release approvals являются отдельными gates. [FR-080, FR-092, SC-012]
- [x] CHK010 Feature не отменяет общие `pilot_blocked` gaps и не объявляет публичный launch. [FR-092, Dependencies]

Результат: PASS — production flag должен оставаться off до полной матрицы approvals/evidence.

## Перепроверка новых операций 2026-08-06

- [x] CHK011 One-attempt renewal, Free cutoff, unknown/late success and no-retry observability/runbooks определены. [FR-040–FR-048, FR-089]
- [x] CHK012 Storage inventory/reservations, add-on renewal/change and reconciliation имеют owner/gap/runbook. [FR-093–FR-100, FR-087–FR-089]
- [x] CHK013 Внешний refund SLA/calculation/operator execution и off-provider reconciliation разделены; GRAF хранит только observed provider truth и metadata-only gap/audit. [FR-053–FR-056, FR-087–FR-091]
- [x] CHK014 Time-credit maturity/application/expiry/reversal and cap входят в deterministic jobs/monitoring. [FR-063–FR-069, FR-101]

Результат перепроверки: PASS — launch matrix расширена storage/add-on/time-credit/request-only refund evidence.

## Финальная операционная проверка 2026-08-06

- [x] CHK015 Authority/refusal races, planned-vs-actual grants and late-after-refusal cases have deterministic reconciliation paths. [FR-103–FR-105]
- [x] CHK016 Transient-media expiry/purge and paid actual-use writer have source-backed reconciliation. [FR-027, FR-106]
- [x] CHK017 Emergency stop scope preserves external support-email instruction/refusal/cancel and blocks every GRAF money execution path. [FR-109]
- [x] CHK018 Referral Temporal wiring covers start/replay, active anchor, cancel-scheduled cutoff and add-on bonus interval. [FR-101, FR-108]

Результат финальной проверки: PASS — operational ownership covers all new durable states.
