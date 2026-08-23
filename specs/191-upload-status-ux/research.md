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
11. Use a 36×20 shared switch for independent binary preferences. Keep the
    native checkbox input and add `role="switch"`; this preserves POST/no-JS
    behavior while matching the compact KRISP control geometry.
12. Keep checkboxes for multi-selection, consent, and confirmation. A switch
    communicates an immediately reversible on/off state and would be misleading
    for those tasks.
    Calendar event-type filters are one multi-select set and therefore remain
    checkboxes even though nearby display and prompt modes use switches.
13. Present light, dark, and system as a segmented native radio group with
    locally rendered Lucide-style icons from the existing icon primitive.
14. Move only secondary explanation behind an information button. The button is
    focusable and the hint opens for hover and focus; errors, security, billing,
    storage, and irreversible consequences remain visible.
15. Keep the local system font stack. On macOS it resolves to San Francisco,
    which provides the density and legibility needed here without a font
    download, layout shift, or new dependency.
16. Use KRISP's bounded settings column, divider rhythm, and right-aligned
    actions, but keep GRAF's navigation, Russian language, violet accent, and
    native form submission contracts.
17. Reuse `DesktopMeetingShellChrome.shellAccentColor` for native macOS
    readiness, upload, meeting-prompt, and recording-action accents. Keep green,
    orange, and red for success, warning, and error rather than flattening
    semantic status into one brand color.
18. Use one compact Jinja state component for full-page unavailable and
    full-content empty states. Runtime meeting authorization recovery clones an
    inert instance of that component, so markup and styling cannot drift from
    the server-rendered page.
19. Keep small Settings, billing, validation, and recovery messages inline.
    Promoting every message to a full-page component would erase hierarchy and
    make ordinary recoverable states feel terminal.
20. Remove the old `new-button` alias after the upload trigger and unavailable
    action move to the shared button primitives. Keep the one remaining
    `.empty-state` rule only for bounded list/transcript placeholders.

## Scope boundary

The full server-rendered cabinet stylesheet and native macOS product accents are
audited. Provider-logo brand colors remain unchanged, but all GRAF interaction
accents, shared typography, geometry, Settings navigation, upload dialog, and
upload activity are in scope.
