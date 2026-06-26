# Feature Specification: Web Cabinet HTMX Shell

**Feature Branch**: `058-web-cabinet-htmx-shell`

**Created**: 2026-06-26

**Status**: Draft

**Input**: User description: "Create Spec Kit feature 058 for the web cabinet architecture because 057 is occupied. The current local Swift sidebar/menu should move into the WebView in the future because, without network access, the sidebar has little value; offline users must still be able to record locally. The refactor must support a server-owned cabinet, reusable atomic components, a deliberate decision on whether to adopt a ready UI framework, modern 2026 stable approaches, HTMX adoption where it avoids duplicate migration work, strong security boundaries, maintainability, design consistency, and the full software development lifecycle."

## Architecture Decision *(fixed for this feature)*

Feature 058 uses a server-rendered cabinet frontend: backend routes render Jinja templates, reusable cabinet UI lives in template macros/includes, styling uses one static CSS file with CSS custom properties and semantic component classes, Lucide-style SVG icons remain the cabinet icon source, and HTMX 2.x is vendored locally for bounded progressive enhancements.

Feature 058 does not introduce Tailwind, Bootstrap, daisyUI, Flowbite, shadcn/ui, React, Vue, Svelte, Next.js, a client-side state store, a CDN-hosted UI asset, a standalone frontend app, a component preview app, or a design-system package. The existing Lucide-style inline SVG icon subset is allowed because it is an icon vocabulary, not a UI component framework.

This decision is intentional because the current cabinet has no frontend build pipeline, already has a product-specific visual language, and needs separation of responsibilities more than a new styling framework. Any future Tailwind or UI-kit adoption requires a separate Spec Kit feature that proves the extra toolchain is cheaper than the static CSS/token layer after this refactor lands.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Use One Online Cabinet Shell (Priority: P1)

As a meeting owner with server access, I want the cabinet sidebar, navigation, meeting list, meeting detail, playback, outcomes, and account/workspace menu to feel like one coherent online workspace whether I open it in a browser or inside the macOS app.

**Why this priority**: The product is now beyond a temporary meeting list. Playback, transcripts, outcomes, deletion, access, and future settings need one server-owned cabinet shell instead of duplicated browser and native navigation.

**Independent Test**: Open the web cabinet and the desktop embedded cabinet in an authenticated state and verify that both expose the same product navigation model, active section, core workspace content, localized labels, and bounded unavailable states without duplicating product menu logic in the native app.

**Acceptance Scenarios**:

1. **Given** an authenticated owner opens the standalone web cabinet, **When** the meeting list is shown, **Then** the page includes a product-facing cabinet sidebar, workspace/account area, active meeting navigation, and the meeting list in one coherent layout.
2. **Given** the same owner opens the macOS embedded cabinet, **When** the meeting list is shown in the WebView, **Then** the WebView owns the product sidebar/menu and the native shell does not duplicate that product navigation.
3. **Given** the owner opens a meeting detail from the sidebar/list workspace, **When** the detail page loads, **Then** the same cabinet shell remains in place and only the active workspace content changes.
4. **Given** future online sections are not ready, **When** the user sees their sidebar entries, **Then** they are either hidden or clearly bounded as unavailable without implying the action executed.

---

### User Story 2 - Keep Offline Recording Native (Priority: P1)

As a desktop user without server connectivity, I want local recording controls to remain available and truthful, while online cabinet navigation disappears or becomes clearly unavailable.

**Why this priority**: The desktop app's core safety promise is local recording with visible control. A server-owned menu must not create the impression that offline review, account actions, deletion, or settings are available when the server cannot be reached.

**Independent Test**: Launch or simulate the macOS app with the cabinet offline, timed out, not configured, and auth-expired. Verify that local recording and Stop remain available outside the WebView, while online cabinet navigation is unavailable or routed to login only when network/auth conditions allow it.

**Acceptance Scenarios**:

