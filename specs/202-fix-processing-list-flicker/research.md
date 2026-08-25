# Research: Стабильное обновление processing-строк

## Подтверждённый механизм дефекта

- Submitted/processing включает `hx-trigger="every 1s"` с `outerHTML` target на
  весь `#meeting-list-region`.
- Каждый swap удаляет client projection, сбрасывает request state и запускает
  projection заново через `afterSwap -> initCabinet`.
- Projection выбирает не только processing, но и failed/readiness строки и при
  отсутствии узла динамически добавляет readiness DOM.
- Поэтому одна и та же строка поочерёдно показывает server и client state, а
  высота/содержимое соседних строк периодически перестраиваются.

## Decision: Сервер владеет структурой и terminal truth

Server-rendered list остаётся canonical для состава, порядка, status kind и
terminal результата. Клиентская projection допустима только для уже отмеченной
сервером processing-строки и только как промежуточный readiness text.

## Decision: Processing не требует full-list poll

Официальный HTMX contract означает, что `outerHTML` заменяет target целиком;
повторять такой swap ради одной строки избыточно. Существующий content-safe API
и 15-second throttle позволяют обновлять active row без нового endpoint или
OOB protocol. Источники: https://htmx.org/docs/#polling,
https://htmx.org/attributes/hx-swap/ и
https://htmx.org/examples/update-other-content/.

## Decision: Progress swap сохраняет processing projection

Upload progress и playback preparing по-прежнему требуют серверного списка для
порядка, фильтров и исчезновения строк. В смешанном списке последний bounded
non-terminal projection snapshot восстанавливается на совпавшей processing-
строке сразу после swap; authoritative запросы и исчезновение processing-строки
очищают snapshot. Throttle остаётся 15-секундным.

## Decision: Один refresh на terminal transition

`processed`, `blocked`, `failed_terminal` и `canceled` означают смену
структурного/terminal представления. Клиент не синтезирует его, а вызывает
существующий list form refresh, который уже сохраняет фильтры, selection/focus,
auth fencing и stale request generation.

## Alternatives considered

- **Оставить full swap и добавить ещё один guard**: отклонено — identity guard
  уже исправлен, но не устраняет повторное удаление/создание DOM.
- **HTMX OOB или row-targeted endpoint**: технически корректно, но добавляет
  новый server contract и второй fragment path без необходимости.
- **Полностью server-side polling**: потребовал бы либо тот же full swap, либо
  новый row endpoint; существующая content-safe projection уже решает задачу.
- **Projection для failed/readiness строк**: отклонено — создаёт два источника
  истины и воспроизводит production contradiction.
