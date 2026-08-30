# Contract: UX, UI, IA and status

## Information architecture

```text
Мои встречи → запись → Ещё → Повторно обработать запись
```

Place the action before deletion. Show it only to the meeting creator when a complete result and eligible source audio exist.

## Confirmation

Title: `Повторно обработать запись?`

Body:

```text
GRAF заново подготовит расшифровку, спикеров и итоги.
Текущая версия останется доступной, пока новая не будет готова.
Исходная запись не изменится.
```

Actions:

- `Отмена`;
- `Запустить повторную обработку`;
- submitting state `Запускаем…`, disabled against repeated activation.

No reason field or extra checkbox. Escape and cancel close the dialog and restore focus to the invoking menu item.

## Active replacement

```text
Готовим новую версию
Текущая расшифровка и итоги остаются доступными.
Этап: Ожидаем результат обработки
Обновлено: 12:04
```

Action: `Проверить статус`.

## Temporary failure with reliable time

```text
Временная ошибка
GRAF повторит попытку автоматически в 12:10 (через 04:32).
Текущая версия не изменится.
```

Actions: `Повторить сейчас`, `Проверить статус`.

After a server-accepted retry, discard the old countdown generation. The browser timer displays server state and never starts work.

## No reliable retry time

```text
Ждём актуальный статус
Текущая версия остаётся доступной.
```

Action: `Проверить статус`. No exact countdown.

## Terminal failure

```text
Не удалось подготовить новую версию
Текущая расшифровка и итоги не изменились.
```

Action: `Повторно обработать запись`, opening a fresh confirmation bound to the workflow currently shown by the page.

## Transcript published, outcomes pending

```text
Расшифровка и спикеры обновлены
Новые итоги ещё готовятся. Пока показаны итоги по предыдущей версии.
```

Show `По предыдущей версии расшифровки` next to the outcomes heading, not inside generated content.

## Accessibility and responsive behavior

- Reuse the existing accessible menu and dialog behavior.
- Every action is keyboard reachable with visible focus.
- Status transitions are announced once through a polite live region.
- Per-second countdown text is outside the live region.
- `aria-busy` is used only while a request is in flight.
- Color is not the only status signal.
- The responsive server-rendered page works in browser and embedded macOS cabinet; no native Swift control is added.
