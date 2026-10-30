# Чек-лист качества спецификации: личный кабинет и биллинг

**Назначение**: проверить полноту и тестируемость требований до планирования.
**Создан**: 2026-08-06
**Спецификация**: [spec.md](../spec.md)

## Содержание и границы

- [x] CHK001 Все обязательные разделы заполнены; шаблонные маркеры и `NEEDS CLARIFICATION` отсутствуют.
- [ ] CHK002 Пользовательская ценность, actors, authority и workspace/account scope определены однозначно. [Spec §Scope, §Actors, FR-001–FR-019] Проверка 2026-10-30: B1; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [x] CHK003 Launch scope и out-of-scope отделяют обязательный минимум от team billing, overage, cash rewards и multi-provider. [Spec §Product Decisions, §Out Of Scope]
- [x] CHK004 Каждая P1/P2 история независимо проверяема и содержит acceptance scenarios. [Spec §User Scenarios]
- [x] CHK005 Цена и налоговые значения не выдуманы: для них определён blocking approval gate. [FR-023, FR-051, FR-080]

## Требования и измеримость

- [x] CHK006 Все требования сформулированы проверяемым `MUST/MUST NOT/SHOULD`, без субъективных «удобно» и «быстро».
- [x] CHK007 Денежные и entitlement state machines, authority и идемпотентность заданы явно. [FR-032–FR-055]
- [x] CHK008 Promo/referral lifecycle, stacking, caps, maturity, abuse и reversal заданы. [FR-057–FR-069]
- [x] CHK009 Error/loading/empty/success, retry, unknown result и recovery states покрыты. [FR-039, FR-042–FR-044, FR-073]
- [x] CHK010 Success criteria имеют числовые или бинарные критерии и не зависят от способа реализации. [SC-001–SC-012]

## Риск и готовность

- [x] CHK011 Capture safety и deletion truth сохранены; коммерческий статус не блокирует Record/Stop/deletion/export. [FR-019, FR-026, FR-048]
- [ ] CHK012 Tenant isolation, CSRF, secret discipline, analytics masking и audit определены. [FR-005, FR-075–FR-080] Проверка 2026-10-30: B1; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [ ] CHK013 Доступность, локализация, reflow и brand-distance имеют проверяемые требования. [FR-081–FR-086] Проверка 2026-10-30: X7; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [ ] CHK014 Reconciliation, emergency stop, мониторинг, test shop и real-shop canary являются launch gates. [FR-087–FR-092] Проверка 2026-10-30: B2, X5; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [x] CHK015 Зависимости и внешние согласования перечислены, публичная готовность не обещана заранее. [Spec §Dependencies, SC-012]

## Результат

Спецификация пригодна для планирования. Формальных вопросов clarification нет; неизвестные коммерческие значения превращены в явные blocking gates, а не в допущения реализации.

## Перепроверка новых продуктовых решений 2026-08-06

- [x] CHK016 Paid `unlimited` scope отделён от Free quota, finite storage и technical/fair-use ceilings. [FR-024–FR-028, FR-093–FR-100]
- [ ] CHK017 Storage allowances, chargeable bytes, reservation/delete truth, thresholds, add-on lifecycle and over-capacity последствия однозначны. [FR-093–FR-100] Проверка 2026-10-30: X6; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [ ] CHK018 No-grace renewal, unknown cutoff, late success and fresh manual resume имеют complete state/acceptance coverage. [US5, FR-040–FR-048] Проверка 2026-10-30: X5; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [ ] CHK019 Refund request, legal/operator calculation, provider/off-provider execution and entitlement effects разделены. [US6, FR-053–FR-056, FR-102] Проверка 2026-10-30: X4; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [x] CHK020 Referral 7/30-day mapping, rolling cap, Free expiry, application and bounded reversal измеримы. [US8, FR-063–FR-069, FR-101]

Результат перепроверки: PASS — критические решения пользователя интегрированы без implementation placeholder; price/legal/COGS остаются explicit launch gates.

## Финальный cross-domain audit 2026-08-06

- [x] CHK021 Unlimited paid processing remains usable at full archive through explicit transient-media mode with terminal purge and truthful no-playback copy. [FR-096, FR-106]
- [x] CHK022 Fair-use has enumerated grounds, no single volume/IP/device evidence, ≤24h review, notice/appeal and preserved capture/data controls. [FR-107]
- [ ] CHK023 Recurring refusal, late success and planned-vs-actual entitlement precedence are deterministic. [FR-103–FR-105] Проверка 2026-10-30: X4; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [x] CHK024 Cancel-scheduled referral credit and co-termed add-on never recreate a charge job. [FR-097, FR-101, FR-108]
- [ ] CHK025 Recommended prices/Free allowance are versioned, testable and blocked from checkout pending approvals. [Product Decisions, FR-023] Проверка 2026-10-30: X6; см. [отчёт T075](../t075-requirements-review-20261030.md).

Результат финального аудита: PASS — новые product/economic boundaries no longer rely on hidden implementation choices.

## Независимая перепроверка перед T075 — 2026-10-30

Перечитаны все пункты этого списка и относящиеся к ним требования. Исторические результаты выше сохранены; они не являются текущим PASS. Снятые отметки и область каждого расхождения объяснены в [отчёте T075](../t075-requirements-review-20261030.md). Сохранённые `[x]` подтверждают достаточность соответствующей формулировки требований в проверенной области, а не выполнение тестов, выпуск, готовность всей F140 или закрытие issue.
Текущий подсчёт: **16 отмечены / 9 открыты**. Решение по реализации T075: **BLOCK** до устранения B1–B3.

## Повторное ревью проекта импорта T075 — 2026-10-30

К текущему импорту применимы CHK002/CHK012 (B1), CHK014 (только часть B2), CHK009 (восстановление B3) и общие запреты приватных данных. B1–B3 определены новым контрактом. Полный reconciliation/launch и X4–X7 этими выводами не принимаются.

**PASS только для требований первой части операторского импорта B1–B3** по [новому отчёту](../t075-import-design-review-20261030.md). Предыдущий BLOCK сохраняется как результат прежней версии требований; он снят только для этой ограниченной части после уточнения контракта. Это не глобальный PASS списка, не реализация и не закрытие T075/#4930. Полнота файлов оставляет `financial_status=not_checked`.

Все 25 исходных пунктов перечитаны; глобальные отметки не изменены: **16 отмечены / 9 открыты**. Старые X4–X7 и внешние условия запуска сохраняются отдельно от предметного PASS.
