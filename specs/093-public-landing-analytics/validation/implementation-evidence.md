# Implementation Evidence: Public Landing Analytics

**Feature**: `093-public-landing-analytics`

**Current lane**: high-risk product/privacy/egress implementation.

**Release state**: production deployed for the approved public scope. Yandex
Metrica counter/goals, provider dashboard access, and production provider smoke
are complete for `/` and `/download`; paid campaign launch remains blocked on
legal/campaign-readiness approval.

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

### 2026-07-08 - US3 Privacy, Consent, Legal Pages, And Replay Scope

Implemented:

- Server analytics context now exposes the consent state catalog:
  `unknown`, `accepted_all`, `necessary_only`, `customized`, and `revoked`,
  plus the allowed state transitions.
- Public pages use self-hosted CookieConsent v3.1.0 with Russian copy,
  `accept all`, `necessary only`, `customize`, category choices, local
  persistence keyed by consent-copy revision, and a public cookie-settings
  control.
- Yandex Metrica loads only after the `analytics` category is granted.
- Yandex Webvisor/behavior replay is enabled only when both analytics and
  `behavior_replay` are granted and the server config allows replay.
- Custom public events are gated by current analytics consent and filtered
  through stable allowlists for `section_id`, `cta_location`, and
  `target_kind`.
- Public legal routes now exist for `/privacy`, `/cookies`, `/terms`, and
  `/analytics-consent`.
- Public footer/legal links render on public pages. The cookie-settings button
  appears only when analytics is configured for the current public surface.
- Contract coverage verifies that public analytics config/assets are absent
  from login, admin, cabinet-like, API, and legal-page surfaces even when
  render-only analytics is enabled.

Legal-readiness references reviewed for this implementation draft:

- Official Federal Law No. 152-FZ text on the Russian legal-information portal:
  `https://pravo.gov.ru/proxy/ips/?docbody=&nd=102108261`
- Roskomnadzor personal-data operator notification portal:
  `https://pd.rkn.gov.ru/operators-registry/notification/`
- Yandex Metrica cookie/localStorage behavior documentation:
  `https://yandex.ru/support/metrica/en/general/cookie-usage`

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
  src/twobrain_rec_server/public/web.py \
  tests/unit/test_public_analytics.py \
  tests/contract/test_public_analytics_contract.py \
  tests/unit/test_public_landing.py

node --check apps/server/src/twobrain_rec_server/public/static/public/analytics.js
git diff --check
```

Result:

- Focused pytest: `35 passed, 1 warning`
- Focused ruff: `All checks passed!`
- `node --check` passed
- `git diff --check` passed

Known limitation:

- The legal pages are implementation-ready draft copy, not final legal advice.
  Before paid campaign launch the real operator requisites, privacy/cookie/
  analytics-consent wording, personal-data operator notification status, and
  any cross-border/provider review must be confirmed by the project owner or
  counsel.
- At this checkpoint, no production deploy, live provider smoke, live Yandex
  goal creation, live account IDs, raw cookies, visitor IDs, or screenshots
  were added. Later production closeout evidence below supersedes the
  deploy/provider-smoke status for the approved public scope.

### 2026-07-08 - US4 Phase 2 Activation Contract Guardrails

Implemented:

- Contract tests scan public Phase 1 assets/templates for deferred provider
  script markers and Phase 2 activation event names.
- Phase 2 activation contract now names future activation events without
  authorizing implementation.
- Added explicit gates for event ownership, identity decision, consent/notice
  decision, and deletion/reporting truth before any product analytics work.
- Phase 2 remains planning-only: no PostHog script/SDK, product event capture,
  desktop provider calls, authenticated identity linking, cabinet replay, or ad
  optimization against product activation was added.

Commands:

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_public_analytics_contract.py

cd apps/server && PYTHONPATH=src uv run --extra dev ruff check \
  tests/contract/test_public_analytics_contract.py

git diff --check
```

Result:

- Focused contract pytest: `11 passed, 1 warning`
- Focused ruff: `All checks passed!`
- `git diff --check` passed

Known limitation:

- Product activation attribution is still out of Phase 1. A later
  legal-approved Spec Kit slice must choose provider, identity, consent/notice,
  retention, deletion truth, and validation before implementation.

### 2026-07-08 - US5 Operations And Campaign Readiness

Implemented:

- Production config rejects enabled public analytics without a Yandex counter
  ID and rejects non-numeric placeholder/test/Google/GTM-like counter values in
  production.
