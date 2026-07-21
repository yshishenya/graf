# Feature Specification: Access, Sharing, And Downloads

**Feature Branch**: `017-access-sharing-downloads`

**Created**: 2026-06-16

**Status**: Implemented and production-smoke validated; rollout claims remain bounded

**Input**: User description: "Continue toward MVP after accepted meeting review and desktop cabinet embedding by adding browser-owned meeting access, sharing, export, and download policy around accepted meeting review data while preserving explicit egress, audit, retention/deletion truth, and no-secret evidence gates."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Govern Meeting Access (Priority: P1)

As a meeting owner, I want each meeting to have clear owner/team/shared access
state, so that only permitted people can open the review page and understand
why access is allowed or denied.

**Why this priority**: Access control is the release gate for every later share,
download, export, and audit flow. The product cannot safely launch if meeting
review data is visible only by convention or hidden only by UI.

**Independent Test**: Create meetings owned by one user and visible to a team or
individual recipient; verify owner, allowed teammate, explicitly shared user,
and unrelated user outcomes from both list and detail surfaces without relying
on private content.

**Acceptance Scenarios**:

1. **Given** a meeting owned by User A, **When** User A opens the meeting list
   or detail, **Then** the meeting is visible with owner access state.
2. **Given** a meeting shared with User B, **When** User B opens the meeting
   list or detail, **Then** the meeting is visible with shared access state.
3. **Given** a meeting not visible to User C, **When** User C attempts to open
   the meeting detail, **Then** the system shows a privacy-preserving denied or
   not-found state without confirming private meeting content.
4. **Given** a meeting is team-visible, **When** a permitted teammate views it,
   **Then** the UI shows team visibility and does not imply public access.

---

### User Story 2 - Share A Login-Required Meeting Link (Priority: P1)

As a meeting owner, I want to share a login-required link with specific people
or my workspace team, so that collaborators can review the meeting without
creating uncontrolled public access.

**Why this priority**: Login-required sharing is the narrowest useful share path
and matches the PRD's privacy posture. It moves the product toward launch while
keeping public-link risk out of the default MVP path.

**Independent Test**: From a meeting detail, grant and revoke a login-required
share; verify the recipient can access while shared, loses access after revoke,
and all visible states and audit records stay metadata-safe.

**Acceptance Scenarios**:

1. **Given** User A owns a meeting, **When** User A grants User B view access,
   **Then** User B can open the meeting through a login-required share link.
2. **Given** User B has shared access, **When** User A revokes that access,
   **Then** User B can no longer open the meeting and sees a bounded denied
   state.
3. **Given** a share link is copied, **When** an unauthenticated person opens it,
   **Then** they must authenticate before any meeting title, transcript, audio,
   summary, or participant content is exposed.
4. **Given** a meeting is shared, **When** reviewers inspect the activity trail,
   **Then** share-created, share-viewed, and share-revoked events are visible as
   metadata-only audit entries.

---

### User Story 3 - Download Permitted Artifacts (Priority: P2)

As a permitted reviewer, I want to download only the audio, transcript, or
summary artifacts that policy allows, so that I can use meeting outputs outside
the app without bypassing owner-controlled egress rules.

**Why this priority**: Downloads are useful for MVP customers but create egress
and deletion-truth obligations. They must be policy-gated, auditable, and clear
about what `2brain Rec` can and cannot revoke after export.

**Independent Test**: Configure different download permissions for audio,
transcript, and summary; verify allowed users see only permitted download
actions, denied users cannot fetch artifacts directly, and each completed
download creates audit and egress evidence.

**Acceptance Scenarios**:

1. **Given** a meeting policy permits transcript download but not audio
   download, **When** a permitted reviewer opens the detail page, **Then** only
   the transcript download action is available.
2. **Given** a reviewer lacks artifact download permission, **When** they try to
   open a direct download destination, **Then** the request is denied without a
   signed URL, storage key, or artifact path being exposed.
