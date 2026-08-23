# Feature Specification: Upload Status And Cabinet Design System

**Feature Branch**: `191-upload-status-ux`

**Created**: 2026-08-23

**Status**: Draft

**Input**: User request to redesign upload and processing states on the main meeting screen, simplify the upload dialog, show the upload date, replace product blue with the GRAF violet accent, and centralize repeated cabinet and native-app styles and components.

## Clarifications

### Session 2026-08-23

- Q: Is the scope limited to the upload dialog? → A: No. The main meeting screen is primary; the dialog, Settings, and shared cabinet system are included.
- Q: May KRISP be used as a direct UX/UI reference? → A: Yes. Reuse effective density, sizing, hierarchy, and behavior while applying GRAF branding and product language.
- Q: Which product accent is canonical? → A: One GRAF violet accent across controls, selection, progress, focus, checkboxes, and radios; provider-owned brand marks keep their required colors.
- Q: How verbose should user-facing copy be? → A: Short, plain Russian; one state and one next action at a glance.
- Q: Which controls should become switches? → A: Independent binary preferences use switches. Multi-select lists, legal consent, destructive confirmation, and bulk selection remain checkboxes.
- Q: What about calendar event filters? → A: The set of event types remains a checkbox group; display and prompt modes remain switches.
- Q: What belongs in an information hint? → A: Secondary explanation may move behind a keyboard- and touch-accessible information button. Errors, security boundaries, legal terms, and irreversible consequences remain visible.
- Q: How should theme selection work? → A: Light, dark, and system themes use one segmented radio group with an icon and short label per option.

## User Scenarios & Testing

### User Story 1 - Understand the server state (Priority: P1)

As a meeting owner, I can immediately tell that a file was accepted, is being processed on the server, or needs attention.

**Independent Test**: Open the meeting list with an uploaded meeting in each upload/processing state and confirm the state, icon, and next action are visible without opening the meeting.

**Acceptance Scenarios**:

1. **Given** an uploaded file has been accepted and processing has started, **when** the list renders, **then** the row shows a clear processing state distinct from upload progress.
2. **Given** the server has accepted the upload but has not started processing, **when** the list renders, **then** the UI says that processing is waiting and does not imply completion.
3. **Given** processing or upload fails, **when** the list renders, **then** the user sees an attention state and an available recovery action where one exists.

### User Story 2 - See when the file entered GRAF (Priority: P1)

As a meeting owner, I can see the date and time when a manually uploaded file was received by GRAF, even when the source recording has no recording start timestamp.

**Independent Test**: Create a manual upload with no `started_at` and confirm the list shows its server upload timestamp instead of «Без даты»; confirm legacy rows without either timestamp keep «Без даты».

**Acceptance Scenarios**:

1. **Given** a manual upload has no recording start time, **when** it appears in the list, **then** the list shows the server-recorded upload date and time.
2. **Given** a recording has a real start time, **when** it appears in the list, **then** the recording time remains the primary date.
3. **Given** a legacy row has neither a recording time nor upload time, **when** it appears in the list, **then** the UI continues to say «Без даты».

### User Story 3 - Track an active upload without visual guesswork (Priority: P1)

As a meeting owner, I can follow the upload at a glance, including percentage, file metadata, state, and the next available action, with enough density to keep the meeting list useful.

**Independent Test**: Start a manual upload and inspect queued, active, accepted, canceled, and failed states on desktop and a narrow viewport.

**Acceptance Scenarios**:

1. **Given** an upload is active, **when** progress is determinate, **then** the percentage is shown next to a violet progress bar and the cancel action remains discoverable.
2. **Given** progress is not determinate, **when** the upload is active, **then** the UI uses an accessible indeterminate bar and does not show a false percentage.
3. **Given** an upload is accepted, **when** the server response is received, **then** the activity changes to a completed state and the meeting list refreshes.

### User Story 4 - See one consistent interface system (Priority: P1)

As a GRAF user, I see the same violet accent, control geometry, typography hierarchy, helper text, and interaction states throughout the cabinet.

**Independent Test**: Review the main list, upload dialog, Settings overview, one Settings detail page, and shared controls in dark/light themes and confirm they use the shared tokens and primitives without product-blue fallbacks.

**Acceptance Scenarios**:

1. **Given** a checkbox, radio, focus ring, selected row, primary button, or progress bar, **when** it is active or selected, **then** its product accent is the GRAF violet token.
2. **Given** repeated text roles such as body, helper, caption, section title, and page title, **when** they appear on different pages, **then** they use the shared typography scale rather than local one-off sizes.
3. **Given** repeated controls or cards, **when** their CSS is inspected, **then** their common dimensions, radii, spacing, colors, and states come from the central cabinet tokens or shared primitives.

### User Story 5 - Read Settings without drifting labels (Priority: P1)

