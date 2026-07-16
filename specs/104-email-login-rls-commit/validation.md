# Validation evidence

- Root cause traced from the production callback endpoint to the callback-state
  update at transaction commit. No user email, code or token was retained.
- Focused browser email-login integration suite passed locally.
- Ruff passed for the changed module and RLS regression.
- The new PostgreSQL RLS test is intentionally skipped locally without the
  disposable `RLS_TEST_DATABASE_URL`.
- The dedicated PostgreSQL RLS proof passed against a disposable database:
  `1 passed, 13 deselected` in 4m33s. A request context sees zero rows when
  attempting to complete the callback; the exact auth-bootstrap context can
  complete it. The isolated database and its SSH tunnel were removed after the
  proof.
- `infra/scripts/ci-local.sh` passed after the implementation change and again
  after the RLS expectation correction: 1,741 passed, 26 skipped; macOS
  643/643; lint and Python compile passed.
- Browser production evidence: after deploy of `v2026.07.16.5`
  (`659c13376e395f712cc6e84b3e5c557923a172f6`), a new email login reached
  `/meetings` and the visible "Мои встречи" cabinet instead of an error page.
