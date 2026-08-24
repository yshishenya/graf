# Data Model: Повторный ввод email-кода

## Existing entities

### AuthCallbackState

- `state_nonce`: browser-bound auth state identifier.
- `expected_state`: for public login/signup, a bounded pair of server-keyed
  HMAC digests: one for provider/state/email/code and one for
  provider/state/email/browser nonce; authenticated email-link keeps its
  existing single digest.
- `expires_at`: existing 15-minute TTL.
- `result`: `pending` until success, expiry, replay or another terminal failure.
- `error_code`: existing terminal failure metadata; wrong attempts do not
  complete the state.

### AuthRateLimitBucket

- Scope `email_code_verify_state` identifies one auth state.
- Existing limit changes from 10 to 3 attempts per 15-minute window.
- Existing `email_code_verify_address` (10) and `email_code_verify_ip` (40)
  remain unchanged.
- Existing send scopes remain unchanged.

## State transitions

```text
pending --wrong attempt 1/2--> pending
pending --wrong attempt 3--> rate-limited recovery response; no session
pending --next verify--> rate-limited response; no session
pending --correct code--> completed
pending --TTL elapsed--> expired
completed/expired/failed --replay--> rejected
```

No database schema or migration changes are required.
