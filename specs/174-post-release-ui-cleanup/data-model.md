# Data Model: Пострелизная очистка интерфейса

Изменение presentation-only. Новые persisted entities, поля, migrations или runtime state transitions не нужны.

## Sidebar presentation state

- `surface`: standalone web или embedded cabinet.
- `ready`: shell initialization завершена.
- `expanded`: существующий pinned state.
- `width`: 64px compact или 176px expanded.
- `control`: toggle, navigation, optional update/download или profile.
- `visibleBox`: rendered width/height и computed display/visibility/opacity.

Invariant: compact controls имеют видимую цель 40×40px и общий центр; profile не исчезает ни на одном поддерживаемом breakpoint.

## Settings navigation ownership

- `owner`: outer cabinet sidebar — единственное допустимое значение production.
- `contentMode`: full page или content-only HTMX fragment.
- `activeSection`: существующая settings category.

Invariant: navigation model остаётся доступен outer shell, но content templates не создают второго landmark или зарезервированной колонки.

## Native inspector presentation

- `expanded`: существующее пользовательское состояние.
- `width`: 52px compact или 308px expanded.
- `togglePosition`: top trailing slot с существующими inset values.
- `accessibleLabel`: показать или скрыть панель управления.

Invariant: удаление layout wrapper не меняет размеры, position, hit target, focus/help или action semantics.
