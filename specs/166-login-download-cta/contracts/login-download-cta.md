# UI Contract: Login download CTA

## Web login

For `/login` with a normalized `next` that does not start with `/desktop/`:

- render exactly one web-only download CTA;
- its destination is the existing same-origin `/download` route;
- its accessible name explains that it opens the GRAF application download page;
- it remains keyboard reachable with a visible focus state;
- it is outside the primary auth card and must not cover the form, alert or
  legal copy at supported widths.

## Embedded login

For `/login` with a normalized `next` beginning with `/desktop/`:

- render no `/download` link, download CTA text or empty CTA placeholder;
- keep provider links, email form, error alert, terms and privacy links intact;
- preserve the same `next` value and auth submission routes.

## Scope boundary

This contract does not change `/download`, signup, email-code, referral landing,
authenticated cabinet sidebar or auth/session behavior.
