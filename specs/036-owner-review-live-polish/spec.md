# Feature Specification: Owner Review Live Polish

**Feature Branch**: `036-owner-review-live-polish`

**Created**: 2026-06-16

**Status**: Draft

**Input**: User description: "Continue toward MVP through the full SDD/Spec Kit cycle, carefully verifying against the reference desktop application and web product. Close the next plan item after 035: prove the live owner review route, decide notes/action truth, and move the installed desktop/web review surfaces toward the accepted clean-room V8 baseline without copying Krisp."

## Clarifications

### Session 2026-06-16

- Q: Does 036 require full generated notes/actions, or is truthful output status enough? → A: Truthful status is required; generated output improves readiness only when proven, while unavailable/deferred output keeps `mvp_loop_ready` excluded.
- Q: What live owner review evidence may be committed? → A: Metadata-safe evidence only; private meeting text, account identifiers, cookies, tokens, signed URLs, private screenshots, and raw content remain forbidden.
- Q: Does V8 polish require all 17 design frames in this slice? → A: No; this slice targets runtime-critical desktop/web owner review surfaces and records any remaining V8 gaps separately.

### Session 2026-06-17

- Q: Can the installed desktop MVP rely only on process environment variables for cabinet connectivity? → A: No; installed `/Applications/2brain Rec.app` must have a persistent or packaged internal-pilot cabinet connection path, with a truthful recovery state when server/auth configuration is missing.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prove Live Owner Review Access (Priority: P1)

As the product owner, I need to open the protected `rec.2brain.pro` review workspace as an authenticated owner and see my meeting list, meeting detail, and governance states without relying only on fixtures.

**Why this priority**: The current P1 blocker is `web-owner-live-auth-context`. Without live owner review proof, the product cannot claim the MVP loop is usable beyond infrastructure smoke.

**Independent Test**: A reviewer can use an authenticated owner session to open the production meeting list and at least one meeting review state, then record metadata-safe evidence showing whether the route is ready, empty, processing, denied, or blocked.

**Acceptance Scenarios**:

1. **Given** the owner has a valid session and at least one accessible meeting or safe empty state, **When** the owner opens the production review workspace, **Then** the page shows owner-appropriate meeting list content or an explicit empty state without exposing another user's data.
2. **Given** the owner opens a meeting detail state, **When** transcript, playback context, speaker information, governance actions, or processing status are available, **Then** the review surface shows the available state truthfully and keeps unavailable states explicit.
3. **Given** the owner session is missing, expired, or blocked, **When** the review workspace is opened, **Then** the product shows a login or recovery path without leaking meeting titles, transcript text, account identifiers, or existence proof.

---

### User Story 2 - Make Notes And Actions Truth Launch-Safe (Priority: P1)

As the product owner, I need the meeting review surface to state whether summary, decisions, action items, and follow-ups are available, still processing, blocked, or explicitly deferred so that the product does not overclaim AI meeting notes.

**Why this priority**: The current P1 blocker `notes-action-output` prevents `mvp_loop_ready` and `internal_pilot_candidate` claims. A polished UI that still hides missing notes would be misleading.

**Independent Test**: A reviewer can open ready, partial, processing, and no-output meeting states and determine within the review workspace whether notes/actions are available, pending, blocked, or deferred, with the readiness claim updated accordingly.

**Acceptance Scenarios**:

1. **Given** summary and action output exists for a meeting, **When** the owner opens the meeting review, **Then** the output is shown as meeting outcomes with source/provenance context and no fake confidence claim.
2. **Given** transcript exists but notes/action output is unavailable, **When** the owner opens the meeting review, **Then** the surface states the exact output status and whether the MVP claim remains blocked.
3. **Given** the product intentionally defers generated notes/actions for a narrower pilot, **When** readiness evidence is generated, **Then** `mvp_loop_ready` remains excluded and the deferral is named in the launch gap register.

---

### User Story 3 - Polish Desktop And Web Review Surfaces Toward V8 (Priority: P2)

As a user, I want the installed desktop app and web review workspace to feel like a product workspace rather than diagnostics, while preserving native capture trust controls and clean-room brand distance.

**Why this priority**: Feature 035 proves capture works from `/Applications/2brain Rec.app`, but the installed surface is still too operational/local-mode heavy for broad MVP review. V8 is the accepted implementation baseline.

