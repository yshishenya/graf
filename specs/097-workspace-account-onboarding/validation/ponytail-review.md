# Feature 097 review receipt

## Scope

The final review covered the auth/session boundary, workspace and invitation
helpers, PostgreSQL migrations/RLS, browser and embedded settings surfaces,
macOS recovery state, and the Feature 110 test-runner integration.

## Findings and fixes

- The accelerated runner removed the obsolete `postgres_test_database_url`
  compatibility fixture. The onboarding downgrade test now uses the explicit
  disposable `postgres_clean_database_url` fixture.
- The packaged migration head advanced to `0028_active_space_read`; the worker
  startup tests now assert that real head instead of the retired 0026 value.
- No secret-bearing data, raw invitation token, private content or SQLite
  runtime path was introduced.

## Review result

- `git diff --check`: pass.
- Ruff over `apps/server`: pass.
- Python compilation over source, tests and scripts: pass.
- Canonical CI now selects four workers by default on the current Docker
  allocation; a caller may still provide a bounded override.
- The active legacy bootstrap path is intentionally retained as a bounded,
  report-only compatibility anchor; migrations and historical ADR text are not
  dead runtime support and must not be deleted in this slice.
- No additional complexity or unrelated user-worktree changes were identified.
