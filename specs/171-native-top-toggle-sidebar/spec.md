# Feature Specification: Единый верхний toggle и аккуратный rail

**Feature Branch**: `codex/168-cabinet-layout-polish`

**Created**: 2026-08-19

**Status**: Implemented and validated

**Input**: Регрессия после срезов 165 и 170: native-toggle macOS должен быть
сверху в обоих состояниях, а левое меню должно предсказуемо выглядеть и не
сворачиваться от случайных кликов.

## User Scenarios & Testing

### User Story 1 - Сворачивать native-панель в том же месте (Priority: P1)

Пользователь видит кнопку управления правой native-панелью в верхнем правом
слоте панели. После раскрытия кнопка остаётся в том же месте, поэтому повторный
клик без движения мыши сразу сворачивает панель.

**Why this priority**: Перемещение единственной кнопки между состояниями создаёт
ошибочное ощущение, что панель нужно искать, и мешает быстрому управлению
записью.

**Independent Test**: Computer Use открывает `GRAF Dev`, фиксирует collapsed и
expanded состояния и два последовательных клика по одному координатному слоту;
focused XCTest/source checks подтверждают геометрию и accessibility contract.

**Acceptance Scenarios**:

1. **Given** native inspector collapsed or expanded, **When** it is rendered,
   **Then** exactly one disclosure control is visible in the same top-trailing
   slot with a hit target of at least 44 px.
2. **Given** the inspector is expanded, **When** the user clicks the same
   disclosure control again without moving the pointer, **Then** the inspector
   collapses and the control remains available in that same slot.
3. **Given** the expanded inspector contains long or attention content, **When**
   the content scrolls, **Then** the top control stays fixed and does not cover
   the title, settings action or capture controls.
4. **Given** keyboard focus or VoiceOver, **When** the control is activated,
   **Then** its Russian label, hint, focus state and expanded state describe the
   actual next action in both modes.

### User Story 2 - Получать ясное стартовое и ручное состояние web-меню (Priority: P1)

Пользователь открывает GRAF и на широком экране сразу видит раскрытую левую
навигацию, а на узком — компактный rail с понятным toggle. После ручного
переключения меню остаётся в выбранном состоянии до явного обратного действия;
клики по содержимому или переходы по разделам не должны случайно его закрывать.

**Why this priority**: Левая панель — основная навигация между встречами,
доступом и настройками. Случайное закрытие и пустая полоса вокруг toggle делают
интерфейс похожим на сломанный.

**Independent Test**: Встроенный браузер проверяет standalone shell на 1280 и
900 px, а Computer Use — embedded shell после Reload в широком окне. Проверяются
initial state, два toggle, клик по содержимому, переход по nav, focus/ARIA,
видимые подсказки и отсутствие горизонтального overflow.

**Acceptance Scenarios**:

1. **Given** a fresh wide browser or sufficiently wide embedded surface,
   **When** the shell initializes without explicit state, **Then** the rail is
   expanded and navigation labels are visible.
2. **Given** a narrow browser or embedded surface, **When** the shell initializes,
   **Then** the rail is compact, the toggle remains visible, and the content has
   no horizontal overflow.
3. **Given** the user expands or collapses the rail, **When** they click the
   page content or follow a navigation link, **Then** the manually selected rail
   state is preserved until the user activates the toggle or Escape.
4. **Given** the rail is compact, **When** the user inspects it with keyboard or
   assistive technology, **Then** each navigation action still has an accessible
   name, while visual labels remain hidden without reserving an empty logo slot.
5. **Given** either rail state, **When** the pointer hovers or keyboard focuses
   the toggle, **Then** the tooltip and accessible label state the truthful action
   «Показать боковую панель» or «Скрыть боковую панель».

### Edge Cases

- A reload starts from the responsive default; no new cross-session persistence
  is added and an existing explicit `is-rail-pinned` state still wins.
- A native panel expansion reduces the embedded web viewport; the embedded rail
  may switch to its compact responsive default on the next full initialization,
  but it must not change state during the current page lifetime.
