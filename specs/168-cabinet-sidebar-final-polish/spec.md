# Feature Specification: Финальная геометрия боковой панели кабинета

**Feature Branch**: `codex/168-cabinet-layout-polish`

**Created**: 2026-08-19

**Status**: Implemented and validated

**Input**: Пользовательская регрессия: левое меню должно выглядеть одинаково
понятно в раскрытом и компактном состоянии, а нижний playback не должен
оставлять рядом с ним пустую полосу.

## User Scenarios & Testing

### User Story 1 - Понимать состояние левого меню (Priority: P1)

Пользователь открывает кабинет на широком экране и видит обычную навигацию с
подписями. На узком экране видит компактный rail и понятную кнопку раскрытия.
После ручного изменения состояния меню layout остаётся согласованным с нижним
playback bar.

**Why this priority**: Основная навигация должна выглядеть частью единого
рабочего пространства, а не отдельным слоем с ошибочным default state.

**Independent Test**: Synthetic browser/embedded shell проверить в expanded и
collapsed состояниях, включая первый paint, два последовательных toggle,
keyboard focus, tooltip и нижний playback bar.

**Acceptance Scenarios**:

1. **Given** rail раскрыт, **When** пользователь смотрит на кабинет, **Then**
   подписи навигации и нижний playback начинаются от одной границы панели.
2. **Given** rail свернут, **When** пользователь смотрит на кабинет, **Then**
   компактный rail остаётся видимым, playback начинается сразу после его
   ширины, а пустой полосы между ними нет.
3. **Given** пользователь наводит курсор или переводит focus на toggle, **Then**
   подсказка на русском объясняет действие и не перекрывает основное меню.
4. **Given** пользователь меняет состояние rail, **Then** ширина shell,
   доступный label, `aria-expanded`, icon и playback alignment меняются
   согласованно.

### Edge Cases

- Узкий standalone и embedded viewport не получают горизонтальный overflow.
- Состояние, выбранное пользователем, не перезаписывается resize automation в
  течение жизни страницы.
- Partial/HTMX initialization не добавляет второй toggle handler.
- Reduced motion, keyboard focus и forced colors сохраняют различимый control.

## Requirements

### Functional Requirements

- **FR-001**: Expanded и collapsed rail MUST использовать одну геометрическую
  модель ширины для shell и fixed playback bar.
- **FR-002**: Compact rail MUST занимать только `--app-rail-width`, expanded rail
  MUST занимать `--app-sidebar-width`; main content MUST начинаться сразу после
  актуального rail.
- **FR-003**: Toggle MUST оставаться одним видимым top control с truthful
  Russian label, title, tooltip, icon, focus и `aria-expanded`.
- **FR-004**: Collapse/expand MUST NOT добавлять resize listener, persistence,
  analytics, auth changes или meeting-content changes.
- **FR-005**: Поведение MUST быть одинаковым в browser и embedded shell при
  breakpoint defaults из Feature 165.

## Success Criteria

- **SC-001**: В 100% synthetic expanded/collapsed states playback bar имеет
  inline start ровно 64px или 176px соответственно и не показывает gap.
- **SC-002**: Browser/embedded boundary matrix не имеет горизонтального overflow.
- **SC-003**: Два последовательных pointer/keyboard toggle оставляют focus,
  label, icon и `aria-expanded` синхронными.
- **SC-004**: Визуальная проверка wide/narrow shell проходит без overlap tooltip,
  nav labels или playback controls.

## Assumptions

- Breakpoints и initial state принадлежат Feature 165; 168 исправляет только
  финальную геометрию и визуальную continuity.
- Ширины 64px и 176px — существующие CSS tokens.
- Персональное состояние rail между сессиями не сохраняется.

## Out of Scope

- Новый navigation IA, profile menu, settings routes, auth, capture и release.
- Переписывание toggle tooltip или добавление onboarding.