1. **Given** the server is offline, **When** the user opens the desktop app, **Then** the native shell shows local recording availability and cabinet-unavailable truth instead of rendering a stale online sidebar.
2. **Given** a recording is active and the cabinet becomes unavailable, **When** the WebView fails or reloads, **Then** the active recording indicator and one-action Stop remain visible and keyboard reachable outside the WebView.
3. **Given** local recordings or upload queue items exist while the server is unavailable, **When** the user views the desktop shell, **Then** local queue/upload truth remains visible without exposing private local paths or raw meeting content.
4. **Given** the session is expired but the server is reachable, **When** the user opens the desktop cabinet, **Then** login may be shown in the WebView while local recording controls remain native.

---

### User Story 3 - Build A Reusable Atomic Cabinet System (Priority: P1)

As a product and engineering team, I want cabinet UI pieces to be organized as a reusable atomic component system so future pages do not grow another monolithic file or drift in copy, spacing, icons, accessibility, and behavior.

**Why this priority**: The current cabinet grew through many MVP slices. The next architecture slice must stop further duplication before more pages are added.

**Independent Test**: Add or inspect at least three cabinet surfaces that share atomic controls, composed sections, navigation, status chips, icon buttons, rows, empty states, dialogs, and panels. Verify they use the same visible language, accessibility behavior, and state vocabulary.

**Acceptance Scenarios**:

1. **Given** the meeting list, meeting detail, and auth-required/unavailable states are rendered, **When** common controls appear, **Then** they use one shared component vocabulary and consistent Russian copy.
2. **Given** a destructive action such as deletion is shown, **When** the user opens its confirmation UI, **Then** the same bounded deletion wording and destructive visual treatment are reused everywhere.
3. **Given** a future online page is added, **When** it needs atoms such as buttons, icons, chips, inputs, tabs, badges, or loaders, **Then** it can reuse the existing atomic cabinet components without copying page-level markup.
4. **Given** a future online page needs composed regions such as sidebar, topbar, list row, playback bar, detail panel, modal, or empty state, **When** it is designed and implemented, **Then** it uses the shared cabinet component catalog instead of creating a one-off visual pattern.

---

### User Story 4 - Use The Fixed Cabinet UI Foundation (Priority: P1)

As the team maintaining the cabinet, I want one fixed UI foundation for this refactor so every new cabinet page uses the same product-owned components, static styling tokens, and progressive interaction rules.

**Why this priority**: Leaving Tailwind, UI-kit, or client-app adoption open creates drift. The cabinet needs a boring, stable baseline first: extract the current product-specific UI from the monolith into reusable server-rendered components and static CSS tokens.

**Independent Test**: Review the specification, plan, and resulting files to confirm that the cabinet uses server-rendered reusable components, one static CSS/token layer, local HTMX 2.x for bounded enhancement, and no Tailwind/UI-kit/client-app pipeline.

**Acceptance Scenarios**:

1. **Given** a cabinet page needs a button, icon button, chip, input, tab, dialog, list row, sidebar item, empty state, or panel, **When** it is implemented, **Then** it uses the internal cabinet component catalog and static CSS tokens.
2. **Given** a developer considers Tailwind or a ready UI kit during this feature, **When** the implementation plan is reviewed, **Then** that adoption is rejected as out of scope for 058.
3. **Given** HTMX is used for filters, sorting, deletion feedback, or region refresh, **When** JavaScript is unavailable, **Then** the same user flow still has a server-rendered full-page fallback.
4. **Given** a future page needs a visual pattern not yet in the catalog, **When** the pattern is added, **Then** it extends the small cabinet catalog rather than introducing a page-local styling system.

---

### User Story 5 - Use Progressive Server-Owned Interactions (Priority: P2)

As a meeting owner, I want filtering, sorting, deletion feedback, and page navigation to feel responsive without turning the cabinet into a separate frontend application.

**Why this priority**: The server owns meeting truth, access, deletion, playback, and outcomes. Progressive server-rendered interactions keep that truth centralized while avoiding a large client-side app.

**Independent Test**: With JavaScript enabled, perform list filtering, sorting, navigation, and safe mutation flows and verify only the relevant cabinet region updates. With JavaScript disabled or blocked, verify primary GET navigation and non-destructive review still work through full page loads.