As a GRAF user, I can scan Settings navigation and content without unstable wrapping, mismatched row heights, or text moving between pages and viewport sizes.

**Independent Test**: Open Settings overview and detail pages at desktop and 375px widths; verify navigation labels, helper copy, cards, actions, and headings reflow without clipping, accidental two-line rows, or horizontal scroll.

**Acceptance Scenarios**:

1. **Given** the desktop Settings sidebar, **when** long Russian labels are shown, **then** each navigation item keeps one stable row height and uses truncation only when the viewport cannot provide the designed width.
2. **Given** a narrow viewport, **when** Settings content reflows, **then** cards become one column and actions remain readable and reachable.
3. **Given** helper copy, **when** it wraps, **then** it wraps within its content column and does not push controls out of alignment.

### User Story 6 - Change preferences with familiar controls (Priority: P1)

As a GRAF user, I can distinguish a single on/off preference from a multi-select choice and can scan Settings without reading paragraphs before every action.

**Independent Test**: Open upload, account, notifications, and calendar Settings; verify binary preferences use the same switch, theme uses one segmented radio group, secondary explanation is available from an information button, and required safety copy stays visible.

**Acceptance Scenarios**:

1. **Given** a binary preference, **when** it is rendered, **then** it uses the shared switch with a visible label, keyboard focus, and native checked semantics.
2. **Given** a theme preference, **when** the user chooses light, dark, or system, **then** the selected segment is visibly violet and the existing preview/save behavior remains intact.
3. **Given** secondary explanatory copy, **when** the user hovers, focuses, or taps its information button, **then** the hint is readable without moving the associated control.
4. **Given** a multi-select list, consent, or destructive confirmation, **when** it is rendered, **then** it remains a checkbox or explicit confirmation rather than being misrepresented as a switch.

## Edge Cases

- The server returns an accepted upload without starting processing.
- The upload is interrupted or canceled while the dialog is closed.
- A session expires while the upload is active.
- The server returns no upload byte total, so percentage cannot be trusted.
- A legacy meeting has no `started_at` and no known upload timestamp.
- The viewport is narrow enough that metadata and actions would otherwise collide.
- A long Russian Settings label exceeds the available navigation width.
- Browser-native checkbox and radio colors differ by operating system.
- A provider identity uses blue as a required third-party brand color while nearby GRAF controls use violet.
- A long filename or upload title would otherwise push progress or actions outside the card.
- Reduced-motion or forced-colors preferences are active.
- A hint is opened with a keyboard or on a touch device rather than a mouse.
- A switch label wraps at 375px while the control must remain aligned and reachable.
- System theme is selected while the operating-system appearance changes.

## Requirements

### Functional Requirements

- **FR-001**: The meeting list MUST expose upload and server-processing states as separate, truthful user-facing states.
- **FR-002**: The backend response for a meeting list item MUST expose the server-recorded upload/creation timestamp separately from the recording start timestamp.
- **FR-003**: For manual uploads without a recording start timestamp, the list MUST display the server-recorded upload timestamp with the user's local display offset.
- **FR-004**: Rows with a real recording start timestamp MUST continue to use that timestamp as the primary meeting date.
- **FR-005**: Active upload UI MUST show determinate percentage only when total and accepted bytes are trustworthy.
- **FR-006**: Active upload UI MUST provide a visible status message, a violet progress treatment, and one relevant action without requiring hover.
- **FR-007**: Completed, waiting, canceled, and failed upload states MUST remain distinguishable after the upload dialog closes.
- **FR-008**: Blue used for upload, focus, selection, checkbox, and primary controls in the affected cabinet surface MUST be replaced with the existing GRAF violet accent or its accessible violet variant.
- **FR-009**: The redesign MUST preserve keyboard focus, live announcements, reduced-motion behavior, and forced-colors behavior.
- **FR-010**: The change MUST reuse the existing server-mediated upload endpoint and persisted timestamps; no new credential or storage boundary may be introduced.
- **FR-011**: Product UI accent color across the cabinet and native macOS product surfaces MUST be sourced from the central violet accent tokens; hard-coded product-blue interaction states MUST NOT remain.
- **FR-012**: Third-party provider marks MAY retain their official brand colors, but those colors MUST be isolated as provider identity and MUST NOT style GRAF controls, focus, selection, status, or progress.
- **FR-013**: Shared typography roles MUST be defined centrally for caption, helper, body, label, section title, dialog title, and page title text.
- **FR-014**: Shared control heights, radii, spacing, surfaces, borders, focus treatment, and semantic status colors MUST be defined centrally in the existing cabinet stylesheet and reused by repeated components.
- **FR-015**: Native checkboxes and radios MUST use the GRAF violet accent in supported browsers and remain identifiable in forced-colors mode.
- **FR-016**: Upload-dialog and upload-status copy MUST use short plain Russian that states the current state and next action without explanatory paragraphs in the primary scan path.
- **FR-017**: The desktop Settings navigation MUST keep stable row geometry for long Russian labels; narrow layouts MUST reflow without clipping or horizontal scrolling.
- **FR-018**: The implementation MUST consolidate conflicting duplicate rules for the same shared component instead of adding a second design-system layer or frontend dependency.
- **FR-019**: Independent binary preferences in manual upload, notifications, and calendar behavior MUST use one shared switch primitive with native checkbox form semantics and `role="switch"`.
- **FR-020**: Multi-select calendars, calendar event-filter groups, meeting selection, summary sections, billing consent, and destructive confirmation MUST remain checkboxes or explicit confirmations.
- **FR-021**: The upload retention row MUST keep its label vertically aligned with the switch and MUST NOT reserve a second line for explanatory copy.
- **FR-022**: Secondary retention explanation MUST be available through a shared information-button hint on hover, keyboard focus, and touch activation.
- **FR-023**: Security, legal, error, storage, and irreversible-action consequences MUST remain visible in the primary interface and MUST NOT be available only through a tooltip.
- **FR-024**: Theme selection MUST use one shared segmented radio group for light, dark, and system values while preserving native form submission and the existing live preview.
- **FR-025**: Settings preference rows MUST use one shared content/action geometry with a bounded content width, stable divider rhythm, and responsive wrapping that does not move switches below their labels.
- **FR-026**: Settings typography MUST use the existing local system font stack and central text-role tokens; the change MUST NOT introduce a remote font, frontend package, or second stylesheet.
- **FR-027**: Native macOS upload/readiness states, meeting prompts, and recording actions MUST reuse `DesktopMeetingShellChrome.shellAccentColor`; semantic success, warning, and error colors MAY remain green, orange, and red.

