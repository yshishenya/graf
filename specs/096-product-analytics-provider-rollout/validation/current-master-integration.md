# Feature 096 current-master integration receipt

Date: 2026-07-20

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
- Rollback execution-path check with the explicit local metadata-only guard:
  `rollback_execution=execute_confirmed_metadata_only`, no provider or product
  state changed, and `normal_product_workflows=preserved`.
- Rollback/provider/Yandex contract tests: `10 passed`; Yandex offline unit
  tests: `6 passed`.
- Public analytics contract drift was reconciled with 096 first-party
  PostHog autocapture: `7 passed` for the no-database controller/assets subset.
- Full server Ruff pass: `ruff check .` returned `All checks passed`.
- Provider/config/secret/retention/rollback/smoke/public contract subset:
  `34 passed` (database-backed public render cases remain excluded).
- Ruff over the changed server provider/API/public modules: pass.
- Targeted provider page/template contract checks:
  `8 passed` (`test_product_analytics_autocapture_pages` template contract,
  PostHog autocapture contract, replay/Webvisor boundaries).
- Direct synthetic render check for authenticated browser provider context:
  `browser-provider-render=pass` (one config script, pseudonymous user and
  workspace IDs).
- The accelerated PostgreSQL runner completed
  `tests/integration/test_product_analytics_autocapture_pages.py`: **3 passed**
  in 7 seconds, including public, auth, cabinet, and desktop rendered-page
  provider configuration. The disposable container was removed by the runner.
- The rendered-page check exposed and the integration fix restored the
  `provider_private_attrs` macro in the cabinet primitives template. The
  macro masks provider content without adding `data-ph-no-capture`, preserving
  first-party PostHog autocapture while protecting private values.
- Canonical `infra/scripts/ci-local.sh` at code SHA `0e467865` (later commits
  are documentation-only) passed:
  macOS **577 tests**, server **1910 passed, 1 skipped**, strict PostgreSQL/RLS
  subset **34 passed, 1 skipped**, Ruff, Python compile, production Compose
  rendering, and deployment-evidence scan. The RLS hardening step stayed at its
  documented `postgres_test` boundary because no live production probe was
  supplied; it did not fail the CI gate.
- `infra/scripts/cd-remote.sh --dry-run` passed with the separate PostHog
  handoff metadata and no execution or state change.
- `python -m compileall -q` over the changed server provider/admin/cabinet
  modules: pass.
- `git diff --check`: pass.

## T103 ordinary-workflow and identity-scope receipt

- Identity decision: this current integration slice supports only a real,
  previously bound Yandex `UserId`. `ClientId` and `Yclid` remain explicitly
  out of the live upload slice until a runtime resolver supplies their real
  values; the exporter rejects unresolved values instead of deriving them
  from the GRAF pseudonymous ID.
- The rollback execution-path check passed with the metadata-only guard and
  reported `normal_product_workflows=preserved`; no provider or product state
  was changed.
- `apps/server/scripts/run_local_postgres_tests.sh --focused -q
  tests/integration/test_recording_sync_conflicts.py
  tests/integration/test_processing_pickup.py
  tests/integration/test_cabinet_web_access_states.py
  tests/integration/test_cabinet_meeting_list.py` passed: **35 passed** in
  63 seconds. The disposable PostgreSQL container was removed by the runner.
- The same runner also passed the focused browser-session/auth subset:
  **5 passed, 30 deselected** in 16 seconds, covering owner-session cookies,
  provider callback return safety, email login, and the workspace-provider
  login page; its disposable container was removed as well.
- This receipt proves the ordinary recording-sync, processing-pickup, and
  cabinet web/list/auth paths remain intact on the current integration branch.
  It does not prove Yandex OAuth/live upload, PostHog operations, or product
  rollout approval.

## Not claimed

- The provider smoke above does not prove a real PostHog or Yandex production
  request; it uses synthetic values and fake transports.
- No production flags, provider secrets, dashboard data, or rollback state were
  changed.
- Local PostHog operational prerequisites are absent: no `graf-posthog-*`
  volumes and no runtime secret files were present, so backup/restore and live
  Yandex OAuth upload remain blocked rather than simulated.
- The full CI receipt covers the current integration SHA; production runtime
  enablement, Yandex OAuth/live upload, dashboard business review, and live
  RLS enforcement remain separate evidence gates.
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

## Read-only production runtime inventory

