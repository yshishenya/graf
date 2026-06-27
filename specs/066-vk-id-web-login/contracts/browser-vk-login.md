# Contract: Browser VK Login

## GET `/login`

- Render active provider action when workspace policy enables VK:
  - provider: `vk`
  - label: `Продолжить через VK ID`
  - href: `/login/vk/start?next=<safe_next>`
  - no `скоро` badge attached to VK
- Keep email login visible.
- Do not expose workspace UUID or secret values in HTML.

## GET `/sign-up`

Same provider rendering rules as `/login`.

## GET `/login/vk/start`

Inputs:

- Query `next`: optional safe first-party return path.
- Query `workspace_id`: optional UUID; normally omitted because production uses configured web-login workspace.

Success:

- Status: `303`
- Location: VK authorization URL.
- Query contains:
  - `client_id` from VK settings
  - `redirect_uri` ending in `/api/v1/auth/callback/vk`
  - `state`
  - safe workspace return path metadata when supported by the provider adapter

Failures:

- `400 workspace_required` rendered login page when no workspace is configured.
- `403 provider_disabled` rendered login page when policy disables VK.
- `403 provider_missing` rendered login page when the provider is unsupported.
- `503 auth_dependency_unavailable` or `provider_unavailable` rendered login page when auth dependencies are unavailable.

Safety:

- Never render raw provider code, access token, client secret, profile payload, email, phone, or secret path.

## GET `/api/v1/auth/callback/vk`

Existing 013 callback contract applies. Browser-specific behavior:

- Successful browser callback sets the existing host-prefixed owner-session cookie.
- Redirects only to a safe first-party cabinet path.
- Unsafe return paths collapse to `/meetings`.
