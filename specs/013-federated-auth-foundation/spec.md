# Feature Specification: Provider-Neutral Federated Authentication with RU-Local Identity & Device Sessions

**Feature Branch**: `013-federated-auth-foundation`

**Created**: 2026-06-10

**Status**: Implemented

**Input**: User description: "Fix current docs and implement feature 013: one-click auth for Russian users via local-friendly providers, privacy and data localization, and account/device unification across multiple providers."

## Actors and Context

- **Participant**: Russian workspace user (employee or operator) who joins a workspace that has a compliance requirement for personal data handling in Russia.
- **System Admin**: workspace operator who manages workspace identity policy and available providers.
- **Desktop Client**: existing 2brain Rec desktop app that needs identity continuity for future upload flows.
- **Service**: 2brain Rec backend API currently using header-based identity context.

This feature is specifically for identity/session foundation; it does not replace transport encryption, MediaScribe protocol, or transcription capture behavior.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — One-click auth in Russian workspace (Priority: P1)

A user can authenticate in one click using a configured Russian-friendly provider without manual credential entry.

**Why this priority**: This is the core user activation path for all future usage in Russian enterprises.

**Independent Test**: A workspace user with no prior 2brain account can choose `Yandex ID`, `VK ID`, or `Telegram Login` on first visit and open a valid workspace session.

**Acceptance Scenarios**:

1. **Given** a workspace has an enabled provider, **When** the user clicks that provider button, **Then** they are redirected to provider consent and return to an authenticated workspace session within 2 minutes.
2. **Given** the same workspace has multiple enabled providers, **When** a user signs in with any enabled provider, **Then** no separate 2brain password is required and the returned account is in a 2brain workspace context.
3. **Given** a workspace is Russia-localized by policy, **When** sign-in completes, **Then** session is bound to allowed data boundary and stored in approved RU infrastructure.

### User Story 2 — Duplicate provider identity merges for same human (Priority: P1)

A single person using multiple provider identities should be able to treat these identities as one user account in the same workspace.

**Why this priority**: Prevents account fragmentation and reduces support churn for enterprise users.

**Independent Test**: A user who previously logged in via Yandex can explicitly link VK and Telegram identities and then authenticate with any linked provider and access the same workspace permissions.

**Acceptance Scenarios**:

1. **Given** an active authenticated session exists, **When** the user opens link flow for a second provider, **Then** the new external identity is attached to the same internal user profile after explicit confirmation.
2. **Given** a second provider claim appears to match an existing verified phone/email already linked, **When** user confirms ownership, **Then** the system performs a verified link automatically and prevents duplicate accounts.
3. **Given** a conflicting identity exists for another workspace user, **When** verification cannot prove ownership, **Then** the system creates a separate user record and provides safe conflict resolution.

### User Story 3 — Device registration and workspace session continuity (Priority: P1)

A workspace should register trusted desktop devices and issue workspace-scoped upload identity proofs without exposing provider secrets.

**Why this priority**: This prepares `014` and prevents direct provider token handling in clients.

**Independent Test**: A linked user can register a desktop device, receive a workspace session proof, and later re-authenticate that device without repeating provider login where policy allows.

**Acceptance Scenarios**:

1. **Given** a logged-in user opens settings, **When** they register a macOS device, **Then** the service stores a device record with ownership and optional trust level.
2. **Given** the device is revoked, **When** the app reuses it, **Then** API refuses ingest token flow and prompts re-login.
3. **Given** device trust is not required, **When** login completes via provider, **Then** registration starts in untrusted state until approved by workspace policy.

### User Story 4 — Workspace policy for provider availability and data residency (Priority: P2)

Workspace admins can enable/disable providers and set RU-residency rules so that auth processing and profile/session/device/audit data obey policy.

**Why this priority**: This enforces legal and operational controls needed for Russian markets.

**Independent Test**: An admin disables `Telegram Login` and enables `Yandex ID` only for a workspace; users can see only enabled provider options.

**Acceptance Scenarios**:

1. **Given** a workspace has restricted providers, **When** admin changes list, **Then** unsupported provider buttons are hidden for all users in that workspace.
2. **Given** residency policy requires RU-local storage, **When** user data is updated, **Then** data and session metadata are written to RU-configured stores only.
3. **Given** provider policy is changed during a session, **When** the change takes effect, **Then** existing sessions remain safe, and future sessions are evaluated against the new policy.

### User Story 5 — Safe failure and recovery visibility (Priority: P2)

Users and admins see clear state when auth or linkage fails and can recover without account takeover risk.

