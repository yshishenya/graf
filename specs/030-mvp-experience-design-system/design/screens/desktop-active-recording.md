# Desktop Active Recording

## Purpose

Make active capture impossible to miss and one action away from stop.

## Frame And Pinning

- Same window structure as Desktop Home.
- Capture strip expands to `96 px`.
- Capture strip remains pinned above every embedded route.
- Popovers, modals, and embedded product UI cannot cover the `Остановить`
  button.

## Native Strip Content

Left:

- Red recording dot.
- Label: `Запись идёт`.
- Elapsed timer.
- Capture source: `Звук системы + микрофон`.
- Local buffer state: `Сохраняем на этом Mac`, `Мало места`, or
  `Готовим файл`.

Center:

- Live `Микрофон` and `Система` meters.
- Track truth labels: `Дорожка микрофона` and `Дорожка системы`.
- Optional warning row if one track is silent or degraded.

Right:

- Destructive `Остановить` button, `40 px`, minimum `128 px`.
- Secondary `Отметить момент`.
- Overflow button for `Диагностика`.

## Embedded Cabinet During Recording

- User may browse meetings or open upload/status sheets, but active strip stays
  visible.
- Embedded pages may show a read-only banner: `Запись идёт на этом Mac`.
- Embedded pages cannot start, stop, pause, or hide recording.

## Required States

- Active normal.
- Active with system track silent.
- Active with microphone track silent.
- Active while sync is unavailable.
- Active with low disk/buffer warning.
- `Остановить` clicked and local save preparing.
- The stop action failed or degraded, with retry/recovery entry.

## Local stop action behavior

- Single click initiates stop.
- `Остановить` button changes to busy state only after action begins.
- After stop, route goes to local saved/upload queue state.
- Copy must say `Сохраняем на этом Mac` before upload truth exists.

## Forbidden

- No `Свернуть` action if it hides the active indicator.
- No full-screen alarm styling; use red as semantic accent.
- No embedded product UI-controlled capture state.

## Acceptance Evidence

Covered by Figma `V8 05 - Активная запись в меню и окне`,
`V8 06 - Загрузка и обработка в списке`, `V8 14 - Правила интерфейса и QA`, and
`design/validation-evidence.md`.
