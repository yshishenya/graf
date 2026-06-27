# Feature Specification: Yandex ID Web Login

**Feature Branch**: `codex/065-yandex-id-web-login`

**Created**: 2026-06-27

**Status**: Draft

**Input**: User description: "давай настроим авторизацию через yandex ID"; follow-up: "бери 065"

## Clarifications

### Session 2026-06-27

- Scope decision: feature 065 enables the existing 013 Yandex ID backend for the browser web-cabinet login and registration surfaces. It does not rebuild the provider foundation and does not add a desktop-native OAuth flow.
- Release decision: no production deployment is part of this slice unless the user later approves the release/deploy gate.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sign In Through Yandex ID (Priority: P1)

A workspace user opens the web cabinet login page, chooses Yandex ID, completes Yandex consent, and returns to the requested cabinet page with a valid owner-session cookie.

**Why this priority**: This turns the already implemented provider backend into a usable login path. Without it, Yandex ID remains visible as a disabled "soon" option.

**Independent Test**: Start `/login/yandex/start?next=/meetings`, verify the user is redirected to a Yandex authorization URL, then complete a callback with a verified provider profile in tests and confirm the cabinet session opens `/meetings`.

**Acceptance Scenarios**:

1. **Given** a workspace has Yandex ID enabled, **When** the user opens `/login`, **Then** the Yandex ID action is an active link to `/login/yandex/start` and is not marked "скоро".
2. **Given** the user starts Yandex ID login with `next=/meetings`, **When** the start route succeeds, **Then** the browser receives a redirect to Yandex with a single-use callback state and a safe return path.
3. **Given** Yandex returns a verified callback, **When** the server accepts it, **Then** the browser receives the existing owner-session cookie and lands only on a safe first-party cabinet path.

---

### User Story 2 - Fail Closed With Email Fallback (Priority: P2)

A user who cannot use Yandex ID because the provider is disabled, missing, misconfigured, denied, or temporarily unavailable gets a safe, actionable login page and can still use email login.

**Why this priority**: Auth failures are security-sensitive and must not strand a user or leak provider details.

**Independent Test**: Simulate disabled provider, missing workspace, bad callback state, provider denial, and provider verification outage; each case returns bounded copy without raw provider data and leaves the email path visible.

**Acceptance Scenarios**:

1. **Given** Yandex is disabled by workspace policy, **When** the user opens `/login`, **Then** Yandex is hidden from active provider choices and email login remains available.
2. **Given** Yandex returns a denial or invalid callback state, **When** the browser returns to the cabinet, **Then** the user sees a generic recovery message and no token, code, subject, email, or raw Yandex payload is exposed.

---

### User Story 3 - Configure Public Callback Truth (Priority: P2)

An operator configures the public auth base URL for the self-hosted cabinet so Yandex receives the registered public callback URL rather than an internal container or testserver URL.

**Why this priority**: Yandex OAuth depends on exact redirect URI matching; a working button is not enough if the callback URL is wrong behind the reverse proxy.

**Independent Test**: Configure `TWOBRAIN_AUTH_BASE_URL=https://rec.2brain.pro`, start Yandex login, and verify the generated `redirect_uri` is `https://rec.2brain.pro/api/v1/auth/callback/yandex`.

**Acceptance Scenarios**:

1. **Given** a public auth base URL is configured, **When** any provider start flow builds its callback URL, **Then** the callback URL uses the configured public origin plus the provider callback path.
2. **Given** no public auth base URL is configured in local tests, **When** the flow starts, **Then** existing request-derived local URLs continue to work.

### Edge Cases

- Workspace login is not configured for the web cabinet.
- Yandex ID is enabled in policy but the client secret file is missing or empty.
- Yandex denies consent or returns an error query.
- Callback state is missing, expired, reused, or does not match.
- The requested return path is external, protocol-relative, empty, or includes newline characters.
- The provider start route is called for a provider other than Yandex; this slice must not accidentally enable VK or Telegram browser login.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The browser login and sign-up pages MUST render enabled Yandex ID as an active first-party action when workspace policy enables Yandex.
- **FR-002**: The browser login and sign-up pages MUST NOT label active Yandex ID as "скоро" or disabled.
- **FR-003**: The browser Yandex start route MUST create the same single-use callback state and audit trail used by the 013 provider start API.
- **FR-004**: The browser Yandex start route MUST redirect the user to Yandex authorization rather than returning an in-app stub.
- **FR-005**: Browser Yandex login MUST preserve only safe first-party return paths and fall back to `/meetings` for unsafe paths.
- **FR-006**: A successful Yandex callback from browser login MUST set the existing host-prefixed owner-session cookie and redirect to the requested safe cabinet path.
- **FR-007**: Yandex provider failures MUST fail closed with existing deterministic auth problem codes and safe user-visible recovery copy.
- **FR-008**: The generated provider callback URL MUST use `TWOBRAIN_AUTH_BASE_URL` when configured and MUST fall back to the request-derived URL when it is not configured.
- **FR-009**: The slice MUST keep email login available as a fallback on all browser login and sign-up pages.
- **FR-010**: The slice MUST NOT expose raw Yandex authorization codes, access tokens, client secrets, profile payloads, raw emails, raw phones, or live secret paths in rendered HTML, logs, specs, tests, or evidence.
- **FR-011**: The slice MUST NOT add new database tables, migrations, provider types, desktop-native OAuth, or direct desktop access to Yandex tokens.
- **FR-012**: The slice MUST include focused regression coverage for active Yandex rendering, start-route redirect behavior, public callback URL generation, and safe failure fallback.

### Key Entities

- **Browser Provider Action**: A rendered login/sign-up action for a workspace-enabled provider, including label, mark, provider id, href, and active state.
- **Browser Auth Return Path**: A first-party cabinet path accepted after Yandex callback; unsafe paths collapse to `/meetings`.
- **Public Auth Base URL**: Operator-provided public origin used to build provider callback URLs behind the reverse proxy.
- **Yandex Callback State**: Existing 013 `AuthCallbackState` reused for browser login start and callback completion.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a workspace with Yandex enabled, 100% of browser login and sign-up page checks show an active Yandex ID action and 0 "скоро" badges attached to Yandex.
- **SC-002**: 100% of Yandex browser start checks return a redirect to Yandex authorization with a callback state and no raw secret material.
- **SC-003**: 100% of configured public-base-url checks generate `redirect_uri` values under the configured public origin.
- **SC-004**: 100% of unsafe `next` values in focused tests redirect to `/meetings`.
- **SC-005**: Existing email login tests continue to pass, proving Yandex did not remove the fallback path.

## Assumptions

- Feature 013 remains the backend source of truth for Yandex callback verification, session issuance, provider policy, audit events, and RU-local auth storage.
- The self-hosted operator registers the same public callback URL in the Yandex app settings that the server emits through `TWOBRAIN_AUTH_BASE_URL`.
- Browser cabinet login is the first user-visible Yandex ID surface; desktop-native OAuth and device pairing can be a later slice.
- VK ID and Telegram Login remain listed by existing policy but stay disabled as browser start actions unless a later slice explicitly enables them.
