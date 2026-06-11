# Feature Specification: MVP Product Experience And Design System

**Feature Branch**: `030-mvp-experience-design-system`

**Created**: 2026-06-11

**Status**: Draft

**Input**: User description: "Create the MVP product experience and design system for 2brain Rec. Think through what is already implemented, what is missing for a complete first launch, the macOS-first but multiplatform product model, the server-loaded account/cabinet experience inside the app, manual upload of users' own media files, and a modern 2026 minimal UX inspired by Krisp category patterns without copying Krisp UI, assets, copy, or proprietary behavior."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define The Launchable MVP Product Shape (Priority: P1)

As the product owner, I want one clear MVP product experience definition so that engineering, design, and QA know what must exist before the first version can be launched.

**Why this priority**: The current repository has strong capture, ingest, auth, and upload foundations, but launch readiness is blocked by missing product surfaces and inconsistent "what is ready" language. Without a single product shape, design and implementation will fragment across desktop, server, dashboard, and future platform work.

**Independent Test**: Review the feature output with current PRD/status/spec artifacts and confirm it names every launch-critical surface, state, dependency, and excluded item without contradicting the constitution.

**Acceptance Scenarios**:

1. **Given** the current accepted implementation baseline, **when** the MVP experience definition is reviewed, **then** it distinguishes implemented foundations from missing launch-critical product surfaces.
2. **Given** the launch scope includes desktop capture, account state, upload, processing, dashboard, and deletion truth, **when** the scope is reviewed, **then** each area is marked as required for first launch, deferred, or explicitly out of scope.
3. **Given** a stakeholder asks what the first version delivers, **when** they read the output, **then** they can explain the end-to-end user promise without reading implementation specs.

---

### User Story 2 - Design The Native Desktop Trust Shell (Priority: P1)

As a macOS user, I want the desktop app to feel simple, trustworthy, and always clear about recording, upload, and account state so that I can record meetings without guessing what is happening.

**Why this priority**: The desktop app owns capture-critical trust: visible recording state, one-action stop, local artifact truth, upload queue truth, permissions, offline/degraded states, and server/account connection state. The design must not be a generic dashboard embedded in a recorder.

**Independent Test**: Validate the desktop experience map against active recording, idle, blocked permission, uploading, upload failed, signed out, server offline, and policy-stale states. Each state must show one primary action and must not hide stop or active capture truth.

**Acceptance Scenarios**:

1. **Given** no recording is active, **when** the user opens the app, **then** the primary surface shows readiness, account/server status, recent local/uploaded meetings, and a clear recording action.
2. **Given** recording is active, **when** server or account state changes, **then** the app keeps local recording state and Stop visible and does not depend on server-rendered UI.
3. **Given** upload is blocked or delayed, **when** the user views the desktop shell, **then** the app explains whether data is local, queued, retrying, uploaded, or blocked and offers the correct next action.
4. **Given** the user needs account or workspace state, **when** they open the account area, **then** server-loaded account details are visible without giving remote UI control over capture-critical actions.

---

### User Story 3 - Design The Server Web Cabinet And Meeting Review Surface (Priority: P1)

As a meeting owner, I want a web cabinet where I can upload media, see meetings, track processing, review transcripts and notes, and manage access so that 2brain Rec is useful after recording stops.

**Why this priority**: The product promise is not just recording; it is uploaded meetings, transcripts, notes, playback, review, sharing, retention, and deletion truth in owner-controlled infrastructure. These surfaces are currently not implemented and must be designed before launch implementation.

**Independent Test**: Walk through a user uploading an existing media file, waiting for processing, opening the meeting detail page, reviewing transcript-linked playback, reading notes/action items, and handling a failed processing state.

**Acceptance Scenarios**:

1. **Given** a signed-in user has no meetings, **when** they open the cabinet, **then** the empty state offers recording guidance and manual media upload without pretending processing already exists.
2. **Given** the user uploads a media file, **when** upload begins, **then** the cabinet shows upload progress, accepted file truth, processing status, and failure recovery without exposing storage credentials.
3. **Given** a meeting is processed, **when** the user opens its detail page, **then** they can play audio, read transcript segments, review summary, decisions, action items, and see provenance/status of generated notes.
4. **Given** processing fails or is not available, **when** the user opens the meeting, **then** the page shows what exists, what failed, and what action is available without claiming transcript or notes readiness.

---

### User Story 4 - Define Cross-Platform UI Contracts And Boundaries (Priority: P2)

As the team preparing future platforms, I want shared product states, terminology, and design tokens so that macOS, future Windows, and web surfaces feel like one product without moving capture-critical control into a remote UI.

**Why this priority**: 2brain Rec is macOS-first now, but it is a multiplatform system. The first design system must support future platforms through shared contracts while preserving native trust shells per platform.

