# Feature Specification: Safe Browser Login Returns and Callback Diagnostics

**Feature Branch**: `107-auth-return-safety`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Fix the new-user Yandex login path that returns to an unavailable meeting, complete the related hardening, update from the mainline first, and do not release while parallel work is in progress."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Return to a Safe Place After Sign-in (Priority: P1)

As a person who signs in through the browser or embedded desktop cabinet, I want to arrive at a page I can actually use after login, so a stale link from another account does not leave me at a technical error.

**Why this priority**: A successful sign-in is blocked from delivering product value when it ends on an unavailable detail page. The destination decision must preserve privacy and work for a newly created account as well as an existing account.

**Independent Test**: Start signed out on an embedded or regular meeting-detail link, sign in as a user without access to that meeting, and verify that the user reaches the corresponding meeting list without receiving meeting content or a technical error payload.

**Acceptance Scenarios**:

1. **Given** a signed-out person opens a stale embedded meeting-detail link and then completes a supported sign-in, **When** the new session cannot view that meeting, **Then** the person is shown the embedded meeting list as a neutral recovery destination that does not reveal whether the requested meeting exists.
2. **Given** a signed-out person opens a regular browser meeting-detail link and then completes a supported sign-in, **When** the new session cannot view that meeting, **Then** the person is shown the regular meeting list without meeting content or a raw problem response.
3. **Given** a person completes sign-in from a meeting-detail link that their new session is permitted to view, **When** sign-in finishes, **Then** the person continues to that same meeting.
4. **Given** the meeting's sharing or workspace access changes while sign-in is in progress, **When** sign-in finishes, **Then** the destination reflects the access decision at completion rather than the state before sign-in.

---

### User Story 2 - Receive a Useful Unavailable Page (Priority: P2)

As a cabinet user who opens an unavailable detail link directly, I want a clear, normal product page with a way back to my meetings, so I do not have to interpret diagnostic JSON.

**Why this priority**: The return-path fix prevents the reported journey, but bookmarked, deleted, malformed, and revoked links can still happen outside login.

**Independent Test**: Open both embedded and regular unavailable meeting-detail links as an authenticated user and verify that each presents a neutral HTML page with a route back to the appropriate meeting list and no meeting data.

**Acceptance Scenarios**:

1. **Given** an authenticated person opens a detail link that is unavailable to their session, **When** the cabinet renders the failure, **Then** it shows a neutral unavailable page and a list-navigation action instead of a machine-readable problem document.
2. **Given** a detail link names a deleted, malformed, missing, or inaccessible meeting, **When** the unavailable page is shown, **Then** its wording does not distinguish among those cases or disclose another person's meeting information.

---

### User Story 3 - Keep Callback Diagnostics Safe (Priority: P1)

As an operator, I want login callback diagnostics to retain useful metadata without retaining authorization material, so support can investigate a failed or successful sign-in without exposing credentials through runtime logs.

**Why this priority**: Callback URLs can contain short-lived authorization and anti-forgery values. They must never become a second credential store in application logs.

**Independent Test**: Exercise successful and rejected callback requests containing unique harmless test markers, then verify that runtime logs retain route, outcome, timing, and correlation metadata but contain none of the marker values, cookies, session tokens, authorization codes, or callback state values.

**Acceptance Scenarios**:

1. **Given** a supported provider returns a browser callback, **When** the service records access and diagnostic events, **Then** it records only metadata needed for support and never records callback query values or authentication material.
2. **Given** callback validation fails, is cancelled, or is replayed, **When** the service records the outcome, **Then** the failure remains diagnosable without exposing authorization material or weakening the existing callback protections.

### Edge Cases

