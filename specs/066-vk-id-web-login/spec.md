# Feature Specification: VK ID Web Login

**Feature Branch**: `codex/066-vk-id-web-login`

**Created**: 2026-06-27

**Status**: Draft

**Input**: User description: "давай теперь сделаем VK"

## Clarifications

### Session 2026-06-27

- Scope decision: feature 066 enables the existing 013 VK ID backend for the browser web-cabinet login and registration surfaces. It does not rebuild the provider foundation and does not add a desktop-native OAuth flow.
- Credential decision: production rollout requires a VK app client ID, client secret, and registered callback URL `https://rec.2brain.pro/api/v1/auth/callback/vk`.
- Release decision: production deployment may proceed only after VK credentials are configured as server-side secrets.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sign In Through VK ID (Priority: P1)

A workspace user opens the web cabinet login page, chooses VK ID, completes VK consent, and returns to the requested cabinet page with a valid owner-session cookie.

**Why this priority**: This turns the already implemented provider backend into a usable login path. Without it, VK ID remains visible as a disabled "soon" option.

**Independent Test**: Start `/login/vk/start?next=/meetings`, verify the user is redirected to a VK authorization URL, then complete a callback with a verified provider profile in tests and confirm the cabinet session opens `/meetings`.

**Acceptance Scenarios**:

1. **Given** a workspace has VK ID enabled, **When** the user opens `/login`, **Then** the VK ID action is an active link to `/login/vk/start` and is not marked "скоро".
2. **Given** the user starts VK ID login with `next=/meetings`, **When** the start route succeeds, **Then** the browser receives a redirect to VK with a single-use callback state and a safe return path.
3. **Given** VK returns a verified callback, **When** the server accepts it, **Then** the browser receives the existing owner-session cookie and lands only on a safe first-party cabinet path.

---

### User Story 2 - Fail Closed With Email Fallback (Priority: P2)

A user who cannot use VK ID because the provider is disabled, missing, misconfigured, denied, or temporarily unavailable gets a safe, actionable login page and can still use email login.

**Why this priority**: Auth failures are security-sensitive and must not strand a user or leak provider details.

**Independent Test**: Simulate disabled provider, missing workspace, bad callback state, provider denial, and provider verification outage; each case returns bounded copy without raw provider data and leaves the email path visible.

**Acceptance Scenarios**:

1. **Given** VK is disabled by workspace policy, **When** the user opens `/login`, **Then** VK is hidden from active provider choices and email login remains available.
2. **Given** VK returns a denial or invalid callback state, **When** the browser returns to the cabinet, **Then** the user sees a generic recovery message and no token, code, subject, email, phone, or raw VK payload is exposed.

---

### User Story 3 - Configure Public Callback Truth (Priority: P2)

An operator configures the public auth base URL and VK credentials for the self-hosted cabinet so VK receives the registered public callback URL rather than an internal container or testserver URL.

**Why this priority**: VK OAuth depends on exact redirect URI matching and the provider-specific client ID/secret; a working button is not enough if callback or credentials are wrong behind the reverse proxy.

**Independent Test**: Configure `TWOBRAIN_AUTH_BASE_URL=https://rec.2brain.pro`, start VK login, and verify the generated `redirect_uri` is `https://rec.2brain.pro/api/v1/auth/callback/vk` and the authorization URL uses the VK client ID.

**Acceptance Scenarios**:

1. **Given** a public auth base URL is configured, **When** VK start flow builds its callback URL, **Then** the callback URL uses the configured public origin plus the VK callback path.
2. **Given** no public auth base URL is configured in local tests, **When** the flow starts, **Then** existing request-derived local URLs continue to work.
3. **Given** production starts with VK enabled, **When** the runtime validates provider secrets, **Then** missing or empty VK secret files fail closed before callback verification.

### Edge Cases

- Workspace login is not configured for the web cabinet.
- VK ID is enabled in policy but the client secret file is missing or empty.
- VK denies consent or returns an error query.
- Callback state is missing, expired, reused, or does not match.
- The requested return path is external, protocol-relative, empty, or includes newline characters.
- The provider start route is called for Telegram; this slice must not accidentally enable Telegram browser login.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The browser login and sign-up pages MUST render enabled VK ID as an active first-party action when workspace policy enables VK.
- **FR-002**: The browser login and sign-up pages MUST NOT label active VK ID as "скоро" or disabled.
- **FR-003**: The browser VK start route MUST create the same single-use callback state and audit trail used by the 013 provider start API.
- **FR-004**: The browser VK start route MUST redirect the user to VK authorization rather than returning an in-app stub.
- **FR-005**: Browser VK login MUST preserve only safe first-party return paths and fall back to `/meetings` for unsafe paths.
- **FR-006**: A successful VK callback from browser login MUST set the existing host-prefixed owner-session cookie and redirect to the requested safe cabinet path.
- **FR-007**: VK provider failures MUST fail closed with existing deterministic auth problem codes and safe user-visible recovery copy.
- **FR-008**: The generated VK callback URL MUST use `TWOBRAIN_AUTH_BASE_URL` when configured and MUST fall back to the request-derived URL when it is not configured.
- **FR-009**: The VK browser start flow MUST use `TWOBRAIN_VK_CLIENT_ID`, not the Yandex or Telegram client ID.
- **FR-010**: Production deployment MUST pass the VK client secret through a Docker secret file mounted only into `rec-api`.
- **FR-011**: The slice MUST keep email login available as a fallback on all browser login and sign-up pages.
- **FR-012**: The slice MUST NOT expose raw VK authorization codes, access tokens, client secrets, profile payloads, raw emails, raw phones, or live secret paths in rendered HTML, logs, specs, tests, or evidence.
- **FR-013**: The slice MUST NOT add new database tables, migrations, provider types, desktop-native OAuth, or direct desktop access to VK tokens.
- **FR-014**: The slice MUST include focused regression coverage for active VK rendering, start-route redirect behavior, public callback URL generation, provider-specific client ID selection, and safe failure fallback.

### Key Entities

- **Browser Provider Action**: A rendered login/sign-up action for a workspace-enabled provider, including label, mark, provider id, href, and active state.
- **Browser Auth Return Path**: A first-party cabinet path accepted after VK callback; unsafe paths collapse to `/meetings`.
- **Public Auth Base URL**: Operator-provided public origin used to build provider callback URLs behind the reverse proxy.
- **VK Callback State**: Existing 013 `AuthCallbackState` reused for browser login start and callback completion.
- **VK Provider Secret**: Server-side credential file used only by the API container to verify VK callbacks.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a workspace with VK enabled, 100% of browser login and sign-up page checks show an active VK ID action and 0 "скоро" badges attached to VK.
- **SC-002**: 100% of VK browser start checks return a redirect to VK authorization with a callback state and no raw secret material.
- **SC-003**: 100% of configured public-base-url checks generate VK `redirect_uri` values under the configured public origin.
- **SC-004**: 100% of VK start checks use the configured VK client ID.
- **SC-005**: 100% of unsafe `next` values in focused tests redirect to `/meetings`.
- **SC-006**: Existing email login tests continue to pass, proving VK did not remove the fallback path.

## Assumptions

- Feature 013 remains the backend source of truth for VK callback verification, session issuance, provider policy, audit events, and RU-local auth storage.
- The self-hosted operator registers `https://rec.2brain.pro/api/v1/auth/callback/vk` in the VK app settings.
- Browser cabinet login is the first user-visible VK ID surface; desktop-native OAuth and device pairing can be a later slice.
- Telegram Login remains listed by existing policy but stays disabled as a browser start action unless a later slice explicitly enables it.