### Key Entities

- **Meeting list item**: A meeting projection containing recording time, server upload time, and current review/upload/processing status.
- **Upload activity**: The client-side visible transfer state for the selected file, including accepted bytes, total bytes, progress mode, and recovery action.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In a list screenshot, a reviewer can identify upload, processing, ready, and attention states without opening a meeting in 4 out of 4 seeded states.
- **SC-002**: 100% of manual uploads with no recording start timestamp show a non-empty server upload date when the backend has a creation timestamp.
- **SC-003**: 0 affected active-upload states display a blue progress bar, blue primary button, or false percentage.
- **SC-004**: The upload activity remains usable at desktop width and at 375px viewport width without clipped primary actions.
- **SC-005**: Focused backend/view-model/static contract tests pass, and the relevant local rendered flow has no framework overlay or relevant console errors.
- **SC-006**: Across the audited cabinet stylesheet and native macOS product UI, zero GRAF interaction accents use legacy product-blue values; any remaining blue is documented provider identity or non-interactive content semantics.
- **SC-007**: Main upload activity keeps progress, percent, state, and action in one compact scan path with no fixed empty gap at desktop or 375px widths.
- **SC-008**: Shared checkbox and radio controls render with violet selection in the upload dialog and Settings on the current local browser.
- **SC-009**: Settings navigation labels have stable 36-40px rows on desktop and no label-driven vertical drift in the audited screenshots.
- **SC-010**: The stylesheet has one canonical rule set for Settings overview cards and one central token group for repeated typography, geometry, and interaction colors.
- **SC-011**: 100% of audited independent binary settings in upload, notifications, and calendar behavior render through the shared switch primitive; audited multi-select and consent controls remain checkboxes.
- **SC-012**: Upload retention label, information button, and switch remain vertically centered at desktop and 375px widths with no visible explanatory line below the control.
- **SC-013**: Light, dark, and system theme choices render as one segmented group and remain operable with pointer and keyboard in both browser and embedded surfaces.
- **SC-014**: Focused rendered-template contracts prove the hint has an accessible name and tooltip relation, switches preserve checked state, and no critical safety copy was moved to tooltip-only presentation.
- **SC-015**: Focused macOS source contracts and a Swift build prove the audited native product surfaces use the shared violet token and contain no system `.blue` accent.

## Assumptions

- `Meeting.created_at` is the authoritative server receipt time for a manual upload and is already persisted for existing rows.
- A recording's `started_at` remains authoritative when present; the upload timestamp is a fallback only for missing recording time.
- The scope is the whole server-rendered cabinet stylesheet and its shared primitives plus native macOS product-accent cleanup, with the main meeting upload/processing experience as the primary deliverable.
- KRISP is an approved reference for effective density, component sizing, hierarchy, and interaction behavior; GRAF keeps its own violet palette, assets, and Russian product language.
- Provider logos and identity badges are not recolored when their blue is part of the provider brand.
- No production deployment or release is requested in this task.