**Independent Test**: Compare desktop and web states for recording, upload, processing, auth, deletion, policy, and degraded modes. Each state must have the same user meaning across surfaces while allowing native presentation differences.

**Acceptance Scenarios**:

1. **Given** the desktop app shows an upload state, **when** the same meeting appears in the web cabinet, **then** both surfaces use consistent user meaning and do not contradict each other.
2. **Given** a future platform is planned, **when** designers inspect the system, **then** they can reuse naming, states, tokens, and interaction principles without reusing macOS-specific capture UI.
3. **Given** a server policy is stale or unavailable, **when** the desktop app continues locally, **then** the shared contract defines the user-visible state and fail-closed behavior.

---

### User Story 5 - Establish Clean-Room Visual Direction And Brand-Distance Gate (Priority: P2)

As the product owner, I want a modern 2026 visual direction inspired by category expectations but original to 2brain Rec so that the app feels simple, premium, and safe without copying Krisp.

**Why this priority**: Krisp is a useful category reference for logic and information architecture, but copying its UI, copy, icons, assets, or proprietary behavior would violate product and legal boundaries. The first launch needs a distinct design language before implementation expands.

**Independent Test**: Review the visual direction, key screens, and copy against a brand-distance checklist. The output must identify which category patterns are borrowed at the conceptual level and which Krisp-specific elements are forbidden.

**Acceptance Scenarios**:

1. **Given** Krisp is used as a benchmark, **when** design decisions are documented, **then** they describe category-level patterns such as compact audio controls, meeting notes navigation, and settings structure without copying visual expression.
2. **Given** 2brain Rec states require trust and clarity, **when** visual direction is reviewed, **then** it uses original typography, spacing, color roles, component rules, icon choices, and empty/error/loading states.
3. **Given** dark and light themes are required, **when** the design system is reviewed, **then** both themes preserve accessibility, non-color cues, and readable technical status text.

---

### User Story 6 - Produce An Implementation-Ready Experience Backlog (Priority: P2)

As engineering, I want the design feature to end with implementation-ready slices so that the next Spec Kit work can be planned without re-discovering the product.

**Why this priority**: A design-only output is not enough. The result must become concrete follow-up features, contracts, checklists, and sequencing for auth, cabinet, media upload, processing, dashboard review, sharing, retention, and desktop UI polish.

**Independent Test**: Convert the resulting experience backlog into follow-up Spec Kit feature candidates with owners, dependencies, acceptance gates, and validation evidence expected for each slice.

**Acceptance Scenarios**:

1. **Given** the design slice is complete, **when** the backlog is reviewed, **then** each launch-critical gap maps to a follow-up feature or task family.
2. **Given** a later implementation slice starts, **when** it uses this design output, **then** it can reference screen/state contracts and acceptance criteria instead of inventing UX from scratch.
3. **Given** an item is deferred, **when** the launch scope is reviewed, **then** the reason and user impact are explicit.

### Edge Cases

- User is signed out but local recording is still allowed by policy.
- Server is unreachable while a recording is active.
- Server account/cabinet state loads slowly or returns stale policy.
- User belongs to multiple workspaces with different recording and retention policies.
- User manually uploads a media file that lacks separate microphone/system tracks.
- User uploads unsupported, oversized, encrypted, corrupted, duplicate, or partial media.
- Processing succeeds for transcript but notes fail.
- Upload succeeds but MediaScribe processing is not configured or unavailable.
- Meeting exists locally but has not reached the server.
- Meeting exists on the server but the local desktop no longer has files.
- User attempts to delete a meeting with local buffers, server objects, backups, processing dependencies, and diagnostics involved.
- Design includes a component that could be mistaken for an OS recording indicator or a Krisp-specific UI element.
- Long technical status text overflows in compact desktop surfaces.
- Light/dark theme or color-only status would make a warning inaccessible.
- Future Windows design wants to reuse dashboard/account patterns but cannot reuse macOS capture controls.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST produce a launch-scope MVP experience map that separates accepted foundations, required first-launch gaps, deferred items, and out-of-scope items.
- **FR-002**: The feature MUST define the desktop app information architecture for home, live recording, account/workspace, recent meetings, upload queue, media upload entry point, audio health, privacy, retention, diagnostics, and settings.
- **FR-003**: The desktop experience MUST preserve native local authority for active capture state, visible recording indicator, one-action stop, permission state, local artifact truth, and offline/degraded recording states.
- **FR-004**: The desktop experience MUST define how server-loaded account/cabinet data appears in the app without giving server-rendered UI ownership of capture-critical truth or Stop availability.
- **FR-005**: The feature MUST define the web cabinet information architecture for meeting list, meeting detail, manual media upload, processing status, transcript review, notes/action items, account/security, admin settings, audit, retention, deletion, sharing, and downloads.
- **FR-006**: The manual media upload experience MUST define accepted user goals, upload states, processing states, failure states, duplicate handling, ownership labeling, and deletion/retention implications.
- **FR-007**: The meeting review experience MUST define required states for no transcript, uploading, ingested pending processing, processing, partial transcript, notes failed, complete, degraded, deleted, and access denied.
- **FR-008**: The design system MUST define shared state names, status meanings, tone, typography roles, spacing density, component families, icon rules, and light/dark theme behavior for desktop and web surfaces.
- **FR-009**: The design direction MUST be original to 2brain Rec and MUST NOT copy Krisp UI, assets, icons, copy, brand expression, proprietary flows, or model behavior.
- **FR-010**: The feature MUST include a clean-room benchmark summary that identifies allowed category-level lessons from Krisp and forbidden Krisp-specific elements.
- **FR-011**: The feature MUST define accessibility requirements for keyboard navigation, focus states, screen reader labels, non-color status communication, contrast, text overflow, and compact control surfaces.
- **FR-012**: The feature MUST define localization expectations for at least Russian and English user-facing copy categories, including recording, upload, processing, auth, deletion, and policy states.
- **FR-013**: The feature MUST define status copy principles that avoid false claims about processing readiness, upload completion, deletion scope, server availability, and external dependency deletion.
- **FR-014**: The feature MUST produce an implementation-ready backlog that maps launch-critical product gaps to follow-up Spec Kit slices and validation gates.
- **FR-015**: The feature MUST define which visual artifacts are required before implementation: screen inventory, user flows, state matrix, component inventory, visual direction, and QA checklist.
- **FR-016**: The feature MUST not authorize implementation of capture behavior, auth credentials, MediaScribe processing, sharing, deletion jobs, or production rollout by itself; it defines product/design readiness for later slices.

