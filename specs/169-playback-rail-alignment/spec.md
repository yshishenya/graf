# Feature Specification: Выравнивание нижнего playback относительно rail

**Feature Branch**: `codex/168-cabinet-layout-polish`

**Created**: 2026-08-19

**Status**: Implemented and validated

**Input**: Отдельный successor-срез для нижней панели playback: она должна
начинаться там же, где заканчивается актуальная левая rail.

## User Scenarios & Testing

### User Story 1 - Использовать всю ширину рабочего пространства (Priority: P1)

Пользователь сворачивает или раскрывает левую панель и видит, что нижний
playback bar сразу подстраивается под новую границу без пустого промежутка.

**Independent Test**: Synthetic shell с playback bar открыть в compact и full
rail состояниях на browser и embedded widths; сравнить inline start, grid
column, controls и отсутствие overlap.

**Acceptance Scenarios**:

1. **Given** compact rail, **When** playback доступен, **Then** его left edge
   совпадает с compact rail width.
2. **Given** expanded rail, **When** playback доступен, **Then** его left edge
   совпадает с expanded rail width.
3. **Given** rail toggled twice, **When** playback remains active, **Then** its
   current time, controls and height remain unchanged except for horizontal
   placement.

### Edge Cases

- Standalone narrow shell and embedded narrow shell use the same visible compact
  rail contract.
- Playback unavailable/preparing states preserve the same horizontal alignment.
- Partial update does not leave an old inline offset.

## Requirements

- **FR-001**: Fixed playback MUST use the same compact/expanded inline start as
  the shell grid.
- **FR-002**: Rail transition MUST NOT change playback state, source, current
  time, controls or vertical position.
- **FR-003**: Unavailable and preparing states MUST use the same left offset.
- **FR-004**: The solution MUST reuse existing CSS tokens and MUST NOT add a
  JavaScript resize observer, persistence or new dependency.

## Success Criteria

- **SC-001**: Compact and expanded synthetic layouts match their rail edge in
  100% of checked states.
- **SC-002**: No tested browser/embedded state has a visible horizontal gap or
  overlap at the playback boundary.
- **SC-003**: Focused playback contract confirms the audio state remains stable
  after two rail toggles.

## Assumptions

- Rail widths remain 64px and 176px.
- Initial state and toggle semantics belong to Feature 165/168.

## Out of Scope

- Playback control redesign, audio source changes, timeline height behavior and
  native macOS inspector.
