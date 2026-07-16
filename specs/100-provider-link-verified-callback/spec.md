# Feature Specification: Provider Link Verified Callback

**Feature Branch**: `100-provider-link-verified-callback`
**Created**: 2026-07-09
**Status**: Draft
**Input**: User description: "Security finding: Provider link trusts caller subject. Нужно не чинить точечно, а сделать отдельную 100-фичу и продумать безопасный flow привязки внешнего провайдера к существующему аккаунту."

## Implementation Note

The 090 security closeout changed the deprecated direct `/api/v1/auth/link`
compatibility endpoint to fail safe: authenticated callers may no longer create
or verify an external identity from a request body containing
`candidate_provider_subject`. The route records a metadata-only rejected audit
event and returns `provider_link_requires_verified_callback`.

That hotfix removes the immediate raw-subject trust boundary. It does not
complete 100: the user-facing ability to add a new provider to an existing
account still needs the verified callback/link-intent flow described below.

## Clarifications

### Session 2026-07-16

- Q: Must every verified callback require an explicit GRAF confirmation before linking? → A: Yes. A callback alone never links a provider identity.
- Q: Who may start a link and where is the first user surface? → A: An active member using the current authenticated session may link an enabled provider from browser Settings; the embedded desktop cabinet reuses that server-owned surface.
- Q: What happens to verified data before and after confirmation? → A: The callback stores a short-lived pending candidate only. It neither creates an identity nor changes the GRAF session; terminal or expired intents remove candidate claims while retaining metadata-only audit status.

## Product Context

GRAF supports external provider authentication such as Yandex, VK, Telegram or future identity providers. The normal login/signup callback flow already has the right trust direction: the server starts a provider flow, receives a callback, verifies provider claims and then treats the provider subject as verified.

The security review found a separate provider-link path with a weaker trust boundary. In that path, an authenticated client can submit a candidate provider subject and candidate contact fields. The server may then create or consider a verified external identity from values that originated in client JSON rather than from a verified provider callback.

This is not a calendar integration issue. It is account/auth linking:

- Calendar linking connects recordings with calendar events or calendar sources.
- Provider linking connects a GRAF user account with an external identity provider account.

The product requirement is simple: a user must be able to link another external provider account to their existing GRAF account, but the provider identity must be proven by the provider, not by a browser or app payload.

## Security Problem

The current risky shape is:

1. User is authenticated in GRAF.
2. Client calls provider-link endpoint.
3. Request body includes candidate provider, provider subject and optional email/phone/display name.
4. Server may treat that candidate subject as verified identity material.
5. A verified external identity can be created without a fresh provider callback proving control of that provider account.

The broken boundary is not merely "missing validation". The issue is that the client is allowed to supply the identity proof itself. Validation cannot make this safe because the server still lacks proof that the user controls that external account.

## Required Product Direction

Provider linking must become a verified callback flow:

1. User is already logged into GRAF.
2. User chooses to link a provider from account/settings.
3. Server creates a short-lived, one-time link intent bound to the current user, workspace and session.
4. User completes the provider auth/callback.
5. Server verifies the provider callback and obtains provider subject/contact claims from the provider adapter.
6. Server creates a pending verified link candidate for the current user.
7. User confirms the link in GRAF.
8. Server creates or reuses the external identity only after both conditions are true:
   - current GRAF account/session is valid;
   - provider callback proved control of the external provider account.

This must not break ordinary provider login/signup. Login/signup and link must be separate intent types, even if they share some provider callback infrastructure.

## Product Principles For 100

- **Provider proves provider identity**: `provider_subject` is trusted only after verified provider callback.
- **Client does not prove identity**: frontend/mobile/desktop may initiate or confirm, but cannot assert verified provider subject.
- **Two-sided control**: linking requires control of the current GRAF session and control of the external provider account.
- **Login is not link**: existing provider login/signup behavior must keep working, but link intent must not silently log in as another account.
- **No auto-merge**: matching email/phone is not enough to merge users or attach another user's identity.
- **Idempotent success**: linking an already-linked provider account to the same user should be safe and repeatable.
- **Conflict is explicit**: provider identity already owned by another user is a conflict, not an automatic merge.
- **Short-lived state**: link intents and pending candidates must expire and be one-time-use.
- **Metadata-only audit**: audit and diagnostics must not log raw provider subject, tokens, provider payloads, authorization codes or session tokens.
- **Compatibility with migration**: existing users and already-linked identities should keep working.

## Current-State Correction

This feature should supersede the direct provider-link request shape where client-provided candidate identity fields are treated as proof.

