# Feature Specification: Email Auth And Account Linking

**Feature Branch**: `029-email-auth-account-linking`

**Created**: 2026-06-11

**Status**: Draft

**Input**: User description: "External provider auth is not enough. If a user has no provider accounts, support email authorization and allow linking accounts."

## Clarifications

### Session 2026-06-11

- Decision: Track email authorization and account linking as a separate feature from `028-provider-auth-session`.
- Decision: Email auth is a first-class fallback for users who do not have, cannot use, or do not want to use an external provider account.
- Decision: Account linking must require proof of control for every identity being linked and must protect against accidental or malicious account takeover.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sign In With Email When No Provider Account Exists (Priority: P1)

As a user without an approved external provider account, I want to sign in with my email so that I can use 2brain Rec without being forced into Google/Apple/GitHub/SSO.

**Why this priority**: Provider-only auth blocks valid users and weakens onboarding for smaller teams or users with restricted identity-provider access.

**Independent Test**: Start from signed-out state, enter an email, complete email verification, and confirm the app receives a verified 2brain Rec session without any provider account.

**Acceptance Scenarios**:

1. **Given** the user has no linked provider account, **when** they verify email ownership, **then** they can access their allowed 2brain Rec workspace.
2. **Given** the user enters an unknown email, **when** signup is allowed by workspace policy, **then** the system creates or invites the account according to policy.
3. **Given** signup is restricted, **when** an unknown email attempts login, **then** the system shows a safe denial state and does not reveal whether the email belongs to another workspace.

---

### User Story 2 - Link Provider Accounts To Existing Email Account (Priority: P1)

As a user who started with email auth, I want to link an external provider later so that I can sign in through either method without creating duplicate accounts.

**Why this priority**: Users often start simple and later adopt SSO/provider login. Linking avoids duplicate identities, lost uploads, and workspace confusion.

**Independent Test**: Sign in with email, link a provider account after completing provider verification, sign out, sign back in with the provider, and confirm the same 2brain Rec user/workspace/device scope is used.

**Acceptance Scenarios**:

1. **Given** a signed-in email user, **when** they complete provider verification, **then** the provider identity links to the existing 2brain Rec user.
2. **Given** the provider email differs from the existing account email, **when** linking is requested, **then** the system requires explicit confirmation and workspace policy approval where required.
3. **Given** the provider identity is already linked to another 2brain Rec account, **when** linking is attempted, **then** the request is blocked or sent to a safe admin-mediated merge flow.

---

### User Story 3 - Link Email To Provider-First Account (Priority: P1)

As a user who first signed in through a provider, I want to add email login as a fallback so that I can recover access if the provider is unavailable or blocked.

**Why this priority**: Provider outage, organization policy changes, or personal account loss should not strand a legitimate user when email fallback is allowed.

**Independent Test**: Sign in through a provider, add an email identity, verify email control, then sign in with email and confirm the same account/session scope.

**Acceptance Scenarios**:

1. **Given** a provider-authenticated user, **when** they verify an email address, **then** email auth becomes available for the same 2brain Rec account.
2. **Given** email verification expires, **when** the user tries to finish linking, **then** linking fails safely and can be restarted.
3. **Given** the email is already used by another account, **when** linking is attempted, **then** automatic linking is blocked unless an approved merge/recovery flow confirms ownership and policy.

---

### User Story 4 - Manage Linked Accounts And Recovery Truth (Priority: P2)

As a user or workspace admin, I want to see and manage linked sign-in methods so that access remains understandable, revocable, and auditable.

**Why this priority**: Linked identity state affects account recovery, device revocation, incident response, and user trust.

**Independent Test**: Link two methods, remove one method, revoke a device/session, and confirm the UI and audit trail show truthful remaining access without exposing tokens.

**Acceptance Scenarios**:

1. **Given** multiple sign-in methods are linked, **when** the user views account security, **then** they can see provider/email method names and verification status without secret values.
2. **Given** the user removes a linked method, **when** at least one recovery/sign-in method remains, **then** the method is unlinked and future sign-in through it is denied.
3. **Given** unlinking would leave the account without any allowed sign-in method, **when** the user attempts removal, **then** the system blocks removal or requires adding another verified method first.

## Edge Cases

