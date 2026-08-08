# Cabinet Selection Delete Contract

## List UI Contract

- `/meetings` and `/desktop/meetings` expose each meeting row with a selectable control.
- Selecting one or more rows shows a selection toolbar with:
  - Russian selected count.
  - Disabled download control.
  - Enabled delete control.
- Disabled download feedback says in Russian that download will be implemented later.
- Row hover/focus exposes a direct delete control.
- The row UI does not expose mark-as-unread or a three-dot menu in this slice.

## Deletion Request Contract

The list UI uses the existing endpoint for each confirmed meeting:

```http
POST /api/v1/cabinet/meetings/{meeting_id}/deletion-requests
Content-Type: application/json
```

```json
{
  "confirmation_boundary": "Delete this meeting everywhere 2brain Rec controls."
}
```

Expected successful response:

- HTTP `202`
- Existing deletion lifecycle response
- The owner web flow stays on the meeting list and removes the accepted meeting from the active list without opening a deletion report.
- The accepted meeting row is removed from the active list immediately after the
  request succeeds; no persistent success or cleanup banner is rendered.
- The user-facing list flow contains no report URL, report link, or internal
  cleanup status. Detailed lifecycle information remains available only through
  its existing direct diagnostic/operator path.

The detailed deletion report and API `report_url` remain available only through their existing direct diagnostic/operator paths; they are not part of the owner list confirmation flow.

Expected failure behavior:

- Affected row remains visible or returns to the list.
- Russian failure message is shown.
- No raw audio, transcript text, signed URLs, object keys, private account IDs, or private local paths are displayed.

## Copy Contract

Required visible Russian copy:

- Selection count: `Выбрано N`
- Disabled download title or feedback: `Скачивание появится позже`
- Delete confirmation title: `Удалить запись?` / `Удалить записи?`
- Bounded deletion sentence includes: `2brain Rec`
- Cancel button: `Отмена`
- Confirm button: `Удалить`
- Accepted request status: the row disappears from the list and the confirmation
  dialog closes. No success/cleanup copy is required.
