# Research: invitation magic-link RLS 500

## Production evidence

- Production runtime was on migration head `0041_share_account_created_email`
  and healthy API endpoints returned 200; health alone did not exercise the
  invitation continuation route.
- Sanitized API logs contained six occurrences in the inspected four-hour
  window of `InsufficientPrivilegeError` for `auth_audit_events`.
- The stack reached `share_invitation_magic_link` →
  `accept_share_invitation` → `enforce_share_rate_limit`; the database error
  was an RLS `WITH CHECK` failure, not a notification provider failure.
- The pending event was `email_auth_completed` for the recipient personal
  workspace. The event is added while the personal context is active, then the
  session switches to the invited meeting workspace before the next SQL query.
  SQLAlchemy autoflushes the pending event during that query, so RLS evaluates
  the row against the wrong current workspace.

No email, token, meeting content, request identifier or opaque production row
identifier is stored in this document.

## Options considered

### A. Flush the audit row before switching context — selected

Call the existing session flush immediately after the email-login audit is
created and while the personal workspace context is active. This is the smallest
change, preserves one transaction and keeps the existing RLS policy authoritative.

### B. Write the audit in a separate session

This could isolate contexts, but would add transaction ordering and failure
semantics to an already sensitive first-entry flow. It is unnecessary if the
existing session can flush the row under the correct context.

### C. Broaden or bypass the RLS policy — rejected

This would hide a tenant-context bug and weaken the audit boundary. It violates
the constitution and is not needed for the user journey.

### D. Disable autoflush around rate-limit queries — rejected

This would leave the audit pending until an arbitrary later query/commit and
could make the same mismatch reappear. It treats the symptom rather than
establishing the correct transaction boundary.

## Cleanup review

Callers of `enforce_share_rate_limit`, `apply_tenant_context`,
`_record_email_login_audit` and `_dispatch_account_created_email` were searched.
The post-commit notification catch is still required because workflow startup
and failure bookkeeping are independent secondary work. No duplicate helper or
dead branch is removed speculatively; cleanup is limited to code proven unused
by the focused call-site review and tests.

## Local validation evidence

- The pre-fix contract failed because no audit flush existed between the audit
  write and the workspace-context switch.
- The strict non-superuser RLS regression passed after the flush boundary was
  added; the intentionally wrong ordering still fails closed with a database
  RLS error.
- Focused invitation, contract and UI matrix: `23 passed`.
- Full `infra/scripts/ci-local.sh`: macOS `640 passed`, server `2440 passed / 1
  skipped`, strict PostgreSQL `42 passed / 1 skipped`; lint, compile, Compose
  and deployment evidence scan passed.
