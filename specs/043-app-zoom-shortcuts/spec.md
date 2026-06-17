# Feature Specification: App Zoom Shortcuts

**Feature Branch**: `043-app-zoom-shortcuts`

**Created**: 2026-06-18

**Status**: Draft

**Input**: User description: "Analyze whether Cmd plus and Cmd minus can increase and decrease application zoom on the current stack with an embedded web view page. If possible, plan it as a new feature and implement it through SDD Spec Kit."

## Actors And User Goals

- **Desktop app user**: wants to make the meeting workspace easier to read or fit more content without leaving the macOS app.
- **Recording user**: needs recording controls, the visible capture indicator, and the one-action stop path to remain stable while changing the workspace scale.
- **Reviewer or QA**: needs a measurable way to confirm zoom behavior, persistence, accessibility, and brand-distance requirements without depending on production meeting data.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Adjust Meeting Workspace Zoom With Keyboard Shortcuts (Priority: P1)

As a desktop app user, I can press the standard macOS zoom shortcuts to increase, decrease, and reset the meeting workspace scale while staying inside the app.

**Why this priority**: The primary value is immediate readability control for the embedded meeting workspace without a separate settings flow.

**Independent Test**: Can be tested by opening the desktop app with a configured meeting workspace, using the zoom shortcuts, and confirming that the embedded workspace visibly changes scale while native recording controls stay in place.

**Acceptance Scenarios**:

1. **Given** the meeting workspace is available in the desktop app, **When** the user presses Command-Plus, **Then** the workspace content increases by one step without navigating away or hiding native controls.
2. **Given** the meeting workspace is available in the desktop app at an increased scale, **When** the user presses Command-Minus, **Then** the workspace content decreases by one step without breaking the loaded route.
3. **Given** the meeting workspace is available at any non-default scale, **When** the user presses Command-0, **Then** the workspace returns to the default scale.

---

### User Story 2 - Preserve Zoom Preference Across App Restarts (Priority: P2)

As a returning desktop app user, I want the app to remember the last chosen workspace scale so that readability does not need to be adjusted every launch.

**Why this priority**: Persistence turns the shortcut from a temporary aid into a usable accessibility and comfort preference.

**Independent Test**: Can be tested by changing the workspace scale, closing and reopening the app, and confirming the same scale is applied to the meeting workspace.

**Acceptance Scenarios**:

1. **Given** the user changed the workspace scale to a supported non-default value, **When** the app restarts, **Then** the embedded meeting workspace opens at the saved scale.
2. **Given** the stored zoom value is missing or invalid, **When** the app starts, **Then** the workspace uses the default scale.

---

### User Story 3 - Keep Recording Safety Controls Unaffected (Priority: P2)

As a recording user, I need zoom changes to affect only the meeting workspace surface, not the native recording indicator, stop path, upload truth, or local audio readiness controls.

**Why this priority**: The constitution requires visible capture state and one-action stop to remain reliable; zoom must not create a focus trap or hide those controls.

**Independent Test**: Can be tested with active and inactive recording states by changing zoom and confirming the native capture region remains visible, focusable, and outside the zoomed workspace.

**Acceptance Scenarios**:

1. **Given** recording is active and the stop action is available, **When** the user changes workspace zoom, **Then** the visible indicator and one-action stop remain reachable.
2. **Given** upload truth or local audio readiness messages are visible, **When** the user changes workspace zoom, **Then** those native messages do not change scale or disappear.

### Edge Cases

- Zoom changes must clamp at supported minimum and maximum values so repeated shortcuts cannot make the workspace unreadable or unusably large.
- The default scale must remain recoverable through Command-0 even after repeated zoom changes.
- Invalid, missing, or out-of-range saved preferences must fall back to the default scale.
- If the embedded workspace is unavailable or not configured, zoom shortcuts must not change recording behavior or show secret/configuration details.
- Keyboard shortcuts must not conflict with the existing recording shortcut or the Escape stop shortcut.
- Zoom must not change backend requests, meeting data, upload state, local recording state, or deletion behavior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The app MUST provide keyboard shortcuts for increasing, decreasing, and resetting the meeting workspace zoom.
- **FR-002**: The zoom shortcuts MUST use standard macOS command semantics: Command-Plus or Command-Equals to increase, Command-Minus to decrease, and Command-0 to reset.
- **FR-003**: The app MUST apply zoom only to the embedded meeting workspace surface, leaving native capture, upload truth, and local audio readiness controls at their normal scale.
- **FR-004**: The app MUST keep the visible recording indicator and one-action stop path reachable after every supported zoom change.
- **FR-005**: The app MUST constrain zoom to a documented supported range with predictable step increments.
- **FR-006**: The app MUST persist the user's chosen zoom level across app launches.
- **FR-007**: The app MUST recover to the default zoom level when the saved preference is absent, invalid, or outside the supported range.
- **FR-008**: The app MUST expose enough state for automated validation of shortcut behavior, clamping, reset, persistence, and native-control boundaries.
- **FR-009**: The app MUST avoid showing implementation terms such as "web view" in user-facing copy for this feature.
- **FR-010**: The feature MUST NOT alter meeting routes, workspace authorization headers, upload queue state, recording state, audio capture state, deletion state, or backend egress.

### Key Entities *(include if feature involves data)*

- **Workspace Zoom Preference**: A local user preference representing the selected meeting workspace scale. It has a default value, supported minimum and maximum bounds, and a fixed step size.
- **Zoom Command**: A user-triggered action to increase, decrease, or reset the workspace scale.
- **Native Shell Boundary**: The desktop app surface containing capture controls, upload truth, and local audio readiness; it must remain outside workspace zoom.

## Out Of Scope

- Pinch gesture zoom, trackpad smart zoom, and per-page browser zoom UI.
- Server-side changes to the meeting cabinet, API contracts, upload flows, auth, retention, or deletion.
- Scaling native capture controls, upload status, local audio diagnostics, or the full app window.
- New preferences screen or toolbar controls for zoom; this slice is keyboard-command-first.
- Any change to recording start/stop behavior, capture permissions, MediaScribe, Langfuse, MinIO, Postgres, Temporal, or Docker deployment.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can increase, decrease, and reset meeting workspace zoom with keyboard shortcuts in under 5 seconds without leaving the desktop app.
- **SC-002**: Repeated zoom-in and zoom-out commands never move the workspace outside the supported minimum and maximum values.
- **SC-003**: A saved supported zoom value is restored on the next app launch, and invalid saved values return to the default scale.
- **SC-004**: During active recording, the visible capture indicator and one-action stop remain reachable after zoom changes.
- **SC-005**: Automated macOS tests cover zoom command stepping, clamping, reset, persistence fallback, and native-shell boundary behavior.

## Assumptions

- The current macOS desktop stack remains the feature target.
- The meeting workspace is already embedded in the desktop app and can be scaled from the host application.
- The default zoom level is 100%.
- The supported range is intentionally conservative so accessibility benefits do not make the workspace unusable.
- Existing native recording shortcuts remain authoritative and must not be remapped by this feature.
