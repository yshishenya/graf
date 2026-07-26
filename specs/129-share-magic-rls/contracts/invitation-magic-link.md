# Invitation magic-link contract

## Anonymous GET

- Valid invitation GET remains side-effect-limited to the existing continuation
  exchange and renders no meeting content.
- JavaScript-enabled clients may submit the existing CSRF-bound continuation
  form automatically; JavaScript-disabled clients retain one visible fallback
  action.

## Continuation POST

- A valid first-entry request returns the existing allowed summary/recording
  result or its existing redirect, sets the recipient session cookie, and does
  not return HTTP 500 from audit/RLS context handling.
- Existing identity, replay, expiry, revoke, deletion, recipient-bound and
  CSRF behavior remains unchanged.
- Domain failures remain the existing safe 4xx responses; internal errors are
  not converted into a broad authorization bypass.

## Audit and notification

- The email-login audit is persisted under the recipient personal workspace
  context before the session enters the source meeting workspace context.
- Post-commit account-created notification failures remain bounded and cannot
  change a successful access response into HTTP 500.
