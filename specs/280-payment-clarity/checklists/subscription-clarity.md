# F280 — качество требований простого управления подпиской

**Date**: 2026-10-04 · **Story**: US4 · **Lane**: high-risk-product
**Owner**: независимый reviewer; создание оставляет все пункты `[ ]`.
**Scope**: spec FR-039–045/SC-014, plan/research/contract/quickstart продолжения2026-10-04. Это проверка требований, не подтверждение кода, выпуска либо финансовой приемки.

- [x] CHK001 Определены ли обязательные сведения активной карточки и измеримое ограничение одного доминирующего действия? [Clarity, spec FR-039, SC-014]
- [x] CHK002 Различены ли отсутствие карты как нормальное состояние и настоящая причина запрета, без общего ложного предупреждения? [Consistency, spec FR-039/042]
- [x] CHK003 Явно ли сохранены цикл оформления и отсутствие списания/включения продления от GET навигации? [Completeness, spec FR-039/044, contract]
- [x] CHK004 Определены ли для auto on видимые сумма/срок попытки, прямая отмена и правдивые последствия без новых препятствий? [Coverage, spec FR-040]
- [x] CHK005 Заданы ли для resume ready сумма/точный срок/карта, непринятое согласие и сохранение CSRF/version/quote? [Completeness, spec FR-041/044]
- [x] CHK006 Определены ли один уровень дополнительных сведений, полная локальная дата и граница существенных условий перед денежным действием? [Clarity, spec FR-041, contract]
- [x] CHK007 Явно ли запрещены новые/manual/early/resume действия при pending/unknown/unknown_pending/provider_key_expired, включая отсутствие pending amount и незавершенные initial_checkout/storage_upgrade? [Coverage, spec FR-042]
- [x] CHK008 Описаны ли реальные прочие blockers, подготовленное списание, будущий объем и сохранение existing early-preview/contact/error пути? [Coverage, spec FR-041/042, plan/contract]
- [x] CHK009 Правдиво ли разделены effective trial/free/paid/expired и отсутствие известной даты/суммы, без расширения прав участника? [Consistency, spec FR-040/043]
- [x] CHK010 Явно ли ограничены изменения presentation и сохранены денежные/API/DB/JS/provider/idempotency/session/tenant guards, с запретом новых реальных финансовых действий? [Scope, spec FR-044]
- [x] CHK011 Заданы ли keyboard/focus, Chromium/WebKit320/1280, light/dark200% и NoJS без перекрытия/горизонтальной прокрутки? [Measurability, spec FR-012/045, quickstart]
- [x] CHK012 Указаны ли точные official Krisp источники, исторический предел, independent GRAF implementation/assets и причины отклонений? [Traceability, spec FR-045, research]
- [x] CHK013 Измеримы ли сокращение текста≥50% на том же synthetic fixture и границы этой метрики, без гарантии конверсии? [Measurability, spec SC-014]
- [x] CHK014 Заданы ли независимые проверки/converge/exact-SHA выпуск и отдельные SC005/006/T011/T012/F278 без ложной живой приемки? [Completeness, spec SC-014, plan/quickstart]

## Reviewer notes

Первоначальный независимый обзор требований выполнен 2026-10-04: **PASS — 14 отмечено, 0 не отмечено**; исторические основания сохранены в [review-subscription-clarity-requirements.md](../review-subscription-clarity-requirements.md). После уточнения plan/contract/tasks выполнена новая независимая проверка всех CHK001–014: **PASS — 14 отмечено, 0 не отмечено**. Текущие основания, покрытие T046–T048 и SHA-256 проверенных документов: [review-subscription-clarity-requirements-refresh.md](../review-subscription-clarity-requirements-refresh.md). Неподтвержденных критериев качества требований и блокирующих пробелов нет. После записи результата reviewer перечитал checklist и повторно подсчитал отметки.

Это допуск требований FR-039–045/SC-014, а не подтверждение реализации, измеренного сокращения текста, браузерной приемки либо выпуска. T046–T048 уже созданы после первоначального PASS и остаются открытыми; их актуальное покрытие проверено повторно. Поиск счетов всех видов действует и без subscription, использует только локальный набор чтения `CHECKOUT_BLOCKING_STATES | {"provider_key_expired"}` и сохраняет отдельное prepared состояние scheduled renewal без provider_id. `INITIAL_CHECKOUT_OBSERVATION_EXPIRED` намеренно исключен; прежнее разрешение нового оформления и общий денежный набор состояний не меняются. До кода основной агент проверяет актуальные analyze и issue sync. Исторические T011/T012, SC-005/006 и финансовая приемка F278 остаются отдельными и не являются дополнительным условием этого допуска требований. Reviewer изменил только этот checklist и новый отдельный отчет; чужие правки и первоначальный отчет сохранены.