- Runtime settings remain Yandex-only; no Google/GA4/GTM runtime settings were
  added.
- Production env example documents disabled-by-default public analytics,
  runtime-only Yandex counter ID, validation mode, replay flag, and consent
  copy version without committing a live ID.
- Provider setup contract now records runtime env checklist, provider
  failure/duplicate-init behavior, and a structured campaign closeout template.
- Browser controller records provider script load failure, stops future custom
  event dispatch when provider is blocked, and avoids duplicate provider script
  initialization.

Commands:

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_public_analytics.py \
  tests/contract/test_public_analytics_contract.py

cd apps/server && PYTHONPATH=src uv run --extra dev ruff check \
  src/twobrain_rec_server/config.py \
  tests/unit/test_public_analytics.py \
  tests/contract/test_public_analytics_contract.py

node --check apps/server/src/twobrain_rec_server/public/static/public/analytics.js
git diff --check
```

Result:

- Focused pytest: `25 passed, 1 warning`
- Focused ruff: `All checks passed!`
- `node --check` passed
- `git diff --check` passed

Campaign readiness status:

```yaml
feature: 093-public-landing-analytics
analytics_runtime:
  enabled: false
  yandex_counter_id: runtime_only_redacted
  validation_mode: disabled
  replay_enabled: false
legal_readiness:
  owner: not_assigned
  review_status: not_started
  operator_notice_status: not_checked
  foreign_provider_status: yandex_only_phase1_google_deferred
campaign_readiness:
  decision: blocked
  blockers:
    - legal_reviewer_not_approved
    - paid_campaign_readiness_not_approved
```

Known limitation:

- At this checkpoint, live provider smoke, Yandex Direct linking, live
  dashboard access verification, legal approval, and campaign launch were still
  deferred. Later production closeout evidence below supersedes the provider
  smoke/dashboard status for the public scope only. Paid traffic remains
  blocked until a separate legal/campaign approval gate.

### 2026-07-08 - Final Closeout Validation

Risk / validation lane:

- High-risk product/privacy/egress implementation.
- Spec Kit implementation lane completed through setup, foundation, US1-US5,
  and polish evidence.

Quickstart focused validation:

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_public_landing.py \
  tests/unit/test_public_analytics.py \
  tests/contract/test_public_landing_contract.py \
  tests/contract/test_public_analytics_contract.py
```

Result:

- `41 passed, 1 warning`

Full server lint:

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev ruff check .
```

Result:

- `All checks passed!`

Forbidden-content scan:

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

Result:

- Reviewed matches were field names, local variable names, secret-file readers,
  or redacted placeholders:
  - `counter_id` / `lowered_counter_id` local variables in config code.
  - `postgres_password` and `web_csrf_secret` secret-file reader assignments in
    config code.
  - `_normalized_counter_id` local helper usage.
  - `yandex_counter_id: runtime_only_redacted` in docs/evidence.
- No live provider IDs, ad account IDs, raw cookies, visitor IDs, bearer
  tokens, signed URLs, private keys, raw network payloads, email/account
  identifiers, meeting text, transcript, or audio content were found.

Local CI:

```sh
infra/scripts/ci-local.sh
```

Result:

- `ci_local_result=pass`
- Server tests: `1068 passed, 4 skipped, 1 warning`
- Server lint: `All checks passed!`
- Python compile: passed
- RLS hardening validation boundary reported `rls_validation_result=blocked`
  because a dedicated `postgres_test` database/destructive production probe was
  not provided; the overall local CI gate still returned pass.
- Production compose config rendered with public analytics disabled and no live
  Yandex counter ID.
- Deployment evidence scan: pass

Checklist review:

- `requirements.md`: all checklist items complete; no open requirement-quality
  blockers.
- `privacy.md`: all checklist items complete; privacy, consent, egress, replay,
  forbidden-data, and live-smoke separation requirements remain represented in
  implementation/tests/evidence.
- `ux.md`: all checklist items complete; consent control and analytics metadata
  preserve the install-first public flow and CTA destinations.
- `operations.md`: all checklist items complete; launch blockers, env gating,
  dashboard setup, provider failure, and legal readiness remain documented.

Structured legal/campaign readiness:

```yaml
legal_readiness:
  owner: not_assigned
  review_status: not_started
  reviewed_at: not_reviewed
  operator_notice_status: not_checked
  foreign_provider_status: yandex_only_phase1_google_deferred
  blockers:
    - operator_requisites_not_committed
    - counsel_or_owner_review_not_recorded
  campaign_decision: blocked
