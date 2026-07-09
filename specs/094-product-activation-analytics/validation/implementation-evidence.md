# Implementation Evidence: Product Activation Analytics 094

Feature: `094-product-activation-analytics`

Risk / validation lane: high-risk Spec Kit implementation slice.

Implementation boundary:

- Safe contract, config, tests, docs, env placeholders, and smoke helpers are in
  scope.
- Live PostHog setup, live Yandex all-pages expansion, Yandex offline upload,
  production deploy, and paid campaign launch are out of scope.
- Public 093 production scope remains `/` and `/download` only.

## Task Evidence

| Area | Evidence |
| --- | --- |
| Config | Product analytics runtime settings are disabled by default with 90-day minimum retention. |
| Privacy | Forbidden-field validator rejects raw identity, meeting content, local paths, secrets, tokens, signed URLs, and private text. |
| Consent | Product telemetry gate model blocks normal product use until accepted and stops future analytics after withdrawal/refusal. |
| Providers | PostHog and Yandex wrappers are disabled by default; provider smoke is dry-run only. |
| Runtime | Compose passes product analytics env only to `rec-api`, not the processing worker. |
| Desktop | macOS payload models and client shell keep direct provider egress closed until every approval exists. |

## Validation Runs

### Focused Server Tests

Command:

```sh
cd apps/server
uv run pytest \
  tests/unit/test_product_activation_analytics.py \
  tests/contract/test_product_activation_analytics_contract.py \
  tests/integration/test_product_activation_analytics_rollout.py
```

Result: pass, `23 passed in 0.44s`.

### OpenAPI Drift

Command:

```sh
cd apps/server
uv run pytest tests/contract/test_openapi_contract_drift.py
```

Result: pass, `5 passed in 5.18s`.

Note: first full CI attempt failed on OpenAPI drift after adding the
product-analytics API. The committed runtime contract at
`specs/012-server-ingest-foundation/contracts/openapi.yaml` was regenerated
from the current FastAPI schema, and the drift test passed.

### Focused macOS Tests

Command:

```sh
cd apps/macos
swift test --filter ProductActivationAnalyticsContractTests
```

Result: pass, `7 tests, 0 failures`.

### Metadata-Only Smoke Helpers

Commands:

```sh
infra/scripts/run-product-analytics-smoke.sh
infra/scripts/validate-product-analytics-pages.sh
```

Result:

```text
product_analytics_smoke=pass
provider_statuses=disabled,not_applicable
product_analytics_page_scope=pass
approved=public_landing,public_download
blocked=auth_callback,admin,error_pages
```

### Lint And Whitespace

Commands:

```sh
cd apps/server
uv run ruff check \
  src/twobrain_rec_server/product_analytics \
  src/twobrain_rec_server/api/product_analytics.py \
  src/twobrain_rec_server/config.py \
  tests/unit/test_product_activation_analytics.py \
  tests/contract/test_product_activation_analytics_contract.py \
  tests/integration/test_product_activation_analytics_rollout.py
git diff --check
```

Result: pass, `All checks passed!`; no diff whitespace errors.

### Full Local CI

Command:

```sh
infra/scripts/ci-local.sh
```

Result: pass.

Key output:

```text
1106 passed, 4 skipped in 217.25s
server lint: All checks passed!
deployment_evidence_scan=pass files=7 target=docs/deployments/2brain-rec
ci_local_result=pass
```

The RLS validation sub-step reported `rls_validation_result=blocked` with
`reason=postgres_test_database_required`; this is the existing local boundary
message inside a passing `ci-local` run, not a 094 rollout approval.

The production compose config step showed 094 product analytics runtime keys in
`rec-api` only. Product analytics keys are not active in the shared env_file and
do not appear under `rec-migrate` or `rec-processing-worker`.

### No-Secret / Evidence Scan

Command:

```sh
rg -n "sk_live_[A-Za-z0-9]{8,}|sk-proj-[A-Za-z0-9]{8,}|phc_[A-Za-z0-9]{8,}|oauth_token=[A-Za-z0-9._-]{8,}|mc\\.yandex\\.ru/watch/[0-9]{5,}|Authorization: Bearer [A-Za-z0-9._-]{8,}" \
  specs/094-product-activation-analytics \
  docs/analytics \
  apps/server/src/twobrain_rec_server/product_analytics \
  apps/server/src/twobrain_rec_server/api/product_analytics.py \
  apps/macos/Shared/Sources/Models/ProductActivationAnalyticsModels.swift \
  apps/macos/RecApp/Sources/Upload/ProductActivationAnalyticsClient.swift \
  apps/macos/RecApp/Sources/Cabinet/ProductTelemetryGateViewModel.swift
```

Result: pass, no matches.

## Closeout Boundary

No production rollout approval is granted by this file. Campaign readiness and
provider activation require separate legal/product/security/QA approval.

Selected lane closeout: high-risk Spec Kit implementation slice completed for
safe scaffold only. Production rollout, live provider setup, direct desktop
provider egress, Yandex all-pages expansion, offline conversion upload, and
paid campaign optimization remain blocked until separate approvals.
