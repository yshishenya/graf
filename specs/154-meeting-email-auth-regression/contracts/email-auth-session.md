# Email Auth Session Contract

- Start normalizes email, resolves the workspace/identity, creates a pending
  provider-bound callback state and delivers the code; production delivery
  failure invalidates the state and creates no usable session.
- Verify accepts only the matching pending, unexpired state and normalized
  email/code, then uses `resolve_browser_auth_return_path` and
  `auth_session_cookie_name(request)`.
- Local fixed code is accepted only for non-production loopback HTTP local mode.
- Embedded WebKit and native HTTP requests use the same origin-selected cookie;
  no copied auth header, JavaScript cookie read or parallel auth flow is allowed.
