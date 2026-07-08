# Implementation Evidence: Public Landing Analytics

**Feature**: `093-public-landing-analytics`

**Current lane**: high-risk product/privacy/egress implementation.

**Release state**: implementation readiness only. No production deploy, live
provider smoke, provider dashboard access, paid campaign launch, or live
provider identifiers are part of this evidence unless a separate release or
campaign-readiness gate is approved.

## Baseline Review

Reviewed before implementation:

- `specs/093-public-landing-analytics/spec.md`
- `specs/093-public-landing-analytics/plan.md`
- `specs/093-public-landing-analytics/research.md`
- `specs/093-public-landing-analytics/data-model.md`
- `specs/093-public-landing-analytics/contracts/public-analytics-contract.md`
- `specs/093-public-landing-analytics/contracts/analytics-provider-setup.md`
- `specs/093-public-landing-analytics/contracts/phase2-activation-contract.md`
- `specs/093-public-landing-analytics/quickstart.md`
- `apps/server/src/twobrain_rec_server/public/web.py`
- `apps/server/src/twobrain_rec_server/public/templates.py`
- `apps/server/src/twobrain_rec_server/public/templates/public/landing.html`
- `apps/server/src/twobrain_rec_server/public/templates/public/download.html`
- `apps/server/tests/unit/test_public_landing.py`
- `apps/server/tests/contract/test_public_landing_contract.py`
- `apps/server/src/twobrain_rec_server/config.py`
- `infra/env/rec.production.env.example`

Baseline findings:

- Public web currently exposes `/` and `/download` through server-rendered
  Jinja templates.
- Public pages currently use local static assets and no analytics provider
  scripts.
- There is no existing public analytics runtime configuration, legal-page
  routing, consent UI, analytics event catalog, or analytics browser
  controller.
- Existing landing tests assert local assets, current copy, CTA destinations,
  keyboard skip link, and download handoff behavior.
- Phase 1 must keep Google, GA4, Google Ads, GTM, PostHog, Clarity, Amplitude,
  Mixpanel, Matomo, custom analytics storage, and live provider IDs out of the
  implementation.

## Validation Log

### 2026-07-08 - Setup Review

Commands:

```sh
python3 .specify/extensions/github-issue-canon/scripts/ensure_issue_canon.py
python3 .specify/extensions/github-issue-canon/scripts/validate_issue_canon.py
python3 -m py_compile \
  .specify/extensions/github-issue-canon/scripts/issue_canon_common.py \
  .specify/extensions/github-issue-canon/scripts/ensure_issue_canon.py \
  .specify/extensions/github-issue-canon/scripts/normalize_issue_canon.py \
  .specify/extensions/github-issue-canon/scripts/validate_issue_canon.py
git diff --check
```

Result:

- `github-issue-canon: OK (68 Spec Kit issue(s) checked)`
- `git diff --check` passed

Notes:

- This setup evidence does not validate analytics behavior yet; focused
  analytics tests are added in later tasks.

### 2026-07-08 - Phase 2 Foundation

Implemented:

- Public analytics runtime settings are disabled by default.
- `public.analytics` builds a bounded public-only analytics context for `/` and
  `/download`.
- Public templates include an empty-safe analytics partial.
- Render-only mode emits only local static assets and JSON configuration; it
  does not load live Yandex, Google, PostHog, Clarity, GTM, or consent-manager
  CDN URLs.
- Local `analytics.js` is a controller scaffold only. It reads config and does
  not load providers.
- CookieConsent assets are vendored from `vanilla-cookieconsent@3.1.0`.

CookieConsent source:

```text
package: vanilla-cookieconsent
version: 3.1.0
license: MIT
tarball: https://registry.npmjs.org/vanilla-cookieconsent/-/vanilla-cookieconsent-3.1.0.tgz
integrity: sha512-/McNRtm/3IXzb9dhqMIcbquoU45SzbN2VB+To4jxEPqMmp7uVniP6BhGLjU8MC7ZCDsNQVOp27fhQTM/ruIXAA==
```

Commands:

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_public_analytics.py \
  tests/contract/test_public_analytics_contract.py \
  tests/unit/test_public_landing.py \
  tests/contract/test_public_landing_contract.py

cd apps/server && PYTHONPATH=src uv run --extra dev ruff check \
  src/twobrain_rec_server/config.py \
  src/twobrain_rec_server/public/analytics.py \
  src/twobrain_rec_server/public/templates.py \
  src/twobrain_rec_server/public/web.py \
  tests/unit/test_public_analytics.py \
  tests/contract/test_public_analytics_contract.py \
  tests/contract/test_public_landing_contract.py

