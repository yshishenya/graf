# Embedded billing contract

- Same-origin `/billing` document routes are `allow` + `billing` route kind.
- Billing GET requests use the existing desktop session-header injection.
- Browser-owned admin/account/referral routes remain external.
- External payment navigation is allowed only for HTTPS hosts in the existing YooKassa allowlist and only while the current document is a billing checkout route.
- No auth token, CSRF token, amount, provider id, promo code or signed URL is appended by the desktop client.
