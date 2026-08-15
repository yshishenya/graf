# Research: embedded billing

- Existing client route policy sends `/billing*` to `NSWorkspace.shared.open` after a one-time desktop handoff.
- Existing billing pages already validate session, tenant, owner role and CSRF server-side.
- Existing server YooKassa contract allowlists HTTPS hosts in `billing.yookassa.is_allowed_confirmation_url`.
- Therefore the smallest safe change is client-side route ownership plus reuse of the existing payment allowlist; no database or API migration is needed.
