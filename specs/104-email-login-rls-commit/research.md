# Research

- Production traceback reached `browser_email_login_verify` and failed while
  flushing an update during `_consume_email_login_code`.
- The callback row is readable under `auth_callback_lookup`; later device and
  session creation correctly switches to request context. The final callback
  state update then runs under request context, which the forced-RLS callback
  policy intentionally rejects.
- Reapply existing `auth_bootstrap` context only after request-scoped writes
  are flushed. That context already authorizes callback-state and auth-audit
  writes, without broadening a policy or adding a new role.
