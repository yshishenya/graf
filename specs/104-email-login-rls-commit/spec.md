# Feature 104: RLS-safe email login completion

**Status**: Implemented and deployed; RLS production proof recorded

**Risk / validation lane**: high-risk auth

## User story

An existing workspace member who enters a valid email code can finish browser
login and reach the cabinet without seeing an internal server error.

## Requirements

- A valid code creates one trusted browser session and redirects to the safe
  requested cabinet path.
- The callback state is completed under an RLS context that is allowed to
  update it; session/device writes keep their narrower request context.
- Invalid, expired, replayed and cross-workspace codes retain their existing
  non-success behavior.
- No code, token, email address or session identifier is added to logs or
  evidence.

## Success criteria

- PostgreSQL RLS proves request context cannot update a callback state while
  the exact auth-bootstrap context can.
- The existing browser email-login integration path returns its normal `303`.

## Out of scope

- Changes to providers, email delivery, account enrolment, cookies, database
  schema, RLS policy text or authentication lifetime.
