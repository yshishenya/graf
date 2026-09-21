# Product Activation Analytics 094

Status: 094 scaffold plus 096 provider layer plus 273 measurement levels
implemented; self-hosted PostHog delivery is live-safe validated in production,
while Yandex offline upload, product rollout readiness, and paid campaign launch
remain blocked. 273 adds the three legal measurement levels, the click-to-first
value funnel, the report set, and the launch approval gate.

## Scope

094 adds a safe product activation analytics contract and validation surface for:

```text
public_installer_download_clicked
-> desktop_first_opened
-> desktop_account_connected
-> desktop_autorecord_enabled
-> first_recording_completed
-> first_result_viewed
-> first_value_session_completed
```

PostHog self-hosted remains the preferred primary product analytics workspace.
Yandex remains a parallel all-web-pages/ad/Webvisor/offline-conversion surface
only after masking, sanitization, legal, QA, provider smoke, and rollout gates.

094 itself did not enable live PostHog delivery, Yandex all-pages expansion,
Yandex offline uploads, production deploy, or paid campaign optimization. 096
adds the provider layer after 094 and validates self-hosted PostHog delivery,
but still does not approve product rollout readiness or paid campaign launch.

## Default Runtime State

- `TWOBRAIN_PRODUCT_ANALYTICS_ENABLED=false`
- `TWOBRAIN_PRODUCT_ANALYTICS_VALIDATION_MODE=disabled`
- `TWOBRAIN_PRODUCT_ANALYTICS_PROVIDER_MODE=disabled`
- `TWOBRAIN_PRODUCT_ANALYTICS_ANONYMOUS_AGGREGATE_ENABLED=true`
- PostHog, Yandex all-pages, Yandex offline conversions, replay, and direct
  desktop provider egress are disabled by default.
- Direct desktop provider egress requires explicit legal, security, QA, provider
  smoke, and disclosure approval.

## Consent Copy Revision

The runtime consent copy revision is `2026-09-15.1`. Each repository copy of a
published analytics document names this exact revision independently; a revision
mentioned by one document cannot satisfy the check for another document. The
checked copies are:

- `docs/analytics/product-activation-analytics.md`;
- `specs/273-paid-traffic-analytics/contracts/operations.md`.

This repository check does not confirm copies hosted outside the repository or
the provider retention setting in the analytics cabinet; those remain operator
confirmations before launch.

## Measurement Levels And Retention

273 splits measurement into three levels. Each level has its own legal basis,
its own storage, and its own retention term. Level 1 is on by default; the two
levels that process personal data are off by default.

| Level | What it measures | Legal basis | Storage | Retention | Default |
|---|---|---|---|---|---|
| 1 `anonymous_aggregate` | visits to every public page, including visitors who gave no consent | no personal data | GRAF PostgreSQL | 1095 days | on |
| 2 `attribution_profiles` | campaign attribution and registered-user data | contract / legitimate interest | GRAF PostgreSQL | 1095 days for the client acquisition attribute, 90 days for the visit attribution row | off |
| 3 `provider_analytics` | consent-based measurement, including replay | consent | self-hosted PostHog ClickHouse | 365 days, replay 90 days | off |

Level 1 is on because two requirements need it: FR-009 requires the anonymous
count on every public page including visitors who gave no consent, and FR-012
needs that count as the denominator of the consent share. It keeps no
identifier, no device address and no link between visits, so it carries no
personal data and needs no consent. Setting
`TWOBRAIN_PRODUCT_ANALYTICS_ANONYMOUS_AGGREGATE_ENABLED=false` stops level 1
counting on public pages and on web registration steps without touching the
optional levels.

The terms are not restated here as the source of truth: they live in
`product_analytics/retention.py` and are read from there by the level
definitions in `product_analytics/provider_config.py`. If a category has no
retention term, configuration fails rather than defaulting.

