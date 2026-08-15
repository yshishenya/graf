# UX Checklist: Продуктовый раздел настроек

**Purpose**: Validate completeness of the settings UX requirements.
**Created**: 2026-08-16
**Feature**: [spec.md](../spec.md)

## Visual Hierarchy

- [X] CHK010 Scope is visible before each category description. [Spec §FR-002]
- [X] CHK011 Overview, rail, selected state, dividers and working radii are specified. [Spec §FR-001, UI Contract]

## Accessibility

- [X] CHK012 Active navigation has semantic `aria-current="page"`. [Spec §FR-006]
- [X] CHK013 Keyboard focus, forced-colors compatibility and reduced-motion behavior are explicitly required. [Spec User Story 3]

## Responsive And State Coverage

- [X] CHK014 390px behavior and no document-level horizontal overflow are measurable. [Spec §FR-007, SC-003]
- [X] CHK015 Empty, unavailable, gated, session-expired and no-JavaScript states are described. [Spec Edge Cases]