- SSH metadata check reached the existing production host and found the
  generated `graf-posthog` runtime running with its documented service family
  and all twelve documented persistent volume classes present.
- The production PostHog project-key secret file and the out-of-git Yandex OAuth
  secret file are present with redacted metadata; product analytics remains
  disabled in the runtime environment.
- The latest generated-stack inventory counted 33 running PostHog containers,
  0 unhealthy containers, and 0 containers with an enforced Docker memory/CPU
  limit in `HostConfig`; the resource-threshold review therefore remains open.
- An earlier read-only inventory counted 32 running containers and 8 explicit
  health states; the latest check supersedes that count for runtime status.
- `https://analytics.2brain.pro/_health/` returned `200 ok`; this proves service
  health only, not dashboard freshness, RBAC/audit, or business data review.
- A metadata-only backup and isolated restore rehearsal for all twelve
  generated-runtime volume classes passed under receipt `20260718T011751Z`.
  Archive SHA/tar integrity passed, the restored web health endpoint returned
  HTTP `200` with the approved analytics host header, all twelve rehearsal
  volumes were removed, and the GRAF readiness probe remained `ready`.
- No dashboard/RBAC mutation, provider enablement, or user-content export was
  performed. PostHog restarted as part of the controlled rehearsal and
  recovered to health after delayed migrations.
- Read-only PostHog schema/config review found one team with event retention
  configured to `84` months and one non-empty activity log with `4` rows; only
  counts, settings, and timestamps were inspected, never activity detail or
  user data.
- The same review found one organization, one membership, one project, no
  custom role/resource-access memberships, invitations enabled, project
  creation disabled, and no confirmed `enforce_2fa` value. Session-recording
  retention was unset. These are partial operational signals, not a completed
  RBAC/audit or lifecycle approval.
- Aggregate-only dashboard checks found one dashboard with eight items
  (created `2026-07-09`); ClickHouse contained three
  `desktop_first_opened` events and twenty `graf_web_autocapture_pageview`
  events, with latest timestamps on `2026-07-09`. No offline Yandex conversion
  events were present, and the provider/catalog remains disabled, so this is
  not current dashboard-freshness or campaign-goal evidence.

## T101 backup/restore subgate receipt

The backup/restore portion of T101 is now evidenced. The read-only schema/config
review adds partial retention and audit-surface evidence, but T101 stays open
for the independent RBAC/audit approval, complete retention/deletion lifecycle
coverage (including backups/exports/session data), dashboard freshness/goal
visibility, and concrete resource-alert threshold reviews.
The receipt is metadata-only and contains no secrets, event payloads, or
private host paths.

## T101 metadata-only operations continuation: 2026-07-18

The additional production review inspected counts, settings, and resource
metadata only. It did not inspect event rows, person rows, activity details,
exports, identifiers, or provider payloads.

| Review | Status | Metadata-only result |
| --- | --- | --- |
| Team retention | partial | One team reports `event_retention_months=84`; session-recording opt-in is false. The earlier day-field check appeared unset; the corrected 2026-07-20 recheck found policy string `5y`. |
| Session data | pass for current empty state | `posthog_sessionrecording` contains 0 rows and 0 rows with a retention period; this does not prove future lifecycle enforcement. |
| Exports | pass for current empty state | Exported assets, exported recordings, batch exports, batch-export runs, and batch-export downloads each have 0 rows. |
| Deletion requests | pass for current empty state | No PostHog data-deletion requests are present; provider-held deletion behavior still needs a documented lifecycle approval. |
| RBAC and MFA | partial | One organization exists; `enforce_2fa` is unset. Custom role, role-membership, organization-resource-access, and explicit-team-membership tables all contain 0 rows. |
| Audit surface | partial | Four activity records exist across `created` Dashboard/Organization/OrganizationMembership and `updated` User categories; no activity details or actor identifiers were inspected. |
| Log rotation | pass | Generated runtime containers report `json-file` rotation at `50m` with `3` files. |
| Resource limits | blocked | Host metadata reports 12 CPUs, 128703 MiB memory and 71% disk free; the 32 running PostHog containers have no enforced non-zero Docker CPU/memory limits. |
| Runtime health | pass | 32 PostHog containers are running without an unhealthy/restarting status; analytics health remains `200`. |

These results narrow T101's remaining work to independent RBAC/audit and
lifecycle approval, dashboard freshness/goal visibility, and applying/verifying
concrete alert/rollback thresholds for the generated stack.