**Acceptance Scenarios**:

1. **Given** JavaScript is enabled, **When** the user changes meeting filters or sort order, **Then** the meeting list updates without a full browser-like page reset and without losing the cabinet shell.
2. **Given** JavaScript is disabled, **When** the user opens the meeting list or detail, **Then** the essential read-only review still works through normal server-rendered pages.
3. **Given** a selected recording is deleted from the list, **When** the request succeeds or fails, **Then** the visible row state and error copy update from server-owned truth and do not silently remove data on failure.
4. **Given** an interactive update request is made from the embedded desktop WebView, **When** it reaches the server, **Then** authentication, authorization, and anti-forgery protection are enforced the same as in the standalone web cabinet.
5. **Given** the same cabinet route is requested as a normal navigation and as an enhanced region update, **When** the server responds, **Then** normal navigation receives a full page and enhanced updates receive only the intended bounded region.

---

### User Story 6 - Preserve Security, Privacy, And Lifecycle Truth (Priority: P1)

As a security-conscious owner, I want the cabinet refactor to preserve privacy boundaries, authorization, anti-forgery protection, deletion truth, and metadata-only evidence.

**Why this priority**: The web cabinet now touches meeting content, playback, outcomes, deletion, account/session state, and desktop embedding. A presentation refactor must not weaken the product's security promises.

**Independent Test**: Attempt unauthenticated, expired-session, unauthorized workspace, cross-site mutation, deleted/deleting meeting, and blocked-route scenarios. Verify each fails closed with bounded copy and no private content exposure.

**Acceptance Scenarios**:

1. **Given** a browser session uses cookies, **When** the user performs any unsafe cabinet action, **Then** the request is protected by anti-forgery controls in addition to cookie attributes.
2. **Given** a meeting is deleted, deleting, denied, or outside the viewer's workspace, **When** the user opens list, detail, playback, outcomes, export, or deletion routes, **Then** the cabinet hides or blocks content according to existing access and lifecycle truth.
3. **Given** validation evidence is collected, **When** screenshots, logs, traces, reports, or issue comments are produced, **Then** they contain only metadata-safe proof and no raw audio, transcript text, generated outcome text, signed URLs, object keys, credentials, private local paths, or private meeting identifiers.
4. **Given** the desktop WebView receives a route that tries to control capture, device routing, local diagnostics, local files, uploads, or permission recovery, **When** route policy evaluates it, **Then** the route is blocked, bounded, or opened externally without mutating local state.

---

### User Story 7 - Support Maintainable Delivery And Verification (Priority: P2)

As the team maintaining the product, I want this architectural slice to be delivered in small, reversible steps with clear validation so normal feature work can continue safely.

**Why this priority**: The cabinet is actively changing. The refactor must lower risk instead of pausing all product delivery behind a large rewrite.

**Independent Test**: Review the feature plan and tasks to confirm each migration step keeps current URLs and behavior working, has focused tests, and can be verified independently before the next step.

**Acceptance Scenarios**:

1. **Given** current browser and desktop cabinet URLs exist, **When** the refactor is delivered, **Then** those URLs continue to work or redirect safely without breaking existing desktop review links.
2. **Given** feature work continues during the refactor, **When** a new cabinet page is added, **Then** it has a clear place in the shared shell/component model and does not require editing a monolithic presentation file.
3. **Given** validation runs after each migration step, **When** failures occur, **Then** the team can identify whether they are shell, component, route-policy, security, or page-specific failures.

### Edge Cases

