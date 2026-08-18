# Data Model: Meeting Review Continuity

This slice adds no persisted data or database migration. The following are
ephemeral view states used by the existing server-rendered review.

## Speaker lane

- `speaker_key`: existing stable lane key.
- `speaker_label`: existing server-confirmed display label.
- `segments`: existing bounded start/end seconds used for seek navigation.
- `talk_time_percent`: existing display metric.
- `interactive`: true only when the review has playable audio and the lane is rendered.

## Timeline height state

- `default_height_px`: fixed baseline `96`.
- `natural_height_px`: measured full height of complete rendered rows.
- `viewport_height_px`: current safe height available inside the review viewport.
- `current_height_px`: session-local value, bounded by the default and the smaller natural/viewport ceiling.
- `resize_available`: true only when the natural content exceeds the default.

State transitions:

```text
default -> expanded by pointer/ArrowUp/End
expanded -> smaller expanded value by pointer/ArrowDown
expanded -> default by Home or dragging to the baseline
any -> clamped value after viewport resize
any -> default and hidden affordance when rows fit
```

## Playback continuity state

The existing audio element remains the sole owner of:

- media source and DOM identity;
- current time and duration;
- playing/paused state;
- playback scale and active lane highlighting.

Speaker rename may update labels around this state but must not replace or
reinitialize it.

## Meeting review navigation

- `active_tab`: existing `recording` or `outcomes` value.
- `hash`: existing `#recording` or `#outcomes` deep-link value.
- `tab_panel`: existing ARIA relationship between tab and panel.

The sticky presentation changes no persisted navigation or URL semantics.
