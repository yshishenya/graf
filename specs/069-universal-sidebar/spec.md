# Feature Specification: Universal Cabinet Sidebar

**Feature Branch**: `069-universal-sidebar`

**Created**: 2026-06-28

**Status**: Implemented and merged as the shared web/desktop cabinet sidebar

**Input**: User description: "Use feature 069 for a single reusable left sidebar so cabinet pages are laid out correctly and the same sidebar is reused in the web version and desktop embedded app. Remove the native app product sidebar and do not use it."

## Clarifications

### Session 2026-06-28

- Best-practice review: the shared sidebar is a repeated navigation landmark; it must have a stable accessible purpose, must not duplicate itself during dynamic updates, must expose exactly one current destination, and must keep keyboard focus visually distinct from the selected destination.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consistent Cabinet Navigation (Priority: P1)

A cabinet user opens the meetings list, meeting detail, and settings pages and sees the same left navigation structure, brand area, active item, disabled items, counters, and footer on every full cabinet page.

**Why this priority**: The sidebar is the primary product navigation. If each page owns its own sidebar, pages drift visually and future navigation changes become error-prone.

**Independent Test**: Can be tested by opening each full cabinet page and confirming that the navigation structure, active item, labels, disabled state, counters, and footer are consistent while page content changes independently.

**Acceptance Scenarios**:

1. **Given** a user is on the meetings list, **When** they navigate to meeting detail, **Then** the sidebar remains visually and structurally consistent and the page content changes to the detail view.
2. **Given** a user is on a settings page, **When** they compare it with the meetings page, **Then** both pages show the same sidebar contract with the correct active settings item.
3. **Given** a disabled navigation item is displayed, **When** the user tabs through navigation, **Then** the disabled item is not focusable as an active destination and does not imply an available feature.
4. **Given** a keyboard or assistive-technology user enters the sidebar, **When** they move through the navigation, **Then** exactly one available destination is exposed as current and the current keyboard focus is perceivable without being confused with that selected destination.

---

### User Story 2 - Same Navigation In Desktop Embedded App (Priority: P2)

A desktop app user views the embedded cabinet and gets the same product navigation and destination behavior as the web cabinet, adapted to the desktop embedded surface without any separate native product sidebar.

**Why this priority**: The desktop app should not maintain a second product navigation system. Product navigation must remain owned by the embedded cabinet while native app chrome keeps only capture and local safety controls.

**Independent Test**: Can be tested by opening the desktop embedded meetings and settings routes and confirming they use the same sidebar destinations and active states as the web cabinet, while preserving the desktop embedded compact behavior.

**Acceptance Scenarios**:

1. **Given** the embedded cabinet is open in the desktop app, **When** the user opens meetings or calendar settings, **Then** the sidebar uses the same navigation labels and destinations adapted for embedded routes.
2. **Given** the embedded surface is narrow, **When** the sidebar enters compact behavior, **Then** it preserves recognizable icons, accessible labels, active state, and a way to expand the menu.
3. **Given** the desktop app has native capture controls, **When** product navigation is displayed, **Then** navigation is owned by the embedded cabinet and no native desktop product sidebar is used.
4. **Given** compact navigation hides visible text labels, **When** a screen reader or keyboard user reaches a destination, **Then** the destination still has a clear accessible name and selected state.

---

### User Story 3 - Fragment Updates Do Not Duplicate Shell (Priority: P3)

A user filters meetings, opens dynamic fragments, or uses settings interactions and the page updates only the intended content area without re-rendering or duplicating the sidebar shell.

**Why this priority**: Cabinet pages use partial updates. A reusable sidebar must not break fragment behavior or create nested shells.

**Independent Test**: Can be tested by performing a meeting list filter update and a settings fragment action, then confirming that only the intended content region changes and there is still exactly one sidebar shell on the page.

**Acceptance Scenarios**:

1. **Given** the user filters the meeting list, **When** the content refresh completes, **Then** the sidebar remains unchanged and is not duplicated in the updated region.
2. **Given** a settings fragment is updated, **When** the response is rendered, **Then** the fragment contains page content only and does not include a second sidebar shell.

### Edge Cases

