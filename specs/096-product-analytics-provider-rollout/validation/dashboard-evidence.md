# Dashboard Evidence: Product Analytics Provider Rollout

**Feature**: `096-product-analytics-provider-rollout`

**Evidence status**: `historical_branch_reference_current_integration_unaccepted`

This file is the metadata-only dashboard evidence for the 096 implementation and
review-remediation pass. Future live dashboard proof must keep the same
metadata-only shape. It intentionally contains no live provider IDs,
screenshots, visitor/account identifiers, event payload rows, meeting content,
transcripts, audio, signed URLs, local paths, cookies, or secrets.

## Current-master boundary

The production/runtime rows below are retained historical receipts from the
old 096 branch at `137565c0`; they are not evidence for current `master` or
the integration candidate PR #3852. Current-branch evidence is limited to
`validation/current-master-integration.md`: compile/default checks, Compose
config, page validation, synthetic metadata-only smoke, rollback dry-run,
ordinary-workflow regression, diff hygiene, and the T102 live-safe receipt.
T097–T100, T102, and T103 are closed by the current-master receipts; T101 and
T104 remain open. Do
not use historical rows to approve a release, production provider enablement,
or campaign launch.

## Current-master operations review: 2026-07-18

This continuation is aggregate-only and does not inspect event rows, persons,
activity details, exports, identifiers, or provider payloads.

| Review | Status | Metadata-only result | Remaining gate |
| --- | --- | --- | --- |
| PostHog backup/restore | subgate_pass | Twelve generated runtime volume classes passed archive integrity and isolated restore; GRAF readiness remained ready. | Independent ops approval. |
| Retention/session lifecycle | partial | At the 2026-07-18 snapshot the separate day field appeared unset; the 2026-07-20 recheck found event retention `84` months and policy string `5y`, with recording opted out and 0 current recordings. Export and deletion-request tables are empty. | Future lifecycle enforcement and backup/export deletion approval. |
| RBAC/audit | partial | One organization has unset `enforce_2fa`; custom role/resource-access tables are empty. Four audit-category records exist; only categories/counts were inspected. | Independent access/audit review and MFA decision. |
| Dashboard freshness | open | One dashboard with eight items and historical aggregate provider events is present; current business-goal freshness has not been independently approved. | Aggregate-only dashboard review. |
| Resource thresholds | blocked | Generated runtime has 32 healthy containers but no enforced Docker CPU/memory limits; host free disk is 71% and JSON logs rotate at `50m`/`3`. | Apply and verify concrete limits, alerts and rollback triggers. |

The resource row above is superseded by the 2026-07-20 runtime receipt below;
the RBAC, lifecycle and dashboard rows remain open.

## Current-master operations recheck: 2026-07-20

This recheck is aggregate-only and contains no event rows, persons, activity
details, exports, identifiers, screenshots, or provider payloads.

| Review | Status | Metadata-only result | Remaining gate |
| --- | --- | --- | --- |
| Resource limits | runtime_subgate_pass | Generated compose renders 35 services with 35 CPU and 35 memory entries; 33 running containers report non-zero Docker limits, zero OOM-killed containers, and web restart count `0`. | Automated alert/rollback receipt is still absent. |
| Health and disk | pass | Analytics health returned `200` repeatedly; GRAF readiness returned `200`; analytics filesystem is `29%` used. | Keep the documented `20%` review / `10%` rollback disk thresholds. |
| Log rotation | pass | All checked generated containers use `json-file` `50m`/`3` rotation. | Recheck after every generated-runtime update. |
| Session policy | policy_signal | Event retention is `84` months; session recording is opted out and the configured policy string is `5y`; current recording rows are `0`. | Prove future deletion behavior and owner approval; null day field is not enforcement proof. |
| RBAC and audit | partial | `enforce_2fa` is unset; custom roles/access memberships are empty; four audit-category rows cover only create/user-update categories. | Independent MFA/access and audit review. |
| Dashboard freshness | open | One dashboard has eight saved items with no refresh timestamps; latest aggregate provider events remain `2026-07-09`; no approved Yandex conversions are present. | Owner review of freshness, goals and smoke/test filtering. |

The 2026-07-20 production compose hardening and web startup-path repair were
performed outside git with retained rollback copies. They do not enable provider
delivery or product rollout.

## Current Planning Evidence

