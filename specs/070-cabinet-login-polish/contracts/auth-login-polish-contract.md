# Auth Login Polish Contract

## Auth Layout Contract

- `auth-panel` width is the shared responsive bound for login, sign-up, and code confirmation.
- Provider actions remain in a two-column grid on roomy viewports and remain readable on narrow viewports.
- Disabled providers keep `aria-disabled="true"` and do not expose active links.
- Email fallback remains visible on login and sign-up pages.

## Code Entry Contract

- Six `data-code-slot` inputs compose the hidden `data-code-hidden` value.
- Non-digit input is stripped before sync.
- Pasting a code distributes at most six digits across the slots.
- When all six slots contain digits, the form submits once through the existing form action.
- A partial code never auto-submits.

## Desktop Embedded OAuth Contract

- Same-origin cabinet routes continue to use existing route classifications.
- Any HTTPS provider authorization URL is allowed as `authProvider` only while auth continuation is active.
- Same-origin `/api/v1/auth/callback/{provider}` routes with safe provider ids are allowed as `authCallback`; provider enablement remains server-validated.
- Unknown external hosts remain blocked unless they already satisfy the safe help/documentation exception.
- Desktop headers are never injected into provider-origin requests.
- Route policy tests must cover one allowed provider origin, one auth-continuation provider origin, one allowed first-party callback route, and one blocked unknown external origin outside auth continuation.
