# Feature Specification: Recording Selection And Delete

**Feature Branch**: `053-recording-selection-delete`

**Created**: 2026-06-26

**Status**: Implemented; owner flow stays on the list and deletion lifecycle remains server-owned

**Input**: User description: "Fix the recordings list so records can be selected and deleted. Match the KRISP interaction expectation where selecting one or more records shows a top selection menu. Add a download icon but keep it disabled with Russian copy that download will be implemented later. Implement deletion now. On row hover, do not add the KRISP three-dot menu or unread action; show a direct delete icon instead. Pressing delete opens a Russian confirmation dialog. All dialogs and menu elements must be in Russian."

## Clarifications

### Session 2026-07-21

- Q: What should the owner see after confirming deletion? → A: Stay on the meeting list, remove the selected row or rows immediately after the server accepts the request, and do not show a persistent success or cleanup banner; do not open or link a deletion report.
- Q: What happens to lifecycle details that are not needed in the normal user flow? → A: Keep the existing lifecycle accounting and separate report endpoint for support and operator diagnostics, but keep it out of the owner confirmation and success flow.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Delete One Recording From The List (Priority: P1)

As an owner reviewing meeting records, I can delete one recording directly from the list after a clear Russian confirmation.

**Why this priority**: Broken deletion blocks basic cleanup and makes the review cabinet feel unfinished. A single-record delete is the smallest useful path.

**Independent Test**: Open a meeting list with at least one owned recording, use the visible row delete control, confirm deletion in Russian, and verify that the record leaves the active list and is not opened accidentally.

**Acceptance Scenarios**:

1. **Given** an owner can see a recording row, **When** the owner hovers or focuses the row, **Then** a direct delete control appears for that row without a three-dot menu.
2. **Given** the row delete control is activated, **When** the owner sees the confirmation dialog, **Then** all visible title, body, and buttons are in Russian and the dialog explains that the meeting will be deleted where `2brain Rec` controls it.
3. **Given** the owner confirms deletion, **When** the deletion succeeds, **Then** the row is removed from the active list and the owner stays on the list.
4. **Given** the owner cancels deletion, **When** the dialog closes, **Then** the row remains visible and unchanged.
5. **Given** the owner confirms deletion, **When** the request is accepted, **Then** the row disappears, the dialog closes, and the list does not render a persistent status banner or redirect to a deletion report.

---

### User Story 2 - Select Recordings And Delete Them Together (Priority: P1)

As an owner, I can select one or more recording rows and see a compact selection toolbar that lets me delete the selected recordings together.

**Why this priority**: The user explicitly reported that selection is broken. Selection must unlock the batch deletion path before production polish can continue.

**Independent Test**: Select multiple rows, confirm that the top toolbar replaces the normal list header with selected count, disabled download, and delete actions, then delete the selection through the Russian confirmation dialog.

**Acceptance Scenarios**:

1. **Given** no rows are selected, **When** the owner selects one row, **Then** the selected row is visually marked and a selection toolbar appears with the count in Russian.
2. **Given** two or more rows are selected, **When** the owner reviews the toolbar, **Then** the toolbar shows the selected count, a disabled download icon, and an enabled delete control.
3. **Given** the disabled download control is focused, hovered, or activated, **When** feedback is shown, **Then** the visible Russian copy says download will be implemented later and no download starts.
4. **Given** selected rows are deleted, **When** deletion succeeds, **Then** selected rows leave the active list and selection state clears.
5. **Given** selected rows are deleted, **When** the requests are accepted, **Then** the owner sees the list result rather than a lifecycle report.

---

### User Story 3 - Deletion Copy Stays Truthful (Priority: P2)

As the product owner, I can ship this delete UI without overstating erasure beyond systems controlled by `2brain Rec`.

**Why this priority**: Deletion is high-risk product copy. The UI must preserve existing deletion truth and lifecycle boundaries.

**Independent Test**: Review every new delete confirmation, disabled action, and error string and confirm it is Russian, understandable, and bounded to controlled `2brain Rec` storage.

**Acceptance Scenarios**:

1. **Given** deletion is presented to the owner, **When** the owner reads the dialog, **Then** the copy does not promise universal deletion outside `2brain Rec` control.
2. **Given** deletion fails, **When** feedback is shown, **Then** the owner sees a Russian failure message and the rows remain visible or return to the list.
3. **Given** one or many rows are selected, **When** the confirmation dialog is shown, **Then** the copy uses correct Russian plural meaning for the number of selected recordings.

### Edge Cases

