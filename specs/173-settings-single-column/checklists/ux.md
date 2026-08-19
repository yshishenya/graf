# UX Requirements Checklist: Одна колонка настроек без legacy gutter

**Purpose**: Validate clarity and completeness of navigation/layout requirements
**Created**: 2026-08-19
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Is one navigation owner explicitly required for settings mode? [Completeness, Spec §FR-001]
- [x] CHK002 Are overview, form, calendar and billing surfaces included? [Coverage, Spec §FR-002]
- [x] CHK003 Is the supported fallback navigation explicitly preserved? [Edge Case, Spec §FR-005]
- [x] CHK004 Are wide, narrow, web and embedded surfaces named? [Coverage, Spec §FR-006]

## Clarity And Measurability

- [x] CHK005 Is the unwanted offset quantified as 220px + 32px? [Clarity, Spec §SC-002]
- [x] CHK006 Is the desired content origin defined by existing main padding rather than a vague visual judgment? [Measurability, Spec §FR-003]
- [x] CHK007 Are navigation landmark count and grid-column outcomes measurable? [Acceptance Criteria, Spec §SC-001–SC-003]

## Consistency And Accessibility

- [x] CHK008 Are the single-rail requirements consistent with Feature 159 ownership? [Consistency, Spec §Assumptions]
- [x] CHK009 Are focus order, accessible names and overflow requirements defined? [Coverage, Spec §FR-006]
- [x] CHK010 Are auth, CSRF, role, billing and capture boundaries preserved? [Dependency, Spec §FR-004]

## Scope Boundaries

- [x] CHK011 Is visual redesign excluded while content width and styles remain stable? [Scope, Spec §Out of Scope]
- [x] CHK012 Are new JS state, storage, routing and breakpoints explicitly excluded? [Scope, Spec §FR-007]

## Notes

- Standard depth for author and PR reviewer. All 12 requirement-quality checks
  pass before task generation.
