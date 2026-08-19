# Data Model: Одна колонка настроек без legacy gutter

Presentation-only change. No persisted entity, field, migration or state
transition is introduced.

## Existing presentation state

- `settings_mode=true`: outer cabinet sidebar owns settings navigation.
- `legacy_hidden=true`: existing macro call signal corresponding to that mode.
- fallback: `legacy_hidden=false`, where the inner navigation remains visible.

Invariant: exactly one settings navigation owner is rendered. Content occupies
the first workspace column whenever the outer shell is the owner.