| Item | Status | Metadata-Only Evidence |
| --- | --- | --- |
| PostHog workspace | production_metadata_validated | Self-hosted PostHog selected; Cloud excluded; production workspace/project exists; project key remains runtime-only and redacted from evidence. |
| PostHog hosting | production_metadata_validated | Same production server, separate analytics domain, portable later; analytics domain health passed. |
| PostHog RBAC/access model | metadata_only_validated | Role/audit expectations documented; personal identifiers forbidden in committed evidence. |
| Provider lifecycle truth | metadata_only_validated | Retention/deletion caveats documented for provider data, backups, exports, and offline conversions. |
| Deploy dry-run handoff | metadata_only_validated | Separate PostHog stack is represented in deploy dry-run evidence without secret output. |
| PostHog autocapture | production_rendered_pages_verified | Real rendered public/auth/cabinet/settings/detail/deletion/desktop pages include first-party provider config; live public/auth route checks passed; future pages default enabled after inventory/suppression. |
| PostHog replay | blocked by default | Separate masking/storage/legal/QA proof required. |
| Yandex counter | metadata_only_validated | Existing 093 production counter reuse selected; live ID not committed. |
| Yandex all-pages inventory | metadata_only_validated | Inventory-gated; future pages default blocked for Yandex. |
| Yandex offline conversions | live_safe_verified_runtime_disabled | Exactly two approved conversion names were accepted by the provider in a two-event live-safe smoke using the out-of-git OAuth secret file and synthetic safe `UserId` path. Production runtime upload remains disabled; product rollout, dashboard freshness, and campaign launch remain separate gates. |
| Provider smoke | production_posthog_live_safe_verified | Provider smoke records dry-run delivery, live-safe transport proof, dashboard/goal metadata contract proof, blockers, and rollback without private payload output. Production PostHog web/desktop proxy delivery and aggregate ClickHouse presence were verified metadata-only. |
| Rollback | ready_not_executed | Rollback script records switches and product-impact rules in dry-run mode; no production state change performed. |
| Paid campaign launch | blocked | Not approved by this feature. |

## 096 Provider Readiness Metadata

This section is the closeout dashboard evidence record for 096. It is
metadata-only: no screenshots, visitor rows, provider exports, raw payloads,
provider IDs, tokens, cookies, or account/meeting data are committed.

| Surface | Owner Role | Purpose | provider delivery-gap caveat | retention/deletion caveat | RBAC/audit | Blocker Status | Rollback |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PostHog source to first value funnel | product analytics operator | product activation | Delivery gaps are measurement gaps, not product failures. | PostHog provider data/backups/exports require lifecycle caveats. | RBAC/audit documented for dashboard access, exports, replay, and retention changes. | product rollout readiness remains blocked; privacy/security/QA/disclosure approval remains separate. | rollback_status=ready_not_executed |
| PostHog autocapture exploration | product analytics operator | product learning | Autocapture delivery loss must be shown as a provider gap. | No content-bearing provider exports are committed; provider-held aggregates need truthful deletion caveats. | RBAC/audit required before live dashboard review. | replay remains disabled; Yandex Webvisor/maps/forms remain blocked. | rollback_status=ready_not_executed |
| Yandex public and offline reports | growth analytics operator | acquisition/offline conversion linkage | Offline upload failure is a reporting gap. | Already uploaded offline conversions and provider aggregates are not promised deleted by GRAF alone. | Counter/dashboard access is operator-only and evidence is redacted. | paid campaign launch remains blocked. | rollback_status=ready_not_executed |
| Provider lifecycle and blockers | privacy/security reviewer | review gate | Provider-gap caveats must be visible before decisions. | retention/deletion caveat required for every dashboard/report. | RBAC/audit review required for PostHog workspace. | legal/privacy/security/QA/disclosure/campaign/product rollout approvals remain separate from smoke. | rollback_status=ready_not_executed |

## 096 Convergence Live-Safe Metadata Proof

This convergence section records the extra proof added after the final analyze
pass. It is not a production execute log and does not include provider exports,
raw request bodies, visitor/account rows, screenshots, secrets, counter IDs,
ClientIDs, Yclids, cookies, or project keys.

