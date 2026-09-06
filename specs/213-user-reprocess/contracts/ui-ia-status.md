# Contract: UX, UI, IA and status

## Information architecture

```text
Мои встречи → запись → Ещё → Повторно обработать запись
```

Place the action before deletion. Show it only to the meeting creator when a complete result and eligible source audio exist.

## Confirmation

Title: `Подготовить новую версию?`

Body:

`Имена спикеров, заданные вручную, будут сброшены после успешной обработки.`

Actions:

- `Отмена`;
- `Подготовить`;
- submitting state `Готовим…`, disabled against repeated activation.

No reason field or extra checkbox. Escape and cancel close the dialog and restore focus to the invoking menu item.

## Active replacement and expected waiting

```text
Готовим новую версию
```

The owner's previous outcomes, transcript, speaker controls and player are hidden. No action, stage, timestamp, percentage, countdown or explanatory paragraph is shown. The same state covers normal provider waiting, `result_not_ready`, automatic retry, unknown provider outcome and a temporary status-fetch failure.

The previous complete result remains stored and available to shared recipients and server-side exports until publication succeeds.

Temporary inability to fetch status does not replace the indicator with an error; polling continues automatically.

## Terminal failure

```text
Не удалось подготовить новую версию
Текущая версия не изменилась.
```

The previous outcomes, transcript, manual speaker names and player are visible again. Action: `Попробовать снова`, opening the same confirmation bound to the workflow currently shown by the page.

## Successful publication

Replace the main meeting detail and adjacent player from one server fragment in the same browser turn. Both surfaces use the new processing result and its speaker labels; manual names from the previous result are not copied.

## Transcript published, outcomes pending

```text
Расшифровка и спикеры обновлены
Новые итоги ещё готовятся. Пока показаны итоги по предыдущей версии.
```

Show `По предыдущей версии расшифровки` next to the outcomes heading, not inside generated content.

## Accessibility and responsive behavior

- Reuse the existing accessible menu and dialog behavior.
- Every action is keyboard reachable with visible focus.
- Replacement start, successful publication and terminal failure are announced once through a polite live region.
- Hidden prior content is absent from keyboard and screen-reader navigation.
- `aria-busy` is used only while a request is in flight.
- Color is not the only status signal.
- The responsive server-rendered page works in browser and embedded macOS cabinet; no native Swift control is added.
