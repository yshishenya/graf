# Data Model: Цельная геометрия compact rail

Изменение presentation-only. Новые persisted entities, fields, migrations или
state transitions не нужны.

## Compact rail geometry

- `railWidth`: existing 64px token.
- `controlSize`: 40×40px for toggle, navigation and profile.
- `horizontalAxis`: center of rail, 32px from its inline start.
- `iconBox`: existing icon size, centered inside the control.
- `gap`: existing navigation and shell spacing tokens.
- `active`, `hover`, `focus`: visual states sharing the control bounds.

Invariant: every compact control and state background has the same horizontal
center; wide manual and narrow responsive collapse compute the same bounds.

## Existing rail presentation state

- `expanded`: existing `is-rail-pinned` class.
- `collapsed`: absence of `is-rail-pinned` after JS initialization.
- `surface`: standalone or `desktop-embedded`.
- `ready`: existing HTML/rail initialization markers.

Invariant: this feature changes only geometry. State initialization, toggle,
Escape, focus retention and profile-menu behavior remain unchanged.
