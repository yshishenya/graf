# Quickstart: Product Analytics Provider Rollout

**Feature**: `096-product-analytics-provider-rollout`

This quickstart is the review and validation guide for the provider rollout.
It is safe to commit because it contains no live provider identifiers, tokens,
payloads, screenshots, account data, or secret paths.

## Current Implementation Status

096 has completed planning, implementation, convergence, production runtime
enablement for self-hosted PostHog, and post-runtime review remediation on the
feature branch.

Self-hosted PostHog delivery is live-safe validated in production with runtime
secret-file configuration and metadata-only evidence. No PostHog project key is
committed. No Yandex OAuth token, live counter ID, ClientID, Yclid, cookie, or
offline conversion row has been committed. Yandex offline upload, product
rollout readiness, and paid campaign launch remain blocked.

## Review Order

1. Read [spec.md](./spec.md).
2. Read [plan.md](./plan.md).
3. Read [research.md](./research.md).
4. Read [data-model.md](./data-model.md).
5. Read each file in [contracts/](./contracts/).
6. Read [validation/dashboard-evidence.md](./validation/dashboard-evidence.md).
7. Read [validation/implementation-evidence.md](./validation/implementation-evidence.md).

## Planning Validation Commands

Run from the repository root:

```sh
.specify/scripts/bash/check-prerequisites.sh --json --paths-only
rg -n "\[NEEDS CLARIFICATION\]|NEEDS CLARIFICATION:" specs/096-product-analytics-provider-rollout
git diff --check
git status --short --branch
```

Expected result for this planning pass:

- prerequisites script returns the active 096 spec/plan paths;
- no `NEEDS CLARIFICATION` markers remain;
- `git diff --check` reports no whitespace errors;
- only intended 096 planning artifacts and managed agent-context updates are
  changed.

## Implementation Validation

`tasks.md` is complete for 096. Future release or production work must keep the
task/evidence mapping intact and append only metadata-safe live evidence.

## 096 Final Validation Command Order

Run from the repository root unless a command changes directory explicitly:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_product_analytics_provider_smoke_output.py \
  tests/contract/test_product_analytics_provider_rollback.py \
  tests/contract/test_product_analytics_dashboard_evidence.py \
  tests/integration/test_product_analytics_provider_readiness_blockers.py

