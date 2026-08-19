# Data Model: Одна колонка настроек без legacy gutter

Presentation-only change. No persisted entity, field, migration or state
transition is introduced.

## Historical presentation state — superseded by Feature 174

- `settings_mode`: removed after the outer cabinet sidebar became the only
  production navigation owner.
- `legacy_hidden`: superseded by Feature 174 and removed with the unused macro.
- fallback: superseded by Feature 174 after no production consumer was found.

Current invariant: the outer cabinet sidebar is the only settings navigation
owner. Content occupies the first workspace column.
