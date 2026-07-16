# Validation evidence

- Root cause traced from the production callback endpoint to the callback-state
  update at transaction commit. No user email, code or token was retained.
- Focused browser email-login integration suite passed locally.
- Ruff passed for the changed module and RLS regression.
- The new PostgreSQL RLS test is intentionally skipped locally without the
  disposable `RLS_TEST_DATABASE_URL`; the production deploy gate must execute
  that test against its disposable database before T003 may close.
- `infra/scripts/ci-local.sh` passed after the implementation change.
