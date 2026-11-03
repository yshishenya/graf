# Чек-лист качества требований: security и privacy

- [ ] CHK001 Trust boundaries browser/desktop/provider/worker и authority заданы. [FR-005, FR-012, FR-032] Проверка 2026-10-30: B1; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [ ] CHK002 Owner/Admin/Member visibility и multi-workspace isolation непротиворечивы. [FR-003–FR-006] Проверка 2026-10-30: B1; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [x] CHK003 CSRF/session/role recheck и re-auth sensitive actions определены. [FR-005, FR-015–FR-018]
- [x] CHK004 PAN/CVC и provider secret запрещены во всех client/evidence paths. [FR-029, FR-075, FR-077]
- [x] CHK005 Opaque payment method encryption/masking/revocation определены. [FR-037–FR-038]
- [x] CHK006 RLS inventory и same/cross-tenant tests обязательны для каждой новой таблицы. [FR-078, SC-001]
- [x] CHK007 Analytics/replay/log/diagnostic forbidden fields перечислены. [FR-058, FR-071, FR-076–FR-077]
- [x] CHK008 Promo/referral abuse controls не превращают сигналы в единственное доказательство. [FR-061, FR-066–FR-069]
- [ ] CHK009 Audit/correction/four-eyes требования покрывают sensitive operator actions. [FR-056, FR-079] Проверка 2026-10-30: B1; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [x] CHK010 Account close/financial retention/provider boundaries используют правдивую deletion copy. [FR-018–FR-019, FR-080]

Результат: PASS — privacy/security требования трассируются в contracts и launch gates.

## Перепроверка новых trust boundaries 2026-08-06

- [x] CHK011 Storage/add-on/observed-refund/time-credit tables включены в RLS/audit requirements, а product refund-case/execution tables запрещены. [FR-078–FR-079, FR-093–FR-102]
- [ ] CHK012 Refund provider mutation доступна только audited operator; support/browser не может изменить money ledger. [FR-053–FR-056, contract security] Проверка 2026-10-30: X4; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [x] CHK013 Unlimited fair-use/abuse controls отделены от скрытой commercial quota и не снимают capture safety. [FR-024–FR-028, FR-080]

Результат перепроверки: PASS — новые данные и полномочия имеют fail-closed границы.

## Финальная проверка abuse/privacy 2026-08-06

- [x] CHK014 Transient media is non-chargeable, non-playable, short-lived and overdue purge becomes a privacy incident. [FR-106]
- [x] CHK015 Fair-use review cannot be decided by volume/IP/device alone and provides bounded evidence/appeal. [FR-107]
- [ ] CHK016 Post-role-loss/closed-account refund claim route exposes only safe claim facts and no money mutation. [FR-003] Проверка 2026-10-30: X4; см. [отчёт T075](../t075-requirements-review-20261030.md).
- [ ] CHK017 Emergency stop preserves claim intake/refusal/cancel while blocking provider and off-provider execution. [FR-109] Проверка 2026-10-30: X4, X5; см. [отчёт T075](../t075-requirements-review-20261030.md).

Результат финальной проверки: PASS — safety controls do not become hidden billing or deny statutory intake.

## Независимая перепроверка перед T075 — 2026-10-30

Перечитаны все пункты этого списка и относящиеся к ним требования. Исторические результаты выше сохранены; они не являются текущим PASS. Снятые отметки и область каждого расхождения объяснены в [отчёте T075](../t075-requirements-review-20261030.md). Сохранённые `[x]` подтверждают достаточность соответствующей формулировки требований в проверенной области, а не выполнение тестов, выпуск, готовность всей F140 или закрытие issue.
Текущий подсчёт: **11 отмечены / 6 открыты**. Решение по реализации T075: **BLOCK** до устранения B1–B3.

## Повторное ревью проекта импорта T075 — 2026-10-30

CHK001/CHK002/CHK006/CHK007/CHK009/CHK011 применены к реальной роли БД, двум отдельным таблицам, RLS inventory и безопасным метаданным. Доказано качество требований; действительные права PostgreSQL ещё предстоит испытать. Глобальные correction/four-eyes/refund требования и X4–X7 не закрыты.

**PASS только для требований первой части операторского импорта B1–B3** по [новому отчёту](../t075-import-design-review-20261030.md). Предыдущий BLOCK сохраняется как результат прежней версии требований; он снят только для этой ограниченной части после уточнения контракта. Это не глобальный PASS списка, не реализация и не закрытие T075/#4930. Полнота файлов оставляет `financial_status=not_checked`.

Все 17 исходных пунктов перечитаны; глобальные отметки не изменены: **11 отмечены / 6 открыты**. Старые X4–X7 и внешние условия запуска сохраняются отдельно от предметного PASS.