The future implementation should preserve or migrate the user-facing ability to link a provider, but the trusted source of identity fields must move from request body to verified callback result.

It is acceptable for a transitional release to keep an old route name or compatibility response, but the old behavior must not be able to create or verify identities from raw client-supplied provider subjects.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Link a new provider safely (Priority: P1)

As an existing GRAF user, I want to link another external provider to my account, so I can sign in with that provider later without creating a duplicate account.

**Why this priority**: This is the legitimate user value behind the risky endpoint. The fix must preserve the useful behavior while changing the trust boundary.

**Independent Test**: Start from an authenticated GRAF session, initiate provider link, complete verified provider callback, confirm the link, then verify that the provider appears as linked for the same user.

**Acceptance Scenarios**:

1. **Given** an authenticated user starts provider linking, **When** the server creates a link intent, **Then** the intent is bound to that user, workspace and current session.
2. **Given** a user completes the provider callback for a link intent, **When** the provider claims verify successfully, **Then** the system creates a pending verified link candidate instead of trusting client-entered subject data.
3. **Given** the pending verified link candidate belongs to the current user/session, **When** the user confirms, **Then** the provider identity is linked to the same GRAF user.
4. **Given** the linked provider is later used for login, **When** the user signs in with that provider, **Then** GRAF resolves to the same user account.

---

### User Story 2 - Reject raw subject linking (Priority: P1)

As a security owner, I want the system to reject any attempt to create a verified external identity from raw client-supplied provider subject, so attackers cannot claim ownership of an external account by guessing or injecting an identifier.

**Why this priority**: This is the core security finding. A patch that preserves raw subject trust does not close the issue.

**Independent Test**: Call the old/direct link path or equivalent request with a candidate provider subject and no verified callback. Confirm that no external identity is created.

**Acceptance Scenarios**:

1. **Given** a client submits provider subject, email or phone directly to a link action, **When** no verified link candidate exists, **Then** the system rejects the request and does not create an external identity.
2. **Given** a client modifies provider subject in a request body after callback, **When** confirmation runs, **Then** the server ignores client-provided identity claims and uses only the stored verified candidate.
3. **Given** a malformed or missing link intent is supplied, **When** the user tries to confirm, **Then** the system returns a safe failure and records metadata-only audit.

---

### User Story 3 - Preserve ordinary provider login/signup (Priority: P1)

As a user who signs in with Yandex/VK/Telegram, I want existing provider login/signup to continue working, so the security fix does not break normal access to GRAF.

**Why this priority**: The risky link path is separate from ordinary login. Fixing it must not block legitimate provider authentication.

**Independent Test**: Run existing provider start/callback login scenarios before and after the change. Existing users can log in, invited users can enroll when policy allows, and denied users remain denied.

**Acceptance Scenarios**:

1. **Given** a normal login intent is started, **When** provider callback succeeds, **Then** the existing login/signup policy flow applies.
2. **Given** a link intent is started, **When** provider callback succeeds, **Then** it does not silently create a new login session as another account.
3. **Given** provider self-enrollment is disabled, **When** an uninvited new external identity attempts normal login, **Then** existing workspace enrollment policy still denies or requires invitation as before.
4. **Given** a provider is disabled by workspace policy, **When** login or link is attempted, **Then** both flows deny that provider consistently.

---

### User Story 4 - Handle conflicts without unsafe account merge (Priority: P1)

As a security-conscious admin, I want provider identity conflicts to be explicit, so one user cannot accidentally or maliciously attach an identity already belonging to another user.

**Why this priority**: Account-link conflict handling is where unsafe auto-merge bugs commonly appear.

**Independent Test**: Seed provider identity owned by another user, then attempt verified link from a different user. Confirm conflict and no ownership change.

**Acceptance Scenarios**:

1. **Given** the verified provider subject is already linked to the same user, **When** the user confirms linking again, **Then** the operation succeeds idempotently without duplicate identity rows.
2. **Given** the verified provider subject is linked to another user, **When** the current user confirms linking, **Then** the system returns a conflict and does not move the identity.
3. **Given** provider callback returns email or phone matching another user, **When** the subject is not already linked to the current user, **Then** the system does not auto-merge users or attach another user's identity.
4. **Given** multiple candidate users share email/phone-like contact data, **When** link confirmation runs, **Then** the system requires explicit conflict handling outside this automatic flow.

---

### User Story 5 - Expired, reused or cross-session link attempts are denied (Priority: P1)

