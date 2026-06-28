# Research: Yandex ID Web Login

## Decision: Reuse the 013 Yandex provider adapter

**Rationale**: The existing backend already exchanges a Yandex authorization code for an access token, reads the Yandex profile, verifies the returned client id, creates or resolves internal identity, issues a session, and writes auth audit events.

**Alternatives considered**:

- New web-only Yandex implementation: rejected because it would duplicate provider verification and increase takeover risk.
- Direct client-side Yandex handling: rejected because desktop/browser clients must not receive provider tokens or secrets.

## Decision: Enable only Yandex ID in the browser start route

**Rationale**: The user asked specifically for Yandex ID. VK and Telegram provider adapters exist from 013, but turning all browser provider buttons on would broaden product and test scope.

**Alternatives considered**:

- Enable all providers: rejected as unrequested scope.
- Leave Yandex as a stub and document setup only: rejected because it would not satisfy the user-visible authorization request.

## Decision: Use public auth base URL for callback URI generation

**Rationale**: OAuth redirect URI matching depends on the public callback URL registered with the provider. Behind Docker/reverse proxy, request-derived URLs may be internal or test URLs. The existing `TWOBRAIN_AUTH_BASE_URL` setting should define the public origin when configured.

**Alternatives considered**:

- Always use `request.url_for`: works in tests, but can produce wrong host/scheme behind a proxy.
- Add per-provider callback URL settings: rejected; one public auth origin plus existing provider callback path is enough.

## Decision: Keep email login fallback

**Rationale**: Provider outages, disabled policy, secret misconfiguration, and user denial are normal auth outcomes. Email login is already implemented and should remain visible.

**Alternatives considered**:

- Remove email after Yandex is active: rejected because it reduces recovery.

## References

- Yandex OAuth endpoints are still reachable as of 2026-06-27:
  - `https://oauth.yandex.ru/authorize`
  - `https://oauth.yandex.com/authorize`
  - `https://login.yandex.ru/info`
- Feature 013 already documents the provider reference: `https://yandex.com/dev/id/doc/en/`.
