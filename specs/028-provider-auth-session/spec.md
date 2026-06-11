# Feature Specification: Provider Auth Session And Device Identity

**Feature Branch**: `028-provider-auth-session`

**Created**: 2026-06-11

**Status**: Draft

**Input**: User description: "Save full provider authorization as a separate feature or include it when setting up authorization properly."

## Clarifications

### Session 2026-06-11

- Decision: Track full provider authorization as a separate feature, not inside `014-desktop-upload-queue`.
- Decision: `014` may keep an env-only bearer bridge for production smoke, but user-facing upload must later consume a first-party 2brain Rec session token from this feature.
- Decision: Raw provider tokens must not become the uploader credential. The backend exchanges provider proof for scoped 2brain Rec auth/session/device credentials.
- Decision: Email sign-in fallback and account linking are tracked separately in `029-email-auth-account-linking`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sign In With Approved Provider (Priority: P1)

As a macOS user, I want to sign in through an approved identity provider so that the desktop app can securely connect my recordings to my 2brain Rec workspace.

**Why this priority**: Desktop upload, retention, deletion, and workspace scoping cannot be trusted until the app has a verified user/session context.

**Independent Test**: Start with a signed-out app, complete provider sign-in, and confirm the app shows a verified workspace/session state without exposing provider secrets.

**Acceptance Scenarios**:

1. **Given** the user is signed out, **when** they complete provider sign-in, **then** the app receives a 2brain Rec session state and can identify the active workspace.
2. **Given** provider sign-in is canceled, **when** the app returns to the main surface, **then** capture remains locally available where policy permits and upload stays blocked with a clear sign-in action.
3. **Given** the provider account is not allowed for the workspace, **when** sign-in completes at the provider, **then** the backend denies workspace access and the desktop shows a safe, non-recording-specific error.

---

### User Story 2 - Store And Refresh First-Party Session Safely (Priority: P1)

As a returning user, I want the app to stay signed in safely so that queued uploads can continue without repeatedly asking me to authenticate.

**Why this priority**: Upload queue reliability depends on auth refresh, but storing long-lived or raw provider credentials in local app state would violate project security rules.

**Independent Test**: Sign in, quit and relaunch the app, then confirm the app can refresh its 2brain Rec session using secure local storage and without writing tokens to diagnostics or queue metadata.

**Acceptance Scenarios**:

1. **Given** the user has a valid stored session, **when** the app launches, **then** it restores signed-in state from secure OS storage and does not require manual token entry.
2. **Given** the access token expires, **when** refresh is still allowed, **then** the app obtains a new first-party access token without losing local queue state.
3. **Given** refresh fails or the device is revoked, **when** upload needs auth, **then** uploads move to an auth-blocked state and local artifacts remain retained.

---

### User Story 3 - Authorize Uploads From Verified Session Context (Priority: P1)

As a security owner, I want upload API calls authorized from verified backend session/device state so that desktop-controlled headers cannot impersonate another user, device, organization, or workspace.

**Why this priority**: `014` currently uses explicit identity headers for smoke and local tests; user-facing production must derive identity from verified auth.

**Independent Test**: Attempt upload with mismatched or missing desktop identity headers while a valid session exists; confirm the backend trusts the verified token/session scope and rejects unauthorized scope changes.

**Acceptance Scenarios**:

1. **Given** the app has a valid 2brain Rec access token, **when** upload requests are sent, **then** the backend derives user, workspace, organization, and device from verified session context.
2. **Given** a request tries to override workspace or device identity with client-controlled headers, **when** the backend authorizes it, **then** the override is ignored or rejected.
3. **Given** the app receives `401` or `403` during upload, **when** the queue handles the response, **then** the item becomes auth-blocked/recoverable and is not deleted or marked uploaded.

---

### User Story 4 - Logout, Revocation, And Audit Truth (Priority: P2)

As a workspace owner, I want logout and device revocation to be truthful and auditable so that access can be stopped without falsely claiming local recording deletion.

**Why this priority**: Auth state participates in deletion, retention, and incident response, but it must not overpromise erasure outside controlled storage.

**Independent Test**: Revoke a device or log out from the app, then confirm upload stops, secure credentials are removed, audit metadata is recorded, and local artifacts remain governed by retention/deletion policy.

**Acceptance Scenarios**:

1. **Given** the user logs out, **when** the app clears session state, **then** secure local auth material is removed and queued uploads stop automatic network attempts.
2. **Given** an admin revokes a device, **when** the desktop next contacts the server, **then** the app enters a re-auth/re-enroll state and records metadata-only audit evidence.
3. **Given** logout occurs while local recordings exist, **when** the app reports status, **then** it does not claim those local artifacts were deleted unless deletion policy actually removed them.

## Edge Cases

