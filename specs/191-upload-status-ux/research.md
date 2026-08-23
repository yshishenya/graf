# UX Research: Upload Status And Processing Visibility

## Evidence used

- Nielsen's visibility-of-system-status heuristic: show the current state and
  feedback close to the action that caused it.
- WAI-ARIA progressbar pattern: expose `aria-valuenow` only for determinate
  progress; an indeterminate progressbar must omit the value instead of
  presenting a guessed percentage.
- WCAG 2.2 focus and non-text-contrast guidance: actions and focus treatment
  remain visible without hover and must survive narrow layouts, reduced motion,
  and forced-colors mode.

## Decisions applied

1. Keep transfer and server processing as separate states: `Загружаем файл…`,
   `Файл принят. Обрабатывается на сервере.`, and the meeting-row state
   `Обрабатывается` answer different user questions.
2. Put file name, metadata, status, bar, percentage, and the relevant action in
   one activity card. Actions are always present for keyboard and touch users;
   hover is only a visual affordance.
3. Use a violet determinate bar with a large numeric percentage when byte total
   is trustworthy. If it is not, keep the violet bar visible as indeterminate
   and hide both the percentage and `aria-valuenow`.
4. Preserve the recording start time as the primary date. For a manual upload
   without one, show the server receipt as `Загружено <date>, <time>` so the
   user can tell this is an upload timestamp rather than a recording timestamp.
5. Stack actions below the content at 375px and keep the date/status in the
   same row; this avoids a second dialog or a large empty progress panel.
6. Use KRISP's successful density pattern as a direct reference: 12px helper
   text, 13-14px body/label text, 36-40px controls, compact list rows, and a
   semantic token palette. Apply those patterns through GRAF's violet palette.
7. Keep percentage next to the upload state inside the content column and let
   the progress bar use the available width. A fixed side percentage creates
   an empty middle area and weakens the state/action relationship.
8. Use native `accent-color` for checkbox and radio controls instead of a
   custom painted control. It is the smallest accessible fix and survives
   platform semantics and forced-colors mode.
9. Preserve official provider-brand colors only inside provider identity
   marks. Blue is not allowed as a GRAF selection, focus, primary, checkbox,
   radio, or progress color.
10. Keep a single cabinet stylesheet. Central tokens and existing Jinja
    primitives are enough; a second CSS framework would increase drift.

## Scope boundary

The full server-rendered cabinet stylesheet is audited. Provider-logo brand
colors remain unchanged, but all GRAF interaction accents, shared typography,
geometry, Settings navigation, upload dialog, and upload activity are in scope.