Level 1 never leaves GRAF. It stores coarse dimensions (`bucket_date`,
`bucket_hour`, `surface`, `landing_path`, `source`, `medium`, `campaign`,
`content`, `term`, `device_class`, `referrer_category`, `traffic_class`) and a
visit counter. It must not store a device address, a session identifier, a user
agent, a device fingerprint, or any pseudonym, and it must not link visits to
each other. Reporting reads only buckets at or above
`MINIMUM_AGGREGATE_BUCKET_SIZE` (3) and only the `external` traffic class, so
internal, support, test, and automated visits are collected with their marker
but never reported.

There is deliberately **no** shared anonymous provider identifier. An earlier
build handed every anonymous visitor the same `graf_pseudo_browser_anonymous`
value. That was wrong twice over: a single value reused by everybody is a
long-lived identifier, and it merges unrelated visits into one person, which
FR-010 forbids. That constant no longer exists. A visitor without a
pseudonymous identity has no provider identity at all and is measured by the
level 1 aggregate instead; provider-facing endpoints refuse an event that
carries no per-person pseudonym.

Level 3 additionally requires every approval record to be present. A technical
flag can hold a level back, but it cannot switch one on by itself.

## Restore And Retention Operations

Anonymous aggregate rows are ordinary GRAF PostgreSQL data and come back with
the GRAF database. Provider events, replay, and level 3 measurement live in the
PostHog stack and are restored from the PostHog backup, not from the GRAF
database. That split matters during an incident: restoring GRAF alone leaves
level 3 empty, and restoring PostHog alone leaves level 1 and the client
acquisition attribute at whatever the GRAF database holds.

Runbooks:

- backup, restore, and what is lost without a copy: `infra/posthog/backup-restore.md`
- retention enforcement and event TTL: `infra/posthog/clickhouse-retention.sql`,
  `infra/scripts/enforce-product-analytics-retention.sh`
- storage baseline and growth: `docs/analytics/product-analytics-capacity-baseline.md`
- alert ownership and escalation: `infra/posthog/alert-rules.txt`

## Reports

The report set, its owners, its mandatory caveats, and how it handles a gap in
data are defined in `docs/analytics/product-analytics-reports.md`, with machine
readable definitions under `infra/analytics/dashboards/`. Reports show a gap as
a gap: an empty dashboard means delivery was switched off, not that nobody was
interested.

Launch approvals are separate from reports and are described in
`docs/analytics/product-analytics-launch-approval.md`.

## Safe Event Contract

Allowed product events are stable and allowlisted in server code:

- `desktop_first_opened`
- `desktop_account_connected`
- `desktop_autorecord_enabled`
- `first_recording_completed`
- `first_result_viewed`
- `first_value_session_completed`

Forbidden everywhere:

- raw email, phone, full names, organization/account/workspace names;
- raw user/account/workspace/meeting/device IDs;
- meeting title, participants, transcript, summary text, audio, calendar text;
- local paths, object keys, signed URLs, tokens, cookies, passwords, passcodes;
- private free text and user-provided filenames.

## Telemetry Gate

Normal desktop/cabinet/product use requires one personal acceptance of the
bounded telemetry package. If the user withdraws or refuses updated mandatory
terms, normal product use stops and only account/legal/export/deletion flows
remain available. Provider outage does not block accepted product use; it is
reported as a measurement gap.

## Provider Boundaries

PostHog:

- primary full-funnel workspace after approval;
- 094 wrapper was disabled by default;
- 096 adds self-hosted PostHog live-safe delivery, while product rollout
  readiness remains separately blocked.

Yandex:

- public `/` and `/download` remain the only approved live scope from 093;
- all-pages inventory exists, but non-public classes are blocked or
  replay-unavailable until evidence passes;
- default offline conversion subset is only:
  `desktop_account_connected`, `first_value_session_completed`.

## Page And Replay State

Approved now:

- `public_landing`
- `public_download`

Blocked or pending for 094 rollout:

- auth callback and admin are blocked;
- cabinet, meeting detail, upload, deletion, embedded desktop webview, login,
  legal, and error classes require sanitization and legal/QA proof;
- replay/Webvisor/click maps/scroll maps/form analytics stay disabled on
  replay-unavailable classes.

## Dashboard Caveats

Every 094 dashboard must disclose:

