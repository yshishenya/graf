# Чек-лист качества требований: платежи

**Цель**: убедиться, что денежные требования полны, непротиворечивы и пригодны для release review.

- [x] CHK001 Источник истины разделён между provider object и GRAF subscription ledger. [FR-032, FR-041]
- [x] CHK002 Требования к сумме, валюте, invoice/receipt snapshot и округлению однозначны. [FR-020, FR-030, FR-049–FR-051]
- [x] CHK003 Идемпотентность покрывает double click, concurrent worker и период после provider TTL. [FR-033–FR-035]
- [x] CHK004 Unknown HTTP outcome не допускает новый payment до разрешения. [FR-043–FR-044]
- [x] CHK005 Saved-method success/failure/replacement и current-period consequence определены. [FR-037–FR-039]
- [ ] CHK006 Cancel/resume/no-grace renewal имеют точные состояния, даты, отсутствие повторов и CTA. [FR-040–FR-048] Проверка 2026-10-30: X5; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [x] CHK007 Refund отделён от cancel и содержит partial/full, pending, receipt и entitlement rules. [FR-053–FR-056]
- [x] CHK008 Promo calculation, atomic redemption, stacking и race описаны. [FR-057–FR-061]
- [ ] CHK009 Webhook/poll/API/registry reconciliation и emergency stop являются обязательными. [FR-087–FR-091] Проверка 2026-10-30: B2, X5; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [x] CHK010 Неутверждённые VAT/54-ФЗ/цены блокируют production вместо неявного дефолта. [FR-023, FR-051, FR-080, SC-012]

Результат: PASS — требований достаточно для plan/tasks; значения launch-конфигурации остаются gated.

## Перепроверка решений 2026-08-06

Исторический CHK006 описывает заменённую grace-модель; current gate задают пункты ниже.

- [ ] CHK011 Зафиксированы одна renewal operation, immediate `Free`, отсутствие scheduled retries и отдельный unknown/late-success flow. [FR-040–FR-048] Проверка 2026-10-30: X5; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [x] CHK012 Base/add-on invoice lines, shared anchor, positive mid-cycle pro-rata and next-period decrease/removal однозначны. [FR-093–FR-100]
- [x] CHK013 Публичное refund обращение отделено от operator approval/provider execution и не принимает пользовательскую сумму. [FR-053–FR-056, FR-102]
- [ ] CHK014 Pro-rata launch default, statutory reason classes, YooKassa limits and off-provider path имеют отдельные policy/legal gates. [FR-054–FR-056, FR-080] Проверка 2026-10-30: X4; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [x] CHK015 Referral discount приглашённого и 7/30-day service credit пригласившего не смешиваются с invoice/refund wallet. [FR-060, FR-063–FR-069, FR-101]

Результат перепроверки: PASS — прежняя grace-модель superseded; текущие no-grace/add-on/refund/time-credit требования полны.

## Финальная проверка authority и денег 2026-08-06

- [x] CHK016 Shared atomic recurring-authority version makes refusal win before any provider charge. [FR-044, FR-103]
- [ ] CHK017 Late-after-refusal stays Free, records one internal incident and sends static support-email instruction; no product case or keep-period workflow exists. [FR-048, FR-104] Проверка 2026-10-30: X4; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [x] CHK018 Invoice purchased duration/planned interval is separate from actual grant and fiscal wording. [FR-105]
- [x] CHK019 Consumer withdrawal affects access immediately while monetary state changes only after confirmed refund outcome. [FR-102]
- [ ] CHK020 Refund approval/execution concurrency and four-eyes produce exactly one money mutation. [FR-056, FR-102] Проверка 2026-10-30: X4; см. [отчёт T075](../t075-requirements-review-20261030.md).

Результат финальной проверки: PASS — race and authority rules are testable before provider mutation.

## Независимая перепроверка перед T075 — 2026-10-30

Перечитаны все пункты этого списка и относящиеся к ним требования. Исторические результаты выше сохранены; они не являются текущим PASS. Снятые отметки и область каждого расхождения объяснены в [отчёте T075](../t075-requirements-review-20261030.md). Сохранённые `[x]` подтверждают достаточность соответствующей формулировки требований в проверенной области, а не выполнение тестов, выпуск, готовность всей F140 или закрытие issue.
Текущий подсчёт: **14 отмечены / 6 открыты**. Решение по реализации T075: **BLOCK** до устранения B1–B3.
