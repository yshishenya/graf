# Product Activation Analytics 094

Status: 094 scaffold plus 096 provider layer implemented; self-hosted PostHog
delivery is live-safe validated in production, while Yandex offline upload,
product rollout readiness, and paid campaign launch remain blocked.

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
- PostHog, Yandex all-pages, Yandex offline conversions, replay, and direct
  desktop provider egress are disabled by default.
- Minimum approved analytics retention is 90 days.
- Direct desktop provider egress requires explicit legal, security, QA, provider
  smoke, and disclosure approval.

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
- public/auth pages use anonymous `graf_pseudo_browser_anonymous`; authenticated
  cabinet, settings, meeting, deletion, and embedded desktop pages use
  pseudonymous `graf_pseudo_*` identity metadata;
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