- A full cabinet page is rendered without an explicit active item; the default active destination remains meetings.
- The user opens an embedded route for a destination that has a different browser route; the active state remains the same product destination while the route path is adapted to the surface.
- The viewport is narrow or the embedded app window is constrained; the sidebar remains usable without hiding active recording stop or local safety controls outside the cabinet.
- A navigation item is unavailable for the MVP; it remains visibly disabled and non-committal rather than linking to unfinished behavior.
- A partial response is requested; the response must not include the full shell or sidebar.
- A future page introduces secondary navigation; the primary sidebar keeps a distinct accessible name so users can tell navigation regions apart.
- A dynamic content update returns a larger page response; the update must select only the intended content region and must not replace or duplicate the shared shell.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Full user-facing cabinet pages MUST use one shared sidebar contract for brand area, navigation items, active state, disabled state, counters, footer, and accessibility labels.
- **FR-002**: The shared sidebar MUST support both standalone browser cabinet pages and desktop embedded cabinet pages without creating separate product navigation experiences.
- **FR-003**: Desktop embedded cabinet pages MUST use the same product navigation destinations as browser pages, with route paths adapted to the embedded surface where needed.
- **FR-004**: The desktop app MUST NOT provide or depend on a native desktop product sidebar for cabinet navigation.
- **FR-005**: Each full cabinet page MUST declare only its content and selected navigation destination; sidebar markup and shell structure MUST be provided by the shared cabinet shell.
- **FR-006**: Partial page updates and fragments MUST render content only and MUST NOT include the full cabinet shell or duplicate the sidebar.
- **FR-007**: The sidebar MUST expose the current destination to assistive technology and keyboard users through a clear active state.
- **FR-008**: Disabled or future navigation items MUST be visible only as unavailable destinations and MUST NOT be keyboard-focusable links to unfinished behavior.
- **FR-009**: The sidebar MUST preserve brand-distance requirements by using the existing GRAF/2brain Rec visual language and avoiding copied third-party navigation patterns.
- **FR-010**: The shared shell MUST preserve desktop embedded compact navigation behavior, including an accessible expand/collapse affordance where compact mode is used.
- **FR-011**: Existing cabinet pages MUST keep their current user-facing page content, filters, forms, and safe copy while adopting the shared sidebar contract.
- **FR-012**: Admin pages are out of scope for this feature and MUST remain on their existing admin navigation surface unless a later feature explicitly unifies admin primitives.
- **FR-013**: The sidebar MUST be exposed as the primary cabinet navigation region with a stable accessible purpose that remains the same across covered pages.
- **FR-014**: The selected destination state MUST be visually distinct from the keyboard focus indicator on every supported surface mode.
- **FR-015**: Dynamic content updates MUST target or select the intended content region and MUST preserve exactly one shared shell and one primary sidebar on the page.
- **FR-016**: The primary sidebar navigation MUST expose exactly one current available destination on every covered full page and MUST NOT expose disabled or future destinations as current.

### Key Entities

- **Cabinet Navigation Item**: A user-facing destination with an identifier, label, destination, icon, availability state, and optional count.
- **Cabinet Navigation Model**: The ordered collection of navigation items plus the active destination and workspace presentation needed by the sidebar.
- **Cabinet Shell**: The full-page layout that combines the shared sidebar with a page content region for standalone browser and desktop embedded surfaces.
- **Cabinet Content Fragment**: A content-only response used for dynamic updates that must not include the cabinet shell or sidebar.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of full user-facing cabinet pages covered by this feature render the sidebar from the shared sidebar contract.
- **SC-002**: Browser and desktop embedded versions of the meetings and settings destinations show matching navigation labels and active states in validation.
- **SC-003**: Meeting list filtering and settings fragment updates complete without adding a second sidebar or shell in validation.
- **SC-004**: Keyboard navigation reaches the sidebar destinations in a predictable order, skips unavailable destinations, exposes exactly one current destination, and keeps focus visible and distinct on every full cabinet page.
- **SC-005**: Desktop embedded validation confirms product navigation is owned by the embedded cabinet and no native desktop product sidebar is required for meetings or settings navigation.
- **SC-006**: A sidebar label, active state, or footer change made through the shared sidebar contract appears consistently on 100% of covered full cabinet pages in validation.

## Assumptions

- The feature covers the user cabinet surfaces: meetings list, meeting detail, deletion report when rendered as a full cabinet page, settings, calendar settings, and their desktop embedded equivalents.
- Admin navigation remains separate because admin pages represent a different role, information architecture, and review surface.
- Authentication pages remain separate because they do not use the authenticated cabinet sidebar.
- The existing cabinet visual language, route ownership, and fragment behavior are retained unless a requirement above explicitly changes them.
- Native desktop chrome continues to own recording controls, local custody visibility, and one-action stop; product navigation remains in the embedded cabinet.
