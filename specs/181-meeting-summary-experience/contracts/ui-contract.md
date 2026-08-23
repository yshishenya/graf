# UI contract

## Accepted result present

- Show accepted format and result first.
- Format picker describes purpose; choosing a different format clearly creates a new variant.
- `Обновить итоги` means regenerate the current accepted format.
- Candidate status copy always states that current results remain unchanged.
- Preview is a named review region; passive live text and action buttons are siblings.
- Closing comparison does not reject candidate. Reject is a separate explicit action.

## No accepted result

- Default tab shows `Итоги готовятся` with selected default format.
- No transcript fragments are rendered as ready notes.
- Dependency/error state names one safe next action.
- Controls are shown only when the generation route is genuinely available; unavailable state explains why.
- Fully empty validated result collapses to one meeting-level explanation.

## Accessibility

- Keyboard: tabs, picker/listbox, dialog, candidate actions and source links.
- Focus returns to invoking control after list/dialog; candidate completion does not steal focus unexpectedly.
- Live region contains bounded text only; buttons are in a sibling action region.
- 390px viewport and 200% zoom retain one-column readable outcome and reachable actions.
- Web and embedded routes render the same lifecycle and accepted content.
