# Data Model: VK ID Web Login

No new database tables or migrations are introduced.

## Browser Provider Action

Rendered login/sign-up action for an enabled workspace provider.

- `provider`: `vk`
- `label`: user-visible VK ID label
- `mark`: compact provider mark
- `href`: `/login/vk/start?next=<safe_next>`
- `active`: true when provider is enabled and in the browser-enabled set

Validation rules:

- Disabled workspace providers are hidden from public provider choices.
- Active provider links preserve only safe first-party `next` paths.
- Telegram remains disabled for browser start in this slice.

## VK Callback State

Existing 013 callback state row. Used by browser VK start to store provider, workspace, single-use state nonce, requested safe return path, expiry, result, and error code.

Rules:

- State remains single-use.
- Expired, reused, missing, or mismatched state fails closed.
- State metadata is safe to audit; raw provider code/token/payload is not.

## External Identity

Existing 013 provider identity row. VK callback verification resolves provider subject and safe profile fields before this row is linked to an internal user.

Rules:

- `(provider, provider_subject)` remains globally unique.
- New workspace membership still follows workspace enrollment policy.
- Raw VK token responses and full provider payloads are not stored.

## VK Provider Secret

Server-side credential file used by `rec-api` to verify VK callbacks.

Rules:

- The secret is mounted into `rec-api` only.
- Missing or empty configured secret files fail closed during production startup.
- Secret path and value are not rendered, logged, or committed.
