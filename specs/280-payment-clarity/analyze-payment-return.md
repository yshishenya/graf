# F280 — анализ согласованности возвращения после оплаты

Дата: 2026-10-03. Scope: только продолжение «результат оплаты и восстановление фоновой сверки». Исторические T001–T028 не переоценивались. Прочитаны spec/plan/tasks/quickstart/payment-journey/research и независимые checklist/review; анализ требований/плана/задач выполнен без изменения их содержимого. Отчет сохранен по прямому заданию основного агента.

## Specification Analysis Report

| ID | Category | Severity | Location | Summary | Recommendation |
|---|---|---|---|---|---|
| — | — | — | Новый срез F280 | Открытых противоречий, неотображенных требований и необоснованных финансовых изменений не обнаружено | Реализация по T029–T032 после canon issue sync |

Исторический HOLD15/2 завершен независимым PASS17/0: непустая session/incoming-current meta заданы в FR-034, новый критерий SC-013 уникален; прежний SC-012 промокода сохранен. Новые T029–T032 сформированы после этого PASS. Повторное чтение checklist:17 checked,0unchecked; автор реализации markers не изменял.

## Coverage Summary

| Requirement Key | Has Task? | Task IDs | Notes |
|---|---|---|---|
| FR-031 достоверный paid/период/service-gap | Да | T029,T031,T032 | Подтвержденные invoice/operation + результат конкретной покупки; grant для subscription purchases, штатный marker для storage; historical paid не зависит от текущей active subscription |
| FR-032 понятное ожидание/secondary continue | Да | T029,T031 | Проверка главная, no-repeat-charge текст; pending/terminal guards |
| FR-033 bounded automatic refresh | Да | T029,T031 | 6attempts/60с/≥10с/15с, oneflight, terminal/error/auth/context/navigation/hidden stop |
| FR-034 context/lifecycle/late/timeout | Да | T029,T031 | Непустые user/workspace/invoice/session, current/incoming meta; без reset/restart; abort не отменяет server |
| FR-035 GET/CSRF/role/finance safeguards | Да | T029,T030,T031,T032 | Existing POST/30за15мин/owner/tenant, stale initial continue, нет новой оплаты/слабого RLS |
| FR-036 JS-off/accessibility/recovery | Да | T029,T031 | Native manual refresh/local GET; keyboard/status/focus/темы/320/1280/200% |
| FR-037 real browser/independent/live boundaries | Да | T029,T030,T031,T032 | ASGI/PostgreSQL Chromium/WebKit, независимые reviews и отдельный live closeout |
| FR-038 causal maintenance reconciliation | Да | T030,T031,T032 | Единственный существующий queue poller в maintenance; fail-fast actual DB role/row_security/superuser/BYPASSRLS; реальные DB роли и отсутствие дубля grant/payment |
| SC-013 шесть сценариев возвращения | Да | T029,T030,T031,T032 | RED до реализации, полноценный путь и release/live evidence |

## Constitution Alignment

Нарушений не обнаружено. RLS и app role processing сохраняются; maintenance — существующая ограниченная роль. GET не подтверждает деньги, return/query не дает доступ, записи/согласия/суммы не переписываются, отдельная сторонняя аналитика не добавляется. Финансовые проверки/idempotency остаются штатными. T011/T012/F278 и отдельные bank/refund/receipt/recurring/human gates не закрываются synthetic evidence. Рабочий scope — high-risk-product / active Spec Kit slice плюс release-deploy.

## Unmapped Tasks

Нет. T029 — result UI/server/controller/browser; T030 — causal worker/DB guards; T031 — независимые reviews/converge; T032 — exact-SHA release/live closeout. T029/T030 используют непересекающиеся согласованные paths, T031 зависит от обоих, T032 — от T031. Tests/RED precede implementation, каждый денежный сценарий имеет negative assertions.

## Metrics

- Total new functional requirements:8; new success criteria:1.
- Total new tasks:4, all unchecked.
- Requirement coverage:100% (8/8 и SC-013).
- Ambiguity count:0; new duplicate ID count:0.
- Open CRITICAL:0; HIGH:0; applicable MEDIUM:0.
- Independent requirements gate at task generation:17/0.

## Next Actions

Root выполняет canon ensure/deduplicated issue sync/canon validate, затем T029/T030 → T031 → T032. Не добавлять issue links наугад. Уточнение projection FR-031 про grant/исторический period конкретизирует уже допущенную достоверность; root передает его независимому reviewer для повторного чтения CHK001, без изменения markers исполнителем. Этот анализ подтверждает согласованность документов, не выполненный код/платеж/выпуск.

Historical tasks prefix до новой секции сохранен byte-for-byte; SHA256 исходного prefix: `3a1fdbc2d1b0d7f1c532bb16e1b7d158811d47a4a22b076c46fdc645e1808756`. `git diff --check` проходит. Enabled Spec Kit hooks до/после tasks/analyze отсутствуют; новых commit hooks не выполнялось.

## Дополнительный анализ T033 после convergence

T033/#7478 добавлен append-only по найденному разрыву FR-038 при передаче существующей очереди. Scope требований прежний; задача реализует strict stop после baseline до forward up и strict recovery barrier до любого восстановления consumer. Покрытие FR-038: T030/T031/T032/T033. Никаких изменений финансовых правил, очереди/истории/идентификаторов, ролей RLS и подписанного приложения.

Independent review UI-R4/R5 выявил и затем подтвердил устранение обеих ветвей. Причинные Bash tests0/23 доказывают отсутствие up при failed stop; общая suite56 PASS. T033 связан с выпуском T032, не заменяет runtime/live proof. Current code/requirements/task alignment: CRITICAL0/HIGH0/applicable MEDIUM0; browser и release evidence ещё отдельные gates. Historical T001–T028 не переотмечены;4 основных новых задачи и1 convergence task.
