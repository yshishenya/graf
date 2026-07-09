# Dashboard Evidence: Product Analytics Provider Rollout

**Feature**: `096-product-analytics-provider-rollout`

**Evidence status**: `metadata_only_live_safe_verified`

This file is the metadata-only dashboard evidence for the 096 implementation and
review-remediation pass. Future live dashboard proof must keep the same
metadata-only shape. It intentionally contains no live provider IDs,
screenshots, visitor/account identifiers, event payload rows, meeting content,
transcripts, audio, signed URLs, local paths, cookies, or secrets.

## Current Planning Evidence

| Item | Status | Metadata-Only Evidence |
| --- | --- | --- |
| PostHog workspace | metadata_only_validated | Self-hosted PostHog selected; Cloud excluded; runbook and Compose handoff validated without live secrets. |
| PostHog hosting | metadata_only_validated | Same production server, separate analytics domain, portable later; production execute not run. |
| PostHog RBAC/access model | metadata_only_validated | Role/audit expectations documented; personal identifiers forbidden in committed evidence. |
| Provider lifecycle truth | metadata_only_validated | Retention/deletion caveats documented for provider data, backups, exports, and offline conversions. |
| Deploy dry-run handoff | metadata_only_validated | Separate PostHog stack is represented in deploy dry-run evidence without secret output. |
| PostHog autocapture | rendered_pages_verified | Real rendered public/auth/cabinet/settings/detail/deletion/desktop pages include first-party provider config; future pages default enabled after inventory/suppression. |
| PostHog replay | blocked by default | Separate masking/storage/legal/QA proof required. |
| Yandex counter | metadata_only_validated | Existing 093 production counter reuse selected; live ID not committed. |
| Yandex all-pages inventory | metadata_only_validated | Inventory-gated; future pages default blocked for Yandex. |
| Yandex offline conversions | user_id_binding_rule_validated | Exactly two approved conversion names; `UserId` upload requires prior Yandex `setUserID`/`userParams` binding. |
| Provider smoke | metadata_only_live_safe_verified | Provider smoke records dry-run delivery, live-safe transport proof, dashboard/goal metadata contract proof, blockers, and rollback without private payload output. |
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
| PostHog server delivery | live_safe_transport_verified | Fake transport confirms self-hosted `/capture/` request construction, project-key secret-file loading, provider response handling, and redacted result metadata. | Production PostHog execute and real dashboard data review. |
| PostHog browser autocapture | first_party_proxy_verified | Browser context exposes `/api/v1/product-analytics/posthog-web-capture`; JS uses `sendBeacon`/`fetch` to the first-party proxy and does not load PostHog Cloud/CDN SDK. | PostHog replay remains disabled. |
| PostHog rendered-page wiring | rendered_pages_verified | TestClient proof covers `/`, `/download`, `/privacy`, `/login`, `/sign-up`, `/meetings`, meeting detail, settings, calendar settings, deletion report, and embedded desktop pages with anonymous or pseudonymous `graf_pseudo_*` identity metadata only. | Production execute and real provider dashboard review remain separate. |
| PostHog secret-material rejection | provider_smoke_verified | Provider smoke and endpoint tests reject token/secret-like autocapture material before dry-run success while allowing first-party product-visible identity context inside self-hosted PostHog. | Raw provider payloads and content-bearing exports remain forbidden in git. |
| PostHog desktop route | first_party_desktop_proxy_verified | macOS builds PostHog-style body with `event`, `distinct_id`, `properties`, and `api_key_state=server_injected_redacted`; no Authorization header or provider secret is shipped. | Direct desktop Yandex remains blocked. |
| Yandex offline upload | live_safe_transport_verified | Fake transport confirms Yandex offline upload URL, multipart CSV upload shape, OAuth secret-file loading, exactly two conversion names, `UserId` binding rule, and redacted result metadata. | Production Yandex upload and paid campaign launch. |
| Dashboard/goal visibility | metadata_only_contract_verified | Smoke verifies dashboard evidence contains PostHog dashboard names and Yandex conversion names only. | Screenshots and real provider rows remain forbidden in git. |

## Required PostHog Dashboard Evidence

Metadata-only 096 implementation evidence for PostHog is recorded below. No
screenshots, visitor/account rows, raw payloads, content-bearing exports, project
keys, cookies, local paths, signed URLs, transcript text, meeting content, or
audio references are included.

| Dashboard | Status | Owner Role | Required Metadata | Caveats |
| --- | --- | --- | --- | --- |
| Source to first value funnel | drafted_metadata_only | product analytics operator | Event names: `desktop_first_opened`, `desktop_account_connected`, `desktop_autorecord_enabled`, `first_recording_completed`, `first_result_viewed`, `first_value_session_completed`; freshness pending live provider smoke | Internal/support/smoke/test activity may be counted; delivery gaps must be shown. |
| First milestone dedupe | drafted_metadata_only | product analytics operator | Dedupe by stable pseudonymous user; no raw user IDs in evidence | Provider aggregates may remain after GRAF deletion unless provider action is verified. |
| Account connection drop-off | drafted_metadata_only | product analytics operator | Event names only; aggregate visibility pending live provider smoke | No account names, emails, or support notes in committed evidence. |
| Autocapture exploration | drafted_metadata_only | product analytics operator | Page-class scope: all current browser-rendered pages; credential suppression required | Autocapture is first-party PostHog only; no raw autocapture exports in git. |
| Delivery health | drafted_metadata_only | infrastructure operator | Provider status, delivery-gap status, smoke status | Measurement gaps do not block product workflows. |
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
| Offline conversions | user_id_binding_rule_validated | growth analytics operator | Conversion names: `desktop_account_connected`, `first_value_session_completed`; dry-run/live-safe fake transport status pass; `UserId` requires rendered-page `setUserID`/`userParams` binding | Raw CSV rows and identity values are forbidden. |
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
