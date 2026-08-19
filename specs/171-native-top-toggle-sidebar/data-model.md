# Data Model: Единый верхний toggle и аккуратный rail

Изменяемые сущности — presentation-only; новые записи, поля хранения и
миграции не нужны.

## Native inspector disclosure slot

- `mode`: `collapsed` or `expanded`.
- `topInset`: existing 10px visual inset.
- `trailingInset`: existing 4px visual inset.
- `hitTarget`: existing 44px minimum.
- `actionLabel`: «Показать панель управления» or «Скрыть панель управления».
- `accessibilityHint`: matching expand/collapse action.

Invariant: both modes render one button at the same top-trailing coordinate;
expanded scrolling content begins after the slot.

## Cabinet rail state

- `surface`: standalone browser or `desktop-embedded`.
- `explicitPinned`: server-rendered `is-rail-pinned` presence.
- `responsiveDefault`: expanded at `min-width: 981px`, compact below it.
- `manualState`: ephemeral class `is-rail-pinned` after toggle.
- `ready`: `data-rail-ready` idempotency guard.

Invariant: explicit state wins during initialization; manual state is not
overwritten by content clicks or resize during the current page lifetime.

## Navigation item

- `id`, `href`, `label`, `icon`, `active` — existing server-rendered values.
- `ariaLabel`: same user-facing `label` when visual compact CSS hides the text.

Invariant: every visible or compact navigation action remains named and points
to the existing first-party route.