| Check | Status | Metadata-Only Evidence | Still Blocked |
| --- | --- | --- | --- |
| Approval gates | pass | `live_safe` provider mode requires legal, privacy, security, QA, disclosure, dashboard, provider-smoke, rollback, and live-provider-delivery approval flags. | Product rollout and paid campaign launch. |
| Campaign launch | blocked_by_096 | `campaign_launch_allowed=false` even if campaign-readiness and provider-delivery flags are true. | Paid campaign launch requires a separate feature/gate. |
| PostHog server delivery | live_safe_transport_verified | Fake transport confirms self-hosted `/capture/` request construction, project-key secret-file loading, provider response handling, and redacted result metadata. Production runtime proof is recorded below. | Real dashboard data review. |
| PostHog browser autocapture | first_party_proxy_verified | Browser context exposes `/api/v1/product-analytics/posthog-web-capture`; JS uses `sendBeacon`/`fetch` to the first-party proxy and does not load PostHog Cloud/CDN SDK. | PostHog replay remains disabled. |
| PostHog rendered-page wiring | rendered_pages_verified | TestClient proof covers `/`, `/download`, `/privacy`, `/login`, `/sign-up`, `/meetings`, meeting detail, settings, calendar settings, deletion report, and embedded desktop pages with anonymous or pseudonymous `graf_pseudo_*` identity metadata only. Production runtime proof is recorded below. | Real provider dashboard review remains separate. |
| PostHog secret-material rejection | provider_smoke_verified | Provider smoke and endpoint tests reject token/secret-like autocapture material before dry-run success while allowing first-party product-visible identity context inside self-hosted PostHog. | Raw provider payloads and content-bearing exports remain forbidden in git. |
| PostHog desktop route | first_party_desktop_proxy_verified | macOS builds PostHog-style body with `event`, `distinct_id`, `properties`, and `api_key_state=server_injected_redacted`; no Authorization header or provider secret is shipped. | Direct desktop Yandex remains blocked. |
| Yandex offline upload | live_safe_transport_verified | Fake transport confirms Yandex offline upload URL, multipart CSV upload shape, OAuth secret-file loading, exactly two conversion names, `UserId` binding rule, and redacted result metadata. | Production Yandex upload and paid campaign launch. |
| Yandex live-safe upload | live_safe_runtime_verified | Disposable candidate-code smoke accepted exactly `desktop_account_connected` and `first_value_session_completed` with `live_safe_uploaded`; the OAuth secret file was present with mode `600`, and no token, counter ID, CSV row, or response body entered evidence. | Runtime flags stay disabled; product rollout, dashboard freshness, and paid campaign launch remain blocked. |
| Dashboard/goal visibility | metadata_only_contract_verified | Smoke verifies dashboard evidence contains PostHog dashboard names and Yandex conversion names only. | Screenshots and real provider rows remain forbidden in git. |

## Production Runtime Dashboard Metadata: 2026-07-09

This section records production runtime proof without screenshots, provider
exports, visitor/account rows, raw payloads, cookies, live counter IDs, project
keys, OAuth tokens, local paths, signed URLs, meeting content, transcripts, or
audio.

| Check | Status | Metadata-Only Evidence | Caveat |
| --- | --- | --- | --- |
| PostHog domain health | pass | Analytics domain `_health` returned `ok` through the internal route and external HTTPS route. | This is service health, not dashboard review. |
| GRAF provider catalog | pass | Runtime catalog reports product analytics enabled, `live_safe`, `parallel_measurement`, PostHog key configured/redacted, autocapture enabled, web-direct enabled, desktop-direct enabled, replay disabled, live provider delivery allowed, and no PostHog blockers. | Product rollout readiness remains separate. |
| Live rendered provider config | pass | `/`, `/download`, `/login`, and `/sign-up` include the product provider config. `/login` reports page class `login_signup`, PostHog enabled, autocapture enabled, replay disabled, Yandex disabled, and private attributes present. | Authenticated product pages still need periodic live QA after UI changes. |
| Web autocapture delivery | pass | First-party GRAF web proxy returned `live_safe_sent` for a metadata-only `graf_web_autocapture_pageview` smoke event. | Raw payload and visitor rows are not committed. |
| Desktop delivery | pass | First-party GRAF desktop proxy returned `live_safe_sent` for a metadata-only `desktop_first_opened` smoke event. | Direct desktop Yandex remains blocked. |
| PostHog storage freshness | pass | Aggregate ClickHouse query found one `graf_web_autocapture_pageview` smoke event and one `desktop_first_opened` smoke event. | This proves ingestion, not business dashboard correctness. |
| Production smoke | pass | Full production smoke passed with config validation, migration verification, upload smoke, auth cleanup, and artifact cleanup. | Verdict is `infra_smoke_ready`, not product rollout readiness. |
| Yandex public/all-pages inventory | partial pass | Runtime reports Yandex all-pages enabled with counter configured/redacted; inventory still limits Yandex to the approved public baseline classes and blocks/replay-unavailable classes. | Webvisor/maps/forms remain disabled. |
| Yandex offline upload | live_safe_verified_runtime_disabled | Candidate-code smoke accepted both approved conversion names; the long-running production runtime still reports Yandex offline disabled. | Product rollout, dashboard freshness, and paid campaign launch remain separate gates. |
| PostHog backup/restore | subgate pass; readiness follow-ups open | All twelve generated runtime volume classes passed metadata-only archive integrity and isolated restore; the restored web health endpoint returned `200`, and rehearsal volumes were removed. | RBAC/audit, retention/lifecycle, dashboard freshness, and resource-threshold reviews remain required before full long-term ops readiness. |
| PostHog image pinning | pass | Mutable generated-runtime image references were pinned by reviewed digest outside git; Compose config validation, mutable-tag scan, analytics health, and post-pinning live-safe smoke passed. | Repeat the pinning check after every future PostHog stack update. |

