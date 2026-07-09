# Dashboard Evidence: Product Analytics Provider Rollout

**Feature**: `096-product-analytics-provider-rollout`

**Evidence status**: `planning_created`

This file is the metadata-only dashboard evidence template for the later
implementation pass. It intentionally contains no live provider IDs, screenshots,
visitor/account identifiers, event payload rows, meeting content, transcripts,
audio, signed URLs, local paths, cookies, or secrets.

## Current Planning Evidence

| Item | Status | Metadata-Only Evidence |
| --- | --- | --- |
| PostHog workspace | pending implementation | Self-hosted PostHog selected; Cloud excluded. |
| PostHog hosting | pending implementation | Same production server, separate analytics domain, portable later. |
| PostHog RBAC/access model | pending implementation | Role/audit expectations required; personal identifiers forbidden in evidence. |
| Provider lifecycle truth | pending implementation | Retention/deletion caveats required for provider data, backups, exports, and offline conversions. |
| Deploy dry-run handoff | pending implementation | Separate PostHog stack must be represented in deploy dry-run evidence without secret output. |
| PostHog autocapture | pending implementation | Approved for all current browser-rendered pages and future pages after credential suppression. |
| PostHog replay | blocked by default | Separate masking/storage/legal/QA proof required. |
| Yandex counter | pending implementation | Existing 093 production counter reuse selected; live ID not committed. |
| Yandex all-pages inventory | pending implementation | Inventory-gated; future pages default blocked for Yandex. |
| Yandex offline conversions | pending implementation | Exactly two approved conversion names. |
| Provider smoke | pending implementation | Smoke contract created; scripts not implemented in this planning pass. |
| Rollback | pending implementation | Rollback contract created; executable rollback not implemented in this planning pass. |
| Paid campaign launch | blocked | Not approved by this feature. |

## Required PostHog Dashboard Evidence

Later implementation must update this section with metadata-only proof.

| Dashboard | Required Metadata | Forbidden Evidence |
| --- | --- | --- |
| Source to first value funnel | dashboard exists, owner, event names, freshness, caveats | screenshots with visitor/account rows, raw payloads |
| First milestone dedupe | dashboard exists, dedupe rule, sample status without identifiers | user IDs, emails, cookies, client IDs |
| Account connection drop-off | dashboard exists, event names, aggregate visibility | account names, support notes, raw properties |
| Autocapture exploration | dashboard exists, page-class scope, credential suppression status | autocapture payload dumps, private DOM text screenshots |
| Delivery health | provider status, delivery gap count, smoke status | provider keys, request/response bodies |
| Access/RBAC audit readiness | access model status, audit-review status, export restrictions | user emails, personal names, account screenshots |
| Retention/deletion caveat | retention days, deletion truth statement, backup caveat | content-bearing exports |

## Required Yandex Dashboard Evidence

Later implementation must update this section with metadata-only proof.

| Dashboard Or Report | Required Metadata | Forbidden Evidence |
| --- | --- | --- |
| Sources by source/medium/campaign | report exists, date range, campaign caveat | visitor rows, raw click IDs |
| Public landing to download funnel | `/` and `/download` scope, goal names | live counter ID screenshots |
| Yandex Direct linkage | linkage status, campaign blocker status | OAuth token, account screenshots |
| Offline conversions | two conversion names, upload status, freshness | raw CSV rows, ClientID/Yclid/UserId values |
| Page-class scope | approved/blocked/replay-unavailable counts | private page screenshots |
| Webvisor/maps/forms availability | enabled/blocked by page class, proof status | session recordings or visitor data |
| Retention/deletion caveats | provider lifecycle statement, offline conversion caveat, rollback status | raw upload rows, visitor identifiers |

## Approved Conversion Names

Only these Yandex offline conversions are approved in 096:

- `desktop_account_connected`
- `first_value_session_completed`

## Evidence Update Rules

When implementation starts, update this file after each provider smoke pass with:

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
