# Baseline and local validation

- Branch: `codex/179-production-landing-refresh`
- Starting SHA: `bf7c8d4fde9504bf9ca57bae9e3b183a560c5fdc`
- Local Docker/PostgreSQL runtime: unavailable on this Mac; the repository test fixture correctly refused to run database-backed tests without `TWOBRAIN_DATABASE_URL`.
- Initial focused run: database-independent assertions passed; database-backed cases stopped at fixture setup rather than using a substitute database.
- Current database-independent focused gate: 36 distinct tests pass, including catalog/launch-gate truth, price rendering, static assets, headers, analytics contracts, checkout snapshots and preservation of private product analytics.
- `ruff check src tests`: pass.
- `node --check` for `landing.js` and `analytics.js`: pass.
- `git diff --check`: pass.
- Repository fast lane on an isolated temporary checkout at `2brain.dev`: pass; 1,116 unit tests, server lint and Python compile checks passed. The test fixture created and removed its own PostgreSQL container; the production database and running application containers were not used.
- Fast-lane tested implementation SHA: `982fba42e1bf4b56a11d9778ca2e77e48cadecb6`, the code commit in this candidate. The later pushed commit `450ae4722d70fed52e6962acfe16d4b07ead958` contains documentation-only release evidence and does not change executable code.

The fast lane is sufficient for PR feedback under the repository policy. The mandatory full exact-SHA lane remains part of the separately approved production execution gate.