- A selected recording disappears because another state update removes it before confirmation.
- A row delete is requested while other rows are selected.
- A delete request fails for one selected recording but succeeds for another.
- The selected list includes a meeting already deleting, deleted, or unavailable to the owner.
- The list is empty after deletion.
- A deletion request is accepted while lifecycle cleanup of local copies, backups, or dependencies is still pending; the list removes the row without exposing an internal cleanup status or claiming universal erasure.
- Keyboard-only users need to select rows, discover delete, cancel, and confirm without mouse hover.
- Disabled download must not start egress, create audit rows, or imply availability.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The meeting list MUST let an owner select and deselect individual recording rows.
- **FR-002**: The selected state MUST be visible on each selected row and MUST update the selected count immediately.
- **FR-003**: When one or more rows are selected, the normal list header MUST expose a selection toolbar with Russian visible labels, selected count, disabled download, and delete actions.
- **FR-004**: The download action in the selection toolbar MUST remain disabled and MUST explain in Russian that download will be implemented later.
- **FR-005**: The list row hover/focus state MUST expose a direct delete control and MUST NOT introduce a three-dot menu or unread action in this slice.
- **FR-006**: Every delete action MUST require explicit Russian confirmation before deletion starts.
- **FR-007**: Delete confirmation copy MUST use truthful deletion wording bounded to `2brain Rec` controlled systems.
- **FR-008**: Owners MUST be able to cancel delete confirmation without changing selected records.
- **FR-009**: Confirmed delete MUST remove deleted records from the active owner list after success.
- **FR-009a**: The owner list MUST remove a row immediately after its server-side deletion request is accepted and MUST keep the owner on the current list surface.
- **FR-010**: If deletion fails, the UI MUST keep or restore the affected rows and show a Russian failure message.
- **FR-011**: Batch deletion MUST clear selection for records that are no longer present after a successful delete.
- **FR-012**: Selection and deletion controls MUST be keyboard reachable and screen-reader understandable.
- **FR-013**: The implementation MUST preserve existing access, retention, deletion lifecycle, audit, and no-secret/no-private-content boundaries.
- **FR-014**: This slice MUST NOT implement mark-as-unread, a row overflow menu, bulk download, public links, external share, or partial artifact deletion.
- **FR-015**: User-facing changes MUST be covered by focused automated checks and a metadata-safe runtime proof for the list selection/delete flow.
- **FR-016**: The normal owner deletion flow MUST remove accepted rows and close the confirmation without rendering a persistent success or cleanup status, and MUST NOT redirect to, embed, or link the detailed deletion report.
- **FR-017**: The existing deletion lifecycle, audit records, and detailed report endpoint MUST remain available through separate support/operator or direct diagnostic paths; removing the report from the normal flow MUST NOT remove lifecycle accounting.

### Key Entities *(include if feature involves data)*

- **Recording Row**: A meeting record visible in the owner list, with identity, title, date, duration, state, and owner access.
- **Selection Set**: The current set of recording rows selected by the owner in the visible list.
- **Delete Request**: A user-confirmed request to delete one or more selected recording rows through the existing deletion lifecycle.
- **Selection Toolbar**: The temporary top action surface shown while at least one row is selected.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In focused runtime proof, selecting one row shows the selection toolbar and count in under one second.
- **SC-002**: In focused runtime proof, selecting three rows shows the correct selected count, disabled download action, and enabled delete action.
- **SC-003**: In focused runtime proof, confirming delete removes the selected rows from the active list with zero stale selected rows remaining.
- **SC-004**: 100% of new visible menu, toolbar, confirmation, disabled-action, and error strings for this slice are in Russian.
- **SC-005**: New deletion copy contains no universal-erasure promise and keeps the bounded `2brain Rec` control wording.
- **SC-006**: Focused automated checks cover single delete, batch delete, cancel, disabled download, and failed deletion behavior.
- **SC-007**: No new evidence committed by this slice contains raw audio, transcript text, credentials, tokens, signed URLs, object keys, private account identifiers, or private local paths.
- **SC-008**: In focused web-flow checks, an accepted delete leaves the owner on the meeting list, removes the selected row or rows, and renders no persistent success, cleanup, or report-status fragment.

## Assumptions

- The owner meeting list and existing deletion lifecycle from feature `018` are the source of truth for delete execution.
- The list already has enough stable row identity to support selection without a new data model.
- Batch deletion can be implemented by applying the existing whole-meeting deletion path to each selected meeting.
- The existing lifecycle service may finish local, backup, or dependency cleanup after the list has removed the row; detailed lifecycle/report information remains available only through its direct diagnostic/operator path.
- Download/export policy remains out of scope until a later slice explicitly enables it.
- KRISP screenshots are used only as clean-room interaction reference; 2brain Rec keeps original visual design and Russian copy.
