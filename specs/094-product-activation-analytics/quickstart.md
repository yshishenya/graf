# Quickstart: Product Activation Analytics Validation

**Feature**: `094-product-activation-analytics`

This guide validates planning artifacts now and defines the expected future
implementation checks. It does not enable product analytics.

## Current Planning Validation

Run from repository root:

```sh
git diff --check
.specify/scripts/bash/check-prerequisites.sh --json --paths-only
```

Expected:

- no whitespace/diff errors
- feature paths point to `specs/094-product-activation-analytics`
- no implementation files are required for this planning pass

Review artifacts:

```sh
rg -n "^\\s*\\[NEEDS CLARIFICATION\\]|NEEDS CLARIFICATION:" \
  specs/094-product-activation-analytics \
  --glob '!quickstart.md'
rg -n "full replay everywhere|internal/test-user filtering" \
  specs/094-product-activation-analytics \
  --glob '!quickstart.md'
rg -n "best-effort.*replay|best effort.*replay" \
  specs/094-product-activation-analytics/spec.md \
  specs/094-product-activation-analytics/research.md \
  specs/094-product-activation-analytics/contracts/replay-masking-contract.md
```

Expected:

- no unresolved `NEEDS CLARIFICATION`
- no old "full replay everywhere" requirement
- no old mandatory internal/test filtering requirement
- any `best-effort real-user replay` match is a prohibition, not permission

## Artifact Review Checklist

Before `$speckit-tasks`, confirm:

- [ ] [research.md](./research.md) has provider, identity, consent, replay,
      retention, delivery, and rollout decisions.
- [ ] [data-model.md](./data-model.md) defines logical entities and validation
      rules.
- [ ] [contracts/parallel-measurement-matrix.md](./contracts/parallel-measurement-matrix.md)
      lists every public/product event route.
- [ ] [contracts/yandex-all-pages-inventory.md](./contracts/yandex-all-pages-inventory.md)
      lists every browser-rendered page class.
- [ ] [contracts/replay-masking-contract.md](./contracts/replay-masking-contract.md)
      distinguishes replay-disabled from fully blocked page classes.
- [ ] [contracts/identity-attribution-contract.md](./contracts/identity-attribution-contract.md)
      rejects raw identity and defines attribution reliability.
- [ ] [contracts/telemetry-gate-contract.md](./contracts/telemetry-gate-contract.md)
      defines the one-time product telemetry acceptance.
- [ ] [contracts/dashboard-rollout-contract.md](./contracts/dashboard-rollout-contract.md)
      defines dashboards, blockers, and smoke evidence.

## Future Implementation Validation Scenarios

These are not runnable until implementation tasks exist.

### Scenario 1: Telemetry Gate Blocks Normal Use Until Accepted

Expected future checks:

- desktop/cabinet unauthenticated or not-accepted state cannot enter normal
  product surfaces
- account/legal/export/deletion flows remain available as defined
- accepted state allows normal product use
- withdrawn/refused-updated-terms state stops future product analytics

### Scenario 2: Forbidden Fields Are Rejected

Expected future checks:

- event schemas reject email, names, raw IDs, meeting titles, transcript/audio,
  calendar text, local paths, object keys, signed URLs, tokens, device names,
  and private free text
- rendered page titles and URLs are sanitized
- analytics evidence contains no live IDs/secrets/private payloads

### Scenario 3: PostHog Primary Funnel Works

Expected future checks:

- PostHog receives approved public acquisition context
- PostHog receives approved product activation events
- first milestones dedupe by stable pseudonymous user identity
- `first_value_session_completed` fires only after ready useful result view
- product owner can inspect source-to-first-value funnel in one workspace

### Scenario 4: Yandex Parallel Scope Is Bounded

Expected future checks:

- Yandex tag appears only on approved page classes
- Yandex receives safe page views/events/goals only
- default offline conversions are limited to `desktop_account_connected` and
  `first_value_session_completed`
- Yandex reports are not treated as product source of truth

### Scenario 5: Replay-Unavailable Page Class Is Safe

Expected future checks:

- page class emits approved sanitized page views/events
- PostHog Session Replay is disabled
- Yandex Webvisor is disabled
- click map, scroll map, and form analytics are disabled
- dashboard/evidence says replay unavailable
- no real-user best-effort replay exists

### Scenario 6: Runtime Propagation Smoke Catches 093-Class Bugs

Expected future checks:

```sh
docker compose -f infra/docker-compose.yml config
infra/scripts/cd-remote.sh --dry-run
```

Production execution requires a later release gate. Smoke evidence must prove:

- host env/secret source
- composed service config
- live container env
- rendered HTML/JS
- allowed and blocked page classes
- provider reachability
- dashboard/goal/offline-conversion visibility

### Scenario 7: Provider Failure Is A Measurement Gap

Expected future checks:

- blocked PostHog/Yandex scripts do not break navigation, recording, upload,
  result viewing, or account flows
- bounded retry/buffering is used only for approved events
- unrecovered loss is visible as a safe delivery-gap caveat

## Full Repository Gate For Future Implementation

Future implementation closeout must run:

```sh
infra/scripts/ci-local.sh
```

Production deployment and paid campaign optimization require separate explicit
approval after `$speckit-analyze`, task execution, review, and release gates.

## Current Implementation Slice Validation

Run focused server checks:

```sh
cd apps/server
uv run pytest \
  tests/unit/test_product_activation_analytics.py \
  tests/contract/test_product_activation_analytics_contract.py \
  tests/integration/test_product_activation_analytics_rollout.py
```

Run focused macOS checks:

```sh
cd apps/macos
swift test --filter ProductActivationAnalyticsContractTests
```

Run metadata-only smoke helpers from repository root:

```sh
infra/scripts/run-product-analytics-smoke.sh
infra/scripts/validate-product-analytics-pages.sh
```

Expected:

- product analytics stays disabled by default;
- synthetic validation events are server-mediated;
- PostHog and Yandex delivery remain disabled or dry-run;
- only public landing/download are approved provider page classes;
- cabinet/product classes remain blocked or replay-unavailable until evidence;
- no live provider IDs, tokens, raw identity, meeting content, or signed URLs
  appear in committed artifacts.
