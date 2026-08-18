# Data Model: Понятный toggle боковой панели

Новых persistent entities, migrations и API contracts не требуется.

## Presentation state

| Поле | Источник | Инвариант |
|---|---|---|
| `rail_pinned` | существующий DOM class `is-rail-pinned` | Следующее действие label/icon/tooltip обратны текущему состоянию. |
| `aria_expanded` | существующий toggle attribute | Равно `true` только при expanded rail. |
| `tooltip_text` | существующий action label | Совпадает с accessible name и виден на hover/focus. |

## Validation rules

- Один shell содержит один toggle и один initializer.
- Tooltip не содержит interactive descendants и не меняет route.
- State is ephemeral; persistence и viewport default не входят в Feature 164.