As a user, I want provider linking to be safe even if browser tabs, refreshes or old links are reused, so stale state cannot attach identities to the wrong account.

**Why this priority**: Link state is sensitive. Reuse and cross-session mistakes are common in OAuth-like flows.

**Independent Test**: Try confirming expired, already-used, wrong-session, wrong-user and wrong-workspace link candidates. All are rejected without creating identities.

**Acceptance Scenarios**:

1. **Given** a link intent expired, **When** callback or confirmation occurs, **Then** the system rejects it and no identity is created.
2. **Given** a link intent was already completed, **When** callback or confirmation is replayed, **Then** the system rejects replay and no duplicate identity is created.
3. **Given** link intent was started by user A, **When** user B attempts to confirm it, **Then** the system rejects the action.
4. **Given** link intent belongs to one workspace, **When** confirmation is attempted in another workspace, **Then** the system rejects the action.
5. **Given** a user opens multiple tabs, **When** one tab completes linking, **Then** other tabs observe completed/rejected state without creating duplicates.

---

### User Story 6 - Audit and diagnostics stay metadata-only (Priority: P2)

As an operator, I want to understand provider link attempts and failures without exposing secrets or identity payloads in logs, so support and security review remain safe.

**Why this priority**: Auth flows often contain sensitive codes, tokens, provider subjects and contact claims.

**Independent Test**: Execute successful, conflict, denied, expired and replayed link attempts. Audit contains event type, outcome and safe fingerprints/status only.

**Acceptance Scenarios**:

1. **Given** link start succeeds, **When** audit is written, **Then** it records safe metadata but not raw state nonce, authorization code, provider subject or token.
2. **Given** provider callback succeeds, **When** audit is written, **Then** it may include a fingerprint but not raw provider subject or raw provider payload.
3. **Given** link confirmation fails, **When** support reviews logs, **Then** logs show reason code without exposing raw provider identity data.

## Edge Cases

- User starts link flow but never returns from provider.
- User starts two link flows for the same provider in two tabs.
- User starts link for provider A but callback arrives for provider B.
- Provider callback succeeds but user closes browser before confirmation.
- Provider callback returns contact claims that differ from the current user's existing identity.
- Provider callback returns no email or no phone.
- Provider callback returns unverified or provider-limited contact fields.
- Provider subject is already linked to the same user.
- Provider subject is already linked to another user in same organization.
- Provider subject is already linked to another user in another organization.
- Email/phone matches another workspace member but subject is new.
- Workspace provider policy changes between link start and callback.
- User loses workspace membership between link start and confirmation.
- User session expires between link start and confirmation.
- Link state is replayed after success.
- Link state is replayed after failure.
- Old direct link clients still send candidate provider subject.
- Legacy tests or internal tools use direct link request shape.
- Audit redaction must hide raw provider subject, provider payload, authorization code, state nonce, session token and cookies.
- Existing linked identities must keep working after migration.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST NOT create a verified external identity from a provider subject supplied directly by a client request body.
- **FR-002**: Provider linking MUST require a verified provider callback before any new provider subject can be linked to a user.
- **FR-003**: Provider linking MUST require an authenticated GRAF user/session before a link intent can be created.
- **FR-004**: Link intent MUST be bound to initiating user, workspace and current session or equivalent authenticated context.
- **FR-005**: Link intent MUST be short-lived and one-time-use.
- **FR-006**: Link callback MUST distinguish link intent from normal login/signup intent.
- **FR-007**: Link callback MUST NOT silently create or switch to a different GRAF account.
- **FR-008**: Every verified callback MUST require an explicit GRAF confirmation before linking; confirmation MUST use the server-stored verified provider candidate, not identity claims supplied in the confirm request.
- **FR-008a**: A link callback MUST NOT create an external identity, create or switch a GRAF user, issue a session, or return a GRAF session token before the explicit confirmation.
- **FR-008b**: Confirmation MUST be an authenticated, CSRF-protected state-changing action that accepts only an opaque server-issued intent identifier; it MUST require the initiating active session, user and workspace.
- **FR-009**: If the provider subject is already linked to the same user, confirmation MUST be idempotent and MUST NOT create duplicate active identities.
- **FR-010**: If the provider subject is already linked to another user, confirmation MUST fail with an explicit conflict and MUST NOT transfer ownership.
- **FR-011**: Matching email, phone, display name or provider username MUST NOT be sufficient to create a verified provider identity.
- **FR-012**: Provider policy MUST be checked for both link start and callback/confirmation so disabled providers cannot be linked.
- **FR-013**: Workspace membership or equivalent account authority MUST be checked before link start and before final confirmation.
- **FR-014**: Expired, reused, wrong-user, wrong-session and wrong-workspace link states MUST be rejected.
- **FR-015**: Existing ordinary provider login/signup MUST continue to work according to current workspace enrollment policy.
- **FR-016**: Old/direct link behavior MUST be removed or changed so it cannot create external identities from raw client-supplied subjects.
- **FR-017**: Compatibility responses for old clients MUST fail safely with a clear error that instructs clients to use verified link flow.
- **FR-018**: Audit events MUST distinguish link started, callback verified, confirmation completed, conflict, expired, replayed and rejected states.
- **FR-019**: Audit, diagnostics, specs and validation evidence MUST NOT contain raw provider subject, provider payload, authorization code, state nonce, session token, cookies or live credentials.
- **FR-020**: Tests MUST cover direct subject rejection, verified callback linking, normal login preservation, conflict handling, state expiry/replay and audit redaction.
- **FR-021**: Pending verified candidate claims MUST be deleted or minimized when an intent is confirmed, rejected or expired; only metadata-only lifecycle evidence may remain.
- **FR-022**: Linking MUST NOT create a user, membership, enrolment, account merge, primary-provider change, or session change. An identity conflict response MUST not reveal the owning user or contact data.

