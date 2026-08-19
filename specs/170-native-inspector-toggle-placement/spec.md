# Feature Specification: Нижний toggle native панели управления

**Feature Branch**: `codex/168-cabinet-layout-polish`

**Created**: 2026-08-19

**Status**: Superseded by Feature 171 after user validation

**Input**: В macOS-приложении кнопка native right panel сейчас находится сверху
в раскрытом состоянии и снизу в компактном. Обе кнопки должны быть снизу.

## User Scenarios & Testing

### User Story 1 - Сворачивать native panel без поиска кнопки (Priority: P1)

Пользователь раскрывает native панель управления, видит toggle в нижнем правом
углу и может сразу нажать ту же кнопку ещё раз, не двигая мышь в другое место.

**Independent Test**: Computer Use visual review of collapsed and expanded
native shell, plus XCTest/source accessibility checks for footer placement,
trailing alignment and labels.

**Acceptance Scenarios**:

1. **Given** native inspector collapsed, **Then** its disclosure control is in a
   fixed bottom footer with at least a 44px target.
2. **Given** native inspector expanded, **Then** the same disclosure control is
   in a fixed bottom footer, aligned to the trailing edge of the shell so the
   pointer does not need a compensating move after expansion.
3. **Given** keyboard focus or VoiceOver, **Then** the control exposes truthful
   Russian label, hint, identifier and visible focus/hover state in both modes.
4. **Given** actionable capture attention, **When** the user collapses the panel,
   **Then** the existing attention semantics remain unchanged and the bottom
   control remains available.

### Edge Cases

- Long inspector content scrolls independently while footer toggle remains
  visible.
- Reduced motion does not remove the control or its focus state.
- Compact and expanded widths preserve the existing 52px/308px contract.

## Requirements

- **FR-001**: Both compact and expanded native inspector states MUST place the
  disclosure control in a non-scrolling bottom footer.
- **FR-002**: Expanded footer control MUST be trailing-aligned with the compact
  control so its absolute horizontal position remains stable across collapse.
- **FR-003**: The control MUST retain at least a 44px hit target, labels,
  accessibility hint and identifier in both states.
- **FR-004**: Moving the control MUST NOT change capture controls, attention
  expansion semantics, settings action or web cabinet ownership.

## Success Criteria

- **SC-001**: Computer Use confirms both modes show the only disclosure control
  at the bottom of the native rail.
- **SC-002**: XCTest/source contract confirms 44px target, fixed footer and
  trailing alignment.
- **SC-003**: Two consecutive toggle actions preserve expanded/collapsed state,
  focus semantics and existing capture status.

## Assumptions

- The native inspector remains the right-hand shell surface.
- The existing `InspectorDisclosureButton` is reused; no new component is needed.

## Out of Scope

- Native panel content redesign, capture flow, permissions, web rail and
  production packaging.