- Server offline, timeout, malformed response, or 5xx while the desktop app is idle, recording, stopping, or uploading.
- Auth expired while the WebView is on a protected route, including login recovery from the desktop shell.
- Enhanced interaction request receives an auth redirect, validation error, unavailable state, or problem response.
- Browser cookies present but anti-forgery token missing, stale, malformed, reused from another session, or submitted from an unexpected origin.
- Desktop WebView navigation to blocked local routes for capture, device routing, diagnostics, local files, upload picker, permission recovery, unsafe destructive actions without anti-forgery proof, billing, admin, or unknown external URLs.
- User opens a stale direct link to a meeting that is deleted, deleting, denied, or outside the workspace.
- User performs list filtering/sorting while selected rows or pending delete confirmation exists.
- User uses keyboard navigation, screen reader navigation, reduced-motion settings, high zoom, narrow desktop WebView, and mobile-width browser layouts.
- JavaScript disabled, failed to load, or blocked by policy; read-only cabinet pages must remain usable.
- A contributor attempts to introduce Tailwind, a ready UI kit, a client-side app framework, CDN UI assets, or a separate component-preview tool inside this feature instead of extending the fixed cabinet component catalog.
- Static CSS tokens or internal atomic components drift from the 2brain Rec visual language, use inconsistent icon sizing, or introduce one-off spacing/radius/token values.
- Interactive request returns partial failure, validation error, auth redirect, or unavailable state.
- Long Russian labels, long meeting titles, large row counts within the current list limit, empty list, and processing/partial/failed state mixes.
- Multiple tabs or WebViews open the same cabinet session and one tab mutates deletion/session state.
- Validation evidence collection must avoid private meeting content even when the UI naturally renders transcripts or outcomes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The product MUST define one canonical online cabinet shell for browser and desktop embedded use, including product navigation, workspace/account presentation, active route state, and a main content region.
- **FR-002**: The desktop app MUST keep local recording controls, active recording state, one-action Stop, permission recovery, local queue/upload truth, and local diagnostics outside the server-owned WebView.
- **FR-003**: The desktop app MUST NOT show a stale or non-functional online cabinet sidebar when the server is offline, timed out, malformed, or not configured.
- **FR-004**: The desktop app MUST show bounded native offline/unavailable states that preserve local recording availability and explain that online cabinet review requires the server.
- **FR-005**: The cabinet shell MUST support the current meeting list, meeting detail, playback, outcomes, deletion report, auth-required, expired-session, denied, not-found, and unavailable states without changing their user-facing truth.
- **FR-006**: The cabinet shell MUST provide a reusable navigation model that can represent current and future online sections without duplicating menu definitions across browser and native code.
- **FR-007**: The cabinet UI MUST provide reusable presentation components for sidebar items, topbar/workspace status, status chips, icon buttons, meeting rows, empty states, tabs, dialogs, playback controls, and destructive confirmations.
- **FR-008**: Shared cabinet components MUST use one localized Russian copy vocabulary, one Lucide-style 24px stroke icon vocabulary, one spacing/radius/typography system, and one accessibility behavior per control type.
- **FR-009**: The cabinet MUST support progressive server-owned interactions for list filtering, sorting, route transitions, selected-row delete feedback, and bounded error updates while preserving full-page server-rendered fallbacks for primary read-only routes.
- **FR-009A**: Progressive enhanced behavior MUST be opt-in by bounded cabinet region rather than a global shell-wide navigation takeover, and normal links/forms MUST remain correct when enhancement scripts are unavailable.
- **FR-009B**: Browser-side state MUST be limited to ephemeral interaction state such as focus, open dialog, pending request, and selected visible rows; meeting truth, lifecycle truth, authorization, deletion, playback, and outcomes MUST come from the server.
- **FR-010**: The feature MUST use server-rendered templates, one static CSS/token layer, and locally vendored HTMX 2.x as the complete cabinet frontend foundation for this slice.
- **FR-011**: The implementation plan MUST verify and pin stable versions for the server template dependency and HTMX 2.x before coding begins; prerelease, experimental, or under-construction major versions MUST be excluded.
- **FR-012**: Unsafe cookie-authenticated web actions MUST require anti-forgery protection in addition to cookie attributes and normal authorization.
- **FR-013**: Anti-forgery failure MUST fail closed with bounded user copy and MUST NOT execute deletion, share, export, retention, account, or other unsafe actions.
- **FR-013A**: Full-page and enhanced-region responses MUST be distinguishable so caches, redirects, tests, and error handlers do not confuse full layouts with fragments.
- **FR-014**: The desktop embedded route policy MUST allow only approved online cabinet routes and MUST block, bound, or externalize local capture, local diagnostics, local file, local upload picker, device routing, permission recovery, and unknown external routes.
- **FR-014A**: The desktop embedded route policy MUST classify routes by exact approved route kind rather than broad substring matching, including online cabinet routes, auth recovery routes, safe external help routes, blocked native/local routes, and blocked unknown routes.
- **FR-015**: Browser and desktop embedded cabinet routes MUST preserve existing access, tenant, lifecycle, deletion, egress, playback, and outcome privacy gates.
- **FR-016**: The refactor MUST preserve current public URL behavior for existing meeting list, meeting detail, desktop embedded list/detail, login/sign-up, playback, deletion, and report links.
- **FR-017**: The cabinet MUST not expose raw audio, transcript text, generated outcome text, signed URLs, object keys, credentials, private local paths, or private meeting identifiers in logs, diagnostics, traces, screenshots, issue text, or committed evidence.
- **FR-018**: The desktop native shell MUST remain keyboard reachable and must not let the WebView trap focus away from active recording Stop during active capture.
- **FR-019**: The cabinet shell MUST remain usable at desktop embedded width, standalone desktop browser width, and mobile-width browser validation without horizontal overflow or overlapping controls.
- **FR-020**: The feature MUST define a migration path that can be delivered in independently verifiable steps without requiring a full rewrite of all cabinet pages at once.
- **FR-021**: The feature MUST preserve fixture-backed and production-safe validation boundaries: private content is never required to prove layout, routing, security, or component behavior.
- **FR-022**: The feature MUST document what remains intentionally native after the sidebar moves into the WebView, and what belongs to the online cabinet.
- **FR-023**: The feature MUST define acceptance checks for both JavaScript-enhanced behavior and non-enhanced read-only fallback behavior.
- **FR-024**: The feature MUST keep future account, settings, activity, actions, access, export, deletion, and retention pages within the online cabinet navigation model unless a later spec proves they must be native.
- **FR-024A**: Existing machine-readable cabinet API contracts MUST remain stable unless a later API-specific spec explicitly approves changes; web fragments must not silently change public JSON response semantics.
- **FR-025**: The feature MUST standardize on a small product-owned atomic cabinet component catalog as the reusable UI boundary for this slice.
- **FR-026**: The styling foundation MUST be one static cabinet stylesheet with CSS custom properties, semantic component classes, and no frontend build pipeline.
- **FR-027**: Tailwind or Tailwind-style utility tooling MUST NOT be introduced in this feature.
- **FR-027A**: Bootstrap, daisyUI, Flowbite, shadcn/ui, Web Component UI kits, and other ready component kits MUST NOT be introduced in this feature.
- **FR-028**: React, Vue, Svelte, Next.js, client-side stores, hydration frameworks, and standalone frontend application shells MUST NOT be introduced in this feature.
- **FR-029**: CDN-hosted UI assets, external font dependencies, third-party analytics scripts, and prerelease/unstable component lines MUST NOT be introduced in this feature.
- **FR-030**: The static styling layer MUST NOT own product-specific cabinet composition, copy, lifecycle states, deletion truth, route policy, privacy wording, or evidence policy.
- **FR-031**: The component catalog MUST classify reusable pieces into primitive controls, composed cabinet sections, and full page templates so future pages have an obvious reuse path.
- **FR-031A**: The component catalog MUST centralize icon rendering through the existing Lucide-style inline SVG icon helper or equivalent template macro so pages do not embed ad hoc symbols, emoji, or one-off SVG styles.
- **FR-032**: Every reusable component MUST define required states, disabled/unavailable behavior, loading behavior when relevant, selected behavior when relevant, keyboard behavior, accessible name expectations, localization rules, and destructive/error treatment when applicable.
- **FR-032A**: High-use interactive cabinet controls MUST provide visible focus treatment, keyboard operation, and a minimum usable target size of 24 by 24 CSS pixels unless spacing constraints are explicitly validated with an equivalent accessible target.
- **FR-033**: Component examples or validation fixtures MUST cover at least normal, hover, focus, disabled, unavailable, loading, selected, destructive, error, empty, and overflow text states for the high-use cabinet components.
- **FR-033A**: The feature MUST NOT create a separate component preview application or broad design-system package for this slice; lightweight fixtures, component examples, and runtime checks are sufficient until reuse needs exceed the cabinet.
- **FR-034**: Template rendering MUST receive already-authorized view data and MUST NOT perform database access, tenant selection, authorization policy, deletion lifecycle decisions, or egress policy decisions.
- **FR-035**: Template rendering MUST preserve safe output encoding by default; any explicitly trusted HTML must be limited to reviewed component-owned fragments.
- **FR-036**: Desktop cabinet ready state MUST be based on successful allowed authenticated cabinet routes, not on a configured URL, a loaded login page, or a generic WebView success event.

