# Accessibility Requirements

## Keyboard

- Every primary action is reachable by keyboard.
- Focus order follows visual order.
- `Остановить` is first reachable critical control while recording is active.
- Escape closes popovers, drawers, modals, search, and filter menus unless a
  destructive confirmation is in progress.
- Tab order in meeting review is: title/actions, playback, transcript search,
  transcript turns, notes/actions, AI drawer trigger.
- Tray popover order is: `Остановить` while active, current status, open app, recent
  queue issue, settings handoff.

## Screen Reader

- Status badges include text labels, not only color.
- Progress and degraded states include stage and next action.
- Browser-only handoff says why the route opens in browser.
- Active capture uses an announced status change when recording starts, stops,
  saves locally, uploads, or fails.
- Transcript segments expose speaker label, timestamp, and confidence/provenance
  note when available.
- Upload drop zones expose accepted media types, max size when known, and the
  current validation stage.

## Contrast And Themes

- Light and dark themes must preserve contrast for primary text, status labels, and warnings.
- Danger/recording status uses text plus shape/icon, not color alone.
- Disabled controls must meet readable contrast for labels and include helper
  copy near the disabled action.
- Charts or audio meters are decorative unless paired with textual status; they
  must not be the only signal for active capture.

## Text Overflow

- Compact desktop surfaces must wrap long technical copy.
- Buttons use short verbs; long details move to secondary text.
- Meeting titles clamp to two lines in rows and expand in detail view.
- File names clamp in queue rows but remain available through tooltip and detail
  drawer.
- Russian and English copy must fit the same controls; if Russian copy exceeds
  the button width, move detail to helper text rather than shrinking type below
  12px.

## Motion And Timing

- Processing animations are optional and must not be the only progress signal.
- Active recording may pulse at low amplitude, but it must respect reduced
  motion and keep the static recording label visible.
- Toasts persist long enough to read and must also be reflected in durable row
  state.

## Privacy And Safety

- No hidden recording state: the active capture indicator and `Остановить` action remain
  visible in window and tray.
- Destructive actions require confirmation and a clear bounded deletion
  statement.
- Sharing/public-link controls require explicit confirmation before access is
  broadened.