**Why this priority**: Auth failures and mismatches are common in multi-provider flows and must be safe and understandable.

**Independent Test**: A user who had provider outage, cancelled login, or conflict scenario gets a deterministic outcome and next step.

**Acceptance Scenarios**:

1. **Given** provider callback is unavailable, **When** login attempt is initiated, **Then** service reports provider unavailable and keeps the user in a recoverable state.
2. **Given** callback state mismatch is detected, **Then** service rejects callback and logs a security event without logging sensitive claims.
3. **Given** an existing workspace token expires or device is lost, **When** user returns, **Then** user is guided to re-login and revoke stale sessions.

### User Story 6 — Transparent consent and auditability in Russian market (Priority: P3)

Users and admins can see what provider profile fields are collected and what is stored locally.

**Why this priority**: Clarifies legal and compliance expectations before onboarding at scale.

**Independent Test**: User can view concise auth/data-processing copy before linking and admin can inspect audit records for auth and linking events.

**Acceptance Scenarios**:

1. **Given** a user opens provider flow, **When** consent details are shown, **Then** they receive notice of external provider claims used and fields stored locally.
2. **Given** auth operations occur, **When** each operation completes, **Then** a redacted audit record exists with actor, workspace, provider, and decision outcome.
3. **Given** a privacy review occurs, **When** records are queried, **Then** raw tokens/claims are not stored in logs while required policy proof fields remain.

### Edge Cases

- Provider returns no verified email/phone and the system cannot safely auto-match to an existing account.
- Telegram profile data may omit email; phone data may be stale or hidden depending on user privacy settings.
- Same phone/email appears on an inactive or revoked internal identity.
- User starts linking provider in workspace A while callback lands with workspace B context.
- Provider account was soft-deleted or changed claims between authorization request and callback.
- User cancels or closes provider window mid-flow.
- Replay attack or CSRF state mismatch on callback.
- Provider outage or timeout while callback is pending.
- Workspace-local residency policy disallows provider-specific claims currently configured as mandatory.
- Device is duplicated (same hardware identity) across users and must not auto-assign.
- Duplicate external identity attempts for different users.
- Time drift between auth service and provider callback validation window.
- Legacy header-based session from previous implementation attempts to access new auth-protected endpoints.

## Clarifications (resolved)

- **Provider scope in MVP:** The MVP includes `Yandex ID`, `VK ID`, and `Telegram Login` as enabled provider families. `T-ID`, `Sber ID`, `MTS ID` are supported as configurable adapters and can be enabled later after the same policy framework is stable.
- **Russian account linking rule:** Safe automatic linking is only allowed after explicit user confirmation or deterministic verified-field matching from an active workspace session. Silent auto-merge without confirmation is not allowed.
- **Data residency default:** For RU-local workspaces, auth profile data, external-identity records, auth sessions, device registrations, and auth audit events are stored only in RU-controlled infrastructure. Raw provider tokens/claims are not logged and are minimized in persistence to policy proof only.
- **One-click UX definition:** One-click is satisfied when a user can authenticate by selecting one enabled provider button and returning to active workspace session; multi-factor or password entry is not introduced for this feature.
- **Fallback behavior:** The feature includes explicit visible failure and retry states for provider outage, cancelled consent, CSRF/replay mismatch, and conflict. A disabled provider is not shown.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support at least `Yandex ID`, `VK ID`, and `Telegram Login` as provider options for Russian-market users.
- **FR-002**: The system MUST allow workspace-scoped provider enable/disable configuration, and only enabled providers can be presented to users in that workspace.
- **FR-003**: The system MUST maintain a stable internal user identity that is independent of provider subject values.
- **FR-004**: The system MUST map provider identities using a unique `(provider, provider_subject)` identity tuple.
- **FR-005**: The system MUST support explicit account linking for authenticated sessions and approved fallback linking via verified matching fields.
- **FR-006**: The system MUST not merge two unconfirmed identities without explicit operator/user confirmation.
- **FR-007**: The system MUST record provider linking events and session/device actions in auditable redacted logs.
- **FR-008**: The system MUST support registered desktop devices with owner, fingerprint, status, trust level, and revocation support.
- **FR-009**: The system MUST support device de-registration and denial of ingest for revoked devices.
- **FR-010**: The system MUST block ingest for unknown/untrusted devices unless configured as allowed by workspace policy.
- **FR-011**: The system MUST rotate and invalidate workspace sessions according to existing session policies and logout/revoke events.
- **FR-012**: The system MUST enforce RU-local storage for personal, auth, and audit data for workspaces marked RU-local.
- **FR-013**: The system MUST never store raw provider OAuth tokens, secrets, or full claim payloads in diagnostics or application logs.
- **FR-014**: The system MUST redact token-like values and personal data from logs and expose only required policy fields.
- **FR-015**: The system MUST persist consent language indicating processed fields and storage location before final account link.
- **FR-016**: The system MUST support clear provider-failure states: unavailable, cancelled, timeout, denied, and conflict.
- **FR-017**: The system MUST reject callback state mismatches and suspicious replay patterns.
- **FR-018**: The system MUST reject stale callback/state with explicit recovery guidance.
- **FR-019**: The system MUST prevent direct upload credentials in desktop client; only server-issued, short-lived session proofs may be used.
- **FR-020**: The system MUST preserve existing tenant/workspace authorization behavior for non-auth endpoints while introducing new auth provider flows.
- **FR-021**: `T-ID`, `Sber ID`, `MTS ID` MAY exist as configurable adapters but are out of MVP scope unless explicitly approved by legal/compliance.
- **FR-022**: ESIA/Gosuslugi authentication is out of MVP scope unless a regulated user explicitly requires it.
- **FR-023**: All auth/session/device operations MUST provide deterministic error reasons in user-visible copy and admin-visible audit entries.