cd ../..
swift test --package-path apps/macos --filter ProductActivationAnalyticsContractTests
infra/scripts/run-product-analytics-provider-smoke.sh
infra/scripts/validate-product-analytics-provider-pages.sh
infra/scripts/rollback-product-analytics-providers.sh
infra/scripts/ci-local.sh
infra/scripts/cd-remote.sh --dry-run
```

Do not run this command as part of 096 without separate explicit approval:

```sh
infra/scripts/cd-remote.sh --execute
```

Passing 096 provider smoke means the provider layer has reviewable technical
evidence. It does not mean product rollout readiness, direct user rollout
approval, or paid campaign launch approval.

### 1. PostHog Stack

Validate that self-hosted PostHog is:

- deployed on the same production server as GRAF for the first rollout;
- exposed through a separate analytics domain;
- isolated by Docker service boundary, TLS routing, runtime secret files,
  volumes, backup target, resource limits, restart policy, and health checks;
- represented in deploy dry-run orchestration without printing live secrets;
- backed by the official generated PostHog self-hosted Compose runtime, not by
  the simplified GRAF handoff contract alone;
- portable to a future separate analytics server by changing DNS/runtime
  endpoint, not event names or dashboard contracts.

Base `rec-api` Compose uses an empty committed placeholder for optional
PostHog/Yandex provider secret sources so disabled deployments can execute
before live project keys and OAuth tokens exist. Live enablement must replace
that source with out-of-git `infra/secrets/...` files through the documented
`*_SECRET_FILE` variables; never paste provider values into env files.

### 2. PostHog Data Delivery

Validate that PostHog accepts only approved product analytics routes:

- server-mediated events from the 094 activation scaffold;
- web-direct page/event/autocapture delivery;
- desktop-direct product analytics delivery to self-hosted PostHog only.

Each route must also declare RBAC/audit expectations, retention/deletion truth,
dashboard caveats, retry/loss behavior, and rollback behavior before readiness
can pass.

Credential material remains forbidden even in first-party PostHog:

- passwords/passcodes;
- OAuth codes;
- access, refresh, or ID tokens;
- API keys and provider/client secrets;
- signed URLs;
- cookies;
- private keys;
- raw audio files;
- raw payload dumps in logs/evidence.

### 3. PostHog Autocapture Everywhere

Validate that every current browser-rendered page class has PostHog autocapture
enabled after credential suppression is active.

Validate that future browser pages default to PostHog autocapture after they
inherit the global credential suppression path and update the page inventory.

PostHog session replay is not implied by this check. Replay remains disabled
until a separate page-class masking/storage/legal/QA proof exists.

### 4. Yandex Counter And Page Scope

Validate that the existing 093 production Yandex counter is reused without
committing the live counter ID.

Validate that `/` and `/download` remain approved.

Validate that every other current or future browser page class is either:

- explicitly approved for safe Yandex page/event collection;
- blocked; or
- marked replay-unavailable.

Yandex Webvisor, click map, scroll map, and form analytics require separate
page-class proof and are not approved by PostHog autocapture.

### 5. Yandex Offline Conversions

Validate live upload readiness for exactly these conversion names:

- `desktop_account_connected`
- `first_value_session_completed`

No other product activation event may be uploaded to Yandex in 096.

Validate:

- OAuth token comes only from a runtime secret file;
- upload uses a supported identity source without exposing raw values in
  evidence;
- `UserId` upload is allowed only when the same pseudonymous GRAF user ID was
  sent to Yandex through `setUserID` and `userParams` on an eligible
  Yandex-counted page;
- `ClientId` and `Yclid` upload require real runtime resolver values and must
  not be synthesized from the GRAF pseudonymous user ID;
- duplicate protection exists;
- provider status can be checked without committing raw CSV rows;
- dashboards show the conversion surface without screenshots containing
  visitor/account data.

### 6. Secret And Env Propagation

Validate:

- runtime secrets are read from files, not committed values;
- provider configuration reaches only intended services;
- deploy dry-run sees the separate PostHog stack without printing secret values;
- smoke scripts redact secret values;
- generated evidence contains no live project keys, counter IDs, tokens,
  cookies, client IDs, Yclids, signed URLs, local paths, raw payloads, account
  names, emails, meeting content, transcripts, or audio references.

### 7. Provider Smoke

The provider smoke scripts must prove:

- PostHog stack health;
- PostHog secret-file wiring;
- PostHog RBAC/access model and audit expectation status;
- provider retention/deletion lifecycle status;
- separate PostHog deploy dry-run handoff;
- PostHog server/web/desktop delivery readiness;
- PostHog autocapture scope;
- Yandex counter reuse;
- Yandex public baseline preservation;
- Yandex blocked-page behavior;
- Yandex offline upload auth and live-safe delivery;
- duplicate protection;
- dashboard readiness;
- rollback.

Smoke output must be metadata-only and safe to commit.

### 8. Rollback

Validate rollback for:

- PostHog server delivery;
- PostHog web-direct delivery;
- PostHog desktop-direct delivery;
- PostHog autocapture;
- PostHog session replay;
- PostHog stack/domain exposure;
- Yandex all-pages expansion;
- Yandex offline upload;
- Yandex Webvisor/maps/forms;
- provider validation mode.

Rollback must create only an analytics measurement gap. Normal GRAF product
workflows must continue.

### 9. Release Gate

Before any future production provider execution or runtime update:

```sh
infra/scripts/ci-local.sh
infra/scripts/cd-remote.sh --dry-run
```

Set or verify pinned PostHog runtime images outside git before production
changes:

```sh
POSTHOG_RUNTIME_ENV_FILE=/opt/graf/posthog/posthog.production.env
POSTHOG_IMAGE=posthog/posthog:<reviewed-pinned-release-tag-or-digest>
```

Runtime hardening on 2026-07-09 pinned the generated PostHog runtime images by
digest outside git. Do not use mutable PostHog runtime images for unattended
operation, and repeat the mutable-tag scan after every future stack update.

Production execution or runtime changes require explicit approval before:

```sh
infra/scripts/cd-remote.sh --execute
```

Passing provider smoke is not paid campaign launch approval.
