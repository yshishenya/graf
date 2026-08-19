# Clarifications: Одна колонка настроек без legacy gutter

> **Superseded by Feature 174:** полный caller trace подтвердил, что standalone
> inner navigation не имеет production-потребителей. Macro, `settings_mode` и
> fallback удалены; outer cabinet sidebar теперь единственный владелец навигации.

### Session 2026-08-19

- Критических неоднозначностей нет: current screenshot, computed grid,
  templates, tests and history all identify the same incomplete migration.
- `settings_mode` и inner-navigation fallback были временной границей Feature
  173 и удалены Feature 174 после полного caller trace.
- Content aligns to existing main padding in the first workspace column. It is
  not artificially centered around the removed 252px slot.
- Routes, forms, access gates, billing/capture behavior and responsive
  breakpoints remain outside scope.

No formal question was required; all high-impact choices are fixed by the
existing Feature 159 IA contract and the user's one-sidebar requirement.