- Long profile names, email addresses, settings labels and the download/update
  action must not create horizontal overflow or overlap the toggle.
- Reduced motion, light/dark theme, high contrast and keyboard focus preserve the
  same action meaning and visible focus treatment.
- HTMX/partial initialization must not add duplicate rail handlers or duplicate
  visible toggles.

## Requirements

### Functional Requirements

- **FR-001**: The native inspector MUST render one disclosure control in a fixed
  top-trailing slot in both collapsed and expanded states.
- **FR-002**: The native top slot MUST reserve enough vertical space for the
  control so the title, settings action, capture controls and attention content
  cannot be covered; the control MUST remain outside the scrolling content.
- **FR-003**: The native control MUST retain a hit target of at least 44 px,
  truthful Russian label and hint, visible hover/focus state, stable identifier
  and reduced-motion behavior.
- **FR-004**: Native inspector expansion/collapse MUST preserve capture status,
  settings action, attention semantics and the two-click same-slot interaction.
- **FR-005**: The shared cabinet rail MUST select its initial expanded/collapsed
  state from the existing surface-aware responsive default and give an explicit
  `is-rail-pinned` state precedence.
- **FR-006**: The embedded default MUST use the same practical wide-surface
  threshold as the standalone cabinet (`min-width: 981px`) so a normal large
  macOS window is not forced into compact mode solely because it is embedded.
- **FR-007**: After initialization, clicks on content and navigation links MUST
  NOT overwrite the user's manual rail state; only the existing toggle or Escape
  may collapse/expand it during that page lifetime.
- **FR-008**: Compact rail navigation links MUST retain accessible names and the
  compact presentation MUST remove the hidden workspace-header slot rather than
  leaving an empty vertical band.
- **FR-009**: The rail MUST keep one toggle per shell, truthful `aria-expanded`,
  title/tooltip copy, focus retention and no horizontal overflow in supported
  wide/narrow, embedded and keyboard states.
- **FR-010**: The change MUST NOT add storage, router, analytics, dependency,
  capture, auth, meeting-content, permission or release-packaging behavior.

### Key Entities

- **Native inspector disclosure slot**: The fixed top-trailing interaction area
  shared by the collapsed and expanded native panel states.
- **Cabinet rail state**: Ephemeral `expanded`/`collapsed` presentation state for
  one page lifetime, governed by explicit state, responsive default and manual
  toggle actions.
- **Cabinet navigation item**: An existing meeting, shared-content or settings
  link that must remain visually compactable and accessible by name.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Computer Use confirms the native disclosure control has the same
  top-right position in collapsed and expanded `GRAF Dev` states, and two clicks
  return to the original state without pointer repositioning.
- **SC-002**: Focused native source/XCTest checks confirm one control per mode,
  fixed top slot, no overlap reservation, truthful labels/hints and a 44 px
  target.
- **SC-003**: The browser/embedded responsive matrix passes at wide and narrow
  widths with the expected default in 100% of synthetic cases and no horizontal
  overflow.
- **SC-004**: In 100% of focused interaction cases, a manual rail state survives
  a content click, navigation click, two toggles, keyboard activation and a
  non-reinitializing resize without duplicate handlers.
- **SC-005**: Compact rail screenshots and accessibility snapshots show no empty
  workspace-header band and no unnamed navigation links.

## Assumptions

- The existing SwiftUI disclosure control, cabinet rail state class and
  `railReady` idempotency guard remain the implementation owners.
- `981px` is the smallest supported wide cabinet surface; it is reused for the
  embedded default because the current `1121px` embedded threshold puts a
  normal large `GRAF Dev` window into compact mode.
- Rail state remains ephemeral for the current page lifetime; persistence is not
  requested.
- Visual evidence is metadata-only and must not contain real transcript/audio,
  credentials or private meeting content.

## Out of Scope

- Native capture, permissions, audio routing, settings content or packaging.
- Meeting list/detail content, playback, summaries, auth and production deploy.
- A new sidebar state architecture, persistent preference, analytics or router.
- Redesign of profile actions, download destination or search behavior beyond
  preventing rail-related overlap/overflow.
