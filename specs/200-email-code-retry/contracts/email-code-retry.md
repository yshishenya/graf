# Email-code retry contract

## Public browser login and signup

- The first and second wrong code submissions return a recoverable error page.
- The recoverable page keeps the six-slot code form, the current email and safe
  return path.
- The third wrong code submission immediately returns the blocked recovery state;
  it does not keep a dead verification form visible.
- The fourth verification request after three failed attempts is rate-limited;
  it must not create a session, even if it contains the correct code.
- A resend starts the existing new-code flow and remains subject to existing
  resend limits.

## Terminal and protected cases

- Expired, replayed, missing, cross-workspace or browser-unbound states remain
  fail-closed.
- HMAC/browser binding and single-use behavior are unchanged.
- Auth audit records failure metadata only; no code, token, email, state nonce or
  meeting content is emitted.

## UI copy and accessibility

- Wrong code: explicit error, code inputs remain available, first empty slot can
  receive focus after the response.
- Rate-limited state: explain that a new code is required; hide the dead verify
  form and keep resend and change-email actions.
