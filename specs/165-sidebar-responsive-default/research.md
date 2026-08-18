# Research: Адаптивное стартовое состояние боковой панели

## Decision: reuse the existing CSS breakpoints

The shared stylesheet already expresses the product behavior that the shell
must match:

- standalone browser is collapsed at `max-width: 980px` and expanded from
  `981px`;
- embedded shell keeps the full sidebar from `1121px` and switches to the
  compact rail at `max-width: 1120px`; the compact rail remains operable through
  the visible toggle.

Therefore the initial-state decision uses `(min-width: 981px)` for browser and
`(min-width: 1121px)` for embedded. This avoids inventing a second breakpoint
system in JavaScript and prevents a pinned class from expanding into a compact
embedded grid.

## Decision: explicit state wins, then responsive default

`is-rail-pinned` is the existing explicit expanded-state marker. Initialization
must preserve it when present. When absent, the shell chooses the width-derived
default. There is no existing explicit server marker for a collapsed
preference, so no persistence or additional state encoding is introduced in
this slice.

## Decision: no resize listener

The reported behavior concerns initial load. A resize listener would turn a
one-time default into an unexpected ongoing policy and could overwrite a manual
choice. Reading `matchMedia` once also keeps the change cheap and safe across
HTMX/partial initialization; the existing `railReady` guard remains the only
initialization lifecycle guard.

## Alternatives considered

- **Always collapsed** — rejected because it is the root cause of the reported
  wide-window regression.
- **CSS-only class injection** — rejected because the current accessible label,
  `aria-expanded`, title and icon are synchronized by `setRailPinned`.
- **Window resize synchronization** — rejected because it overrides user intent
  and is not required by the request.
- **localStorage/session persistence** — rejected because this feature does not
  ask for cross-session behavior and existing guidance says not to add it.
