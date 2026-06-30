# Feature Specification: Cabinet Login Polish

**Feature Branch**: `codex/070-cabinet-login-polish`

**Created**: 2026-06-28

**Status**: Draft

**Input**: User description: "070 - make the login window narrower and provider tiles more elegant; align code confirmation width between web and app; auto-submit after the last digit or pasted code; fix provider login errors in the app while web works."

## Clarifications

### Session 2026-06-28

- Scope decision: feature 070 is a narrow polish and recovery slice over the existing web cabinet auth flow. It reuses the server-owned login pages, the existing provider web-login backend, and 033 desktop embedded cabinet shell.
- OAuth boundary decision: the desktop app may load HTTPS provider authorization legs while an auth flow is active; arbitrary external links remain blocked outside that auth continuation.
- Release decision: no production deployment is part of this slice unless the user later approves the release/deploy gate.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Provider Login Works In The App (Priority: P1)

A desktop user with an expired cabinet session opens the embedded login page, chooses an enabled provider, and is taken through that provider authorization leg without the app showing the generic cabinet-session error.

**Why this priority**: The user can log in on the web but hits an app-only blocker. Auth recovery must work before visual polish matters.

**Independent Test**: Use the desktop route policy with the configured cabinet base URL and verify `/login/{provider}/start` is allowed, provider authorization HTTPS URLs are allowed only during auth continuation, first-party provider callbacks are allowed, and unrelated external URLs remain blocked outside auth continuation.

**Acceptance Scenarios**:

1. **Given** the embedded login page redirects to a provider authorization URL, **When** the macOS route policy evaluates that HTTPS URL during auth continuation, **Then** it allows the navigation as an auth-provider leg.
2. **Given** the provider returns to `/api/v1/auth/callback/{provider}`, **When** the macOS route policy evaluates that first-party URL, **Then** it allows the callback so the existing owner-session cookie can return to the WebView.
3. **Given** an unknown external URL attempts to load outside auth continuation, **When** the macOS route policy evaluates it, **Then** it remains blocked or opened externally only under the existing safe-help rules.

---

### User Story 2 - Login Panel Feels Narrower And Cleaner (Priority: P2)

A web or desktop user sees a more compact login panel where provider tiles do not stretch across an overly wide window.

**Why this priority**: The current panel looks heavy in the screenshot and makes provider choices feel clumsy.

**Independent Test**: Render `/login` and verify the auth panel and provider grid use narrower responsive bounds while preserving provider labels, disabled states, and email fallback.

**Acceptance Scenarios**:

1. **Given** the login page has multiple providers, **When** it renders at a desktop width, **Then** the panel and provider grid stay within the polished narrow width.
2. **Given** the login page renders on a small viewport, **When** providers wrap responsively, **Then** labels remain readable and disabled "скоро" states do not overlap controls.

---

### User Story 3 - Code Entry Completes Without Extra Clicks (Priority: P2)

A user who receives a one-time email code enters or pastes all six digits and the form submits immediately with the same comfortable width in web and app.

**Why this priority**: Code confirmation is a critical login step; forcing an extra click after a full code is needless friction.

**Independent Test**: Exercise the shared code form script with six digit input and paste behavior, and verify the hidden code is synced before submit.

**Acceptance Scenarios**:

1. **Given** the user types the sixth digit, **When** all six slots contain digits, **Then** the form submits once with the hidden `code` value set to all six digits.
2. **Given** the user pastes a six-digit code, **When** the slots are filled from the clipboard, **Then** the form submits once with the hidden `code` value set to the pasted code.

### Edge Cases

- The user types non-digits into a code slot.
- The user pastes fewer than six digits.
- The user corrects a digit after a previous failed attempt.
- Reduced-motion users still get the same functional behavior without relying on transitions.
- Unsupported providers remain server-validated; unknown external URLs outside auth continuation remain fail-closed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The desktop WebView MUST allow HTTPS provider authorization URLs initiated by the first-party login flow for any configured provider.
- **FR-002**: The desktop route policy MUST allow the first-party auth callback route needed to set the existing owner-session cookie in the WebView.
- **FR-003**: The desktop route policy MUST preserve blocking for unknown external URLs and MUST NOT attach desktop headers to provider authorization origins.
- **FR-004**: The login and sign-up auth panel MUST use a narrower responsive desktop width than the current oversized provider layout.
- **FR-005**: Provider tiles MUST remain two-column on suitable widths, readable on small widths, and keep active/disabled states visually distinct.
- **FR-006**: The email code panel MUST share the same panel width rules as the login panel across web and app.
- **FR-007**: The code form MUST sync the hidden `code` field after every digit and paste operation.
- **FR-008**: The code form MUST submit automatically after exactly six digits are present, whether typed or pasted.
- **FR-009**: The auto-submit behavior MUST avoid duplicate submits from repeated input or paste events.
- **FR-010**: The slice MUST NOT add provider credentials, expose raw OAuth codes/tokens, add desktop access to provider tokens, or change callback verification.
- **FR-011**: The slice MUST include focused regression coverage for desktop route policy behavior and the server-rendered login/code assets.

### Key Entities

- **Embedded Auth Provider Leg**: An HTTPS provider authorization origin that the desktop WebView may load only as part of an active login route.
- **Auth Panel Layout**: Shared responsive CSS for login, sign-up, and code confirmation pages.
- **Code Form State**: Six visible digit slots plus one hidden form field submitted to the existing server route.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of focused route-policy checks allow provider OAuth continuation plus the first-party callback and continue blocking an unknown external host outside auth continuation.
- **SC-002**: 100% of focused server-rendered auth page checks still expose enabled providers, email fallback, and code-form assets without workspace id leakage.
- **SC-003**: 100% of focused JS/code-form checks prove a complete typed or pasted six-digit code submits once.
- **SC-004**: Existing email login and provider-start integration tests continue to pass.

## Assumptions

- Existing backend provider auth remains the source of truth for callback verification and browser session issuance.
- The app's embedded login recovery remains server-owned; this slice does not introduce a native OAuth/device pairing flow.
- The desktop app route policy does not decide provider enablement; it only allows the same web-auth navigation path and lets the server validate the provider.
- Production deploy and live account re-test are out of scope until the release gate is explicitly approved.
