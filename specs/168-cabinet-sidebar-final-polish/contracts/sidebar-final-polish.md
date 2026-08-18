# UI Contract: Финальная геометрия боковой панели

- Ready cabinet shell in collapsed state sets grid first column and
  `--playback-inline-start` to `var(--app-rail-width)`.
- Ready cabinet shell in `.is-rail-pinned` state sets both to
  `var(--app-sidebar-width)`.
- Standalone narrow shell follows the same compact rail contract when the
  visible rail is rendered; no empty grid column is introduced.
- The only web rail toggle remains `data-cabinet-rail-toggle`, with truthful
  `aria-expanded`, `aria-label`, `title`, icon and tooltip state.
- No new event listener or persistent state is introduced.
