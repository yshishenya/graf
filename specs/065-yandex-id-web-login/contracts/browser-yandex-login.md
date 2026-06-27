# Contract: Browser Yandex ID Login

## GET `/login`

When workspace login is configured and Yandex is enabled:

- Render active provider action:
  - label: `Продолжить через Яндекс ID`
  - href: `/login/yandex/start?next=<safe_next>`
  - no `aria-disabled=true`
  - no `скоро` badge for Yandex
- Keep email login form visible.

When Yandex is disabled:

- Do not render Yandex as an active provider action.
- Keep email login form visible.

## GET `/sign-up`

Same provider rendering rules as `/login`.

## GET `/login/yandex/start`

Inputs:

- `next` query string, optional, defaults to `/meetings`
- `workspace_id` query string, optional when server `web_login_workspace_id` is configured

Success:

- HTTP `303`
- `Location` points to Yandex authorization URL
- authorization URL includes:
  - `response_type=code`
  - configured Yandex client id
  - callback `redirect_uri`
  - single-use `state`
- creates auth callback state with the safe return path.

Failure:

- `400 workspace_required` rendered login page when workspace cannot be resolved
- `403 provider_disabled` rendered login page when policy disables Yandex
- `403 provider_missing` rendered login page when the provider is unsupported
- `503 auth_dependency_unavailable` or `provider_unavailable` rendered login page when auth dependencies are unavailable

Security:

- Never render raw provider code, access token, client secret, profile payload, email, phone, or secret path.
- Unsafe `next` values resolve to `/meetings`.

## GET `/api/v1/auth/callback/yandex`

Existing 013 API callback behavior remains authoritative.

Browser behavior:

- If the callback state has a safe requested redirect, set the owner-session cookie and redirect there.
- If the requested redirect is unsafe or missing, set the cookie and return the existing JSON callback response.
