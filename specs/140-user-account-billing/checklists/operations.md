# Чек-лист качества требований: эксплуатация и launch

- [ ] CHK001 Webhook, poller, API/list и daily registry reconciliation определены. [FR-087] Проверка 2026-10-30: B2; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [ ] CHK002 Stale object и gap всегда имеют owner/status/resolution, silent final state запрещён. [FR-087, SC-008] Проверка 2026-10-30: B3; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [ ] CHK003 Stop-all-charges scope сохраняет history/cancel/product availability. [FR-088] Проверка 2026-10-30: X5; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [x] CHK004 Метрики покрывают money lifecycle без private payload. [FR-089]
- [x] CHK005 Test-shop matrix включает success/failure/race/outage/refund/receipt. [FR-090]
- [x] CHK006 Real-shop canary завершает полный payment/refund/registry цикл. [FR-091]
- [x] CHK007 Notification dedupe/delivery failure входит в operational truth. [FR-070–FR-072, SC-011]
- [ ] CHK008 Manual correction/refund требует actor/reason/audit/four-eyes. [FR-056, FR-079] Проверка 2026-10-30: X4; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [x] CHK009 Legal/finance/security/QA/product/release approvals являются отдельными gates. [FR-080, FR-092, SC-012]
- [x] CHK010 Feature не отменяет общие `pilot_blocked` gaps и не объявляет публичный launch. [FR-092, Dependencies]

Результат: PASS — production flag должен оставаться off до полной матрицы approvals/evidence.

## Перепроверка новых операций 2026-08-06

- [ ] CHK011 One-attempt renewal, Free cutoff, unknown/late success and no-retry observability/runbooks определены. [FR-040–FR-048, FR-089] Проверка 2026-10-30: X5; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [x] CHK012 Storage inventory/reservations, add-on renewal/change and reconciliation имеют owner/gap/runbook. [FR-093–FR-100, FR-087–FR-089]
- [ ] CHK013 Внешний refund SLA/calculation/operator execution и off-provider reconciliation разделены; GRAF хранит только observed provider truth и metadata-only gap/audit. [FR-053–FR-056, FR-087–FR-091] Проверка 2026-10-30: X4; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [x] CHK014 Time-credit maturity/application/expiry/reversal and cap входят в deterministic jobs/monitoring. [FR-063–FR-069, FR-101]

Результат перепроверки: PASS — launch matrix расширена storage/add-on/time-credit/request-only refund evidence.

## Финальная операционная проверка 2026-08-06

- [ ] CHK015 Authority/refusal races, planned-vs-actual grants and late-after-refusal cases have deterministic reconciliation paths. [FR-103–FR-105] Проверка 2026-10-30: X4; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [x] CHK016 Transient-media expiry/purge and paid actual-use writer have source-backed reconciliation. [FR-027, FR-106]
- [ ] CHK017 Emergency stop scope preserves external support-email instruction/refusal/cancel and blocks every GRAF money execution path. [FR-109] Проверка 2026-10-30: X5; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [x] CHK018 Referral Temporal wiring covers start/replay, active anchor, cancel-scheduled cutoff and add-on bonus interval. [FR-101, FR-108]

Результат финальной проверки: PASS — operational ownership covers all new durable states.

## Независимая перепроверка перед T075 — 2026-10-30

Перечитаны все пункты этого списка и относящиеся к ним требования. Исторические результаты выше сохранены; они не являются текущим PASS. Снятые отметки и область каждого расхождения объяснены в [отчёте T075](../t075-requirements-review-20261030.md). Сохранённые `[x]` подтверждают достаточность соответствующей формулировки требований в проверенной области, а не выполнение тестов, выпуск, готовность всей F140 или закрытие issue.
Текущий подсчёт: **10 отмечены / 8 открыты**. Решение по реализации T075: **BLOCK** до устранения B1–B3.

## Повторное ревью проекта импорта T075 — 2026-10-30

CHK001/CHK002 проверены в узкой части: ввод обоих видов, completeness, сохраняемый результат и поколение расхождения. Полная сверка API/ledger, общая система incidents, monitoring и canary не входят. Упрощённый detected/resolved путь не отменяет общий процесс инцидентов.

**PASS только для требований первой части операторского импорта B1–B3** по [новому отчёту](../t075-import-design-review-20261030.md). Предыдущий BLOCK сохраняется как результат прежней версии требований; он снят только для этой ограниченной части после уточнения контракта. Это не глобальный PASS списка, не реализация и не закрытие T075/#4930. Полнота файлов оставляет `financial_status=not_checked`.

Все 18 исходных пунктов перечитаны; глобальные отметки не изменены: **10 отмечены / 8 открыты**. Старые X4–X7 и внешние условия запуска сохраняются отдельно от предметного PASS.
