# Data Model: Финальная геометрия боковой панели

Постоянной модели данных нет.

| Presentation field | Value | Meaning |
|---|---:|---|
| `compactRailWidth` | 64px | collapsed rail and playback start |
| `expandedRailWidth` | 176px | expanded rail and playback start |
| `railState` | class | existing `is-rail-pinned` transient state |
| `tooltipState` | attribute | existing `data-rail-tooltip` text |

Все поля transient и не покидают текущий shell.
