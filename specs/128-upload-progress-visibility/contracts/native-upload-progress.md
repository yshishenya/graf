# Contract: Native Upload Progress Presentation

## Scope

The contract covers the existing native local-recording row in
`DesktopMeetingShellView`. It does not change upload transport, custody state,
server egress, retries, retention, deletion or local purge.

## Visibility

- When the item is `uploading` and its artifact profile has a positive total
  upload size, the row contains a determinate linear progress indicator and a
  localized percentage from `0%` through `100%`.
- When the item is `uploading` but no positive total is available, the row keeps
  the upload status copy and omits the percentage and determinate bar.
- When the item is `queued`, `retrying`, blocked, local-only or `uploaded`, the
  row does not show an active upload progress bar.
- `uploaded` continues to use the existing ready-to-view copy; 100% accepted
  bytes while still `uploading` uses bounded finalization/check copy.

## Accessibility

- The row exposes text state and percentage through its existing combined
  accessibility label.
- The progress visual is not the only state signal and does not expose paths,
  IDs, filenames, content or transport internals.
- Copy remains Russian-ready and works without color perception.

## Invariants

- The displayed value is clamped to 0…1 and comes from the current queue
  snapshot; there is no client timer or network request.
- No retry, stop, cancel, verify, upload-session or storage controls appear.
- Multiple rows keep the existing order and visibility limit.
- Browser/WebView meeting-list authority remains unchanged.

## Focused matrix

| State | Total known | Expected visible result |
|---|---:|---|
| `uploading` | yes, 0% | Active copy + empty linear bar + `0%`. |
| `uploading` | yes, 25–99% | Active copy + determinate bar + percentage. |
| `uploading` | yes, 100% | Finalization/check copy + full bar; not ready. |
| `uploading` | no | Active copy only; no invented percentage. |
| `queued` / `retrying` | any | Existing automatic-custody copy; no stale active bar. |
| `uploaded` | any | Existing ready copy; no active progress bar. |
