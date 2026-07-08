# Implementation Plan: Public Landing Analytics

**Branch**: `codex/093-public-landing-analytics` | **Date**: 2026-07-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/093-public-landing-analytics/spec.md`

## Summary

Add privacy-safe public landing analytics for GRAF's install-first funnel:
landing visit, section reach, CTA click, download page view, installer download
intent, and login intent. Use ready-made provider capabilities from Yandex
Metrica, keep tracking consent-gated, limit Webvisor/behavior recording to `/`
and `/download`, and leave Google/GA4 plus product activation attribution to
later legal-approved slices. Reuse the existing FastAPI/Jinja public templates
and local static assets; do not add a frontend build system, tag manager,
custom analytics backend, paid CMP, or new runtime dependency.

## Technical Context

**Language/Version**: Python 3.13 FastAPI server, Jinja2 templates, static
vanilla JavaScript/CSS.

**Primary Dependencies**: Existing FastAPI/Jinja/static asset pipeline,
Pydantic settings, pytest, ruff. Runtime analytics uses external Yandex
Metrica provider scripts only when enabled and consent permits. Consent uses
self-hosted CookieConsent v3.1.0 as pinned local static assets with MIT
attribution. No new Python package, paid CMP, Google tag, consent-manager CDN,
or frontend package is planned.

**Storage**: No new server database tables. Public consent preference is a
local browser preference keyed by consent-copy version. Analytics event storage
belongs to the configured Yandex Metrica provider. Phase 2 activation identity is
contract-only in this slice.

**Testing**: Focused server unit/contract tests for disabled/enabled analytics
rendering, consent states, public event catalog, no-private-data allowlist,
public-only replay scope, UTM normalization, no provider calls in disabled
mode, no Google tags in Phase 1, no consent-manager CDN URLs, and
landing/download regression. Static JS/CSS checks and ruff. Manual Yandex
dashboard smoke only for production/campaign readiness.

**Risk / Validation Lane**: High-risk feature. The slice touches privacy,
third-party egress, advertising attribution, session observation, public UX,
consent, external provider configuration, operations, and campaign launch
readiness.

**Release Gate**: No deploy. Implementation readiness only. Production deploy,
live provider IDs, and paid campaign launch require a separate release/deploy
lane and explicit approval.

**Target Platform**: Linux containerized FastAPI server at the public GRAF
site, plus browser clients on desktop/mobile. Authenticated cabinet and macOS
embedded cabinet are negative-scope validation surfaces only.

**Project Type**: Server-rendered public web surface with static browser
behavior.

**Performance Goals**: Public pages render and remain usable without analytics.
Analytics and consent scripts do not block first paint or the installer
download action. One user action emits at most one event per provider. Provider
script failures do not create user-visible hard errors.

**Constraints**: No custom analytics backend. No Google Analytics, GA4, Google
Ads tags, GTM/tag manager, or Google Consent Mode in Phase 1. No PostHog,
Clarity, Amplitude, Mixpanel, Matomo, or product activation code in Phase 1. No
live provider IDs, ad account IDs, credentials, cookies, raw network payloads,
visitor identifiers, or private meeting/account content in git, tests, logs,
screenshots, diagnostics, or evidence. Consent copy and UI are Russian. Replay
is forbidden off public `/` and `/download`.

**Scale/Scope**: Two public routes, six public analytics events, one external
analytics provider, one consent control, one campaign UTM canon, dashboard
setup guidance, and Phase 2 activation contract. No authenticated product
tracking in this slice.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Before Phase 0**: PASS with high-risk gates.

- Capture-first MVP integrity: PASS. No macOS capture, permissions, recording,
  routing, installer, upload custody, MediaScribe, or local artifact behavior
  changes.
- Visible consent and user control: PASS with required tasks. The feature adds
  explicit analytics consent and must not alter recording visibility or Stop.
- Data boundary and secret discipline: PASS with required tasks. The feature
  adds third-party public analytics egress, so provider IDs, event fields,
  consent behavior, replay scope, and forbidden data require tests and
  metadata-only evidence. No meeting content, credentials, account identifiers,
  raw paths, object keys, tokens, signed URLs, or transcripts may be sent.
- Deletion truth and lifecycle accounting: PASS. No GRAF meeting artifact is
  created. Analytics copy must not promise universal deletion from third-party
  analytics providers.
- Spec-driven delivery: PASS. Full high-risk Spec Kit sequence is required:
  specify, clarify, plan, checklist, tasks, analyze, task-to-issues, implement.
- UI and brand distance: PASS with required tasks. Consent UI must fit the
  original GRAF public landing and avoid marketing-page redesign.
- Ponytail form: PASS. Reuse current public routes, templates, settings,
  static assets, and tests. Add only the smallest wrapper needed around
  provider snippets and consent/event dispatch.

**After Phase 1 design**: PASS. Research and contracts keep the work to
public pages, Yandex Metrica, strict no-tags-before-consent behavior, no Google
tracking, no custom analytics storage, no new runtime dependencies, and
metadata-only validation.

## Validation Plan

- Run focused public landing tests for current copy/CTA/download behavior.
- Add and run focused contract/unit tests for analytics disabled by default,
  enabled config rendering, consent copy and category states, legal-page links,
  safe event catalog, public route scope, no analytics on
  login/cabinet/admin/product surfaces, UTM normalization, and no forbidden
  content in event fields.
- Run focused static checks for public analytics JS/CSS, self-hosted
  CookieConsent v3.1.0 assets, and no new frontend toolchain/CDN dependencies
  beyond the explicitly configured Yandex provider script hosts.
- Run quickstart scenarios from [quickstart.md](./quickstart.md).
- Run forbidden-content scans over `specs/093-public-landing-analytics`,
  public templates/static files, settings, tests, infra env examples, and
  evidence.
- Run `infra/scripts/ci-local.sh` before closeout because the slice changes
  high-risk public UX, privacy, egress, and release/campaign readiness.
- Do not run production CD dry-run/execute or live provider dashboard smoke
  unless a separate release/deploy or campaign-readiness gate is approved.

## Project Structure

### Documentation (this feature)

```text
specs/093-public-landing-analytics/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── public-analytics-contract.md
│   ├── analytics-provider-setup.md
│   └── phase2-activation-contract.md
├── checklists/
│   ├── requirements.md
│   ├── privacy.md
│   ├── ux.md
│   └── operations.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── config.py
└── public/
    ├── web.py
    ├── templates.py
    ├── templates/public/
    │   ├── _analytics.html
    │   ├── landing.html
    │   ├── download.html
    │   ├── privacy.html
    │   ├── cookies.html
    │   ├── terms.html
    │   └── analytics_consent.html
    └── static/public/
        ├── analytics.js
        ├── cookieconsent.umd.js
        ├── cookieconsent.css
        └── landing.css

apps/server/tests/
├── contract/
│   ├── test_public_landing_contract.py
│   └── test_public_analytics_contract.py
└── unit/
    ├── test_public_landing.py
    └── test_public_analytics.py

infra/env/rec.production.env.example
CHANGELOG.md
AGENTS.md
```

**Structure Decision**: Keep Phase 1 inside the existing server-owned public
web package. `Settings` owns non-secret analytics configuration; public route
rendering passes a bounded analytics context to templates; a small local
`analytics.js` owns consent state, event dispatch, section observation, and
Yandex provider load order. CookieConsent v3.1.0 is vendored only as local
static assets and must not load from a runtime CDN. Tests stay under the
current server test suite. No
cabinet, macOS, storage, processing, or ingestion source changes are planned.

## Complexity Tracking

No constitution violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
