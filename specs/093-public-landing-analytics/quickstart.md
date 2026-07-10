# Quickstart: Public Landing Analytics

**Feature**: 093-public-landing-analytics

This guide describes validation scenarios for implementation. Commands
reference tests expected to be created during `$speckit-tasks` and
`$speckit-implement`.

## Prerequisites

- Active feature directory: `specs/093-public-landing-analytics/`
- Local server dependencies installed.
- No real analytics provider IDs, ad account IDs, visitor IDs, cookies, or raw
  network payloads in committed tests/evidence.
- Use synthetic Yandex provider IDs in local tests, such as `YA_TEST_COUNTER`,
  only in render-only mode.

## Focused Validation Scenarios

### 1. Analytics Disabled By Default

Expected:

- `/` and `/download` render normally.
- No live Yandex, Google, PostHog, Clarity, GTM, or other analytics script URL
  appears.
- No consent banner is shown if analytics is unavailable.
- Existing landing copy, CTAs, local assets, and accessibility skip link still
  pass current tests.

### 2. Configured But Consent Unknown

Expected:

- Public pages show a non-blocking Russian analytics consent control.
- No provider script loads before a choice.
- Yandex Metrica and Session Replay are not loaded before consent.
- GA4, Google Analytics, Google Ads tags, and GTM are not present in Phase 1.
- Accept all, necessary-only, customize, and later change actions are keyboard
  accessible.
- Footer and consent UI link to privacy, cookies, terms, analytics-consent
  text, and cookie settings.
- Legal page routes render without live analytics until the relevant optional
  category is granted.

### 3. Consent Accepted Or Customized

Expected:

- Approved Yandex provider snippets load only on `/` and `/download` when the
  relevant optional category is granted.
- `public_landing_viewed` fires on `/`.
- `public_download_viewed` fires on `/download`.
- Section, CTA, installer download, and login intent events fire once per
  action per provider when analytics is granted.
- Replay/behavior recording is allowed only for public pages and only when the
  behavior-replay category is granted.

### 4. Necessary Only Or Revoked

Expected:

- Future public-page interactions do not send non-essential analytics events.
- Replay remains off.
- The public UX still works.
- A public-page control allows changing the choice.

### 5. Public Funnel

Expected:

- Hero/header/final download CTAs produce `public_landing_cta_clicked` with
  stable CTA labels.
- `/download` produces `public_download_viewed`.
- Installer package click produces `public_installer_download_clicked`.
- Login links produce `public_login_intent_clicked`, separate from installer
  download.

### 6. UTM Attribution

Expected:

- Standard UTM parameters are preserved for provider attribution.
- Source and medium are normalized.
- Unsafe UTM values are dropped or marked unsafe rather than sent.
- Direct `/download` traffic is not falsely attributed to landing CTA.

### 7. Negative Scope

Expected:

- `/login`, cabinet, admin, API, meeting, upload, playback, deletion, and
  desktop embedded routes do not include landing analytics or replay.
- Authenticated pages do not receive the public analytics event dispatcher.

### 8. Provider Failure

Expected:

- Blocking Yandex scripts does not break page navigation, CTAs, or installer
  download.
- Console-critical errors are avoided or bounded.
- Known measurement loss is documented in evidence, not hidden.

### 9. Provider Dashboard Smoke

Run only with explicit release/campaign-readiness approval.

Expected:

- Yandex Metrica receives the configured public goals.
- Yandex Direct linking/import status is checked externally.
- Legal readiness evidence records owner, status, date, blockers, and
  campaign-readiness decision without treating it as legal advice.
- Evidence is metadata-only and redacted.

## Focused Test Commands

Run focused tests during implementation as they are added:

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_public_landing.py \
  tests/unit/test_public_analytics.py \
  tests/contract/test_public_landing_contract.py \
  tests/contract/test_public_analytics_contract.py

cd apps/server && PYTHONPATH=src uv run --extra dev ruff check .
```

Run a forbidden-content scan before closeout:

```sh
rg -n -i \
  -e "authorization\\s*[:=]\\s*bearer\\s+[a-z0-9._~+/-]{10,}" \
  -e "x-amz-signature=[a-z0-9]" \
  -e "-----BEGIN [A-Z ]*PRIVATE KEY-----" \
  -e "(refresh_token|access_token|id_token|api[_-]?key|secret|password|passcode|signed_url|client_id|measurement_id|counter_id|visitor_id|client_id)\\s*[:=]\\s*[^,[:space:]}]{4,}" \
  specs/093-public-landing-analytics \
  apps/server/src/twobrain_rec_server/config.py \
  apps/server/src/twobrain_rec_server/public \
  apps/server/tests/unit/test_public_analytics.py \
  apps/server/tests/contract/test_public_analytics_contract.py \
  infra/env/rec.production.env.example
```

## Closeout Gate

Before implementation closeout or PR:

```sh
infra/scripts/ci-local.sh
```

No production deploy, live provider smoke, or campaign launch is part of the
implementation closeout unless the user separately approves a release/deploy
or campaign-readiness gate.