git diff --check
```

Result:

- Focused pytest: `18 passed, 1 warning`
- Focused ruff: `All checks passed!`
- `git diff --check` passed

Known limitation:

- Consent UI, UTM extraction, event dispatch, Yandex provider initialization,
  replay gating, legal pages, and production env variables are not implemented
  in this foundation phase. They remain covered by later tasks.

### 2026-07-08 - US1 Source And Campaign Attribution

Implemented:

- Public UTM allowlist: `utm_source`, `utm_medium`, `utm_campaign`, `utm_id`,
  `utm_content`, and `utm_term`.
- Source/medium normalization to lowercase.
- Unsafe UTM values are dropped when they look like email, phone, token,
  signed/private URL, passcode, path, or other private payload.
- Render-only public analytics config includes safe campaign attribution for
  `/` and `/download`.
- Local browser controller can build allowlisted event payloads and has a
  Yandex provider entrypoint gated by an explicit analytics category grant.

Dashboard and reporting caveats:

- Consent undercount is expected: necessary-only, unknown, revoked, blocked
  scripts, or browser-level blocking will reduce measured traffic.
- `public_installer_download_clicked` is web intent only; it does not prove
  install, first open, login, first recording, or first value.
- Direct and unknown traffic must not be "fixed" by inventing campaign values.
- Unsafe campaign values are dropped rather than sanitized into misleading
  labels, so campaign reports may have partial attribution when ad URLs carry
  private or malformed values.
- Yandex Direct optimization requires external dashboard setup and counter
  linking before campaign launch; this implementation does not perform live
  provider smoke.

Commands:

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_public_analytics.py \
  tests/contract/test_public_analytics_contract.py \
  tests/unit/test_public_landing.py \
  tests/contract/test_public_landing_contract.py

cd apps/server && PYTHONPATH=src uv run --extra dev ruff check \
  src/twobrain_rec_server/public/analytics.py \
  src/twobrain_rec_server/public/templates.py \
  tests/unit/test_public_analytics.py \
  tests/contract/test_public_analytics_contract.py \
  tests/unit/test_public_landing.py

git diff --check
```

Result:

- Focused pytest: `24 passed, 1 warning`
- Focused ruff: `All checks passed!`
- `git diff --check` passed

Known limitation:

- Consent UI is not implemented at this checkpoint. The provider entrypoint
  remains explicit and gated so no provider script loads before a later consent
  decision calls it.

### 2026-07-08 - US2 Public Conversion Events

Implemented:

- Stable landing section labels: `hero`, `platforms`, `outcomes`, `trust`, and
  `final_cta`.
- Stable CTA labels for header, hero, final download, hero/final login,
  download-page installer, and download-page login paths.
- Public page view event selection for `/` and `/download`.
- Click dispatch for landing CTA, installer download intent, and public login
  intent.
- Section visibility dispatch through `IntersectionObserver`.
- One-event-per-action deduplication for page views, CTA clicks, and section
  reach within a page load.
- Route regression coverage confirming analytics attributes do not change
  landing CTA destinations, login destinations, or installer handoff behavior.

Yandex goal mapping notes:

| Goal key | Yandex event name | Conversion role | Notes |
| --- | --- | --- | --- |
| `landing_view` | `public_landing_viewed` | funnel entry | Fires for `/` after analytics consent and provider init. |
| `landing_engaged` | `public_landing_section_seen` | secondary | Uses stable `section_id`; does not send visible section text. |
| `landing_cta_click` | `public_landing_cta_clicked` | secondary | Uses stable `cta_location` and `target_kind=download_page`. |
| `download_page_view` | `public_download_viewed` | secondary | Separates direct `/download` traffic from landing CTA click. |
| `installer_download_click` | `public_installer_download_clicked` | primary web conversion | Candidate optimization goal for Yandex Direct. |
| `login_intent_click` | `public_login_intent_clicked` | secondary | Kept separate from installer download intent. |

Commands:

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_public_analytics.py \
  tests/contract/test_public_analytics_contract.py \
  tests/unit/test_public_landing.py \
  tests/contract/test_public_landing_contract.py

cd apps/server && PYTHONPATH=src uv run --extra dev ruff check \
  src/twobrain_rec_server/public/analytics.py \
  tests/unit/test_public_analytics.py \
  tests/contract/test_public_analytics_contract.py \
  tests/unit/test_public_landing.py

node --check apps/server/src/twobrain_rec_server/public/static/public/analytics.js
git diff --check
```

Result:

- Focused pytest: `29 passed, 1 warning`
- Focused ruff: `All checks passed!`
- `node --check` passed
- `git diff --check` passed

Known limitation:

- Consent UI, consent persistence, legal-page routes, replay-category gating,
  provider-failure hardening, production env examples, and live Yandex dashboard
  smoke remain later tasks. No live goal or counter identifiers were added.
