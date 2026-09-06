# Research: Системная компоновка playback-панели

## Decision 1: playback — отдельная строка shell grid

**Decision**: Сделать playback прямым дочерним элементом `.app-shell` в content-column и выделить ему `auto`-строку; sidebar занимает обе строки, main занимает верхнюю `minmax(0, 1fr)` строку.

**Rationale**: Scrollbar принадлежит main-cell и физически не может проходить через sibling playback-cell. Границы панели автоматически совпадают с content-column при любом состоянии rail.

**Alternatives considered**:

- `right: scrollbar-width` или дополнительный padding — зависит от платформы и маскирует root cause.
- `position: sticky` внутри main — нижний sticky элемент в конце потока не гарантирует постоянную видимость до прокрутки к нему.
- JavaScript geometry sync — создаёт второй источник истины и race при resize/rail toggle.

## Decision 2: удалить clearance observer

**Decision**: Удалить динамический `--playback-clearance` и `ResizeObserver` из playback initialization.

**Rationale**: Grid-row резервирует точную фактическую высоту панели, включая resize speaker timeline; ручной bottom padding больше не нужен.

**Alternatives considered**:

- Сохранить observer «на всякий случай» — лишняя работа и риск двойного зазора.

## Decision 3: тестировать наблюдаемую геометрию

**Decision**: Совместить статический contract (структура и отсутствие overlay primitives) с runtime computed geometry на реальном shell.

**Rationale**: Text assertions ловят возврат архитектурного anti-pattern, а browser measurements подтверждают пользовательский результат на responsive states.

**Alternatives considered**:

- Screenshot-only проверка — менее детерминирована и хуже локализует регрессию.
- Новая frontend test dependency — не нужна; существующих pytest/Node/browser средств достаточно.
