# UI Contract: Выравнивание нижнего playback

- Collapsed ready shell: grid first column and `--playback-inline-start` are
  `var(--app-rail-width)`.
- Expanded ready shell: grid first column and `--playback-inline-start` are
  `var(--app-sidebar-width)`.
- Both values are inherited by `.playback-bar { left: var(--playback-inline-start) }`.
- Toggle transitions do not replace the audio element or mutate current time.
- The same offset applies to available, preparing and unavailable playback
  states.
