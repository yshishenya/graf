# Research: Финальная геометрия боковой панели

## Decision: derive playback start from the rail state

The shell already exposes `--app-rail-width`, `--app-sidebar-width` and
`is-rail-pinned`. The late ready-state CSS overrides the grid but does not set
the matching playback variable, which creates the gap after collapse. Adding
the paired variable selectors in the same late layer fixes the shared cause.

## Decision: keep web toggle top and singular

The server macro already renders one top toggle with icon, title, tooltip,
label and ARIA state. Duplicating it or moving it to a bottom affordance would
reintroduce ambiguity and is outside this successor slice.

## Alternatives considered

- JavaScript `style.left` updates — rejected: duplicates CSS state and can drift
  after partial updates.
- Measuring sidebar width in JavaScript — rejected: existing CSS tokens already
  express both widths.
- A second toggle — rejected: one control is clearer and keeps focus behavior.