### Key Entities *(include if feature involves data)*

- **Cabinet Shell**: The server-owned online workspace frame that contains product navigation, workspace/account status, main content, and bounded unavailable/auth states.
- **Cabinet Navigation Item**: A user-facing online section entry with label, icon, route, active state, availability state, badge/count, and optional bounded unavailable reason.
- **Cabinet Surface Mode**: The rendering context for standalone browser, desktop embedded WebView, login/auth recovery, and unavailable/offline fallback.
- **Native Capture Shell**: The macOS-owned area that remains responsible for recording start/stop, active recording truth, permissions, local queue/upload truth, diagnostics, and offline recovery.
- **Progressive Cabinet Interaction**: A server-owned UI update that can refresh a specific cabinet region when enhanced behavior is available and fall back to full page navigation when it is not.
- **Cabinet Fragment Response**: A bounded server-rendered region returned for an enhanced interaction, distinct from a full cabinet page and from machine-readable API responses.
- **Cabinet Component**: A reusable UI pattern with shared copy, visual treatment, state vocabulary, accessibility behavior, and validation expectations.
- **Atomic Cabinet Component**: A primitive reusable control such as a button, icon, chip, badge, input, link, tab, loader, tooltip, or text treatment with a defined state model.
- **Lucide-Style Icon**: A local inline SVG icon using the existing 24 by 24 viewBox, current-color stroke, rounded linecap/linejoin, and shared stroke width conventions; it standardizes icon shape without adding a UI framework.
- **Composed Cabinet Section**: A reusable combination of atomic components such as sidebar, topbar, meeting row, playback bar, detail panel, delete dialog, empty state, or unavailable state.
- **Internal Atomic Component Catalog**: The selected cabinet reuse boundary for this slice: product-owned primitive controls, composed cabinet sections, state vocabulary, accessibility behavior, localization rules, and validation fixtures.
- **Static Cabinet Style Layer**: The fixed styling foundation for this slice: one local stylesheet with CSS custom properties, semantic component classes, responsive rules, accessibility states, and no frontend build pipeline.
- **Out-of-Scope UI Framework**: Any Tailwind-style utility system, ready component kit, client-side app framework, component preview app, or design-system package; these are excluded from feature 058.
- **Anti-Forgery Guard**: A session-bound protection for unsafe web actions submitted through browser or embedded WebView cookie-authenticated flows.
- **Route Policy Decision**: The desktop classification of an embedded or external URL as allowed, blocked, opened externally, or bounded with a safe message.
- **Metadata-Safe Evidence**: Validation output that proves behavior using route classes, state names, counts, timing, viewport results, and pass/fail outcomes without private meeting content.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of validated browser and desktop embedded meeting list/detail routes show the same canonical online cabinet navigation model and active section state.
- **SC-002**: 100% of validated offline, timeout, not-configured, malformed, and server-error desktop states keep local recording controls available while hiding or bounding online cabinet navigation.
- **SC-003**: During active recording, 100% of validated desktop cabinet states keep active recording status and one-action Stop visible and keyboard reachable outside the WebView.
- **SC-004**: 100% of unsafe cookie-authenticated cabinet actions in validation either include valid anti-forgery protection and authorization or fail closed without mutation.
- **SC-005**: At least five common cabinet UI patterns are reused across at least three surfaces, with no duplicated product sidebar/menu definitions in native code after the migration step that enables the web-owned sidebar.
- **SC-006**: Existing public and desktop embedded cabinet URLs for meeting list, detail, auth recovery, playback, and deletion/report flows continue to pass focused compatibility checks.
- **SC-006A**: Existing cabinet API operation identifiers and response models remain unchanged in compatibility checks.
- **SC-007**: Enhanced list interactions complete visibly within one second for the current list limit under local validation, while read-only list/detail pages remain usable when enhancement scripts are unavailable.
- **SC-008**: Browser desktop, browser mobile-width, and desktop embedded validation record no horizontal overflow, incoherent overlap, or inaccessible primary navigation/action controls.
- **SC-009**: Forbidden-content scans over feature docs, evidence, logs, and screenshots find zero raw audio, transcript text, generated outcome text, signed URLs, object keys, credentials, private local paths, or private meeting identifiers.
- **SC-010**: The implementation plan records stable-version checks for the server template dependency and HTMX 2.x and excludes prerelease or under-construction major versions.
- **SC-011**: The migration plan defines at least four independently verifiable steps, each with focused validation and rollback/safe-stop criteria.
- **SC-012**: Product/design review confirms the web-owned cabinet shell remains original 2brain Rec UI, Russian-first, clean-room, and not copied from reference products.
- **SC-013**: UI foundation documentation records the fixed 058 baseline: server-rendered reusable components, one static CSS/token layer, centralized Lucide-style inline SVG icons, local HTMX 2.x enhancement, and no Tailwind/UI-kit/client-app pipeline.
- **SC-014**: At least twelve atomic cabinet components and six composed cabinet sections are specified or validated before broad page migration begins.
- **SC-015**: Component validation confirms long Russian labels, narrow embedded width, keyboard navigation, focus states, disabled states, loading states, selected states, destructive states, error states, and overflow behavior for all high-use cabinet primitives.
- **SC-016**: Enhanced interaction validation covers full-page response, fragment response, auth-required response, validation-error response, and unavailable-state response for at least the list and deletion flows.
- **SC-017**: Runtime and source validation confirms the cabinet shell uses zero CDN-hosted UI assets, external fonts, third-party analytics scripts, Tailwind-generated CSS, ready UI-kit runtime code, or broad external UI framework runtime code.
- **SC-018**: The implementation plan confirms no separate component preview application, design-system package, standalone frontend app, or frontend build pipeline is created for this slice.