## Post-Runtime Dashboard/Counter Review: 2026-07-09

This section records metadata-only review follow-up after the user-reported
Yandex zero-data and admin audit/metrics usability issues. It contains no live
provider IDs, screenshots, visitor/account rows, raw payloads, cookies, names,
emails, meeting content, transcripts, audio, signed URLs, or private local
paths.

| Check | Status | Metadata-Only Evidence | Caveat |
| --- | --- | --- | --- |
| Yandex public counter visibility | consent_gated_pass | Public landing/download pages render Yandex counter config as configured/redacted. Browser verification showed no Yandex requests before consent and approved public Yandex goal requests after analytics/attribution consent. | Zero Yandex dashboards can still be expected if visits do not grant analytics consent or Yandex reporting is delayed/filtered. |
| Yandex page scope | pass | `/` and `/download` remain the only approved public baseline pages; login/auth/admin/product-private classes stay blocked or replay-unavailable for Yandex. | Webvisor/maps/forms remain disabled. |
| Public analytics duplicate controller | fixed_locally_pending_deploy | Branch rendering now includes one shared `analytics.js` controller for public pages and has a duplicate-load guard. | Production needs the next app deploy before this local duplicate-script fix is live. |
| Admin audit dashboard usability | pass | Audit rows now show when, actor, action, object, outcome, source, and drill-down link labels across admin/auth/egress/lifecycle sources. | Audit evidence remains metadata-only; private content is still excluded. |
| Admin metrics dashboard usability | pass | Metrics cards now show Russian family labels, questions, source meaning, detail links, and audit-source breakdowns. | This improves admin observability; it is not product rollout readiness. |

## Final Live Dashboard Transport Proof: 2026-07-09

This final closeout section records live transport/dashboard-readiness evidence
after production deploy to SHA `f12b8761538a31152a1cf3db9780643cb55d1301`.
It contains no provider IDs, screenshots, visitor/account rows, raw payloads,
cookies, names, emails, meeting content, transcripts, audio, signed URLs, or
private local paths.

| Check | Status | Metadata-Only Evidence | Caveat |
| --- | --- | --- | --- |
| App and analytics health | pass | GRAF health returned `ready`; PostHog analytics health returned `ok`. | Health is not product rollout readiness. |
| Analytics script deployment | pass | Live `/`, `/download`, and `/login` each rendered exactly one versioned analytics controller script. | Authenticated product/admin pages still need periodic operator QA. |
| PostHog live-safe transport | pass | Web and desktop first-party capture endpoints returned `live_safe_sent` after deploy. | Smoke activity can appear in analytics and should be filtered in business dashboards. |
| PostHog storage aggregate | pass | Recent aggregate storage contained the expected web autocapture and desktop activation event names. | No event properties, person rows, screenshots, or exports are committed. |
| Yandex consent-gated public transport | pass | Browser/CDP proof showed no Yandex traffic before consent and approved public landing goal traffic after analytics/attribution consent. | Yandex dashboards can remain zero for no-consent traffic, provider delay, filters, or blockers. |
| Admin observability surface | pass | Deployed admin audit/metrics now expose actor/action/object/outcome/source/detail context and metric breakdowns. | Authenticated production review requires an operator session and metadata-only notes. |

## Required PostHog Dashboard Evidence

Metadata-only 096 implementation evidence for PostHog is recorded below. No
screenshots, visitor/account rows, raw payloads, content-bearing exports, project
keys, cookies, local paths, signed URLs, transcript text, meeting content, or
audio references are included.

