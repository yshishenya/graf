# Data Model: Recording Selection And Delete

## Recording Row

Represents one meeting row visible in the owner meeting list.

- Identity: existing meeting ID.
- Display: title, duration, date, processing/review status.
- Access: existing owner/team/shared decision from cabinet list response.
- Lifecycle: existing deletion state controls whether the row is visible in active list.

## Selection Set

Temporary browser state for selected recording rows.

- Contains meeting IDs currently selected in the visible list.
- Clears after successful delete or when no selected rows remain visible.
- Does not persist to server storage.

## Delete Request

Existing server lifecycle request for whole-meeting deletion.

- Uses the existing bounded confirmation phrase.
- Creates deletion request, audit, report, artifact states, and local purge tasks through the existing lifecycle service.
- For batch selection, one request is submitted per selected meeting.

## Selection Toolbar

Temporary list UI state shown when `Selection Set` is not empty.

- Shows selected count in Russian.
- Shows disabled download action with later-copy.
- Shows enabled delete action.
