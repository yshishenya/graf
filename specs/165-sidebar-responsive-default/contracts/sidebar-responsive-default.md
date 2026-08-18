# UI Contract: Адаптивное стартовое состояние боковой панели

- Every full cabinet shell contains one `[data-cabinet-rail-toggle]` and one
  `[data-cabinet-navigation]` region.
- `initCabinetRail` initializes one shell only when `shell.dataset.railReady` is
  not `"true"`.
- If the shell already has `is-rail-pinned`, initialization passes `true` to
  the existing state synchronizer.
- Otherwise, standalone shells use `(min-width: 981px)` and embedded shells
  use `(min-width: 1121px)` as the one-time initial-state query.
- `setRailPinned` remains the single source for class, `aria-expanded`,
  accessible label, title, tooltip and icon state.
- A manual click, Escape, outside click, navigation click or partial
  initialization does not add a resize policy or second handler.
- The contract is presentation-only: no route, authentication, meeting,
  capture, playback, storage or analytics behavior changes.