| Dashboard | Status | Owner Role | Required Metadata | Caveats |
| --- | --- | --- | --- | --- |
| Source to first value funnel | live_safe_smoke_metadata_verified | product analytics operator | Event names: `desktop_first_opened`, `desktop_account_connected`, `desktop_autorecord_enabled`, `first_recording_completed`, `first_result_viewed`, `first_value_session_completed`; production smoke proved `desktop_first_opened` ingestion metadata-only | Internal/support/smoke/test activity may be counted; delivery gaps must be shown. |
| First milestone dedupe | drafted_metadata_only | product analytics operator | Dedupe by stable pseudonymous user; no raw user IDs in evidence | Provider aggregates may remain after GRAF deletion unless provider action is verified. |
| Account connection drop-off | drafted_metadata_only | product analytics operator | Event names only; aggregate visibility pending live provider smoke | No account names, emails, or support notes in committed evidence. |
| Autocapture exploration | live_safe_smoke_metadata_verified | product analytics operator | Page-class scope: all current browser-rendered pages; production smoke proved `graf_web_autocapture_pageview` ingestion metadata-only | Autocapture is first-party PostHog only; no raw autocapture exports in git. |
| Delivery health | production_metadata_verified | infrastructure operator | Provider status, delivery-gap status, smoke status, domain health, service health, and production smoke status | Measurement gaps do not block product workflows. |
| Access/RBAC audit readiness | drafted_metadata_only | infrastructure operator | Role-based access model and audit expectation documented | No personal names or emails in evidence. |
| Retention/deletion caveat | drafted_metadata_only | privacy/security reviewer | Minimum 90-day retention baseline; provider lifecycle records documented | Backups, aggregates, and exports require truthful caveats. |

## Required Yandex Dashboard Evidence

Metadata-only 096 implementation evidence for Yandex is recorded below. No live
counter IDs, OAuth tokens, ClientIDs, Yclids, cookies, raw CSV rows, screenshots,
visitor/account data, raw payloads, signed URLs, or private local paths are
included.

| Dashboard Or Report | Status | Owner Role | Required Metadata | Caveats |
| --- | --- | --- | --- | --- |
| Sources by source/medium/campaign | drafted_metadata_only | growth analytics operator | Existing 093 counter strategy; campaign report status pending provider dashboard review | Paid campaign launch remains blocked. |
| Public landing to download funnel | preserved_metadata_only | growth analytics operator | `/` and `/download` remain approved public baseline | Live counter ID screenshots are forbidden. |
| Yandex Direct linkage | blocked_for_campaign_launch | growth analytics operator | Linkage status is runtime-only/redacted | Technical provider setup does not approve campaign launch. |
| Offline conversions | live_safe_verified_runtime_disabled | growth analytics operator | Conversion names: `desktop_account_connected`, `first_value_session_completed`; both candidate-code live-safe uploads returned `live_safe_uploaded`; the proven path uses a safe pseudonymous `UserId` bound by the existing Yandex identity contract | Long-running production upload remains disabled; raw CSV rows, token values, and identity values are forbidden. |
| Page-class scope | drafted_metadata_only | privacy/security reviewer | Approved: 2 public page classes; blocked/replay-unavailable classes recorded in inventory | Future pages default blocked for Yandex. |
| Webvisor/maps/forms availability | blocked_by_default | privacy/security reviewer | No page class has Webvisor/maps/forms proof in 096 | PostHog autocapture does not approve Yandex behavior replay. |
| Retention/deletion caveats | drafted_metadata_only | privacy/security reviewer | Yandex page events/offline conversions/provider aggregates have lifecycle caveats | Already uploaded offline conversions and provider aggregates are not promised deleted by GRAF user deletion. |

## Approved Conversion Names

Only these Yandex offline conversions are approved in 096:

- `desktop_account_connected`
- `first_value_session_completed`

## Evidence Update Rules

For later live dashboard updates, update this file after each provider smoke pass with:

- provider name;
- environment name without live identifiers;
- dashboard/report name;
- dashboard/report owner;
- status: `pending`, `pass`, `blocked`, or `rollback_verified`;
- event or conversion names only;
- freshness or date range without visitor-level data;
- caveats and blockers;
- RBAC/access status where the dashboard depends on PostHog data;
- retention/deletion lifecycle status where the dashboard/report uses provider-held data;
- validation command name;
- rollback status.

Do not paste screenshots with account data. Do not paste raw network payloads.
Do not paste Yandex CSV rows. Do not paste PostHog event exports. Do not paste
secret-file paths if the path exposes private local structure.
