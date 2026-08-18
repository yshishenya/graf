# Feature Specification: Закреплённый верхний блок встречи

**Feature Branch**: `codex/161-graf-ux-regressions`

**Created**: 2026-08-18

**Status**: Ready for implementation

**Input**: Отзыв пользователя по задаче 4: при прокрутке встречи должна
оставаться закреплённой вся верхняя часть с названием, метаданными, действиями
и вкладками «Итоги / Расшифровка».

## User Scenarios & Testing

### User Story 1 - Не терять контекст встречи (Priority: P1)

Пользователь прокручивает длинную расшифровку или итоги и в любой момент видит
название встречи, дату/статус, доступные действия и переключатель вкладок.

**Why this priority**: Без контекста пользователь может оказаться в другой
встрече визуально и теряет быстрый путь к итогам.

**Independent Test**: В synthetic meeting detail с длинным transcript и
outcomes прокрутить main container до нескольких позиций и проверить, что
единый верхний блок остаётся на верхней границе scroll container, не
перекрывает контент и сохраняет tab keyboard contract.

**Acceptance Scenarios**:

1. **Given** открыта встреча с длинным контентом, **When** пользователь
   прокручивает main container, **Then** title, date/status, top actions и
   tabs остаются в одном закреплённом блоке.
2. **Given** пользователь переключает «Итоги» или «Расшифровка», **When**
   верхний блок закреплён, **Then** selected state и focus semantics tabs
   сохраняются, а контент не уходит под sticky background.
3. **Given** narrow viewport или embedded shell, **When** title/actions
   переносятся на несколько строк, **Then** весь блок остаётся читаемым,
   controls доступны, horizontal overflow отсутствует.
4. **Given** пользователь переходит к transcript turn или outcome source,
   **When** браузер прокручивает к цели, **Then** цель не скрывается под
   закреплённым блоком.

### Edge Cases

- Длинное название и несколько top actions не должны вызывать overlap.
- Partial/HTMX render не должен создавать второй sticky wrapper или второй
  tablist.
- Страница с unavailable playback сохраняет тот же header contract.
- Reduced-motion и light/dark themes не меняют порядок или доступность блока.

## Requirements

### Functional Requirements

- **FR-001**: Meeting detail MUST render one semantic sticky wrapper around the
  topline, share host and content tabs.
- **FR-002**: Wrapper MUST be sticky relative to the existing main scroll
  container and MUST keep title, metadata, actions and tabs visually connected.
- **FR-003**: The tabs MUST no longer implement a competing independent sticky
  layer; they MUST remain one tablist inside the wrapper.
- **FR-004**: Sticky background MUST fully cover the content passing behind it,
  preserve readable contrast and keep focus indicators visible, including the
  existing main-container top padding at the scrollport edge.
- **FR-005**: Transcript/outcome programmatic scrolling MUST reserve enough
  scroll margin for the responsive header so a target is not obscured.
- **FR-006**: Browser and embedded meeting detail MUST use the same structure;
  existing actions, tab state, playback, auth and deletion semantics MUST NOT
  change.
- **FR-007**: The wrapper MUST remain usable at wide and narrow widths,
  support keyboard tabs, reduced motion and both supported color schemes.
- **FR-008**: The change MUST add no new router, persistence, observer service
  or dependency unless the existing CSS contract cannot meet the requirement.

### Key Entities

- **Meeting detail header**: presentation group containing the meeting context
  and tabs; it has no persistent state.
- **Content tablist**: existing two-tab contract for outcomes and transcript.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Synthetic wide and narrow scroll matrix finds one sticky header,
  one tablist and no independent sticky tabs after repeated initialization.
- **SC-002**: At every tested scroll position, title and tabs remain visible,
  with no overlap or horizontal overflow.
- **SC-003**: Programmatic transcript/outcome jumps leave the target visible
  below the header in 100% of synthetic cases.
- **SC-004**: Existing tab keyboard, ARIA and active-panel assertions remain
  green; no playback or auth behavior changes.

## Assumptions

- `.main` is the authoritative scroll container for meeting detail.
- A CSS sticky wrapper with responsive scroll-margin is sufficient; no client
  header state is needed.
- Screenshot red-box feedback defines the scope: title/meta/actions plus the
  tabs, not the playback bar or summary generation controls.

## Out of Scope

- Summary generation, prompts, formats or outcome quality.
- Native macOS toolbar navigation.
- Redesign of action buttons, tab labels or meeting metadata.
