# Research: Cabinet Login Polish

## Decision: Reuse Shared Auth Assets

**Rationale**: Login, sign-up, and code confirmation already share `auth-panel`, `auth-provider-grid`, and `code-grid` in `cabinet.css`. Narrowing these shared rules fixes web and app together with the smallest diff.

**Alternatives considered**:

- Add app-specific CSS: rejected because the mismatch comes from shared responsive bounds and app-specific CSS would duplicate behavior.
- Add new templates/components: rejected because existing templates already express the needed structure.

## Decision: Auto-submit In Existing Code Form Script

**Rationale**: `cabinet.js` already owns slot cleanup, paste distribution, hidden-field sync, and submit sync. Adding a guarded `requestSubmit()` after a complete six-digit value fixes typed and pasted codes in one place.

**Alternatives considered**:

- Inline template script: rejected because it duplicates the static asset behavior.
- Server-side polling or htmx behavior: rejected because the existing plain form is enough.

## Decision: Allow Provider OAuth Continuation In Desktop Policy

**Rationale**: The app error happens because the embedded route policy blocks provider redirects as unknown external URLs. Allowing HTTPS provider legs only while the WebView is already in the first-party auth flow lets all server-configured providers behave like web, keeps arbitrary external navigation blocked outside auth continuation, and avoids sending desktop headers to providers.

**Alternatives considered**:

- Open provider auth in the system browser: rejected for this slice because it would complete auth in the browser cookie jar, not the embedded app session.
- Allow all external login redirects unconditionally: rejected because it weakens the desktop embedded boundary outside auth continuation.
- Native OAuth/device pairing: rejected as a larger future slice.