- Email delivery is delayed, blocked, or lands in spam.
- Verification link/code is expired, reused, brute-forced, or opened on another device.
- User enters a typo email that belongs to someone else.
- Provider email is unverified or hidden by provider policy.
- Provider account email changes after linking.
- Two users attempt to link the same provider identity or email.
- User belongs to multiple organizations or workspaces with different auth policies.
- Workspace disables email auth after a user already linked email.
- User loses provider access and uses email recovery.
- User loses email access and tries provider recovery.
- Admin revokes a linked identity while the desktop app is offline.
- Account merge is requested while upload queue items, devices, or audit records already exist.
- Diagnostics or evidence accidentally include verification codes, login links, session tokens, provider tokens, or email secrets.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support email-based sign-in as an alternative to external provider sign-in where workspace policy permits it.
- **FR-002**: Email auth MUST require proof of email control before issuing a first-party 2brain Rec session.
- **FR-003**: Email verification links/codes MUST be single-use, time-bounded, and safe against replay.
- **FR-004**: The system MUST NOT reveal whether an email address exists in another workspace when access is denied.
- **FR-005**: Users MUST be able to link an approved provider identity to an existing email-authenticated 2brain Rec account after proving control of both identities.
- **FR-006**: Users MUST be able to link a verified email identity to an existing provider-authenticated 2brain Rec account after proving email control.
- **FR-007**: The system MUST block automatic linking when the email or provider identity is already associated with another account unless a safe merge/recovery policy explicitly permits it.
- **FR-008**: Account linking MUST preserve existing workspace membership, device records, upload ownership, retention/deletion accounting, and audit traceability.
- **FR-009**: The system MUST prevent unlinking the last usable sign-in method unless an approved recovery or admin policy exists.
- **FR-010**: The system MUST provide metadata-only audit events for email verification, link, unlink, failed link, recovery, and merge decisions.
- **FR-011**: The desktop app MUST treat email-authenticated sessions the same as provider-authenticated first-party Rec sessions for upload authorization.
- **FR-012**: The upload queue MUST NOT care which auth method produced the first-party session; it only consumes verified session/device authorization from the auth layer.
- **FR-013**: Diagnostics, logs, queue state, screenshots, and Spec Kit evidence MUST NOT contain email verification codes, magic links, raw provider tokens, first-party tokens, refresh tokens, passwords, or live credential paths.
- **FR-014**: The UI MUST clearly distinguish sign-in method management from recording/capture state so auth changes do not imply local recording deletion or upload completion.
- **FR-015**: Admin or workspace policy MUST be able to disable email auth, require provider auth, or require admin approval for account linking where needed.
- **FR-016**: Account merge/linking flows MUST record truthful outcomes without silently moving recordings, devices, or audit records between accounts.

### Key Entities *(include if feature involves data)*

- **EmailIdentity**: Verified or pending email sign-in method associated with a 2brain Rec account.
- **ProviderIdentityLink**: External provider identity associated with a 2brain Rec account after verification.
- **AccountLinkRequest**: Pending request to attach email/provider identity to an existing account.
- **VerificationChallenge**: Time-bounded proof-of-control challenge for email or link confirmation.
- **LinkedAuthMethod**: User-visible sign-in method with type, status, created date, last used date, and revocation state.
- **AccountMergeDecision**: Admin/user-approved decision record for conflicts where two identities may belong to the same person.

## Out of Scope *(mandatory)*

- Full provider-auth session implementation already tracked in `028-provider-auth-session`.
- Password-based login unless a later feature explicitly chooses passwords.
- Enterprise SSO policy design beyond enabling/disabling email auth and linking approval.
- Billing, organization provisioning, or invite lifecycle beyond auth/linking decisions.
- Changing upload queue retry logic except for consuming verified first-party session state.
- Deleting local recordings as a side effect of unlink, logout, or account merge.

## Dependencies *(mandatory)*

- `028-provider-auth-session` for first-party session/device token behavior consumed by the desktop app.
- `014-desktop-upload-queue` for upload auth-blocked behavior when session state is unavailable.
- Backend account/workspace/device model capable of representing multiple linked sign-in methods.
- Constitution rules for secret discipline, deletion truth, diagnostics redaction, and owner-controlled data boundaries.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of email-authenticated sign-ins require successful email ownership proof before a Rec session is issued.
- **SC-002**: 100% of linked provider/email identities require proof of control for every linked method.
- **SC-003**: 0 account-linking flows automatically merge two existing accounts without an explicit approved conflict-resolution path.
- **SC-004**: 100% of auth methods shown in account security reflect current linked, pending, revoked, or blocked truth.
- **SC-005**: 100% of upload requests authorized after email login use the same first-party session/device boundary as provider-authenticated requests.
- **SC-006**: 0 diagnostics, logs, queue files, or evidence artifacts contain verification codes, magic links, auth tokens, provider tokens, refresh tokens, passwords, or live credential paths.
- **SC-007**: At least 95% of users who cannot use provider auth can complete email sign-in without manual support when workspace policy allows email auth.

## Assumptions

- Email auth should be passwordless by default unless a later spec explicitly chooses password login.
- Email deliverability, rate limiting, and abuse prevention are required planning topics before implementation.
- Linked identities belong to one canonical 2brain Rec account only after verified control and policy checks.
- The desktop app should not collect or store provider secrets, email verification secrets, or long-lived raw auth values.
- Account linking must preserve deletion/audit truth and must not silently reassign meeting ownership without evidence.