## Assumptions

- Existing server-side authentication, tenant scope, access, deletion, playback, outcome, egress, and RLS boundaries remain authoritative and are reused.
- The online cabinet is the right home for product navigation, workspace/account menus, review surfaces, access/sharing, deletion, retention, activity, actions, settings, and future admin-facing pages.
- The native macOS app remains the right home for capture-critical controls, active recording truth, local permissions, local diagnostics, local queue/upload truth, and offline recovery.
- Desktop users may need to record while the server is unavailable; offline recording is therefore not dependent on the WebView.
- The current feature is an architecture and migration foundation, not a redesign of meeting content, a new capture feature, a new public sharing model, or a full account/settings implementation.
- Feature 058 uses server-rendered templates, a small product-owned component catalog, one static CSS/token layer, and local HTMX 2.x enhancement as fixed architecture decisions.
- The existing Lucide-style inline SVG icon subset remains the cabinet icon vocabulary and should be centralized with the component catalog.
- Tailwind, ready UI kits, client-side app frameworks, component preview apps, design-system packages, and frontend build pipelines are not part of this feature.
- Any future Tailwind or UI-kit adoption must be proposed in a separate Spec Kit feature after this refactor proves the remaining maintenance pain.
- Progressive enhanced behavior is expected for interaction-heavy online cabinet workflows, but primary read-only review must remain server-rendered and accessible without enhancement scripts.
- Existing URLs and route contracts should be preserved unless a later spec explicitly approves a migration with redirects and compatibility evidence.