3. **Given** an artifact is missing, failed, deleted by policy, or still
   processing, **When** the reviewer opens download actions, **Then** the UI
   explains the unavailable state without promising recovery outside current
   product control.
4. **Given** a download completes, **When** the meeting activity is reviewed,
   **Then** a metadata-only download event identifies the artifact class,
   actor, time, and policy reason without recording private content.

---

### User Story 4 - Export A Safe Meeting Package (Priority: P2)

As a meeting owner or permitted reviewer, I want to export a safe meeting
package only when policy allows, so that I can share meeting outputs while
keeping egress, audit, and deletion truth explicit.

**Why this priority**: Export packaging is a natural extension of downloads and
is needed by teams that want transcript plus summary together. It can be
implemented after per-artifact permission gates because it depends on the same
policy and egress model.

**Independent Test**: Generate an allowed export package from a meeting with
ready transcript and summary; verify denied packages cannot be created, partial
packages show exactly which artifacts are included, and export events are
audited.

**Acceptance Scenarios**:

1. **Given** export is permitted and required artifacts are ready, **When** the
   user requests an export, **Then** the package includes only permitted artifact
   classes and shows what is included.
2. **Given** audio export is disabled but transcript and summary export are
   enabled, **When** an export is created, **Then** audio is excluded and the UI
   does not offer a hidden audio path.
3. **Given** an export has been created, **When** the user sees deletion or
   egress copy, **Then** the UI states that files already downloaded or exported
   cannot be revoked by `2brain Rec`.

### Edge Cases

- A user opens a valid share link after their account, workspace membership, or
  share grant was removed.
- A meeting owner shares with a person who already has team-level access.
- A share recipient tries to access a meeting while transcript or summary is
  still processing.
- A permitted reviewer refreshes an expired download destination.
- A meeting artifact is deleted by policy while a share link remains active.
- A direct artifact URL is copied and opened by a user without permission.
- A public-link policy is disabled for the workspace but a user tries to enable
  public access.
- A share, revoke, download, or export event cannot be written to the audit
  trail before the action completes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST represent meeting visibility as owner-only,
  team-visible, individually shared, or unavailable due to policy or lifecycle
  state.
- **FR-002**: The system MUST enforce meeting list and detail access using the
  viewer's authenticated identity, workspace membership, explicit share grants,
  and meeting lifecycle state.
- **FR-003**: The system MUST show privacy-preserving denied or not-found states
  for unauthorized meeting access without exposing private title, transcript,
  audio, summary, participant, storage, or processing details.
- **FR-004**: Meeting owners and permitted admins MUST be able to grant and
  revoke login-required view access for specific authenticated users.
- **FR-005**: Meeting owners and permitted admins MUST be able to set or clear
  team visibility when workspace policy allows team-visible meetings.
- **FR-006**: Share links MUST require authentication before exposing any meeting
  content or private metadata.
- **FR-007**: The system MUST show share state on meeting list and detail
  surfaces using product-facing copy that distinguishes owner, team, and
  individual share access.
- **FR-008**: The system MUST record metadata-only audit events for share grant,
  share revoke, share link open, successful view, denied view, download request,
  successful download, export request, successful export, and policy-denied
  egress attempts.
- **FR-009**: The system MUST support separate policy decisions for audio,
  transcript, summary, and combined package downloads/exports.
- **FR-010**: The system MUST hide or disable download/export actions when the
  viewer lacks permission or when the underlying artifact is missing, processing,
  failed, or deleted by policy.
- **FR-011**: Direct download or export destinations MUST re-check authorization
  and artifact lifecycle state at access time.
- **FR-012**: The system MUST avoid exposing storage keys, signed dependency
  URLs, raw object paths, credentials, bearer tokens, or private filesystem
  paths in list/detail responses, share links, download responses, exports,
  audit events, logs, specs, and validation evidence.
