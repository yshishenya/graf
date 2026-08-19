# Clarifications: Одна колонка настроек без legacy gutter

### Session 2026-08-19

- Критических неоднозначностей нет: current screenshot, computed grid,
  templates, tests and history all identify the same incomplete migration.
- `settings_mode` remains the authoritative signal that outer cabinet sidebar
  already owns settings navigation.
- Inner navigation remains available only for a real supported fallback without
  outer settings mode; hidden duplicate markup is not a fallback.
- Content aligns to existing main padding in the first workspace column. It is
  not artificially centered around the removed 252px slot.
- Routes, forms, access gates, billing/capture behavior and responsive
  breakpoints remain outside scope.

No formal question was required; all high-impact choices are fixed by the
existing Feature 159 IA contract and the user's one-sidebar requirement.
