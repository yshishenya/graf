# Data Model: Yandex ID Web Login

No new database entities are introduced.

## Reused Entities

### AuthCallbackState

Existing 013 callback state row. Used by browser Yandex start to store provider, workspace, single-use state nonce, requested safe return path, expiry, result, and error code.

Validation:

- State is single-use.
- Expired or reused state fails closed.
- Requested return path must be first-party and safe.

### ExternalIdentity

Existing 013 provider identity row. Yandex callback verification resolves provider subject and safe profile fields before this row is linked to an internal user.

Validation:

- `(provider, provider_subject)` remains globally unique.
- Raw OAuth codes, tokens, and full profile payloads are not stored.

### AuthSession

Existing 013 session row. A successful browser Yandex callback issues a server session and the web route sets the host-prefixed owner-session cookie.

Validation:

- Session tokens are hashed at rest.
- Cookie is HttpOnly, Secure, SameSite=Lax, and path-scoped to `/`.

### WorkspaceAuthPolicy

Existing workspace policy row. Browser login uses it to decide whether Yandex is active for the workspace.

Validation:

- Disabled providers are hidden from public provider choices.
- This slice enables only Yandex browser start behavior.

## View Concepts

### BrowserProviderAction

Rendered page action with:

- `provider`
- `label`
- `mark`
- `href`
- `active`

Validation:

- Yandex has an active href when enabled.
- Non-Yandex providers remain disabled unless a later slice enables them.

### BrowserAuthReturnPath

Safe path used after provider callback.

Validation:

- Must start with `/`.
- Must not start with `//`.
- Must not contain newlines.
- Defaults to `/meetings` when unsafe.

### PublicAuthCallbackUrl

Callback URL sent to Yandex in the authorization request.

Validation:

- Uses `TWOBRAIN_AUTH_BASE_URL` when configured.
- Falls back to `request.url_for("auth_callback", provider="yandex")` in local/test contexts.