**Independent Test**: A reviewer compares installed desktop and web surfaces against the accepted V8 handoff checklist and confirms meeting-workspace-first information architecture, persistent native capture controls, contextual search/filter/upload/review actions, readable text, and no Krisp visual/copy similarity.

**Acceptance Scenarios**:

1. **Given** the installed desktop app is launched from `/Applications/2brain Rec.app`, **When** the user lands in the main workspace, **Then** meetings, review status, and capture readiness are visible before low-level diagnostics.
2. **Given** recording is active, paused, resumed, or stopped, **When** the desktop workspace is visible, **Then** native Record/Pause/Resume/Stop authority remains persistent and cannot be obscured by embedded review content.
3. **Given** the web review workspace is open, **When** the owner uses list, detail, filter, upload, share/export/delete entry points, or responsive layouts, **Then** controls fit, labels are product-facing, and unavailable policy states are explicit.
4. **Given** the app is launched normally from Finder or `/Applications` with no developer shell environment, **When** the desktop workspace evaluates cabinet connectivity, **Then** it uses persisted or packaged MVP cabinet configuration before falling back to local-only mode, and the fallback explains the exact missing connection/auth state.

---

### User Story 4 - Update Readiness Claim And Next Slice (Priority: P3)

As the product owner, I need a single updated launch-readiness decision after this slice so the team knows whether the MVP loop is ready, still blocked, or ready for a narrower internal pilot.

**Why this priority**: The product plan must not drift. Closing a P1 blocker should update the strongest truthful claim and the next recommended product slice.

**Independent Test**: The readiness report, gap register, current product status, and changelog agree on the same outcome and do not list closed gaps as future work.

**Acceptance Scenarios**:

1. **Given** owner review proof and notes/action truth are complete, **When** readiness evidence is regenerated, **Then** closed gaps are removed or downgraded and the strongest claim is updated without exceeding evidence.
2. **Given** any P1 gap remains, **When** the status is published, **Then** the product remains `pilot_blocked` or a narrower truthful state with the missing evidence named.

### Edge Cases

- Authenticated owner review succeeds but contains private meeting content that cannot be committed as evidence.
- Production review route is reachable but returns an empty state because the owner has no processed meetings.
- The owner has meetings in multiple states: uploaded, processing, partial, failed, deleted, shared, or access-limited.
- Notes/action output exists for some meetings but not others.
- Summary is available while action items are unavailable, or transcript is available while summary is not.
- A shared or unauthorized viewer opens a protected owner route.
- Desktop embedded review fails to load while local capture controls must remain usable.
- Installed desktop app has no process environment variables because it was launched from Finder, Dock, login items, or `/Applications`.
- V8 visual baseline conflicts with constitution requirements, data-boundary rules, or live runtime constraints.
- Reference comparison reveals useful IA lessons but would require copying Krisp expression to match exactly.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The product MUST provide a commit-safe way to prove authenticated owner access to the production review workspace on `rec.2brain.pro`.
- **FR-002**: The owner review proof MUST include list, detail, and governance states, or an explicit reason why each state cannot be proven in the current environment.
- **FR-003**: Missing, expired, or invalid owner sessions MUST produce a safe login/recovery/blocked state without leaking meeting existence, titles, transcript text, account identifiers, cookies, tokens, or private URLs.
- **FR-004**: The meeting list MUST use product-facing labels for meeting status, source, duration, processing state, upload/search/filter/sort actions, access state, and primary review action.
- **FR-005**: The meeting detail MUST show transcript, speaker/provenance, playback context, processing status, and governance state truthfully when available.
- **FR-006**: The meeting detail MUST never fabricate transcript, summary, decisions, action items, follow-ups, speaker certainty, playback success, share success, export success, or deletion success.
- **FR-007**: Notes/action output MUST be represented as one of: available, processing, blocked, unavailable, or explicitly deferred; each state MUST explain the launch-readiness impact.
- **FR-008**: If notes/action output is available, the review surface MUST distinguish summary, decisions, action items, and follow-ups where the data supports that distinction.
- **FR-009**: If notes/action output remains unavailable or deferred, the readiness claim MUST keep `mvp_loop_ready` excluded and name the remaining gap.
- **FR-010**: The installed desktop app MUST remain anchored to `/Applications/2brain Rec.app` for runtime evidence and preserve native capture control authority outside server-rendered review content.
- **FR-011**: Desktop and web review surfaces MUST move toward the accepted clean-room V8 baseline: meeting workspace first, contextual list/detail actions, persistent capture status, dense but readable review content, responsive fit, and no internal diagnostic-first default.
- **FR-012**: The feature MUST preserve clean-room brand distance: no Krisp screenshots committed, no copied Krisp visual expression, no copied brand assets, no copied icons, and no exact copied product copy beyond generic category labels.
- **FR-013**: Evidence artifacts MUST be metadata-safe and MUST NOT include raw audio, transcript text from private meetings, private emails, account identifiers, cookies, credentials, tokens, signed URLs, local private paths, provider payloads, or private reference captures.
- **FR-014**: The final readiness report MUST update closed/remaining gaps, strongest truthful claim, next recommended product slice, and validation evidence.
- **FR-015**: The feature MUST update product status and changelog entries so completed 036 work is not listed as future work.
- **FR-016**: The feature MUST not broaden public-link, external-recipient, assisted auto-start, signed installer, or broad production rollout claims unless separate evidence exists.
- **FR-017**: The installed desktop cabinet configuration MUST NOT depend only on process environment variables; it MUST support a persistent or packaged internal-pilot base URL path and a truthful missing-auth/missing-server recovery state.
- **FR-018**: Desktop upload review links and embedded cabinet routes MUST share the same resolved cabinet base URL and safe owner/session context so an uploaded meeting can lead to a review surface without manual developer headers.

