# Feature 096 current-master integration receipt

Date: 2026-07-18

## Scope transferred

- Product analytics provider modules, API contracts, rendered provider context,
  macOS direct-PostHog contract, provider-specific tests, PostHog/Yandex
  runbooks, and bounded smoke/rollback/page-validation scripts were transferred
  from the historical 096 branch onto a clean branch based on current master.
- Existing Features 097–111 files were not replaced by a wholesale merge or
  rebase of the historical branch.
- Provider runtime defaults remain disabled and live approval gates remain
  fail-closed.

## Bounded checks

- `python -m compileall -q` over the changed server provider/API/public modules:
  pass.
- Provider defaults self-check (`Settings`, redacted provider config, readiness):
  `provider-defaults=pass`.
- `docker compose -f infra/posthog/docker-compose.posthog.yml config`: pass.
- `infra/scripts/validate-product-analytics-provider-pages.sh`: pass.
- `infra/scripts/run-product-analytics-provider-smoke.sh`: pass with synthetic
  metadata-only/fake transports.
- `infra/scripts/rollback-product-analytics-providers.sh --dry-run`: pass with
  `dry_run_no_state_change`.
- Ruff over the changed server provider/API/public modules: pass.
- Targeted provider page/template contract checks:
  `8 passed` (`test_product_analytics_autocapture_pages` template contract,
  PostHog autocapture contract, replay/Webvisor boundaries).
- Direct synthetic render check for authenticated browser provider context:
  `browser-provider-render=pass` (one config script, pseudonymous user and
  workspace IDs).
- Targeted rendered-page integration test was not started because this clean
  worktree has no `TWOBRAIN_DATABASE_URL`; the fixture explicitly requires the
  repository's local-Postgres test runner. No long test run was started.
- `python -m compileall -q` over the changed server provider/admin/cabinet
  modules: pass.
- `git diff --check`: pass.

## Not claimed

- The provider smoke above does not prove a real PostHog or Yandex production
  request; it uses synthetic values and fake transports.
- No production flags, provider secrets, dashboard data, or rollback state were
  changed.
- Full repository CI was not rerun in this turn by user instruction; this
  receipt is bounded evidence only.
- The targeted contract checks do not replace the database-backed rendered
  page test; that test remains open until the local Postgres test environment is
  available.

## Read-only production probe

- `GET https://rec.2brain.pro/api/v1/health/ready`: `{"status":"ready"}`.
- `GET https://rec.2brain.pro/api/v1/product-analytics/catalog` reported
  `enabled=false`, `validation_mode=disabled`, `provider_mode=disabled`, all
  PostHog/Yandex provider states disabled, and rollout readiness `blocked`.

This confirms that the candidate PR has not been deployed or enabled in
production; it is not provider delivery or dashboard evidence.

## Remaining convergence tasks

T097–T104 in `tasks.md` remain open. In particular, the current page inventory,
real PostHog backup/restore and dashboard/RBAC review, Yandex OAuth/live upload,
executed rollback, ClientId/Yclid resolver decision, approvals, release, and
production receipt are still required before Feature 096 can be accepted.
