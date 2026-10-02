# Проверочный список требований: промокод на месте F280

**Purpose**: Независимая полнота/ясность требований FR-024–030 и SC-010–012 до реализации.
**Created**: 2026-10-02
**Feature**: [spec.md](../spec.md), [plan.md](../plan.md), [договор](../contracts/payment-journey.md), [quickstart](../quickstart.md).
**Review Ownership**: Состояние отметок принадлежит только независимому reviewer. `[x]` подтверждает качество требований, не реализацию/тест/выпуск. Все новые пункты generated unchecked; прежние checklist marks не заменяют эту проверку.

## Полнота и ясность

- [x] CHK001 Определены ли Apply/Enter/clear+Apply/month/year на месте и отдельно обычные формы без JavaScript, с измеримым запретом полной навигации и новых записей истории? [Completeness, Spec FR-025/029, SC-010]
- [x] CHK002 Различены ли отказ кода и недоступность оплаты целого аккаунта, с понятным следующим действием и без обещания обхода закрытого бюджета? [Clarity, Spec FR-024, Contract §Отказ]
- [x] CHK003 Покрывает ли требование текста все5loader callers и непосредственный final reserve caller, а не только один шаблон, сохраняя прежние финансовые условия? [Coverage, Plan §Архитектура5, Research §public ошибка, SC-012]
- [x] CHK004 Ясно ли, что срок кода300с и срок quote10мин различны, MAX48/подпись/binding неизменны и cycle/GET/start error не продлевают draft? [Consistency, Spec FR-029, Contract §Транспорт, Plan §Сроки]

## Согласия, данные и защита

- [x] CHK005 Достаточно ли определено сохранение обоих режимов через несколько inline errors/correction/remove/cycle при denied sessionStorage, без переноса между user/workspace/session и без нового финансового разрешения? [Completeness, Spec FR-026, Contract §Локальные состояния]
- [x] CHK006 Ясно ли обязательное снятие оферты для новой/недостоверной суммы и граница best effort полной навигации без JavaScript/storage, без противоречия историческому FR-019/020? [Consistency, Spec FR-026/027, Clarifications2026-10-02]
- [x] CHK007 Перечислены ли неизменяемые owner/tenant/session/CSRF/rate limit/catalog/receipt/pending/quote/authority/idempotency проверки и запрет operation/invoice/reservation/provider call от preview? [Completeness, Spec FR-028, Contract §Финансовые границы]
- [x] CHK008 Определены ли запрещенные места хранения/передачи кодов, расчетов, согласий и чувствительных данных и минимальная область временного bool в документе? [Security/Privacy, Spec FR-011/029, Contract §Локальные состояния]

## Ошибки и восстановление

- [x] CHK009 Определены ли одиночный request, busy/input/Apply/cycle/start blocking, конечное ожидание15с и запрет автоматического денежного повтора? [Clarity, Spec FR-027, SC-011]
- [x] CHK010 Охвачены ли delay/stale/detached/request mismatch/unexpected HTML/auth/owner/scope change, с запретом вставки чужого результата и ясным ручным восстановлением? [Coverage, Spec FR-027/028, Plan §Архитектура3]
- [x] CHK011 Определено ли network/timeout/500/429/swapError восстановление без ложного успеха и без активного старого start до успешного нового расчета, с пустой офертой? [Completeness, Spec FR-027, SC-011, Contract §recovery required]
- [x] CHK012 Учтен ли устаревший query cycle после inline switch и reload, без нового history entry/утечки кода или изменения серверного приоритета ссылок? [Edge Case/Consistency, Spec FR-025, Plan §Архитектура4]

## Проверяемость и допуск

- [x] CHK013 Достаточно ли точно определены focus/status/alert/aria-invalid, mouse/Enter/keyboard,320px/200% обе темы и неизменность документа в Chromium/WebKit? [Measurability/Accessibility, Spec FR-030, SC-010]
- [x] CHK014 Требуются ли настоящие browser→ASGI→PostgreSQL traces, отдельный JS-off native путь и RED/GREEN вместо замены их screenshot/fixture/историческим PASS? [Evidence, Spec SC-010–012, Quickstart §Матрица]
- [x] CHK015 Ограничена ли архитектура существующими form/HTMX/template/lifecycle/shared public errors без новых API/миграций/финансовых переходов и с непересекающимся владением? [Scope/Consistency, Plan §Архитектура, Research §Alternatives]
- [x] CHK016 Различены ли reviewer requirements gate, executable tasks/analyze/issue sync, три independent post-code reviews/converge, exact-SHA PR/Full/CD/runtime/publication и отдельная F278/люди/банк/возврат приемка? [Completeness/Traceability, Spec FR-015/SC-012, Plan §Порядок допуска, Quickstart §Выпуск]

## Notes

Generated checked/unchecked:0/16. Это не reviewer verdict. Рецензент перечитывает каждое требование, может изменить только этот checklist и свой review report, оставляет неподтвержденные пункты unchecked с причиной. Код/задачи/другие документы/GitHub он не меняет. Реализация закрыта до независимого PASS и остальных gates. Окончательные tasks создаются после reviewer gate, поэтому первоначальный обзор читает существующий tasks.md и планируемые T026–T028 из plan.md; после генерации окончательных задач проводится новый read-only analyze.

## Независимое ревью требований — 2026-10-02

PASS: checked16 / unchecked0. Все CHK001–CHK016 подтверждены конкретными требованиями и договорами; основания по каждому пункту — `../review-promo-inline-requirements.md`. После записи список перечитан и посчитан заново. Это допуск качества требований, не результат реализации/испытаний/выпуска; окончательные задачи, analyze и issue sync — следующие отдельные ворота.