- internal/support/smoke/test activity is counted by default;
- provider delivery loss is a measurement gap, not a user-facing failure;
- first desktop open can be unlinked or weakly linked until account connection;
- `desktop_account_connected` is the first reliable default campaign-linked
  product milestone;
- exported reports and provider-held aggregate reports may remain outside
  direct GRAF erasure control.

## Validation Commands

Focused server checks:

```sh
cd apps/server
uv run pytest \
  tests/unit/test_product_activation_analytics.py \
  tests/contract/test_product_activation_analytics_contract.py \
  tests/integration/test_product_activation_analytics_rollout.py
```

Focused macOS check:

```sh
cd apps/macos
swift test --filter ProductActivationAnalyticsContractTests
```

Smoke helpers:

```sh
infra/scripts/run-product-analytics-smoke.sh
infra/scripts/validate-product-analytics-pages.sh
```

Full local gate remains:

```sh
infra/scripts/ci-local.sh
```

## 096 Provider Rollout Addendum

Status: self-hosted PostHog runtime delivery is live-safe validated; Yandex
offline upload, production product rollout readiness, and paid campaign launch
remain blocked.

096 extends the 094 scaffold with a production-ready provider layer:

- self-hosted first-party PostHog is the primary product analytics workspace;
- Yandex remains the parallel public/ad/offline-conversion surface;
- runtime secrets stay outside git and are read through secret files only;
- provider evidence stays metadata-only.

Disabled-by-default production deploys do not require live provider secret files
to exist. The app Compose mounts optional provider secret slots from the
committed empty `infra/secret-placeholders/disabled_optional_provider_secret`
placeholder until operators set the host-side `*_SECRET_FILE` variables to
out-of-git files under `infra/secrets/`. The in-container paths stay
`/run/secrets/...` when providers are enabled.

PostHog broad autocapture:

- first-party PostHog autocapture is enabled for every current
  browser-rendered page class and for future browser-rendered pages by default;
- authenticated cabinet, settings, meeting, deletion, and embedded desktop pages
  use pseudonymous `graf_pseudo_*` identity metadata;
- public pages no longer send a shared anonymous identifier. An earlier build
  used `graf_pseudo_browser_anonymous` for public and auth pages; 273 removed it
  because one value reused by every visitor is both a long-lived identifier and
  a link between unrelated visits. An unidentified visitor is measured by the
  level 1 aggregate and is not sent to a provider at all;
- self-hosted PostHog may receive owner-controlled product-visible context that
  GRAF can already display to authorized operators;
- credential/content suppression is still mandatory: pages and shared
  primitives use private attributes such as `data-ph-mask`, not committed raw
  payload examples;
- credentials, tokens, signed URLs, cookies, local paths, raw audio,
  transcript/meeting-content dumps, and raw payload dumps remain forbidden;
- PostHog replay is a separate capability and remains disabled;
- replay can be considered later only after page-class masking, legal, QA, and
  evidence proof;
- disabling PostHog provider flags must leave normal product workflows running
  and create only a measurement gap.

Yandex separation:

- existing 093 public `/` and `/download` scope is preserved;
- non-public, admin, callback, meeting/detail, upload, deletion, embedded, and
  future page classes remain blocked or replay-unavailable for Yandex until
  inventory evidence changes;
- Webvisor, click map, scroll map, and form analytics remain disabled;
- offline conversions are limited to `desktop_account_connected` and
  `first_value_session_completed`;
- Yandex offline upload with `UserId` requires that the same pseudonymous ID was
  sent during an eligible Yandex-counted browser session through `setUserID` and
  `userParams`; `ClientId`/`Yclid` require real runtime resolver values and
  cannot be replaced by a GRAF pseudonym;
- paid campaign launch remains blocked until a separate campaign readiness
  approval exists.

Desktop direct provider route:

- direct desktop provider egress is allowed only for first-party PostHog after
  explicit config and approval flags;
- direct desktop Yandex provider egress remains blocked;
- desktop request construction must not include provider secrets or raw private
  identifiers.

096 validation helpers:

```sh
infra/scripts/run-product-analytics-provider-smoke.sh
infra/scripts/validate-product-analytics-provider-pages.sh
```
