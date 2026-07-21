# Feature Specification: Desktop UI Polish

**Feature Branch**: `054-desktop-ui-polish`

**Created**: 2026-06-26

**Status**: Implemented locally; release and production rollout remain separate

**Input**: User description: "Причешем интерфейс 2brain Rec по присланному KRISP reference и текущему appshot: обратить внимание на масштаб записей, заполнение экрана, боковое меню, его верстку и наполнение. 053 уже занят, беру 054."

## User Scenarios & Testing

### User Story 1 - Meeting List Uses The Screen (Priority: P1)

As an owner in the macOS app, I can open "Мои встречи" and see a dense, readable meeting list that uses the available center workspace instead of sitting as a narrow strip.

**Why this priority**: The current list is the main entry point and the screenshot shows the strongest visual mismatch there.

**Independent Test**: Render the embedded meeting list and confirm the workspace width, row density, row metadata, and floating search remain readable without horizontal overflow.

**Acceptance Scenarios**:

1. **Given** the embedded desktop meeting list is open, **When** many recordings are present, **Then** rows stay compact, readable, and use most of the available workspace.
2. **Given** the list is viewed inside the native shell, **When** the right inspector is collapsed or expanded, **Then** the meeting list still has enough width for title, duration, status, actions, and date.

---

### User Story 2 - Sidebars Feel Like Product Navigation (Priority: P1)

As an owner, I can scan the left navigation and right control rail without oversized empty panels or confusing filler.

**Why this priority**: The reference uses persistent, compact sidebars; 2brain Rec should keep the same information rhythm while preserving its own brand and Russian copy.

**Independent Test**: Inspect the native shell constants and rendered web sidebar to confirm compact widths, stable labels, and no KRISP copy/assets are introduced.

**Acceptance Scenarios**:

1. **Given** the native shell is idle, **When** the right inspector is collapsed, **Then** the central workspace keeps priority and the rail remains usable.
2. **Given** the web cabinet is opened outside the app, **When** the left sidebar is visible, **Then** it shows product navigation, account/workspace status, and bottom account actions without marketing hero content.

---

### User Story 3 - Detail Review Remains Coherent (Priority: P2)

As an owner, I can open a meeting detail and keep transcript/review content readable while the side panel and playback bar stay out of the way.

**Why this priority**: Detail review already has more 052 coverage; this slice should preserve it while adjusting the page frame.

**Independent Test**: Render web and embedded detail pages and confirm playback, tabs, transcript empty state, right panel, and mobile breakpoints remain present.

**Acceptance Scenarios**:

1. **Given** a meeting detail has no transcript yet, **When** it renders, **Then** the empty state is centered in useful space and the right panel does not crowd the content.
2. **Given** playback is available, **When** the bottom player is visible, **Then** transcript content and speaker timeline are not hidden or clipped.

### Edge Cases

- Long recording titles must truncate cleanly without resizing rows.
- Empty lists must not leave a tiny card in the middle of a wide workspace.
- Embedded desktop and standalone web must share the same density without exposing native-only controls in web HTML.
- The design must not copy KRISP private content, brand assets, account text, or trade dress.
- Existing capture, upload, deletion, and privacy truth copy must remain intact.

## Requirements

### Functional Requirements

- **FR-001**: Embedded meeting list workspace MUST expand beyond the previous narrow `820px` cap while preserving responsive bounds.
- **FR-002**: Meeting rows MUST be scaled up from the current tiny rendering to a readable desktop row height while still supporting a scan-friendly list.
- **FR-003**: Meeting rows MUST expose title, duration, status, planned action slots, and date in a stable layout.
- **FR-004**: Native shell sidebar and right inspector widths MUST preserve central workspace priority in idle review mode.
- **FR-005**: Web sidebar MUST remain product-facing, localized, and free of KRISP copy/assets.
- **FR-006**: Detail review MUST preserve tabs, playback, transcript, right-panel governance, deletion truth, and speaker timeline behavior.
- **FR-007**: The feature MUST update regression tests for the changed density/width contract.
- **FR-008**: Evidence and docs MUST avoid raw meeting content, credentials, private account data, screenshots with private content, signed URLs, and local private paths.

### Key Entities

- **Embedded Workspace**: The server-rendered cabinet surface inside the native macOS shell.
- **Meeting Row**: A compact list item for one recording or meeting.
- **Native Inspector Rail**: The right-side SwiftUI controls for local recording, upload truth, trust, and diagnostics.
- **Clean-Room Reference**: KRISP observations used only for layout rhythm and information architecture.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Embedded web workspace max width is raised to at least `1040px` and native shell constants agree with that direction.
- **SC-002**: Embedded list rows use a readable desktop height between `44px` and `52px` while retaining title/status/date.
- **SC-003**: Focused server web-shell tests and focused macOS shell tests pass.
- **SC-004**: Rendered validation records no horizontal overflow for embedded list/detail screens.
- **SC-005**: No new dependency, route, schema, service, or design system layer is introduced for this polish.

## Assumptions

- KRISP is a clean-room reference for density and navigation rhythm only.
- This slice changes layout and copy density, not auth, upload, processing, deletion, or playback semantics.
- Browser/runtime proof may use existing 052 verifier patterns where useful.