### Key Entities *(include if feature involves data)*

- **MVP Experience Map**: The launch product boundary across desktop, web cabinet, server account state, upload, processing, and governance surfaces.
- **Desktop Trust Shell**: Native desktop experience responsible for active capture, local recording truth, upload truth, account/server status, and local recovery.
- **Server Web Cabinet**: Browser-based workspace for meetings, manual uploads, transcripts, notes, sharing, retention, deletion, audit, account, and admin workflows.
- **Media Upload Flow**: User journey and state model for uploading existing files that were not recorded by the desktop app.
- **Meeting Review Surface**: Meeting detail experience with playback, transcript, notes, action items, processing truth, access, and deletion state.
- **Design System Contract**: Shared visual, interaction, state, copy, accessibility, and localization rules for desktop and web surfaces.
- **Brand-Distance Gate**: Review artifact that proves category inspiration remains clean-room and original to 2brain Rec.
- **Launch Backlog Map**: Follow-up feature sequence and validation gates needed to implement the designed MVP.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of launch-critical surfaces are classified as implemented foundation, required for first launch, deferred, or out of scope.
- **SC-002**: 100% of desktop capture-critical states preserve visible local recording truth and one-action stop in the experience definition.
- **SC-003**: At least 95% of reviewed primary MVP user journeys can be completed on paper from the design artifacts without inventing missing screens or states.
- **SC-004**: 100% of manual media upload states include user-visible truth for upload, processing, failure, ownership, retention, and deletion implications.
- **SC-005**: 100% of meeting review states distinguish upload success from transcript readiness, notes readiness, sharing readiness, and deletion truth.
- **SC-006**: 100% of design-system states include light/dark theme behavior, accessibility expectations, and non-color status communication.
- **SC-007**: Brand-distance review identifies zero copied Krisp assets, copied UI expression, copied product copy, copied icons, or proprietary behavior requirements.
- **SC-008**: The output produces at least six implementation-ready follow-up feature candidates with dependencies and validation gates.
- **SC-009**: At least 90% of internal reviewers can correctly answer "what ships in MVP" and "what remains after MVP" using the resulting artifacts.
- **SC-010**: No resulting artifact contradicts the constitution rules for capture authority, visible consent, data boundary, deletion truth, or Spec Kit delivery.

## Assumptions

- macOS remains the first launch platform; Windows and other platforms are future phases.
- The first launch must include a real server-connected account/cabinet experience, not only local recording.
- Desktop capture-critical surfaces remain native and locally authoritative.
- Web cabinet surfaces own post-meeting review, manual media upload, admin, sharing, retention, deletion, audit, and account/security workflows.
- Krisp may be studied only as a category and information-architecture reference; copied visual design, copy, assets, and proprietary behavior are forbidden.
- This feature produces specification and design-readiness artifacts; it does not directly implement the UI.
- Follow-up design generation, Figma/prototype work, and implementation slices may be separate tasks after this specification is clarified and planned.
- Existing specs `028` and `029` remain the auth/session and email/account-linking sources of truth unless later planning supersedes them.