- A return destination is empty, malformed, non-local, or names a route outside the cabinet.
- A detail route has an invalid identifier, extra query values, or a different cabinet surface than the active session.
- A user receives access through ownership, workspace role, or an explicit share; each may change before callback completion.
- A callback is cancelled, expires, is replayed, or lacks its initiating browser binding.
- The normal meeting list is reachable but the requested detail is not; the fallback must remain useful without revealing the detail's existence.
- The service records a callback while logging is degraded; the login outcome must remain safe and no fallback logging may include raw callback data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST decide a browser sign-in return destination only after it has established the user and workspace session that will receive it.
- **FR-002**: The system MUST apply the same post-sign-in access decision to regular browser and embedded desktop meeting-detail destinations.
- **FR-003**: The system MUST preserve a requested meeting-detail destination when the completed session is authorized to view it.
- **FR-004**: When the completed session is not authorized to view a requested meeting-detail destination, the system MUST take the user to the corresponding meeting list as the neutral recovery destination.
- **FR-005**: The system MUST apply the return-destination policy to every supported browser sign-in path, including external identity providers and email sign-in or registration.
- **FR-006**: The system MUST keep existing callback anti-forgery, single-use, expiry, and initiating-browser protections effective for all sign-in paths.
- **FR-007**: A browser or embedded cabinet request for an unavailable meeting detail MUST receive a neutral human-facing unavailable page with a route back to the matching meeting list.
- **FR-008**: Neither a post-sign-in fallback nor an unavailable page MUST disclose whether a requested meeting exists, its title, owner, workspace, transcript, media, or sharing state.
- **FR-009**: Runtime access and diagnostic records for provider callbacks MUST exclude authorization codes, callback state values, cookies, session tokens, provider tokens, and raw callback query strings.
- **FR-010**: Safe callback diagnostics MUST retain correlation, route category, method, outcome, status, and duration metadata sufficient for support triage.
- **FR-011**: The feature MUST include repeatable verification that both allowed and denied post-sign-in destinations, direct unavailable links, and callback-log redaction behave as specified.
- **FR-012**: An email sign-in or registration completion MUST use the return candidate captured in its one-time server-side state; a later submitted `next` value MUST NOT override that candidate.
- **FR-013**: A malformed browser or embedded detail identifier MUST receive the same neutral unavailable experience as a missing or inaccessible detail, while asynchronous fragment requests retain their existing machine-readable contract.
- **FR-014**: The unavailable page MUST use the existing cabinet shell, a semantic page heading, and a keyboard-accessible matching-list action without introducing a new brand or diagnostic surface.

### Key Entities

- **Post-sign-in Destination**: The local cabinet page requested before login and resolved for the session created by that login.
- **Meeting Access Decision**: The current privacy-preserving determination of whether a session may view a meeting.
- **Unavailable Cabinet Page**: A neutral recovery page for a requested detail that is not available to the current session.
- **Callback Diagnostic Record**: Metadata-only operational evidence for a provider callback and its outcome.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of exercised denied post-sign-in detail journeys finish on the appropriate meeting list and expose no meeting content or raw problem document.
- **SC-002**: 100% of exercised allowed post-sign-in detail journeys retain the requested detail destination.
- **SC-003**: 100% of exercised direct unavailable detail journeys present a neutral human-facing recovery page with matching list navigation.
- **SC-004**: Automated callback-log checks find zero occurrences of unique test authorization-code, callback-state, cookie, or session-token markers in runtime access and diagnostic output.
- **SC-005**: Existing callback cancellation, expiry, replay, and initiating-browser-binding checks remain passing after the feature is introduced.
- **SC-006**: In automated email login and registration checks, a changed verification-form `next` value never changes the final return destination.

## Assumptions

- The existing meeting access policy remains the authority for ownership, workspace-role, share, deletion, and cross-workspace decisions; this feature does not alter who may access a meeting.
- The existing browser and embedded meeting lists are the safe recovery destinations for their respective surfaces.
- Supported browser sign-in methods retain their current identity and enrollment policies; this feature changes only the final local destination and diagnostics safety.
- Production log retention assessment, rotation, or deletion is a separate incident-operation decision and requires explicit authority.
- No release, deployment, tag, GitHub Release, or production cleanup is in scope until the user explicitly opens that gate after parallel work is complete.

## Out of Scope

- New identity providers, changes to enrollment policy, or changes to meeting sharing policy.
- Any change to capture, transcription, media storage, or macOS permission behavior.
- Client-only routing as the primary fix; existing clients must receive the safe behavior from the server.