### Key Entities

- **Owner Review Proof**: Metadata-safe evidence that an authenticated owner can or cannot access list, detail, and governance states on the production review workspace.
- **Review Surface State**: The user-visible list/detail/governance state for a meeting, including ready, partial, processing, failed, deleted, access-limited, empty, or blocked.
- **Notes Action Truth**: The availability and launch impact of summary, decisions, action items, and follow-ups for each meeting review state.
- **Clean-Room UI Delta**: A documented change or validation result comparing current desktop/web surfaces to the accepted V8 baseline without copying reference expression.
- **Desktop Cabinet Connection**: The resolved installed-app configuration that decides whether the desktop shell opens server-owned meeting review or a truthful local-only recovery state.
- **Launch Claim Update**: The final bounded readiness decision and gap register after 036 validation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: One committed evidence pack shows the production owner review workspace state for list, detail, and governance, with every unproven state explicitly marked `blocked`, `empty`, or `deferred`.
- **SC-002**: 100% of ready, partial, processing, failed, empty, denied, and unauthenticated review states covered by this feature have a truthful notes/action status.
- **SC-003**: A reviewer can identify within 10 seconds whether a meeting has transcript, playback context, speaker/provenance, notes/actions, and governance actions available.
- **SC-004**: The installed desktop workspace evidence confirms native capture controls remain visible and usable in active, paused, resumed, and stopped states.
- **SC-005**: Clean-room reference validation records zero committed private Krisp screenshots, zero copied brand assets, zero copied icons, and zero exact copied non-generic product copy.
- **SC-006**: Final forbidden-content scans find no private payload values, raw audio, private transcript text, credentials, tokens, signed URLs, cookies, or live local private paths in committed 036 evidence.
- **SC-007**: Readiness, current status, changelog, and issue/task closeout agree on the same final claim and remaining gaps.
- **SC-008**: Installed-app evidence distinguishes configured cabinet, missing-auth, missing-server, and local-only states without requiring shell-only environment variables.

## Assumptions

- Existing features 013, 016, 017, 018, 033, 034, and 035 remain accepted foundations for authentication, meeting review, access/governance, deletion truth, desktop embedding, readiness reporting, and installed-app evidence.
- The accepted V8 design artifacts from feature 030 are the clean-room implementation baseline unless a later approved design artifact supersedes them.
- Live owner evidence may use screenshots or structured observations only after private meeting content, private account identifiers, tokens, cookies, and private URLs are excluded or redacted.
- If production owner review cannot be proven safely in this slice, the feature must preserve a truthful blocker rather than claim readiness.
- This feature may improve owner review and notes/action truth, but broad user rollout, signed installer evidence, assisted auto-start, public links, and external-recipient policy remain separate unless explicitly added by a later spec.