deployment:
  production_deploy: completed_for_public_scope
  live_provider_smoke: completed_for_public_scope
  paid_campaign_launch: blocked
```

Closeout statement:

- Implementation and production deployment are complete for the approved public
  scope `/` and `/download`.
- This is not legal approval or paid campaign launch approval.
- This does not expand analytics into login, cabinet, desktop, meetings,
  uploads, playback, deletion, admin, API, legal pages, or embedded desktop
  product surfaces.

### 2026-07-08 - Production Provider Closeout

Scope:

- Public analytics live on production for `/` and `/download` only.
- Login/authenticated/product/legal/API surfaces remain outside 093 analytics
  scope.
- Product activation analytics remains feature `094-product-activation-analytics`.

Yandex provider setup:

- Production Yandex Metrica counter was created for `rec.2brain.pro`.
- Domain-only collection is enabled for the production domain.
- Webvisor, scroll map, and form analytics are enabled in the provider, but the
  browser controller still loads Webvisor only after `behavior_replay` consent
  and only for the approved public pages.
- Six JavaScript-event goals are configured and visible in Yandex Metrica:
  `public_landing_viewed`, `public_landing_section_seen`,
  `public_landing_cta_clicked`, `public_download_viewed`,
  `public_installer_download_clicked`, and `public_login_intent_clicked`.
- Provider dashboard links:
  - Overview: `https://metrica.yandex.ru/overview?id=<runtime-counter-id>`
  - Goals/conversions:
    `https://metrica.yandex.ru/stat/conversion_rate?id=<runtime-counter-id>`
  - Webvisor: Yandex Metrica UI -> Behavior -> Webvisor

Production deployment:

```text
deploy_result=pass
branch=codex/deploy-093-public-analytics
deployed_sha=3e35e9af1def0e106ef811a52ace49b4b6723546
backup_reference=/opt/projects/2brain-rec/backups/20260708T204545Z
readiness_verdict=infra_smoke_ready
smoke_result=pass
```

Production runtime checks:

- `rec-api` container is healthy.
- `rec-processing-worker` restarted successfully.
- Production health endpoints passed:
  - `https://rec.2brain.pro/api/v1/health/live`
  - `https://rec.2brain.pro/api/v1/health/ready`
- Live `rec-api` container environment includes public analytics enabled,
  runtime Yandex counter ID configured, validation mode disabled, replay flag
  enabled, and consent copy version `2026-07-08.1`.
- Rendered HTML verification passed:
  - `/` contains the public analytics config, runtime counter reference,
    landing page event catalog, CTA events, and local analytics controller.
  - `/download` contains the public analytics config, runtime counter
    reference, download page event catalog, installer-download event, and local
    analytics controller.
  - `/login` does not contain the public analytics config or runtime counter.
- Static/provider reachability passed:
  - `https://rec.2brain.pro/static/public/analytics.js` returned HTTP 200.
  - `https://mc.yandex.ru/metrika/tag.js` returned HTTP 200.

Production bug found and fixed during closeout:

- The server-side `.env` contained the public analytics values, but
  `docker-compose.yml` did not pass those values into `rec-api`; the first
  post-deploy smoke showed `TWOBRAIN_PUBLIC_ANALYTICS_ENABLED=false` inside the
  live container and no analytics config in rendered public pages.
- Fix committed in `effff92a` on the feature branch and deployed from clean
  deploy branch commit `3e35e9af`: `rec-api` now receives runtime public
  analytics environment overrides while committed env templates remain safe and
  disabled by default.
- Regression coverage added in
  `apps/server/tests/integration/test_compose_hardening.py` to prove public
  analytics runtime overrides reach `rec-api` and are not sent to the worker as
  product analytics.

Final validation summary:

- Focused public analytics tests: `41 passed, 1 warning`
- Runtime compose mapping tests plus public analytics contracts:
  `37 passed, 1 warning`
- Full deployment CI: `1069 passed, 4 skipped, 1 warning`
- Server lint: `All checks passed!`
- Production backup/restore rehearsal: `pass`
- Production smoke: `pass`
- Open GitHub issues with label `feature:093`: `[]`

Remaining boundaries after full closeout:

- Paid campaign launch remains blocked until legal/campaign-readiness approval
  is recorded.
- 093 measures public web intent only; it does not prove install, desktop first
  open, account connection, recording, result view, or first value.
- No Google/GA4/GTM/PostHog/product analytics was enabled in 093.
- 094 must handle product activation analytics through a separate high-risk SDD
  flow.
