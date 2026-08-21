# Calendar settings UI contract

## IA

`Настройки → Интеграции → Календари` and the embedded equivalent use the
existing GRAF settings shell. The DOM and visual order is: source summary,
connected source cards, display/reminder preferences, available provider add,
advanced preview, read-only/privacy and degraded-support details. Unavailable
providers are disclosed separately and have no connect action.

`/meetings` and `/desktop/meetings` render an initially expanded, compact
`Ближайшие встречи` section before meeting history. It uses the same selected
calendar/event projection, title/time preferences and tenant scope as settings;
it does not call providers, persist data or expose raw meeting URLs.

## Mutation states

Each connect/sync/selection/preferences/disconnect form has:

```text
idle -> submitting/running -> succeeded | failed | action_required
```

During `submitting/running`: initiating control is disabled, has visible busy
copy and `aria-busy=true` on the status region; duplicate submit is prevented;
native POST works without JavaScript. On completion, focus goes to the result
region or source card; after PRG reload the same result remains visible.

## Copy rules (Russian)

| State | Required copy intent |
|---|---|
| connecting | `Подключаем…` / `Проверяем доступ…` |
| cataloging | `Получаем список календарей…` |
| success | `Календарь подключен. Теперь выберите конкретные календари.` |
| selection empty | `Источник подключен, но календари не выбраны.` |
| sync accepted | `Синхронизация поставлена в очередь.` |
| syncing | `Синхронизация выполняется…` |
| stale | `Данные устарели. Попробуйте синхронизировать или переподключить.` |
| provider failure | `Не удалось получить данные. Технические детали скрыты.` |
| reconnect | `Нужно обновить доступ.` |
| disconnect success | `Календарь отключён от GRAF.` |
| manual boundary | `Ручные Record/Stop доступны независимо от календаря.` |

Copy must not promise deletion outside GRAF control or imply automatic
recording/meeting participation.

## Accessibility

- Provider buttons use `aria-haspopup=dialog` and `aria-controls`.
- Dialog has labeled heading, form labels, error association and focus return.
- Status/result uses `role=status`, `aria-live=polite`; destructive errors use
  an assertive region only when necessary.
- Disabled controls remain readable and have a text status, not color only.
- Unavailable providers are readable non-actions, not disabled buttons that
  disappear from keyboard/screen-reader explanation.
- Checkboxes expose selected/unavailable/private state without relying on color.
- Keyboard can reach add, select, save/cancel, sync and disconnect in logical
  order; narrow viewport does not hide the primary action.

## Browser/embedded parity

Same source IDs/state/result and API/service contract; only base route, shell
navigation and desktop session bridge differ. Native macOS Record/Stop remains
outside the embedded web content and must stay reachable during any web error.
