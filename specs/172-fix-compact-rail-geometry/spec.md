# Feature Specification: Цельная геометрия compact rail

**Feature Branch**: `codex/172-fix-compact-rail-geometry`

**Created**: 2026-08-19

**Status**: Ready for clarification

**Input**: Регрессия compact left rail: toggle, navigation, active state и
профиль смещены относительно друг друга; требуется восстановить простую
исторически цельную модель без новых конструкций.

## User Scenarios & Testing

### User Story 1 - Видеть ровную компактную навигацию (Priority: P1)

Пользователь сворачивает левую панель и видит аккуратный rail: верхний toggle,
все навигационные иконки, их hover/active/focus states и профиль лежат на одной
вертикальной оси. Выделенный пункт выглядит компактной кнопкой, а не широкой
смещённой плашкой.

**Why this priority**: Compact rail — постоянная основная навигация. Нарушенная
геометрия делает весь интерфейс визуально сломанным и затрудняет понимание
активного раздела.

**Independent Test**: На широком и узком окне свернуть панель, сравнить центры и
границы toggle, каждого navigation item и profile; затем проверить hover,
keyboard focus и active state.

**Acceptance Scenarios**:

1. **Given** панель свёрнута, **When** пользователь смотрит на rail, **Then**
   центры toggle, navigation icons и profile совпадают с центром rail без
   заметного горизонтального смещения.
2. **Given** один navigation item активен, **When** rail свёрнут, **Then** его
   фон имеет ту же компактную квадратную геометрию, что hover/focus targets
   соседних действий, и иконка находится в центре фона.
3. **Given** пользователь меняет ширину окна или раскрывает и снова сворачивает
   панель, **When** compact state возвращается, **Then** геометрия не меняется
   между responsive-состояниями.
4. **Given** пользователь работает клавиатурой, **When** focus проходит по rail,
   **Then** focus ring не обрезается, элементы не перекрываются и доступные имена
   сохраняются.

### Edge Cases

- Широкое окно, где compact state выбран вручную, не должно наследовать
  неполную геометрию только из узкого media-режима.
- Embedded macOS titlebar и traffic lights не меняют ось web rail; контент
  начинается ниже системной области и не перекрывается с ней.
- Длинные имя и email скрыты в compact state и не расширяют rail; profile menu
  продолжает открываться за пределами rail без обрезания.
- Отсутствие download/update action не меняет позицию navigation или profile.
- Инициализация и partial updates не создают второй toggle или дополнительный
  пустой workspace-header slot.

## Requirements

### Functional Requirements

- **FR-001**: Compact rail MUST использовать одну общую вертикальную ось для
  toggle, navigation icons и profile action.
- **FR-002**: Compact navigation hover, active и focus backgrounds MUST иметь
  одинаковую квадратную геометрию и MUST быть центрированы в rail.
- **FR-003**: Compact toggle, navigation targets и profile action MUST
  использовать один согласованный размер интерактивной области.
- **FR-004**: Одинаковая compact-геометрия MUST сохраняться в standalone web и
  embedded macOS surface, на широком ручном и узком responsive состоянии.
- **FR-005**: Compact rail MUST NOT резервировать скрытый workspace-header slot
  или создавать лишний вертикальный разрыв между toggle и navigation.
- **FR-006**: Expanded sidebar MUST сохранить текущую ширину, тексты, profile,
  download/update actions и существующую модель раскрытия/сворачивания.
- **FR-007**: Toggle MUST остаться сверху и в том же экранном слоте между
  expanded и collapsed состояниями; второй клик без движения указателя MUST
  выполнять обратное действие.
- **FR-008**: Исправление MUST сохранить доступные имена, keyboard operation,
  видимый focus, profile menu behavior и отсутствие horizontal overflow.
- **FR-009**: Исправление MUST NOT добавлять новое состояние, JavaScript,
  хранилище, router, dependency или отдельную систему responsive layout.

## Success Criteria

### Measurable Outcomes

- **SC-001**: В 100% проверенных compact-состояний горизонтальные центры toggle,
  navigation icons, active backgrounds и profile совпадают с центром rail с
  погрешностью не более 1 px.
- **SC-002**: В 100% проверенных wide/narrow и web/embedded состояний compact
  controls имеют одинаковую квадратную область 40×40 px и не перекрываются.
- **SC-003**: После двух последовательных переключений панель возвращается к
  исходному состоянию, а toggle остаётся в том же слоте без перемещения
  указателя.
- **SC-004**: Keyboard и accessibility проверка подтверждает доступное имя и
  необрезанный focus ring у каждого compact action.
- **SC-005**: В compact state отсутствует пустой workspace-header slot, а
  expanded state визуально и функционально не регрессирует.

## Assumptions

- Сохраняются текущие product tokens: compact rail 64 px и expanded sidebar
  176 px.
- Историческая модель `99479bcc` / `9a93a5cc` используется как принцип: одна
  замкнутая геометрия, а не как полный откат старого UI.
- Текущие JS state semantics и Jinja markup корректны; regression находится в
  CSS cascade.

## Out of Scope

- Редизайн иконок, цветов, sidebar information architecture или profile menu.
- Изменение responsive breakpoint, persistence или rail state logic.
- Native inspector, playback, capture, auth, permissions, release и deploy.
