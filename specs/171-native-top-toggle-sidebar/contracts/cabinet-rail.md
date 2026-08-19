# Cabinet rail contract

## Initialization

- No explicit state: `min-width: 981px` means expanded for both standalone and
  embedded surfaces; smaller surfaces start compact.
- Existing `is-rail-pinned` state wins.
- `data-rail-ready` prevents duplicate handlers.
- No resize listener or cross-session persistence.

## Interaction

- Toggle changes `is-rail-pinned`, `aria-expanded`, `aria-label`, `title`,
  `data-tooltip` and root tooltip copy together.
- Toggle retains focus with `preventScroll: true`.
- Main-content and nav-link clicks do not alter the manual state.
- Escape may collapse the rail and returns focus to the toggle through the
  existing shared path.

## Markup and layout

- Exactly one `[data-cabinet-rail-toggle]` exists in each shell.
- Navigation anchors carry the existing visible label and matching `aria-label`.
- Compact mode uses `var(--app-rail-width)` and hides the workspace header
  itself, not only its text, so there is no empty header band.
- Expanded mode uses the existing `var(--app-sidebar-width)` and keeps profile,
  update/download and navigation controls within the existing column.