### Key Entities *(include if feature involves data)*

- **UserAccount**: Existing GRAF user identity that owns sessions and linked providers.
- **ExternalProviderIdentity**: Verified account identity from an external provider. It includes provider and provider subject, but subject must originate from verified provider callback.
- **ProviderLoginIntent**: Existing provider start/callback state for normal login/signup.
- **ProviderLinkIntent**: Short-lived authenticated intent to link a provider to an existing GRAF user.
- **VerifiedProviderLinkCandidate**: Server-stored provider claims obtained from verified callback and awaiting user confirmation.
- **ProviderLinkConfirmation**: Final authenticated user action that converts a verified candidate into a linked external identity.
- **ProviderLinkAuditEvent**: Metadata-only audit event describing link lifecycle and safe status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of direct raw-subject link attempts fail without creating or modifying external identities.
- **SC-002**: 100% of new provider links are based on provider subjects obtained from verified provider callback.
- **SC-003**: 100% of link confirmations validate user, workspace and session ownership before linking.
- **SC-004**: 0 normal provider login/signup contract tests regress because of the link-flow change.
- **SC-005**: 100% of same-user duplicate link attempts are idempotent and produce no duplicate active external identities.
- **SC-006**: 100% of cross-user provider subject conflicts fail without identity transfer or auto-merge.
- **SC-007**: 100% of expired/replayed/wrong-session link attempts fail safely.
- **SC-008**: 0 audit logs, diagnostics, specs or validation evidence contain raw provider subjects, authorization codes, provider payloads, state nonces, session tokens, cookies or live credentials.
- **SC-009**: 100% of old direct-link clients receive a clear safe error instead of a partially successful insecure link.

## Assumptions

- Existing provider callback verification remains the authority for provider subject truth.
- Existing provider login/signup should stay available and should not be redesigned in this feature except where necessary to separate login intent from link intent.
- Existing linked provider identities remain valid unless they are already invalid by separate policy.
- Email/phone matching is useful as conflict/context signal, but not as identity proof.
- Implementation should prefer minimal changes to existing auth state and audit patterns while fully removing raw-subject trust.
- UI can tolerate a two-step link flow: start provider auth, then confirm linking after callback.

## Dependencies *(mandatory)*

- Existing provider start/callback auth flow.
- Existing external identity uniqueness model.
- Existing auth session and workspace membership checks.
- Existing provider policy settings for enabled/disabled providers.
- Existing auth audit redaction rules.
- Future `097-workspace-account-onboarding` may adjust account/workspace semantics; 100 must preserve whichever membership authority is current when implemented.

## Out Of Scope *(mandatory)*

- Calendar account linking or calendar event matching.
- Enterprise SSO/SAML/SCIM.
- Full account merge UX.
- Automatic merging based on email, phone or display name.
- Changing provider-specific OAuth contracts unless required for verified link callback.
- Deleting or migrating existing valid linked identities.
- Reworking all login/signup onboarding policy beyond the link trust-boundary fix.

## Clarifications Needed Before Implementation

None. The 2026-07-16 clarification and planning decisions retain the existing
safe legacy response for one release, extend the existing provider-link state,
use the shared browser/embedded Settings surface, and permit an active member
to link an enabled provider using the initiating session.
