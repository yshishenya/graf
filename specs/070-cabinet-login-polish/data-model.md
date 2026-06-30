# Data Model: Cabinet Login Polish

No new persistent data model is introduced.

## Existing Entities Reused

- **AuthCallbackState**: Existing single-use provider/email login state. Unchanged.
- **AuthSession**: Existing owner-session cookie backing state. Unchanged.
- **WorkspaceProviderPolicy**: Existing provider enablement policy. Unchanged.

## Transient UI State

- **Code Form State**
  - `slots`: six visible one-character digit inputs.
  - `code`: hidden form field composed from `slots`.
  - `submitted`: client-side guard to avoid duplicate auto-submits.

## Desktop Route Classification

- **Auth Provider Leg**
  - `scheme`: `https`.
  - `host`: any HTTPS provider host reached while auth continuation is active.
  - `action`: allowed in the embedded WebView without desktop header injection while the web auth flow remains active.
- **Auth Callback Route**
  - `path`: `/api/v1/auth/callback/{provider}` with a safe provider segment.
  - `action`: allowed as a same-origin cabinet route; provider support and state verification remain server-owned.

No migrations, retention behavior, or deletion lifecycle changes are required.