### Non-functional Requirements

- **NFR-001**: Account linking and login completion target is under two minutes in normal network conditions.
- **NFR-002**: Auth audit retention and deletion metadata must align with existing deletion truth and data policy.
- **NFR-003**: Duplicate external claims must be detectable with a false positive risk suitable for enterprise onboarding.
- **NFR-004**: All auth endpoints must be resilient to malformed requests and continue to enforce fail-closed behavior.
- **NFR-005**: Russian-language explanatory text for auth and privacy notices is preferred for RU workspaces.

### Key Entities *(include if feature involves data)*

- **InternalUser**: Stable local user record used across providers.
- **ExternalIdentity**: `(provider, provider_subject)` record with provider metadata and verification status.
- **WorkspaceMembership**: Existing workspace membership and role context tied to InternalUser.
- **AuthSession**: Workspace-authenticated session with device context and expiry/rotation metadata.
- **RegisteredDevice**: Trusted desktop client identity and status lifecycle.
- **AuthAuditEvent**: Redacted event entries for login, logout, link, unlink, revoke, and failures.
- **WorkspaceAuthPolicy**: Allowed providers, consent settings, and residency mode.
- **LinkCandidate**: Proposed identity match before explicit user confirmation when auto-match is eligible.

### Out of Scope

- Desktop uploader implementation and desktop-side credential storage (already deferred).
- MediaScribe protocol changes and deletion execution jobs.
- Dashboard, invitation emails, or admin portal beyond auth-policy and audit visibility controls.
- Cross-platform mobile onboarding flows.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Over 95% of new RU-workspace users complete provider login and first session creation within two minutes.
- **SC-002**: Duplicate provider identities for the same verified user are resolved without creating duplicate internal users for all explicit linking and confirmed-match scenarios.
- **SC-003**: At least 100% of RU-local workspaces use RU-configured data stores for auth/session/device/audit write paths where configured.
- **SC-004**: Rejected callback mismatch/replay events and unauthenticated failures are always represented in audit trail within the same transaction path.
- **SC-005**: Revoked device sessions are denied within one request cycle of revoke event.
- **SC-006**: Disabled providers never appear in the user-visible sign-in options for the same workspace.
- **SC-007**: 100% of login or linking failures expose deterministic user-facing recovery path messages.
- **SC-008**: Existing tenant authorization behavior does not regress for header-based tenant-scoped API access where new auth session is not involved.

### Adoption Criteria (for release readiness)

- Workspace policy can be changed without code release.
- Russian users can sign in from desktop via at least one provider and immediately reach protected workspace flows.
- Linking flow is deterministic and cannot be abused for silent account takeover.

## Assumptions

- 2brain Rec MVP is deployed self-hosted for one or more RU-hosted infrastructure stacks with RU control over Postgres, object storage, logs, and backups.
- Provider credentials and secrets are managed on server side by workspace operators or deployment operator.
- Provider profile scope includes stable subject where available and may exclude direct email/phone for privacy-restricted users.
- Existing header-based tenant identity model remains supported for internal integrations during migration.
- Future feature `014-desktop-upload-queue` depends on this feature and can consume registered-device/session model when ready.
- Full legal final review is required before commercial rollout, but conservative RU-default rules are implemented now.