- Provider login popup is canceled or times out.
- Provider login succeeds but backend exchange fails.
- User belongs to multiple organizations or workspaces.
- Provider account is valid but not a member of the selected workspace.
- Access token expires during a multi-part upload.
- Refresh token expires, is revoked, or is rotated by policy.
- Device credential is revoked while the app is offline.
- System clock skew causes token validity ambiguity.
- Keychain item is missing, locked, corrupted, or inaccessible after OS migration.
- Network is unavailable during login, refresh, or logout.
- User signs into a different provider account than the currently linked workspace account.
- Diagnostics, crash reports, logs, queue state, or evidence accidentally receive auth-looking fields.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The app MUST support sign-in through an approved external identity provider and complete backend exchange into a first-party 2brain Rec session.
- **FR-002**: Raw provider access tokens, refresh tokens, authorization codes, and ID tokens MUST NOT be used as desktop upload credentials.
- **FR-003**: The backend MUST issue scoped first-party session/device credentials for desktop API calls after provider proof is verified.
- **FR-004**: The desktop app MUST store reusable auth material only in secure OS credential storage and MUST NOT persist it in queue JSON, UserDefaults, logs, diagnostics, screenshots, or Spec Kit evidence.
- **FR-005**: The desktop upload queue MUST obtain authorization through an auth/session manager rather than direct environment variables in user-facing production mode.
- **FR-006**: The env-only bearer bridge from `014-desktop-upload-queue` MUST be treated as production-smoke-only and replaced before user-facing production rollout.
- **FR-007**: Upload requests MUST include first-party authorization suitable for the Rec API and MUST NOT require users to paste bearer tokens into the app.
- **FR-008**: The backend MUST derive user, workspace, organization, and device scope from verified auth/session context, not from desktop-controlled identity headers alone.
- **FR-009**: The app MUST classify auth failures separately from network, server validation, local resource, and storage quota failures.
- **FR-010**: When auth expires or is revoked during upload, queued items MUST remain recoverable/auth-blocked and local artifacts MUST remain retained until explicit retention/deletion policy acts.
- **FR-011**: The app MUST provide a clear re-auth action when upload or workspace sync is blocked by auth state.
- **FR-012**: Logout MUST remove local auth material and stop automatic authenticated network actions without claiming local recordings are deleted.
- **FR-013**: Device enrollment, device rotation, and device revocation MUST have metadata-only audit events.
- **FR-014**: Diagnostics and audit exports MUST redact auth headers, provider tokens, first-party tokens, refresh tokens, device credentials, session IDs when sensitive, and live credential paths.
- **FR-015**: The feature MUST support multiple workspace membership outcomes: allowed, denied, requires selection, and requires admin action.
- **FR-016**: The app MUST preserve manual capture controls and visible capture state regardless of signed-in/signed-out upload status where workspace policy permits local recording.

### Key Entities *(include if feature involves data)*

- **AuthSession**: Current signed-in state, expiry, workspace scope, and re-auth status for the desktop app.
- **ProviderIdentity**: Backend-verified external identity link without storing raw provider secrets in desktop state.
- **DeviceCredential**: First-party device-scoped credential or enrollment record used to authorize desktop API calls.
- **WorkspaceMembershipScope**: Organization/workspace/user/device authorization boundary derived from backend truth.
- **TokenRefreshEvent**: Metadata-only refresh attempt outcome, reason, and next required action.
- **AuthFailureState**: User-visible failure classification such as signed-out, expired, revoked, denied, or provider-unavailable.

## Out of Scope *(mandatory)*

- Changing recording start/stop semantics or visible capture indicator rules.
- Direct provider-token upload to Rec ingest, MediaScribe, MinIO, or Langfuse.
- Meeting transcription, notes, dashboard, or sharing features.
- Replacing the `014` upload queue state machine except for consuming proper auth state.
- Admin organization provisioning and billing.
- Long-term enterprise SSO policy design beyond the approved provider login/session boundary for this slice.
- Email-based sign-in fallback and account linking; tracked separately in `029-email-auth-account-linking`.

## Dependencies *(mandatory)*

- `012-server-ingest-foundation` for authenticated Rec API boundaries.
- `014-desktop-upload-queue` for upload retry/auth-blocked behavior that will consume this session state.
- `029-email-auth-account-linking` for email fallback and linking provider/email identities into the same first-party session boundary.
- Existing constitution rules for secret discipline, owner-controlled egress, visible capture, diagnostics, retention, and deletion truth.
- A backend account/workspace/device model capable of verifying provider identity and issuing first-party session/device scope.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of successful sign-ins produce a first-party 2brain Rec session without exposing raw provider tokens to queue state, diagnostics, or evidence.
- **SC-002**: 100% of upload API calls in user-facing production mode are authorized by first-party session/device context rather than manually pasted bearer tokens.
- **SC-003**: 100% of expired or revoked auth states move upload queue items into recoverable auth-blocked state without deleting local artifacts.
- **SC-004**: 0 diagnostics, logs, queue files, or Spec Kit evidence artifacts contain bearer tokens, provider tokens, refresh tokens, device credentials, signed URLs, passwords, or live credential paths.
- **SC-005**: At least 95% of returning users with valid secure credentials restore signed-in state without manual token entry.
- **SC-006**: 100% of logout and revocation flows record metadata-only audit truth and avoid claiming local artifact deletion unless deletion actually occurred.

## Assumptions

- The feature is provider-neutral at specification time; concrete provider order and configuration can be finalized during clarification/planning.
- macOS desktop auth should use a system/browser-mediated login flow rather than embedded password collection.
- First-party Rec API credentials are short-lived or revocable and scoped to user/workspace/device.
- Keychain or equivalent secure OS credential storage is available on the MVP macOS target.
- The current `014` env bearer path remains allowed only for internal production smoke until this feature supersedes it.
