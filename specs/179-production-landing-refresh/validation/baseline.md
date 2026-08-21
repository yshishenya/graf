# Baseline and local validation

- Branch: `codex/179-production-landing-refresh`
- Starting SHA: `bf7c8d4fde9504bf9ca57bae9e3b183a560c5fdc`
- Local Docker/PostgreSQL runtime: unavailable on this Mac; the repository test fixture correctly refused to run database-backed tests without `TWOBRAIN_DATABASE_URL`.
- Initial focused run: database-independent assertions passed; database-backed cases stopped at fixture setup rather than using a substitute database.
- Current database-independent focused gate: 30 tests pass in the final local rerun, including catalog/launch-gate truth, price rendering, static assets, headers, analytics contracts, checkout snapshots and preservation of private product analytics. Eight database-backed public-page cases and one analytics-default case were not run because Docker/PostgreSQL is unavailable on this Mac; the fixture failed closed before any test database was used.
- `ruff check src tests`: pass.
- `node --check` for `landing.js` and `analytics.js`: pass.
- `git diff --check`: pass.
- Canonical local `infra/scripts/ci-local.sh --fast` was attempted against the final branch and stopped before server tests because Docker Engine is unavailable; the script failed closed and removed no container.
- Repository fast lane on an isolated temporary checkout at `2brain.dev`: pass; 1,116 unit tests, server lint and Python compile checks passed. The test fixture created and removed its own PostgreSQL container; the production database and running application containers were not used.
- Historical fast-lane tested implementation SHA: `982fba42e1bf4b56a11d9778ca2e77e48cadecb6`. The pushed commits `4fbdad2`, `eea5b6d` and `7f6a7fe` also change executable code; the focused checks above were rerun against executable head `7f6a7fef966976123a64196fbbb45386f161643c`. Current branch head `d3d7f4e111018440788b3189d610d95acf6f4f1a` adds documentation only.

The fast lane is sufficient for PR feedback under the repository policy. The mandatory full exact-SHA lane remains part of the separately approved production execution gate.