- **FR-013**: Download/export copy MUST state that files already downloaded,
  exported, or sent outside `2brain Rec` control cannot be revoked by later
  meeting deletion.
- **FR-014**: Public links MUST remain disabled by default unless a workspace
  policy explicitly enables them in a later or explicitly accepted scope.
- **FR-015**: The feature MUST not execute retention jobs, deletion workflows,
  legal hold, local desktop purge, or external dependency deletion; it must only
  preserve truthful copy and lifecycle state for those future controls.
- **FR-016**: The feature MUST keep browser/server ownership for sharing,
  access, export, download, and audit surfaces; the desktop app may embed or
  open those surfaces but MUST NOT own policy execution or artifact egress.
- **FR-017**: The UI MUST remain clean-room relative to Krisp and use existing
  `2brain Rec` product language, V8 IA gates, and feature `016` review cabinet
  patterns without copying Krisp assets, copy, private screenshots, or exact
  visual treatment.
- **FR-018**: The system MUST provide validation evidence showing permitted,
  denied, revoked, missing-artifact, and policy-disabled states without using
  private customer content.
- **FR-019**: Share grants, share revokes, downloads, and exports MUST fail
  closed when the required metadata-only audit event cannot be recorded before
  the action completes.

### Key Entities *(include if feature involves data)*

- **Meeting Access State**: The effective visibility of a meeting for a viewer:
  owner, team-visible, individually shared, denied, deleted, or unavailable.
- **Share Grant**: A login-required permission record that grants a specific
  authenticated user or allowed team scope view access to a meeting.
- **Share Link**: A stable meeting reference that requires authentication and
  resolves through the current access policy before showing content.
- **Download Policy**: A per-meeting or workspace-derived policy that determines
  whether audio, transcript, summary, or combined export egress is allowed.
- **Artifact Egress Event**: A metadata-only audit record for attempted,
  permitted, denied, completed, or failed download/export actions.
- **Export Package**: A policy-filtered package containing only permitted
  artifact classes and metadata-safe manifest information.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In validation, owner, explicitly shared user, team-visible user,
  unauthenticated visitor, revoked user, and unrelated user access outcomes are
  all demonstrated for list and detail surfaces.
- **SC-002**: 100% of direct artifact egress attempts in validation re-check
  current authorization and policy before returning downloadable content.
- **SC-003**: Reviewers can grant and revoke a login-required share and observe
  the access change within one page refresh or retry.
- **SC-004**: Download/export validation covers audio allowed, transcript
  allowed, summary allowed, package allowed, artifact missing, artifact deleted,
  and policy-disabled states.
- **SC-005**: Audit validation shows metadata-only events for share, revoke,
  denied access, download, and export actions without private transcript/audio
  content, credentials, signed URLs, storage keys, or live local paths.
- **SC-006**: Product copy for download/export/deletion truth avoids universal
  erasure claims and states the `2brain Rec` control boundary for exported
  files.
- **SC-007**: Sanitized screenshots or rendered evidence prove share/access and
  download/export UI states in desktop-width and mobile-width browser surfaces,
  using synthetic content only.

## Assumptions

- Existing feature `016-meeting-dashboard-review` remains the owner of the
  meeting list/detail review surfaces that this slice extends.
- Existing feature `033-desktop-cabinet-embedding` may embed these browser-owned
  surfaces but does not change the policy owner.
- Existing authentication, workspace, device/session, meeting, processing, and
  audit foundations are reused.
- Public-link sharing is out of scope by default; only login-required sharing is
  included unless a later clarification explicitly enables public links.
- Retention/deletion execution remains out of scope for feature `017` and is
  reserved for feature `018`.
- Export/download artifacts are generated from already accepted meeting review
  data and must not require desktop clients to hold server credentials or
  dependency credentials.
- All reference comparison uses clean-room V8 and Krisp IA/category notes, not
  private Krisp screenshots or copied product assets.