## T101 production resource and health receipt: 2026-07-20

The generated production PostHog compose was hardened in place with a retained
out-of-git rollback copy. The first controlled restart exposed a latent web
mount mismatch: `/compose/start` used a relative `./compose/wait` path while the
generated compose mounted the directory elsewhere. The narrow fix changed the
web command and mount to the same `/code/compose` location; it did not change
provider flags, secrets, data volumes, or GRAF services.

| Check | Status | Metadata-only result |
| --- | --- | --- |
| Compose rendering | pass | `docker compose config` passed; 35 services, 35 CPU entries, 35 memory entries. |
| Runtime limits | pass | 33 running containers all report non-zero Docker `NanoCpus` and memory limits; web is `running` with restart count `0`. |
| Resource safety | pass | No PostHog container is `OOMKilled`; one historical non-zero restart count remains outside the web container and was not an OOM event. |
| Log rotation | pass | Generated containers report `json-file` rotation at `50m` with `3` files. |
| Disk headroom | pass | Analytics filesystem reports `29%` used (`71%` free), above the documented `20%` review and `10%` rollback boundaries. |
| Analytics health | pass | `https://analytics.2brain.pro/_health/` returned HTTP `200` on repeated probes after migrations completed. |
| GRAF readiness | pass | `https://rec.2brain.pro/api/v1/health/ready` returned HTTP `200`. |
| Rollback safety | partial | Compose rollback copies are retained and provider rollback remains fail-closed; no automated host alert/rollback service is installed. |

The resource/runtime subgate is therefore verified. T101 remains open because
the numeric thresholds are currently a documented operator contract, not an
automated alert receipt, and because independent RBAC/MFA, lifecycle/deletion,
and dashboard freshness/goal reviews are still missing.

## T101 corrected aggregate lifecycle and dashboard recheck: 2026-07-20

The fresh read-only review supersedes the earlier session-retention wording:
PostHog reports event retention `84` months and a session-recording policy of
`5y`; recording is opted out, with zero current recording rows. The separate
`retention_period_days` field is null, so this is a policy signal, not proof of
future deletion enforcement. Export/asset/recording/batch-export/download and
deletion-request counts are zero. Organization `enforce_2fa` remains unset;
custom roles, role memberships, resource-access rows, and explicit team
memberships remain empty; four audit-category records exist only for create or
user-update categories.

Dashboard review found one dashboard with eight saved items, no item refresh
timestamps, and aggregate provider events whose latest timestamp remains
2026-07-09. No approved Yandex conversion events are present. This is not a
freshness or goal-visibility approval.

## T102 live-safe Yandex upload receipt: 2026-07-20

- A separate Yandex OAuth application was created with the minimal
  `metrika:offline_data` permission. Its client metadata and OAuth credential
  remain outside git and outside committed evidence.
- The production host now has a non-empty Yandex OAuth secret file with mode
  `600`. The token value was never printed, logged, or committed; the temporary
  local handoff file was removed after provisioning.
- Production product-analytics flags remain disabled. The smoke used the
  current integration candidate source in a disposable container, passed
  `live_safe` approval gates only for that invocation, and did not recreate or
  modify the long-running production service.
- Exactly the approved conversion names were uploaded to the reused runtime
  counter: `desktop_account_connected` and `first_value_session_completed`.
  Both provider results were `live_safe_uploaded`.
- The smoke used a synthetic safe pseudonymous `UserId` path. This proves
  secret-file loading, OAuth authorization, request reachability, and provider
  acceptance for the two-row contract; it does not approve product rollout,
  campaign launch, dashboard freshness, or unresolved ClientId/Yclid paths.

## Remaining convergence tasks

T101 and T104 in `tasks.md` remain open (tracker issues #3857 and #3860). T102
is closed by the live-safe receipt above (tracker issue #3858). T103 is now explicitly scoped
and evidenced by the rollback-path and ordinary-workflow receipt above. The
completed T097–T100 receipts cover the clean branch transfer, manual
current-master reconciliation, current page and privacy contract validation,
bounded metadata-only smoke, and T102 covers the real two-event Yandex upload.
Remaining PostHog operations (dashboard/RBAC, retention/lifecycle, and resource
thresholds), approvals, release, and production receipt are still required
before Feature 096 can be accepted. The backup/restore subgate itself is now
passed.
