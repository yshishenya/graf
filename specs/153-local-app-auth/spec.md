# Feature Specification: Авторизация в локальном macOS-приложении

**Feature**: `153-local-app-auth`
**Risk lane**: high-risk-feature (auth, desktop, local development)

## User Stories

1. Разработчик открывает `GRAF Local` без browser cookie и видит понятный
   переход во встроенный login-flow.
2. Разработчик входит через `local@graf.test` и после email-code возвращается к
   локальному списку встреч.
3. Production macOS-приложение сохраняет текущую auth/session обработку без
   local-only fallback и без legacy headers.

## Requirements

- Local auth recovery MUST be enabled only when the explicit local-app flag is
  set together with an explicit HTTP loopback origin.
- An unauthenticated local cabinet request MUST offer an in-app action that opens
  `/login?next=/desktop/meetings` in the same WebKit session.
- The local flow MUST reuse the existing email-code auth, CSRF and session cookie
  flow; it MUST NOT copy browser cookies, add bypass headers, or add a second auth
  protocol.
- After successful verification, the local WebKit session MUST follow the safe
  `next` path back to the local meetings route.
- When the local flag is absent, production/default app behavior and recovery
  labels MUST remain unchanged.

## Success Criteria

- A fresh `GRAF Local` launch exposes an in-app «Войти в кабинет» action when the
  local meetings request has no session.
- Completing email-code login inside the app reaches local `/desktop/meetings`
  without a 401 on the next request.
- Existing production configuration tests and focused macOS cabinet tests pass;
  no production URL, cookie, header or update behavior changes.

## Edge Cases

- If the local API is stopped, the login action may fail with a truthful network
  state; it must not silently fall back to production.
- A browser login outside the app is not treated as an app login.

## Out of Scope

Password auth, OAuth changes, browser-cookie import, shared bypass tokens,
legacy authentication headers, production deployment and production UX changes.

## Clarifications

### Session 2026-08-16

- Q: Should local auth be isolated from production? → A: Yes; gate it with an explicit loopback-only local flag and preserve production behavior.
